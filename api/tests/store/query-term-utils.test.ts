import { describe, expect, it } from "vitest";
import {
  categoryDiversityBoost,
  matchedQueryTerms,
  novelQueryTermBoost,
  queryTerms,
} from "../../src/store/query-term-utils.js";

describe("query-term-utils", () => {
  it("queryTerms lowercases, trims, and drops one-character tokens", () => {
    expect(queryTerms("  AI   ChatGPT a SEO  ")).toEqual([
      "ai",
      "chatgpt",
      "seo",
    ]);
  });

  it("queryTerms keeps mixed Chinese and English multi-character tokens", () => {
    expect(queryTerms("AI 流量佔比 ChatGPT Perplexity Gemini")).toEqual([
      "ai",
      "流量佔比",
      "chatgpt",
      "perplexity",
      "gemini",
    ]);
  });

  it("matchedQueryTerms returns only the terms present in the haystack", () => {
    expect(
      matchedQueryTerms("chatgpt perplexity ai traffic share", [
        "chatgpt",
        "gemini",
        "ai",
      ]),
    ).toEqual(new Set(["chatgpt", "ai"]));
  });

  it("categoryDiversityBoost preserves the original single-category boost and adds a second step", () => {
    expect(categoryDiversityBoost(0)).toBe(0);
    expect(categoryDiversityBoost(1)).toBe(0.12);
    expect(categoryDiversityBoost(2)).toBe(0.18);
    expect(categoryDiversityBoost(3)).toBe(0.18);
  });

  it("novelQueryTermBoost downweights long queries", () => {
    expect(novelQueryTermBoost(2, 4)).toBe(0.04);
    expect(novelQueryTermBoost(2, 6)).toBe(0.03);
    expect(novelQueryTermBoost(2, 10)).toBe(0.02);
  });

  it("novelQueryTermBoost caps long queries more aggressively", () => {
    expect(novelQueryTermBoost(8, 4)).toBe(0.08);
    expect(novelQueryTermBoost(8, 6)).toBe(0.06);
    expect(novelQueryTermBoost(8, 10)).toBe(0.04);
  });
});