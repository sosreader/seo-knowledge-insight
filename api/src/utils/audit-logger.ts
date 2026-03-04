/**
 * Audit Logger — JSONL append-only access log.
 *
 * Writes to output/access_logs/access_YYYYMMDD.jsonl
 */

import { appendFileSync, existsSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { paths } from "../config.js";

function getLogPath(): string {
  const dir = paths.accessLogsDir;
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  return join(dir, `access_${date}.jsonl`);
}

function writeLog(record: Record<string, unknown>): void {
  try {
    const line = JSON.stringify({ timestamp: new Date().toISOString(), ...record });
    appendFileSync(getLogPath(), line + "\n", "utf-8");
  } catch {
    // Audit logging should never crash the app
  }
}

export function logListQa(params: {
  filters: Record<string, unknown>;
  returnedIds: readonly string[];
  total: number;
  clientIp: string | null;
}): void {
  writeLog({ event: "list_qa", ...params });
}

export function logSearch(params: {
  query: string;
  topK: number;
  category: string | null;
  returnedIds: readonly string[];
  sourceTitles: readonly string[];
  clientIp: string | null;
}): void {
  writeLog({ event: "search", ...params });
}

export function logChat(params: {
  message: string;
  returnedIds: readonly string[];
  sourceTitles: readonly string[];
  clientIp: string | null;
}): void {
  writeLog({ event: "chat", ...params });
}
