import { describe, it, expect, beforeEach } from "vitest";
import { Hono } from "hono";
import { rateLimit, resetRateLimitStore, pruneEntries } from "../../src/middleware/rate-limit.js";

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

describe("rate-limit identity keys", () => {
  beforeEach(() => {
    resetRateLimitStore();
  });

  function identityApp(max: number, windowMs: number, bucket?: string) {
    const app = new Hono();
    app.use("*", async (c, next) => {
      const id = c.req.header("x-test-identity");
      if (id) c.set("accessIdentity", id);
      await next();
    });
    app.use("/chat/*", rateLimit(max, windowMs, bucket ? { bucket } : undefined));
    app.post("/chat/:id", (c) => c.json({ ok: true }));
    return app;
  }

  it("keys by the Access identity rather than the client IP", async () => {
    const app = identityApp(1, 60_000);
    const send = (id: string) =>
      app.request("/chat/x", {
        method: "POST",
        headers: { "x-test-identity": id, "x-forwarded-for": "10.0.0.1" },
      });
    expect((await send("alice")).status).toBe(200);
    expect((await send("bob")).status).toBe(200);
    expect((await send("alice")).status).toBe(429);
  });

  it("shares one bucket across paths when a bucket name is given", async () => {
    const app = identityApp(1, 60_000, "chat");
    const send = (path: string) =>
      app.request(path, { method: "POST", headers: { "x-test-identity": "alice" } });
    expect((await send("/chat/a")).status).toBe(200);
    expect((await send("/chat/b")).status).toBe(429);
  });

  it("keeps daily windows independent of a shorter window on the same identity", async () => {
    const app = new Hono();
    app.use("*", async (c, next) => {
      c.set("accessIdentity", "alice");
      await next();
    });
    app.use("/chat", rateLimit(5, 60_000, { bucket: "chat-minute" }));
    app.use("/chat", rateLimit(2, 86_400_000, { bucket: "chat-day" }));
    app.post("/chat", (c) => c.json({ ok: true }));
    expect((await app.request("/chat", { method: "POST" })).status).toBe(200);
    expect((await app.request("/chat", { method: "POST" })).status).toBe(200);
    const res = await app.request("/chat", { method: "POST" });
    expect(res.status).toBe(429);
    expect(res.headers.get("X-RateLimit-Limit")).toBe("2");
  });

  it("prunes entries using each entry's own window", () => {
    const now = 10_000_000;
    const store = new Map([
      ["day", { timestamps: [now - 120_000], windowMs: 86_400_000 }],
      ["minute", { timestamps: [now - 120_000], windowMs: 60_000 }],
    ]);
    const pruned = pruneEntries(store, now);
    expect([...pruned.keys()]).toEqual(["day"]);
  });
});
