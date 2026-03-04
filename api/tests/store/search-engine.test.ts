import { describe, it, expect } from "vitest";
import { SearchEngine, type QADict } from "../../src/store/search-engine.js";
import { normalizeL2 } from "../../src/utils/cosine-similarity.js";

const FAKE_QA: readonly QADict[] = [
  {
    id: "aa",
    question: "What is LCP?",
    answer: "LCP measures loading performance.",
    keywords: ["LCP", "Core Web Vitals"],
    category: "Technical",
    _enrichment: { synonyms: ["largest contentful paint"], freshness_score: 1.0 },
  },
  {
    id: "bb",
    question: "How to write title tags?",
    answer: "Include keyword near beginning.",
    keywords: ["title tag", "meta"],
    category: "On-Page",
    _enrichment: { synonyms: ["meta title"], freshness_score: 0.9 },
  },
  {
    id: "cc",
    question: "What is structured data?",
    answer: "Schema.org in JSON-LD format.",
    keywords: ["structured data", "JSON-LD"],
    category: "Technical",
    _enrichment: { synonyms: [], freshness_score: 1.0 },
  },
];

// 3 items x 4 dims (simple deterministic embeddings)
const DIM = 4;
const EMB = new Float32Array([
  1, 0, 0, 0, // item 0: along x-axis
  0, 1, 0, 0, // item 1: along y-axis
  0, 0, 1, 0, // item 2: along z-axis
]);

describe("SearchEngine", () => {
  it("throws if embeddings size mismatches", () => {
    expect(
      () => new SearchEngine(FAKE_QA, new Float32Array(10), 4),
    ).toThrow("qaPairs");
  });

  it("returns results sorted by score descending", () => {
    const engine = new SearchEngine(FAKE_QA, EMB, DIM);

    // Query embedding similar to item 0
    const queryEmb = normalizeL2(new Float32Array([0.9, 0.1, 0, 0]));

    const results = engine.search("LCP performance", queryEmb, 3, null, 0);
    expect(results.length).toBeGreaterThan(0);
    expect(results[0]!.qa.id).toBe("aa");

    // Scores should be descending
    for (let i = 1; i < results.length; i++) {
      expect(results[i]!.score).toBeLessThanOrEqual(results[i - 1]!.score);
    }
  });

  it("filters by category", () => {
    const engine = new SearchEngine(FAKE_QA, EMB, DIM);
    const queryEmb = normalizeL2(new Float32Array([0.5, 0.5, 0.5, 0]));

    const results = engine.search("something", queryEmb, 10, "On-Page", 0);
    for (const r of results) {
      expect(r.qa.category).toBe("On-Page");
    }
  });

  it("respects minScore threshold", () => {
    const engine = new SearchEngine(FAKE_QA, EMB, DIM);
    const queryEmb = normalizeL2(new Float32Array([1, 0, 0, 0]));

    const results = engine.search("test", queryEmb, 10, null, 0.5);
    for (const r of results) {
      expect(r.score).toBeGreaterThanOrEqual(0.5);
    }
  });

  it("applies keyword boost", () => {
    const engine = new SearchEngine(FAKE_QA, EMB, DIM);

    // Query embedding equidistant to all items
    const queryEmb = normalizeL2(new Float32Array([0.33, 0.33, 0.33, 0]));

    // Query text matches "LCP" keyword of item 0
    const results = engine.search("LCP", queryEmb, 3, null, 0);
    // Item 0 should rank higher due to keyword boost
    expect(results[0]!.qa.id).toBe("aa");
  });
});
