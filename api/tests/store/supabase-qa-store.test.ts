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

// Row shape returned by 直接 SELECT qa_items（load() 用）。
// 不含 answer、不含 primary_category 等 extended retrieval 欄位——對應 live schema
// 實測結果（qa_items 沒有這些欄位），見 supabase-qa-store.ts 的 QARow 註解。
const FAKE_ROWS = FAKE_ITEMS.map((item) => ({
  id: item.id,
  seq: item.seq,
  question: item.question,
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

// Row shape returned by 補撈 answer 的 `select=id,answer` 查詢。
const FAKE_ANSWER_ROWS = FAKE_ITEMS.map((item) => ({
  id: item.id,
  answer: item.answer,
}));

// Row shape returned by match_qa_items() RPC — 本來就含 answer + similarity，不受
// startup select 拿掉 answer 這件事影響。
const FAKE_MATCH_ROWS = FAKE_ROWS.map((row, i) => ({
  ...row,
  answer: FAKE_ITEMS[i]!.answer,
  similarity: 0.9,
}));

import { SupabaseQAStore } from "../../src/store/supabase-qa-store.js";

describe("SupabaseQAStore", () => {
  let store: SupabaseQAStore;

  beforeEach(async () => {
    // resetAllMocks clears queued mockResolvedValueOnce values (clearAllMocks does not)
    vi.resetAllMocks();
    mockSupabaseCount.mockResolvedValueOnce(FAKE_ITEMS.length);
    // load() 只發一次 supabaseSelect，因為 FAKE_ITEMS.length < PAGE_SIZE(2000)
    mockSupabaseSelect.mockResolvedValueOnce(FAKE_ROWS);

    store = new SupabaseQAStore();
    await store.load();
  });

  it("loads items from Supabase at startup", () => {
    expect(store.loaded).toBe(true);
    expect(store.count).toBe(FAKE_ITEMS.length);
  });

  it("load() 只選 base 欄位——不含 answer，不再發送必失敗的 extended columns 請求", () => {
    // beforeEach 已驗證：整個 load() 只發一次 supabaseSelect（不會像舊版那樣
    // 先打一次 42703 400 再 fallback 重打）。
    expect(mockSupabaseCount).toHaveBeenCalledTimes(1);
    expect(mockSupabaseSelect).toHaveBeenCalledTimes(1);

    const [, queryString] = mockSupabaseSelect.mock.calls[0]!;
    expect(queryString).not.toContain("primary_category");
    expect(queryString).not.toContain("retrieval_surface_text");
    expect(queryString).not.toContain("booster_target_queries");
    expect(queryString).toMatch(/select=[^&]*question/);
    // "answer" 不該出現在 select 欄位清單裡（用 &/? 邊界避免誤中其他子字串）
    expect(queryString.split("&")[0]).not.toMatch(/\banswer\b/);
  });

  it("load() 前的 in-memory item 沒有 answer（placeholder，命中後才補撈）", () => {
    const item = store.getById(FAKE_ITEMS[0]!.id);
    expect(item).toBeDefined();
    expect(item!.answer).toBe("");
  });

  it("load() 平行抓取多分頁，且組裝結果依 seq 正確、不受非同步回應順序影響", async () => {
    mockSupabaseCount.mockReset();
    mockSupabaseSelect.mockReset();
    const pageSize = 2000;
    const total = pageSize * 2 + 500; // 3 頁
    mockSupabaseCount.mockResolvedValueOnce(total);

    const makeRow = (seq: number) => ({
      ...FAKE_ROWS[0]!,
      id: `row-${seq}`,
      seq,
    });

    // 刻意讓 offset=2000 這頁比 offset=0 晚回應，驗證組裝結果仍照頁碼排序，
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

  it("load() 的分頁並行度受限於 PAGE_CONCURRENCY(4)，不會一次把所有分頁打出去", async () => {
    mockSupabaseCount.mockReset();
    mockSupabaseSelect.mockReset();
    const pageSize = 2000;
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

  it("load() 在 supabaseCount 失敗（回傳 -1）時，退回循序探頁而非平行猜頁數", async () => {
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
    // 注意：in-memory item 的 answer 是 placeholder("")，關鍵字比對只能靠
    // question/keywords 命中（"LCP" 剛好兩者都有，見 tests/setup.ts）。
    for (const item of items) {
      const hasKw =
        item.question.toLowerCase().includes("lcp") ||
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
    const mockCandidates = FAKE_MATCH_ROWS.slice(0, 3).map((row, i) => ({
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
      // hybridSearch 走 RPC，answer 本來就在 row 裡，不受 startup select 影響。
      expect(r.item.answer.length).toBeGreaterThan(0);
    }
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

  describe("answer hydration", () => {
    it("hydrateAnswer 補撈單一 item 的 answer", async () => {
      const target = FAKE_ITEMS[0]!;
      const item = store.getById(target.id)!;
      expect(item.answer).toBe("");

      mockSupabaseSelect.mockResolvedValueOnce([
        { id: target.id, answer: target.answer },
      ]);
      const hydrated = await store.hydrateAnswer(item);

      expect(hydrated.answer).toBe(target.answer);
      expect(mockSupabaseSelect).toHaveBeenCalledWith(
        "qa_items",
        expect.stringContaining(`id=in.(${target.id})`),
      );
      // hydrateAnswer 回傳新物件，不 mutate 原本的 store 狀態
      expect(store.getById(target.id)!.answer).toBe("");
    });

    it("hydrateAnswer 的 memo cache 對同一 id 不重打 Supabase", async () => {
      const target = FAKE_ITEMS[0]!;
      const item = store.getById(target.id)!;

      mockSupabaseSelect.mockResolvedValueOnce([
        { id: target.id, answer: target.answer },
      ]);
      await store.hydrateAnswer(item);
      mockSupabaseSelect.mockClear();

      const hydratedAgain = await store.hydrateAnswer(item);
      expect(hydratedAgain.answer).toBe(target.answer);
      expect(mockSupabaseSelect).not.toHaveBeenCalled();
    });

    it("hydrateAnswers 把命中結果的多個 id 合併成一次批次請求", async () => {
      const hits = FAKE_ITEMS.slice(0, 2).map((target) => ({
        item: store.getById(target.id)!,
        score: 1,
      }));
      mockSupabaseSelect.mockClear(); // 只看這次 hydrateAnswers 觸發的呼叫，排除 beforeEach 的 load()
      mockSupabaseSelect.mockResolvedValueOnce(FAKE_ANSWER_ROWS.slice(0, 2));

      const hydrated = await store.hydrateAnswers(hits);

      expect(mockSupabaseSelect).toHaveBeenCalledTimes(1);
      expect(hydrated[0]!.item.answer).toBe(FAKE_ITEMS[0]!.answer);
      expect(hydrated[1]!.item.answer).toBe(FAKE_ITEMS[1]!.answer);
      // score 等其餘欄位原樣保留
      expect(hydrated[0]!.score).toBe(1);
    });

    it("hydrateItemAnswers 補撈 listQa 分頁結果（不含 score 包裝）的 answer", async () => {
      const { items } = store.listQa({ limit: 2 });
      mockSupabaseSelect.mockResolvedValueOnce(
        items.map((i) => ({
          id: i.id,
          answer: FAKE_ITEMS.find((f) => f.id === i.id)!.answer,
        })),
      );

      const hydrated = await store.hydrateItemAnswers(items);

      expect(hydrated.every((i) => i.answer.length > 0)).toBe(true);
    });
  });
});
