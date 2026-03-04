import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock config
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

// Mock observability — not initialized
vi.mock("../../src/utils/observability.js", () => ({
  isLaminarInitialized: () => false,
  initLaminar: vi.fn(),
  observe: (_name: string, fn: Function) => fn,
  flushLaminar: vi.fn(),
  _resetForTest: vi.fn(),
}));

import { scoreEvent, scoreRagResponse } from "../../src/utils/laminar-scoring.js";

describe("laminar-scoring", () => {
  it("scoreEvent does not throw when Laminar not initialized", async () => {
    await expect(scoreEvent("test", 1.0)).resolves.toBeUndefined();
  });

  it("scoreRagResponse does not throw with valid inputs", async () => {
    await expect(
      scoreRagResponse("This is a long enough answer for testing purposes and more", [
        { score: 0.85 },
        { score: 0.72 },
      ]),
    ).resolves.toBeUndefined();
  });

  it("scoreRagResponse handles empty answer", async () => {
    await expect(scoreRagResponse("", [])).resolves.toBeUndefined();
  });

  it("scoreRagResponse handles sources without score", async () => {
    await expect(scoreRagResponse("short", [{}])).resolves.toBeUndefined();
  });
});
