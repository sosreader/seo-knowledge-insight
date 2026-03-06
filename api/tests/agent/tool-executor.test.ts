import { describe, it, expect, vi } from "vitest";
import { executeTool } from "../../src/agent/tool-executor.js";
import type { AgentDeps } from "../../src/agent/types.js";

function mockDeps(overrides?: Partial<AgentDeps>): AgentDeps {
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
        },
        score: 0.85,
      },
    ]),
    getQaDetail: vi.fn().mockReturnValue({
      id: "abc123",
      question: "What is SEO?",
      answer: "SEO is Search Engine Optimization",
    }),
    listCategories: vi.fn().mockReturnValue(["技術SEO", "Core Web Vitals", "內容策略"]),
    getStats: vi.fn().mockReturnValue({ total: 1323, categories: 10 }),
    ...overrides,
  };
}

describe("tool-executor", () => {
  describe("search_knowledge_base", () => {
    it("returns search results as JSON", async () => {
      const deps = mockDeps();
      const result = await executeTool("search_knowledge_base", { query: "SEO" }, deps);

      expect(result.toolName).toBe("search_knowledge_base");
      expect(result.durationMs).toBeGreaterThanOrEqual(0);

      const parsed = JSON.parse(result.result);
      expect(parsed).toHaveLength(1);
      expect(parsed[0].id).toBe("abc123");
      expect(parsed[0].score).toBe(0.85);
    });

    it("filters by category when provided", async () => {
      const deps = mockDeps({
        searchKnowledgeBase: vi.fn().mockResolvedValue([
          { item: { id: "1", category: "技術SEO" }, score: 0.9 },
          { item: { id: "2", category: "內容策略" }, score: 0.8 },
        ]),
      });

      const result = await executeTool(
        "search_knowledge_base",
        { query: "test", category: "技術SEO" },
        deps,
      );

      const parsed = JSON.parse(result.result);
      expect(parsed).toHaveLength(1);
      expect(parsed[0].id).toBe("1");
    });

    it("returns error for invalid args", async () => {
      const deps = mockDeps();
      const result = await executeTool("search_knowledge_base", { query: "" }, deps);
      const parsed = JSON.parse(result.result);
      expect(parsed.error).toBeDefined();
    });
  });

  describe("get_qa_detail", () => {
    it("returns QA detail", async () => {
      const deps = mockDeps();
      const result = await executeTool("get_qa_detail", { id: "abc123" }, deps);

      const parsed = JSON.parse(result.result);
      expect(parsed.question).toBe("What is SEO?");
    });

    it("returns error for missing item", async () => {
      const deps = mockDeps({ getQaDetail: vi.fn().mockReturnValue(null) });
      const result = await executeTool("get_qa_detail", { id: "missing" }, deps);

      const parsed = JSON.parse(result.result);
      expect(parsed.error).toContain("not found");
    });
  });

  describe("list_categories", () => {
    it("returns categories", async () => {
      const deps = mockDeps();
      const result = await executeTool("list_categories", {}, deps);

      const parsed = JSON.parse(result.result);
      expect(parsed).toEqual(["技術SEO", "Core Web Vitals", "內容策略"]);
    });
  });

  describe("get_stats", () => {
    it("returns stats", async () => {
      const deps = mockDeps();
      const result = await executeTool("get_stats", {}, deps);

      const parsed = JSON.parse(result.result);
      expect(parsed.total).toBe(1323);
      expect(parsed.categories).toBe(10);
    });
  });
});
