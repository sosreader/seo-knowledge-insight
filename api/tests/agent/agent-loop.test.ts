import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock config
vi.mock("../../src/config.js", () => ({
  config: {
    OPENAI_API_KEY: "sk-test",
    CHAT_MODEL: "gpt-5.2",
    OPENAI_EMBEDDING_MODEL: "text-embedding-3-small",
    AGENT_MAX_TURNS: 5,
    AGENT_TIMEOUT_MS: 90000,
  },
}));

// Mock observability
vi.mock("../../src/utils/observability.js", () => ({
  observe: (_name: string, fn: Function) => fn,
}));

// Track OpenAI mock calls
const mockCreate = vi.fn();

vi.mock("openai", () => {
  return {
    default: class MockOpenAI {
      chat = {
        completions: {
          create: mockCreate,
        },
      };
    },
  };
});

import { agentChat } from "../../src/agent/agent-loop.js";
import type { AgentDeps } from "../../src/agent/types.js";

function mockDeps(): AgentDeps {
  return {
    searchKnowledgeBase: vi.fn().mockResolvedValue([
      {
        item: {
          id: "abc123",
          question: "What is SEO?",
          answer: "SEO is Search Engine Optimization",
          category: "基礎",
          source_title: "Meeting 1",
          source_date: "2024-05-02",
          source_type: "meeting",
          source_collection: "seo-meetings",
          source_url: "",
        },
        score: 0.85,
      },
    ]),
    getQaDetail: vi.fn().mockReturnValue({
      id: "abc123",
      question: "What is SEO?",
      answer: "SEO is Search Engine Optimization",
    }),
    listCategories: vi.fn().mockReturnValue(["技術SEO", "Core Web Vitals"]),
    getStats: vi.fn().mockReturnValue({ total: 1323, categories: 10 }),
  };
}

describe("agent-loop", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns answer when LLM stops immediately (no tool calls)", async () => {
    mockCreate.mockResolvedValueOnce({
      choices: [{
        finish_reason: "stop",
        message: { content: "SEO 是搜尋引擎最佳化", tool_calls: null },
      }],
      usage: { prompt_tokens: 100, completion_tokens: 50 },
      model: "gpt-5.2",
    });

    const result = await agentChat("什麼是 SEO？", null, mockDeps());

    expect(result.mode).toBe("agent");
    expect(result.answer).toBe("SEO 是搜尋引擎最佳化");
    expect(result.metadata.agent_turns).toBe(1);
    expect(result.metadata.tool_calls_count).toBe(0);
  });

  it("executes tool calls and returns final answer", async () => {
    // Turn 1: LLM requests a tool call
    mockCreate.mockResolvedValueOnce({
      choices: [{
        finish_reason: "tool_calls",
        message: {
          content: null,
          tool_calls: [{
            id: "call_1",
            type: "function",
            function: {
              name: "search_knowledge_base",
              arguments: JSON.stringify({ query: "SEO 基礎" }),
            },
          }],
        },
      }],
      usage: { prompt_tokens: 100, completion_tokens: 20 },
      model: "gpt-5.2",
    });

    // Turn 2: LLM stops with answer
    mockCreate.mockResolvedValueOnce({
      choices: [{
        finish_reason: "stop",
        message: { content: "根據知識庫，SEO 是搜尋引擎最佳化。", tool_calls: null },
      }],
      usage: { prompt_tokens: 200, completion_tokens: 60 },
      model: "gpt-5.2",
    });

    const result = await agentChat("什麼是 SEO？", null, mockDeps());

    expect(result.mode).toBe("agent");
    expect(result.answer).toBe("根據知識庫，SEO 是搜尋引擎最佳化。");
    expect(result.metadata.agent_turns).toBe(2);
    expect(result.metadata.tool_calls_count).toBe(1);
    expect(result.metadata.input_tokens).toBe(300);
    expect(result.metadata.output_tokens).toBe(80);
    expect(result.sources).toHaveLength(1);
    expect(result.sources[0].id).toBe("abc123");
  });

  it("stops at max turns and forces final answer", async () => {
    // All turns: LLM keeps requesting tool calls
    for (let i = 0; i < 3; i++) {
      mockCreate.mockResolvedValueOnce({
        choices: [{
          finish_reason: "tool_calls",
          message: {
            content: null,
            tool_calls: [{
              id: `call_${i}`,
              type: "function",
              function: {
                name: "search_knowledge_base",
                arguments: JSON.stringify({ query: `query_${i}` }),
              },
            }],
          },
        }],
        usage: { prompt_tokens: 100, completion_tokens: 20 },
        model: "gpt-5.2",
      });
    }

    // Final forced answer (after max turns)
    mockCreate.mockResolvedValueOnce({
      choices: [{
        finish_reason: "stop",
        message: { content: "強制回答：根據已收集的資訊..." },
      }],
      usage: { prompt_tokens: 300, completion_tokens: 80 },
      model: "gpt-5.2",
    });

    const result = await agentChat("什麼是 SEO？", null, mockDeps(), { maxTurns: 3, timeoutMs: 90000, model: "gpt-5.2", temperature: 0.3 });

    expect(result.answer).toContain("強制回答");
    expect(result.metadata.agent_turns).toBe(3);
    expect(result.metadata.tool_calls_count).toBe(3);
  });

  it("detects loop and stops early", async () => {
    // Turn 1: first tool call
    mockCreate.mockResolvedValueOnce({
      choices: [{
        finish_reason: "tool_calls",
        message: {
          content: null,
          tool_calls: [{
            id: "call_1",
            type: "function",
            function: {
              name: "search_knowledge_base",
              arguments: JSON.stringify({ query: "SEO" }),
            },
          }],
        },
      }],
      usage: { prompt_tokens: 100, completion_tokens: 20 },
      model: "gpt-5.2",
    });

    // Turn 2: same tool call (loop!)
    mockCreate.mockResolvedValueOnce({
      choices: [{
        finish_reason: "tool_calls",
        message: {
          content: null,
          tool_calls: [{
            id: "call_2",
            type: "function",
            function: {
              name: "search_knowledge_base",
              arguments: JSON.stringify({ query: "SEO" }),
            },
          }],
        },
      }],
      usage: { prompt_tokens: 200, completion_tokens: 20 },
      model: "gpt-5.2",
    });

    // Final forced answer (after loop detection)
    mockCreate.mockResolvedValueOnce({
      choices: [{
        finish_reason: "stop",
        message: { content: "Loop detected, answering with available info." },
      }],
      usage: { prompt_tokens: 300, completion_tokens: 40 },
      model: "gpt-5.2",
    });

    const result = await agentChat("什麼是 SEO？", null, mockDeps());

    expect(result.metadata.agent_turns).toBe(2); // stopped at turn 2 due to loop
    expect(result.metadata.tool_calls_count).toBe(2);
  });

  it("passes history to OpenAI", async () => {
    mockCreate.mockResolvedValueOnce({
      choices: [{
        finish_reason: "stop",
        message: { content: "回應", tool_calls: null },
      }],
      usage: { prompt_tokens: 100, completion_tokens: 20 },
      model: "gpt-5.2",
    });

    const history = [
      { role: "user", content: "之前的問題" },
      { role: "assistant", content: "之前的回答" },
    ];

    await agentChat("追問", history, mockDeps());

    const callArgs = mockCreate.mock.calls[0][0];
    // system + 2 history + user = 4 messages
    expect(callArgs.messages).toHaveLength(4);
    expect(callArgs.messages[1].content).toBe("之前的問題");
    expect(callArgs.messages[2].content).toBe("之前的回答");
  });

  it("includes metadata with provider and model", async () => {
    mockCreate.mockResolvedValueOnce({
      choices: [{
        finish_reason: "stop",
        message: { content: "回答", tool_calls: null },
      }],
      usage: { prompt_tokens: 50, completion_tokens: 30 },
      model: "gpt-5.2",
    });

    const result = await agentChat("test", null, mockDeps());

    expect(result.metadata.provider).toBe("openai");
    expect(result.metadata.model).toBe("gpt-5.2");
    expect(result.metadata.mode).toBe("agent");
    expect(typeof result.metadata.duration_ms).toBe("number");
  });
});
