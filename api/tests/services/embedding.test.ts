/**
 * Tests for embedding.ts — OpenAI embedding wrapper.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../src/config.js", () => ({
  config: {
    OPENAI_API_KEY: "test-key",
    OPENAI_EMBEDDING_MODEL: "text-embedding-3-small",
    VW_DB_SECRET_FILE_RAG: "",
    SEO_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
    CHAT_CONTEXT_K: 5,
  },
  paths: { outputDir: "/tmp" },
}));

const mockCreate = vi.fn();

vi.mock("openai", () => ({
  default: class OpenAI {
    embeddings = { create: mockCreate };
  },
}));

vi.mock("../../src/utils/observability.js", () => ({
  observe: (_name: string, fn: Function) => fn,
}));

const mockLogUsage = vi.fn();
vi.mock("../../src/utils/llm-usage-logger.js", () => ({
  logLLMUsage: (...args: unknown[]) => mockLogUsage(...args),
}));

import { getEmbedding } from "../../src/services/embedding.js";
import { config } from "../../src/config.js";

describe("getEmbedding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns L2-normalized Float32Array", async () => {
    // Return a simple 3D embedding
    mockCreate.mockResolvedValueOnce({
      data: [{ embedding: [3, 4, 0] }],
    });

    const result = await getEmbedding("test query");
    expect(result).toBeInstanceOf(Float32Array);
    expect(result.length).toBe(3);

    // Check L2 normalization: magnitude should be ~1
    const magnitude = Math.sqrt(
      result[0]! ** 2 + result[1]! ** 2 + result[2]! ** 2,
    );
    expect(magnitude).toBeCloseTo(1.0, 4);
  });

  it("trims input text", async () => {
    mockCreate.mockResolvedValueOnce({
      data: [{ embedding: [1, 0] }],
    });

    await getEmbedding("  test  ");
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({ input: "test" }),
    );
  });

  it("logs app_llm_usage for the embedding call", async () => {
    mockCreate.mockResolvedValueOnce({
      data: [{ embedding: [1, 0, 0] }],
      model: "text-embedding-3-small",
      usage: { prompt_tokens: 7 },
    });
    await getEmbedding("LCP");
    expect(mockLogUsage).toHaveBeenCalledWith(
      expect.objectContaining({ endpoint: "embedding", model: "text-embedding-3-small", input_tokens: 7, output_tokens: 0 }),
    );
  });

  it("uses LLM_EMBEDDING_MODEL when set (local Ollama)", async () => {
    const mutable = config as Record<string, unknown>;
    mutable.LLM_EMBEDDING_MODEL = "nomic-embed-text";
    mockCreate.mockResolvedValueOnce({ data: [{ embedding: [1, 0] }] });
    try {
      await getEmbedding("LCP");
      expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({ model: "nomic-embed-text" }));
    } finally {
      mutable.LLM_EMBEDDING_MODEL = "";
    }
  });

  it("throws llm_disabled without calling the API when no LLM is configured", async () => {
    const mutable = config as Record<string, unknown>;
    const original = mutable.OPENAI_API_KEY;
    mutable.OPENAI_API_KEY = "";
    try {
      await expect(getEmbedding("LCP")).rejects.toMatchObject({ code: "llm_disabled", status: 501 });
      expect(mockCreate).not.toHaveBeenCalled();
      expect(mockLogUsage).not.toHaveBeenCalled();
    } finally {
      mutable.OPENAI_API_KEY = original;
    }
  });
});
