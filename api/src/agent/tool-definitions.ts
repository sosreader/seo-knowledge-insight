/**
 * Agent tool definitions — Zod schemas + OpenAI function calling format.
 */

import { z } from "zod";

// --- Zod schemas for argument validation ---

export const searchKnowledgeBaseSchema = z.object({
  query: z.string().min(1).max(500).describe("搜尋查詢（中文或英文皆可）"),
  top_k: z.number().int().min(1).max(10).default(5).describe("回傳筆數"),
  category: z.string().optional().describe("限定分類（如「技術SEO」「Core Web Vitals」）"),
});

export const getQaDetailSchema = z.object({
  id: z.string().min(1).describe("Q&A 的 stable_id（16-char hex）或 seq number"),
});

export const listCategoriesSchema = z.object({});

export const getStatsSchema = z.object({});

// --- OpenAI function calling tool definitions ---

export type ToolName = "search_knowledge_base" | "get_qa_detail" | "list_categories" | "get_stats";

export function getOpenAITools() {
  return [
    {
      type: "function" as const,
      function: {
        name: "search_knowledge_base" as const,
        description: "搜尋 SEO 知識庫，回傳最相關的 Q&A 條目。支援語意搜尋和分類篩選。",
        parameters: {
          type: "object",
          properties: {
            query: { type: "string", description: "搜尋查詢（中文或英文皆可）" },
            top_k: { type: "number", description: "回傳筆數（1-10，預設 5）" },
            category: { type: "string", description: "限定分類（如「技術SEO」「Core Web Vitals」）" },
          },
          required: ["query"],
        },
      },
    },
    {
      type: "function" as const,
      function: {
        name: "get_qa_detail" as const,
        description: "取得特定 Q&A 的完整內容（question + answer + metadata）。",
        parameters: {
          type: "object",
          properties: {
            id: { type: "string", description: "Q&A 的 stable_id 或 seq number" },
          },
          required: ["id"],
        },
      },
    },
    {
      type: "function" as const,
      function: {
        name: "list_categories" as const,
        description: "列出知識庫所有分類名稱，用於了解知識庫覆蓋範圍。",
        parameters: { type: "object", properties: {} },
      },
    },
    {
      type: "function" as const,
      function: {
        name: "get_stats" as const,
        description: "取得知識庫統計資訊（總筆數、分類數量）。",
        parameters: { type: "object", properties: {} },
      },
    },
  ];
}
