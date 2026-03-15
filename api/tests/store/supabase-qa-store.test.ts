/**
 * Tests for SupabaseQAStore.
 * Uses mocked supabase-client to avoid real network calls.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { FAKE_ITEMS } from "../setup.js";

// vi.hoisted: variables available inside vi.mock factories (hoisted to top of file)
const { mockSupabaseSelect, mockSupabaseRpc } = vi.hoisted(() => ({
  mockSupabaseSelect: vi.fn(),
  mockSupabaseRpc: vi.fn(),
}));

// Mock config — Supabase enabled
vi.mock("../../src/config.js", () => ({
  config: {
    SUPABASE_URL: "https://test.supabase.co",
    SUPABASE_ANON_KEY: "test-anon-key",
    SEO_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
    CHAT_CONTEXT_K: 5,
  },
  paths: { outputDir: "/tmp" },
}));

vi.mock("../../src/store/supabase-client.js", () => ({
  hasSupabase: () => true,
  supabaseSelect: (...args: unknown[]) => mockSupabaseSelect(...args),
  supabaseRpc: (...args: unknown[]) => mockSupabaseRpc(...args),
  supabaseHeaders: () => ({ apikey: "test", Authorization: "Bearer test" }),
}));

// Raw DB rows matching FAKE_ITEMS
const FAKE_ROWS = FAKE_ITEMS.map((item) => ({
  id: item.id,
  seq: item.seq,
  question: item.question,
  answer: item.answer,
  keywords: [...item.keywords],
  confidence: item.confidence,
  category: item.category,
  difficulty: item.difficulty,
  evergreen: item.evergreen,
  source_title: item.source_title,
  source_date: item.source_date,
  source_type: item.source_type,
  source_collection: item.source_collection,
  source_url: item.source_url,
  is_merged: item.is_merged,
  extraction_model: item.extraction_model ?? null,
  primary_category: item.primary_category ?? item.category,
  categories: [...(item.categories ?? [item.category])],
  intent_labels: [...(item.intent_labels ?? [])],
  scenario_tags: [...(item.scenario_tags ?? [])],
  serving_tier: item.serving_tier ?? "canonical",
  retrieval_phrases: [...(item.retrieval_phrases ?? item.keywords)],
  retrieval_surface_text:
    item.retrieval_surface_text ?? `${item.question}\n${item.answer}`,
  content_granularity: item.content_granularity ?? null,
  evidence_scope: [...(item.evidence_scope ?? [])],
  booster_target_queries: [...(item.booster_target_queries ?? [])],
  hard_negative_terms: [...(item.hard_negative_terms ?? [])],
  synonyms: [...item.synonyms],
  freshness_score: item.freshness_score,
  search_hit_count: item.search_hit_count,
}));

import { SupabaseQAStore } from "../../src/store/supabase-qa-store.js";

describe("SupabaseQAStore", () => {
  let store: SupabaseQAStore;

  beforeEach(async () => {
    // resetAllMocks clears queued mockResolvedValueOnce values (clearAllMocks does not)
    vi.resetAllMocks();
    // load() only makes ONE supabaseSelect call because FAKE_ROWS.length < PAGE_SIZE(500)
    mockSupabaseSelect.mockResolvedValueOnce(FAKE_ROWS);

    store = new SupabaseQAStore();
    await store.load();
  });

  it("loads items from Supabase at startup", () => {
    expect(store.loaded).toBe(true);
    expect(store.count).toBe(FAKE_ITEMS.length);
  });

  it("falls back to base schema when extended retrieval columns are missing", async () => {
    const legacyRows = FAKE_ROWS.map((row) => {
      const {
        primary_category,
        categories,
        intent_labels,
        scenario_tags,
        serving_tier,
        retrieval_phrases,
        retrieval_surface_text,
        content_granularity,
        evidence_scope,
        booster_target_queries,
        hard_negative_terms,
        ...legacy
      } = row;
      return legacy;
    });
    mockSupabaseSelect.mockReset();
    mockSupabaseSelect
      .mockRejectedValueOnce(
        new Error(
          'Supabase SELECT qa_items failed (400): {"code":"42703","message":"column qa_items.primary_category does not exist"}',
        ),
      )
      .mockResolvedValueOnce(legacyRows);

    const legacyStore = new SupabaseQAStore();
    await legacyStore.load();

    expect(mockSupabaseSelect).toHaveBeenCalledTimes(2);
    expect(legacyStore.loaded).toBe(true);
    expect(legacyStore.count).toBe(FAKE_ITEMS.length);
    const first = legacyStore.getById(FAKE_ITEMS[0]!.id);
    expect(first).toBeDefined();
    expect(first!.primary_category).toBe(first!.category);
    expect(first!.categories).toEqual([first!.category]);
  });

  it("getById returns correct item", () => {
    const item = store.getById(FAKE_ITEMS[0]!.id);
    expect(item).toBeDefined();
    expect(item!.question).toBe(FAKE_ITEMS[0]!.question);
  });

  it("getById returns undefined for unknown id", () => {
    expect(store.getById("unknown_id_123456")).toBeUndefined();
  });

  it("getBySeq returns correct item", () => {
    const item = store.getBySeq(1);
    expect(item).toBeDefined();
    expect(item!.seq).toBe(1);
  });

  it("categories() returns sorted list", () => {
    const cats = store.categories();
    expect(cats.length).toBeGreaterThan(0);
    expect(cats).toContain("SEO Technical");
  });

  it("collections() returns list with source info", () => {
    const colls = store.collections();
    expect(colls.length).toBeGreaterThan(0);
    const meeting = colls.find((c) => c.source_collection === "seo-meetings");
    expect(meeting).toBeDefined();
    expect(meeting!.source_type).toBe("meeting");
    expect(meeting!.count).toBeGreaterThan(0);
  });

  it("listQa with no filters returns all items", () => {
    const { items, total } = store.listQa({ limit: 100 });
    expect(total).toBe(FAKE_ITEMS.length);
    expect(items.length).toBe(FAKE_ITEMS.length);
  });

  it("listQa filters by category", () => {
    const { items } = store.listQa({ category: "SEO Technical", limit: 100 });
    for (const item of items) {
      expect(item.category).toBe("SEO Technical");
    }
  });

  it("listQa filters by source_type", () => {
    const { items, total } = store.listQa({ source_type: "article" });
    expect(total).toBe(1);
    expect(items[0]!.source_type).toBe("article");
  });

  it("listQa filters by keyword", () => {
    const { items } = store.listQa({ keyword: "LCP" });
    expect(items.length).toBeGreaterThan(0);
    for (const item of items) {
      const hasKw =
        item.question.toLowerCase().includes("lcp") ||
        item.answer.toLowerCase().includes("lcp") ||
        item.keywords.some((k) => k.toLowerCase().includes("lcp"));
      expect(hasKw).toBe(true);
    }
  });

  it("listQa pagination works", () => {
    const { items, total } = store.listQa({ limit: 2, offset: 0 });
    expect(items.length).toBe(2);
    expect(total).toBe(FAKE_ITEMS.length);

    const { items: page2 } = store.listQa({ limit: 2, offset: 2 });
    expect(page2[0]!.id).not.toBe(items[0]!.id);
  });

  it("keywordSearch returns scored results", () => {
    const results = store.keywordSearch("LCP performance", 3);
    expect(results.length).toBeGreaterThan(0);
    for (const r of results) {
      expect(r.score).toBeGreaterThan(0);
    }
  });

  it("keywordSearch returns retrieval metadata in items", () => {
    const [first] = store.keywordSearch("AI SEO", 3);
    expect(first).toBeDefined();
    expect(first!.item.categories).toBeDefined();
    expect(first!.item.serving_tier).toBeDefined();
  });

  it("keywordSearch filters by category", () => {
    const results = store.keywordSearch("SEO", 10, "SEO Technical");
    for (const r of results) {
      expect(r.item.category).toBe("SEO Technical");
    }
  });

  it("hybridSearch calls supabaseRpc and re-ranks", async () => {
    const mockCandidates = FAKE_ROWS.slice(0, 3).map((row, i) => ({
      ...row,
      similarity: 0.9 - i * 0.1,
    }));
    mockSupabaseRpc.mockResolvedValueOnce(mockCandidates);

    const queryEmbedding = new Float32Array(1536).fill(0.1);
    const results = await store.hybridSearch(
      "LCP performance",
      queryEmbedding,
      3,
    );

    expect(mockSupabaseRpc).toHaveBeenCalledWith(
      "match_qa_items",
      expect.objectContaining({
        match_count: 9, // topK=3 * OVER_RETRIEVE_FACTOR=3
        filter_category: null,
      }),
    );
    expect(results.length).toBeGreaterThan(0);
    for (const r of results) {
      expect(r.score).toBeGreaterThanOrEqual(0);
    }
  });

  it("keywordSearch prefers targeted booster for AI scenario query", () => {
    const [first] = store.keywordSearch("AI SEO SGE", 3);
    expect(first).toBeDefined();
    expect(first!.item.serving_tier).toBe("booster");
  });

  it("keywordSearch prefers technical video metadata matches over generic indexing", async () => {
    mockSupabaseSelect.mockReset();
    mockSupabaseSelect.mockResolvedValueOnce([
      {
        ...FAKE_ROWS[0],
        id: "video-metadata",
        question: "How to implement VideoObject structured data?",
        answer: "Add JSON-LD VideoObject and monitor Video Appearance.",
        keywords: ["VideoObject", "structured data", "video"],
        category: "索引與檢索",
        primary_category: "索引與檢索",
        categories: ["索引與檢索", "技術SEO"],
        scenario_tags: ["video-seo"],
        retrieval_phrases: ["videoobject structured data", "video appearance"],
        retrieval_surface_text:
          "videoobject structured data video appearance json-ld",
      },
      {
        ...FAKE_ROWS[0],
        id: "video-indexing",
        question: "Why are videos not indexed?",
        answer: "Check canonical and crawlability.",
        keywords: ["video", "indexing"],
        category: "索引與檢索",
        primary_category: "索引與檢索",
        categories: ["索引與檢索"],
        scenario_tags: [],
        retrieval_phrases: ["video indexing"],
        retrieval_surface_text: "video indexing canonical crawlability",
      },
    ]);

    const localStore = new SupabaseQAStore();
    await localStore.load();

    const [first] = localStore.keywordSearch(
      "影片 SEO VideoObject 結構化資料 影片索引",
      2,
    );
    expect(first).toBeDefined();
    expect(first!.item.id).toBe("video-metadata");
  });

  it("hybridSearch passes category filter to RPC", async () => {
    mockSupabaseRpc.mockResolvedValueOnce([]);
    await store.hybridSearch("SEO", new Float32Array(1536), 5, "SEO Technical");

    expect(mockSupabaseRpc).toHaveBeenCalledWith(
      "match_qa_items",
      expect.objectContaining({
        filter_category: "SEO Technical",
      }),
    );
  });

  it("hybridSearch rethrows RPC error", async () => {
    mockSupabaseRpc.mockRejectedValueOnce(new Error("Network error"));
    await expect(
      store.hybridSearch("test", new Float32Array(1536), 5),
    ).rejects.toThrow("Network error");
  });

  it("hasEmbeddings is always true for Supabase store", () => {
    expect(store.hasEmbeddings).toBe(true);
  });
});
