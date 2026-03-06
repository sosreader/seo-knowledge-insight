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
import { filterAndPaginateQa, categoriesFromItems, collectionsFromItems, type ListQaParams } from "./qa-filter.js";
import type { QAItem } from "./qa-store.js";

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
  synonyms: string[];
  freshness_score: number;
  search_hit_count: number;
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
  };
}

function computeSynonymBonus(query: string, synonyms: readonly string[]): number {
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

    for (let page = 0; page < MAX_PAGES; page++) {
      const rows = await supabaseSelect<QARow>(
        "qa_items",
        `?select=id,seq,question,answer,keywords,confidence,category,difficulty,evergreen,source_title,source_date,source_type,source_collection,source_url,is_merged,extraction_model,synonyms,freshness_score,search_hit_count&order=seq.asc&limit=${PAGE_SIZE}&offset=${offset}`,
      );

      if (rows.length === 0) break;
      allItems.push(...rows.map(rowToQAItem));
      if (rows.length < PAGE_SIZE) break;
      offset += PAGE_SIZE;
    }

    this.items = allItems;
    this.idIndex = new Map(allItems.map((item) => [item.id, item]));
    this.seqIndex = new Map(allItems.map((item) => [item.seq, item]));
    this._loaded = true;

    console.log(`SupabaseQAStore loaded: ${this.items.length} items from Supabase`);
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
      const kwBoost = computeKeywordBoostSingle(query, row.keywords ?? [], KW_BOOST_CONFIG);
      const synonymBonus = computeSynonymBonus(query, row.synonyms ?? []);
      const base = row.similarity * SEMANTIC_WEIGHT + kwBoost + synonymBonus;
      const score = base * (row.freshness_score ?? 1.0);
      return { item: rowToQAItem(row), score };
    });

    return reranked
      .sort((a, b) => b.score - a.score)
      .slice(0, topK)
      .filter((r) => r.score >= minScore);
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
      .filter((item) => !category || item.category === category)
      .map((item) => {
        const kwBoost = computeKeywordBoostSingle(query, item.keywords, KW_BOOST_CONFIG);
        const synonymBonus = computeSynonymBonus(query, item.synonyms);
        const textMatch =
          item.question.toLowerCase().includes(queryLower) ||
          item.answer.toLowerCase().includes(queryLower)
            ? 0.05
            : 0;
        const score = (kwBoost + synonymBonus + textMatch) * (item.freshness_score ?? 1.0);
        return { item, score };
      })
      .filter((r) => r.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, topK);

    return scored;
  }

  listQa(params: ListQaParams): { items: readonly QAItem[]; total: number } {
    return filterAndPaginateQa(this.items, params);
  }

  categories(): readonly string[] {
    return categoriesFromItems(this.items);
  }

  collections(): ReadonlyArray<{ source_collection: string; source_type: string; count: number }> {
    return collectionsFromItems(this.items);
  }
}
