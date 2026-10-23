/**
 * PgSynonymsStore.reload() 的記憶體內行為（mock pgQuery，不連 DB）。
 * SQL 與權限由 tests/store/pg-synonyms-store.test.ts 對真 PG 驗證。
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

const { mockPgQuery } = vi.hoisted(() => ({ mockPgQuery: vi.fn() }));

vi.mock("../../src/store/pg-client.js", () => ({
  hasPg: () => true,
  pgQuery: (...args: unknown[]) => mockPgQuery(...args),
}));

// synonyms-store 與 pg-synonyms-store 互相引用，必須從 synonyms-store 進入（與正式程式的載入順序一致）
import "../../src/store/synonyms-store.js";
import { PgSynonymsStore } from "../../src/store/pg-synonyms-store.js";
import { DbTimeoutError, DbUnavailableError } from "../../src/store/store-errors.js";

describe("PgSynonymsStore.reload", () => {
  let store: PgSynonymsStore;

  beforeEach(async () => {
    mockPgQuery.mockReset();
    mockPgQuery.mockResolvedValueOnce([{ term: "舊詞", synonyms: ["old"] }]);
    store = new PgSynonymsStore();
    await store.load();
  });

  it("swaps the whole custom cache on success", async () => {
    mockPgQuery.mockResolvedValueOnce([
      { term: "新詞", synonyms: ["new"] },
      { term: "另一個", synonyms: ["x", "y"] },
    ]);
    const result = await store.reload();
    expect(result).toEqual({ ok: true, count: 2 });
    expect(store.isCustom("舊詞")).toBe(false);
    expect(store.get("新詞")).toEqual({ term: "新詞", synonyms: ["new"], source: "custom" });
  });

  it("marks the store loaded even if the first load never happened", async () => {
    const fresh = new PgSynonymsStore();
    mockPgQuery.mockResolvedValueOnce([]);
    expect(fresh.loaded).toBe(false);
    expect(await fresh.reload()).toEqual({ ok: true, count: 0 });
    expect(fresh.loaded).toBe(true);
  });

  it.each([
    ["db_timeout", new DbTimeoutError()],
    ["db_unavailable", new DbUnavailableError("ECONNREFUSED")],
    ["reload_failed", new Error("boom host=db.internal")],
  ])("keeps the old cache and returns %s when the query fails", async (code, err) => {
    mockPgQuery.mockRejectedValueOnce(err);
    const result = await store.reload();
    expect(result).toEqual({ ok: false, code });
    expect(store.get("舊詞")?.synonyms).toEqual(["old"]);
  });

  it("does not throw when the query fails", async () => {
    mockPgQuery.mockRejectedValueOnce(new Error("x"));
    await expect(store.reload()).resolves.toMatchObject({ ok: false });
  });

  it("drops the snapshot when a write lands while the reload query is in flight", async () => {
    let resolveSelect!: (rows: unknown[]) => void;
    mockPgQuery.mockImplementationOnce(() => new Promise((resolve) => (resolveSelect = resolve)));
    const pending = store.reload();

    mockPgQuery.mockResolvedValueOnce([{ term: "剛寫入", synonyms: ["fresh"] }]);
    await store.create("剛寫入", ["fresh"]);

    // 讀取快照是寫入前的狀態，換入會蓋掉剛寫入的值
    resolveSelect([{ term: "舊詞", synonyms: ["old"] }]);
    expect(await pending).toEqual({ ok: false, code: "concurrent_write" });
    expect(store.get("剛寫入")?.synonyms).toEqual(["fresh"]);
  });

  it("delete during reload also invalidates the snapshot", async () => {
    let resolveSelect!: (rows: unknown[]) => void;
    mockPgQuery.mockImplementationOnce(() => new Promise((resolve) => (resolveSelect = resolve)));
    const pending = store.reload();

    mockPgQuery.mockResolvedValueOnce([{ term: "舊詞" }]);
    await store.delete("舊詞");

    resolveSelect([{ term: "舊詞", synonyms: ["old"] }]);
    expect(await pending).toEqual({ ok: false, code: "concurrent_write" });
    expect(store.isCustom("舊詞")).toBe(false);
  });
});
