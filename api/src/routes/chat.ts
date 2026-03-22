import { Hono } from "hono";
import { streamSSE } from "hono/streaming";
import { chatRequestSchema, itemToSource } from "../schemas/chat.js";
import { ok, fail } from "../schemas/api-response.js";
import { ragChatObserved as ragChat } from "../services/rag-chat.js";
import { ragChatStream } from "../services/rag-chat-stream.js";
import { qaStore } from "../store/qa-store.js";
import { resolveMode } from "../utils/mode-detect.js";
import { resolveCapabilities, formatCapabilityTag } from "../utils/capabilities.js";
import { config } from "../config.js";
import { agentChatObserved as agentChat } from "../agent/agent-loop.js";
import { createAgentDeps } from "../agent/agent-deps.js";

export const chatRoute = new Hono();

function isLambdaRuntime(): boolean {
  return (
    !!process.env.AWS_LAMBDA_FUNCTION_NAME || !!process.env.AWS_EXECUTION_ENV
  );
}

function contextOnlyResponse(message: string) {
  const startMs = Date.now();
  const hits = qaStore.keywordSearch(message, config.CHAT_CONTEXT_K);
  const sources = hits.map(({ item, score }) => itemToSource(item, score));
  const metadata = {
    provider: "local",
    mode: "context-only",
    retrieval_count: sources.length,
    duration_ms: Date.now() - startMs,
  };
  return { answer: null, sources, mode: "context-only" as const, metadata };
}

chatRoute.post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = chatRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const {
    message,
    history,
    mode: requestMode,
    maturity_level: maturityLevel,
  } = parsed.data;

  const caps = resolveCapabilities(c.req.header("user-agent"));

  if (caps.llm === "none") {
    const result = { ...contextOnlyResponse(message), execution_context: formatCapabilityTag(caps) };
    return c.json(ok(result));
  }

  const historyDicts = history.map((h) => ({
    role: h.role,
    content: h.content,
  }));
  const effectiveMode = resolveMode(requestMode);

  try {
    // Agent mode: LLM autonomously decides when to search
    if (effectiveMode === "agent") {
      const deps = createAgentDeps();
      const result = await agentChat(
        message,
        historyDicts.length > 0 ? historyDicts : null,
        deps,
        {
          maxTurns: config.AGENT_MAX_TURNS,
          timeoutMs: config.AGENT_TIMEOUT_MS,
        },
        maturityLevel,
      );
      return c.json(
        ok({
          answer: result.answer,
          sources: result.sources,
          mode: result.mode,
          metadata: result.metadata,
          execution_context: formatCapabilityTag(caps),
        }),
      );
    }

    // Full mode: single-pass RAG
    const result = await ragChat(
      message,
      historyDicts.length > 0 ? historyDicts : null,
      maturityLevel ?? null,
    );
    return c.json(
      ok({
        answer: result.answer,
        sources: result.sources,
        mode: result.mode,
        metadata: result.metadata,
        execution_context: formatCapabilityTag(caps),
      }),
    );
  } catch (err: unknown) {
    // OpenAI auth/quota errors — fall back to context-only mode
    const status = (err as { status?: number }).status;
    if (status === 401 || status === 403 || status === 429) {
      console.warn(
        `OpenAI API error (${status}), falling back to context-only mode`,
      );
      const result = contextOnlyResponse(message);
      return c.json(ok(result));
    }
    throw err;
  }
});

/**
 * POST /chat/stream — SSE streaming RAG chat.
 *
 * Events:
 *   - event: sources   → JSON array of SourceItem
 *   - event: token     → partial text chunk
 *   - event: metadata  → MessageMetadata JSON
 *   - event: done      → stream complete
 *   - event: error     → error message
 */
chatRoute.post("/stream", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = chatRequestSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const { message, history, maturity_level: streamMaturityLevel } = parsed.data;

  const streamCaps = resolveCapabilities(c.req.header("user-agent"));

  if (streamCaps.llm === "none") {
    // Streaming not available without OpenAI — return non-streaming fallback
    const result = { ...contextOnlyResponse(message), execution_context: formatCapabilityTag(streamCaps) };
    return c.json(ok(result));
  }

  if (isLambdaRuntime()) {
    return c.json(
      fail(
        "Streaming is not available in Lambda production. Use POST /api/v1/chat instead.",
      ),
      501,
    );
  }

  const historyDicts = history.map((h) => ({
    role: h.role,
    content: h.content,
  }));

  return streamSSE(c, async (stream) => {
    let eventId = 0;

    await ragChatStream(
      message,
      historyDicts.length > 0 ? historyDicts : null,
      {
        onSources: async (sources) => {
          await stream.writeSSE({
            event: "sources",
            data: JSON.stringify(sources),
            id: String(eventId++),
          });
        },
        onToken: async (token) => {
          await stream.writeSSE({
            event: "token",
            data: token,
            id: String(eventId++),
          });
        },
        onMetadata: async (metadata) => {
          await stream.writeSSE({
            event: "metadata",
            data: JSON.stringify(metadata),
            id: String(eventId++),
          });
        },
        onDone: async () => {
          await stream.writeSSE({
            event: "done",
            data: "[DONE]",
            id: String(eventId++),
          });
        },
        onError: async (error) => {
          await stream.writeSSE({
            event: "error",
            data: error,
            id: String(eventId++),
          });
        },
      },
      streamMaturityLevel ?? null,
    );
  });
});
