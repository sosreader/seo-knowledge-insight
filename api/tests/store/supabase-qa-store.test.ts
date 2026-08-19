/**
 * Tests for SupabaseQAStore.
 * Uses mocked supabase-client to avoid real network calls.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { FAKE_ITEMS } from "../setup.js";

// vi.hoisted: variables available inside vi.mock factories (hoisted to top of file)
const { mockSupabaseSelect, mockSupabaseRpc, mockSupabaseCount } = vi.hoisted(
  () => ({
    mockSupabaseSelect: vi.fn(),
    mockSupabaseRpc: vi.fn(),
    mockSupabaseCount: vi.fn(),
  }),
);

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
  supabaseCount: (...args: unknown[]) => mockSupabaseCount(...args),
  supabaseHeaders: () => ({ apikey: "test", Authorization: "Bearer test" }),
}));

// Raw DB rows matching FAKE_ITEMS — 直接 SELECT qa_items 撈到的形狀。
// 不含 primary_category 等 extended retrieval 欄位：live schema（2026-08-19 實測）
// 沒有這些欄位，見 supabase-qa-store.ts 的 QARow 註解。answer 仍在（沒拿掉）。
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

import { SupabaseQAStore } from "../../src/store/supabase-qa-store.js";

describe("SupabaseQAStore", () => {
  let store: SupabaseQAStore;

  beforeEach(async () => {
    // resetAllMocks clears queued mockResolvedValueOnce values (clearAllMocks does not)
    vi.resetAllMocks();
    mockSupabaseCount.mockResolvedValueOnce(FAKE_ITEMS.length);
    // load() 只發一次 supabaseSelect，因為 FAKE_ITEMS.length < PAGE_SIZE(1000)
    mockSupabaseSelect.mockResolvedValueOnce(FAKE_ROWS);

    store = new SupabaseQAStore();
    await store.load();
  });

  it("loads items from Supabase at startup", () => {
    expect(store.loaded).toBe(true);
    expect(store.count).toBe(FAKE_ITEMS.length);
  });

  it("load() 只選 base 欄位——不再發送必失敗的 extended columns 請求（dead path 已移除）", () => {
    // beforeEach 已驗證：整個 load() 只發一次 supabaseCount + 一次 supabaseSelect
    // （不會像舊版那樣先打一次 42703 400 再 fallback 重打）。
    expect(mockSupabaseCount).toHaveBeenCalledTimes(1);
    expect(mockSupabaseSelect).toHaveBeenCalledTimes(1);

    const [, queryString] = mockSupabaseSelect.mock.calls[0]!;
    expect(queryString).not.toContain("primary_category");
    expect(queryString).not.toContain("retrieval_surface_text");
    expect(queryString).not.toContain("booster_target_queries");
    // answer 這次沒拿掉，應該還在 select 欄位裡
    expect(queryString).toMatch(/select=[^&]*\banswer\b/);
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

  // 註：原本這裡有兩個測試餵 mock row 帶 serving_tier/scenario_tags 等 extended
  // 欄位，驗證 keywordSearch 依這些欄位做 booster/scenario 排序偏好。已移除——
  // live schema（2026-08-19 實測）根本沒有這些欄位，這兩個測試驗證的能力在
  // 真實 qa_items 直接 SELECT 路徑下本來就不可能生效，是用假資料通過的假陽性
  // 測試。hybridSearch（RPC 路徑）與 JSON 版 QAStore 不受影響，各自的
  // booster 測試仍在（tests/store/qa-store.test.ts）。

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

  describe("total-count 驅動分頁", () => {
    it("已知總筆數時，並行抓取多分頁，組裝結果依 seq 正確、不受非同步回應順序影響", async () => {
      mockSupabaseCount.mockReset();
      mockSupabaseSelect.mockReset();
      const pageSize = 1000;
      const total = pageSize * 2 + 500; // 3 頁
      mockSupabaseCount.mockResolvedValueOnce(total);

      const makeRow = (seq: number) => ({ ...FAKE_ROWS[0]!, id: `row-${seq}`, seq });

      // 刻意讓 offset=1000 這頁比 offset=0 晚回應，驗證組裝結果仍照頁碼排序，
      // 不是照到達順序。
      mockSupabaseSelect.mockImplementation(
        async (_table: string, queryString: string) => {
          const offset = Number(queryString.match(/offset=(\d+)/)?.[1] ?? "0");
          if (offset === pageSize) {
            await new Promise((resolve) => setTimeout(resolve, 5));
          }
          const size = Math.min(pageSize, total - offset);
          return Array.from({ length: size }, (_, i) => makeRow(offset + i));
        },
      );

      const parallelStore = new SupabaseQAStore();
      await parallelStore.load();

      expect(mockSupabaseSelect).toHaveBeenCalledTimes(3);
      expect(parallelStore.count).toBe(total);
      expect(parallelStore.getBySeq(0)?.seq).toBe(0);
      expect(parallelStore.getBySeq(pageSize - 1)?.seq).toBe(pageSize - 1);
      expect(parallelStore.getBySeq(pageSize)?.seq).toBe(pageSize);
      expect(parallelStore.getBySeq(total - 1)?.seq).toBe(total - 1);
    });

    it("分頁並行度受限於 PAGE_CONCURRENCY(4)，不會一次把所有分頁打出去", async () => {
      mockSupabaseCount.mockReset();
      mockSupabaseSelect.mockReset();
      const pageSize = 1000;
      const total = pageSize * 6; // 6 頁，超過並行度上限
      mockSupabaseCount.mockResolvedValueOnce(total);

      let inFlight = 0;
      let maxInFlight = 0;
      mockSupabaseSelect.mockImplementation(
        async (_table: string, queryString: string) => {
          inFlight += 1;
          maxInFlight = Math.max(maxInFlight, inFlight);
          await new Promise((resolve) => setTimeout(resolve, 1));
          inFlight -= 1;
          const offset = Number(queryString.match(/offset=(\d+)/)?.[1] ?? "0");
          return Array.from({ length: pageSize }, (_, i) => ({
            ...FAKE_ROWS[0]!,
            id: `row-${offset + i}`,
            seq: offset + i,
          }));
        },
      );

      const boundedStore = new SupabaseQAStore();
      await boundedStore.load();

      expect(mockSupabaseSelect).toHaveBeenCalledTimes(6);
      expect(maxInFlight).toBeLessThanOrEqual(4);
      expect(maxInFlight).toBeGreaterThan(1); // 確實有平行，不是退化成循序
      expect(boundedStore.count).toBe(total);
    });

    it("單頁請求失敗會重試一次，重試成功就正常完成 load()", async () => {
      mockSupabaseCount.mockReset();
      mockSupabaseSelect.mockReset();
      mockSupabaseCount.mockResolvedValueOnce(FAKE_ITEMS.length);
      mockSupabaseSelect
        .mockRejectedValueOnce(new Error("Supabase SELECT qa_items failed (503)"))
        .mockResolvedValueOnce(FAKE_ROWS);

      const retryStore = new SupabaseQAStore();
      await retryStore.load();

      expect(mockSupabaseSelect).toHaveBeenCalledTimes(2);
      expect(retryStore.loaded).toBe(true);
      expect(retryStore.count).toBe(FAKE_ITEMS.length);
    });

    it("單頁請求重試後仍失敗，整個 load() 要拋出（不能回傳不完整的 store）", async () => {
      mockSupabaseCount.mockReset();
      mockSupabaseSelect.mockReset();
      mockSupabaseCount.mockResolvedValueOnce(FAKE_ITEMS.length);
      mockSupabaseSelect
        .mockRejectedValueOnce(new Error("Supabase SELECT qa_items failed (503)"))
        .mockRejectedValueOnce(new Error("Supabase SELECT qa_items failed (503)"));

      const failingStore = new SupabaseQAStore();
      await expect(failingStore.load()).rejects.toThrow(
        "Supabase SELECT qa_items failed (503)",
      );
      expect(mockSupabaseSelect).toHaveBeenCalledTimes(2);
      expect(failingStore.loaded).toBe(false);
    });

    it("實際載入筆數與宣告總數不符時會 console.warn 兩個數字（不能靜默通過）", async () => {
      mockSupabaseCount.mockReset();
      mockSupabaseSelect.mockReset();
      mockSupabaseCount.mockResolvedValueOnce(10); // 宣告 10 筆
      mockSupabaseSelect.mockResolvedValueOnce(FAKE_ROWS); // 實際只回 5 筆
      const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

      const mismatchStore = new SupabaseQAStore();
      await mismatchStore.load();

      expect(mismatchStore.count).toBe(FAKE_ITEMS.length);
      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining("10"),
      );
      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining(String(FAKE_ITEMS.length)),
      );
      warnSpy.mockRestore();
    });

    it("supabaseCount 失敗（回傳 -1）時退回循序探頁而非平行猜頁數", async () => {
      mockSupabaseCount.mockReset();
      mockSupabaseSelect.mockReset();
      mockSupabaseCount.mockResolvedValueOnce(-1);
      mockSupabaseSelect
        .mockResolvedValueOnce(FAKE_ROWS)
        .mockResolvedValueOnce([]);

      const fallbackStore = new SupabaseQAStore();
      await fallbackStore.load();

      expect(fallbackStore.loaded).toBe(true);
      expect(fallbackStore.count).toBe(FAKE_ITEMS.length);
    });
  });
});
