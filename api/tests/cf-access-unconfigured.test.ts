/**
 * 容器模式（AUTH_MODE=cf-access）且 RAG_AUDS 尚未回填（S2.4 之前的部署狀態）：
 *   - /health 照常 200（readiness 不受影響）
 *   - /api/v1/* 與 /internal/rag/* 全部 503 {"error":"unavailable"}，fail closed
 */

import { describe, it, expect, vi, beforeAll, afterAll } from "vitest";
import type { Hono } from "hono";
import { mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const TEAM = vi.hoisted(() => "vocus-test.cloudflareaccess.com");

const tmpDir = mkdtempSync(join(tmpdir(), "cf-access-unconfigured-"));

vi.mock("../src/config.js", () => ({
  config: {
    SEO_API_KEY: "",
    AUTH_MODE: "cf-access",
    CF_ACCESS_TEAM_DOMAIN: TEAM,
    RAG_AUDS: "",
    RATE_LIMIT_CHAT_DAILY: 1000,
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
  vi.spyOn(console, "error").mockImplementation(() => undefined);
  app = (await import("../src/index.js")).app as unknown as Hono;
});

afterAll(() => {
  vi.restoreAllMocks();
});

describe("container mode with RAG_AUDS empty", () => {
  it("keeps /health public", async () => {
    expect((await app.request("/health")).status).toBe(200);
  });

  it.each(["/internal/rag/qa", "/internal/rag/sessions", "/api/v1/qa", "/api/v1/pipeline/status"])(
    "GET %s → 503 unavailable",
    async (path) => {
      const res = await app.request(path);
      expect(res.status).toBe(503);
      expect(((await res.json()) as { error: string }).error).toBe("unavailable");
    },
  );
});
