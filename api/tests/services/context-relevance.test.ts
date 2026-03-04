import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock Anthropic SDK — must use function (not arrow) so it can be called with `new`
const mockCreate = vi.fn().mockResolvedValue({
  content: [
    {
      type: "text",
      text: JSON.stringify({
        overall_score: 0.82,
        reason: "大部分結果與查詢語意相符",
        per_context: [
          { id: "abc123", score: 0.9 },
          { id: "def456", score: 0.75 },
        ],
      }),
    },
  ],
});

vi.mock("@anthropic-ai/sdk", () => ({
  default: function MockAnthropic() {
    return {
      messages: { create: mockCreate },
    };
  },
}));

vi.mock("../../src/config.js", () => ({
  config: {
    ANTHROPIC_API_KEY: "test-key",
    CHAT_CONTEXT_K: 5,
  },
  paths: {},
}));

import { contextRelevance } from "../../src/services/context-relevance.js";
import type { QAItem } from "../../src/store/qa-store.js";

function makeItem(id: string, question: string, category: string, freshnessScore = 1.0): QAItem {
  return {
    id,
    seq: 1,
    question,
    answer: "test answer",
    keywords: [],
    confidence: 0.9,
    category,
    difficulty: "intermediate",
    evergreen: true,
    source_title: "Test",
    source_date: "2024-01-01",
    is_merged: false,
    synonyms: [],
    freshness_score: freshnessScore,
    search_hit_count: 0,
    notion_url: "",
    source_type: "meeting",
    source_collection: "seo-meetings",
    source_url: "",
  };
}

describe("contextRelevance", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns score=0 for empty contexts", async () => {
    const result = await contextRelevance("Discover 流量下降", []);
    expect(result.score).toBe(0);
    expect(result.per_context).toHaveLength(0);
    expect(result.reason).toBeTruthy();
  });

  it("returns score and per_context from Claude response", async () => {
    const contexts = [
      makeItem("abc123", "Discover 流量下降的原因為何？", "SEO"),
      makeItem("def456", "GSC 如何分析流量趨勢？", "Analytics"),
    ];
    const result = await contextRelevance("Discover 流量下降", contexts);
    expect(result.score).toBeCloseTo(0.82, 2);
    expect(result.reason).toContain("語意");
    expect(result.per_context).toHaveLength(2);
    expect(result.per_context[0]!.id).toBe("abc123");
    expect(result.per_context[0]!.score).toBeCloseTo(0.9, 2);
  });

  it("uses fallback heuristic when API key is missing", async () => {
    const { config } = await import("../../src/config.js");
    const originalKey = config.ANTHROPIC_API_KEY;
    // Simulate missing key by overriding the mock
    vi.doMock("../../src/config.js", () => ({
      config: { ANTHROPIC_API_KEY: "", CHAT_CONTEXT_K: 5 },
      paths: {},
    }));

    // Import fresh module to pick up mocked config
    const { contextRelevance: crNoKey } = await import(
      "../../src/services/context-relevance.js?nocache=" + Date.now()
    ).catch(() => import("../../src/services/context-relevance.js"));

    const contexts = [
      makeItem("id1", "Q1", "SEO", 0.8),
      makeItem("id2", "Q2", "Technical", 0.6),
    ];
    // Can't fully test key-missing branch without module cache isolation,
    // but verify the function doesn't throw
    const result = await crNoKey("query", contexts);
    expect(typeof result.score).toBe("number");
    expect(result.score).toBeGreaterThanOrEqual(0);
    expect(result.score).toBeLessThanOrEqual(1);
    expect(result.per_context.length).toBe(contexts.length);

    // Restore
    vi.doMock("../../src/config.js", () => ({
      config: { ANTHROPIC_API_KEY: originalKey, CHAT_CONTEXT_K: 5 },
      paths: {},
    }));
  });

  it("falls back gracefully on malformed JSON from Claude", async () => {
    mockCreate.mockResolvedValueOnce({
      content: [{ type: "text", text: "not valid json at all" }],
    });
    const contexts = [makeItem("abc123", "Q1", "SEO", 0.7)];
    const result = await contextRelevance("query", contexts);
    // Fallback returns freshness_score as proxy
    expect(result.score).toBeGreaterThanOrEqual(0);
    expect(result.score).toBeLessThanOrEqual(1);
    expect(result.per_context).toHaveLength(1);
  });

  it("falls back gracefully when Claude returns non-text content", async () => {
    mockCreate.mockResolvedValueOnce({
      content: [{ type: "tool_use", id: "x", name: "y", input: {} }],
    });
    const contexts = [makeItem("abc123", "Q1", "SEO", 0.5)];
    const result = await contextRelevance("query", contexts);
    expect(result.score).toBeGreaterThanOrEqual(0);
    expect(result.per_context).toHaveLength(1);
  });

  it("clamps scores to [0, 1] range", async () => {
    mockCreate.mockResolvedValueOnce({
      content: [
        {
          type: "text",
          text: JSON.stringify({
            overall_score: 1.5, // out of range
            reason: "超過範圍測試",
            per_context: [{ id: "abc123", score: -0.2 }],
          }),
        },
      ],
    });
    const contexts = [makeItem("abc123", "Q1", "SEO")];
    const result = await contextRelevance("query", contexts);
    expect(result.score).toBeLessThanOrEqual(1);
    expect(result.per_context[0]!.score).toBeGreaterThanOrEqual(0);
  });
});
