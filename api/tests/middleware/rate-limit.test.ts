import { describe, it, expect, beforeEach } from "vitest";
import { Hono } from "hono";
import { rateLimit, resetRateLimitStore } from "../../src/middleware/rate-limit.js";

function createApp(maxRequests: number) {
  const app = new Hono();
  app.use("/api/test", rateLimit(maxRequests, 60_000));
  app.get("/api/test", (c) => c.json({ ok: true }));
  return app;
}

describe("rate-limit middleware", () => {
  beforeEach(() => {
    resetRateLimitStore();
  });

  it("allows requests under limit", async () => {
    const app = createApp(3);

    const res = await app.request("/api/test");
    expect(res.status).toBe(200);
    expect(res.headers.get("X-RateLimit-Limit")).toBe("3");
    expect(res.headers.get("X-RateLimit-Remaining")).toBe("2");
  });

  it("returns 429 when limit exceeded", async () => {
    const app = createApp(2);

    await app.request("/api/test");
    await app.request("/api/test");
    const res = await app.request("/api/test");

    expect(res.status).toBe(429);

    const body = await res.json();
    expect(body.error).toBe("Rate limit exceeded");
    expect(body.data).toBeNull();
    expect(res.headers.get("Retry-After")).toBeDefined();
    expect(res.headers.get("X-RateLimit-Remaining")).toBe("0");
  });

  it("tracks different paths separately", async () => {
    const app = new Hono();
    app.use("/api/a", rateLimit(1, 60_000));
    app.use("/api/b", rateLimit(1, 60_000));
    app.get("/api/a", (c) => c.json({ route: "a" }));
    app.get("/api/b", (c) => c.json({ route: "b" }));

    const resA = await app.request("/api/a");
    const resB = await app.request("/api/b");

    expect(resA.status).toBe(200);
    expect(resB.status).toBe(200);
  });
});
