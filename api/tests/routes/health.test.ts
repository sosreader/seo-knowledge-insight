import { describe, it, expect, vi } from "vitest";

// Mock config — ensure no OpenAI key so resolveHealthCapabilities tests are deterministic
vi.mock("../../src/config.js", () => ({
  config: {
    SEO_API_KEY: "",
    OPENAI_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
  },
  paths: {
    rootDir: "/tmp",
    outputDir: "/tmp/output",
    rawDataDir: "/tmp/raw_data",
    fetchLogsDir: "/tmp/output/fetch_logs",
    qaJsonPath: "/tmp/output/qa_final.json",
    qaEnrichedJsonPath: "/tmp/output/qa_enriched.json",
    qaEmbeddingsPath: "/tmp/output/qa_embeddings.npy",
    sessionsDir: "/tmp/output/sessions",
    scriptsDir: "/tmp/scripts",
    accessLogsDir: "/tmp/output/access_logs",
    evalsDir: "/tmp/output/evals",
  },
}));

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

  it("returns capabilities object", async () => {
    const res = await app.request("/health");
    const body = await res.json();
    expect(body.capabilities).toBeDefined();
    expect(body.capabilities.runtime).toMatch(/^(local-server|lambda)$/);
    expect(body.capabilities.llm).toMatch(/^(openai|claude-code|none)$/);
    expect(body.capabilities.store).toMatch(/^(supabase|file)$/);
    expect(body.capabilities.agent).toMatch(/^(enabled|disabled)$/);
  });

  it("returns llm claude-code when called with Claude Code User-Agent", async () => {
    const res = await app.request("/health", {
      headers: { "User-Agent": "claude-code/1.0" },
    });
    const body = await res.json();
    expect(body.capabilities.llm).toBe("claude-code");
    expect(body.capabilities.caller).toBe("claude-code");
  });

  it("returns llm none when called from browser", async () => {
    const res = await app.request("/health", {
      headers: { "User-Agent": "Mozilla/5.0" },
    });
    const body = await res.json();
    expect(body.capabilities.llm).toBe("none");
  });
});
