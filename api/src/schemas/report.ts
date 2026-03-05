import { z } from "zod";

export const generateRequestSchema = z.object({
  metrics_url: z.string().url().optional(),
  snapshot_id: z.string().regex(/^[0-9]{8}-[0-9]{6}$/).optional(),
  weeks: z.number().int().min(1).max(12).optional(),
  situation_analysis: z.string().max(2000).optional(),
  traffic_analysis: z.string().max(2000).optional(),
});

export type GenerateRequest = z.infer<typeof generateRequestSchema>;

export interface ReportSummary {
  readonly date: string;
  readonly filename: string;
  readonly size_bytes: number;
  readonly meta?: ReportMeta;
}

export interface ReportMeta {
  readonly weeks: number;
  readonly generated_at: string;
  readonly generation_mode: string;
  readonly generation_label: string;
}

export interface ReportDetail extends ReportSummary {
  readonly content: string;
  readonly meta?: ReportMeta;
}
