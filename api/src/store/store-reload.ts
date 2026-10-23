/**
 * 把 PG 模式的 QA store 與 synonyms store 一起重載，彙整成單一結果給 store-reloader 記 log。
 *
 * 兩個 store 各自保證「失敗保舊、成功整組換入」，所以其中一個失敗不影響另一個：
 * 這裡兩個都會跑，任一失敗整體回 ok:false（帶第一個失敗的固定代碼與失敗的 store 名）。
 * 依序執行而非並行，避免同時佔用連線池。
 */

import type { ReloadResult } from "../services/store-reloader.js";
import { qaStore } from "./qa-store.js";
import { PgQAStore } from "./pg-qa-store.js";
// synonyms-store 與 pg-synonyms-store 互相引用：必須先載入 synonyms-store，
// 否則 pg-synonyms-store 先求值時 PgSynonymsStore 還沒定義，createSynonymsStore() 會失敗。
import { synonymsStore } from "./synonyms-store.js";
import { PgSynonymsStore } from "./pg-synonyms-store.js";
import type { StoreReloadResult } from "./store-errors.js";

export interface Reloadable {
  reload(): Promise<StoreReloadResult>;
}

export interface ReloadTargets {
  readonly qa: Reloadable;
  readonly synonyms: Reloadable;
}

export async function reloadStores(targets: ReloadTargets): Promise<ReloadResult> {
  const qa = await targets.qa.reload();
  const synonyms = await targets.synonyms.reload();

  const failed: Array<{ name: string; code: string }> = [];
  if (!qa.ok) failed.push({ name: "qa_items", code: qa.code });
  if (!synonyms.ok) failed.push({ name: "synonyms", code: synonyms.code });

  if (failed.length > 0) {
    return { ok: false, code: failed[0]!.code, failed: failed.map((f) => f.name) };
  }
  return {
    ok: true,
    qa_items: qa.ok ? qa.count : 0,
    synonyms: synonyms.ok ? synonyms.count : 0,
  };
}

/** PG 模式的單例重載入口；檔案模式的 store 沒有 reload，回傳固定代碼 not_pg_mode。 */
export async function reloadPgStores(): Promise<ReloadResult> {
  if (!(qaStore instanceof PgQAStore) || !(synonymsStore instanceof PgSynonymsStore)) {
    return { ok: false, code: "not_pg_mode", failed: [] };
  }
  return reloadStores({ qa: qaStore, synonyms: synonymsStore });
}
