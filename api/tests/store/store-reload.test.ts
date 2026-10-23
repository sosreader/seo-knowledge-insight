import { describe, expect, it, vi } from "vitest";

const { mockPgQuery } = vi.hoisted(() => ({ mockPgQuery: vi.fn() }));

vi.mock("../../src/config.js", () => ({
  config: { VW_DB_SECRET_FILE_RAG: "/var/run/secrets/db-rag", SEO_API_KEY: "" },
  paths: { outputDir: "/tmp" },
}));

vi.mock("../../src/store/pg-client.js", () => ({
  hasPg: () => true,
  pgQuery: (...args: unknown[]) => mockPgQuery(...args),
}));

import { reloadPgStores, reloadStores } from "../../src/store/store-reload.js";
import { qaStore } from "../../src/store/qa-store.js";
import { synonymsStore } from "../../src/store/synonyms-store.js";
import type { StoreReloadResult } from "../../src/store/store-errors.js";

const store = (result: StoreReloadResult) => ({ reload: vi.fn().mockResolvedValue(result) });

describe("reloadStores", () => {
  it("sums both stores when both succeed", async () => {
    const result = await reloadStores({
      qa: store({ ok: true, count: 32439 }),
      synonyms: store({ ok: true, count: 7 }),
    });
    expect(result).toEqual({ ok: true, qa_items: 32439, synonyms: 7 });
  });

  it("reports the failed store and still reloads the other one", async () => {
    const synonyms = store({ ok: true, count: 7 });
    const result = await reloadStores({
      qa: store({ ok: false, code: "db_timeout" }),
      synonyms,
    });
    expect(result).toEqual({ ok: false, code: "db_timeout", failed: ["qa_items"] });
    expect(synonyms.reload).toHaveBeenCalledTimes(1);
  });

  it("uses the first failure code when both fail", async () => {
    const result = await reloadStores({
      qa: store({ ok: false, code: "db_unavailable" }),
      synonyms: store({ ok: false, code: "db_timeout" }),
    });
    expect(result).toEqual({ ok: false, code: "db_unavailable", failed: ["qa_items", "synonyms"] });
  });

  it("reloads sequentially (qa first, then synonyms)", async () => {
    const order: string[] = [];
    await reloadStores({
      qa: { reload: async () => (order.push("qa"), { ok: true, count: 1 }) },
      synonyms: { reload: async () => (order.push("synonyms"), { ok: true, count: 1 }) },
    });
    expect(order).toEqual(["qa", "synonyms"]);
  });
});

describe("reloadPgStores (PG-mode singletons)", () => {
  it("reloads the real PgQAStore and PgSynonymsStore singletons", async () => {
    mockPgQuery.mockReset();
    mockPgQuery.mockImplementation(async (sql: string) =>
      sql.includes("app_synonym_custom") ? [{ term: "t", synonyms: ["a"] }] : [],
    );

    // 單例目前是空的，所以 QA 查到 0 列屬正常（沒有舊資料可保留）
    const result = await reloadPgStores();
    expect(result).toEqual({ ok: true, qa_items: 0, synonyms: 1 });
    expect(qaStore.loaded).toBe(true);
    expect(synonymsStore.loaded).toBe(true);
  });

  it("returns a fixed failure code when the DB is down, without throwing", async () => {
    mockPgQuery.mockReset();
    mockPgQuery.mockRejectedValue(new Error("password authentication failed for user x"));
    const result = await reloadPgStores();
    expect(result).toEqual({ ok: false, code: "reload_failed", failed: ["qa_items", "synonyms"] });
  });
});
