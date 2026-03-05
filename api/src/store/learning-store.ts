/**
 * Learning Store — JSONL append-only log for feedback and search misses.
 *
 * Factory pattern: uses Supabase when available, falls back to local JSONL.
 */

import { appendFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { paths } from "../config.js";
import { hasSupabase } from "./supabase-client.js";
import {
  recordFeedbackSupabase,
  recordMissSupabase,
} from "./supabase-learning-store.js";

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

/** Record feedback — Supabase or local JSONL. Fire-and-forget for Supabase. */
export function recordFeedback(params: {
  query: string;
  qa_id: string;
  feedback: string;
  top_score?: number;
}): void {
  if (hasSupabase()) {
    recordFeedbackSupabase(params).catch((err) =>
      console.warn("Failed to record feedback to Supabase:", err),
    );
    return;
  }
  recordFeedbackLocal(params);
}

/** Record search miss — Supabase or local JSONL. Fire-and-forget for Supabase. */
export function recordMiss(params: {
  query: string;
  top_score: number;
  context: string;
}): void {
  if (hasSupabase()) {
    recordMissSupabase(params).catch((err) =>
      console.warn("Failed to record miss to Supabase:", err),
    );
    return;
  }
  recordMissLocal(params);
}
