import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock config — no OpenAI key by default
vi.mock("../../src/config.js", () => ({
  config: {
    OPENAI_API_KEY: "",
    SEO_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
    CHAT_CONTEXT_K: 5,
  },
  paths: {
    rootDir: "/tmp",
    outputDir: "/tmp/output",
    rawDataDir: "/tmp/raw_data",
    fetchLogsDir: "/tmp/output/fetch_logs",
    qaJsonPath: "/tmp/output/qa_final.json",
    qaEnrichedJsonPath: "/tmp/output/qa_enriched.json",
    qaEmbeddingsPath: "/tmp/output/qa_embeddings.npy",
    sessionsDir: "/tmp/output/sessions",
    scriptsDir: "/tmp/scripts",
    accessLogsDir: "/tmp/output/access_logs",
    evalsDir: "/tmp/output/evals",
  },
}));

const mockKeywordSearch = vi.fn().mockReturnValue([
  {
    item: {
      id: "abc123def456",
      question: "What is SEO?",
      answer: "SEO stands for Search Engine Optimization",
      keywords: ["SEO", "optimization"],
      category: "basics",
      primary_category: "SEO Strategy",
      categories: ["SEO Strategy", "Technical SEO"],
      intent_labels: ["platform-decision"],
      scenario_tags: ["faq-rich-result"],
      serving_tier: "booster",
      evidence_scope: ["platform"],
      difficulty: "easy",
      evergreen: true,
      source_title: "SEO Meeting",
      source_date: "2024-05-02",
      source_type: "meeting",
      source_collection: "seo-meetings",
      source_url: "",
      extraction_model: "claude-code",
    },
    score: 0.3,
  },
]);

const mockHybridSearch = vi.fn().mockResolvedValue([
  {
    item: {
      id: "abc123def456",
      question: "What is SEO?",
      answer: "SEO stands for Search Engine Optimization",
      keywords: ["SEO", "optimization"],
      category: "basics",
      primary_category: "SEO Strategy",
      categories: ["SEO Strategy", "Technical SEO"],
      intent_labels: ["platform-decision"],
      scenario_tags: ["faq-rich-result"],
      serving_tier: "booster",
      evidence_scope: ["platform"],
      difficulty: "easy",
      evergreen: true,
      source_title: "SEO Meeting",
      source_date: "2024-05-02",
      source_type: "meeting",
      source_collection: "seo-meetings",
      source_url: "",
      extraction_model: "claude-code",
    },
    score: 0.85,
  },
]);

vi.mock("../../src/store/qa-store.js", () => ({
  qaStore: {
    loaded: true,
    count: 10,
    keywordSearch: (...args: unknown[]) => mockKeywordSearch(...args),
    hybridSearch: (...args: unknown[]) => mockHybridSearch(...args),
  },
}));

vi.mock("../../src/services/embedding.js", () => ({
  getEmbedding: vi.fn().mockResolvedValue(new Float32Array(1536)),
}));

import { Hono } from "hono";
import { searchRoute } from "../../src/routes/search.js";
import { config } from "../../src/config.js";

function buildApp() {
  const app = new Hono();
  app.route("/api/v1/search", searchRoute);
  return app;
}

describe("POST /api/v1/search", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns keyword mode when no OpenAI key", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "SEO" }),
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.mode).toBe("keyword");
    expect(body.data.results).toHaveLength(1);
    expect(body.data.results[0].question).toBe("What is SEO?");
    expect(mockKeywordSearch).toHaveBeenCalledWith("SEO", 5, null);
  });

  it("returns hybrid mode when OpenAI key is set", async () => {
    // Temporarily set key
    const original = config.OPENAI_API_KEY;
    (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test-key";

    try {
      const app = buildApp();
      const res = await app.request("/api/v1/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "SEO" }),
      });
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.data.mode).toBe("hybrid");
      expect(mockHybridSearch).toHaveBeenCalled();
    } finally {
      (config as Record<string, unknown>).OPENAI_API_KEY = original;
    }
  });

  it("passes category filter to keyword search", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "SEO", category: "basics" }),
    });
    expect(res.status).toBe(200);
    expect(mockKeywordSearch).toHaveBeenCalledWith("SEO", 5, "basics");
  });

  it("returns 400 for empty query", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "" }),
    });
    expect(res.status).toBe(400);
  });

  it("respects top_k parameter", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "SEO", top_k: 10 }),
    });
    expect(res.status).toBe(200);
    expect(mockKeywordSearch).toHaveBeenCalledWith("SEO", 10, null);
  });

  it("rounds score to 4 decimal places", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "SEO" }),
    });
    const body = await res.json();
    expect(body.data.results[0].score).toBe(0.3);
  });

  it("falls back to keyword when OpenAI returns 429", async () => {
    const original = config.OPENAI_API_KEY;
    (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test-key";
    const { getEmbedding } = await import("../../src/services/embedding.js");
    vi.mocked(getEmbedding).mockRejectedValueOnce(
      Object.assign(new Error("rate limited"), { status: 429 }),
    );

    try {
      const app = buildApp();
      const res = await app.request("/api/v1/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "SEO" }),
      });
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.data.mode).toBe("keyword");
      expect(mockKeywordSearch).toHaveBeenCalled();
    } finally {
      (config as Record<string, unknown>).OPENAI_API_KEY = original;
    }
  });

  it("rethrows non-auth OpenAI errors", async () => {
    const original = config.OPENAI_API_KEY;
    (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test-key";
    const { getEmbedding } = await import("../../src/services/embedding.js");
    vi.mocked(getEmbedding).mockRejectedValueOnce(
      Object.assign(new Error("server error"), { status: 500 }),
    );

    try {
      const app = buildApp();
      const res = await app.request("/api/v1/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "SEO" }),
      });
      expect(res.status).toBe(500);
    } finally {
      (config as Record<string, unknown>).OPENAI_API_KEY = original;
    }
  });

  it("includes source_type, source_collection, source_url in results", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "SEO" }),
    });
    const body = await res.json();
    const result = body.data.results[0];
    expect(result.source_type).toBe("meeting");
    expect(result.source_collection).toBe("seo-meetings");
    expect(result).toHaveProperty("source_url");
    expect(result.extraction_model).toBe("claude-code");
  });

  it("filters keyword results by primary_category and intent_label", async () => {
    mockKeywordSearch.mockReturnValueOnce([
      {
        item: {
          id: "abc123def456",
          question: "What is SEO?",
          answer: "SEO stands for Search Engine Optimization",
          keywords: ["SEO", "optimization"],
          category: "basics",
          primary_category: "SEO Strategy",
          categories: ["SEO Strategy"],
          intent_labels: ["platform-decision"],
          scenario_tags: ["faq-rich-result"],
          serving_tier: "booster",
          evidence_scope: ["platform"],
          difficulty: "easy",
          evergreen: true,
          source_title: "SEO Meeting",
          source_date: "2024-05-02",
          source_type: "meeting",
          source_collection: "seo-meetings",
          source_url: "",
          extraction_model: "claude-code",
        },
        score: 0.3,
      },
      {
        item: {
          id: "other",
          question: "Technical indexing",
          answer: "Indexing answer",
          keywords: ["indexing"],
          category: "technical",
          primary_category: "Technical SEO",
          categories: ["Technical SEO"],
          intent_labels: ["diagnosis"],
          scenario_tags: ["indexing"],
          serving_tier: "canonical",
          evidence_scope: ["site"],
          difficulty: "easy",
          evergreen: true,
          source_title: "SEO Meeting",
          source_date: "2024-05-02",
          source_type: "meeting",
          source_collection: "seo-meetings",
          source_url: "",
          extraction_model: "claude-code",
        },
        score: 0.2,
      },
    ]);

    const app = buildApp();
    const res = await app.request("/api/v1/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: "SEO",
        primary_category: "SEO Strategy",
        intent_label: "platform-decision",
      }),
    });

    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.results).toHaveLength(1);
    expect(body.data.results[0].primary_category).toBe("SEO Strategy");
    expect(body.data.results[0].intent_labels).toContain("platform-decision");
  });

  it("filters keyword results by scenario_tag, serving_tier, and evidence_scope", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: "SEO",
        scenario_tag: "faq-rich-result",
        serving_tier: "booster",
        evidence_scope: "platform",
      }),
    });

    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.results).toHaveLength(1);
    expect(body.data.results[0].scenario_tags).toContain("faq-rich-result");
    expect(body.data.results[0].serving_tier).toBe("booster");
    expect(body.data.results[0].evidence_scope).toContain("platform");
  });

  it("filters keyword results by extraction_model", async () => {
    mockKeywordSearch.mockReturnValueOnce([
      {
        item: {
          id: "abc123def456",
          question: "What is SEO?",
          answer: "SEO stands for Search Engine Optimization",
          keywords: ["SEO", "optimization"],
          category: "basics",
          difficulty: "easy",
          evergreen: true,
          source_title: "SEO Meeting",
          source_date: "2024-05-02",
          source_type: "meeting",
          source_collection: "seo-meetings",
          source_url: "",
          extraction_model: "claude-code",
        },
        score: 0.3,
      },
      {
        item: {
          id: "def456ghi789",
          question: "What is CWV?",
          answer: "Core Web Vitals metrics",
          keywords: ["CWV"],
          category: "basics",
          difficulty: "easy",
          evergreen: true,
          source_title: "SEO Meeting",
          source_date: "2024-05-02",
          source_type: "meeting",
          source_collection: "seo-meetings",
          source_url: "",
          extraction_model: "gpt-4o",
        },
        score: 0.2,
      },
    ]);

    const app = buildApp();
    const res = await app.request("/api/v1/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "SEO", extraction_model: "claude-code" }),
    });

    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.results).toHaveLength(1);
    expect(body.data.results[0].extraction_model).toBe("claude-code");
    expect(mockKeywordSearch).toHaveBeenCalledWith("SEO", 15, null);
  });

  it("over-fetches hybrid results before extraction_model filtering", async () => {
    const original = config.OPENAI_API_KEY;
    (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test-key";

    try {
      const app = buildApp();
      const res = await app.request("/api/v1/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: "SEO",
          top_k: 4,
          extraction_model: "claude-code",
        }),
      });

      expect(res.status).toBe(200);
      expect(mockHybridSearch).toHaveBeenCalledWith(
        "SEO",
        expect.any(Float32Array),
        12,
        null,
      );
    } finally {
      (config as Record<string, unknown>).OPENAI_API_KEY = original;
    }
  });

  it("applies maturity_level boosting without breaking filtered results", async () => {
    mockKeywordSearch.mockReturnValueOnce([
      {
        item: {
          id: "l1-item",
          question: "SEO basics",
          answer: "Basic answer",
          keywords: ["seo"],
          category: "basics",
          primary_category: "SEO Strategy",
          categories: ["SEO Strategy"],
          intent_labels: ["platform-decision"],
          scenario_tags: ["faq-rich-result"],
          serving_tier: "booster",
          evidence_scope: ["platform"],
          difficulty: "easy",
          evergreen: true,
          source_title: "SEO Meeting",
          source_date: "2024-05-02",
          source_type: "meeting",
          source_collection: "seo-meetings",
          source_url: "",
          extraction_model: "claude-code",
          maturity_relevance: "L1",
        },
        score: 0.3,
      },
      {
        item: {
          id: "l4-item",
          question: "Advanced SEO program",
          answer: "Advanced answer",
          keywords: ["seo"],
          category: "basics",
          primary_category: "SEO Strategy",
          categories: ["SEO Strategy"],
          intent_labels: ["platform-decision"],
          scenario_tags: ["faq-rich-result"],
          serving_tier: "booster",
          evidence_scope: ["platform"],
          difficulty: "easy",
          evergreen: true,
          source_title: "SEO Meeting",
          source_date: "2024-05-02",
          source_type: "meeting",
          source_collection: "seo-meetings",
          source_url: "",
          extraction_model: "claude-code",
          maturity_relevance: "L4",
        },
        score: 0.29,
      },
    ]);

    const app = buildApp();
    const res = await app.request("/api/v1/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: "SEO",
        primary_category: "SEO Strategy",
        maturity_level: "L4",
      }),
    });

    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.results).toHaveLength(2);
    expect(body.data.results[0].id).toBe("l4-item");
  });
});
