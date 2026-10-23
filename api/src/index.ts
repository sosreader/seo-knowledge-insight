import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { apiReference } from "@scalar/hono-api-reference";
import { config } from "./config.js";
import { corsMiddleware } from "./middleware/cors.js";
import { securityHeaders } from "./middleware/security-headers.js";
import { requestLogger } from "./middleware/request-logger.js";
import { authMiddleware } from "./middleware/auth.js";
import { createCfAccessMiddleware, parseAccessSettings } from "./middleware/cf-access.js";
import { resolveAuthMode, selectAuthMiddleware } from "./middleware/auth-mode.js";
import { errorHandler } from "./middleware/error-handler.js";
import { rateLimit } from "./middleware/rate-limit.js";
import { healthRoute } from "./routes/health.js";
import { qaRoute } from "./routes/qa.js";
import { searchRoute } from "./routes/search.js";
import { chatRoute } from "./routes/chat.js";
import { reportsRoute } from "./routes/reports.js";
import { sessionsRoute } from "./routes/sessions.js";
import { feedbackRoute } from "./routes/feedback.js";
import { pipelineRoute } from "./routes/pipeline.js";
import { synonymsRoute } from "./routes/synonyms.js";
import { meetingPrepRoute } from "./routes/meeting-prep.js";
import { buildOpenAPISpec } from "./openapi.js";
import { qaStoreReady, synonymsReady } from "./middleware/qa-ready.js";
import { requireLlm } from "./middleware/feature-gates.js";
import {
  ensureQaStoreLoaded,
  ensureSynonymsLoaded,
} from "./store/store-init.js";
import { initLaminar, flushLaminar } from "./utils/observability.js";
import { closePool } from "./store/pg-client.js";
import { resolveServerCapabilities, formatCapabilityTag } from "./utils/capabilities.js";

const isLambda = !!process.env.AWS_LAMBDA_FUNCTION_NAME || !!process.env.AWS_EXECUTION_ENV;

const app = new Hono();

// Global middleware
app.onError(errorHandler);
app.use("*", corsMiddleware);
app.use("*", securityHeaders);
app.use("*", requestLogger);

// Health check (no auth, no rate limit)
app.route("/", healthRoute);

// OpenAPI spec + Scalar docs (no auth, no rate limit)
app.get("/openapi.json", (c) => c.json(buildOpenAPISpec()));
app.get(
  "/docs",
  apiReference({
    url: "/openapi.json",
    pageTitle: "SEO Knowledge Insight API",
  }),
);

// API routes (auth + rate limit)
// 驗證：容器模式（vocus-stg rag-api）驗 Cloudflare Access JWT；Lambda 模式與本機 docker-compose 沿用 X-API-Key。
const authMode = resolveAuthMode(config.AUTH_MODE, isLambda);
const api = new Hono();
api.use(
  "*",
  selectAuthMiddleware(authMode, {
    apiKey: authMiddleware,
    cfAccess: createCfAccessMiddleware(
      parseAccessSettings(config.CF_ACCESS_TEAM_DOMAIN, config.RAG_AUDS),
    ),
  }),
);

const DAY_MS = 24 * 60 * 60 * 1000;
// chat 類路由（會打 LLM）每身分共用一個每分鐘與每日額度
const chatLimits = [
  rateLimit(config.RATE_LIMIT_CHAT, 60_000, { bucket: "chat" }),
  rateLimit(config.RATE_LIMIT_CHAT_DAILY, DAY_MS, { bucket: "chat-daily" }),
] as const;

// Rate-limited routes
api.use("/qa/*", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/qa", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/search", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/chat", ...chatLimits);
api.use("/chat/*", ...chatLimits);
api.use("/feedback", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/reports", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/reports/generate", rateLimit(config.RATE_LIMIT_GENERATE));
api.use("/reports/*", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/sessions", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/sessions/:session_id/messages", ...chatLimits);
api.use("/sessions/*", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/pipeline", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/pipeline/*", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/synonyms", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/synonyms/*", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/meeting-prep", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/meeting-prep/*", rateLimit(config.RATE_LIMIT_DEFAULT));

// LLM 類路由：線上未設 OPENAI_API_KEY／LLM_BASE_URL → 501 llm_disabled。
// 排在 rate limit 之後（額度照算）、qaStoreReady 之前（功能沒開就不等 QA 載入）。
api.use("/chat", requireLlm);
api.use("/chat/*", requireLlm);
api.use("/sessions/:session_id/messages", requireLlm);

// Store-ready middleware — 只掛在真正需要該 store 的掛載點，
// 其餘 route（/reports、/pipeline、/meeting-prep、/feedback、/sessions 列表）
// 在 cold start 時完全不觸發 qa_items 查詢。
api.use("/qa", qaStoreReady);
api.use("/qa/*", qaStoreReady);
api.use("/search", qaStoreReady);
api.use("/chat", qaStoreReady);
api.use("/chat/*", qaStoreReady);
// GET /sessions 列表不需要 QA；只有送訊息會走 RAG／agent 檢索
api.use("/sessions/:session_id/messages", qaStoreReady);
api.use("/synonyms", synonymsReady);
api.use("/synonyms/*", synonymsReady);

// Mount routes
api.route("/qa", qaRoute);
api.route("/search", searchRoute);
api.route("/chat", chatRoute);
api.route("/reports", reportsRoute);
api.route("/sessions", sessionsRoute);
api.route("/feedback", feedbackRoute);
api.route("/pipeline", pipelineRoute);
api.route("/synonyms", synonymsRoute);
api.route("/meeting-prep", meetingPrepRoute);

app.route("/api/v1", api);
// Cloudflare tunnel ingress `^/internal/rag/`（S2.4）原樣轉送路徑，同一組路由與驗證也掛在這個前綴
app.route("/internal/rag", api);

// Server startup
const port = config.PORT;

/**
 * Cold start 必做的最小初始化（Node.js server 與 Lambda 共用）。冪等。
 * 這裡不得加入任何會打資料庫的動作——QA store 與 synonyms
 * 一律交給 store/store-init.ts 的 ensureXxxLoaded() 在需要時才載入。
 */
let _corePromise: Promise<void> | null = null;

export function initCore(): Promise<void> {
  if (!_corePromise) {
    _corePromise = _doInitCore().catch((err) => {
      _corePromise = null;
      throw err;
    });
  }
  return _corePromise;
}

/** 保留給既有呼叫端／測試的名稱；語意已改為只做 initCore()。 */
export function initStores(): Promise<void> {
  return initCore();
}

async function _doInitCore(): Promise<void> {
  await initLaminar();
  console.log(formatCapabilityTag(resolveServerCapabilities()));
}

export { ensureQaStoreLoaded, ensureSynonymsLoaded };

if (process.env.NODE_ENV !== "test" && !isLambda) {
  // 本機是長駐 process，啟動時預載仍然划算——但走的是同一組 lazy 函式，不另開一套邏輯。
  await initCore();
  await ensureQaStoreLoaded();
  await ensureSynonymsLoaded();

  serve({ fetch: app.fetch, port }, (info) => {
    console.log(`Server running on http://localhost:${info.port}`);
  });

  const shutdown = async () => {
    await flushLaminar();
    await closePool().catch(() => undefined);
    process.exit(0);
  };
  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);
}

export { app };
export default app;
