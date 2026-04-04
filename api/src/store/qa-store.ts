/**
 * QAStore — loads qa_final.json + qa_embeddings.npy into memory.
 *
 * Provides:
 *   - search (semantic only)
 *   - hybridSearch (semantic + keyword boost + synonym + freshness)
 *   - listQa (filtered listing with pagination)
 *   - getById (O(1) lookup)
 *   - categories (sorted by count desc)
 */

import { readFileSync, existsSync, statSync } from "node:fs";
import { createHash } from "node:crypto";
import { paths } from "../config.js";
import { parseNpy } from "../utils/npy-reader.js";
import {
  normalizeRows,
  normalizeL2,
  matrixDotVector,
} from "../utils/cosine-similarity.js";
import {
  SearchEngine,
  type QADict,
  type SearchResult,
} from "./search-engine.js";
import { type ListQaParams } from "./qa-filter.js";
import {
  createStoreData,
  getById as getByIdFn,
  getBySeq as getBySeqFn,
  listQa as listQaFn,
  categories as categoriesFn,
  collections as collectionsFn,
  type QAStoreData,
} from "./qa-fns.js";
import { hasSupabase } from "./supabase-client.js";
import { SupabaseQAStore } from "./supabase-qa-store.js";

function shouldLoadEnrichedJson(
  jsonPath: string,
  enrichedPath: string,
): boolean {
  if (!existsSync(enrichedPath)) {
    return false;
  }

  if (!existsSync(jsonPath)) {
    console.warn(
      `QAStore: qa_final.json not found at ${jsonPath}, trying qa_enriched.json`,
    );
    return true;
  }

  try {
    const finalMtime = statSync(jsonPath).mtimeMs;
    const enrichedMtime = statSync(enrichedPath).mtimeMs;
    if (finalMtime > enrichedMtime) {
      console.warn(
        "QAStore: qa_enriched.json is stale, fallback to qa_final.json",
      );
      return false;
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.warn(
      `QAStore: qa_enriched.json freshness check failed (${message}), trying enriched artifact`,
    );
  }

  return true;
}

export interface QAItem {
  readonly id: string; // stable_id (16-char hex)
  readonly seq: number; // sequential number for display
  readonly question: string;
  readonly answer: string;
  readonly keywords: readonly string[];
  readonly confidence: number;
  readonly category: string;
  readonly difficulty: string;
  readonly evergreen: boolean;
  readonly source_title: string;
  readonly source_date: string;
  readonly is_merged: boolean;
  readonly synonyms: readonly string[];
  readonly freshness_score: number;
  readonly search_hit_count: number;
  readonly notion_url: string;
  readonly source_type: string; // "meeting" | "article" | "paper" | "transcript"
  readonly source_collection: string; // "seo-meetings" | "genehong-medium" | "ithelp-sc-kpi"
  readonly source_url: string; // canonical URL to original content
  readonly extraction_model?: string; // model used to extract this QA
  readonly maturity_relevance?: "L1" | "L2" | "L3" | "L4"; // SEO maturity level
  readonly primary_category?: string;
  readonly categories?: readonly string[];
  readonly intent_labels?: readonly string[];
  readonly scenario_tags?: readonly string[];
  readonly serving_tier?: string;
  readonly retrieval_phrases?: readonly string[];
  readonly retrieval_surface_text?: string;
  readonly content_granularity?: string;
  readonly evidence_scope?: readonly string[];
  readonly booster_target_queries?: readonly string[];
  readonly hard_negative_terms?: readonly string[];
}

interface RawQAData {
  qa_database: Array<{
    id: number;
    stable_id?: string;
    question: string;
    answer: string;
    keywords?: string[];
    confidence?: number;
    category?: string;
    difficulty?: string;
    evergreen?: boolean;
    source_title?: string;
    source_date?: string;
    is_merged?: boolean;
    source_type?: string;
    source_collection?: string;
    source_url?: string;
    extraction_model?: string;
    maturity_relevance?: string;
    primary_category?: string;
    categories?: string[];
    intent_labels?: string[];
    scenario_tags?: string[];
    serving_tier?: string;
    retrieval_phrases?: string[];
    retrieval_surface_text?: string;
    content_granularity?: string;
    evidence_scope?: string[];
    booster_target_queries?: string[];
    hard_negative_terms?: string[];
    _enrichment?: {
      synonyms?: string[];
      freshness_score?: number;
      search_hit_count?: number;
      notion_url?: string;
      source_url?: string;
      maturity_relevance?: string;
    };
  }>;
}

/**
 * Deterministic ID from content — matches Python's compute_stable_id().
 * Formula: sha256(f"{source_title}::{question[:120]}")[:16]
 */
function computeStableId(sourceTitle: string, question: string): string {
  const content = `${sourceTitle}::${question.slice(0, 120)}`;
  return createHash("sha256").update(content).digest("hex").slice(0, 16);
}

export class QAStore {
  private data: QAStoreData = createStoreData([]);
  private qaDicts: readonly QADict[] = [];
  private embNorm: Float32Array = new Float32Array(0); // flat [N x dim], L2-normalized
  private embDim: number = 1536;
  private engine: SearchEngine | null = null;

  get loaded(): boolean {
    return this.data.items.length > 0;
  }

  get count(): number {
    return this.data.items.length;
  }

  /** Expose items for read-only iteration (e.g., deriving source docs). */
  get allItems(): readonly QAItem[] {
    return this.data.items;
  }

  load(
    jsonPath: string = paths.qaJsonPath,
    npyPath: string = paths.qaEmbeddingsPath,
    enrichedPath: string = paths.qaEnrichedJsonPath,
  ): void {
    // Prefer enriched JSON only when it is not older than qa_final.json.
    let rawText: string;
    if (shouldLoadEnrichedJson(jsonPath, enrichedPath)) {
      try {
        rawText = readFileSync(enrichedPath, "utf-8");
        console.log(`QAStore: loaded enriched data from ${enrichedPath}`);
      } catch (error) {
        console.warn(
          "QAStore: qa_enriched.json load failed, fallback to qa_final.json",
        );
        if (!existsSync(jsonPath)) {
          const message =
            error instanceof Error ? error.message : String(error);
          throw new Error(
            `QAStore: both qa_enriched.json and qa_final.json are unavailable (${message})`,
          );
        }
        rawText = readFileSync(jsonPath, "utf-8");
      }
    } else {
      rawText = readFileSync(jsonPath, "utf-8");
    }

    const data: RawQAData = JSON.parse(rawText);
    const rawItems = data.qa_database;

    const parsedItems: QAItem[] = rawItems.map((qa) => ({
      id: qa.stable_id ?? computeStableId(qa.source_title ?? "", qa.question),
      seq: qa.id,
      question: qa.question,
      answer: qa.answer,
      keywords: qa.keywords ?? [],
      confidence: qa.confidence ?? 0,
      category: qa.category ?? "",
      difficulty: qa.difficulty ?? "",
      evergreen: qa.evergreen ?? false,
      source_title: qa.source_title ?? "",
      source_date: qa.source_date ?? "",
      is_merged: qa.is_merged ?? false,
      synonyms: qa._enrichment?.synonyms ?? [],
      freshness_score: qa._enrichment?.freshness_score ?? 1.0,
      search_hit_count: qa._enrichment?.search_hit_count ?? 0,
      notion_url: qa._enrichment?.notion_url ?? "",
      source_type: qa.source_type ?? "meeting",
      source_collection: qa.source_collection ?? "seo-meetings",
      source_url:
        qa.source_url ??
        qa._enrichment?.source_url ??
        qa._enrichment?.notion_url ??
        "",
      extraction_model: qa.extraction_model,
      maturity_relevance: (qa.maturity_relevance ??
        qa._enrichment?.maturity_relevance) as
        | "L1"
        | "L2"
        | "L3"
        | "L4"
        | undefined,
      primary_category: qa.primary_category ?? qa.category ?? "",
      categories: qa.categories ?? (qa.category ? [qa.category] : []),
      intent_labels: qa.intent_labels ?? [],
      scenario_tags: qa.scenario_tags ?? [],
      serving_tier: qa.serving_tier ?? "canonical",
      retrieval_phrases: qa.retrieval_phrases ?? [],
      retrieval_surface_text:
        qa.retrieval_surface_text ??
        [qa.question, qa.answer, ...(qa.keywords ?? [])].join("\n"),
      content_granularity: qa.content_granularity,
      evidence_scope: qa.evidence_scope ?? [],
      booster_target_queries: qa.booster_target_queries ?? [],
      hard_negative_terms: qa.hard_negative_terms ?? [],
    }));

    // Build store data (items + indexes) via pure function
    this.data = createStoreData(parsedItems);

    // Build QADicts for SearchEngine (needed for both hybrid and keyword-only)
    const qaDicts: QADict[] = rawItems.map((qa) => ({
      id: qa.stable_id ?? computeStableId(qa.source_title ?? "", qa.question),
      question: qa.question,
      answer: qa.answer,
      keywords: qa.keywords ?? [],
      category: qa.category ?? "",
      primary_category: qa.primary_category ?? qa.category ?? "",
      categories: qa.categories ?? (qa.category ? [qa.category] : []),
      intent_labels: qa.intent_labels ?? [],
      scenario_tags: qa.scenario_tags ?? [],
      serving_tier: qa.serving_tier ?? "canonical",
      retrieval_phrases: qa.retrieval_phrases ?? [],
      retrieval_surface_text:
        qa.retrieval_surface_text ??
        [qa.question, qa.answer, ...(qa.keywords ?? [])].join("\n"),
      booster_target_queries: qa.booster_target_queries ?? [],
      hard_negative_terms: qa.hard_negative_terms ?? [],
      _enrichment: qa._enrichment
        ? {
            synonyms: qa._enrichment.synonyms,
            freshness_score: qa._enrichment.freshness_score,
          }
        : undefined,
    }));
    this.qaDicts = qaDicts;

    // Load embeddings (optional — keyword-only mode when npy not found)
    if (existsSync(npyPath)) {
      const npyBuf = readFileSync(npyPath);
      const npy = parseNpy(npyBuf);
      this.embDim = npy.shape[1];

      // L2-normalize rows
      this.embNorm = normalizeRows(npy.data, npy.shape[0], npy.shape[1]);

      console.log(
        `QAStore loaded: ${this.data.items.length} items, embeddings shape [${npy.shape[0]}, ${npy.shape[1]}]`,
      );

      // Initialize hybrid search engine
      if (this.data.items.length === npy.shape[0]) {
        this.engine = new SearchEngine(qaDicts, npy.data, this.embDim);
      } else {
        console.warn(
          `SearchEngine not initialized: items (${this.data.items.length}) != embeddings (${npy.shape[0]})`,
        );
        this.engine = null;
      }
    } else {
      console.warn("QAStore: embeddings not found, keyword-only mode");
      this.engine = null;
    }
  }

  getById(qaId: string): QAItem | undefined {
    return getByIdFn(this.data, qaId);
  }

  getBySeq(seq: number): QAItem | undefined {
    return getBySeqFn(this.data, seq);
  }

  /**
   * Pure semantic search (dot product with normalized embeddings).
   */
  search(
    queryEmbedding: readonly number[] | Float32Array,
    topK: number = 5,
    category: string | null = null,
  ): ReadonlyArray<{ item: QAItem; score: number }> {
    const qVec =
      queryEmbedding instanceof Float32Array
        ? queryEmbedding
        : new Float32Array(queryEmbedding);

    const qNorm = normalizeL2(qVec);
    const scores = matrixDotVector(
      this.embNorm,
      qNorm,
      this.data.items.length,
      this.embDim,
    );

    // Apply category mask
    if (category) {
      for (let i = 0; i < this.data.items.length; i++) {
        if (this.data.items[i]!.category !== category) {
          scores[i] = -1;
        }
      }
    }

    // Sort and take top-K
    const indexed: Array<{ idx: number; score: number }> = [];
    for (let i = 0; i < scores.length; i++) {
      if (scores[i]! > 0) {
        indexed.push({ idx: i, score: scores[i]! });
      }
    }
    indexed.sort((a, b) => b.score - a.score);

    return indexed.slice(0, topK).map(({ idx, score }) => ({
      item: this.data.items[idx]!,
      score,
    }));
  }

  /**
   * Hybrid search (semantic + keyword boost + synonym + freshness).
   * Returns a Promise for interface compatibility with SupabaseQAStore.
   */
  async hybridSearch(
    query: string,
    queryEmbedding: readonly number[] | Float32Array,
    topK: number = 5,
    category: string | null = null,
    minScore: number = 0.2,
  ): Promise<ReadonlyArray<{ item: QAItem; score: number }>> {
    if (!this.engine) {
      console.warn(
        "hybridSearch: SearchEngine not initialized, fallback to search()",
      );
      return this.search(queryEmbedding, topK, category);
    }

    const qVec =
      queryEmbedding instanceof Float32Array
        ? queryEmbedding
        : new Float32Array(queryEmbedding);

    const results: SearchResult[] = [
      ...this.engine.search(query, qVec, topK, category, minScore),
    ];

    // Map QADict back to QAItem
    return results
      .map(({ qa, score }) => {
        const item = this.data.idIndex.get(qa.id);
        return item ? { item, score } : null;
      })
      .filter((r): r is { item: QAItem; score: number } => r !== null);
  }

  /**
   * Keyword-only search (no embedding required).
   * Uses SearchEngine.keywordOnlySearch when available, otherwise basic substring.
   */
  keywordSearch(
    query: string,
    topK: number = 5,
    category: string | null = null,
  ): ReadonlyArray<{ item: QAItem; score: number }> {
    if (this.engine) {
      return this.engine
        .keywordOnlySearch(query, topK, category)
        .map(({ qa, score }) => {
          const item = this.data.idIndex.get(qa.id);
          return item ? { item, score } : null;
        })
        .filter((r): r is { item: QAItem; score: number } => r !== null);
    }

    // Fallback: basic substring matching
    return this.listQa({ keyword: query, limit: topK }).items.map((item) => ({
      item,
      score: 1.0,
    }));
  }

  /**
   * Whether hybrid search (semantic + keyword) is available.
   */
  get hasEmbeddings(): boolean {
    return this.embNorm.length > 0 && this.engine !== null;
  }

  listQa(params: ListQaParams): { items: readonly QAItem[]; total: number } {
    return listQaFn(this.data, params);
  }

  categories(): readonly string[] {
    return categoriesFn(this.data);
  }

  collections(): ReadonlyArray<{
    source_collection: string;
    source_type: string;
    count: number;
  }> {
    return collectionsFn(this.data);
  }
}

// Module-level singleton — use Supabase backend when configured, file-based otherwise
export const qaStore: QAStore | SupabaseQAStore = hasSupabase()
  ? new SupabaseQAStore()
  : new QAStore();

/**
 * Initialise the qa store.
 * - Supabase mode: async load from Supabase (no .npy needed)
 * - File mode: sync load from qa_final.json + qa_embeddings.npy
 */
export async function loadQaStore(): Promise<void> {
  if (qaStore instanceof SupabaseQAStore) {
    await qaStore.load();
  } else {
    qaStore.load();
  }
}
