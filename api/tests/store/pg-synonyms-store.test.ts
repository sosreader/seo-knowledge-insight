import { beforeEach, describe, expect, it } from "vitest";
import { PgSynonymsStore } from "../../src/store/pg-synonyms-store.js";
import { STATIC_SYNONYMS } from "../../src/store/synonyms-store.js";
import { pgAvailable, usePgFixture } from "../pg/pg-fixture.js";

const fx = usePgFixture("syn");
const STATIC_TERM = Object.keys(STATIC_SYNONYMS)[0]!;

describe.skipIf(!pgAvailable)("PgSynonymsStore against app_synonym_custom (warehouse_rag)", () => {
  beforeEach(async () => {
    await fx.activate();
    await fx.admin().query("TRUNCATE app_synonym_custom");
  });

  it("loads custom rows and merges them over the static layer", async () => {
    await fx.admin().query("INSERT INTO app_synonym_custom (term, synonyms) VALUES ($1, $2), ($3, $4)", [
      "核心網頁指標",
      ["CWV"],
      STATIC_TERM,
      ["override"],
    ]);
    const store = new PgSynonymsStore();
    await store.load();
    expect(store.loaded).toBe(true);
    expect(store.get("核心網頁指標")).toEqual({ term: "核心網頁指標", synonyms: ["CWV"], source: "custom" });
    expect(store.get(STATIC_TERM)?.source).toBe("custom");
    expect(store.isCustom(STATIC_TERM)).toBe(true);
    expect(store.isStatic(STATIC_TERM)).toBe(true);
    expect(store.list().filter((i) => i.term === STATIC_TERM)).toHaveLength(1);
    expect(store.getCustom()).toMatchObject({ 核心網頁指標: ["CWV"] });
  });

  it("falls back to the static layer and returns undefined for unknown terms", async () => {
    const store = new PgSynonymsStore();
    await store.load();
    expect(store.get(STATIC_TERM)).toMatchObject({ term: STATIC_TERM, source: "static" });
    expect(store.get("完全沒有這個詞")).toBeUndefined();
    expect(store.isCustom(STATIC_TERM)).toBe(false);
  });

  it("create upserts and updates the cache", async () => {
    const store = new PgSynonymsStore();
    await store.load();
    await store.create("canonical", ["rel=canonical"]);
    await store.create("canonical", ["rel=canonical", "標準網址"]);
    const { rows } = await fx.admin().query("SELECT synonyms FROM app_synonym_custom WHERE term = 'canonical'");
    expect(rows[0].synonyms).toEqual(["rel=canonical", "標準網址"]);
    expect(store.get("canonical")?.synonyms).toEqual(["rel=canonical", "標準網址"]);
  });

  it("update modifies an existing row, or creates a custom override when missing", async () => {
    const store = new PgSynonymsStore();
    await store.load();
    await store.create("hreflang", ["語系"]);
    await store.update("hreflang", ["語系標記"]);
    await store.update(STATIC_TERM, ["static-override"]);
    const { rows } = await fx.admin().query("SELECT term, synonyms FROM app_synonym_custom ORDER BY term");
    expect(rows).toEqual(
      expect.arrayContaining([
        { term: "hreflang", synonyms: ["語系標記"] },
        { term: STATIC_TERM, synonyms: ["static-override"] },
      ]),
    );
  });

  it("delete hard-deletes custom rows and returns false for unknown terms", async () => {
    const store = new PgSynonymsStore();
    await store.load();
    await store.create("robots", ["robots.txt"]);
    expect(await store.delete("robots")).toBe(true);
    expect(await store.delete("robots")).toBe(false);
    expect(await store.delete("never-existed")).toBe(false);
    const { rowCount } = await fx.admin().query("SELECT 1 FROM app_synonym_custom WHERE term = 'robots'");
    expect(rowCount).toBe(0);
  });

  it("create／update return the row read back from the DB", async () => {
    const store = new PgSynonymsStore();
    await store.load();
    const created = await store.create("讀回", ["x"]);
    expect(created).toEqual({ term: "讀回", synonyms: ["x"], source: "custom" });
    const updated = await store.update("讀回", ["y", "z"]);
    expect(updated).toEqual({ term: "讀回", synonyms: ["y", "z"], source: "custom" });
  });

  it("delete reports false when another writer already removed the row", async () => {
    const store = new PgSynonymsStore();
    await store.create("已被刪", ["x"]);
    await fx.admin().query("DELETE FROM app_synonym_custom WHERE term = '已被刪'");
    expect(await store.delete("已被刪")).toBe(false);
    expect(store.isCustom("已被刪")).toBe(false);
  });
});
