/**
 * Tests for QAStore — file-based mode (JSON + .npy).
 * Uses temp files with real data to test load, search, and hybrid operations.
 */

import { describe, it, expect, vi, beforeAll, afterAll } from "vitest";
import { writeFileSync, mkdirSync, rmSync, utimesSync } from "node:fs";
import { join } from "node:path";
import { FAKE_ITEMS, generateFakeEmbeddings, createNpyBuffer } from "../setup.js";

// Mock config — file-based (no Supabase)
vi.mock("../../src/config.js", () => ({
  config: {
    SUPABASE_URL: "",
    SUPABASE_ANON_KEY: "",
    SEO_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
    CHAT_CONTEXT_K: 5,
  },
  paths: {
    qaJsonPath: "",
    qaEmbeddingsPath: "",
    qaEnrichedJsonPath: "",
    outputDir: "/tmp",
    accessLogsDir: "/tmp/test-logs",
  },
}));

vi.mock("../../src/store/supabase-client.js", () => ({
  hasSupabase: () => false,
}));

vi.mock("../../src/store/supabase-qa-store.js", () => ({
  SupabaseQAStore: class {},
}));

import { QAStore } from "../../src/store/qa-store.js";

const DIM = 4;
const tmpDir = join("/tmp", `qa-store-test-${Date.now()}`);

// Build qa_final.json from FAKE_ITEMS
function buildFakeJson() {
  return {
    qa_database: FAKE_ITEMS.map((item) => ({
      id: item.seq,
      stable_id: item.id,
      question: item.question,
      answer: item.answer,
      keywords: [...item.keywords],
      confidence: item.confidence,
      category: item.category,
      difficulty: item.difficulty,
      evergreen: item.evergreen,
      source_title: item.source_title,
      source_date: item.source_date,
      is_merged: item.is_merged,
      source_type: item.source_type,
      source_collection: item.source_collection,
      source_url: item.source_url,
      extraction_model: item.extraction_model,
      primary_category: item.primary_category,
      categories: item.categories,
      intent_labels: item.intent_labels,
      scenario_tags: item.scenario_tags,
      serving_tier: item.serving_tier,
      retrieval_phrases: item.retrieval_phrases,
      retrieval_surface_text: item.retrieval_surface_text,
      content_granularity: item.content_granularity,
      evidence_scope: item.evidence_scope,
      booster_target_queries: item.booster_target_queries,
      hard_negative_terms: item.hard_negative_terms,
      _enrichment: {
        synonyms: [...item.synonyms],
        freshness_score: item.freshness_score,
        search_hit_count: item.search_hit_count,
        notion_url: item.notion_url,
      },
    })),
  };
}

function writeFakeEmbeddings(npyPath: string, itemCount: number): void {
  const embeddings = generateFakeEmbeddings(itemCount, DIM);
  const npyBuffer = createNpyBuffer(embeddings, itemCount, DIM);
  writeFileSync(npyPath, npyBuffer);
}

describe("QAStore (file-based)", () => {
  let store: QAStore;
  const jsonPath = join(tmpDir, "qa_final.json");
  const npyPath = join(tmpDir, "qa_embeddings.npy");
  const enrichedPath = join(tmpDir, "qa_enriched.json");

  beforeAll(() => {
    mkdirSync(tmpDir, { recursive: true });

    // Write fake JSON
    writeFileSync(jsonPath, JSON.stringify(buildFakeJson()), "utf-8");

    // Write fake .npy embeddings
    writeFakeEmbeddings(npyPath, FAKE_ITEMS.length);

    store = new QAStore();
    store.load(jsonPath, npyPath, enrichedPath);
  });

  afterAll(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  it("loads items from JSON", () => {
    expect(store.loaded).toBe(true);
    expect(store.count).toBe(FAKE_ITEMS.length);
  });

  it("getById returns correct item", () => {
    const item = store.getById(FAKE_ITEMS[0]!.id);
    expect(item).toBeDefined();
    expect(item!.question).toBe(FAKE_ITEMS[0]!.question);
  });

  it("getById returns undefined for unknown id", () => {
    expect(store.getById("nonexistent")).toBeUndefined();
  });

  it("getBySeq returns correct item", () => {
    const item = store.getBySeq(1);
    expect(item).toBeDefined();
    expect(item!.seq).toBe(1);
  });

  it("getBySeq returns undefined for unknown seq", () => {
    expect(store.getBySeq(999)).toBeUndefined();
  });

  it("categories() returns sorted categories", () => {
    const cats = store.categories();
    expect(cats.length).toBeGreaterThan(0);
    expect(cats).toContain("SEO Technical");
  });

  it("collections() returns source info", () => {
    const colls = store.collections();
    expect(colls.length).toBeGreaterThan(0);
    const meetings = colls.find((c) => c.source_collection === "seo-meetings");
    expect(meetings).toBeDefined();
  });

  it("listQa returns all items with no filters", () => {
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

  it("hasEmbeddings is true when .npy loaded", () => {
    expect(store.hasEmbeddings).toBe(true);
  });

  it("search returns scored results", () => {
    const queryVec = new Float32Array(DIM).fill(0.5);
    const results = store.search(queryVec, 3);
    expect(results.length).toBeGreaterThan(0);
    for (const r of results) {
      expect(r.score).toBeGreaterThan(0);
    }
  });

  it("search filters by category", () => {
    const queryVec = new Float32Array(DIM).fill(0.5);
    const results = store.search(queryVec, 10, "SEO Technical");
    for (const r of results) {
      expect(r.item.category).toBe("SEO Technical");
    }
  });

  it("keywordSearch returns results", () => {
    const results = store.keywordSearch("LCP", 3);
    expect(results.length).toBeGreaterThan(0);
    for (const r of results) {
      expect(r.score).toBeGreaterThan(0);
    }
  });

  it("keywordSearch exposes retrieval metadata on returned items", () => {
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

  it("hybridSearch returns results", async () => {
    const queryVec = new Float32Array(DIM).fill(0.5);
    const results = await store.hybridSearch("LCP performance", queryVec, 3);
    expect(results.length).toBeGreaterThan(0);
    for (const r of results) {
      expect(r.score).toBeGreaterThanOrEqual(0);
    }
  });

  it("keywordSearch prefers targeted booster for matching AI scenario query", () => {
    const [first] = store.keywordSearch("AI SEO SGE", 3);
    expect(first).toBeDefined();
    expect(first!.item.serving_tier).toBe("booster");
  });

  it("falls back to qa_final.json when qa_enriched.json is older", () => {
    const staleDir = `${tmpDir}-stale-enriched`;
    const staleJsonPath = join(staleDir, "qa_final.json");
    const staleNpyPath = join(staleDir, "qa_embeddings.npy");
    const staleEnrichedPath = join(staleDir, "qa_enriched.json");

    mkdirSync(staleDir, { recursive: true });

    const freshJson = buildFakeJson();
    const staleEnrichedJson = {
      qa_database: freshJson.qa_database.slice(0, freshJson.qa_database.length - 1),
    };

    writeFileSync(staleJsonPath, JSON.stringify(freshJson), "utf-8");
    writeFileSync(staleEnrichedPath, JSON.stringify(staleEnrichedJson), "utf-8");
    writeFakeEmbeddings(staleNpyPath, freshJson.qa_database.length);

    utimesSync(staleEnrichedPath, new Date("2026-01-01T00:00:00.000Z"), new Date("2026-01-01T00:00:00.000Z"));
    utimesSync(staleJsonPath, new Date("2026-01-02T00:00:00.000Z"), new Date("2026-01-02T00:00:00.000Z"));

    try {
      const staleStore = new QAStore();
      staleStore.load(staleJsonPath, staleNpyPath, staleEnrichedPath);

      expect(staleStore.count).toBe(freshJson.qa_database.length);
      expect(staleStore.getById(FAKE_ITEMS.at(-1)!.id)).toBeDefined();
    } finally {
      rmSync(staleDir, { recursive: true, force: true });
    }
  });

  it("loads qa_enriched.json when it is newer than qa_final.json", () => {
    const freshDir = `${tmpDir}-fresh-enriched`;
    const freshJsonPath = join(freshDir, "qa_final.json");
    const freshNpyPath = join(freshDir, "qa_embeddings.npy");
    const freshEnrichedPath = join(freshDir, "qa_enriched.json");

    mkdirSync(freshDir, { recursive: true });

    const finalJson = buildFakeJson();
    const enrichedJson = {
      qa_database: finalJson.qa_database.slice(0, finalJson.qa_database.length - 1),
    };

    writeFileSync(freshJsonPath, JSON.stringify(finalJson), "utf-8");
    writeFileSync(freshEnrichedPath, JSON.stringify(enrichedJson), "utf-8");
    writeFakeEmbeddings(freshNpyPath, enrichedJson.qa_database.length);

    utimesSync(freshJsonPath, new Date("2026-01-01T00:00:00.000Z"), new Date("2026-01-01T00:00:00.000Z"));
    utimesSync(freshEnrichedPath, new Date("2026-01-02T00:00:00.000Z"), new Date("2026-01-02T00:00:00.000Z"));

    try {
      const freshStore = new QAStore();
      freshStore.load(freshJsonPath, freshNpyPath, freshEnrichedPath);

      expect(freshStore.count).toBe(enrichedJson.qa_database.length);
      expect(freshStore.getById(FAKE_ITEMS.at(-1)!.id)).toBeUndefined();
    } finally {
      rmSync(freshDir, { recursive: true, force: true });
    }
  });

  it("throws a clear error when qa_final.json is missing and qa_enriched.json cannot be read", () => {
    const brokenDir = `${tmpDir}-broken-enriched`;
    const missingJsonPath = join(brokenDir, "qa_final.json");
    const brokenEnrichedPath = join(brokenDir, "qa_enriched.json");
    const missingNpyPath = join(brokenDir, "qa_embeddings.npy");

    mkdirSync(brokenEnrichedPath, { recursive: true });

    try {
      const brokenStore = new QAStore();
      expect(() => brokenStore.load(missingJsonPath, missingNpyPath, brokenEnrichedPath)).toThrow(
        "QAStore: both qa_enriched.json and qa_final.json are unavailable",
      );
    } finally {
      rmSync(brokenDir, { recursive: true, force: true });
    }
  });
});

describe("QAStore (keyword-only — no .npy)", () => {
  let store: QAStore;
  const jsonPath = join(tmpDir + "-kwonly", "qa_final.json");
  const npyPath = join(tmpDir + "-kwonly", "nonexistent.npy");
  const enrichedPath = join(tmpDir + "-kwonly", "nonexistent.json");

  beforeAll(() => {
    mkdirSync(tmpDir + "-kwonly", { recursive: true });
    writeFileSync(jsonPath, JSON.stringify(buildFakeJson()), "utf-8");

    store = new QAStore();
    store.load(jsonPath, npyPath, enrichedPath);
  });

  afterAll(() => {
    rmSync(tmpDir + "-kwonly", { recursive: true, force: true });
  });

  it("loads in keyword-only mode", () => {
    expect(store.loaded).toBe(true);
    expect(store.hasEmbeddings).toBe(false);
  });

  it("keywordSearch still works via fallback", () => {
    const results = store.keywordSearch("LCP", 3);
    expect(results.length).toBeGreaterThan(0);
  });

  it("hybridSearch falls back to search", async () => {
    const queryVec = new Float32Array(4).fill(0.5);
    const results = await store.hybridSearch("test", queryVec, 3);
    // With no embeddings, fallback returns empty
    expect(results).toBeDefined();
  });
});
