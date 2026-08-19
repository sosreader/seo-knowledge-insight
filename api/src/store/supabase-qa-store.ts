/**
 * SupabaseQAStore — pgvector-backed implementation of the QAStore interface.
 *
 * Strategy:
 *   - At startup: fetch all QA metadata from Supabase (no embeddings) → in-memory
 *   - hybridSearch: pgvector RPC (over-retrieve) → in-memory keyword/freshness re-rank
 *   - keywordSearch: in-memory (loaded at startup, no embedding needed)
 *   - listQa / categories / collections / getById / getBySeq: in-memory (sync)
 *
 * This means:
 *   - No .npy file needed in container
 *   - Memory usage: QA metadata only (~few MB, not 8MB+ for embeddings)
 *   - hybridSearch is async (Supabase RPC), other methods stay sync
 */

import { supabaseCount, supabaseRpc, supabaseSelect } from "./supabase-client.js";
import { computeKeywordBoostSingle } from "../utils/keyword-boost.js";
import { mapWithConcurrency } from "../utils/concurrency.js";
import {
  filterAndPaginateQa,
  categoriesFromItems,
  collectionsFromItems,
  type ListQaParams,
} from "./qa-filter.js";
import type { QAItem } from "./qa-store.js";
import {
  categoryDiversityBoost,
  matchedQueryTerms,
  novelQueryTermBoost,
  queryTerms,
} from "./query-term-utils.js";
import {
  asList,
  tokenize,
  inferQueryLabels,
  questionSignature,
  QUERY_CATEGORY_HINTS,
  QUERY_INTENT_HINTS,
  QUERY_SCENARIO_HINTS,
} from "./search-engine.js";

/** Timeout for initial load — longer than default to handle cold Supabase. */
const LOAD_TIMEOUT_MS = 25_000;

/** Row returned by match_qa_items() RPC. */
interface MatchRow {
  id: string;
  seq: number;
  question: string;
  answer: string;
  keywords: string[];
  confidence: number;
  category: string;
  difficulty: string;
  evergreen: boolean;
  source_title: string;
  source_date: string;
  source_type: string;
  source_collection: string;
  source_url: string;
  is_merged: boolean;
  extraction_model: string | null;
  maturity_relevance: string | null;
  synonyms: string[];
  freshness_score: number;
  search_hit_count: number;
  primary_category?: string | null;
  categories?: string[] | null;
  intent_labels?: string[] | null;
  scenario_tags?: string[] | null;
  serving_tier?: string | null;
  retrieval_phrases?: string[] | null;
  retrieval_surface_text?: string | null;
  content_granularity?: string | null;
  evidence_scope?: string[] | null;
  booster_target_queries?: string[] | null;
  hard_negative_terms?: string[] | null;
  similarity: number;
}

/**
 * 直接 SELECT qa_items 撈到的 row（startup load / 分頁撈取）。
 *
 * 不含 answer：最肥的欄位（約佔傳輸量 70%），startup 只載入 metadata，
 * 命中後才由 hydrateAnswer() / hydrateAnswers() 批次補撈（見類別方法）。
 *
 * 不含 primary_category 等 extended retrieval 欄位：live schema（2026-08-19 實測）
 * 沒有這些欄位，選取它們一律 42703 column does not exist；日後補 migration 再加回。
 */
interface QARow {
  id: string;
  seq: number;
  question: string;
  keywords: string[];
  confidence: number;
  category: string;
  difficulty: string;
  evergreen: boolean;
  source_title: string;
  source_date: string;
  source_type: string;
  source_collection: string;
  source_url: string;
  is_merged: boolean;
  extraction_model: string | null;
  maturity_relevance: string | null;
  synonyms: string[];
  freshness_score: number;
  search_hit_count: number;
}

const OVER_RETRIEVE_FACTOR = 3;
const KW_BOOST_CONFIG = { boost: 0.1, maxHits: 3, partial: 0.05 } as const;
const SEMANTIC_WEIGHT = 0.7;
const SYNONYM_BOOST = 0.05;

/** startup select 用的欄位；刻意不含 answer 與 extended retrieval 欄位，理由見 QARow 註解。 */
const SELECT_COLUMNS = [
  "id",
  "seq",
  "question",
  "keywords",
  "confidence",
  "category",
  "difficulty",
  "evergreen",
  "source_title",
  "source_date",
  "source_type",
  "source_collection",
  "source_url",
  "is_merged",
  "extraction_model",
  "maturity_relevance",
  "synonyms",
  "freshness_score",
  "search_hit_count",
] as const;

function buildSelectQuery(
  columns: readonly string[],
  pageSize: number,
  offset: number,
): string {
  return `?select=${columns.join(",")}&order=seq.asc&limit=${pageSize}&offset=${offset}`;
}

/**
 * 建構 QAItem。answer 由呼叫端明確傳入：
 *   - 直接 SELECT 路徑（load()）：answer 未撈取，傳 "" placeholder，命中後再 hydrate。
 *   - RPC 路徑（hybridSearch 的 match_qa_items）：RPC 本來就回 answer，傳 row.answer。
 *
 * extended retrieval 欄位（primary_category 等）在兩條路徑都不存在於 live schema，
 * 一律用 category / keywords 推導預設值，不再假裝這些欄位「可能存在」。
 */
function rowToQAItem(row: QARow, answer: string): QAItem {
  return {
    id: row.id,
    seq: row.seq,
    question: row.question,
    answer,
    keywords: row.keywords ?? [],
    confidence: row.confidence ?? 0,
    category: row.category ?? "",
    difficulty: row.difficulty ?? "",
    evergreen: row.evergreen ?? false,
    source_title: row.source_title ?? "",
    source_date: row.source_date ?? "",
    is_merged: row.is_merged ?? false,
    synonyms: row.synonyms ?? [],
    freshness_score: row.freshness_score ?? 1.0,
    search_hit_count: row.search_hit_count ?? 0,
    notion_url: "",
    source_type: row.source_type ?? "meeting",
    source_collection: row.source_collection ?? "seo-meetings",
    source_url: row.source_url ?? "",
    extraction_model: row.extraction_model ?? undefined,
    maturity_relevance:
      (row.maturity_relevance as "L1" | "L2" | "L3" | "L4") ?? undefined,
    primary_category: row.category ?? "",
    categories: row.category ? [row.category] : [],
    intent_labels: [],
    scenario_tags: [],
    serving_tier: "canonical",
    retrieval_phrases: row.keywords ?? [],
    retrieval_surface_text: [row.question, answer, ...(row.keywords ?? [])]
      .filter(Boolean)
      .join("\n"),
    content_granularity: undefined,
    evidence_scope: [],
    booster_target_queries: [],
    hard_negative_terms: [],
  };
}

function computeSynonymBonus(
  query: string,
  synonyms: readonly string[],
): number {
  if (!synonyms || synonyms.length === 0) return 0;
  const queryLower = query.toLowerCase();
  for (const syn of synonyms) {
    const synLower = syn.toLowerCase();
    if (queryLower.includes(synLower) || synLower.includes(queryLower)) {
      return SYNONYM_BOOST;
    }
  }
  return 0;
}

// asList, tokenize, inferQueryLabels, QUERY_*_HINTS imported from search-engine.ts

function metadataScore(query: string, item: QAItem): number {
  const queryLower = query.toLowerCase();
  const terms = queryTerms(query);
  const queryTokens = tokenize(query);
  const surfaceTokens = tokenize(item.retrieval_surface_text ?? "");
  const queryCategories = inferQueryLabels(query, QUERY_CATEGORY_HINTS);
  const queryIntents = inferQueryLabels(query, QUERY_INTENT_HINTS);
  const queryScenarios = inferQueryLabels(query, QUERY_SCENARIO_HINTS);
  const itemCategories = new Set(asList(item.categories));
  const itemIntents = new Set(asList(item.intent_labels));
  const itemScenarios = new Set(asList(item.scenario_tags));

  const phraseBoost =
    computeKeywordBoostSingle(
      query,
      item.retrieval_phrases ?? [],
      KW_BOOST_CONFIG,
    ) * 2.0;
  const surfaceBoost =
    [...queryTokens].filter((token) => surfaceTokens.has(token)).length * 0.03;
  const categoryBoost =
    [...queryCategories].filter((label) => itemCategories.has(label)).length *
    0.08;
  const intentBoost =
    [...queryIntents].filter((label) => itemIntents.has(label)).length * 0.06;
  const scenarioBoost =
    [...queryScenarios].filter((label) => itemScenarios.has(label)).length *
    0.05;
  const exactTermBoost =
    matchedQueryTerms(item.retrieval_surface_text ?? "", terms).size * 0.04;
  const tier = (item.serving_tier ?? "canonical").toLowerCase();
  const targetedBooster = asList(item.booster_target_queries).some((target) =>
    queryLower.includes(target.toLowerCase()),
  );
  const tierScore =
    tier === "booster"
      ? targetedBooster
        ? 0.05
        : -0.08
      : tier === "supporting"
        ? 0.02
        : 0.08;
  const hardNegativePenalty = asList(item.hard_negative_terms).some((term) =>
    queryLower.includes(term.toLowerCase()),
  )
    ? -0.05
    : 0;

  return (
    phraseBoost +
    surfaceBoost +
    categoryBoost +
    intentBoost +
    scenarioBoost +
    exactTermBoost +
    tierScore +
    hardNegativePenalty
  );
}

function itemMatchesCategory(item: QAItem, category: string | null): boolean {
  if (!category) return true;
  const categories = asList(item.categories);
  return categories.length > 0
    ? categories.includes(category)
    : item.category === category;
}

// questionSignature imported from search-engine.ts

function rerankResults(
  results: ReadonlyArray<{ item: QAItem; score: number }>,
  topK: number,
  query: string,
): ReadonlyArray<{ item: QAItem; score: number }> {
  const candidates = [...results];
  const selected: Array<{ item: QAItem; score: number }> = [];
  const terms = queryTerms(query);
  const queryCategories = inferQueryLabels(query, QUERY_CATEGORY_HINTS);

  while (candidates.length > 0 && selected.length < topK) {
    const selectedSigs = new Set(
      selected.map((result) => questionSignature(result.item.question)),
    );
    const selectedCategories = new Set(
      selected.flatMap((result) => asList(result.item.categories)),
    );
    const selectedIntents = new Set(
      selected.flatMap((result) => asList(result.item.intent_labels)),
    );
    const selectedTerms = new Set(
      selected.flatMap((result) => [
        ...matchedQueryTerms(result.item.retrieval_surface_text ?? "", terms),
      ]),
    );

    let bestIndex = 0;
    let bestScore = Number.NEGATIVE_INFINITY;
    for (let index = 0; index < candidates.length; index += 1) {
      const candidate = candidates[index]!;
      let adjusted = candidate.score;
      if (selectedSigs.has(questionSignature(candidate.item.question)))
        adjusted -= 0.25;
      const categories = asList(candidate.item.categories);
      const uncoveredQueryCategories = categories.filter(
        (category) =>
          queryCategories.has(category) && !selectedCategories.has(category),
      ).length;
      adjusted += categoryDiversityBoost(uncoveredQueryCategories);
      const intents = asList(candidate.item.intent_labels);
      if (
        intents.length > 0 &&
        intents.every((intent) => !selectedIntents.has(intent))
      )
        adjusted += 0.04;
      const candidateTerms = matchedQueryTerms(
        candidate.item.retrieval_surface_text ?? "",
        terms,
      );
      const novelTerms = [...candidateTerms].filter(
        (term) => !selectedTerms.has(term),
      ).length;
      adjusted += novelQueryTermBoost(novelTerms, terms.length);
      if (adjusted > bestScore) {
        bestScore = adjusted;
        bestIndex = index;
      }
    }
    if (!Number.isFinite(bestScore)) break;
    selected.push({ item: candidates[bestIndex]!.item, score: bestScore });
    candidates.splice(bestIndex, 1);
  }
  return selected;
}

export class SupabaseQAStore {
  /** 分頁大小；拿掉 answer 後單頁約 0.45MB（實測 25,881 筆 → 13 頁）。 */
  private static readonly PAGE_SIZE = 2000;

  /**
   * 分頁並行度；刻意保守，避免同時打爆 Supabase（這正是原本 500/503 的成因）。
   * 不要調高。
   */
  private static readonly PAGE_CONCURRENCY = 4;

  private items: QAItem[] = [];
  private idIndex: Map<string, QAItem> = new Map();
  private seqIndex: Map<number, QAItem> = new Map();
  private _loaded = false;

  /** answer 補撈的 memo cache：同一 Lambda instance 內重複命中同一 id 不用重打 Supabase。 */
  private answerCache: Map<string, string> = new Map();

  get loaded(): boolean {
    return this._loaded;
  }

  get count(): number {
    return this.items.length;
  }

  /** Expose items for read-only iteration (e.g., deriving source docs). */
  get allItems(): readonly QAItem[] {
    return this.items;
  }

  /** hasEmbeddings is always true for Supabase (pgvector handles it). */
  get hasEmbeddings(): boolean {
    return true;
  }

  /**
   * Load QA metadata from Supabase at startup (no embeddings, no answer in memory).
   * 先用 HEAD + count=exact 取得總筆數，再以受限並行度平行抓分頁——
   * 13 頁循序約 11s，並行後目標壓到 5s 內（envoy route timeout 15s）。
   */
  async load(): Promise<void> {
    const total = await supabaseCount("qa_items", "", LOAD_TIMEOUT_MS);
    const allItems =
      total > 0
        ? await this.loadKnownTotal(total)
        : await this.loadUnknownTotal();

    this.items = allItems;
    this.idIndex = new Map(allItems.map((item) => [item.id, item]));
    this.seqIndex = new Map(allItems.map((item) => [item.seq, item]));
    this._loaded = true;

    console.log(
      `SupabaseQAStore loaded: ${this.items.length} items from Supabase`,
    );
  }

  /** 已知總筆數：直接算出頁數，以 PAGE_CONCURRENCY 並行抓取全部分頁。 */
  private async loadKnownTotal(total: number): Promise<QAItem[]> {
    const pageSize = SupabaseQAStore.PAGE_SIZE;
    const pageCount = Math.ceil(total / pageSize);
    const pages = await mapWithConcurrency(
      Array.from({ length: pageCount }, (_, page) => page),
      SupabaseQAStore.PAGE_CONCURRENCY,
      (page) =>
        supabaseSelect<QARow>(
          "qa_items",
          buildSelectQuery(SELECT_COLUMNS, pageSize, page * pageSize),
          LOAD_TIMEOUT_MS,
        ),
    );
    return pages.flat().map((row) => rowToQAItem(row, ""));
  }

  /**
   * count 查詢失敗（HEAD 400/timeout，total <= 0）時的保守 fallback：
   * 循序探頁直到拿到不足一頁的結果，避免在未知總筆數時平行猜頁數而漏資料。
   */
  private async loadUnknownTotal(): Promise<QAItem[]> {
    const pageSize = SupabaseQAStore.PAGE_SIZE;
    const MAX_PAGES = 100;
    const allItems: QAItem[] = [];

    for (let page = 0; page < MAX_PAGES; page++) {
      const rows = await supabaseSelect<QARow>(
        "qa_items",
        buildSelectQuery(SELECT_COLUMNS, pageSize, page * pageSize),
        LOAD_TIMEOUT_MS,
      );
      if (rows.length === 0) break;
      allItems.push(...rows.map((row) => rowToQAItem(row, "")));
      if (rows.length < pageSize) break;
    }
    return allItems;
  }

  getById(qaId: string): QAItem | undefined {
    return this.idIndex.get(qaId);
  }

  getBySeq(seq: number): QAItem | undefined {
    return this.seqIndex.get(seq);
  }

  /**
   * 批次補撈缺漏的 answer（startup select 省流量拿掉了它）。
   * 已在 memo cache 命中的直接用 cache；未命中的合併成一次 `id=in.(...)` 查詢。
   */
  private async fetchAnswers(
    ids: readonly string[],
  ): Promise<Map<string, string>> {
    const uncached = [...new Set(ids)].filter(
      (id) => !this.answerCache.has(id),
    );
    if (uncached.length > 0) {
      const rows = await supabaseSelect<{ id: string; answer: string }>(
        "qa_items",
        `?select=id,answer&id=in.(${uncached.join(",")})`,
      );
      for (const row of rows) {
        this.answerCache.set(row.id, row.answer ?? "");
      }
    }

    const result = new Map<string, string>();
    for (const id of ids) {
      result.set(id, this.answerCache.get(id) ?? "");
    }
    return result;
  }

  /** 補撈單一 item 的 answer（回傳新物件，不 mutate 內部 store 狀態）。 */
  async hydrateAnswer(item: QAItem): Promise<QAItem> {
    const answers = await this.fetchAnswers([item.id]);
    return { ...item, answer: answers.get(item.id) ?? "" };
  }

  /** 批次補撈一組搜尋結果（{item, score} 包裝）的 answer，用於命中後、回傳前。 */
  async hydrateAnswers<T extends { item: QAItem }>(
    hits: readonly T[],
  ): Promise<T[]> {
    const answers = await this.fetchAnswers(hits.map((hit) => hit.item.id));
    return hits.map((hit) => ({
      ...hit,
      item: { ...hit.item, answer: answers.get(hit.item.id) ?? "" },
    }));
  }

  /** 批次補撈一組 QAItem（不含 score 包裝）的 answer，用於 listQa 分頁結果。 */
  async hydrateItemAnswers(items: readonly QAItem[]): Promise<QAItem[]> {
    const answers = await this.fetchAnswers(items.map((item) => item.id));
    return items.map((item) => ({
      ...item,
      answer: answers.get(item.id) ?? "",
    }));
  }

  /**
   * Hybrid search:
   * 1. pgvector over-retrieve (topK * OVER_RETRIEVE_FACTOR candidates)
   * 2. TypeScript re-rank (keyword boost + synonym + freshness)
   */
  async hybridSearch(
    query: string,
    queryEmbedding: readonly number[] | Float32Array,
    topK: number = 5,
    category: string | null = null,
    minScore: number = 0.2,
  ): Promise<ReadonlyArray<{ item: QAItem; score: number }>> {
    const embedding = Array.from(queryEmbedding);

    const candidates = await supabaseRpc<MatchRow>("match_qa_items", {
      query_embedding: embedding,
      match_count: topK * OVER_RETRIEVE_FACTOR,
      filter_category: category ?? null,
      filter_source_type: null,
      filter_collection: null,
    });

    // Re-rank: keyword boost + synonym + freshness
    const reranked = candidates.map((row) => {
      const kwBoost = computeKeywordBoostSingle(
        query,
        row.keywords ?? [],
        KW_BOOST_CONFIG,
      );
      const synonymBonus = computeSynonymBonus(query, row.synonyms ?? []);
      const item = rowToQAItem(row, row.answer);
      const base =
        row.similarity * SEMANTIC_WEIGHT +
        kwBoost +
        synonymBonus +
        metadataScore(query, item);
      const score = base * (row.freshness_score ?? 1.0);
      return { item, score };
    });

    return rerankResults(
      reranked
        .filter((result) => itemMatchesCategory(result.item, category))
        .sort((a, b) => b.score - a.score),
      topK,
      query,
    ).filter((r) => r.score >= minScore);
  }

  /**
   * Keyword-only search — in-memory on startup-loaded items.
   * No Supabase call needed.
   */
  keywordSearch(
    query: string,
    topK: number = 5,
    category: string | null = null,
  ): ReadonlyArray<{ item: QAItem; score: number }> {
    const queryLower = query.toLowerCase();

    const scored = this.items
      .filter((item) => itemMatchesCategory(item, category))
      .map((item) => {
        const kwBoost = computeKeywordBoostSingle(
          query,
          item.keywords,
          KW_BOOST_CONFIG,
        );
        const synonymBonus = computeSynonymBonus(query, item.synonyms);
        const textMatch =
          item.question.toLowerCase().includes(queryLower) ||
          item.answer.toLowerCase().includes(queryLower)
            ? 0.05
            : 0;
        const score =
          (kwBoost + synonymBonus + textMatch + metadataScore(query, item)) *
          (item.freshness_score ?? 1.0);
        return { item, score };
      })
      .filter((r) => r.score > 0)
      .sort((a, b) => b.score - a.score);

    return rerankResults(scored, topK, query);
  }

  listQa(params: ListQaParams): { items: readonly QAItem[]; total: number } {
    return filterAndPaginateQa(this.items, params);
  }

  categories(): readonly string[] {
    return categoriesFromItems(this.items);
  }

  collections(): ReadonlyArray<{
    source_collection: string;
    source_type: string;
    count: number;
  }> {
    return collectionsFromItems(this.items);
  }

  /**
   * Atomically increment search_hit_count for given QA IDs.
   * Fire-and-forget: errors are logged but never thrown.
   */
  async incrementSearchHitCount(ids: readonly string[]): Promise<void> {
    if (ids.length === 0) return;

    try {
      await supabaseRpc("increment_search_hit_count", {
        qa_ids: ids,
      });
    } catch (err) {
      console.warn("incrementSearchHitCount failed (non-fatal):", err);
    }
  }
}
