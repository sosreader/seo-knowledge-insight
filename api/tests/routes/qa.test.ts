import { describe, it, expect, vi, beforeAll } from "vitest";
import { Hono } from "hono";
import { FAKE_ITEMS } from "../setup.js";

// Mock qa-store
vi.mock("../../src/store/qa-store.js", () => {
  const items = FAKE_ITEMS;
  return {
    qaStore: {
      loaded: true,
      count: items.length,
      getById: (id: string) => items.find((i) => i.id === id) ?? undefined,
      getBySeq: (seq: number) => items.find((i) => i.seq === seq) ?? undefined,
      listQa: (params: Record<string, unknown>) => {
        let results = [...items];
        if (params.category) results = results.filter((i) => i.category === params.category);
        if (params.keyword) {
          const kw = (params.keyword as string).toLowerCase();
          results = results.filter(
            (i) => i.question.toLowerCase().includes(kw) || i.answer.toLowerCase().includes(kw),
          );
        }
        const offset = (params.offset as number) ?? 0;
        const limit = (params.limit as number) ?? 20;
        return { items: results.slice(offset, offset + limit), total: results.length };
      },
      categories: () => ["SEO Technical", "On-Page SEO"],
    },
  };
});

// Mock config
vi.mock("../../src/config.js", () => ({
  config: {
    SEO_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
  },
  paths: { outputDir: "/tmp", sessionsDir: "/tmp/sessions-qa-test", scriptsDir: "/tmp/scripts", rootDir: "/tmp" },
}));

let app: Hono;

beforeAll(async () => {
  const { app: mainApp } = await import("../../src/index.js");
  app = mainApp;
});

describe("GET /api/v1/qa/categories", () => {
  it("returns categories", async () => {
    const res = await app.request("/api/v1/qa/categories");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.categories).toContain("SEO Technical");
  });
});

describe("GET /api/v1/qa/:id", () => {
  it("returns 400 for invalid ID format", async () => {
    const res = await app.request("/api/v1/qa/invalid-id");
    expect(res.status).toBe(400);
  });

  it("returns 404 for non-existent ID", async () => {
    const res = await app.request("/api/v1/qa/0000000000000000");
    expect(res.status).toBe(404);
  });

  it("returns QA item for valid hex ID", async () => {
    const res = await app.request("/api/v1/qa/a1b2c3d4e5f67890");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.id).toBe("a1b2c3d4e5f67890");
    expect(body.data.question).toContain("LCP");
  });

  it("returns QA item for integer seq", async () => {
    const res = await app.request("/api/v1/qa/1");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.seq).toBe(1);
    expect(body.data.question).toContain("LCP");
  });

  it("returns 404 for non-existent seq", async () => {
    const res = await app.request("/api/v1/qa/999");
    expect(res.status).toBe(404);
  });
});

describe("GET /api/v1/qa", () => {
  it("returns paginated list", async () => {
    const res = await app.request("/api/v1/qa?limit=2&offset=0");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.items.length).toBeLessThanOrEqual(2);
    expect(body.data.total).toBeGreaterThan(0);
    expect(body.data.offset).toBe(0);
    expect(body.data.limit).toBe(2);
  });

  it("filters by category", async () => {
    const res = await app.request("/api/v1/qa?category=SEO%20Technical");
    expect(res.status).toBe(200);
    const body = await res.json();
    for (const item of body.data.items) {
      expect(item.category).toBe("SEO Technical");
    }
  });
});
