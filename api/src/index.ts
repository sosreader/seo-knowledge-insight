import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { apiReference } from "@scalar/hono-api-reference";
import { config, paths } from "./config.js";
import { corsMiddleware } from "./middleware/cors.js";
import { securityHeaders } from "./middleware/security-headers.js";
import { requestLogger } from "./middleware/request-logger.js";
import { authMiddleware } from "./middleware/auth.js";
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
import { buildOpenAPISpec } from "./openapi.js";
import { qaStore, loadQaStore } from "./store/qa-store.js";
import { synonymsStore } from "./store/synonyms-store.js";
import { initLaminar, flushLaminar } from "./utils/observability.js";

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
const api = new Hono();
api.use("*", authMiddleware);

// Rate-limited routes
api.use("/qa/*", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/qa", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/search", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/chat", rateLimit(config.RATE_LIMIT_CHAT));
api.use("/feedback", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/reports", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/reports/generate", rateLimit(config.RATE_LIMIT_GENERATE));
api.use("/reports/*", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/sessions", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/sessions/*", rateLimit(config.RATE_LIMIT_CHAT));
api.use("/pipeline", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/pipeline/*", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/synonyms", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/synonyms/*", rateLimit(config.RATE_LIMIT_DEFAULT));

// Mount routes
api.route("/qa", qaRoute);
api.route("/search", searchRoute);
api.route("/chat", chatRoute);
api.route("/reports", reportsRoute);
api.route("/sessions", sessionsRoute);
api.route("/feedback", feedbackRoute);
api.route("/pipeline", pipelineRoute);
api.route("/synonyms", synonymsRoute);

app.route("/api/v1", api);

// Server startup
const port = config.PORT;

/** Initialize stores (shared between Node.js server and Lambda cold start). Idempotent. */
let _initPromise: Promise<void> | null = null;

export function initStores(): Promise<void> {
  if (!_initPromise) {
    _initPromise = _doInitStores().catch((err) => {
      _initPromise = null;
      throw err;
    });
  }
  return _initPromise;
}

async function _doInitStores(): Promise<void> {
  await initLaminar();

  try {
    await loadQaStore();
    console.log(`QAStore loaded: ${qaStore.count} items`);
  } catch (err) {
    console.warn("QAStore load failed (API will run without search):", err);
  }

  try {
    if (synonymsStore.load) {
      await synonymsStore.load();
    } else if (synonymsStore.init) {
      synonymsStore.init(paths.synonymCustomJsonPath);
    }
  } catch (err) {
    console.warn("SynonymsStore load failed:", err);
  }
}

if (process.env.NODE_ENV !== "test" && !isLambda) {
  await initStores();

  serve({ fetch: app.fetch, port }, (info) => {
    console.log(`Server running on http://localhost:${info.port}`);
  });

  const shutdown = async () => {
    await flushLaminar();
    process.exit(0);
  };
  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);
}

export { app };
export default app;
