import type { MiddlewareHandler } from "hono";
import { isLlmEnabled } from "../services/llm-client.js";
import { hasPg } from "../store/pg-client.js";
import { featureUnavailableBody } from "../utils/feature-errors.js";

/**
 * LLM 類路由（chat、agent、sessions/:id/messages）的閘門：LLM disabled → 501 llm_disabled。
 * 掛在 rate limit 之後、qaStoreReady 之前：功能沒開就不必等 QA 載入。
 */
export const requireLlm: MiddlewareHandler = async (c, next) => {
  if (!isLlmEnabled()) return c.json(featureUnavailableBody("llm_disabled"), 501);
  await next();
};

/**
 * pipeline 觸發與本機檔案依賴路由：rag-api（PG 模式）不執行 → 501 run_locally。
 * 本機檔案模式（未設 VW_DB_SECRET_FILE_RAG）照舊執行，即 make pipeline／本機 dev server 的用法。
 */
export const runLocallyInRagApi: MiddlewareHandler = async (c, next) => {
  if (hasPg()) return c.json(featureUnavailableBody("run_locally"), 501);
  await next();
};
