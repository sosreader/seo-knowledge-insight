import { describe, it, expect } from "vitest";
import {
  searchKnowledgeBaseSchema,
  getQaDetailSchema,
  getOpenAITools,
} from "../../src/agent/tool-definitions.js";

describe("tool-definitions", () => {
  describe("searchKnowledgeBaseSchema", () => {
    it("parses valid input", () => {
      const result = searchKnowledgeBaseSchema.parse({ query: "SEO" });
      expect(result.query).toBe("SEO");
      expect(result.top_k).toBe(5); // default
    });

    it("parses with optional category", () => {
      const result = searchKnowledgeBaseSchema.parse({
        query: "Core Web Vitals",
        top_k: 3,
        category: "技術SEO",
      });
      expect(result.category).toBe("技術SEO");
      expect(result.top_k).toBe(3);
    });

    it("rejects empty query", () => {
      expect(() => searchKnowledgeBaseSchema.parse({ query: "" })).toThrow();
    });

    it("rejects top_k out of range", () => {
      expect(() => searchKnowledgeBaseSchema.parse({ query: "SEO", top_k: 20 })).toThrow();
    });
  });

  describe("getQaDetailSchema", () => {
    it("parses valid hex stable_id", () => {
      const result = getQaDetailSchema.parse({ id: "abc123def4560000" });
      expect(result.id).toBe("abc123def4560000");
    });

    it("parses valid numeric seq", () => {
      const result = getQaDetailSchema.parse({ id: "123" });
      expect(result.id).toBe("123");
    });

    it("rejects empty id", () => {
      expect(() => getQaDetailSchema.parse({ id: "" })).toThrow();
    });
  });

  describe("getOpenAITools", () => {
    it("returns 4 tools in OpenAI format", () => {
      const tools = getOpenAITools();
      expect(tools).toHaveLength(4);
      expect(tools.every((t) => t.type === "function")).toBe(true);
    });

    it("has correct tool names", () => {
      const tools = getOpenAITools();
      const names = tools.map((t) => t.function.name);
      expect(names).toEqual([
        "search_knowledge_base",
        "get_qa_detail",
        "list_categories",
        "get_stats",
      ]);
    });

    it("search_knowledge_base requires query", () => {
      const tools = getOpenAITools();
      const search = tools.find((t) => t.function.name === "search_knowledge_base")!;
      expect(search.function.parameters.required).toContain("query");
    });
  });
});
