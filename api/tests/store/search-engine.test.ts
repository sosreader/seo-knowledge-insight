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
    _enrichment: {
      synonyms: ["largest contentful paint"],
      freshness_score: 1.0,
    },
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
  1,
  0,
  0,
  0, // item 0: along x-axis
  0,
  1,
  0,
  0, // item 1: along y-axis
  0,
  0,
  1,
  0, // item 2: along z-axis
]);

describe("SearchEngine", () => {
  it("throws if embeddings size mismatches", () => {
    expect(() => new SearchEngine(FAKE_QA, new Float32Array(10), 4)).toThrow(
      "qaPairs",
    );
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

  it("prefers video seo results when technical and video metadata align", () => {
    const qa: readonly QADict[] = [
      {
        id: "video",
        question: "How to implement VideoObject structured data?",
        answer:
          "Use JSON-LD VideoObject markup and monitor Video Appearance eligibility.",
        keywords: ["VideoObject", "structured data", "video"],
        category: "索引與檢索",
        primary_category: "索引與檢索",
        categories: ["索引與檢索", "技術SEO"],
        scenario_tags: ["video-seo"],
        retrieval_phrases: ["videoobject structured data", "video appearance"],
        retrieval_surface_text:
          "VideoObject structured data video appearance json-ld",
        _enrichment: { synonyms: [], freshness_score: 1.0 },
      },
      {
        id: "index",
        question: "Why are videos not indexed?",
        answer: "Check crawlability and canonical consistency.",
        keywords: ["video", "indexing"],
        category: "索引與檢索",
        primary_category: "索引與檢索",
        categories: ["索引與檢索"],
        retrieval_phrases: ["video indexing"],
        retrieval_surface_text: "video indexing canonical crawlability",
        _enrichment: { synonyms: [], freshness_score: 1.0 },
      },
    ];
    const engine = new SearchEngine(
      qa,
      new Float32Array([1, 0, 0, 0, 1, 0, 0, 0]),
      DIM,
    );
    const queryEmb = normalizeL2(new Float32Array([1, 0, 0, 0]));

    const results = engine.search(
      "影片 SEO VideoObject 結構化資料 影片索引",
      queryEmb,
      2,
      null,
      0,
    );

    expect(results[0]!.qa.id).toBe("video");
  });

  it("prefers ai traffic tracking results for ai referral queries", () => {
    const qa: readonly QADict[] = [
      {
        id: "ai-traffic",
        question: "How to track ChatGPT and Perplexity traffic share?",
        answer:
          "Use GA4 referral analysis to monitor AI traffic share across ChatGPT, Perplexity, and Gemini.",
        keywords: ["ChatGPT", "Perplexity", "Gemini", "AI traffic"],
        category: "搜尋表現分析",
        primary_category: "搜尋表現分析",
        categories: ["搜尋表現分析", "GA與數據追蹤", "演算法與趨勢"],
        scenario_tags: ["ai-referral-traffic"],
        retrieval_phrases: ["ai traffic share", "chatgpt perplexity gemini"],
        retrieval_surface_text:
          "chatgpt perplexity gemini ai traffic share ga4 referral",
        _enrichment: { synonyms: [], freshness_score: 1.0 },
      },
      {
        id: "ctr",
        question: "Does low CTR mean there is an SEO issue?",
        answer: "Not always. Analyze SERP changes first.",
        keywords: ["CTR", "SEO"],
        category: "搜尋表現分析",
        primary_category: "搜尋表現分析",
        categories: ["搜尋表現分析"],
        retrieval_phrases: ["ctr seo"],
        retrieval_surface_text: "ctr serp seo issue",
        _enrichment: { synonyms: [], freshness_score: 1.0 },
      },
    ];
    const engine = new SearchEngine(
      qa,
      new Float32Array([1, 0, 0, 0, 1, 0, 0, 0]),
      DIM,
    );
    const queryEmb = normalizeL2(new Float32Array([1, 0, 0, 0]));

    const results = engine.search(
      "AI 流量佔比 ChatGPT Perplexity Gemini AI SEO 策略",
      queryEmb,
      2,
      null,
      0,
    );

    expect(results[0]!.qa.id).toBe("ai-traffic");
  });

  it("promotes candidates that cover novel query terms during reranking", () => {
    const qa: readonly QADict[] = [
      {
        id: "canonical",
        question: "How to fix canonical conflicts?",
        answer: "Audit canonical chains and coverage.",
        keywords: ["canonical", "coverage"],
        category: "索引與檢索",
        primary_category: "索引與檢索",
        categories: ["索引與檢索"],
        retrieval_phrases: ["canonical coverage"],
        retrieval_surface_text: "canonical coverage indexing",
        _enrichment: { synonyms: [], freshness_score: 1.0 },
      },
      {
        id: "waf",
        question: "How does WAF block Googlebot?",
        answer: "Inspect WAF logs and unblock Googlebot requests.",
        keywords: ["WAF", "Googlebot"],
        category: "技術SEO",
        primary_category: "技術SEO",
        categories: ["技術SEO", "索引與檢索"],
        retrieval_phrases: ["waf googlebot"],
        retrieval_surface_text: "waf googlebot blocked crawling",
        _enrichment: { synonyms: [], freshness_score: 1.0 },
      },
      {
        id: "generic",
        question: "What are indexing errors?",
        answer: "Indexing issues can come from many sources.",
        keywords: ["indexing"],
        category: "索引與檢索",
        primary_category: "索引與檢索",
        categories: ["索引與檢索"],
        retrieval_phrases: ["indexing issues"],
        retrieval_surface_text: "indexing issues generic",
        _enrichment: { synonyms: [], freshness_score: 1.0 },
      },
    ];
    const engine = new SearchEngine(
      qa,
      new Float32Array([1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]),
      DIM,
    );
    const queryEmb = normalizeL2(new Float32Array([1, 0, 0, 0]));

    const results = engine.search(
      "檢索未索引增加 WAF 封鎖 Googlebot canonical",
      queryEmb,
      3,
      null,
      0,
    );

    expect(results[0]!.qa.id).toBe("waf");
    expect(results[1]!.qa.id).toBe("canonical");
  });
});
