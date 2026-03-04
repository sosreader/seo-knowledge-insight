import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { writeFileSync, rmSync, existsSync } from "node:fs";

// ---------- mocks ----------

vi.mock("../../src/store/qa-store.js", () => ({
  qaStore: { loaded: false, count: 0 },
}));

vi.mock("../../src/config.js", () => ({
  config: {
    SEO_API_KEY: "",
    OPENAI_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
    CHAT_CONTEXT_K: 5,
  },
  paths: {
    rootDir: tmpdir(),
    outputDir: join(tmpdir(), "output"),
    synonymCustomJsonPath: join(tmpdir(), "output", "synonym_custom_test.json"),
  },
}));

// ---------- test setup ----------

import { Hono } from "hono";
import { synonymsRoute } from "../../src/routes/synonyms.js";
import { synonymsStore } from "../../src/store/synonyms-store.js";
import { paths } from "../../src/config.js";

const TEST_CUSTOM_PATH = paths.synonymCustomJsonPath;

function buildApp() {
  const app = new Hono();
  app.route("/api/v1/synonyms", synonymsRoute);
  return app;
}

function cleanupFile() {
  if (existsSync(TEST_CUSTOM_PATH)) {
    rmSync(TEST_CUSTOM_PATH);
  }
}

beforeEach(() => {
  cleanupFile();
  synonymsStore.init(TEST_CUSTOM_PATH);
});

afterEach(() => {
  cleanupFile();
});

// ---------- GET /api/v1/synonyms ----------

describe("GET /api/v1/synonyms", () => {
  it("returns static terms with source='static'", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/synonyms");
    expect(res.status).toBe(200);

    const body = await res.json();
    expect(body.data).toBeInstanceOf(Array);
    expect(body.data.length).toBeGreaterThan(0);

    // All items have expected shape
    for (const item of body.data) {
      expect(item).toHaveProperty("term");
      expect(item).toHaveProperty("synonyms");
      expect(item).toHaveProperty("source");
      expect(["static", "custom"]).toContain(item.source);
    }

    // Includes known static term
    const ctq = body.data.find((d: { term: string }) => d.term === "CTR");
    expect(ctq).toBeDefined();
    expect(ctq.source).toBe("static");
    expect(ctq.synonyms).toContain("點擊率");
  });

  it("custom entry shows up with source='custom'", async () => {
    synonymsStore.create("18禁", ["成人內容", "adult content"]);

    const app = buildApp();
    const res = await app.request("/api/v1/synonyms");
    expect(res.status).toBe(200);

    const body = await res.json();
    const item = body.data.find((d: { term: string }) => d.term === "18禁");
    expect(item).toBeDefined();
    expect(item.source).toBe("custom");
    expect(item.synonyms).toContain("成人內容");
  });

  it("custom override of static term shows source='custom'", async () => {
    synonymsStore.update("CTR", ["點擊率", "自訂CTR同義詞"]);

    const app = buildApp();
    const res = await app.request("/api/v1/synonyms");
    const body = await res.json();

    const ctq = body.data.find((d: { term: string }) => d.term === "CTR");
    expect(ctq.source).toBe("custom");
    expect(ctq.synonyms).toContain("自訂CTR同義詞");
  });
});

// ---------- POST /api/v1/synonyms ----------

describe("POST /api/v1/synonyms", () => {
  it("creates a new custom synonym entry", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/synonyms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ term: "18禁", synonyms: ["成人內容", "adult content"] }),
    });
    expect(res.status).toBe(201);

    const body = await res.json();
    expect(body.data.term).toBe("18禁");
    expect(body.data.synonyms).toContain("成人內容");
    expect(body.data.source).toBe("custom");

    // Verify file was written
    expect(existsSync(TEST_CUSTOM_PATH)).toBe(true);
    const store = synonymsStore.get("18禁");
    expect(store?.synonyms).toContain("成人內容");
  });

  it("returns 409 if term already exists in custom", async () => {
    synonymsStore.create("18禁", ["成人內容"]);
    const app = buildApp();
    const res = await app.request("/api/v1/synonyms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ term: "18禁", synonyms: ["新增"] }),
    });
    expect(res.status).toBe(409);
  });

  it("returns 400 on missing term", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/synonyms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ synonyms: ["test"] }),
    });
    expect(res.status).toBe(400);
  });

  it("returns 400 on empty synonyms", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/synonyms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ term: "新詞", synonyms: [] }),
    });
    expect(res.status).toBe(400);
  });

  it("rejects term with path traversal characters", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/synonyms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ term: "../../etc/passwd", synonyms: ["hack"] }),
    });
    expect(res.status).toBe(400);
  });

  it("rejects term longer than 100 chars", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/synonyms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ term: "a".repeat(101), synonyms: ["test"] }),
    });
    expect(res.status).toBe(400);
  });
});

// ---------- PUT /api/v1/synonyms/:term ----------

describe("PUT /api/v1/synonyms/:term", () => {
  it("updates synonyms for a custom term", async () => {
    synonymsStore.create("18禁", ["成人內容"]);

    const app = buildApp();
    const res = await app.request("/api/v1/synonyms/18%E7%A6%81", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ synonyms: ["成人內容", "nsfw", "限制級"] }),
    });
    expect(res.status).toBe(200);

    const body = await res.json();
    expect(body.data.synonyms).toContain("nsfw");
  });

  it("can override a static term", async () => {
    const app = buildApp();
    const encoded = encodeURIComponent("CTR");
    const res = await app.request(`/api/v1/synonyms/${encoded}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ synonyms: ["點擊率", "自訂"] }),
    });
    expect(res.status).toBe(200);

    const updated = synonymsStore.get("CTR");
    expect(updated?.source).toBe("custom");
    expect(updated?.synonyms).toContain("自訂");
  });

  it("returns 404 for unknown term", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/synonyms/%E4%B8%8D%E5%AD%98%E5%9C%A8", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ synonyms: ["test"] }),
    });
    expect(res.status).toBe(404);
  });

  it("returns 400 on empty synonyms", async () => {
    synonymsStore.create("18禁", ["成人內容"]);
    const app = buildApp();
    const res = await app.request("/api/v1/synonyms/18%E7%A6%81", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ synonyms: [] }),
    });
    expect(res.status).toBe(400);
  });
});

// ---------- DELETE /api/v1/synonyms/:term ----------

describe("DELETE /api/v1/synonyms/:term", () => {
  it("removes a custom synonym entry", async () => {
    synonymsStore.create("18禁", ["成人內容"]);

    const app = buildApp();
    const res = await app.request("/api/v1/synonyms/18%E7%A6%81", {
      method: "DELETE",
    });
    expect(res.status).toBe(200);

    expect(synonymsStore.get("18禁")).toBeUndefined();
  });

  it("returns 403 when deleting static-only term", async () => {
    const app = buildApp();
    const res = await app.request(`/api/v1/synonyms/${encodeURIComponent("CTR")}`, {
      method: "DELETE",
    });
    expect(res.status).toBe(403);
  });

  it("returns 404 for non-existent term", async () => {
    const app = buildApp();
    const res = await app.request(`/api/v1/synonyms/${encodeURIComponent("不存在")}`, {
      method: "DELETE",
    });
    expect(res.status).toBe(404);
  });

  it("restores static entry after deleting custom override", async () => {
    synonymsStore.update("CTR", ["自訂點擊率"]);
    expect(synonymsStore.get("CTR")?.source).toBe("custom");

    const app = buildApp();
    await app.request(`/api/v1/synonyms/${encodeURIComponent("CTR")}`, {
      method: "DELETE",
    });

    // Should fall back to static
    const restored = synonymsStore.get("CTR");
    expect(restored?.source).toBe("static");
    expect(restored?.synonyms).toContain("點擊率");
  });
});

// ---------- Input validation edge cases ----------

describe("Input validation", () => {
  it("rejects injection-like term with slashes", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/synonyms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ term: "foo/bar", synonyms: ["x"] }),
    });
    expect(res.status).toBe(400);
  });

  it("accepts CJK term", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/synonyms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ term: "搜尋引擎最佳化", synonyms: ["SEO", "Search Engine Optimization"] }),
    });
    expect(res.status).toBe(201);
  });
});
