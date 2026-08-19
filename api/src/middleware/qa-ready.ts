/**
 * Store-ready middleware — 只掛在真正需要該 store 的掛載點。
 *
 * 目的：讓 cold start 不再為了用不到的 route 去載入 QA store。
 * 載入失敗時 ensureXxxLoaded() 不會拋出，route 會拿到空的 store 並降級回應。
 */

import type { MiddlewareHandler } from "hono";
import { fail } from "../schemas/api-response.js";
import { qaStore } from "../store/qa-store.js";
import {
  ensureQaStoreLoaded,
  ensureSynonymsLoaded,
  qaStoreLoadFailed,
} from "../store/store-init.js";

/**
 * QA store 等待上限：envoy route timeout 是 15s，冷查詢（一週用 1-4 次，
 * Postgres cache 必冷）比熱查詢慢。逾時後**不冒充成功**——若 store 這時
 * 仍未載入完成，回 503 明確告知使用者，而不是回 200 + 空結果（那是「回
 * 沒有資料」的靜默錯誤資料，跟 db-max-rows 靜默截斷是同一類失敗模式）。
 * 背景載入繼續跑完，下一個請求就是完整結果。
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
 * 無論哪一邊先贏都會 clearTimeout，不留下沒被清掉的 timer。
 */
function waitBounded(promise: Promise<unknown>, timeoutMs: number): Promise<void> {
  let timer: ReturnType<typeof setTimeout>;
  const timeoutPromise = new Promise<void>((resolve) => {
    timer = setTimeout(resolve, timeoutMs);
  });
  return Promise.race([promise.then(() => undefined), timeoutPromise]).finally(
    () => clearTimeout(timer),
  );
}

/**
 * 建構「有界等待 QA store 載入」的 middleware。
 * 抽成 factory（而非直接 export 寫死 QA_STORE_WAIT_TIMEOUT_MS 的版本）是為了讓
 * 測試可以注入小 timeout，不用真的等 12s 才能驗證逾時行為。
 *
 * 等完之後看的是 qaStore.loaded 這個實際狀態，不是「race 有沒有逾時」——
 * 萬一載入剛好在逾時前一瞬完成，就不該回 503。真的還沒好時，依
 * qaStoreLoadFailed() 分辨是「還在載入中」還是「重試後仍失敗」，
 * 訊息不同，方便排查時區分是壞了還是慢。
 */
export function createQaStoreReadyMiddleware(
  timeoutMs: number,
): MiddlewareHandler {
  return async (c, next) => {
    await waitBounded(ensureQaStoreLoaded(), timeoutMs);

    if (!qaStore.loaded) {
      const message = qaStoreLoadFailed()
        ? "知識庫載入失敗，請稍候後重試"
        : "知識庫載入中，請稍候後重試";
      return c.json(fail(message), 503);
    }

    await next();
  };
}

/** 需要 QA 資料的 route 才掛（/qa、/search、/chat、/sessions 的送訊息端點）。 */
export const qaStoreReady: MiddlewareHandler =
  createQaStoreReadyMiddleware(QA_STORE_WAIT_TIMEOUT_MS);

/**
 * 需要自訂同義詞的 route 才掛（/synonyms）。
 * 刻意不套有界等待：synonyms 資料量小、載入快，目前沒觀察到會拖到 envoy
 * timeout 的情況，加上 QA store 一樣的逾時/503 機制只是徒增複雜度。
 * 若日後 synonyms 資料量變大到需要保護，比照 qaStoreReady 的做法即可。
 */
export const synonymsReady: MiddlewareHandler = async (_c, next) => {
  await ensureSynonymsLoaded();
  await next();
};
