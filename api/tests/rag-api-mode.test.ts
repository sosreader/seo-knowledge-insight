/**
 * rag-api（PG 模式）整個 app 的行為：VW_DB_SECRET_FILE_RAG 有設但 secret 檔不在（例如 Secret 尚未建立）。
 *   - app 照常啟動，/health 200 且 capabilities.store = postgres
 *   - 需要 DB 的路由回 503 db_unavailable（不是 500、不是 crash）
 *   - /reports、/meeting-prep 回 410 not_available_in_rag_api（warehouse_rag 沒有這兩表的權限）
 *   - 沒有 OPENAI_API_KEY／LLM_BASE_URL → /chat 先回 501 llm_disabled（不等 QA store）
 */

import { describe, it, expect, vi, beforeAll } from "vitest";
import type { Hono } from "hono";
import { mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const tmpDir = mkdtempSync(join(tmpdir(), "rag-api-mode-"));

vi.mock("../src/config.js", () => ({
  config: {
    SEO_API_KEY: "",
    AUTH_MODE: "api-key",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
    CHAT_CONTEXT_K: 5,
    OPENAI_API_KEY: "",
    AGENT_ENABLED: false,
    VW_DB_SECRET_FILE_RAG: join(tmpDir, "db-rag-not-mounted"),
    PGSSLROOTCERT: join(tmpDir, "no-ca.pem"),
  },
  paths: {
    rootDir: tmpDir,
    outputDir: tmpDir,
    sessionsDir: join(tmpDir, "sessions"),
    scriptsDir: join(tmpDir, "scripts"),
    metricsSnapshotsDir: join(tmpDir, "metrics_snapshots"),
    synonymCustomJsonPath: join(tmpDir, "synonym_custom.json"),
    qaJsonPath: join(tmpDir, "qa_final.json"),
    qaEmbeddingsPath: join(tmpDir, "qa_embeddings.npy"),
    qaEnrichedJsonPath: join(tmpDir, "qa_enriched.json"),
    accessLogsDir: join(tmpDir, "access_logs"),
    fetchLogsDir: join(tmpDir, "fetch_logs"),
  },
}));

let app: Hono;

beforeAll(async () => {
  vi.spyOn(console, "warn").mockImplementation(() => undefined);
  vi.spyOn(console, "log").mockImplementation(() => undefined);
  app = (await import("../src/index.js")).app as unknown as Hono;
});

async function call(method: string, path: string, body?: unknown) {
  const res = await app.request(path, {
    method,
    headers: { "Content-Type": "application/json" },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  return { status: res.status, json: (await res.json()) as { error: string | null } };
}

describe("rag-api mode without a mounted db-rag secret", () => {
  it("boots and reports the postgres backend on /health", async () => {
    const res = await app.request("/health");
    expect(res.status).toBe(200);
    const json = (await res.json()) as { capabilities: { store: string } };
    expect(json.capabilities.store).toBe("postgres");
  });

  it.each([
    ["GET", "/api/v1/sessions"],
    ["POST", "/api/v1/sessions"],
    ["GET", "/api/v1/sessions/00000000-0000-4000-8000-000000000000"],
    ["DELETE", "/api/v1/sessions/00000000-0000-4000-8000-000000000000"],
    ["GET", "/api/v1/pipeline/metrics/snapshots"],
    ["DELETE", "/api/v1/pipeline/metrics/snapshots/20260101-000000"],
    ["GET", "/api/v1/pipeline/llm-usage"],
    ["GET", "/api/v1/pipeline/metrics/trends"],
  ])("%s %s → 503 db_unavailable", async (method, path) => {
    const { status, json } = await call(method, path, method === "POST" ? {} : undefined);
    expect(status).toBe(503);
    expect(json.error).toBe("db_unavailable");
  });

  it("POST /pipeline/metrics/save → 503 db_unavailable", async () => {
    const { status, json } = await call("POST", "/api/v1/pipeline/metrics/save", {
      metrics: { CTR: { latest: 1 } },
      source: "sheets",
      tab: "weekly",
      label: "w",
      weeks: 1,
    });
    expect(status).toBe(503);
    expect(json.error).toBe("db_unavailable");
  });

  it.each([
    ["GET", "/api/v1/qa", undefined],
    ["POST", "/api/v1/search", { query: "LCP" }],
  ])("%s %s reports the degraded QA store with 503 (not 500)", async (method, path, body) => {
    const { status } = await call(method, path, body);
    expect(status).toBe(503);
  });

  it("POST /api/v1/chat → 501 llm_disabled before waiting for the QA store", async () => {
    const { status, json } = await call("POST", "/api/v1/chat", { message: "LCP" });
    expect(status).toBe(501);
    expect(json.error).toBe("llm_disabled");
  });

  it("POST /synonyms → 503 db_unavailable", async () => {
    const { status, json } = await call("POST", "/api/v1/synonyms", { term: "lcp", synonyms: ["largest contentful paint"] });
    expect(status).toBe(503);
    expect(json.error).toBe("db_unavailable");
  });

  it.each([
    ["GET", "/api/v1/reports"],
    ["GET", "/api/v1/reports/20260101"],
    ["GET", "/api/v1/reports/20260101/metrics"],
    ["POST", "/api/v1/reports/generate"],
    ["GET", "/api/v1/meeting-prep"],
    ["GET", "/api/v1/meeting-prep/maturity-trend"],
    ["GET", "/api/v1/meeting-prep/20260101"],
  ])("%s %s → 410 not_available_in_rag_api", async (method, path) => {
    const { status, json } = await call(method, path, method === "POST" ? {} : undefined);
    expect(status).toBe(410);
    expect(json.error).toBe("not_available_in_rag_api");
  });
});
