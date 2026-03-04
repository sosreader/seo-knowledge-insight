import { describe, it, expect } from "vitest";
import { Hono } from "hono";
import { createAuthMiddleware } from "../../src/middleware/auth.js";

function createApp(apiKey: string) {
  const auth = createAuthMiddleware(() => apiKey);
  const app = new Hono();
  app.use("/api/*", auth);
  app.get("/api/test", (c) => c.json({ ok: true }));
  app.get("/health", (c) => c.json({ status: "healthy" }));
  return app;
}

describe("auth middleware", () => {
  const app = createApp("test-secret-key");

  it("returns 401 when no API key provided", async () => {
    const res = await app.request("/api/test");
    expect(res.status).toBe(401);

    const body = await res.json();
    expect(body.error).toBe("Invalid or missing API key");
    expect(body.data).toBeNull();
    expect(res.headers.get("WWW-Authenticate")).toBe("ApiKey");
  });

  it("returns 401 when wrong API key provided", async () => {
    const res = await app.request("/api/test", {
      headers: { "X-API-Key": "wrong-key" },
    });
    expect(res.status).toBe(401);
  });

  it("returns 200 when correct API key provided", async () => {
    const res = await app.request("/api/test", {
      headers: { "X-API-Key": "test-secret-key" },
    });
    expect(res.status).toBe(200);

    const body = await res.json();
    expect(body.ok).toBe(true);
  });

  it("does not affect routes outside /api/*", async () => {
    const res = await app.request("/health");
    expect(res.status).toBe(200);
  });
});

describe("auth middleware - dev mode (no key set)", () => {
  const app = createApp("");

  it("allows requests when SEO_API_KEY is empty", async () => {
    const res = await app.request("/api/test");
    expect(res.status).toBe(200);

    const body = await res.json();
    expect(body.ok).toBe(true);
  });
});
