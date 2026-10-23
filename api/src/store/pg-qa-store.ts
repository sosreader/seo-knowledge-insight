/**
 * PgQAStore — vocus-warehouse（app_qa_item、match_qa_items）版的 QA store。
 *
 * 策略與 Supabase 版相同：
 *   - 啟動時一次 SELECT 全部 QA metadata（不含 embedding）進記憶體
 *   - hybridSearch：match_qa_items 向量 over-retrieve → 記憶體內 keyword／synonym／freshness 重排
 *   - keywordSearch、listQa、categories、collections、getById、getBySeq：記憶體內（同步）
 *
 * 與 Supabase 版的差異：
 *   - 直連 PG，不受 PostgREST db-max-rows 1000 限制，啟動載入改單一查詢（statement_timeout 放寬到 25s）。
 *   - match_qa_items 以 SQL 呼叫：`SELECT ... FROM match_qa_items($1::vector, LEAST($2, 200), $3, NULL, NULL)`。
 *     函式是 LANGUAGE sql 可 inline，排序表達式與 S1.7 的 halfvec hnsw index 一致。
 *   - app_qa_item 沒有 deleted_at（0011：live 無此欄），所以這裡的 SELECT 不需要軟刪除條件。
 */

import { pgQuery } from "./pg-client.js";
import { computeKeywordBoostSingle } from "../utils/keyword-boost.js";
import {
  filterAndPaginateQa,
  categoriesFromItems,
  collectionsFromItems,
  type ListQaParams,
} from "./qa-filter.js";
import type { QAItem } from "./qa-store.js";
import {
  KW_BOOST_CONFIG,
  OVER_RETRIEVE_FACTOR,
  SELECT_COLUMNS,
  SEMANTIC_WEIGHT,
  computeSynonymBonus,
  itemMatchesCategory,
  metadataScore,
  rerankResults,
  rowToQAItem,
  type MatchRow,
  type QARow,
} from "./qa-rerank.js";

/** 啟動全量載入的 statement_timeout（約 3.2 萬列、不含 embedding）。 */
const LOAD_TIMEOUT_MS = 25_000;
/** match_qa_items 與 increment_search_hit_count 在 DB 端的上限（0011）。 */
export const MAX_MATCH_COUNT = 200;
export const MAX_HIT_IDS = 200;

const LOAD_SQL = `SELECT ${SELECT_COLUMNS.join(", ")} FROM app_qa_item ORDER BY seq ASC NULLS LAST, id ASC`;

/**
 * 回傳欄位就是函式的 RETURNS TABLE（與 Supabase RPC 相同）：沒有 maturity_relevance 等欄，
 * 所以 hybrid 命中的 maturity_relevance 為 undefined——與 Supabase 時期行為一致，刻意不在這裡補。
 */
export const MATCH_SQL = `SELECT * FROM match_qa_items($1::vector, LEAST($2::int, ${MAX_MATCH_COUNT}), $3::text, NULL, NULL)`;

/** pgvector 的文字格式：'[0.1,0.2,...]'；拒絕 NaN／Infinity（pgvector 也會拒絕，先擋下給清楚錯誤）。 */
export function toVectorLiteral(values: readonly number[] | Float32Array): string {
  const arr = Array.from(values);
  if (arr.length === 0 || arr.some((v) => !Number.isFinite(v))) {
    throw new Error("query embedding must be a non-empty finite vector");
  }
  return `[${arr.join(",")}]`;
}

/** 去重、去空字串，截到 DB 上限（超過 200 個 increment_search_hit_count 會 RAISE）。 */
export function normalizeHitIds(ids: readonly string[]): string[] {
  return [...new Set(ids.filter(Boolean))].slice(0, MAX_HIT_IDS);
}

export class PgQAStore {
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

  /** 向量在 DB 端（pgvector），永遠可走 hybrid。 */
  get hasEmbeddings(): boolean {
    return true;
  }

  /** 啟動時載入全部 QA metadata；失敗往外拋，由 ensureQaStoreLoaded() 降級並允許重試。 */
  async load(): Promise<void> {
    const rows = await pgQuery<QARow>(LOAD_SQL, [], { timeoutMs: LOAD_TIMEOUT_MS });
    const allItems = rows.map(rowToQAItem);
    this.items = allItems;
    this.idIndex = new Map(allItems.map((item) => [item.id, item]));
    this.seqIndex = new Map(allItems.map((item) => [item.seq, item]));
    this._loaded = true;
    console.log(`PgQAStore loaded: ${this.items.length} items from vocus-warehouse`);
  }

  getById(qaId: string): QAItem | undefined {
    return this.idIndex.get(qaId);
  }

  getBySeq(seq: number): QAItem | undefined {
    return this.seqIndex.get(seq);
  }

  /**
   * Hybrid search:
   * 1. pgvector over-retrieve (topK * OVER_RETRIEVE_FACTOR candidates, DB 端上限 200)
   * 2. TypeScript re-rank (keyword boost + synonym + freshness)
   */
  async hybridSearch(
    query: string,
    queryEmbedding: readonly number[] | Float32Array,
    topK: number = 5,
    category: string | null = null,
    minScore: number = 0.2,
  ): Promise<ReadonlyArray<{ item: QAItem; score: number }>> {
    const candidates = await pgQuery<MatchRow>(MATCH_SQL, [
      toVectorLiteral(queryEmbedding),
      Math.max(1, Math.trunc(topK * OVER_RETRIEVE_FACTOR)),
      category ?? null,
    ]);

    const reranked = candidates.map((row) => {
      const kwBoost = computeKeywordBoostSingle(query, row.keywords ?? [], KW_BOOST_CONFIG);
      const synonymBonus = computeSynonymBonus(query, row.synonyms ?? []);
      const item = rowToQAItem(row);
      const base = row.similarity * SEMANTIC_WEIGHT + kwBoost + synonymBonus + metadataScore(query, item);
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

  /** Keyword-only search — in-memory on startup-loaded items. */
  keywordSearch(
    query: string,
    topK: number = 5,
    category: string | null = null,
  ): ReadonlyArray<{ item: QAItem; score: number }> {
    const queryLower = query.toLowerCase();

    const scored = this.items
      .filter((item) => itemMatchesCategory(item, category))
      .map((item) => {
        const kwBoost = computeKeywordBoostSingle(query, item.keywords, KW_BOOST_CONFIG);
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
   * search_hit_count +1（DB 函式 increment_search_hit_count，warehouse_rag 只有這兩欄的欄級 UPDATE）。
   * Fire-and-forget：錯誤只記 log，不往外拋。
   */
  async incrementSearchHitCount(ids: readonly string[]): Promise<void> {
    const qaIds = normalizeHitIds(ids);
    if (qaIds.length === 0) return;
    try {
      await pgQuery("SELECT increment_search_hit_count($1::text[])", [qaIds]);
    } catch (err) {
      console.warn("incrementSearchHitCount failed (non-fatal):", err);
    }
  }
}
