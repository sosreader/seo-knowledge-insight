import { z } from "zod";

export const searchRequestSchema = z.object({
  query: z.string().min(1).max(500),
  top_k: z.number().int().min(1).max(20).default(5),
  category: z.string().optional(),
  primary_category: z.string().optional(),
  extraction_model: z.string().optional(),
  maturity_level: z.enum(["L1", "L2", "L3", "L4"]).optional(),
  intent_label: z.string().optional(),
  scenario_tag: z.string().optional(),
  serving_tier: z.string().optional(),
  evidence_scope: z.string().optional(),
});

export type SearchRequest = z.infer<typeof searchRequestSchema>;
