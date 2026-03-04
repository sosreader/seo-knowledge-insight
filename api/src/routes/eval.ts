import { Hono } from "hono";
import { join, resolve } from "node:path";
import { ok, fail } from "../schemas/api-response.js";
import {
  evalSampleRequestSchema,
  evalRetrievalRequestSchema,
  evalSaveRequestSchema,
  evalRerankingRequestSchema,
} from "../schemas/eval.js";
import { execQaTools } from "../services/pipeline-runner.js";
import { paths, config } from "../config.js";

export const evalRoute = new Hono();

// POST /sample — sample Q&A for evaluation
evalRoute.post("/sample", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = evalSampleRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { size, seed, with_golden } = parsed.data;
  const args: string[] = ["--size", String(size), "--seed", String(seed)];
  if (with_golden) args.push("--with-golden");

  const result = await execQaTools("eval-sample", args);
  if (!result.success) {
    console.error("eval-sample failed:", result.output);
    return c.json(fail("eval-sample failed"), 500);
  }

  try {
    return c.json(ok(JSON.parse(result.output)));
  } catch {
    return c.json(ok({ raw: result.output }));
  }
});

// POST /retrieval — local retrieval evaluation
evalRoute.post("/retrieval", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = evalRetrievalRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { top_k, use_enriched } = parsed.data;
  const args: string[] = ["--top-k", String(top_k)];
  if (use_enriched) args.push("--use-enriched");

  const result = await execQaTools("eval-retrieval-local", args);
  if (!result.success) {
    console.error("eval-retrieval-local failed:", result.output);
    return c.json(fail("eval-retrieval-local failed"), 500);
  }

  try {
    return c.json(ok(JSON.parse(result.output)));
  } catch {
    return c.json(ok({ raw: result.output }));
  }
});

// GET /compare — cross-provider eval comparison
evalRoute.get("/compare", async (c) => {
  const result = await execQaTools("eval-compare", ["--json"]);
  if (!result.success) {
    console.error("eval-compare failed:", result.output);
    return c.json(fail("eval-compare failed"), 500);
  }

  try {
    return c.json(ok(JSON.parse(result.output)));
  } catch {
    return c.json(ok({ raw: result.output }));
  }
});

// POST /save — save eval results (with path traversal protection)
evalRoute.post("/save", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = evalSaveRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("input must be a .json filename (no path separators)"), 400);
  }

  const {
    input, extraction_engine, update_baseline,
    extraction_model, embedding_model, classify_model,
  } = parsed.data;

  // Defense-in-depth: resolve and confirm within evalsDir
  const inputPath = resolve(join(paths.evalsDir, input));
  if (!inputPath.startsWith(resolve(paths.evalsDir))) {
    return c.json(fail("input must be a filename, not a path"), 400);
  }
  const args: string[] = ["--input", inputPath, "--extraction-engine", extraction_engine];
  if (update_baseline) args.push("--update-baseline");
  if (extraction_model) args.push("--extraction-model", extraction_model);
  if (embedding_model) args.push("--embedding-model", embedding_model);
  if (classify_model) args.push("--classify-model", classify_model);

  const result = await execQaTools("eval-save", args);
  if (!result.success) {
    console.error("eval-save failed:", result.output);
    return c.json(fail("eval-save failed"), 500);
  }

  return c.json(ok({
    saved: true,
    filename: input,
    models: {
      extraction_model: extraction_model ?? null,
      embedding_model: embedding_model ?? null,
      classify_model: classify_model ?? null,
    },
  }));
});

// POST /reranking — evaluate reranker performance
evalRoute.post("/reranking", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = evalRerankingRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { query, candidates, top_k } = parsed.data;

  // Convert candidates to QAItem-like format for reranker
  const mockHits = candidates.map((cand) => ({
    item: {
      id: cand.id,
      question: cand.question,
      answer: "",
      category: cand.category,
      keywords: [],
      confidence: 0,
      difficulty: "",
      evergreen: false,
      source_title: "",
      source_date: "",
      is_merged: false,
      synonyms: [],
      freshness_score: 1.0,
      search_hit_count: 0,
      notion_url: "",
      source_type: "meeting",
      source_collection: "seo-meetings",
      source_url: "",
      seq: 0,
    },
    score: cand.score,
  }));

  try {
    const { rerank } = await import("../services/reranker.js");
    const reranked = await rerank(query, mockHits, top_k);
    return c.json(ok({
      reranked: reranked.map((r, i) => ({
        rank: i + 1,
        id: r.item.id,
        question: r.item.question,
        category: r.item.category,
        original_score: r.score,
      })),
      total_candidates: candidates.length,
      top_k,
    }));
  } catch (err) {
    console.error("reranking failed:", err);
    return c.json(fail("reranking failed"), 500);
  }
});
