/**
 * Tests for rag-chat-pure.ts — Functional Core (zero I/O, zero mock).
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import {
  isStale,
  formatContext,
  buildSystemPrompt,
  buildMessages,
  buildMetadata,
  appendDisclaimer,
  SYSTEM_PROMPT,
  AMBIGUOUS_DISCLAIMER,
  STALENESS_THRESHOLD_MONTHS,
} from "../../src/services/rag-chat-pure.js";
import type { QAItem } from "../../src/store/qa-store.js";

const makeItem = (overrides: Partial<QAItem> = {}): QAItem => ({
  id: "test-id",
  question: "What is SEO?",
  answer: "SEO is search engine optimization.",
  keywords: ["SEO"],
  category: "技術SEO",
  difficulty: "beginner",
  evergreen: true,
  source_title: "SEO Guide",
  source_date: "2025-01-01",
  source_type: "meeting",
  source_collection: "notion",
  source_url: "",
  ...overrides,
});

describe("rag-chat-pure", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("isStale", () => {
    it("returns false for recent dates", () => {
      const recent = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
      expect(isStale(recent)).toBe(false);
    });

    it("returns true for dates older than 18 months", () => {
      const old = new Date(Date.now() - 20 * 30 * 24 * 60 * 60 * 1000).toISOString();
      expect(isStale(old)).toBe(true);
    });

    it("returns false for exactly threshold (boundary)", () => {
      // Exactly at threshold: ageMonths === STALENESS_THRESHOLD_MONTHS, which is NOT > threshold
      const boundary = new Date(Date.now() - STALENESS_THRESHOLD_MONTHS * 30 * 24 * 60 * 60 * 1000);
      // Add 1 second buffer to avoid floating point equality at boundary
      boundary.setSeconds(boundary.getSeconds() + 1);
      expect(isStale(boundary.toISOString())).toBe(false);
    });

    it("returns false for invalid date strings", () => {
      expect(isStale("not-a-date")).toBe(false);
    });

    it("returns false for empty string", () => {
      expect(isStale("")).toBe(false);
    });
  });

  describe("formatContext", () => {
    it("returns empty string for empty hits", () => {
      expect(formatContext([])).toBe("");
    });

    it("formats a single hit correctly", () => {
      const result = formatContext([{ item: makeItem(), score: 0.85 }]);
      expect(result).toContain("[1] Q: What is SEO?");
      expect(result).toContain("A: SEO is search engine optimization.");
      expect(result).toContain("相似度: 0.85");
    });

    it("formats multiple hits with sequential numbering", () => {
      const hits = [
        { item: makeItem({ question: "Q1" }), score: 0.9 },
        { item: makeItem({ question: "Q2" }), score: 0.7 },
      ];
      const result = formatContext(hits);
      expect(result).toContain("[1] Q: Q1");
      expect(result).toContain("[2] Q: Q2");
    });

    it("adds staleness note for non-evergreen stale items", () => {
      const staleDate = new Date(Date.now() - 20 * 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
      const hits = [
        { item: makeItem({ evergreen: false, source_date: staleDate }), score: 0.8 },
      ];
      const result = formatContext(hits);
      expect(result).toContain("注意：此建議超過 18 個月");
    });

    it("does not add staleness note for evergreen items", () => {
      const staleDate = new Date(Date.now() - 20 * 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
      const hits = [
        { item: makeItem({ evergreen: true, source_date: staleDate }), score: 0.8 },
      ];
      const result = formatContext(hits);
      expect(result).not.toContain("注意：此建議超過 18 個月");
    });

    it("uses source_date as fallback when source_title is empty", () => {
      const hits = [
        { item: makeItem({ source_title: "", source_date: "2025-06-01" }), score: 0.5 },
      ];
      const result = formatContext(hits);
      expect(result).toContain("來源: 2025-06-01");
    });
  });

  describe("buildSystemPrompt", () => {
    it("returns base prompt without maturity or ambiguous", () => {
      const result = buildSystemPrompt(null, "correct");
      expect(result).toBe(SYSTEM_PROMPT);
    });

    it("appends maturity context when maturity level provided", () => {
      const result = buildSystemPrompt("L1", "correct");
      expect(result).toContain("客戶成熟度脈絡");
      expect(result).toContain("脈絡結束");
    });

    it("appends ambiguous warning when retrieval quality is ambiguous", () => {
      const result = buildSystemPrompt(null, "ambiguous");
      expect(result).toContain("檢索結果的相似度偏低");
    });

    it("appends both maturity and ambiguous when both apply", () => {
      const result = buildSystemPrompt("L3", "ambiguous");
      expect(result).toContain("客戶成熟度脈絡");
      expect(result).toContain("檢索結果的相似度偏低");
    });

    it("does not append ambiguous warning for correct quality", () => {
      const result = buildSystemPrompt(null, "correct");
      expect(result).not.toContain("相似度偏低");
    });

    it("does not append ambiguous warning for incorrect quality", () => {
      const result = buildSystemPrompt(null, "incorrect");
      expect(result).not.toContain("相似度偏低");
    });
  });

  describe("buildMessages", () => {
    it("builds messages with system prompt + user message (no history, no context)", () => {
      const msgs = buildMessages({
        systemPrompt: "You are helpful.",
        context: "",
        history: null,
        message: "Hello",
      });
      expect(msgs).toHaveLength(2);
      expect(msgs[0]).toEqual({ role: "system", content: "You are helpful." });
      expect(msgs[1]).toEqual({ role: "user", content: "Hello" });
    });

    it("inserts context as second system message", () => {
      const msgs = buildMessages({
        systemPrompt: "System",
        context: "Some context",
        history: null,
        message: "Question",
      });
      expect(msgs).toHaveLength(3);
      expect(msgs[1].role).toBe("system");
      expect(msgs[1].content).toContain("相關 SEO 知識庫");
      expect(msgs[1].content).toContain("Some context");
    });

    it("appends history messages in order", () => {
      const msgs = buildMessages({
        systemPrompt: "System",
        context: "",
        history: [
          { role: "user", content: "Hi" },
          { role: "assistant", content: "Hello" },
        ],
        message: "Follow up",
      });
      expect(msgs).toHaveLength(4);
      expect(msgs[1]).toEqual({ role: "user", content: "Hi" });
      expect(msgs[2]).toEqual({ role: "assistant", content: "Hello" });
      expect(msgs[3]).toEqual({ role: "user", content: "Follow up" });
    });

    it("handles empty history array as null", () => {
      const msgs = buildMessages({
        systemPrompt: "System",
        context: "",
        history: [],
        message: "Question",
      });
      // Empty array iterates 0 times, same result as null
      expect(msgs).toHaveLength(2);
    });
  });

  describe("buildMetadata", () => {
    it("builds complete metadata object", () => {
      const meta = buildMetadata({
        model: "gpt-5.2",
        embeddingModel: "text-embedding-3-small",
        inputTokens: 100,
        outputTokens: 50,
        totalTokens: 150,
        reasoningTokens: undefined,
        durationMs: 1000,
        retrievalCount: 5,
        rerankerUsed: true,
        cacheHit: false,
        retrievalQuality: "correct",
        citationCount: 3,
      });

      expect(meta.model).toBe("gpt-5.2");
      expect(meta.provider).toBe("openai");
      expect(meta.mode).toBe("rag");
      expect(meta.embedding_model).toBe("text-embedding-3-small");
      expect(meta.input_tokens).toBe(100);
      expect(meta.output_tokens).toBe(50);
      expect(meta.total_tokens).toBe(150);
      expect(meta.duration_ms).toBe(1000);
      expect(meta.retrieval_count).toBe(5);
      expect(meta.reranker_used).toBe(true);
      expect(meta.cache_hit).toBe(false);
      expect(meta.retrieval_quality).toBe("correct");
      expect(meta.citation_count).toBe(3);
    });

    it("uses model string directly", () => {
      const meta = buildMetadata({
        model: "gpt-4o",
        embeddingModel: "text-embedding-3-small",
        inputTokens: 0,
        outputTokens: 0,
        totalTokens: 0,
        reasoningTokens: undefined,
        durationMs: 500,
        retrievalCount: 0,
        rerankerUsed: false,
        cacheHit: false,
        retrievalQuality: "incorrect",
        citationCount: 0,
      });
      expect(meta.model).toBe("gpt-4o");
    });
  });

  describe("appendDisclaimer", () => {
    it("appends disclaimer for ambiguous quality", () => {
      const result = appendDisclaimer("Some answer", "ambiguous");
      expect(result).toBe("Some answer" + AMBIGUOUS_DISCLAIMER);
    });

    it("does not append for correct quality", () => {
      const result = appendDisclaimer("Some answer", "correct");
      expect(result).toBe("Some answer");
    });

    it("does not append for incorrect quality", () => {
      const result = appendDisclaimer("Some answer", "incorrect");
      expect(result).toBe("Some answer");
    });

    it("does not append for empty answer even if ambiguous", () => {
      const result = appendDisclaimer("", "ambiguous");
      expect(result).toBe("");
    });
  });
});
