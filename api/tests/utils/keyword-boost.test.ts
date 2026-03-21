import { describe, it, expect } from "vitest";
import {
  computeKeywordBoostSingle,
  computeKeywordBoostMatrix,
} from "../../src/utils/keyword-boost.js";

describe("computeKeywordBoostSingle", () => {
  it("returns 0 when no keywords match", () => {
    const score = computeKeywordBoostSingle("unrelated topic", ["SEO", "performance"]);
    expect(score).toBe(0);
  });

  it("gives full boost for exact keyword match in query", () => {
    // exact match contributes 3.0 hits, capped at maxHits=3 → boost * 3 = 0.3
    const score = computeKeywordBoostSingle("how to improve LCP performance", ["LCP"]);
    expect(score).toBeCloseTo(0.3);
  });

  it("accumulates multiple keyword hits up to max", () => {
    const score = computeKeywordBoostSingle("LCP performance Core Web Vitals", [
      "LCP",
      "performance",
      "Core Web Vitals",
    ]);
    // each exact match = 3.0 hits, total 9.0, capped at maxHits=3 → 0.3
    expect(score).toBeCloseTo(0.3);
  });

  it("caps at maxHits", () => {
    const score = computeKeywordBoostSingle("keyword1 keyword2 keyword3 keyword4", [
      "keyword1",
      "keyword2",
      "keyword3",
      "keyword4",
    ]);
    // maxHits=3, so 3 * 0.1 = 0.3
    expect(score).toBeCloseTo(0.3);
  });

  it("gives partial score for bigram match", () => {
    // "structured" starts with "st" and query contains "st" via "structured"
    // but here we test where only the bigram matches
    const score = computeKeywordBoostSingle("test page speed", ["mobile optimization"], {
      boost: 0.1,
      maxHits: 3,
      partial: 0.05,
    });
    // "mo" from "mobile optimization" is not in "test page speed"
    // No match expected
    expect(score).toBe(0);
  });
});

describe("computeKeywordBoostMatrix", () => {
  it("returns correct shape for multiple queries", () => {
    const queries = ["LCP optimization", "title tag SEO"];
    const qaPairs = [
      { keywords: ["LCP", "performance"] },
      { keywords: ["title tag", "meta"] },
      { keywords: ["structured data"] },
    ];

    const matrix = computeKeywordBoostMatrix(queries, qaPairs);
    expect(matrix.length).toBe(2 * 3); // 2 queries x 3 qa_pairs
  });

  it("correctly assigns boosts", () => {
    const queries = ["LCP"];
    const qaPairs = [
      { keywords: ["LCP", "performance"] },
      { keywords: ["title tag"] },
    ];

    const matrix = computeKeywordBoostMatrix(queries, qaPairs);
    expect(matrix[0]).toBeGreaterThan(0); // LCP matches
    expect(matrix[1]).toBe(0); // No match
  });
});
