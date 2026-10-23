import type { Context, ErrorHandler } from "hono";
import { fail } from "../schemas/api-response.js";
import { storeErrorResponse } from "../store/store-errors.js";
import { featureUnavailableBody, isFeatureUnavailableError } from "../utils/feature-errors.js";

/**
 * store 層錯誤（DB 不可用 503、逾時 504、rag-api 不提供 410）→ 對應狀態碼與固定代碼；
 * 其他錯誤回 null，由呼叫端決定。訊息只有代碼，不帶 DB 細節。
 */
export function storeFailure(c: Context, err: unknown): Response | null {
  const mapped = storeErrorResponse(err);
  return mapped ? c.json(fail(mapped.code), mapped.status) : null;
}

export const errorHandler: ErrorHandler = (err, c) => {
  // llm_disabled／run_locally：功能在此部署不提供（501），不是錯誤
  if (isFeatureUnavailableError(err)) {
    return c.json(featureUnavailableBody(err.code), err.status);
  }

  const mapped = storeFailure(c, err);
  if (mapped) {
    console.warn(`Store error: ${err.message}`);
    return mapped;
  }

  console.error(`Unhandled error: ${err.message}`, err.stack?.split("\n").slice(0, 5).join("\n"));

  // Do not leak stack trace to client
  return c.json(fail("Internal server error"), 500);
};
