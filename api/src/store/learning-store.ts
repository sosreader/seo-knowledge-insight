/**
 * Learning Store — JSONL append-only log for feedback and search misses.
 */

import { appendFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { paths } from "../config.js";

const LEARNINGS_PATH = resolve(paths.outputDir, "learnings.jsonl");

function ensureDir(filePath: string): void {
  const dir = dirname(filePath);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

export function recordFeedback(params: {
  query: string;
  qa_id: string;
  feedback: string;
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

export function recordMiss(params: {
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
