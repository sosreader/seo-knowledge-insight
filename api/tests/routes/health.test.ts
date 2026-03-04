import { describe, it, expect } from "vitest";
import { app } from "../../src/index.js";

describe("GET /health", () => {
  it("returns healthy status", async () => {
    const res = await app.request("/health");
    expect(res.status).toBe(200);

    const body = await res.json();
    expect(body.status).toBe("healthy");
    expect(body.version).toBe("2.2.0");
    expect(body.timestamp).toBeDefined();
  });

  it("returns valid ISO timestamp", async () => {
    const res = await app.request("/health");
    const body = await res.json();
    const date = new Date(body.timestamp);
    expect(date.toISOString()).toBe(body.timestamp);
  });
});
