import { z } from "zod";

export const historyMessageSchema = z.object({
  role: z.enum(["user", "assistant"]),
  content: z.string(),
});

export const chatRequestSchema = z.object({
  message: z.string().min(1).max(2000),
  history: z.array(historyMessageSchema).max(20).default([]),
});

export type ChatRequest = z.infer<typeof chatRequestSchema>;

export interface SourceItem {
  readonly id: string;
  readonly question: string;
  readonly category: string;
  readonly source_title: string;
  readonly source_date: string;
  readonly score: number;
  readonly source_type: string;
  readonly source_collection: string;
  readonly source_url: string;
}

export interface ChatResponse {
  readonly answer: string | null;
  readonly sources: readonly SourceItem[];
  readonly mode: "full" | "context-only";
}
