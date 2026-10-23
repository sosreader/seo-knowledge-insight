import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { MATCH_SQL, PgQAStore, normalizeHitIds, toVectorLiteral, MAX_HIT_IDS } from "../../src/store/pg-qa-store.js";
import { _configurePgClientForTest, pgQuery } from "../../src/store/pg-client.js";
import { pgAvailable, usePgFixture } from "../pg/pg-fixture.js";
import { axisVector, seedQa } from "../pg/qa-seed.js";

describe("toVectorLiteral / normalizeHitIds", () => {
  it("formats pgvector text literal", () => {
    expect(toVectorLiteral([0.5, -1, 2])).toBe("[0.5,-1,2]");
    expect(toVectorLiteral(new Float32Array([1, 0]))).toBe("[1,0]");
  });

  it("rejects empty or non-finite vectors", () => {
    expect(() => toVectorLiteral([])).toThrow();
    expect(() => toVectorLiteral([1, Number.NaN])).toThrow();
    expect(() => toVectorLiteral([Number.POSITIVE_INFINITY])).toThrow();
  });

  it("dedupes, drops blanks and caps at the DB limit (200)", () => {
    expect(normalizeHitIds(["a", "a", "", "b"])).toEqual(["a", "b"]);
    const many = Array.from({ length: 250 }, (_, i) => `id${i}`);
    expect(normalizeHitIds(many)).toHaveLength(MAX_HIT_IDS);
  });
});

const fx = usePgFixture("qa");

const ROWS = [
  { id: "0000000000000001", seq: 2, question: "What is LCP?", category: "Performance", keywords: ["LCP", "Core Web Vitals"], embedding: axisVector(0) },
  { id: "0000000000000002", seq: 1, question: "How to write title tags?", category: "On-Page", keywords: ["title tag"], synonyms: ["標題"], embedding: axisVector(1) },
  { id: "0000000000000003", seq: 3, question: "LCP image optimisation", category: "Performance", keywords: ["LCP", "image"], embedding: axisVector(0, 0.2), freshness: 0.5 },
  { id: "0000000000000004", seq: 4, question: "Legacy item without embedding", category: "Performance", keywords: ["LCP"], embedding: null },
];

describe.skipIf(!pgAvailable)("PgQAStore against app_qa_item (warehouse_rag)", () => {
  const store = new PgQAStore();

  beforeAll(async () => {
    await seedQa(fx.admin(), ROWS);
  });

  beforeEach(() => fx.activate());

  it("loads all QA metadata ordered by seq and indexes by id/seq", async () => {
    await store.load();
    expect(store.loaded).toBe(true);
    expect(store.count).toBe(4);
    expect(store.hasEmbeddings).toBe(true);
    expect(store.allItems.map((i) => i.seq)).toEqual([1, 2, 3, 4]);
    expect(store.getById("0000000000000001")?.question).toBe("What is LCP?");
    expect(store.getBySeq(1)?.id).toBe("0000000000000002");
    const item = store.getById("0000000000000002")!;
    expect(item).toMatchObject({
      primary_category: "On-Page",
      categories: ["On-Page"],
      serving_tier: "canonical",
      retrieval_phrases: ["title tag"],
      synonyms: ["標題"],
      source_collection: "seo-meetings",
    });
  });

  it("hybridSearch returns nearest vectors first and skips NULL embeddings", async () => {
    const hits = await store.hybridSearch("LCP", axisVector(0), 5, null, 0);
    const ids = hits.map((h) => h.item.id);
    expect(ids[0]).toBe("0000000000000001");
    expect(ids).toContain("0000000000000003");
    expect(ids).not.toContain("0000000000000004");
  });

  it("hybridSearch filters by category in SQL and applies minScore", async () => {
    const onPage = await store.hybridSearch("title", axisVector(1), 5, "On-Page", 0);
    expect(onPage.map((h) => h.item.id)).toEqual(["0000000000000002"]);
    const none = await store.hybridSearch("LCP", axisVector(0), 5, null, 99);
    expect(none).toEqual([]);
  });

  it("hybridSearch tolerates topK above the DB cap (LEAST(...,200))", async () => {
    const hits = await store.hybridSearch("LCP", axisVector(0), 500, null, 0);
    expect(hits.length).toBe(3);
  });

  it("match_qa_items is inlined into the caller query (no Function Scan), so the hnsw index can apply", async () => {
    const plan = await pgQuery<{ "QUERY PLAN": string }>(`EXPLAIN ${MATCH_SQL}`, [
      toVectorLiteral(axisVector(0)),
      15,
      null,
    ]);
    const text = plan.map((r) => r["QUERY PLAN"]).join("\n");
    expect(text).toContain("app_qa_item");
    expect(text).not.toMatch(/Function Scan/);
  });

  it("keywordSearch / listQa / categories / collections work in memory", () => {
    expect(store.keywordSearch("LCP", 5).length).toBeGreaterThan(0);
    expect(store.keywordSearch("LCP", 5, "On-Page").map((h) => h.item.id)).not.toContain("0000000000000001");
    expect(store.listQa({ category: "Performance", limit: 10, offset: 0 }).total).toBe(3);
    expect(store.categories()).toEqual(expect.arrayContaining(["Performance", "On-Page"]));
    expect(store.collections()[0]).toMatchObject({ source_collection: "seo-meetings", count: 4 });
  });

  it("incrementSearchHitCount bumps only the given ids, once per id", async () => {
    await store.incrementSearchHitCount(["0000000000000001", "0000000000000001", "0000000000000003"]);
    const { rows } = await fx
      .admin()
      .query<{ id: string; search_hit_count: number }>("SELECT id, search_hit_count FROM app_qa_item ORDER BY id");
    expect(rows.map((r) => r.search_hit_count)).toEqual([1, 0, 1, 0]);
  });

  it("incrementSearchHitCount caps oversized batches instead of hitting the DB RAISE", async () => {
    const ids = ["0000000000000002", ...Array.from({ length: 300 }, (_, i) => `x${i}`)];
    await store.incrementSearchHitCount(ids);
    const { rows } = await fx.admin().query("SELECT search_hit_count FROM app_qa_item WHERE id = '0000000000000002'");
    expect(rows[0].search_hit_count).toBe(1);
  });

  it("incrementSearchHitCount is a no-op for empty input and never throws", async () => {
    await expect(store.incrementSearchHitCount([])).resolves.toBeUndefined();
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    await _configurePgClientForTest({ secretFile: "" });
    await expect(store.incrementSearchHitCount(["0000000000000001"])).resolves.toBeUndefined();
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });

  it("reload() picks up freshness_score written by another process (update-freshness CronJob)", async () => {
    const id = "0000000000000001";
    await store.load();
    const before = store.getById(id)!.freshness_score;
    try {
      await fx.admin().query("UPDATE app_qa_item SET freshness_score = 0.321 WHERE id = $1", [id]);
      expect(store.getById(id)!.freshness_score).toBe(before);

      const result = await store.reload();

      expect(result).toEqual({ ok: true, count: 4 });
      expect(store.getById(id)!.freshness_score).toBeCloseTo(0.321);
      expect(store.getBySeq(2)!.freshness_score).toBeCloseTo(0.321);
    } finally {
      await fx.admin().query("UPDATE app_qa_item SET freshness_score = $2 WHERE id = $1", [id, before]);
    }
  });

  it("reload() keeps the loaded data and reports db_unavailable when the DB is unreachable", async () => {
    await store.load();
    await _configurePgClientForTest({ secretFile: "" });
    const result = await store.reload();
    expect(result).toEqual({ ok: false, code: "db_unavailable" });
    expect(store.count).toBe(4);
    expect(store.getById("0000000000000001")).toBeDefined();
  });

  it("load() propagates DbUnavailableError so ensureQaStoreLoaded can degrade", async () => {
    await _configurePgClientForTest({ secretFile: "" });
    await expect(new PgQAStore().load()).rejects.toMatchObject({ code: "db_unavailable" });
  });
});
