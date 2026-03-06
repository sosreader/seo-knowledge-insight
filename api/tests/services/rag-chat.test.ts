/**
 * Tests for rag-chat — RAG pipeline (embedding + search + GPT completion).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../src/config.js", () => ({
  config: {
    OPENAI_API_KEY: "test-key",
    OPENAI_EMBEDDING_MODEL: "text-embedding-3-small",
    CHAT_MODEL: "gpt-4o-mini",
    ANTHROPIC_API_KEY: "",
    CHAT_CONTEXT_K: 3,
    SUPABASE_URL: "",
    SUPABASE_ANON_KEY: "",
    SEO_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
  },
  paths: { outputDir: "/tmp" },
}));

const mockCreate = vi.fn();

vi.mock("openai", () => ({
  default: class OpenAI {
    embeddings = { create: vi.fn() };
    chat = { completions: { create: mockCreate } };
  },
}));

vi.mock("../../src/utils/observability.js", () => ({
  observe: (_name: string, fn: Function) => fn,
}));

vi.mock("../../src/utils/laminar-scoring.js", () => ({
  scoreRagResponse: vi.fn(),
}));

const mockGetEmbedding = vi.fn();
vi.mock("../../src/services/embedding.js", () => ({
  getEmbedding: (...args: unknown[]) => mockGetEmbedding(...args),
}));

const mockHybridSearch = vi.fn();
vi.mock("../../src/store/qa-store.js", () => ({
  qaStore: {
    hybridSearch: (...args: unknown[]) => mockHybridSearch(...args),
  },
}));

vi.mock("../../src/services/reranker.js", () => ({
  rerank: vi.fn((_query: string, hits: unknown[]) => hits),
}));

import { FAKE_ITEMS } from "../setup.js";

// Dynamic import to get the un-observed version
const { ragChat } = await import("../../src/services/rag-chat.js");

describe("ragChat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns answer from GPT with sources", async () => {
    mockGetEmbedding.mockResolvedValueOnce(new Float32Array([0.1, 0.2]));
    mockHybridSearch.mockResolvedValueOnce([
      { item: FAKE_ITEMS[0], score: 0.95 },
      { item: FAKE_ITEMS[1], score: 0.80 },
    ]);
    mockCreate.mockResolvedValueOnce({
      choices: [{ message: { content: "LCP measures loading performance." } }],
    });

    const result = await ragChat("What is LCP?");
    expect(result.answer).toBe("LCP measures loading performance.");
    expect(result.sources.length).toBe(2);
    expect(result.mode).toBe("full");
  });

  it("passes history to GPT when provided", async () => {
    mockGetEmbedding.mockResolvedValueOnce(new Float32Array([0.1]));
    mockHybridSearch.mockResolvedValueOnce([]);
    mockCreate.mockResolvedValueOnce({
      choices: [{ message: { content: "Follow-up answer" } }],
    });

    const history = [
      { role: "user" as const, content: "Previous question" },
      { role: "assistant" as const, content: "Previous answer" },
    ];
    const result = await ragChat("Follow-up question", history);
    expect(result.answer).toBe("Follow-up answer");

    const callArgs = mockCreate.mock.calls[0]![0];
    expect(callArgs.messages.length).toBeGreaterThan(2);
  });

  it("handles empty GPT response", async () => {
    mockGetEmbedding.mockResolvedValueOnce(new Float32Array([0.1]));
    mockHybridSearch.mockResolvedValueOnce([]);
    mockCreate.mockResolvedValueOnce({
      choices: [{ message: { content: null } }],
    });

    const result = await ragChat("test");
    expect(result.answer).toBe("");
  });
});
