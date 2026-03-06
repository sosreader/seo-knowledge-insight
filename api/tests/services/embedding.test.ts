/**
 * Tests for embedding.ts — OpenAI embedding wrapper.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../src/config.js", () => ({
  config: {
    OPENAI_API_KEY: "test-key",
    OPENAI_EMBEDDING_MODEL: "text-embedding-3-small",
    SUPABASE_URL: "",
    SUPABASE_ANON_KEY: "",
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

import { getEmbedding } from "../../src/services/embedding.js";

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
});
