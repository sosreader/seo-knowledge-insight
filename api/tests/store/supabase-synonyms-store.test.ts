/**
 * Tests for SupabaseSynonymsStore.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

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

const mockSupabaseSelect = vi.fn();

vi.mock("../../src/store/supabase-client.js", () => ({
  hasSupabase: () => true,
  supabaseSelect: (...args: unknown[]) => mockSupabaseSelect(...args),
  supabaseHeaders: () => ({
    apikey: "test",
    Authorization: "Bearer test",
    "Content-Type": "application/json",
  }),
  SUPABASE_TIMEOUT_MS: 10_000,
}));

// Mock synonyms-store to break circular dependency — only provide STATIC_SYNONYMS
vi.mock("../../src/store/synonyms-store.js", () => ({
  STATIC_SYNONYMS: {
    "CWV": ["Core Web Vitals", "LCP", "CLS"],
    "SEO": ["Search Engine Optimization"],
  },
}));

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

import { SupabaseSynonymsStore } from "../../src/store/supabase-synonyms-store.js";

describe("SupabaseSynonymsStore", () => {
  let store: SupabaseSynonymsStore;

  beforeEach(async () => {
    vi.clearAllMocks();
    mockSupabaseSelect.mockResolvedValueOnce([
      { term: "SEO", synonyms: ["search engine optimization"], created_at: "", updated_at: "" },
    ]);
    store = new SupabaseSynonymsStore();
    await store.load();
  });

  it("loads custom synonyms from Supabase", () => {
    expect(store.loaded).toBe(true);
  });

  it("list() merges static and custom synonyms", () => {
    const items = store.list();
    expect(items.length).toBeGreaterThan(0);
    const seo = items.find((i) => i.term === "SEO");
    expect(seo).toBeDefined();
    expect(seo!.source).toBe("custom"); // custom overrides static
  });

  it("get() returns custom synonym when exists", () => {
    const item = store.get("SEO");
    expect(item).toBeDefined();
    expect(item!.source).toBe("custom");
    expect(item!.synonyms).toContain("search engine optimization");
  });

  it("get() returns static synonym when no custom override", () => {
    const item = store.get("CWV");
    expect(item).toBeDefined();
    expect(item!.source).toBe("static");
  });

  it("get() returns undefined for unknown term", () => {
    expect(store.get("nonexistent_term_xyz")).toBeUndefined();
  });

  it("create() posts to Supabase and updates cache", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true });

    const result = await store.create("newterm", ["alias1", "alias2"]);
    expect(result.term).toBe("newterm");
    expect(result.source).toBe("custom");
    expect(store.get("newterm")).toBeDefined();
  });

  it("create() throws on HTTP error", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

    await expect(store.create("bad", ["x"])).rejects.toThrow(
      "Failed to create synonym (500)",
    );
  });

  it("update() patches existing synonym", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true });

    const result = await store.update("SEO", ["updated alias"]);
    expect(result.synonyms).toContain("updated alias");
    expect(store.get("SEO")!.synonyms).toContain("updated alias");
  });

  it("update() falls back to create when PATCH fails", async () => {
    // PATCH fails
    mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });
    // create succeeds
    mockFetch.mockResolvedValueOnce({ ok: true });

    const result = await store.update("newone", ["val"]);
    expect(result.source).toBe("custom");
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("delete() removes custom synonym", async () => {
    mockFetch.mockResolvedValueOnce({ ok: true });

    const result = await store.delete("SEO");
    expect(result).toBe(true);
    // After deletion, should fall back to static
    const item = store.get("SEO");
    expect(item).toBeDefined();
    expect(item!.source).toBe("static");
  });

  it("delete() returns false for non-existent custom term", async () => {
    expect(await store.delete("nonexistent")).toBe(false);
  });

  it("delete() returns false on HTTP error", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false });
    expect(await store.delete("SEO")).toBe(false);
  });

  it("isCustom() returns true for custom terms", () => {
    expect(store.isCustom("SEO")).toBe(true);
    expect(store.isCustom("nonexistent")).toBe(false);
  });

  it("isStatic() returns true for static terms", () => {
    expect(store.isStatic("CWV")).toBe(true);
    expect(store.isStatic("nonexistent")).toBe(false);
  });

  it("getCustom() returns all custom entries", () => {
    const custom = store.getCustom();
    expect(custom["SEO"]).toBeDefined();
  });
});
