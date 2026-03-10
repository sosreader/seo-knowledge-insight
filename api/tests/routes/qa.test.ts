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
        if (params.source_type) results = results.filter((i) => i.source_type === params.source_type);
        if (params.source_collection) results = results.filter((i) => i.source_collection === params.source_collection);
        if (params.extraction_model) results = results.filter((i) => i.extraction_model === params.extraction_model);
        if (params.sort_by === "source_date") {
          const dir = params.sort_order === "asc" ? 1 : -1;
          results.sort((a, b) => dir * a.source_date.localeCompare(b.source_date));
        }
        const offset = (params.offset as number) ?? 0;
        const limit = (params.limit as number) ?? 20;
        return { items: results.slice(offset, offset + limit), total: results.length };
      },
      categories: () => ["SEO Technical", "On-Page SEO", "SEO Strategy"],
      collections: () => [
        { source_collection: "seo-meetings", source_type: "meeting", count: 4 },
        { source_collection: "genehong-medium", source_type: "article", count: 1 },
      ],
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

  it("sorts by source_date ascending", async () => {
    const res = await app.request("/api/v1/qa?sort_by=source_date&sort_order=asc");
    expect(res.status).toBe(200);
    const body = await res.json();
    const dates = body.data.items.map((i: { source_date: string }) => i.source_date);
    for (let i = 1; i < dates.length; i++) {
      expect(dates[i] >= dates[i - 1]).toBe(true);
    }
  });

  it("sorts by source_date descending", async () => {
    const res = await app.request("/api/v1/qa?sort_by=source_date&sort_order=desc");
    expect(res.status).toBe(200);
    const body = await res.json();
    const dates = body.data.items.map((i: { source_date: string }) => i.source_date);
    for (let i = 1; i < dates.length; i++) {
      expect(dates[i] <= dates[i - 1]).toBe(true);
    }
  });

  it("filters by source_type", async () => {
    const res = await app.request("/api/v1/qa?source_type=article");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.total).toBe(1);
    for (const item of body.data.items) {
      expect(item.source_type).toBe("article");
    }
  });

  it("filters by source_collection", async () => {
    const res = await app.request("/api/v1/qa?source_collection=genehong-medium");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.total).toBe(1);
    for (const item of body.data.items) {
      expect(item.source_collection).toBe("genehong-medium");
    }
  });

  it("returns source_type, source_collection, source_url in response", async () => {
    const res = await app.request("/api/v1/qa?limit=10");
    expect(res.status).toBe(200);
    const body = await res.json();
    for (const item of body.data.items) {
      expect(item).toHaveProperty("source_type");
      expect(item).toHaveProperty("source_collection");
      expect(item).toHaveProperty("source_url");
    }
    // article item should have populated source_url
    const article = body.data.items.find((i: { source_type: string }) => i.source_type === "article");
    expect(article).toBeDefined();
    expect(article.source_url).toContain("genehong.medium.com");
  });

  it("filters by extraction_model", async () => {
    const res = await app.request("/api/v1/qa?extraction_model=gpt-4o");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.total).toBe(1);
    for (const item of body.data.items) {
      expect(item.extraction_model).toBe("gpt-4o");
    }
  });

  it("returns extraction_model and freshness_score in response", async () => {
    const res = await app.request("/api/v1/qa?limit=10");
    expect(res.status).toBe(200);
    const body = await res.json();
    for (const item of body.data.items) {
      expect(item).toHaveProperty("extraction_model");
      expect(item).toHaveProperty("freshness_score");
      expect(typeof item.freshness_score).toBe("number");
    }
  });

  it("returns all items when no source filter applied", async () => {
    const res = await app.request("/api/v1/qa?limit=100");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.total).toBe(5); // 4 meeting + 1 article
  });
});

describe("GET /api/v1/qa/collections", () => {
  it("returns collection list with counts", async () => {
    const res = await app.request("/api/v1/qa/collections");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.collections).toHaveLength(2);
    const seoMeetings = body.data.collections.find(
      (c: { source_collection: string }) => c.source_collection === "seo-meetings",
    );
    expect(seoMeetings).toBeDefined();
    expect(seoMeetings.source_type).toBe("meeting");
    expect(seoMeetings.count).toBe(4);

    const medium = body.data.collections.find(
      (c: { source_collection: string }) => c.source_collection === "genehong-medium",
    );
    expect(medium).toBeDefined();
    expect(medium.source_type).toBe("article");
    expect(medium.count).toBe(1);
  });
});
