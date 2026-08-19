/**
 * Lazy QA store cold start — 驗證 cold start 不再被 QA store 載入阻塞。
 *
 * 對應 plans/active/lazy-qa-store-cold-start.md 的 S1 驗收：
 *   - 頁面 mount 時打的 endpoint（/reports 列表、/pipeline/metrics/snapshots、
 *     /sessions 列表、/meeting-prep）完全不觸發 loadQaStore
 *   - 真正需要 QA 的 endpoint 才觸發，且 memoize 只載入一次
 *   - QA 載入失敗時 route 以降級狀態回應，不是 500
 *   - initCore() 不得觸發任何 store 載入（cold start 不變式）
 */

import { describe, it, expect, vi, beforeAll, beforeEach } from "vitest";
import type { Hono } from "hono";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const tmpDir = mkdtempSync(join(tmpdir(), "lazy-store-init-"));
const tmpSnapshotsDir = join(tmpDir, "metrics_snapshots");
mkdirSync(tmpSnapshotsDir, { recursive: true });
mkdirSync(join(tmpDir, "sessions"), { recursive: true });

const mocks = vi.hoisted(() => {
  // 可變的 fake store：loadQaStore 成功時把 count 從 0 翻成 LOADED_COUNT，
  // 用來驗證「先 await 載入、才讀 count」的順序，而不只是「有呼叫」。
  const LOADED_COUNT = 1234;
  const qaStore = {
    loaded: false,
    count: 0,
    allItems: [] as unknown[],
    keywordSearch: () => [],
    hybridSearch: async () => [],
    categories: () => [],
    collections: () => [],
    listQa: () => ({ items: [], total: 0 }),
  };
  return {
    LOADED_COUNT,
    qaStore,
    loadQaStore: vi.fn(),
    synonymsLoad: vi.fn(async () => {}),
  };
});

vi.mock("../src/store/qa-store.js", () => ({
  qaStore: mocks.qaStore,
  loadQaStore: mocks.loadQaStore,
}));

vi.mock("../src/store/synonyms-store.js", () => ({
  STATIC_SYNONYMS: {},
  synonymsStore: {
    load: mocks.synonymsLoad,
    list: () => [],
    get: () => undefined,
    isCustom: () => false,
    isStatic: () => false,
    getCustom: () => ({}),
  },
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
    AGENT_ENABLED: false,
  },
  paths: {
    rootDir: tmpDir,
    outputDir: tmpDir,
    sessionsDir: join(tmpDir, "sessions"),
    scriptsDir: join(tmpDir, "scripts"),
    metricsSnapshotsDir: tmpSnapshotsDir,
    synonymCustomJsonPath: join(tmpDir, "synonym_custom.json"),
    qaJsonPath: join(tmpDir, "qa_final.json"),
    // 以下目錄刻意不存在——buildSourceDocs 會 existsSync 略過，回空清單
    rawDataDir: join(tmpDir, "raw_data"),
    rawMediumMdDir: join(tmpDir, "raw_data/medium_markdown"),
    rawIthelpMdDir: join(tmpDir, "raw_data/ithelp_markdown"),
    rawGoogleCasesMdDir: join(tmpDir, "raw_data/google_cases_markdown"),
    rawAhrefsMdDir: join(tmpDir, "raw_data/ahrefs_markdown"),
    rawSejMdDir: join(tmpDir, "raw_data/sej_markdown"),
    rawGrowthmemoMdDir: join(tmpDir, "raw_data/growthmemo_markdown"),
    rawGoogleBlogMdDir: join(tmpDir, "raw_data/google_blog_markdown"),
    rawGoogleBlogZhtwMdDir: join(tmpDir, "raw_data/google_blog_zhtw_markdown"),
    rawWebdevMdDir: join(tmpDir, "raw_data/webdev_markdown"),
    rawScreamingfrogMdDir: join(tmpDir, "raw_data/screamingfrog_markdown"),
    fetchLogsDir: join(tmpDir, "fetch_logs"),
  },
}));

const SNAPSHOT_ID = "20260319-120000";

let app: Hono;
let initCore: () => Promise<void>;
let resetStoreInit: () => void;

beforeAll(async () => {
  writeFileSync(join(tmpDir, "report_20260301.md"), "# Report", "utf-8");
  writeFileSync(
    join(tmpSnapshotsDir, `${SNAPSHOT_ID}.json`),
    JSON.stringify({
      id: SNAPSHOT_ID,
      created_at: "2026-03-19T12:00:00.000Z",
      label: "2026/03/19",
      weeks: 2,
      metrics: {
        CTR: { latest: 0.042, monthly: -0.12, weekly: -0.08 },
        曝光: { latest: 120000, monthly: 0.05, weekly: 0.02 },
      },
    }),
    "utf-8",
  );

  const mainModule = await import("../src/index.js");
  const { _resetStoreInitForTest } = await import("../src/store/store-init.js");
  app = mainModule.app;
  initCore = mainModule.initCore;
  resetStoreInit = _resetStoreInitForTest;
});

beforeEach(() => {
  resetStoreInit();
  mocks.qaStore.loaded = false;
  mocks.qaStore.count = 0;
  mocks.loadQaStore.mockReset();
  mocks.loadQaStore.mockImplementation(async () => {
    mocks.qaStore.loaded = true;
    mocks.qaStore.count = mocks.LOADED_COUNT;
  });
  mocks.synonymsLoad.mockClear();
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

  it("GET /api/v1/synonyms 只載入 synonyms，不觸發 loadQaStore", async () => {
    const res = await app.request("/api/v1/synonyms");

    expect(res.status).toBe(200);
    expect(mocks.synonymsLoad).toHaveBeenCalledTimes(1);
    expect(mocks.loadQaStore).not.toHaveBeenCalled();
  });

  it("initCore() 不觸發任何 store 載入", async () => {
    await initCore();

    expect(mocks.loadQaStore).not.toHaveBeenCalled();
    expect(mocks.synonymsLoad).not.toHaveBeenCalled();
  });
});

describe("需要 QA 的 endpoint 才 lazy 載入", () => {
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

  it("GET /api/v1/pipeline/status 觸發載入（前端 rawData 頁在用）", async () => {
    const res = await app.request("/api/v1/pipeline/status");

    expect(res.status).toBe(200);
    expect(mocks.loadQaStore).toHaveBeenCalledTimes(1);
  });

  it("GET /api/v1/pipeline/source-docs 觸發載入（前端 rawData 頁在用）", async () => {
    const res = await app.request("/api/v1/pipeline/source-docs");

    expect(res.status).toBe(200);
    expect(mocks.loadQaStore).toHaveBeenCalledTimes(1);
  });
});

describe("POST /api/v1/reports/generate 先載入再讀 count", () => {
  it("報告 meta 帶到載入後的 QA 筆數，而非 0", async () => {
    const genRes = await app.request("/api/v1/reports/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ snapshot_id: SNAPSHOT_ID }),
    });
    expect(genRes.status).toBe(200);
    expect(mocks.loadQaStore).toHaveBeenCalledTimes(1);

    const { data } = await genRes.json();
    const contentRes = await app.request(`/api/v1/reports/${data.date}`);
    const contentBody = await contentRes.json();

    // qaCount 若在 await 之前取值會是 0，報告會退成「知識庫」字樣
    expect(contentBody.data.content).toContain(`${mocks.LOADED_COUNT} Q&A`);
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
