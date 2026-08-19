/**
 * Store-ready middleware — 只掛在真正需要該 store 的掛載點。
 *
 * 目的：讓 cold start 不再為了用不到的 route 去載入 QA store。
 * 載入失敗時 ensureXxxLoaded() 不會拋出，route 會拿到空的 store 並降級回應。
 */

import type { MiddlewareHandler } from "hono";
import {
  ensureQaStoreLoaded,
  ensureSynonymsLoaded,
} from "../store/store-init.js";

/**
 * QA store 等待上限：envoy route timeout 是 15s，冷查詢（一週用 1-4 次，
 * Postgres cache 必冷）比熱查詢慢，與其讓使用者拿到 504，不如逾時後先讓
 * route 用目前狀態（可能是空的）回應，背景載入繼續跑完，下一個請求就完整。
 */
export const QA_STORE_WAIT_TIMEOUT_MS = 12_000;

/** 純粹計時用的 no-op promise。 */
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * 有界等待：await 到 promise resolve 或逾時，取先發生者。
 * Promise.race 不會取消、也不會重置 promise 本身——逾時只是這次不等它，
 * 原本的 promise（含它背後的任何 memo 狀態）在背景繼續跑到完成。
 */
function waitBounded(promise: Promise<unknown>, timeoutMs: number): Promise<void> {
  return Promise.race([promise.then(() => undefined), delay(timeoutMs)]);
}

/**
 * 建構「有界等待 QA store 載入」的 middleware。
 * 抽成 factory（而非直接 export 寫死 QA_STORE_WAIT_TIMEOUT_MS 的版本）是為了讓
 * 測試可以注入小 timeout，不用真的等 12s 才能驗證逾時行為。
 */
export function createQaStoreReadyMiddleware(
  timeoutMs: number,
): MiddlewareHandler {
  return async (_c, next) => {
    await waitBounded(ensureQaStoreLoaded(), timeoutMs);
    await next();
  };
}

/** 需要 QA 資料的 route 才掛（/qa、/search、/chat、/sessions 的送訊息端點）。 */
export const qaStoreReady: MiddlewareHandler =
  createQaStoreReadyMiddleware(QA_STORE_WAIT_TIMEOUT_MS);

/** 需要自訂同義詞的 route 才掛（/synonyms）。 */
export const synonymsReady: MiddlewareHandler = async (_c, next) => {
  await ensureSynonymsLoaded();
  await next();
};
