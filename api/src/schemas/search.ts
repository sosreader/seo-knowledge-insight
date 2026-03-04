import { z } from "zod";

export const searchRequestSchema = z.object({
  query: z.string().min(1).max(500),
  top_k: z.number().int().min(1).max(20).default(5),
  category: z.string().optional(),
});

export type SearchRequest = z.infer<typeof searchRequestSchema>;
