import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock config with no LMNR key
vi.mock("../../src/config.js", () => ({
  config: {
    OPENAI_API_KEY: "",
    SEO_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
    CHAT_CONTEXT_K: 5,
    OPENAI_MODEL: "gpt-5.2",
    OPENAI_EMBEDDING_MODEL: "text-embedding-3-small",
    LMNR_PROJECT_API_KEY: "",
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

import {
  initLaminar,
  observe,
  flushLaminar,
  isLaminarInitialized,
  _resetForTest,
} from "../../src/utils/observability.js";

describe("observability", () => {
  beforeEach(() => {
    _resetForTest();
  });

  it("initLaminar skips when no API key", async () => {
    await initLaminar();
    expect(isLaminarInitialized()).toBe(false);
  });

  it("observe returns original function result when not initialized", async () => {
    const fn = async (x: number) => x * 2;
    const observed = observe("test_span", fn);
    const result = await observed(21);
    expect(result).toBe(42);
  });

  it("observe preserves function arguments", async () => {
    const fn = async (a: string, b: number) => `${a}-${b}`;
    const observed = observe("test", fn);
    expect(await observed("hello", 5)).toBe("hello-5");
  });

  it("flushLaminar does not throw when not initialized", async () => {
    await expect(flushLaminar()).resolves.toBeUndefined();
  });

  it("isLaminarInitialized returns false by default", () => {
    expect(isLaminarInitialized()).toBe(false);
  });

  it("initLaminar skips on Lambda environment even with API key", async () => {
    // Temporarily set Lambda env var
    process.env.AWS_LAMBDA_FUNCTION_NAME = "seo-insight-api";
    // Override the mocked config to have a key
    const { config } = await import("../../src/config.js");
    const original = config.LMNR_PROJECT_API_KEY;
    (config as Record<string, unknown>).LMNR_PROJECT_API_KEY = "test-key";

    await initLaminar();
    expect(isLaminarInitialized()).toBe(false);

    // Cleanup
    delete process.env.AWS_LAMBDA_FUNCTION_NAME;
    (config as Record<string, unknown>).LMNR_PROJECT_API_KEY = original;
  });
});
