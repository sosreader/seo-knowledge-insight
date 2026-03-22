import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../src/config.js", () => ({
  config: {
    ANTHROPIC_API_KEY: "sk-ant-test",
    CHAT_LLM_PROVIDER: "anthropic",
    CHAT_ANTHROPIC_MODEL: "claude-sonnet-4-5",
    OPENAI_API_KEY: "",
    OPENAI_EMBEDDING_MODEL: "text-embedding-3-small",
    CHAT_CONTEXT_K: 5,
    AGENT_MAX_TURNS: 5,
    AGENT_TIMEOUT_MS: 90000,
  },
}));

const mockCreate = vi.fn();
vi.mock("@anthropic-ai/sdk", () => ({
  default: class MockAnthropic {
    messages = { create: mockCreate };
  },
}));

vi.mock("../../src/utils/observability.js", () => ({
  observe: (_name: string, fn: Function) => fn,
}));

import { anthropicAgentChat } from "../../src/agent/anthropic-agent-loop.js";
import type { AgentDeps } from "../../src/agent/types.js";

function createDeps(): AgentDeps {
  return {
    searchKnowledgeBase: vi.fn().mockResolvedValue([
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
          score: 0.8,
        },
        score: 0.8,
      },
    ]),
    getQaDetail: vi.fn().mockReturnValue(null),
    listCategories: vi.fn().mockReturnValue(["basics", "technical"]),
    getStats: vi.fn().mockReturnValue({ total: 100, categories: 5 }),
  };
}

describe("anthropicAgentChat", () => {
  let deps: AgentDeps;

  beforeEach(() => {
    vi.clearAllMocks();
    deps = createDeps();
  });

  it("returns answer when Claude stops immediately (no tool calls)", async () => {
    mockCreate.mockResolvedValueOnce({
      model: "claude-sonnet-4-5",
      content: [{ type: "text", text: "SEO 是搜尋引擎優化。" }],
      usage: { input_tokens: 100, output_tokens: 50 },
      stop_reason: "end_turn",
    });

    const result = await anthropicAgentChat("什麼是 SEO?", null, deps);

    expect(result.answer).toBe("SEO 是搜尋引擎優化。");
    expect(result.mode).toBe("agent");
    expect(result.metadata.provider).toBe("anthropic");
    expect(result.metadata.model).toBe("claude-sonnet-4-5");
    expect(result.metadata.agent_turns).toBe(1);
    expect(result.metadata.tool_calls_count).toBe(0);
  });

  it("executes tool_use and returns answer after second call", async () => {
    // First call: Claude requests tool_use
    mockCreate.mockResolvedValueOnce({
      model: "claude-sonnet-4-5",
      content: [
        { type: "tool_use", id: "tool_1", name: "search_knowledge_base", input: { query: "SEO basics" } },
      ],
      usage: { input_tokens: 100, output_tokens: 30 },
      stop_reason: "tool_use",
    });

    // Second call: Claude provides answer
    mockCreate.mockResolvedValueOnce({
      model: "claude-sonnet-4-5",
      content: [{ type: "text", text: "根據知識庫 [1]，SEO 是..." }],
      usage: { input_tokens: 200, output_tokens: 80 },
      stop_reason: "end_turn",
    });

    const result = await anthropicAgentChat("什麼是 SEO?", null, deps);

    expect(result.answer).toContain("SEO");
    expect(result.metadata.agent_turns).toBe(2);
    expect(result.metadata.tool_calls_count).toBe(1);
    expect(result.metadata.input_tokens).toBe(300); // 100 + 200
    expect(result.metadata.output_tokens).toBe(110); // 30 + 80
  });

  it("stops at max turns and forces final answer", async () => {
    // Always return tool_use to exhaust turns
    mockCreate.mockResolvedValue({
      model: "claude-sonnet-4-5",
      content: [
        { type: "tool_use", id: "tool_x", name: "search_knowledge_base", input: { query: "test" } },
      ],
      usage: { input_tokens: 50, output_tokens: 10 },
      stop_reason: "tool_use",
    });

    // Override the last call (final synthesis without tools)
    const maxTurns = 2;
    // After maxTurns tool calls, the final synthesis call returns text
    mockCreate
      .mockResolvedValueOnce({
        model: "claude-sonnet-4-5",
        content: [
          { type: "tool_use", id: "tool_1", name: "search_knowledge_base", input: { query: "a" } },
        ],
        usage: { input_tokens: 50, output_tokens: 10 },
        stop_reason: "tool_use",
      })
      .mockResolvedValueOnce({
        model: "claude-sonnet-4-5",
        content: [
          { type: "tool_use", id: "tool_2", name: "list_categories", input: {} },
        ],
        usage: { input_tokens: 50, output_tokens: 10 },
        stop_reason: "tool_use",
      })
      .mockResolvedValueOnce({
        // Final synthesis call
        model: "claude-sonnet-4-5",
        content: [{ type: "text", text: "最終回答" }],
        usage: { input_tokens: 100, output_tokens: 20 },
        stop_reason: "end_turn",
      });

    const result = await anthropicAgentChat("test", null, deps, { maxTurns });

    expect(result.answer).toBe("最終回答");
    expect(result.metadata.agent_turns).toBe(maxTurns);
  });

  it("passes history as user/assistant messages only", async () => {
    mockCreate.mockResolvedValueOnce({
      model: "claude-sonnet-4-5",
      content: [{ type: "text", text: "Follow-up answer" }],
      usage: { input_tokens: 100, output_tokens: 50 },
      stop_reason: "end_turn",
    });

    const history = [
      { role: "user", content: "first question" },
      { role: "assistant", content: "first answer" },
    ];

    await anthropicAgentChat("follow up", history, deps);

    const callArgs = mockCreate.mock.calls[0][0];
    expect(callArgs.messages).toHaveLength(3); // 2 history + 1 user
    expect(callArgs.system).toContain("SEO 顧問");
    // Verify no system role in messages
    for (const msg of callArgs.messages) {
      expect(msg.role).not.toBe("system");
    }
  });

  it("rejects unknown tool names", async () => {
    mockCreate
      .mockResolvedValueOnce({
        model: "claude-sonnet-4-5",
        content: [
          { type: "tool_use", id: "tool_bad", name: "dangerous_tool", input: {} },
        ],
        usage: { input_tokens: 50, output_tokens: 10 },
        stop_reason: "tool_use",
      })
      .mockResolvedValueOnce({
        model: "claude-sonnet-4-5",
        content: [{ type: "text", text: "OK" }],
        usage: { input_tokens: 50, output_tokens: 10 },
        stop_reason: "end_turn",
      });

    const result = await anthropicAgentChat("test", null, deps);

    expect(result.answer).toBe("OK");
    // dangerous_tool should not have been executed
    expect(result.metadata.tool_calls_count).toBe(0);
  });

  it("detects loops and stops early", async () => {
    const sameToolResponse = {
      model: "claude-sonnet-4-5",
      content: [
        { type: "tool_use", id: "tool_loop", name: "search_knowledge_base", input: { query: "same query" } },
      ],
      usage: { input_tokens: 50, output_tokens: 10 },
      stop_reason: "tool_use",
    };

    mockCreate
      .mockResolvedValueOnce(sameToolResponse)
      .mockResolvedValueOnce(sameToolResponse)
      // Final synthesis after loop detection
      .mockResolvedValueOnce({
        model: "claude-sonnet-4-5",
        content: [{ type: "text", text: "Loop stopped" }],
        usage: { input_tokens: 100, output_tokens: 20 },
        stop_reason: "end_turn",
      });

    const result = await anthropicAgentChat("test", null, deps, { maxTurns: 10 });

    expect(result.answer).toBe("Loop stopped");
    // Should stop after 2 turns (loop detected), not run all 10
    expect(result.metadata.agent_turns).toBe(2);
  });
});
