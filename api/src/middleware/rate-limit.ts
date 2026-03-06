import { createMiddleware } from "hono/factory";
import { fail } from "../schemas/api-response.js";

interface RateLimitEntry {
  timestamps: number[];
}

const isLambda = !!process.env.AWS_LAMBDA_FUNCTION_NAME || !!process.env.AWS_EXECUTION_ENV;

const store = new Map<string, RateLimitEntry>();

// Cleanup stale entries every 5 minutes
const CLEANUP_INTERVAL_MS = 5 * 60 * 1000;

let cleanupTimer: ReturnType<typeof setInterval> | null = null;

function startCleanup(windowMs: number): void {
  if (cleanupTimer) return;
  cleanupTimer = setInterval(() => {
    const now = Date.now();
    for (const [key, entry] of store) {
      const filtered = entry.timestamps.filter((t) => now - t < windowMs);
      if (filtered.length === 0) {
        store.delete(key);
      } else {
        entry.timestamps = filtered;
      }
    }
  }, CLEANUP_INTERVAL_MS);
  // Allow process to exit without waiting for timer
  if (cleanupTimer && typeof cleanupTimer === "object" && "unref" in cleanupTimer) {
    cleanupTimer.unref();
  }
}

export function resetRateLimitStore(): void {
  store.clear();
}

export function rateLimit(maxRequests: number, windowMs: number = 60_000) {
  startCleanup(windowMs);

  return createMiddleware(async (c, next) => {
    // In Lambda, each execution environment has its own Map — rate limiting is ineffective.
    // Use API Gateway throttling or an external store for Lambda rate limiting.
    if (isLambda) {
      await next();
      return;
    }
    const ip =
      c.req.header("x-forwarded-for")?.split(",")[0]?.trim() ??
      c.req.header("x-real-ip") ??
      "unknown";

    const key = `${ip}:${c.req.path}`;
    const now = Date.now();

    const entry = store.get(key) ?? { timestamps: [] };
    const filtered = entry.timestamps.filter((t) => now - t < windowMs);

    if (filtered.length >= maxRequests) {
      const retryAfter = Math.ceil((filtered[0]! + windowMs - now) / 1000);
      c.header("Retry-After", String(retryAfter));
      c.header("X-RateLimit-Limit", String(maxRequests));
      c.header("X-RateLimit-Remaining", "0");
      return c.json(fail("Rate limit exceeded"), 429);
    }

    filtered.push(now);
    store.set(key, { timestamps: filtered });

    c.header("X-RateLimit-Limit", String(maxRequests));
    c.header("X-RateLimit-Remaining", String(maxRequests - filtered.length));

    await next();
  });
}
