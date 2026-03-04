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

import { readFileSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { paths } from "../config.js";
import { parseNpy } from "../utils/npy-reader.js";
import { normalizeRows, normalizeL2, matrixDotVector } from "../utils/cosine-similarity.js";
import { SearchEngine, type QADict, type SearchResult } from "./search-engine.js";

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
    _enrichment?: {
      synonyms?: string[];
      freshness_score?: number;
      search_hit_count?: number;
      notion_url?: string;
      source_url?: string;
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
  private items: readonly QAItem[] = [];
  private qaDicts: readonly QADict[] = [];
  private embNorm: Float32Array = new Float32Array(0); // flat [N x dim], L2-normalized
  private embDim: number = 1536;
  private idIndex: Map<string, QAItem> = new Map();
  private engine: SearchEngine | null = null;

  get loaded(): boolean {
    return this.items.length > 0;
  }

  get count(): number {
    return this.items.length;
  }

  load(
    jsonPath: string = paths.qaJsonPath,
    npyPath: string = paths.qaEmbeddingsPath,
    enrichedPath: string = paths.qaEnrichedJsonPath,
  ): void {
    // Prefer enriched JSON, fallback to final
    let rawText: string;
    if (existsSync(enrichedPath)) {
      try {
        rawText = readFileSync(enrichedPath, "utf-8");
        console.log(`QAStore: loaded enriched data from ${enrichedPath}`);
      } catch {
        console.warn("QAStore: qa_enriched.json load failed, fallback to qa_final.json");
        rawText = readFileSync(jsonPath, "utf-8");
      }
    } else {
      rawText = readFileSync(jsonPath, "utf-8");
    }

    const data: RawQAData = JSON.parse(rawText);
    const rawItems = data.qa_database;

    this.items = rawItems.map((qa) => ({
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
      source_url: qa.source_url ?? qa._enrichment?.source_url ?? qa._enrichment?.notion_url ?? "",
    }));

    // Build ID index
    this.idIndex = new Map(this.items.map((item) => [item.id, item]));

    // Build QADicts for SearchEngine (needed for both hybrid and keyword-only)
    const qaDicts: QADict[] = rawItems.map((qa) => ({
      id: qa.stable_id ?? computeStableId(qa.source_title ?? "", qa.question),
      question: qa.question,
      answer: qa.answer,
      keywords: qa.keywords ?? [],
      category: qa.category ?? "",
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
        `QAStore loaded: ${this.items.length} items, embeddings shape [${npy.shape[0]}, ${npy.shape[1]}]`,
      );

      // Initialize hybrid search engine
      if (this.items.length === npy.shape[0]) {
        this.engine = new SearchEngine(qaDicts, npy.data, this.embDim);
      } else {
        console.warn(
          `SearchEngine not initialized: items (${this.items.length}) != embeddings (${npy.shape[0]})`,
        );
        this.engine = null;
      }
    } else {
      console.warn("QAStore: embeddings not found, keyword-only mode");
      this.engine = null;
    }
  }

  getById(qaId: string): QAItem | undefined {
    return this.idIndex.get(qaId);
  }

  getBySeq(seq: number): QAItem | undefined {
    return this.items.find((item) => item.seq === seq);
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
    const scores = matrixDotVector(this.embNorm, qNorm, this.items.length, this.embDim);

    // Apply category mask
    if (category) {
      for (let i = 0; i < this.items.length; i++) {
        if (this.items[i]!.category !== category) {
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
      item: this.items[idx]!,
      score,
    }));
  }

  /**
   * Hybrid search (semantic + keyword boost + synonym + freshness).
   */
  hybridSearch(
    query: string,
    queryEmbedding: readonly number[] | Float32Array,
    topK: number = 5,
    category: string | null = null,
    minScore: number = 0.2,
  ): ReadonlyArray<{ item: QAItem; score: number }> {
    if (!this.engine) {
      console.warn("hybridSearch: SearchEngine not initialized, fallback to search()");
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
        const item = this.idIndex.get(qa.id);
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
          const item = this.idIndex.get(qa.id);
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

  /**
   * Filtered listing with pagination.
   */
  listQa(params: {
    category?: string | null;
    keyword?: string | null;
    difficulty?: string | null;
    evergreen?: boolean | null;
    source_type?: string | null;
    source_collection?: string | null;
    sort_by?: string | null;
    sort_order?: string | null;
    limit?: number;
    offset?: number;
  }): { items: readonly QAItem[]; total: number } {
    const { category, keyword, difficulty, evergreen, source_type, source_collection, sort_by, sort_order, limit = 20, offset = 0 } = params;

    let results: readonly QAItem[] = this.items;

    if (category) {
      const cats = category.includes(",") ? category.split(",") : [category];
      const catSet = new Set(cats);
      results = results.filter((i) => catSet.has(i.category));
    }
    if (keyword) {
      const kwLower = keyword.toLowerCase();
      results = results.filter(
        (i) =>
          i.question.toLowerCase().includes(kwLower) ||
          i.answer.toLowerCase().includes(kwLower) ||
          i.keywords.some((k) => k.toLowerCase().includes(kwLower)),
      );
    }
    if (difficulty) {
      const diffs = difficulty.includes(",") ? difficulty.split(",") : [difficulty];
      const diffSet = new Set(diffs);
      results = results.filter((i) => diffSet.has(i.difficulty));
    }
    if (evergreen !== null && evergreen !== undefined) {
      results = results.filter((i) => i.evergreen === evergreen);
    }
    if (source_type) {
      results = results.filter((i) => i.source_type === source_type);
    }
    if (source_collection) {
      results = results.filter((i) => i.source_collection === source_collection);
    }

    // Sort if requested
    if (sort_by === "source_date") {
      const dir = sort_order === "asc" ? 1 : -1;
      const sorted = [...results];
      sorted.sort((a, b) => dir * a.source_date.localeCompare(b.source_date));
      results = sorted;
    } else if (sort_by === "confidence") {
      const dir = sort_order === "asc" ? 1 : -1;
      const sorted = [...results];
      sorted.sort((a, b) => dir * (a.confidence - b.confidence));
      results = sorted;
    }

    const total = results.length;
    return {
      items: results.slice(offset, offset + limit),
      total,
    };
  }

  /**
   * Categories sorted by count descending.
   */
  categories(): readonly string[] {
    const counts = new Map<string, number>();
    for (const item of this.items) {
      counts.set(item.category, (counts.get(item.category) ?? 0) + 1);
    }
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([cat]) => cat);
  }

  /**
   * Collections with counts, grouped by source_type.
   */
  collections(): ReadonlyArray<{
    source_collection: string;
    source_type: string;
    count: number;
  }> {
    const counts = new Map<string, { source_type: string; count: number }>();
    for (const item of this.items) {
      const existing = counts.get(item.source_collection);
      if (existing) {
        counts.set(item.source_collection, {
          source_type: existing.source_type,
          count: existing.count + 1,
        });
      } else {
        counts.set(item.source_collection, {
          source_type: item.source_type,
          count: 1,
        });
      }
    }
    return [...counts.entries()]
      .sort((a, b) => b[1].count - a[1].count)
      .map(([collection, { source_type, count }]) => ({
        source_collection: collection,
        source_type,
        count,
      }));
  }
}

// Module-level singleton
export const qaStore = new QAStore();
