import { Hono } from "hono";
import { join } from "node:path";
import { ok, fail } from "../schemas/api-response.js";
import {
  evalSampleRequestSchema,
  evalRetrievalRequestSchema,
  evalSaveRequestSchema,
} from "../schemas/eval.js";
import { execQaTools } from "../services/pipeline-runner.js";
import { paths } from "../config.js";

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

  const { input, extraction_engine, update_baseline } = parsed.data;

  // Double-check: reject any path traversal attempts
  if (/[/\\]|\.\./.test(input)) {
    return c.json(fail("input must be a filename, not a path"), 400);
  }

  const inputPath = join(paths.evalsDir, input);
  const args: string[] = ["--input", inputPath, "--extraction-engine", extraction_engine];
  if (update_baseline) args.push("--update-baseline");

  const result = await execQaTools("eval-save", args);
  if (!result.success) {
    console.error("eval-save failed:", result.output);
    return c.json(fail("eval-save failed"), 500);
  }

  return c.json(ok({ saved: true, filename: input }));
});
