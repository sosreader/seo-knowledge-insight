import { z } from "zod";

// --- Request schemas ---

export const fetchRequestSchema = z.object({
  since: z
    .string()
    .regex(/^(\d{4}-\d{2}-\d{2}|\d+d)$/, "Expected YYYY-MM-DD or Nd format")
    .optional(),
});

const SAFE_MD_FILENAME = /^[a-zA-Z0-9._\u4e00-\u9fff-]+\.md$/;

export const extractQARequestSchema = z.object({
  limit: z.number().int().positive().optional(),
  file: z
    .string()
    .regex(SAFE_MD_FILENAME, "file must be a .md filename (no path separators)")
    .optional(),
});

export const dedupeClassifyRequestSchema = z.object({
  skip_dedup: z.boolean().optional(),
  skip_classify: z.boolean().optional(),
  limit: z.number().int().positive().optional(),
});

export const metricsRequestSchema = z.object({
  source: z
    .string()
    .url("source must be a valid URL")
    .max(500)
    .refine(
      (url) => {
        try {
          const parsed = new URL(url);
          return (
            parsed.protocol === "https:" &&
            (parsed.hostname === "docs.google.com" || parsed.hostname === "sheets.google.com")
          );
        } catch {
          return false;
        }
      },
      { message: "source must be a Google Sheets URL (docs.google.com or sheets.google.com)" },
    ),
  tab: z.string().min(1).max(50).regex(/^[\w\s\u4e00-\u9fff-]+$/u, "tab must be alphanumeric, CJK, or spaces").default("vocus"),
});

export const crawledNotIndexedRequestSchema = z.object({
  source: z
    .string()
    .url("source must be a valid URL")
    .max(500)
    .refine(
      (url) => {
        try {
          const parsed = new URL(url);
          return (
            parsed.protocol === "https:" &&
            (parsed.hostname === "docs.google.com" || parsed.hostname === "sheets.google.com")
          );
        } catch {
          return false;
        }
      },
      { message: "source must be a Google Sheets URL (docs.google.com or sheets.google.com)" },
    ),
  tab: z.string().min(1).max(50).regex(/^[\w\s\u4e00-\u9fff-]+$/u, "tab must be alphanumeric, CJK, or spaces").default("vocus"),
});

export const metricsSaveSchema = z.object({
  metrics: z.any(),
  crawled_not_indexed: z.any().optional(),
  source: z.string().max(500),
  tab: z.string().min(1).max(50).regex(/^[\w\s\u4e00-\u9fff-]+$/u, "tab must be alphanumeric, CJK, or spaces"),
  label: z.string().max(60),
  weeks: z.number().int().min(1).max(12),
});

export const snapshotIdSchema = z.string().regex(/^[0-9]{8}-[0-9]{6}$/, "snapshot id must be YYYYMMDD-HHmmss");

// --- Snapshot Types ---

export interface MetricsSnapshotMeta {
  readonly id: string;
  readonly created_at: string;
  readonly label: string;
  readonly source: string;
  readonly tab: string;
  readonly weeks: number;
}

export interface MetricsSnapshot extends MetricsSnapshotMeta {
  readonly metrics: Record<string, unknown>;
}

// --- Response types ---

export interface PipelineStepStatus {
  readonly name: string;
  readonly label: string;
  readonly count: number;
  readonly detail: string;
}

export interface PipelineStatusResponse {
  readonly steps: readonly PipelineStepStatus[];
}

export interface MeetingEntry {
  readonly title: string;
  readonly id: string;
  readonly created_time: string;
  readonly last_edited_time: string;
  readonly url: string;
  readonly json_file: string;
  readonly md_file: string;
  readonly status: string;
}

export interface MeetingsResponse {
  readonly items: readonly MeetingEntry[];
  readonly total: number;
}

export interface MeetingPreviewResponse {
  readonly id: string;
  readonly title: string;
  readonly content: string;
  readonly size_bytes: number;
}

export interface UnprocessedItem {
  readonly file: string;
  readonly title: string;
  readonly source_collection: string;
}

export interface UnprocessedResponse {
  readonly items: readonly UnprocessedItem[];
  readonly total: number;
}

export interface FetchLogEntry {
  readonly event: string;
  readonly session_id: string;
  readonly ts: string;
  readonly page_id?: string;
  readonly page_title?: string;
  readonly [key: string]: unknown;
}

export interface FetchLogsResponse {
  readonly files: readonly string[];
  readonly entries: readonly FetchLogEntry[];
  readonly total: number;
}

export interface PipelineRunResult {
  readonly success: boolean;
  readonly output: string;
  readonly duration_ms: number;
}

// --- Source Docs ---

export interface SourceDocEntry {
  readonly file: string;
  readonly title: string;
  readonly source_type: "meeting" | "article";
  readonly source_collection: string;
  readonly source_url: string;
  readonly created_time: string;
  readonly size_bytes: number;
  readonly is_processed: boolean;
}

export const sourceDocsQuerySchema = z.object({
  source_type: z.enum(["meeting", "article"]).optional(),
  source_collection: z.string().max(100).optional(),
  keyword: z.string().max(200).optional(),
  is_processed: z
    .enum(["true", "false"])
    .transform((v) => v === "true")
    .optional(),
  limit: z.coerce.number().int().positive().max(100).default(20),
  offset: z.coerce.number().int().min(0).default(0),
});

export interface SourceDocsResponse {
  readonly items: readonly SourceDocEntry[];
  readonly total: number;
  readonly offset: number;
  readonly limit: number;
}

export interface SourceDocPreviewResponse {
  readonly file: string;
  readonly title: string;
  readonly collection: string;
  readonly content: string;
  readonly size_bytes: number;
}
