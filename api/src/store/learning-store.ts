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

function recordFeedbackLocal(params: FeedbackParams, timestamp: string): void {
  ensureDir(LEARNINGS_PATH);
  const record = {
    type: "feedback",
    timestamp,
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

export interface FeedbackParams {
  readonly query: string;
  readonly qa_id: string;
  readonly feedback: string;
  readonly feedback_category?: string;
  readonly top_score?: number;
}

/** 寫入後的回饋紀錄。PG 模式為 app_learning 讀回的列（id 為 bigint 字串）；本機 JSONL 無 id。 */
export interface RecordedFeedback {
  readonly id: string | null;
  readonly query: string;
  readonly qa_id: string;
  readonly feedback: string;
  readonly top_score: number | null;
  readonly created_at: string;
}

/**
 * Record feedback — vocus-warehouse（await＋RETURNING 讀回）或本機 JSONL。
 * app_learning 沒有 feedback_category 欄，PG 模式不保存該欄（本機 JSONL 保存）。
 */
export async function recordFeedback(params: FeedbackParams): Promise<RecordedFeedback> {
  if (hasPg()) {
    return recordFeedbackPg(params);
  }
  const timestamp = new Date().toISOString();
  recordFeedbackLocal(params, timestamp);
  return {
    id: null,
    query: params.query,
    qa_id: params.qa_id,
    feedback: params.feedback,
    top_score: params.top_score ?? null,
    created_at: timestamp,
  };
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
