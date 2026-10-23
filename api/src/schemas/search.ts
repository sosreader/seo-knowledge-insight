import { z } from "zod";
import { maturityLevelSchema } from "../utils/maturity.js";

/**
 * hybrid／semantic 需要查詢 embedding（LLM）；keyword 純記憶體。
 * 未指定：LLM 可用走 hybrid，LLM disabled 自動退 keyword 並在回應標 llm_disabled。
 * semantic 目前與 hybrid 同一條檢索路徑（PG 端 match_qa_items 向量 over-retrieve＋重排）。
 */
export const searchModeSchema = z.enum(["hybrid", "semantic", "keyword"]);

export const searchRequestSchema = z.object({
  query: z.string().min(1).max(500),
  mode: searchModeSchema.optional(),
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
export type SearchModeParam = z.infer<typeof searchModeSchema>;
