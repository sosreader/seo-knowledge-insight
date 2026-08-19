/**
 * Lazy store 載入 — 「用到才載入」的單一入口。
 *
 * 背景：Lambda cold start 原本 `await` 整個 initStores()，其中 loadQaStore()
 * 會分頁撈完整張 qa_items（2.5 萬筆）。結果連完全用不到 QA 的 route
 * （/reports、/meeting-prep、/pipeline、/sessions 列表）都被擋住而超時。
 *
 * 兩個 ensure 函式都不會往外拋：載入失敗時降級（API 照跑、只是沒有搜尋結果），
 * 並把 memo 清掉讓下一個請求可以重試。
 *
 * 放在 store/ 而非 index.ts，是為了讓 service 層（report-llm、report-generator-local）
 * 可以直接引用，不必反向 import 整個 Hono app 造成循環相依。
 */

import { qaStore, loadQaStore } from "./qa-store.js";

let _qaPromise: Promise<void> | null = null;
let _synonymsPromise: Promise<void> | null = null;

/**
 * 需要 QA 資料時才載入，且整個 process 只成功載入一次。
 * 失敗不拋出：維持「API will run without search」的降級語意。
 */
export function ensureQaStoreLoaded(): Promise<void> {
  if (!_qaPromise) {
    _qaPromise = loadQaStore()
      .then(() => {
        console.log(`QAStore loaded: ${qaStore.count} items`);
      })
      .catch((err) => {
        // 清掉 memo，讓下一個請求可以重試（沿用舊有 _initPromise 的 reset 語意）
        _qaPromise = null;
        console.warn("QAStore load failed (API will run without search):", err);
      });
  }
  return _qaPromise;
}

/**
 * synonyms store 走動態 import：只有 /synonyms 需要它，
 * 靜態引用會把 config／supabase-client 拖進每個只要 QA 的模組的相依圖。
 */
async function _doLoadSynonyms(): Promise<void> {
  const [{ synonymsStore }, { paths }] = await Promise.all([
    import("./synonyms-store.js"),
    import("../config.js"),
  ]);

  if (synonymsStore.load) {
    await synonymsStore.load();
  } else if (synonymsStore.init) {
    synonymsStore.init(paths.synonymCustomJsonPath);
  }
}

/** 需要自訂同義詞時才載入。失敗語意同 ensureQaStoreLoaded()。 */
export function ensureSynonymsLoaded(): Promise<void> {
  if (!_synonymsPromise) {
    _synonymsPromise = _doLoadSynonyms().catch((err) => {
      _synonymsPromise = null;
      console.warn("SynonymsStore load failed:", err);
    });
  }
  return _synonymsPromise;
}

/** 測試用：清空 memo，讓下一次呼叫重新載入。 */
export function _resetStoreInitForTest(): void {
  _qaPromise = null;
  _synonymsPromise = null;
}
