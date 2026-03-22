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

const mockStream = vi.fn();
vi.mock("@anthropic-ai/sdk", () => ({
  default: class MockAnthropic {
    messages = { stream: mockStream };
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
  },
}));

vi.mock("../../src/services/reranker.js", () => ({
  rerank: vi.fn((_q: string, hits: unknown[]) => hits),
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

import { anthropicRagChatStream } from "../../src/services/anthropic-chat-stream.js";

/** Create a fake Anthropic stream that yields events and resolves finalMessage. */
function createFakeStream(tokens: string[], usage: { input_tokens: number; output_tokens: number }) {
  const events = tokens.map((text) => ({
    type: "content_block_delta" as const,
    delta: { type: "text_delta" as const, text },
  }));

  return {
    [Symbol.asyncIterator]: async function* () {
      for (const event of events) {
        yield event;
      }
    },
    finalMessage: vi.fn().mockResolvedValue({
      model: "claude-sonnet-4-5",
      usage,
      content: [{ type: "text", text: tokens.join("") }],
    }),
  };
}

describe("anthropicRagChatStream", () => {
  const callbacks = {
    onSources: vi.fn().mockResolvedValue(undefined),
    onToken: vi.fn().mockResolvedValue(undefined),
    onMetadata: vi.fn().mockResolvedValue(undefined),
    onDone: vi.fn().mockResolvedValue(undefined),
    onError: vi.fn().mockResolvedValue(undefined),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockStream.mockReturnValue(
      createFakeStream(["SEO ", "是", "搜尋引擎優化"], { input_tokens: 100, output_tokens: 30 }),
    );
  });

  it("streams tokens via onToken callback", async () => {
    await anthropicRagChatStream("什麼是 SEO?", null, callbacks);

    expect(callbacks.onToken).toHaveBeenCalledTimes(3);
    expect(callbacks.onToken).toHaveBeenNthCalledWith(1, "SEO ");
    expect(callbacks.onToken).toHaveBeenNthCalledWith(2, "是");
    expect(callbacks.onToken).toHaveBeenNthCalledWith(3, "搜尋引擎優化");
  });

  it("emits sources before tokens", async () => {
    await anthropicRagChatStream("什麼是 SEO?", null, callbacks);

    expect(callbacks.onSources).toHaveBeenCalledTimes(1);
    const sources = callbacks.onSources.mock.calls[0][0];
    expect(sources).toHaveLength(1);
    // Sources called before first token
    const sourcesOrder = callbacks.onSources.mock.invocationCallOrder[0];
    const firstTokenOrder = callbacks.onToken.mock.invocationCallOrder[0];
    expect(sourcesOrder).toBeLessThan(firstTokenOrder!);
  });

  it("emits metadata with provider=anthropic", async () => {
    await anthropicRagChatStream("什麼是 SEO?", null, callbacks);

    expect(callbacks.onMetadata).toHaveBeenCalledTimes(1);
    const metadata = callbacks.onMetadata.mock.calls[0][0];
    expect(metadata.provider).toBe("anthropic");
    expect(metadata.model).toBe("claude-sonnet-4-5");
    expect(metadata.input_tokens).toBe(100);
    expect(metadata.output_tokens).toBe(30);
  });

  it("calls onDone after stream completes", async () => {
    await anthropicRagChatStream("什麼是 SEO?", null, callbacks);

    expect(callbacks.onDone).toHaveBeenCalledTimes(1);
  });

  it("calls onError when stream fails", async () => {
    mockStream.mockImplementationOnce(() => {
      throw new Error("Anthropic API error");
    });

    await anthropicRagChatStream("test", null, callbacks);

    expect(callbacks.onError).toHaveBeenCalledWith("Anthropic API error");
    expect(callbacks.onDone).not.toHaveBeenCalled();
  });
});
