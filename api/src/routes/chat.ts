import { Hono } from "hono";
import { chatRequestSchema, itemToSource } from "../schemas/chat.js";
import { ok, fail } from "../schemas/api-response.js";
import { ragChatObserved as ragChat } from "../services/rag-chat.js";
import { qaStore } from "../store/qa-store.js";
import { hasOpenAI, isAgentEnabled } from "../utils/mode-detect.js";
import { config } from "../config.js";
import { agentChatObserved as agentChat } from "../agent/agent-loop.js";
import { createAgentDeps } from "../agent/agent-deps.js";

export const chatRoute = new Hono();

function contextOnlyResponse(message: string) {
  const startMs = Date.now();
  const hits = qaStore.keywordSearch(message, config.CHAT_CONTEXT_K);
  const sources = hits.map(({ item, score }) => itemToSource(item, score));
  const metadata = { provider: "local", mode: "context-only", retrieval_count: sources.length, duration_ms: Date.now() - startMs };
  return { answer: null, sources, mode: "context-only" as const, metadata };
}

chatRoute.post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = chatRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { message, history } = parsed.data;

  if (!hasOpenAI()) {
    const result = contextOnlyResponse(message);
    return c.json(ok(result));
  }

  const historyDicts = history.map((h) => ({ role: h.role, content: h.content }));

  try {
    // Agent mode: LLM autonomously decides when to search
    if (isAgentEnabled()) {
      const deps = createAgentDeps();
      const result = await agentChat(
        message,
        historyDicts.length > 0 ? historyDicts : null,
        deps,
        { maxTurns: config.AGENT_MAX_TURNS, timeoutMs: config.AGENT_TIMEOUT_MS },
      );
      return c.json(ok({
        answer: result.answer,
        sources: result.sources,
        mode: result.mode,
        metadata: result.metadata,
      }));
    }

    // Full mode: single-pass RAG
    const result = await ragChat(message, historyDicts.length > 0 ? historyDicts : null);
    return c.json(ok({ answer: result.answer, sources: result.sources, mode: result.mode, metadata: result.metadata }));
  } catch (err: unknown) {
    // OpenAI auth/quota errors — fall back to context-only mode
    const status = (err as { status?: number }).status;
    if (status === 401 || status === 403 || status === 429) {
      console.warn(`OpenAI API error (${status}), falling back to context-only mode`);
      const result = contextOnlyResponse(message);
      return c.json(ok(result));
    }
    throw err;
  }
});
