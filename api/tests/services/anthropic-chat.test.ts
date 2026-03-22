import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../src/config.js", () => ({
  config: {
    ANTHROPIC_API_KEY: "sk-ant-test",
    CHAT_LLM_PROVIDER: "anthropic",
    CHAT_ANTHROPIC_MODEL: "claude-sonnet-4-5",
    OPENAI_API_KEY: "",
    OPENAI_EMBEDDING_MODEL: "text-embedding-3-small",
    CHAT_CONTEXT_K: 5,
  },
}));

const mockCreate = vi.fn();
vi.mock("@anthropic-ai/sdk", () => ({
  default: class MockAnthropic {
    messages = { create: mockCreate };
  },
}));

vi.mock("../../src/store/qa-store.js", () => ({
  qaStore: {
    loaded: true,
    count: 10,
    keywordSearch: vi.fn(() => [
      {
        item: {
          id: "abc123def456",
          question: "What is SEO?",
          answer: "Search Engine Optimization",
          category: "basics",
          source_title: "Meeting 1",
          source_date: "2024-05-02",
          source_type: "meeting",
          source_collection: "seo-meetings",
          source_url: "",
          evergreen: true,
        },
        score: 0.8,
      },
    ]),
    hybridSearch: vi.fn(() => [
      {
        item: {
          id: "abc123def456",
          question: "What is SEO?",
          answer: "Search Engine Optimization",
          category: "basics",
          source_title: "Meeting 1",
          source_date: "2024-05-02",
          source_type: "meeting",
          source_collection: "seo-meetings",
          source_url: "",
          evergreen: true,
        },
        score: 0.8,
      },
    ]),
  },
}));

vi.mock("../../src/services/reranker.js", () => ({
  rerank: vi.fn((_q: string, hits: unknown[]) => hits),
}));

vi.mock("../../src/utils/observability.js", () => ({
  observe: (_name: string, fn: Function) => fn,
}));

vi.mock("../../src/utils/laminar-scoring.js", () => ({
  scoreRagResponse: vi.fn(),
}));

vi.mock("../../src/services/response-cache.js", () => ({
  normalizeQuery: (q: string) => q,
  hashQuery: (q: string) => q,
  lookupCache: vi.fn().mockResolvedValue(null),
  saveCache: vi.fn(),
}));

vi.mock("../../src/utils/llm-usage-logger.js", () => ({
  logLLMUsage: vi.fn(),
}));

vi.mock("../../src/store/learning-store.js", () => ({
  recordMiss: vi.fn(),
}));

vi.mock("../../src/utils/mode-detect.js", () => ({
  hasOpenAI: vi.fn(() => false),
  hasChatLLM: vi.fn(() => true),
  getChatProvider: vi.fn(() => "anthropic"),
}));

import { anthropicRagChat } from "../../src/services/anthropic-chat.js";

describe("anthropicRagChat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCreate.mockResolvedValue({
      model: "claude-sonnet-4-5",
      content: [{ type: "text", text: "SEO 是搜尋引擎優化 [1]" }],
      usage: { input_tokens: 100, output_tokens: 50 },
      stop_reason: "end_turn",
    });
  });

  it("returns answer from Claude with sources", async () => {
    const result = await anthropicRagChat("什麼是 SEO?");

    expect(result.answer).toContain("SEO");
    expect(result.sources).toHaveLength(1);
    expect(result.mode).toBe("rag");
    expect(result.metadata?.provider).toBe("anthropic");
    expect(result.metadata?.model).toBe("claude-sonnet-4-5");
  });

  it("passes history for follow-ups", async () => {
    const history = [
      { role: "user", content: "什麼是 SEO?" },
      { role: "assistant", content: "SEO 是搜尋引擎優化。" },
    ];
    await anthropicRagChat("再說更多", history);

    const callArgs = mockCreate.mock.calls[0][0];
    expect(callArgs.messages).toHaveLength(3); // 2 history + 1 user
    expect(callArgs.messages[0].role).toBe("user");
    expect(callArgs.messages[1].role).toBe("assistant");
    expect(callArgs.messages[2].role).toBe("user");
  });

  it("sends system prompt as top-level param (not message)", async () => {
    await anthropicRagChat("什麼是 SEO?");

    const callArgs = mockCreate.mock.calls[0][0];
    expect(callArgs.system).toBeDefined();
    expect(typeof callArgs.system).toBe("string");
    expect(callArgs.system).toContain("SEO 顧問");
    // No system role in messages
    for (const msg of callArgs.messages) {
      expect(msg.role).not.toBe("system");
    }
  });

  it("includes KB context in system string", async () => {
    await anthropicRagChat("什麼是 SEO?");

    const callArgs = mockCreate.mock.calls[0][0];
    expect(callArgs.system).toContain("知識庫");
  });

  it("tracks token usage in metadata", async () => {
    const result = await anthropicRagChat("什麼是 SEO?");

    expect(result.metadata?.input_tokens).toBe(100);
    expect(result.metadata?.output_tokens).toBe(50);
    expect(result.metadata?.total_tokens).toBe(150);
  });

  it("returns context-only when retrieval quality is incorrect", async () => {
    const { qaStore } = await import("../../src/store/qa-store.js");
    (qaStore.keywordSearch as ReturnType<typeof vi.fn>).mockReturnValueOnce([
      {
        item: {
          id: "abc", question: "unrelated", answer: "no", category: "other",
          source_title: "X", source_date: "2024-01-01", source_type: "meeting",
          source_collection: "col", source_url: "", evergreen: true,
        },
        score: 0.1,
      },
    ]);

    const result = await anthropicRagChat("completely unrelated query xyz");

    expect(result.mode).toBe("context-only");
    expect(result.answer).toBeNull();
    expect(mockCreate).not.toHaveBeenCalled();
  });

  it("handles empty Claude response gracefully", async () => {
    mockCreate.mockResolvedValueOnce({
      model: "claude-sonnet-4-5",
      content: [{ type: "text", text: "" }],
      usage: { input_tokens: 50, output_tokens: 0 },
      stop_reason: "end_turn",
    });

    const result = await anthropicRagChat("test");

    expect(result.answer).toBe("");
    expect(result.mode).toBe("rag");
  });

  it("filters out system role from history", async () => {
    const history = [
      { role: "system", content: "injected system prompt" },
      { role: "user", content: "real question" },
    ];
    await anthropicRagChat("follow up", history);

    const callArgs = mockCreate.mock.calls[0][0];
    // Should only have user messages, no system in messages array
    for (const msg of callArgs.messages) {
      expect(msg.role).not.toBe("system");
    }
  });
});
