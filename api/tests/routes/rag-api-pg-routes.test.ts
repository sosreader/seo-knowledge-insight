/**
 * rag-api 線上組態（PG 模式、沒有 OPENAI_API_KEY、沒有 LLM_BASE_URL）的整條路由行為，
 * 以 warehouse_rag 連 testcontainers 的 VW schema（權限與正式環境相同）。
 *
 *   - LLM 類（chat、sessions/:id/messages、search hybrid／semantic）→ 501 llm_disabled
 *   - search 未指定模式 → keyword，data／meta 標 llm_disabled，命中後 search_hit_count +1
 *   - feedback、synonyms、metrics snapshot 寫入後讀回 DB
 *   - pipeline 觸發與本機檔案路由 → 501 run_locally；status、source-docs 由表推導
 */
import { describe, it, expect, vi, beforeAll, afterAll, beforeEach } from "vitest";
import type { Hono } from "hono";
import { pgAvailable, usePgFixture } from "../pg/pg-fixture.js";
import { axisVector, seedQa } from "../pg/qa-seed.js";

// pg-fixture 靜態 import 會先載入 config mock，tmpDir 必須在 hoisted 區塊建立
const { tmpDir, join } = await vi.hoisted(async () => {
  const fs = await import("node:fs");
  const path = await import("node:path");
  const os = await import("node:os");
  return { tmpDir: fs.mkdtempSync(path.join(os.tmpdir(), "rag-api-pg-routes-")), join: path.join };
});

vi.mock("../../src/config.js", () => ({
  config: {
    SEO_API_KEY: "",
    AUTH_MODE: "api-key",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_CHAT_DAILY: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
    CHAT_CONTEXT_K: 5,
    CHAT_MODEL: "gpt-test",
    OPENAI_EMBEDDING_MODEL: "text-embedding-3-small",
    OPENAI_API_KEY: "",
    LLM_BASE_URL: "",
    AGENT_ENABLED: "auto",
    // 非空 → hasPg() 為真；實際連線由 pg fixture 的 test override 指向容器
    VW_DB_SECRET_FILE_RAG: join(tmpDir, "db-rag-overridden-by-fixture"),
    PGSSLROOTCERT: join(tmpDir, "no-ca.pem"),
  },
  paths: {
    rootDir: tmpDir,
    outputDir: tmpDir,
    rawDataDir: join(tmpDir, "raw_data"),
    sessionsDir: join(tmpDir, "sessions"),
    scriptsDir: join(tmpDir, "scripts"),
    metricsSnapshotsDir: join(tmpDir, "metrics_snapshots"),
    synonymCustomJsonPath: join(tmpDir, "synonym_custom.json"),
    qaJsonPath: join(tmpDir, "qa_final.json"),
    qaEmbeddingsPath: join(tmpDir, "qa_embeddings.npy"),
    qaEnrichedJsonPath: join(tmpDir, "qa_enriched.json"),
    qaPerArticleDir: join(tmpDir, "qa_per_article"),
    accessLogsDir: join(tmpDir, "access_logs"),
    fetchLogsDir: join(tmpDir, "fetch_logs"),
    evalsDir: join(tmpDir, "evals"),
  },
}));

const fx = usePgFixture("routes");

const QA_ROWS = [
  { id: "00000000000000a1", seq: 1, question: "What is LCP?", category: "Performance", keywords: ["LCP"], embedding: axisVector(0) },
  { id: "00000000000000a2", seq: 2, question: "How to write title tags?", category: "On-Page", keywords: ["title tag"], embedding: axisVector(1) },
];
const SESSION_ID = "00000000-0000-4000-8000-0000000000aa";

let app: Hono;

async function call(method: string, path: string, body?: unknown) {
  const res = await app.request(`/internal/rag${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  const json = (await res.json()) as Record<string, any>;
  return { status: res.status, json };
}

async function waitFor(check: () => Promise<boolean>, tries = 40): Promise<boolean> {
  for (let i = 0; i < tries; i++) {
    if (await check()) return true;
    await new Promise((r) => setTimeout(r, 50));
  }
  return false;
}

describe.skipIf(!pgAvailable)("rag-api routes with LLM disabled (PG mode, warehouse_rag)", () => {
  beforeAll(async () => {
    vi.spyOn(console, "log").mockImplementation(() => undefined);
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
    await seedQa(fx.admin(), QA_ROWS);
    app = (await import("../../src/index.js")).app as unknown as Hono;
  });

  beforeEach(() => fx.activate());

  afterAll(() => {
    vi.unstubAllGlobals();
  });

  describe("llm_disabled", () => {
    it.each([
      ["POST", "/chat", { message: "LCP" }],
      ["POST", "/chat/stream", { message: "LCP" }],
      ["POST", "/search", { query: "LCP", mode: "hybrid" }],
      ["POST", "/search", { query: "LCP", mode: "semantic" }],
    ])("%s %s %j → 501 llm_disabled", async (method, path, body) => {
      const { status, json } = await call(method, path, body);
      expect(status).toBe(501);
      expect(json.error).toBe("llm_disabled");
      expect(json.message).toBe("線上未啟用 LLM，請在本機模式執行");
    });

    it("POST /sessions/:id/messages → 501 and does not persist the user message", async () => {
      await fx.admin().query(
        `INSERT INTO app_session (id, title, messages, content_hash) VALUES ($1, 't', '[]'::jsonb, 'seed')
           ON CONFLICT (id) DO NOTHING`,
        [SESSION_ID],
      );
      const { status, json } = await call("POST", `/sessions/${SESSION_ID}/messages`, { message: "LCP" });
      expect(status).toBe(501);
      expect(json.error).toBe("llm_disabled");
      const { rows } = await fx.admin().query("SELECT messages FROM app_session WHERE id = $1", [SESSION_ID]);
      expect(rows[0].messages).toEqual([]);
    });

    it("session reads and soft delete keep working", async () => {
      expect((await call("GET", "/sessions")).status).toBe(200);
      expect((await call("GET", `/sessions/${SESSION_ID}`)).status).toBe(200);
      expect((await call("DELETE", `/sessions/${SESSION_ID}`)).status).toBe(200);
      const { rows } = await fx.admin().query("SELECT deleted_at FROM app_session WHERE id = $1", [SESSION_ID]);
      expect(rows[0].deleted_at).not.toBeNull();
    });
  });

  describe("search keyword fallback", () => {
    it("no mode → keyword with llm_disabled flag in data and meta, then bumps search_hit_count", async () => {
      const { status, json } = await call("POST", "/search", { query: "LCP" });
      expect(status).toBe(200);
      expect(json.data.mode).toBe("keyword");
      expect(json.data.llm_disabled).toBe(true);
      expect(json.meta.mode).toBe("keyword");
      expect(json.meta.llm_disabled).toBe(true);
      expect(json.data.results.map((r: { id: string }) => r.id)).toContain("00000000000000a1");

      const bumped = await waitFor(async () => {
        const { rows } = await fx
          .admin()
          .query("SELECT search_hit_count FROM app_qa_item WHERE id = '00000000000000a1'");
        return Number(rows[0].search_hit_count) > 0;
      });
      expect(bumped).toBe(true);
    });

    it("explicit keyword mode → 200 keyword", async () => {
      const { status, json } = await call("POST", "/search", { query: "title", mode: "keyword" });
      expect(status).toBe(200);
      expect(json.data.mode).toBe("keyword");
    });
  });

  describe("feedback write and read-back", () => {
    it("POST /feedback inserts into app_learning and returns the stored row", async () => {
      const { status, json } = await call("POST", "/feedback", {
        query: "LCP 怎麼改善",
        qa_id: "00000000000000a1",
        feedback: "not_relevant",
        feedback_category: "outdated",
        top_score: 0.5,
      });
      expect(status).toBe(200);
      expect(json.data.recorded).toBe(true);
      expect(json.data.id).toMatch(/^\d+$/);
      expect(json.data.created_at).toBeTruthy();
      const { rows } = await fx
        .admin()
        .query("SELECT type, query, qa_id, feedback, top_score FROM app_learning WHERE id = $1", [json.data.id]);
      expect(rows).toEqual([
        { type: "feedback", query: "LCP 怎麼改善", qa_id: "00000000000000a1", feedback: "not_relevant", top_score: 0.5 },
      ]);
    });
  });

  describe("synonyms write and read-back", () => {
    it("POST → PUT → DELETE round-trips through app_synonym_custom", async () => {
      const created = await call("POST", "/synonyms", { term: "測試詞", synonyms: ["a", "b"] });
      expect(created.status).toBe(201);
      expect(created.json.data).toEqual({ term: "測試詞", synonyms: ["a", "b"], source: "custom" });
      let rows = (await fx.admin().query("SELECT synonyms FROM app_synonym_custom WHERE term = '測試詞'")).rows;
      expect(rows[0].synonyms).toEqual(["a", "b"]);

      const dup = await call("POST", "/synonyms", { term: "測試詞", synonyms: ["c"] });
      expect(dup.status).toBe(409);

      const updated = await call("PUT", `/synonyms/${encodeURIComponent("測試詞")}`, { synonyms: ["c"] });
      expect(updated.status).toBe(200);
      expect(updated.json.data.synonyms).toEqual(["c"]);
      rows = (await fx.admin().query("SELECT synonyms FROM app_synonym_custom WHERE term = '測試詞'")).rows;
      expect(rows[0].synonyms).toEqual(["c"]);

      const listed = await call("GET", "/synonyms");
      expect(listed.json.data.find((i: { term: string }) => i.term === "測試詞")?.synonyms).toEqual(["c"]);

      const deleted = await call("DELETE", `/synonyms/${encodeURIComponent("測試詞")}`);
      expect(deleted.status).toBe(200);
      rows = (await fx.admin().query("SELECT 1 FROM app_synonym_custom WHERE term = '測試詞'")).rows;
      expect(rows).toHaveLength(0);
      expect((await call("DELETE", `/synonyms/${encodeURIComponent("測試詞")}`)).status).toBe(404);
    });
  });

  describe("metrics snapshots", () => {
    it("save → list → soft delete → 404 on second delete", async () => {
      const saved = await call("POST", "/pipeline/metrics/save", {
        metrics: { CTR: { latest: 1.2 } },
        maturity: { L1: "ok" },
        source: "sheets",
        tab: "weekly",
        label: "W43",
        weeks: 1,
      });
      expect(saved.status).toBe(201);
      const id = saved.json.data.id as string;
      expect(saved.json.data.label).toBe("W43");
      const { rows } = await fx
        .admin()
        .query("SELECT label, metrics, deleted_at FROM app_metrics_snapshot WHERE id = $1", [id]);
      expect(rows[0]).toMatchObject({ label: "W43", metrics: { CTR: { latest: 1.2 } }, deleted_at: null });

      const listed = await call("GET", "/pipeline/metrics/snapshots");
      expect(listed.json.data.items.map((s: { id: string }) => s.id)).toContain(id);
      expect((await call("GET", "/pipeline/metrics/trends")).status).toBe(200);

      const del = await call("DELETE", `/pipeline/metrics/snapshots/${id}`);
      expect(del.status).toBe(200);
      const after = await fx.admin().query("SELECT deleted_at FROM app_metrics_snapshot WHERE id = $1", [id]);
      expect(after.rows[0].deleted_at).not.toBeNull();
      expect((await call("DELETE", `/pipeline/metrics/snapshots/${id}`)).status).toBe(404);
    });

    it("POST /pipeline/metrics fetches the Google Sheet (no LLM, no DB)", async () => {
      const fetchMock = vi.fn(async () => new Response("指標\t上週\t本週\nCTR\t1.0\t1.2\n", { status: 200 }));
      vi.stubGlobal("fetch", fetchMock);
      try {
        const { status, json } = await call("POST", "/pipeline/metrics", {
          source: "https://docs.google.com/spreadsheets/d/abcdefghijklmnopqrstuvwxyz0123456789/edit#gid=123",
          tab: "vocus",
        });
        expect(status).toBe(200);
        expect(typeof json.data.total_metrics).toBe("number");
        expect(String(fetchMock.mock.calls[0]?.[0])).toContain("docs.google.com");
      } finally {
        vi.unstubAllGlobals();
      }
    });

    it("POST /pipeline/crawled-not-indexed analyses raw TSV without touching tables", async () => {
      const raw_tsv = ["路徑\t上週\t本週", "/article\t100\t150", "/tags\t50\t40"].join("\n");
      const { status, json } = await call("POST", "/pipeline/crawled-not-indexed", { raw_tsv });
      expect(status).toBe(200);
      expect(json.data).toHaveProperty("insight");
      expect(json.data).toHaveProperty("markdown");
    });
  });

  describe("pipeline", () => {
    it.each([
      ["POST", "/pipeline/fetch"],
      ["POST", "/pipeline/extract-qa"],
      ["POST", "/pipeline/dedupe-classify"],
      ["POST", "/pipeline/fetch-articles"],
      ["GET", "/pipeline/logs"],
      ["GET", "/pipeline/meetings"],
      ["GET", "/pipeline/meetings/00000000-0000-4000-8000-000000000001/preview"],
      ["GET", "/pipeline/unprocessed"],
      ["GET", "/pipeline/source-docs/seo-meetings/a.md/preview"],
    ])("%s %s → 501 run_locally", async (method, path) => {
      const { status, json } = await call(method, path, method === "POST" ? {} : undefined);
      expect(status).toBe(501);
      expect(json.error).toBe("run_locally");
      expect(json.message).toBe("此流程在本機執行，請用 make pipeline");
    });

    it("GET /pipeline/status → 200", async () => {
      expect((await call("GET", "/pipeline/status")).status).toBe(200);
    });

    it("GET /pipeline/source-docs derives the list from app_qa_item", async () => {
      const { status, json } = await call("GET", "/pipeline/source-docs");
      expect(status).toBe(200);
      expect(json.data.total).toBeGreaterThan(0);
      expect(json.data.items.every((d: { is_processed: boolean }) => d.is_processed)).toBe(true);
    });

    it("GET /pipeline/llm-usage → 200 with no rows when nothing called an LLM", async () => {
      const { status } = await call("GET", "/pipeline/llm-usage");
      expect(status).toBe(200);
      const { rows } = await fx.admin().query("SELECT count(*)::int AS n FROM app_llm_usage");
      expect(rows[0].n).toBe(0);
    });
  });

  it("reports stay 410 in rag-api", async () => {
    const { status, json } = await call("GET", "/reports");
    expect(status).toBe(410);
    expect(json.error).toBe("not_available_in_rag_api");
  });
});
