/**
 * Tool executor — dispatches tool calls to actual implementations with Zod validation.
 */

import {
  searchKnowledgeBaseSchema,
  getQaDetailSchema,
  type ToolName,
} from "./tool-definitions.js";
import type { AgentDeps, ToolResult } from "./types.js";

const TOOL_TIMEOUT_MS = 15_000;

async function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  let timer: ReturnType<typeof setTimeout>;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error(`Tool timed out after ${ms}ms`)), ms);
  });
  try {
    return await Promise.race([promise, timeout]);
  } finally {
    clearTimeout(timer!);
  }
}

export async function executeTool(
  name: ToolName,
  rawArgs: Record<string, unknown>,
  deps: AgentDeps,
): Promise<ToolResult> {
  const startMs = Date.now();

  try {
    const result = await withTimeout(executeToolImpl(name, rawArgs, deps), TOOL_TIMEOUT_MS);
    return {
      toolName: name,
      args: rawArgs,
      result,
      durationMs: Date.now() - startMs,
    };
  } catch {
    return {
      toolName: name,
      args: rawArgs,
      result: JSON.stringify({ error: "Tool execution failed" }),
      durationMs: Date.now() - startMs,
    };
  }
}

async function executeToolImpl(
  name: ToolName,
  rawArgs: Record<string, unknown>,
  deps: AgentDeps,
): Promise<string> {
  switch (name) {
    case "search_knowledge_base": {
      const args = searchKnowledgeBaseSchema.parse(rawArgs);
      const hits = await deps.searchKnowledgeBase(args.query, args.top_k);
      const filtered = args.category
        ? hits.filter((h) => (h.item as Record<string, unknown>).category === args.category)
        : hits;
      return JSON.stringify(
        filtered.map(({ item, score }) => ({
          id: (item as Record<string, unknown>).id,
          question: (item as Record<string, unknown>).question,
          answer: String((item as Record<string, unknown>).answer ?? "").slice(0, 300),
          category: (item as Record<string, unknown>).category,
          source_title: (item as Record<string, unknown>).source_title,
          source_date: (item as Record<string, unknown>).source_date,
          score: Math.round(score * 10000) / 10000,
        })),
      );
    }
    case "get_qa_detail": {
      const args = getQaDetailSchema.parse(rawArgs);
      const item = deps.getQaDetail(args.id);
      if (!item) return JSON.stringify({ error: "QA item not found" });
      return JSON.stringify(item);
    }
    case "list_categories": {
      const categories = deps.listCategories();
      return JSON.stringify(categories);
    }
    case "get_stats": {
      const stats = deps.getStats();
      return JSON.stringify(stats);
    }
    default:
      return JSON.stringify({ error: `Unknown tool: ${name}` });
  }
}
