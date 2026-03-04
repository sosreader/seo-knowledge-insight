import { Hono } from "hono";
import { chatRequestSchema } from "../schemas/chat.js";
import type { SourceItem } from "../schemas/chat.js";
import { ok, fail } from "../schemas/api-response.js";
import { ragChat } from "../services/rag-chat.js";
import { qaStore } from "../store/qa-store.js";
import { hasOpenAI } from "../utils/mode-detect.js";
import { config } from "../config.js";

export const chatRoute = new Hono();

function itemToSource(
  item: { id: string; question: string; category: string; source_title: string; source_date: string; source_type: string; source_collection: string; source_url: string },
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

chatRoute.post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = chatRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { message, history } = parsed.data;

  if (!hasOpenAI()) {
    // Context-only mode: keyword search + return sources, no GPT completion
    const hits = qaStore.keywordSearch(message, config.CHAT_CONTEXT_K);
    const sources = hits.map(({ item, score }) => itemToSource(item, score));
    return c.json(ok({ answer: null, sources, mode: "context-only" as const }));
  }

  const historyDicts = history.map((h) => ({ role: h.role, content: h.content }));

  try {
    const result = await ragChat(message, historyDicts.length > 0 ? historyDicts : null);
    return c.json(ok({ answer: result.answer, sources: result.sources, mode: result.mode }));
  } catch (err: unknown) {
    // OpenAI auth/quota errors — fall back to context-only mode
    const status = (err as { status?: number }).status;
    if (status === 401 || status === 403 || status === 429) {
      console.warn(`OpenAI API error (${status}), falling back to context-only mode`);
      const hits = qaStore.keywordSearch(message, config.CHAT_CONTEXT_K);
      const sources = hits.map(({ item, score }) => itemToSource(item, score));
      return c.json(ok({ answer: null, sources, mode: "context-only" as const }));
    }
    throw err;
  }
});
