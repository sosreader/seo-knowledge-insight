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

export function itemToSource(
  item: {
    id: string;
    question: string;
    category: string;
    source_title: string;
    source_date: string;
    source_type: string;
    source_collection: string;
    source_url: string;
  },
  score: number,
): SourceItem {
  return {
    id: item.id,
    question: item.question,
    category: item.category,
    source_title: item.source_title,
    source_date: item.source_date,
    source_type: item.source_type,
    source_collection: item.source_collection,
    source_url: item.source_url,
    score: Math.round(score * 10000) / 10000,
  };
}
