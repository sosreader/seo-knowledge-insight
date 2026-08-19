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

/** 需要 QA 資料的 route 才掛（/qa、/search、/chat、/sessions 的送訊息端點）。 */
export const qaStoreReady: MiddlewareHandler = async (_c, next) => {
  await ensureQaStoreLoaded();
  await next();
};

/** 需要自訂同義詞的 route 才掛（/synonyms）。 */
export const synonymsReady: MiddlewareHandler = async (_c, next) => {
  await ensureSynonymsLoaded();
  await next();
};
