/**
 * PgSynonymsStore — 自訂同義詞（app_synonym_custom）。
 *
 * 兩層（同檔案版 SynonymsStore）：
 *   - static：程式碼內 STATIC_SYNONYMS（唯讀）
 *   - custom：app_synonym_custom（warehouse_rag 有 SELECT／INSERT／UPDATE／DELETE；表無 deleted_at，硬刪）
 * 讀取走記憶體快取（load() 時載入），寫入成功後才更新快取。
 */

import { pgQuery } from "./pg-client.js";
import { STATIC_SYNONYMS } from "./synonyms-store.js";
import type { SynonymItem } from "./synonyms-store.js";

interface SynonymRow {
  readonly term: string;
  readonly synonyms: string[];
}

const UPSERT_SQL = `INSERT INTO app_synonym_custom (term, synonyms, updated_at)
  VALUES ($1, $2::text[], now())
  ON CONFLICT (term) DO UPDATE SET synonyms = EXCLUDED.synonyms, updated_at = now()
  RETURNING term, synonyms`;

const UPDATE_SQL = `UPDATE app_synonym_custom SET synonyms = $2::text[], updated_at = now()
  WHERE term = $1 RETURNING term, synonyms`;

const DELETE_SQL = "DELETE FROM app_synonym_custom WHERE term = $1 RETURNING term";

export class PgSynonymsStore {
  private customCache: Map<string, string[]> = new Map();
  private _loaded = false;

  get loaded(): boolean {
    return this._loaded;
  }

  async load(): Promise<void> {
    const rows = await pgQuery<SynonymRow>("SELECT term, synonyms FROM app_synonym_custom ORDER BY term ASC");
    this.customCache = new Map(rows.map((r) => [r.term, [...r.synonyms]]));
    this._loaded = true;
    console.log(`PgSynonymsStore loaded: ${this.customCache.size} custom entries`);
  }

  /** List all synonyms — custom overrides static. Sorted by term. */
  list(): readonly SynonymItem[] {
    const merged = new Map<string, SynonymItem>();
    for (const [term, synonyms] of Object.entries(STATIC_SYNONYMS)) {
      merged.set(term, { term, synonyms, source: "static" });
    }
    for (const [term, synonyms] of this.customCache) {
      merged.set(term, { term, synonyms, source: "custom" });
    }
    return [...merged.values()].sort((a, b) => a.term.localeCompare(b.term, "zh-TW"));
  }

  get(term: string): SynonymItem | undefined {
    const custom = this.customCache.get(term);
    if (custom) return { term, synonyms: custom, source: "custom" };
    if (term in STATIC_SYNONYMS) {
      return {
        term,
        synonyms: STATIC_SYNONYMS[term as keyof typeof STATIC_SYNONYMS]!,
        source: "static",
      };
    }
    return undefined;
  }

  /** 寫入後讀回：快取與回應一律以 RETURNING 的 DB 值為準。 */
  private remember(row: SynonymRow): SynonymItem {
    this.customCache.set(row.term, [...row.synonyms]);
    return { term: row.term, synonyms: [...row.synonyms], source: "custom" };
  }

  /** 新增或覆寫（以 term upsert），與 Supabase 版 merge-duplicates 語意相同。 */
  async create(term: string, synonyms: string[]): Promise<SynonymItem> {
    const rows = await pgQuery<SynonymRow>(UPSERT_SQL, [term, synonyms]);
    return this.remember(rows[0]!);
  }

  /** 更新既有 custom；DB 沒有這列（例如只在 static 層）就改走 upsert 建一筆 custom 覆寫。 */
  async update(term: string, synonyms: string[]): Promise<SynonymItem> {
    const rows = await pgQuery<SynonymRow>(UPDATE_SQL, [term, synonyms]);
    if (rows.length === 0) return this.create(term, synonyms);
    return this.remember(rows[0]!);
  }

  /** 硬刪（表無 deleted_at）；DB 端實際沒刪到列（他處已刪）也回 false 並清快取。 */
  async delete(term: string): Promise<boolean> {
    if (!this.customCache.has(term)) return false;
    const rows = await pgQuery<{ term: string }>(DELETE_SQL, [term]);
    this.customCache.delete(term);
    return rows.length > 0;
  }

  isCustom(term: string): boolean {
    return this.customCache.has(term);
  }

  isStatic(term: string): boolean {
    return term in STATIC_SYNONYMS;
  }

  getCustom(): Readonly<Record<string, string[]>> {
    return Object.fromEntries(this.customCache);
  }
}
