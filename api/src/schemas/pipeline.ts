import { z } from "zod";

// --- Request schemas ---

export const fetchRequestSchema = z.object({
  since: z
    .string()
    .regex(/^(\d{4}-\d{2}-\d{2}|\d+d)$/, "Expected YYYY-MM-DD or Nd format")
    .optional(),
});

export const extractQARequestSchema = z.object({
  limit: z.number().int().positive().optional(),
  file: z.string().optional(),
});

export const dedupeClassifyRequestSchema = z.object({
  skip_dedup: z.boolean().optional(),
  skip_classify: z.boolean().optional(),
  limit: z.number().int().positive().optional(),
});

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
