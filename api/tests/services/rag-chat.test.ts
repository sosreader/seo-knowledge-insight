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

const mockRecordMiss = vi.fn();
vi.mock("../../src/store/learning-store.js", () => ({
  recordMiss: (...args: unknown[]) => mockRecordMiss(...args),
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
    expect(result.mode).toBe("rag");
  });

  it("passes history to GPT when provided", async () => {
    mockGetEmbedding.mockResolvedValueOnce(new Float32Array([0.1]));
    mockHybridSearch.mockResolvedValueOnce([
      { item: FAKE_ITEMS[0], score: 0.7 },
    ]);
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
    mockHybridSearch.mockResolvedValueOnce([
      { item: FAKE_ITEMS[0], score: 0.65 },
    ]);
    mockCreate.mockResolvedValueOnce({
      choices: [{ message: { content: null } }],
    });

    const result = await ragChat("test");
    expect(result.answer).toBe("");
  });

  describe("retrieval quality gate", () => {
    it("returns context-only when retrieval quality is incorrect (score < 0.4)", async () => {
      mockGetEmbedding.mockResolvedValueOnce(new Float32Array([0.1]));
      mockHybridSearch.mockResolvedValueOnce([
        { item: FAKE_ITEMS[0], score: 0.3 },
      ]);

      const result = await ragChat("completely unrelated query");
      expect(result.mode).toBe("context-only");
      expect(result.answer).toBeNull();
      expect(result.metadata?.retrieval_quality).toBe("incorrect");
      expect(mockCreate).not.toHaveBeenCalled();
      expect(mockRecordMiss).toHaveBeenCalledWith({
        query: "completely unrelated query",
        top_score: 0.3,
        context: "rag-chat",
      });
    });

    it("returns context-only when no hits at all", async () => {
      mockGetEmbedding.mockResolvedValueOnce(new Float32Array([0.1]));
      mockHybridSearch.mockResolvedValueOnce([]);

      const result = await ragChat("no results query");
      expect(result.mode).toBe("context-only");
      expect(result.answer).toBeNull();
      expect(result.metadata?.retrieval_quality).toBe("incorrect");
      expect(mockCreate).not.toHaveBeenCalled();
    });

    it("appends disclaimer for ambiguous retrieval (0.4 <= score < 0.6)", async () => {
      mockGetEmbedding.mockResolvedValueOnce(new Float32Array([0.1]));
      mockHybridSearch.mockResolvedValueOnce([
        { item: FAKE_ITEMS[0], score: 0.5 },
      ]);
      mockCreate.mockResolvedValueOnce({
        choices: [{ message: { content: "Some answer based on limited data." } }],
      });

      const result = await ragChat("ambiguous query");
      expect(result.mode).toBe("rag");
      expect(result.answer).toContain("Some answer based on limited data.");
      expect(result.answer).toContain("注意：以上回答基於相似度較低的知識庫結果");
      expect(result.metadata?.retrieval_quality).toBe("ambiguous");
    });

    it("proceeds normally for correct retrieval (score >= 0.6)", async () => {
      mockGetEmbedding.mockResolvedValueOnce(new Float32Array([0.1]));
      mockHybridSearch.mockResolvedValueOnce([
        { item: FAKE_ITEMS[0], score: 0.85 },
      ]);
      mockCreate.mockResolvedValueOnce({
        choices: [{ message: { content: "Confident answer [1]." } }],
      });

      const result = await ragChat("well-matched query");
      expect(result.mode).toBe("rag");
      expect(result.answer).toBe("Confident answer [1].");
      expect(result.answer).not.toContain("注意：以上回答基於相似度較低的知識庫結果");
      expect(result.metadata?.retrieval_quality).toBe("correct");
    });
  });

  describe("inline citation", () => {
    it("tracks citation count in metadata", async () => {
      mockGetEmbedding.mockResolvedValueOnce(new Float32Array([0.1]));
      mockHybridSearch.mockResolvedValueOnce([
        { item: FAKE_ITEMS[0], score: 0.9 },
        { item: FAKE_ITEMS[1], score: 0.8 },
      ]);
      mockCreate.mockResolvedValueOnce({
        choices: [{ message: { content: "LCP [1] and title tags [2] are important." } }],
      });

      const result = await ragChat("SEO basics");
      expect(result.metadata?.citation_count).toBe(2);
    });

    it("reports zero citations when answer has none", async () => {
      mockGetEmbedding.mockResolvedValueOnce(new Float32Array([0.1]));
      mockHybridSearch.mockResolvedValueOnce([
        { item: FAKE_ITEMS[0], score: 0.75 },
      ]);
      mockCreate.mockResolvedValueOnce({
        choices: [{ message: { content: "General SEO advice." } }],
      });

      const result = await ragChat("general question");
      expect(result.metadata?.citation_count).toBe(0);
    });
  });
});
