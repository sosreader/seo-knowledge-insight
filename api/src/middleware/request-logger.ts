import { createMiddleware } from "hono/factory";
import { inferCaller } from "../utils/capabilities.js";

const SKIP_PATHS = new Set(["/health"]);

type LogLevel = "info" | "warn" | "error";

function resolveLevel(status: number): LogLevel {
  if (status >= 500) return "error";
  if (status >= 400) return "warn";
  return "info";
}

export const requestLogger = createMiddleware(async (c, next) => {
  const path = new URL(c.req.url).pathname;

  if (SKIP_PATHS.has(path)) {
    await next();
    return;
  }

  const requestId = crypto.randomUUID();
  const startMs = Date.now();

  await next();

  const status = c.res.status;
  const durationMs = Date.now() - startMs;

  c.header("X-Request-Id", requestId);

  const userAgent = c.req.header("user-agent");
  const clientType = inferCaller(userAgent);

  const entry = {
    level: resolveLevel(status),
    method: c.req.method,
    path,
    status,
    duration_ms: durationMs,
    request_id: requestId,
    timestamp: new Date().toISOString(),
    user_agent: userAgent ?? null,
    client_type: clientType,
  };

  console.log(JSON.stringify(entry));
});
