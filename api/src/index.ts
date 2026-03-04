import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { config } from "./config.js";
import { corsMiddleware } from "./middleware/cors.js";
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
import { evalRoute } from "./routes/eval.js";
import { qaStore } from "./store/qa-store.js";
import { initLaminar, flushLaminar } from "./utils/observability.js";

const app = new Hono();

// Global middleware
app.onError(errorHandler);
app.use("*", corsMiddleware);

// Health check (no auth, no rate limit)
app.route("/", healthRoute);

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
api.use("/eval", rateLimit(config.RATE_LIMIT_DEFAULT));
api.use("/eval/*", rateLimit(config.RATE_LIMIT_DEFAULT));

// Mount routes
api.route("/qa", qaRoute);
api.route("/search", searchRoute);
api.route("/chat", chatRoute);
api.route("/reports", reportsRoute);
api.route("/sessions", sessionsRoute);
api.route("/feedback", feedbackRoute);
api.route("/pipeline", pipelineRoute);
api.route("/eval", evalRoute);

app.route("/api/v1", api);

// Server startup
const port = config.PORT;

if (process.env.NODE_ENV !== "test") {
  // Initialize Laminar tracing before loading data
  await initLaminar();

  // Load QA store before starting server
  try {
    qaStore.load();
    console.log(`QAStore loaded: ${qaStore.count} items`);
  } catch (err) {
    console.warn("QAStore load failed (API will run without search):", err);
  }

  serve({ fetch: app.fetch, port }, (info) => {
    console.log(`Server running on http://localhost:${info.port}`);
  });

  // Graceful shutdown — flush Laminar spans
  const shutdown = async () => {
    await flushLaminar();
    process.exit(0);
  };
  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);
}

export { app };
export default app;
