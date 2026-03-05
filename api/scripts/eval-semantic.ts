/**
 * eval-semantic.ts — Semantic + Reranker Retrieval Evaluation CLI
 *
 * 比較三種 retrieval 模式在 golden_retrieval.json 上的指標：
 *   1. keyword-only  (baseline)
 *   2. hybrid        (semantic embedding + keyword boost + synonym + freshness)
 *   3. hybrid+rerank (hybrid × overRetrieveFactor=3 → Claude haiku rerank → top-K)
 *
 * 需求：
 *   - OPENAI_API_KEY   — 用於 query embedding（hybrid/rerank 模式必須）
 *   - ANTHROPIC_API_KEY — 用於 reranker（rerank 模式必須）
 *
 * 執行：
 *   cd api && npx tsx scripts/eval-semantic.ts
 *   cd api && npx tsx scripts/eval-semantic.ts --top-k 5 --mode all
 *   cd api && npx tsx scripts/eval-semantic.ts --json > result.json
 */

import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { config as dotenvConfig } from "dotenv";
import { parseArgs } from "node:util";

// Load env vars before importing config-dependent modules
const __dir = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = resolve(__dir, "../..");
dotenvConfig({ path: resolve(__dir, "../.env") });
dotenvConfig({ path: resolve(ROOT_DIR, ".env") });

import { QAStore } from "../src/store/qa-store.js";
import { paths, config } from "../src/config.js";
import { rerank } from "../src/services/reranker.js";

// ────────────────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────────────────

interface GoldenCase {
  readonly scenario: string;
  readonly query: string;
  readonly expected_keywords: readonly string[];
  readonly expected_categories: readonly string[];
  readonly description: string;
}

interface MetricSet {
  readonly precision: number;
  readonly recall: number;
  readonly f1: number;
  readonly hit_rate: number;
  readonly mrr: number;
}

interface ModeResult {
  readonly mode: string;
  readonly metrics: MetricSet;
  readonly cases: ReadonlyArray<{
    readonly query: string;
    readonly retrieved_categories: readonly string[];
    readonly expected_categories: readonly string[];
    readonly precision: number;
    readonly recall: number;
    readonly hit: boolean;
    readonly reciprocal_rank: number;
  }>;
}

// ────────────────────────────────────────────────────────────
// Metric helpers
// ────────────────────────────────────────────────────────────

function computePrecision(
  retrievedCats: readonly string[],
  expectedCats: ReadonlySet<string>,
): number {
  if (retrievedCats.length === 0) return 0;
  const relevant = retrievedCats.filter((c) => expectedCats.has(c)).length;
  return relevant / retrievedCats.length;
}

function computeRecall(
  retrievedCats: readonly string[],
  expectedCats: ReadonlySet<string>,
): number {
  if (expectedCats.size === 0) return 1.0;
  const retrievedSet = new Set(retrievedCats);
  const hit = [...expectedCats].filter((c) => retrievedSet.has(c)).length;
  return hit / expectedCats.size;
}

function computeF1(p: number, r: number): number {
  if (p + r === 0) return 0;
  return (2 * p * r) / (p + r);
}

function computeHitRate(
  retrievedCats: readonly string[],
  expectedCats: ReadonlySet<string>,
): boolean {
  return retrievedCats.some((c) => expectedCats.has(c));
}

function computeMRR(
  retrievedCats: readonly string[],
  expectedCats: ReadonlySet<string>,
): number {
  for (let i = 0; i < retrievedCats.length; i++) {
    if (expectedCats.has(retrievedCats[i]!)) {
      return 1 / (i + 1);
    }
  }
  return 0;
}

function avgMetrics(cases: readonly ReturnType<typeof caseMetrics>[]): MetricSet {
  const n = cases.length;
  if (n === 0) return { precision: 0, recall: 0, f1: 0, hit_rate: 0, mrr: 0 };
  return {
    precision: cases.reduce((s, c) => s + c.precision, 0) / n,
    recall: cases.reduce((s, c) => s + c.recall, 0) / n,
    f1: cases.reduce((s, c) => s + c.f1, 0) / n,
    hit_rate: cases.reduce((s, c) => s + (c.hit ? 1 : 0), 0) / n,
    mrr: cases.reduce((s, c) => s + c.reciprocal_rank, 0) / n,
  };
}

function caseMetrics(
  retrievedCats: readonly string[],
  expectedCats: ReadonlySet<string>,
): { precision: number; recall: number; f1: number; hit: boolean; reciprocal_rank: number } {
  const p = computePrecision(retrievedCats, expectedCats);
  const r = computeRecall(retrievedCats, expectedCats);
  return {
    precision: p,
    recall: r,
    f1: computeF1(p, r),
    hit: computeHitRate(retrievedCats, expectedCats),
    reciprocal_rank: computeMRR(retrievedCats, expectedCats),
  };
}

// ────────────────────────────────────────────────────────────
// Embedding helper (lazy import)
// ────────────────────────────────────────────────────────────

async function embedQuery(query: string): Promise<Float32Array> {
  const { getEmbedding } = await import("../src/services/embedding.js");
  return getEmbedding(query);
}

// ────────────────────────────────────────────────────────────
// Mode runners
// ────────────────────────────────────────────────────────────

async function runKeyword(
  store: QAStore,
  goldenCases: readonly GoldenCase[],
  topK: number,
): Promise<ModeResult> {
  const cases: ReturnType<typeof caseMetrics>[] = [];
  const caseDetails: ModeResult["cases"] = [];

  for (const gc of goldenCases) {
    const hits = store.keywordSearch(gc.query, topK, null);
    const retrievedCats = hits.map((h) => h.item.category);
    const expectedSet = new Set(gc.expected_categories);
    const m = caseMetrics(retrievedCats, expectedSet);
    cases.push(m);
    caseDetails.push({
      query: gc.query,
      retrieved_categories: retrievedCats,
      expected_categories: gc.expected_categories,
      ...m,
    });
  }

  return { mode: "keyword", metrics: avgMetrics(cases), cases: caseDetails };
}

async function runHybrid(
  store: QAStore,
  goldenCases: readonly GoldenCase[],
  topK: number,
): Promise<ModeResult | null> {
  const cases: ReturnType<typeof caseMetrics>[] = [];
  const caseDetails: ModeResult["cases"] = [];

  for (const gc of goldenCases) {
    let queryVec: Float32Array;
    try {
      queryVec = await embedQuery(gc.query);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.warn(`\n[hybrid] embedding failed: ${msg.slice(0, 80)}`);
      return null;
    }
    const hits = store.hybridSearch(gc.query, queryVec, topK, null);
    const retrievedCats = hits.map((h) => h.item.category);
    const expectedSet = new Set(gc.expected_categories);
    const m = caseMetrics(retrievedCats, expectedSet);
    cases.push(m);
    caseDetails.push({
      query: gc.query,
      retrieved_categories: retrievedCats,
      expected_categories: gc.expected_categories,
      ...m,
    });
  }

  return { mode: "hybrid", metrics: avgMetrics(cases), cases: caseDetails };
}

async function runHybridRerank(
  store: QAStore,
  goldenCases: readonly GoldenCase[],
  topK: number,
): Promise<ModeResult | null> {
  const OVER_RETRIEVE = 3;
  const cases: ReturnType<typeof caseMetrics>[] = [];
  const caseDetails: ModeResult["cases"] = [];

  for (const gc of goldenCases) {
    let queryVec: Float32Array;
    try {
      queryVec = await embedQuery(gc.query);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.warn(`\n[hybrid+rerank] embedding failed: ${msg.slice(0, 80)}`);
      return null;
    }
    // Over-retrieve topK×3 candidates
    const candidates = store.hybridSearch(gc.query, queryVec, topK * OVER_RETRIEVE, null);
    // Rerank to top-K
    const reranked = await rerank(
      gc.query,
      candidates as Array<{ item: import("../src/store/qa-store.js").QAItem; score: number }>,
      topK,
    );
    const retrievedCats = reranked.map((h) => h.item.category);
    const expectedSet = new Set(gc.expected_categories);
    const m = caseMetrics(retrievedCats, expectedSet);
    cases.push(m);
    caseDetails.push({
      query: gc.query,
      retrieved_categories: retrievedCats,
      expected_categories: gc.expected_categories,
      ...m,
    });
  }

  return { mode: "hybrid+rerank", metrics: avgMetrics(cases), cases: caseDetails };
}

// ────────────────────────────────────────────────────────────
// Output helpers
// ────────────────────────────────────────────────────────────

function fmt(n: number): string {
  return n.toFixed(3);
}

function printTable(results: readonly ModeResult[]): void {
  const cols = ["Mode             ", "Precision", "Recall ", "F1     ", "HitRate", "MRR    "];
  const sep = "─".repeat(cols.join("  ").length + 2);

  console.log("\n=== Retrieval Eval — Semantic Comparison ===\n");
  console.log(cols.join("  "));
  console.log(sep);

  for (const r of results) {
    const m = r.metrics;
    const row = [
      r.mode.padEnd(17),
      fmt(m.precision).padEnd(9),
      fmt(m.recall).padEnd(7),
      fmt(m.f1).padEnd(7),
      fmt(m.hit_rate).padEnd(7),
      fmt(m.mrr),
    ];
    console.log(row.join("  "));
  }
  console.log(sep);

  // Delta vs keyword baseline
  if (results.length > 1) {
    const base = results[0]!.metrics;
    console.log("\nDelta vs keyword baseline:");
    for (const r of results.slice(1)) {
      const m = r.metrics;
      const delta = (v: number, b: number) =>
        (v - b >= 0 ? "+" : "") + fmt(v - b);
      console.log(
        `  ${r.mode.padEnd(17)}: Precision ${delta(m.precision, base.precision)}  ` +
          `Recall ${delta(m.recall, base.recall)}  ` +
          `F1 ${delta(m.f1, base.f1)}  ` +
          `HitRate ${delta(m.hit_rate, base.hit_rate)}  ` +
          `MRR ${delta(m.mrr, base.mrr)}`,
      );
    }
  }
}

// ────────────────────────────────────────────────────────────
// Main
// ────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const { values: args } = parseArgs({
    options: {
      "top-k": { type: "string", default: "5" },
      mode: { type: "string", default: "all" },
      json: { type: "boolean", default: false },
    },
  });

  const topK = Math.max(1, parseInt(args["top-k"] as string, 10));
  const mode = (args.mode as string).toLowerCase();
  const jsonMode = args.json as boolean;

  const goldenPath = resolve(ROOT_DIR, "output/evals/golden_retrieval.json");
  if (!existsSync(goldenPath)) {
    console.error(`golden_retrieval.json not found: ${goldenPath}`);
    process.exit(1);
  }

  const goldenCases: GoldenCase[] = JSON.parse(readFileSync(goldenPath, "utf-8"));
  if (!Array.isArray(goldenCases) || goldenCases.length === 0) {
    console.error("golden_retrieval.json must be a non-empty array");
    process.exit(1);
  }

  if (!jsonMode) {
    console.log(`Loading QA store (${paths.qaJsonPath})…`);
  }

  const store = new QAStore();
  store.load();

  if (!jsonMode) {
    console.log(
      `Loaded ${store.count} items, embeddings available: ${store.hasEmbeddings}`,
    );
    console.log(`Golden cases: ${goldenCases.length}, top-k: ${topK}\n`);
  }

  const results: ModeResult[] = [];
  const runAll = mode === "all";

  // Mode: keyword
  if (runAll || mode === "keyword") {
    if (!jsonMode) process.stdout.write("Running keyword…");
    const r = await runKeyword(store, goldenCases, topK);
    results.push(r);
    if (!jsonMode) console.log(" done");
  }

  // Mode: hybrid
  if (runAll || mode === "hybrid") {
    if (!config.OPENAI_API_KEY) {
      console.warn("OPENAI_API_KEY not set — skipping hybrid mode");
    } else if (!store.hasEmbeddings) {
      console.warn("Embeddings not loaded — skipping hybrid mode");
    } else {
      if (!jsonMode) process.stdout.write("Running hybrid (embedding)…");
      const r = await runHybrid(store, goldenCases, topK);
      if (r) {
        results.push(r);
        if (!jsonMode) console.log(" done");
      } else {
        if (!jsonMode) console.log(" skipped (embedding error)");
      }
    }
  }

  // Mode: rerank
  if (runAll || mode === "rerank") {
    if (!config.OPENAI_API_KEY) {
      console.warn("OPENAI_API_KEY not set — skipping hybrid+rerank mode");
    } else if (!store.hasEmbeddings) {
      console.warn("Embeddings not loaded — skipping hybrid+rerank mode");
    } else {
      if (!config.ANTHROPIC_API_KEY) {
        console.warn("ANTHROPIC_API_KEY not set — reranker will use original order (fallback)");
      }
      if (!jsonMode) process.stdout.write("Running hybrid+rerank…");
      const r = await runHybridRerank(store, goldenCases, topK);
      if (r) {
        const label = config.ANTHROPIC_API_KEY ? "hybrid+rerank" : "hybrid+rerank(no-key)";
        results.push({ ...r, mode: label });
        if (!jsonMode) console.log(" done");
      } else {
        if (!jsonMode) console.log(" skipped (embedding error)");
      }
    }
  }

  if (jsonMode) {
    console.log(JSON.stringify({ top_k: topK, results }, null, 2));
    return;
  }

  printTable(results);
  console.log("\n");
}

main().catch((err) => {
  console.error("[eval-semantic] Fatal error:", err);
  process.exit(1);
});
