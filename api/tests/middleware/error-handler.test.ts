import { describe, it, expect } from "vitest";
import { Hono } from "hono";
import { errorHandler } from "../../src/middleware/error-handler.js";

describe("error-handler middleware", () => {
  it("returns 500 with generic message, no stack trace", async () => {
    const app = new Hono();
    app.onError(errorHandler);
    app.get("/boom", () => {
      throw new Error("sensitive database details here");
    });

    const res = await app.request("/boom");
    expect(res.status).toBe(500);

    const body = await res.json();
    expect(body.error).toBe("Internal server error");
    expect(body.data).toBeNull();
    expect(body.meta).toBeDefined();
    // Must NOT leak the original error message
    expect(JSON.stringify(body)).not.toContain("sensitive database details");
  });
});
