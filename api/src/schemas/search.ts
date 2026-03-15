import { z } from "zod";
import { maturityLevelSchema } from "../utils/maturity.js";

export const searchRequestSchema = z.object({
  query: z.string().min(1).max(500),
  top_k: z.number().int().min(1).max(20).default(5),
  category: z.string().optional(),
  primary_category: z.string().optional(),
  extraction_model: z.string().optional(),
  maturity_level: maturityLevelSchema.optional(),
  intent_label: z.string().optional(),
  scenario_tag: z.string().optional(),
  serving_tier: z.string().optional(),
  evidence_scope: z.string().optional(),
});

export type SearchRequest = z.infer<typeof searchRequestSchema>;
