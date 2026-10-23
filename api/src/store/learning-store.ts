/**
 * Learning Store — JSONL append-only log for feedback and search misses.
 *
 * Factory pattern: vocus-warehouse app_learning in PG mode, local JSONL otherwise.
 */

import { appendFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { paths } from "../config.js";
import { hasPg } from "./pg-client.js";
import { recordFeedbackPg, recordMissPg } from "./pg-learning-store.js";

const LEARNINGS_PATH = resolve(paths.outputDir, "learnings.jsonl");

function ensureDir(filePath: string): void {
  const dir = dirname(filePath);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

function recordFeedbackLocal(params: {
  query: string;
  qa_id: string;
  feedback: string;
  feedback_category?: string;
  top_score?: number;
}): void {
  ensureDir(LEARNINGS_PATH);
  const record = {
    type: "feedback",
    timestamp: new Date().toISOString(),
    ...params,
  };
  appendFileSync(LEARNINGS_PATH, JSON.stringify(record) + "\n", "utf-8");
}

function recordMissLocal(params: {
  query: string;
  top_score: number;
  context: string;
}): void {
  ensureDir(LEARNINGS_PATH);
  const record = {
    type: "miss",
    timestamp: new Date().toISOString(),
    ...params,
  };
  appendFileSync(LEARNINGS_PATH, JSON.stringify(record) + "\n", "utf-8");
}

/** Record feedback — vocus-warehouse or local JSONL. Fire-and-forget in PG mode. */
export function recordFeedback(params: {
  query: string;
  qa_id: string;
  feedback: string;
  feedback_category?: string;
  top_score?: number;
}): void {
  if (hasPg()) {
    recordFeedbackPg(params).catch((err) =>
      console.warn("Failed to record feedback to vocus-warehouse:", err),
    );
    return;
  }
  recordFeedbackLocal(params);
}

/** Record search miss — vocus-warehouse or local JSONL. Fire-and-forget in PG mode. */
export function recordMiss(params: {
  query: string;
  top_score: number;
  context: string;
}): void {
  if (hasPg()) {
    recordMissPg(params).catch((err) =>
      console.warn("Failed to record miss to vocus-warehouse:", err),
    );
    return;
  }
  recordMissLocal(params);
}
