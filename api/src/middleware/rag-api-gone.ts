import type { MiddlewareHandler } from "hono";
import { hasPg } from "../store/pg-client.js";
import { fail } from "../schemas/api-response.js";
import { NotAvailableInRagApiError } from "../store/store-errors.js";

/**
 * rag-api（PG 模式）不提供的路由群：週報（/reports）、會議準備（/meeting-prep）。
 *
 * warehouse_rag 沒有 app_report／app_meeting_prep 權限（VW roles-matrix），
 * 前端讀報告改走 warehouse-api `/internal/app/*`；這裡回 410 Gone，代碼 not_available_in_rag_api。
 * 本機檔案模式（未設 VW_DB_SECRET_FILE_RAG）照舊讀寫 output/。
 */
export function ragApiGone(feature: string): MiddlewareHandler {
  return async (c, next) => {
    if (hasPg()) {
      const err = new NotAvailableInRagApiError(feature);
      return c.json(fail(err.code), err.status);
    }
    await next();
  };
}
