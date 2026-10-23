import { createMiddleware } from "hono/factory";
import type { Context } from "hono";
import { fail } from "../schemas/api-response.js";
import { getAccessIdentity } from "./access-context.js";

/**
 * In-process 限流（單副本；rag-api 1 replica，Lambda 模式停用）。
 *
 * key：CF Access 驗證過的身分（JWT sub／service token common_name）優先，沒有才退回 client IP。
 * 給 `bucket` 時同一身分跨路徑共用一個計數（例如 chat 類路由共用每分鐘／每日額度）；
 * 否則以「身分＋路徑」分開計數（沿用舊行為）。每筆 entry 記自己的視窗長度，清理時不會用錯視窗。
 */

interface RateLimitEntry {
  readonly timestamps: readonly number[];
  readonly windowMs: number;
}

export interface RateLimitOptions {
  /** 跨路徑共用的計數名稱；未給時以路徑分開計數。 */
  readonly bucket?: string;
}

const isLambda = !!process.env.AWS_LAMBDA_FUNCTION_NAME || !!process.env.AWS_EXECUTION_ENV;

if (isLambda) {
  console.warn("[rate-limit] In-process rate limiting is DISABLED in Lambda. Reserved concurrency=10 provides basic protection.");
}

let store: ReadonlyMap<string, RateLimitEntry> = new Map();

// Cleanup stale entries every 5 minutes
const CLEANUP_INTERVAL_MS = 5 * 60 * 1000;

let cleanupTimer: ReturnType<typeof setInterval> | null = null;

/** 依各 entry 自己的視窗剔除過期時間戳；全空的 entry 移除。純函式。 */
export function pruneEntries(
  entries: ReadonlyMap<string, RateLimitEntry>,
  now: number,
): ReadonlyMap<string, RateLimitEntry> {
  const next = new Map<string, RateLimitEntry>();
  for (const [key, entry] of entries) {
    const timestamps = entry.timestamps.filter((t) => now - t < entry.windowMs);
    if (timestamps.length > 0) next.set(key, { timestamps, windowMs: entry.windowMs });
  }
  return next;
}

function startCleanup(): void {
  if (cleanupTimer) return;
  cleanupTimer = setInterval(() => {
    store = pruneEntries(store, Date.now());
  }, CLEANUP_INTERVAL_MS);
  // Allow process to exit without waiting for timer
  if (cleanupTimer && typeof cleanupTimer === "object" && "unref" in cleanupTimer) {
    cleanupTimer.unref();
  }
}

export function resetRateLimitStore(): void {
  store = new Map();
}

function clientKey(c: Context): string {
  const identity = getAccessIdentity(c);
  if (identity) return `id:${identity}`;
  const ip =
    c.req.header("x-forwarded-for")?.split(",")[0]?.trim() ??
    c.req.header("x-real-ip") ??
    "unknown";
  return `ip:${ip}`;
}

export function rateLimit(
  maxRequests: number,
  windowMs: number = 60_000,
  options: RateLimitOptions = {},
) {
  startCleanup();

  return createMiddleware(async (c, next) => {
    // In Lambda, each execution environment has its own Map — rate limiting is ineffective.
    // Use API Gateway throttling or an external store for Lambda rate limiting.
    if (isLambda) {
      await next();
      return;
    }
    const scope = options.bucket ? `bucket:${options.bucket}` : `path:${c.req.path}`;
    const key = `${clientKey(c)}|${scope}|${windowMs}`;
    const now = Date.now();

    const previous = store.get(key)?.timestamps ?? [];
    const filtered = previous.filter((t) => now - t < windowMs);

    if (filtered.length >= maxRequests) {
      const retryAfter = Math.ceil((filtered[0]! + windowMs - now) / 1000);
      c.header("Retry-After", String(retryAfter));
      c.header("X-RateLimit-Limit", String(maxRequests));
      c.header("X-RateLimit-Remaining", "0");
      return c.json(fail("Rate limit exceeded"), 429);
    }

    const timestamps = [...filtered, now];
    store = new Map(store).set(key, { timestamps, windowMs });

    c.header("X-RateLimit-Limit", String(maxRequests));
    c.header("X-RateLimit-Remaining", String(maxRequests - timestamps.length));

    await next();
  });
}
