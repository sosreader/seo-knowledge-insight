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
 * 不含 primary_category 等 extended retrieval 欄位：live schema（2026-08-19 實測）
 * 沒有這些欄位，選取它們一律 42703 column does not exist；日後補 migration 再加回。
 * answer 仍在選取欄位內——實測含/不含 answer 對冷啟耗時沒有穩定差異（瓶頸是
 * 往返次數與 deep-offset 成本，不是 payload 大小），拿掉它反而讓多個呼叫端的
 * 型別從 sync 變 async，不划算，故保留。
 */
interface QARow {
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
}

const OVER_RETRIEVE_FACTOR = 3;
const KW_BOOST_CONFIG = { boost: 0.1, maxHits: 3, partial: 0.05 } as const;
const SEMANTIC_WEIGHT = 0.7;
const SYNONYM_BOOST = 0.05;

/** startup select 用的欄位；刻意不含 extended retrieval 欄位，理由見 QARow 註解。 */
const SELECT_COLUMNS = [
  "id",
  "seq",
  "question",
  "answer",
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
 * 建構 QAItem。extended retrieval 欄位（primary_category 等）在 live schema
 * 不存在，一律用 category / keywords 推導預設值，不再假裝這些欄位可能存在。
 * row 也接受 MatchRow（RPC 路徑）——MatchRow 是 QARow 的超集，結構相容。
 */
function rowToQAItem(row: QARow): QAItem {
  return {
    id: row.id,
    seq: row.seq,
    question: row.question,
    answer: row.answer,
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
    retrieval_surface_text: [row.question, row.answer, ...(row.keywords ?? [])]
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
  /** PostgREST `db-max-rows` 上限（實測 2026-08-19：limit 超過 1000 會靜默截斷回 1000 筆，不報錯）。 */
  private static readonly PAGE_SIZE = 1000;

  /**
   * 分頁並行度；刻意保守，避免同時打爆 Supabase——併發 6 實測 13 頁裡有 8 頁失敗。
   * 不要調高。
   */
  private static readonly PAGE_CONCURRENCY = 4;

  private items: QAItem[] = [];
  private idIndex: Map<string, QAItem> = new Map();
  private seqIndex: Map<number, QAItem> = new Map();
  private _loaded = false;

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
   * Load QA metadata from Supabase at startup (no embeddings in memory).
   *
   * 先用 supabaseCount（HEAD + count=exact，不傳輸任何 row 資料）取得總筆數，
   * 依總數算出精確頁數再以 PAGE_CONCURRENCY 並行抓取——不能用「這頁筆數 <
   * PAGE_SIZE」當終止條件：PostgREST 的 db-max-rows 上限就是 PAGE_SIZE，
   * 這個訊號在正常結尾與被截斷時長得一模一樣，會靜默漏資料。
   * count 查詢失敗（total <= 0）才退回循序探頁（此時 PAGE_SIZE == db-max-rows
   * 上限，短頁才是可信的結尾訊號，見 loadUnknownTotal 註解）。
   */
  async load(): Promise<void> {
    const total = await supabaseCount("qa_items", "", LOAD_TIMEOUT_MS);
    const allItems =
      total > 0 ? await this.loadKnownTotal(total) : await this.loadUnknownTotal();

    this.items = allItems;
    this.idIndex = new Map(allItems.map((item) => [item.id, item]));
    this.seqIndex = new Map(allItems.map((item) => [item.seq, item]));
    this._loaded = true;

    // 「少載但看起來成功」不能靜默通過：實際筆數對不上宣告總數就要留下訊號。
    if (total > 0 && allItems.length !== total) {
      console.warn(
        `SupabaseQAStore: 載入筆數與宣告總數不符 — 宣告 ${total} 筆，實際載入 ${allItems.length} 筆`,
      );
    }

    console.log(
      `SupabaseQAStore loaded: ${this.items.length} items from Supabase`,
    );
  }

  /** 已知總筆數：直接算出精確頁數，以 PAGE_CONCURRENCY 並行抓取全部分頁。 */
  private async loadKnownTotal(total: number): Promise<QAItem[]> {
    const pageSize = SupabaseQAStore.PAGE_SIZE;
    const pageCount = Math.ceil(total / pageSize);
    const pages = await mapWithConcurrency(
      Array.from({ length: pageCount }, (_, page) => page),
      SupabaseQAStore.PAGE_CONCURRENCY,
      (page) => this.fetchPageWithRetry(page * pageSize),
    );
    return pages.flat().map(rowToQAItem);
  }

  /**
   * count 查詢失敗（HEAD 400/timeout，total <= 0）時的保守 fallback：
   * 循序探頁直到拿到不足一頁的結果。PAGE_SIZE 就是 db-max-rows 上限，
   * 所以「這頁筆數 < PAGE_SIZE」在這裡是可信的結尾訊號（不會被上限截斷混淆）。
   */
  private async loadUnknownTotal(): Promise<QAItem[]> {
    const pageSize = SupabaseQAStore.PAGE_SIZE;
    const MAX_PAGES = 100;
    const allItems: QAItem[] = [];

    for (let page = 0; page < MAX_PAGES; page++) {
      const rows = await this.fetchPageWithRetry(page * pageSize);
      if (rows.length === 0) break;
      allItems.push(...rows.map(rowToQAItem));
      if (rows.length < pageSize) break;
    }
    return allItems;
  }

  /** 抓單一分頁；失敗重試 1 次，重試後仍失敗就往外拋（由 ensureQaStoreLoaded() 接住降級）。 */
  private async fetchPageWithRetry(offset: number): Promise<QARow[]> {
    const pageSize = SupabaseQAStore.PAGE_SIZE;
    const query = buildSelectQuery(SELECT_COLUMNS, pageSize, offset);
    try {
      return await supabaseSelect<QARow>("qa_items", query, LOAD_TIMEOUT_MS);
    } catch (error) {
      console.warn(
        `SupabaseQAStore: 分頁請求失敗（offset=${offset}），重試一次:`,
        error,
      );
      return supabaseSelect<QARow>("qa_items", query, LOAD_TIMEOUT_MS);
    }
  }

  getById(qaId: string): QAItem | undefined {
    return this.idIndex.get(qaId);
  }

  getBySeq(seq: number): QAItem | undefined {
    return this.seqIndex.get(seq);
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
      const item = rowToQAItem(row);
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
