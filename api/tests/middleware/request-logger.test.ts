import { describe, it, expect, vi, afterEach } from "vitest";
import { Hono } from "hono";
import { requestLogger } from "../../src/middleware/request-logger.js";

function createApp() {
  const app = new Hono();
  app.use("*", requestLogger);
  app.get("/ok", (c) => c.json({ ok: true }));
  app.get("/not-found", (c) => c.json({ error: "not found" }, 404));
  app.get("/health", (c) => c.json({ status: "healthy" }));
  app.onError((_err, c) => c.json({ error: "server error" }, 500));
  app.get("/boom", () => {
    throw new Error("unexpected failure");
  });
  return app;
}

describe("request-logger middleware", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("logs request with method, path, status, duration_ms", async () => {
    const spy = vi.spyOn(console, "log").mockImplementation(() => {});
    const app = createApp();

    await app.request("/ok");

    expect(spy).toHaveBeenCalledTimes(1);
    const raw = spy.mock.calls[0][0] as string;
    const log = JSON.parse(raw);

    expect(log.method).toBe("GET");
    expect(log.path).toBe("/ok");
    expect(log.status).toBe(200);
    expect(typeof log.duration_ms).toBe("number");
    expect(log.duration_ms).toBeGreaterThanOrEqual(0);
  });

  it("sets X-Request-Id response header", async () => {
    vi.spyOn(console, "log").mockImplementation(() => {});
    const app = createApp();

    const res = await app.request("/ok");
    const requestId = res.headers.get("X-Request-Id");

    expect(requestId).not.toBeNull();
    // UUID v4 format
    expect(requestId).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
    );
  });

  it('uses "warn" level for 4xx status', async () => {
    const spy = vi.spyOn(console, "log").mockImplementation(() => {});
    const app = createApp();

    await app.request("/not-found");

    expect(spy).toHaveBeenCalledTimes(1);
    const log = JSON.parse(spy.mock.calls[0][0] as string);
    expect(log.level).toBe("warn");
    expect(log.status).toBe(404);
  });

  it('uses "error" level for 5xx status', async () => {
    const spy = vi.spyOn(console, "log").mockImplementation(() => {});
    const app = createApp();

    await app.request("/boom");

    expect(spy).toHaveBeenCalledTimes(1);
    const log = JSON.parse(spy.mock.calls[0][0] as string);
    expect(log.level).toBe("error");
    expect(log.status).toBe(500);
  });

  it("skips /health requests", async () => {
    const spy = vi.spyOn(console, "log").mockImplementation(() => {});
    const app = createApp();

    await app.request("/health");

    expect(spy).not.toHaveBeenCalled();
  });

  it("does not log sensitive headers (X-API-Key)", async () => {
    const spy = vi.spyOn(console, "log").mockImplementation(() => {});
    const app = createApp();
    const secretKey = "super-secret-api-key-value";

    await app.request("/ok", {
      headers: { "X-API-Key": secretKey },
    });

    expect(spy).toHaveBeenCalledTimes(1);
    const raw = spy.mock.calls[0][0] as string;
    expect(raw).not.toContain(secretKey);
  });

  it("outputs valid JSON format", async () => {
    const spy = vi.spyOn(console, "log").mockImplementation(() => {});
    const app = createApp();

    await app.request("/ok");

    expect(spy).toHaveBeenCalledTimes(1);
    const raw = spy.mock.calls[0][0] as string;

    let parsed: unknown;
    expect(() => {
      parsed = JSON.parse(raw);
    }).not.toThrow();

    const log = parsed as Record<string, unknown>;
    expect(log.level).toBeDefined();
    expect(log.method).toBeDefined();
    expect(log.path).toBeDefined();
    expect(log.status).toBeDefined();
    expect(log.duration_ms).toBeDefined();
    expect(log.request_id).toBeDefined();
    expect(log.timestamp).toBeDefined();
  });
});
