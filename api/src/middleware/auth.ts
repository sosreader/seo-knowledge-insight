import { createMiddleware } from "hono/factory";
import { timingSafeEqual } from "node:crypto";
import { config } from "../config.js";
import { fail } from "../schemas/api-response.js";

export function safeCompare(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  return timingSafeEqual(Buffer.from(a), Buffer.from(b));
}

export function createAuthMiddleware(getApiKey: () => string) {
  return createMiddleware(async (c, next) => {
    const expected = getApiKey();

  if (!expected) {
    console.warn(
      "SEO_API_KEY is not set -- API authentication is DISABLED. Set this variable in production.",
    );
    await next();
    return;
  }

  const apiKey = c.req.header("X-API-Key") ?? "";

  if (!apiKey || !safeCompare(apiKey, expected)) {
    c.header("WWW-Authenticate", "ApiKey");
    return c.json(fail("Invalid or missing API key"), 401);
  }

  await next();
  });
}

export const authMiddleware = createAuthMiddleware(() => config.SEO_API_KEY);
