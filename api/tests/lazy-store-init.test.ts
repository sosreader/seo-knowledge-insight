/**
 * Lazy QA store cold start — 驗證 cold start 不再被 QA store 載入阻塞。
 *
 * 對應 plans/active/lazy-qa-store-cold-start.md 的 S1 驗收：
 *   - 用不到 QA 的 route（/reports）完全不觸發 loadQaStore
 *   - 需要 QA 的 route（/search）會觸發，且 memoize 只載入一次
 *   - QA 載入失敗時 route 以降級狀態回應，不是 500
 */

import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest";
import type { Hono } from "hono";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const tmpDir = mkdtempSync(join(tmpdir(), "lazy-store-init-"));
mkdirSync(join(tmpDir, "metrics_snapshots"), { recursive: true });
mkdirSync(join(tmpDir, "sessions"), { recursive: true });

const mocks = vi.hoisted(() => ({
  loadQaStore: vi.fn(async () => {}),
}));

vi.mock("../src/store/qa-store.js", () => ({
  qaStore: {
    loaded: false,
    count: 0,
    allItems: [],
    keywordSearch: () => [],
    hybridSearch: async () => [],
    categories: () => [],
    collections: () => [],
    listQa: () => ({ items: [], total: 0 }),
  },
  loadQaStore: mocks.loadQaStore,
}));

vi.mock("../src/services/embedding.js", () => ({
  getEmbedding: vi.fn().mockResolvedValue(new Float32Array(1536)),
}));

vi.mock("../src/config.js", () => ({
  config: {
    SEO_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
    CHAT_CONTEXT_K: 5,
    OPENAI_API_KEY: "",
  },
  paths: {
    outputDir: tmpDir,
    sessionsDir: join(tmpDir, "sessions"),
    scriptsDir: join(tmpDir, "scripts"),
    rootDir: tmpDir,
    metricsSnapshotsDir: join(tmpDir, "metrics_snapshots"),
    synonymCustomJsonPath: join(tmpDir, "synonym_custom.json"),
  },
}));

let app: Hono;
let resetStoreInit: () => void;

beforeAll(async () => {
  writeFileSync(join(tmpDir, "report_20260301.md"), "# Report", "utf-8");
  const { app: mainApp } = await import("../src/index.js");
  const { _resetStoreInitForTest } = await import("../src/store/store-init.js");
  app = mainApp;
  resetStoreInit = _resetStoreInitForTest;
});

beforeEach(() => {
  resetStoreInit();
  mocks.loadQaStore.mockReset();
  mocks.loadQaStore.mockResolvedValue(undefined);
});

describe("cold start 不載入 QA store", () => {
  it("GET /api/v1/reports 不觸發 loadQaStore", async () => {
    const res = await app.request("/api/v1/reports");

    expect(res.status).toBe(200);
    expect(mocks.loadQaStore).not.toHaveBeenCalled();
  });

  it("GET /api/v1/pipeline/metrics/snapshots 不觸發 loadQaStore", async () => {
    const res = await app.request("/api/v1/pipeline/metrics/snapshots");

    expect(res.status).toBe(200);
    expect(mocks.loadQaStore).not.toHaveBeenCalled();
  });

  it("GET /api/v1/sessions 列表不觸發 loadQaStore", async () => {
    const res = await app.request("/api/v1/sessions");

    expect(res.status).toBe(200);
    expect(mocks.loadQaStore).not.toHaveBeenCalled();
  });

  it("GET /api/v1/synonyms 不觸發 loadQaStore", async () => {
    const res = await app.request("/api/v1/synonyms");

    expect(res.status).toBe(200);
    expect(mocks.loadQaStore).not.toHaveBeenCalled();
  });
});

describe("需要 QA 的 route 才 lazy 載入", () => {
  async function postSearch(query: string) {
    return app.request("/api/v1/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
  }

  it("POST /api/v1/search 觸發載入", async () => {
    const res = await postSearch("SEO");

    expect(res.status).toBe(200);
    expect(mocks.loadQaStore).toHaveBeenCalledTimes(1);
  });

  it("連續請求只載入一次（memoize）", async () => {
    await postSearch("SEO");
    await postSearch("CTR");
    await postSearch("index coverage");

    expect(mocks.loadQaStore).toHaveBeenCalledTimes(1);
  });

  it("POST /api/v1/sessions/:id/messages 會觸發載入（列表不會）", async () => {
    const res = await app.request(
      "/api/v1/sessions/00000000-0000-4000-8000-000000000000/messages",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "SEO" }),
      },
    );

    // session 不存在 → 404；重點是 middleware 已先跑過
    expect(res.status).toBe(404);
    expect(mocks.loadQaStore).toHaveBeenCalledTimes(1);
  });

  it("GET /api/v1/qa 也走同一組 lazy 載入", async () => {
    const res = await app.request("/api/v1/qa");

    expect(res.status).toBe(200);
    expect(mocks.loadQaStore).toHaveBeenCalledTimes(1);
  });
});

describe("QA 載入失敗時降級而非 500", () => {
  it("POST /api/v1/search 在載入失敗時仍回 200 與空結果", async () => {
    mocks.loadQaStore.mockRejectedValueOnce(
      new Error("Supabase SELECT qa_items failed (500): statement timeout"),
    );

    const res = await app.request("/api/v1/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "SEO" }),
    });

    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.results).toEqual([]);
  });

  it("載入失敗後下一個請求會重試", async () => {
    mocks.loadQaStore.mockRejectedValueOnce(new Error("transient failure"));

    await app.request("/api/v1/qa");
    await app.request("/api/v1/qa");

    expect(mocks.loadQaStore).toHaveBeenCalledTimes(2);
  });
});
