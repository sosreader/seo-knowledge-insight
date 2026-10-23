/**
 * 容器模式（AUTH_MODE=cf-access）且 RAG_AUDS 已回填：index.ts 的接線。
 *   - /internal/rag/* 與 /api/v1/* 共用同一組路由與同一個驗證
 *   - 沒帶或帶錯 token → 401；正確 token → 進到路由（這裡用 /reports 的 410 證明已通過驗證）
 */

import { describe, it, expect, vi, beforeAll, afterAll } from "vitest";
import type { Hono } from "hono";
import { mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { generateKeyPair, exportJWK, SignJWT, type CryptoKey, type JWK } from "jose";

const TEAM = vi.hoisted(() => "vocus-test.cloudflareaccess.com");

const tmpDir = mkdtempSync(join(tmpdir(), "cf-access-configured-"));

vi.mock("../src/config.js", () => ({
  config: {
    SEO_API_KEY: "",
    AUTH_MODE: "cf-access",
    CF_ACCESS_TEAM_DOMAIN: TEAM,
    RAG_AUDS: "rag-aud-1",
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
let privateKey: CryptoKey;
let jwk: JWK;
const originalFetch = globalThis.fetch;

async function token(aud: string): Promise<string> {
  return new SignJWT({ sub: "user-1" })
    .setProtectedHeader({ alg: "RS256", kid: "k1" })
    .setIssuer(`https://${TEAM}`)
    .setAudience(aud)
    .setExpirationTime("5m")
    .sign(privateKey);
}

beforeAll(async () => {
  vi.spyOn(console, "warn").mockImplementation(() => undefined);
  vi.spyOn(console, "log").mockImplementation(() => undefined);
  vi.spyOn(console, "error").mockImplementation(() => undefined);
  const pair = await generateKeyPair("RS256", { extractable: true });
  privateKey = pair.privateKey;
  jwk = { ...(await exportJWK(pair.publicKey)), kid: "k1", alg: "RS256" };
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === `https://${TEAM}/cdn-cgi/access/certs`) {
      return new Response(JSON.stringify({ keys: [jwk] }), { status: 200 });
    }
    return originalFetch(input);
  }) as typeof fetch;
  app = (await import("../src/index.js")).app as unknown as Hono;
});

afterAll(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("container mode with RAG_AUDS configured", () => {
  it("rejects requests without a token", async () => {
    expect((await app.request("/internal/rag/reports")).status).toBe(401);
    expect((await app.request("/api/v1/reports")).status).toBe(401);
  });

  it("rejects a token minted for another AUD", async () => {
    const res = await app.request("/internal/rag/reports", {
      headers: { "Cf-Access-Jwt-Assertion": await token("api-aud") },
    });
    expect(res.status).toBe(401);
  });

  it("lets a valid token through on both prefixes", async () => {
    for (const path of ["/internal/rag/reports", "/api/v1/reports"]) {
      const res = await app.request(path, {
        headers: { "Cf-Access-Jwt-Assertion": await token("rag-aud-1") },
      });
      expect(res.status).toBe(410);
    }
  });

  it("ignores X-API-Key in container mode", async () => {
    const res = await app.request("/internal/rag/reports", { headers: { "X-API-Key": "anything" } });
    expect(res.status).toBe(401);
  });
});
