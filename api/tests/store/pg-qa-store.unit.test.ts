/**
 * PgQAStore 的記憶體內行為與重排（mock pgQuery，不連 DB）。
 * 自 Supabase 版測試移植；SQL 與權限由 tests/store/pg-qa-store.test.ts 對真 PG 驗證。
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { FAKE_ITEMS } from "../setup.js";

// vi.hoisted: variables available inside vi.mock factories (hoisted to top of file)
const { mockPgQuery } = vi.hoisted(() => ({ mockPgQuery: vi.fn() }));

// Mock config — PG mode
vi.mock("../../src/config.js", () => ({
  config: {
    VW_DB_SECRET_FILE_RAG: "/var/run/secrets/db-rag",
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

vi.mock("../../src/store/pg-client.js", () => ({
  hasPg: () => true,
  pgQuery: (...args: unknown[]) => mockPgQuery(...args),
}));

// Raw DB rows matching FAKE_ITEMS — 啟動 SELECT app_qa_item 撈到的形狀（見 qa-rerank.ts 的 QARow）。
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
  maturity_relevance: item.maturity_relevance ?? null,
  synonyms: [...item.synonyms],
  freshness_score: item.freshness_score,
  search_hit_count: item.search_hit_count,
}));

import { PgQAStore } from "../../src/store/pg-qa-store.js";
import { DbTimeoutError } from "../../src/store/store-errors.js";

describe("PgQAStore (mocked pgQuery)", () => {
  let store: PgQAStore;

  beforeEach(async () => {
    // resetAllMocks clears queued mockResolvedValueOnce values (clearAllMocks does not)
    vi.resetAllMocks();
    mockPgQuery.mockResolvedValueOnce(FAKE_ROWS);

    store = new PgQAStore();
    await store.load();
  });

  it("loads items at startup with a single query", () => {
    expect(store.loaded).toBe(true);
    expect(store.count).toBe(FAKE_ITEMS.length);
    expect(mockPgQuery).toHaveBeenCalledTimes(1);
  });

  it("load() selects base columns only (same ranking inputs as the Supabase era), with a 25s timeout", () => {
    const [sql, params, options] = mockPgQuery.mock.calls[0]!;
    expect(sql).toMatch(/FROM app_qa_item ORDER BY seq ASC NULLS LAST, id ASC$/);
    expect(sql).not.toContain("primary_category");
    expect(sql).not.toContain("retrieval_surface_text");
    expect(sql).not.toContain("booster_target_queries");
    expect(sql).not.toContain("embedding");
    expect(sql).toMatch(/\banswer\b/);
    expect(params).toEqual([]);
    expect(options).toEqual({ timeoutMs: 25_000 });
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

  it("hybridSearch calls match_qa_items and re-ranks", async () => {
    const mockCandidates = FAKE_ROWS.slice(0, 3).map((row, i) => ({
      ...row,
      similarity: 0.9 - i * 0.1,
    }));
    mockPgQuery.mockResolvedValueOnce(mockCandidates);

    const queryEmbedding = new Float32Array(1536).fill(0.1);
    const results = await store.hybridSearch(
      "LCP performance",
      queryEmbedding,
      3,
    );

    const [sql, params] = mockPgQuery.mock.calls[1]!;
    expect(sql).toContain("SELECT * FROM match_qa_items($1::vector, LEAST($2::int, 200), $3::text, NULL, NULL)");
    // topK=3 * OVER_RETRIEVE_FACTOR=3
    expect(params).toEqual([expect.stringMatching(/^\[0\.1/), 9, null]);
    expect(results.length).toBeGreaterThan(0);
    for (const r of results) {
      expect(r.score).toBeGreaterThanOrEqual(0);
    }
  });

  it("hybridSearch passes the category filter to match_qa_items", async () => {
    mockPgQuery.mockResolvedValueOnce([]);
    await store.hybridSearch("SEO", new Float32Array(1536).fill(0.01), 5, "SEO Technical");

    const [, params] = mockPgQuery.mock.calls[1]!;
    expect(params).toEqual([expect.any(String), 15, "SEO Technical"]);
  });

  it("hybridSearch rethrows DB errors", async () => {
    mockPgQuery.mockRejectedValueOnce(new Error("Network error"));
    await expect(
      store.hybridSearch("test", new Float32Array(1536).fill(0.01), 5),
    ).rejects.toThrow("Network error");
  });

  it("hybridSearch rejects an all-zero-length embedding before hitting the DB", async () => {
    await expect(store.hybridSearch("test", [], 5)).rejects.toThrow(/non-empty finite/);
    expect(mockPgQuery).toHaveBeenCalledTimes(1);
  });

  it("hasEmbeddings is always true for the PG store", () => {
    expect(store.hasEmbeddings).toBe(true);
  });
});

describe("PgQAStore.reload (mocked pgQuery)", () => {
  let store: PgQAStore;

  beforeEach(async () => {
    vi.resetAllMocks();
    mockPgQuery.mockResolvedValueOnce(FAKE_ROWS);
    store = new PgQAStore();
    await store.load();
  });

  it("re-runs the same LOAD_SQL with the 25s timeout", async () => {
    const [loadSql, , loadOptions] = mockPgQuery.mock.calls[0]!;
    mockPgQuery.mockResolvedValueOnce(FAKE_ROWS);
    await store.reload();
    const [sql, params, options] = mockPgQuery.mock.calls[1]!;
    expect(sql).toBe(loadSql);
    expect(params).toEqual([]);
    expect(options).toEqual(loadOptions);
  });

  it("swaps items, idIndex and seqIndex together on success (new freshness_score visible)", async () => {
    const first = FAKE_ROWS[0]!;
    const before = store.getById(first.id)!;
    const refreshed = FAKE_ROWS.map((r) => (r.id === first.id ? { ...r, freshness_score: 0.123 } : r));
    mockPgQuery.mockResolvedValueOnce(refreshed);

    const result = await store.reload();

    expect(result).toEqual({ ok: true, count: FAKE_ROWS.length });
    expect(store.getById(first.id)!.freshness_score).toBeCloseTo(0.123);
    expect(store.getBySeq(first.seq)!.freshness_score).toBeCloseTo(0.123);
    expect(store.allItems.find((i) => i.id === first.id)!.freshness_score).toBeCloseTo(0.123);
    // 舊物件沒有被原地改動（不可變換入）
    expect(before.freshness_score).toBe(first.freshness_score);
  });

  it("reflects added and removed rows", async () => {
    const [removed, ...rest] = FAKE_ROWS;
    const added = { ...FAKE_ROWS[0]!, id: "ffffffffffffffff", seq: 9999 };
    mockPgQuery.mockResolvedValueOnce([...rest, added]);

    await store.reload();

    expect(store.getById(removed!.id)).toBeUndefined();
    expect(store.getBySeq(9999)?.id).toBe("ffffffffffffffff");
    expect(store.count).toBe(FAKE_ROWS.length);
  });

  it("keeps the previous data and returns the fixed code when the query fails", async () => {
    const countBefore = store.count;
    mockPgQuery.mockRejectedValueOnce(new DbTimeoutError());

    const result = await store.reload();

    expect(result).toEqual({ ok: false, code: "db_timeout" });
    expect(store.count).toBe(countBefore);
    expect(store.loaded).toBe(true);
    expect(store.getBySeq(1)).toBeDefined();
  });

  it("maps unknown errors to reload_failed without leaking the message", async () => {
    mockPgQuery.mockRejectedValueOnce(new Error("password authentication failed host=db.internal"));
    const result = await store.reload();
    expect(result).toEqual({ ok: false, code: "reload_failed" });
  });

  it("keeps the previous data when a row fails to map (no half-loaded state)", async () => {
    const countBefore = store.count;
    mockPgQuery.mockResolvedValueOnce([FAKE_ROWS[0], null]);
    const result = await store.reload();
    expect(result).toEqual({ ok: false, code: "reload_failed" });
    expect(store.count).toBe(countBefore);
    expect(store.getById(FAKE_ROWS[1]!.id)).toBeDefined();
  });

  it("refuses to replace existing data with an empty result", async () => {
    const countBefore = store.count;
    mockPgQuery.mockResolvedValueOnce([]);
    const result = await store.reload();
    expect(result).toEqual({ ok: false, code: "empty_result" });
    expect(store.count).toBe(countBefore);
  });

  it("accepts an empty result when nothing was loaded yet", async () => {
    const fresh = new PgQAStore();
    mockPgQuery.mockResolvedValueOnce([]);
    expect(await fresh.reload()).toEqual({ ok: true, count: 0 });
    expect(fresh.loaded).toBe(true);
  });

  it("serves reads from the old snapshot while a reload is still in flight", async () => {
    let resolveSelect!: (rows: unknown[]) => void;
    mockPgQuery.mockImplementationOnce(() => new Promise((resolve) => (resolveSelect = resolve)));
    const pending = store.reload();

    expect(store.getBySeq(1)).toBeDefined();
    expect(store.count).toBe(FAKE_ROWS.length);

    resolveSelect(FAKE_ROWS.slice(0, 1));
    expect(await pending).toEqual({ ok: true, count: 1 });
    expect(store.count).toBe(1);
  });
});
