import { z } from "zod";

export const generateRequestSchema = z.object({
  metrics_url: z.string().url().optional(),
});

export type GenerateRequest = z.infer<typeof generateRequestSchema>;

export interface ReportSummary {
  readonly date: string;
  readonly filename: string;
  readonly size_bytes: number;
}

export interface ReportDetail extends ReportSummary {
  readonly content: string;
}
