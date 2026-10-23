import { describe, it, expect } from "vitest";
import { Hono } from "hono";
import { resolveAuthMode, selectAuthMiddleware } from "../../src/middleware/auth-mode.js";

describe("resolveAuthMode", () => {
  it("defaults to cf-access in the container and api-key in Lambda", () => {
    expect(resolveAuthMode("", false)).toBe("cf-access");
    expect(resolveAuthMode(undefined, false)).toBe("cf-access");
    expect(resolveAuthMode("", true)).toBe("api-key");
  });

  it("honours an explicit mode", () => {
    expect(resolveAuthMode("api-key", false)).toBe("api-key");
    expect(resolveAuthMode("cf-access", true)).toBe("cf-access");
  });

  it("fails closed to cf-access on an unknown value", () => {
    expect(resolveAuthMode("off", false)).toBe("cf-access");
    expect(resolveAuthMode("none", true)).toBe("cf-access");
  });
});

describe("selectAuthMiddleware", () => {
  it("returns the middleware for the resolved mode", async () => {
    const apiKey = async (_c: unknown, next: () => Promise<void>) => next();
    const cf = async () => new Response("cf", { status: 503 });
    const app = new Hono();
    app.use("*", selectAuthMiddleware("cf-access", { apiKey, cfAccess: cf }));
    app.get("/x", (c) => c.text("ok"));
    expect((await app.request("/x")).status).toBe(503);

    const app2 = new Hono();
    app2.use("*", selectAuthMiddleware("api-key", { apiKey, cfAccess: cf }));
    app2.get("/x", (c) => c.text("ok"));
    expect((await app2.request("/x")).status).toBe(200);
  });
});
