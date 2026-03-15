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

import { supabaseRpc, supabaseSelect } from "./supabase-client.js";
import { computeKeywordBoostSingle } from "../utils/keyword-boost.js";
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

/** Row returned by search_qa_items_keyword() RPC. */
type KeywordRow = Omit<MatchRow, "similarity">;

/** DB row (no embedding in TypeScript). */
type QARow = KeywordRow;

const OVER_RETRIEVE_FACTOR = 3;
const KW_BOOST_CONFIG = { boost: 0.1, maxHits: 3, partial: 0.05 } as const;
const SEMANTIC_WEIGHT = 0.7;
const SYNONYM_BOOST = 0.05;
const BASE_SELECT_COLUMNS = [
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
const EXTENDED_SELECT_COLUMNS = [
  ...BASE_SELECT_COLUMNS,
  "primary_category",
  "categories",
  "intent_labels",
  "scenario_tags",
  "serving_tier",
  "retrieval_phrases",
  "retrieval_surface_text",
  "content_granularity",
  "evidence_scope",
  "booster_target_queries",
  "hard_negative_terms",
] as const;

function buildSelectQuery(
  columns: readonly string[],
  pageSize: number,
  offset: number,
): string {
  return `?select=${columns.join(",")}&order=seq.asc&limit=${pageSize}&offset=${offset}`;
}

function isMissingColumnError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  return /column\s+qa_items\.[a-z_]+\s+does not exist/i.test(error.message);
}

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
    primary_category: row.primary_category ?? row.category ?? "",
    categories: row.categories ?? (row.category ? [row.category] : []),
    intent_labels: row.intent_labels ?? [],
    scenario_tags: row.scenario_tags ?? [],
    serving_tier: row.serving_tier ?? "canonical",
    retrieval_phrases: row.retrieval_phrases ?? row.keywords ?? [],
    retrieval_surface_text:
      row.retrieval_surface_text ??
      [row.question, row.answer, ...(row.keywords ?? [])].join("\n"),
    content_granularity: row.content_granularity ?? undefined,
    evidence_scope: row.evidence_scope ?? [],
    booster_target_queries: row.booster_target_queries ?? [],
    hard_negative_terms: row.hard_negative_terms ?? [],
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
   * Uses pagination to handle large datasets.
   */
  async load(): Promise<void> {
    const PAGE_SIZE = 500;
    const MAX_PAGES = 100;
    const allItems: QAItem[] = [];
    let offset = 0;
    let selectColumns: readonly string[] = EXTENDED_SELECT_COLUMNS;

    for (let page = 0; page < MAX_PAGES; page++) {
      let rows: QARow[];
      try {
        rows = await supabaseSelect<QARow>(
          "qa_items",
          buildSelectQuery(selectColumns, PAGE_SIZE, offset),
          LOAD_TIMEOUT_MS,
        );
      } catch (error) {
        if (
          offset === 0 &&
          selectColumns === EXTENDED_SELECT_COLUMNS &&
          isMissingColumnError(error)
        ) {
          console.warn(
            "SupabaseQAStore: qa_items is missing extended retrieval columns; falling back to base schema",
          );
          selectColumns = BASE_SELECT_COLUMNS;
          rows = await supabaseSelect<QARow>(
            "qa_items",
            buildSelectQuery(selectColumns, PAGE_SIZE, offset),
            LOAD_TIMEOUT_MS,
          );
        } else {
          throw error;
        }
      }

      if (rows.length === 0) break;
      allItems.push(...rows.map(rowToQAItem));
      if (rows.length < PAGE_SIZE) break;
      offset += PAGE_SIZE;
    }

    this.items = allItems;
    this.idIndex = new Map(allItems.map((item) => [item.id, item]));
    this.seqIndex = new Map(allItems.map((item) => [item.seq, item]));
    this._loaded = true;

    console.log(
      `SupabaseQAStore loaded: ${this.items.length} items from Supabase`,
    );
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
