/**
 * Tests for rag-chat-stream — streaming RAG pipeline.
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

vi.mock("../../src/store/learning-store.js", () => ({
  recordMiss: vi.fn(),
}));

vi.mock("../../src/utils/llm-usage-logger.js", () => ({
  logLLMUsage: vi.fn(),
}));

import { FAKE_ITEMS } from "../setup.js";
import type { StreamCallbacks } from "../../src/services/rag-chat-stream.js";

const { ragChatStream } = await import("../../src/services/rag-chat-stream.js");

/** Create an async iterable simulating OpenAI streaming chunks. */
function createMockStream(tokens: string[], usage?: { prompt_tokens: number; completion_tokens: number }) {
  const chunks = tokens.map((t, i) => ({
    choices: [{ delta: { content: t }, index: 0 }],
    model: "gpt-4o-mini",
    usage: i === tokens.length - 1 ? usage : undefined,
  }));

  return {
    [Symbol.asyncIterator]: async function* () {
      for (const chunk of chunks) {
        yield chunk;
      }
    },
  };
}

function createCallbackTracker() {
  const events: Array<{ type: string; data: unknown }> = [];
  const callbacks: StreamCallbacks = {
    onSources: async (sources) => { events.push({ type: "sources", data: sources }); },
    onToken: async (token) => { events.push({ type: "token", data: token }); },
    onMetadata: async (metadata) => { events.push({ type: "metadata", data: metadata }); },
    onDone: async () => { events.push({ type: "done", data: null }); },
    onError: async (error) => { events.push({ type: "error", data: error }); },
  };
  return { events, callbacks };
}

describe("ragChatStream", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("streams tokens from GPT response", async () => {
    mockGetEmbedding.mockResolvedValueOnce(new Float32Array([0.1]));
    mockHybridSearch.mockResolvedValueOnce([
      { item: FAKE_ITEMS[0], score: 0.9 },
    ]);
    mockCreate.mockResolvedValueOnce(
      createMockStream(["Hello", " world", "!"], { prompt_tokens: 100, completion_tokens: 3 }),
    );

    const { events, callbacks } = createCallbackTracker();
    await ragChatStream("test query", null, callbacks);

    const tokenEvents = events.filter((e) => e.type === "token");
    expect(tokenEvents.map((e) => e.data)).toEqual(["Hello", " world", "!"]);

    expect(events[0].type).toBe("sources");
    expect(events.some((e) => e.type === "metadata")).toBe(true);
    expect(events[events.length - 1].type).toBe("done");
  });

  it("emits sources before tokens", async () => {
    mockGetEmbedding.mockResolvedValueOnce(new Float32Array([0.1]));
    mockHybridSearch.mockResolvedValueOnce([
      { item: FAKE_ITEMS[0], score: 0.8 },
      { item: FAKE_ITEMS[1], score: 0.7 },
    ]);
    mockCreate.mockResolvedValueOnce(createMockStream(["答案"]));

    const { events, callbacks } = createCallbackTracker();
    await ragChatStream("test", null, callbacks);

    const sourcesIdx = events.findIndex((e) => e.type === "sources");
    const firstTokenIdx = events.findIndex((e) => e.type === "token");
    expect(sourcesIdx).toBeLessThan(firstTokenIdx);

    const sourcesData = events[sourcesIdx].data as Array<{ id: string }>;
    expect(sourcesData).toHaveLength(2);
  });

  it("returns context-only for incorrect retrieval (score < 0.4)", async () => {
    mockGetEmbedding.mockResolvedValueOnce(new Float32Array([0.1]));
    mockHybridSearch.mockResolvedValueOnce([
      { item: FAKE_ITEMS[0], score: 0.2 },
    ]);

    const { events, callbacks } = createCallbackTracker();
    await ragChatStream("bad query", null, callbacks);

    // No tokens should be emitted
    expect(events.filter((e) => e.type === "token")).toHaveLength(0);
    expect(mockCreate).not.toHaveBeenCalled();

    const metaEvent = events.find((e) => e.type === "metadata");
    expect((metaEvent?.data as Record<string, unknown>)?.retrieval_quality).toBe("incorrect");
    expect((metaEvent?.data as Record<string, unknown>)?.mode).toBe("context-only");
    expect(events[events.length - 1].type).toBe("done");
  });

  it("appends disclaimer for ambiguous retrieval", async () => {
    mockGetEmbedding.mockResolvedValueOnce(new Float32Array([0.1]));
    mockHybridSearch.mockResolvedValueOnce([
      { item: FAKE_ITEMS[0], score: 0.5 },
    ]);
    mockCreate.mockResolvedValueOnce(createMockStream(["模糊答案"]));

    const { events, callbacks } = createCallbackTracker();
    await ragChatStream("ambiguous", null, callbacks);

    const tokenTexts = events
      .filter((e) => e.type === "token")
      .map((e) => e.data as string);
    const combined = tokenTexts.join("");
    expect(combined).toContain("模糊答案");
    expect(combined).toContain("注意：以上回答基於相似度較低的知識庫結果");
  });

  it("emits error event on failure", async () => {
    mockGetEmbedding.mockRejectedValueOnce(new Error("Embedding failed"));

    const { events, callbacks } = createCallbackTracker();
    await ragChatStream("test", null, callbacks);

    const errorEvent = events.find((e) => e.type === "error");
    expect(errorEvent).toBeDefined();
    expect(errorEvent?.data).toContain("Embedding failed");
  });
});
