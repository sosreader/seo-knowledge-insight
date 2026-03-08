/**
 * Report file utilities — shared between routes/reports.ts and sync/report-sync.ts.
 *
 * Extracted from routes/reports.ts to avoid duplication.
 */

import {
  readdirSync,
  readFileSync,
  statSync,
  existsSync,
  openSync,
  readSync,
  closeSync,
} from "node:fs";
import { join } from "node:path";
import { paths } from "../config.js";
import type { ReportSummary, ReportMeta } from "../schemas/report.js";

/** Matches report_YYYYMMDD.md (legacy) and report_YYYYMMDD_<sha1-8>.md (content-addressed). */
export const REPORT_PATTERN = /^report_(\d{8}(?:_[0-9a-f]{8})?)\.md$/;

export const REPORT_META_RE = /<!-- report_meta ({[\s\S]*?}) -->/;

/** Parse report_meta JSON from embedded HTML comment in report content. */
export function parseReportMeta(content: string): ReportMeta | undefined {
  const m = content.match(REPORT_META_RE);
  if (!m) return undefined;
  try {
    const raw = JSON.parse(m[1]) as Record<string, unknown>;
    return {
      weeks: typeof raw.weeks === "number" ? raw.weeks : 1,
      generated_at: typeof raw.generated_at === "string" ? raw.generated_at : "",
      generation_mode: typeof raw.generation_mode === "string" ? raw.generation_mode : "template",
      generation_label: typeof raw.generation_label === "string" ? raw.generation_label : "",
      model: typeof raw.model === "string" ? raw.model : undefined,
    };
  } catch {
    return undefined;
  }
}

/** Read last N bytes of a file (for parsing meta from tail without reading entire file). */
export function readTail(filepath: string, bytes: number): string {
  const { size } = statSync(filepath);
  const start = Math.max(0, size - bytes);
  const buf = Buffer.alloc(Math.min(bytes, size));
  const fd = openSync(filepath, "r");
  try {
    readSync(fd, buf, 0, buf.length, start);
    return buf.toString("utf-8");
  } finally {
    closeSync(fd);
  }
}

/** List all report files from the output directory, newest first. */
export function listReportFiles(): readonly ReportSummary[] {
  const dir = paths.outputDir;
  if (!existsSync(dir)) return [];

  const files = readdirSync(dir)
    .filter((f) => REPORT_PATTERN.test(f))
    .map((f) => {
      const m = REPORT_PATTERN.exec(f)!;
      const filepath = join(dir, f);
      const st = statSync(filepath);
      const tail = readTail(filepath, 300);
      const meta = parseReportMeta(tail);
      return {
        date: m[1]!,
        filename: f,
        size_bytes: st.size,
        mtime: st.mtimeMs,
        meta,
      };
    })
    .sort((a, b) => b.mtime - a.mtime);

  return files.map(({ date, filename, size_bytes, meta }) => ({ date, filename, size_bytes, meta }));
}

/** Read the full content of a report file by date_key. Returns null if not found. */
export function readReportFile(dateKey: string): { content: string; size_bytes: number; meta: ReportMeta | undefined } | null {
  const filename = `report_${dateKey}.md`;
  const filepath = join(paths.outputDir, filename);
  if (!existsSync(filepath)) return null;

  const content = readFileSync(filepath, "utf-8");
  const size_bytes = statSync(filepath).size;
  const meta = parseReportMeta(content);
  return { content, size_bytes, meta };
}
