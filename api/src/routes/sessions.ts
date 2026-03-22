import { Hono } from "hono";
import {
  createSessionSchema,
  sendMessageSchema,
  sessionIdSchema,
  sessionListParamsSchema,
  type SessionDetailOut,
  type SessionSummaryOut,
} from "../schemas/session.js";
import { ok, fail } from "../schemas/api-response.js";
import { sessionStore } from "../store/session-store.js";
import type { Session } from "../store/session-store.js";
import { ragChatObserved as ragChat } from "../services/rag-chat.js";
import { anthropicRagChatObserved as anthropicRagChat } from "../services/anthropic-chat.js";
import { resolveMode, getChatProvider } from "../utils/mode-detect.js";
import { resolveCapabilities, formatCapabilityTag } from "../utils/capabilities.js";
import { qaStore } from "../store/qa-store.js";
import { config } from "../config.js";
import { agentChatObserved as agentChat } from "../agent/agent-loop.js";
import { anthropicAgentChatObserved as anthropicAgentChat } from "../agent/anthropic-agent-loop.js";
import { createAgentDeps } from "../agent/agent-deps.js";

export const sessionsRoute = new Hono();

function keywordHitsToSources(message: string, k: number) {
  const hits = qaStore.keywordSearch(message, k);
  return hits.map(({ item, score }) => ({
    id: item.id, question: item.question, category: item.category,
    source_title: item.source_title, source_date: item.source_date,
    score: Math.round(score * 10000) / 10000,
  }));
}

function toSummary(s: Session): SessionSummaryOut {
  return {
    id: s.id,
    title: s.title,
    created_at: s.created_at,
    updated_at: s.updated_at,
  };
}

/** Expose only known-safe metadata fields (allowlist). */
function safeMetadata(metadata: Record<string, unknown> | undefined): Record<string, unknown> | undefined {
  if (!metadata?.maturity_level) return undefined;
  return { maturity_level: metadata.maturity_level };
}

function toDetail(s: Session): SessionDetailOut {
  const meta = safeMetadata(s.metadata);
  return {
    id: s.id,
    title: s.title,
    created_at: s.created_at,
    updated_at: s.updated_at,
    ...(meta ? { metadata: meta } : {}),
    messages: s.messages.map((m) => ({
      role: m.role,
      content: m.content,
      sources: m.sources,
      created_at: m.created_at,
      ...(m.metadata ? { metadata: m.metadata } : {}),
    })),
  };
}

sessionsRoute.get("/", async (c) => {
  const parsed = sessionListParamsSchema.safeParse({
    limit: c.req.query("limit"),
    offset: c.req.query("offset"),
  });

  if (!parsed.success) {
    return c.json(fail("Invalid query parameters"), 400);
  }

  const { limit, offset } = parsed.data;
  const { sessions, total } = await sessionStore.listSessions(limit, offset);

  return c.json(
    ok({
      items: sessions.map(toSummary),
      total,
    }),
  );
});

sessionsRoute.post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}));
  const parsed = createSessionSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  const session = await sessionStore.createSession(parsed.data.title ?? "");
  return c.json(ok(toDetail(session)));
});

sessionsRoute.get("/:session_id", async (c) => {
  const sessionId = c.req.param("session_id");
  if (!sessionIdSchema.safeParse(sessionId).success) {
    return c.json(fail("Invalid session ID format"), 400);
  }
  const session = await sessionStore.getSession(sessionId);

  if (!session) {
    return c.json(fail("Session not found"), 404);
  }

  return c.json(ok(toDetail(session)));
});

sessionsRoute.post("/:session_id/messages", async (c) => {
  const sessionId = c.req.param("session_id");
  if (!sessionIdSchema.safeParse(sessionId).success) {
    return c.json(fail("Invalid session ID format"), 400);
  }
  const body = await c.req.json().catch(() => ({}));
  const parsed = sendMessageSchema.safeParse(body);

  if (!parsed.success) {
    return c.json(fail("Invalid request body"), 400);
  }

  let session = await sessionStore.getSession(sessionId);
  if (!session) {
    return c.json(fail("Session not found"), 404);
  }

  const { message: userMessage, mode: requestMode, maturity_level: requestMaturityLevel } = parsed.data;

  // 1. Save user message
  const userMsg = {
    role: "user" as const,
    content: userMessage,
    sources: [] as Record<string, unknown>[],
    created_at: new Date().toISOString().replace(/(\.\d{3})\d*Z$/, "$1Z"),
  };

  session = await sessionStore.addMessage(sessionId, userMsg);
  if (!session) {
    return c.json(fail("Failed to add message (session full or conflict)"), 409);
  }

  // 1b. Resolve maturity level: request > session > null
  const sessionMaturity = session.metadata?.maturity_level ?? undefined;
  const effectiveMaturity = requestMaturityLevel ?? sessionMaturity ?? null;

  // 1c. Persist maturity_level to session on first use
  if (requestMaturityLevel && requestMaturityLevel !== sessionMaturity) {
    await sessionStore.updateMetadata(sessionId, { maturity_level: requestMaturityLevel });
  }

  // 2. Build history from existing messages (exclude the just-added user msg, cap at 20)
  const MAX_HISTORY = 20;
  const allPrior = session.messages.slice(0, -1);
  const history = allPrior.slice(-MAX_HISTORY).map((m) => ({
    role: m.role,
    content: m.content,
  }));

  // 3. Call RAG chat (with context-only fallback when no LLM)
  let result: { answer: string | null; sources: Record<string, unknown>[]; mode: string; metadata?: Record<string, unknown> };
  const ragStartMs = Date.now();
  const caps = resolveCapabilities(c.req.header("user-agent"));

  if (caps.llm !== "none") {
    const effectiveMode = resolveMode(requestMode);
    const provider = getChatProvider();
    try {
      if (effectiveMode === "agent") {
        const deps = createAgentDeps();
        const agentFn = provider === "anthropic" ? anthropicAgentChat : agentChat;
        const agentResult = await agentFn(
          userMessage,
          history.length > 0 ? history : null,
          deps,
          { maxTurns: config.AGENT_MAX_TURNS, timeoutMs: config.AGENT_TIMEOUT_MS },
          effectiveMaturity,
        );
        result = {
          answer: agentResult.answer,
          sources: agentResult.sources as unknown as Record<string, unknown>[],
          mode: agentResult.mode,
          metadata: agentResult.metadata as unknown as Record<string, unknown>,
        };
      } else {
        const ragFn = provider === "anthropic" ? anthropicRagChat : ragChat;
        const ragResult = await ragFn(userMessage, history.length > 0 ? history : null, effectiveMaturity);
        result = {
          answer: ragResult.answer,
          sources: ragResult.sources as unknown as Record<string, unknown>[],
          mode: ragResult.mode ?? "rag",
          metadata: ragResult.metadata as unknown as Record<string, unknown>,
        };
      }
    } catch (err: unknown) {
      const status = (err as { status?: number }).status;
      if (status === 401 || status === 403 || status === 429) {
        const sources = keywordHitsToSources(userMessage, config.CHAT_CONTEXT_K);
        result = {
          answer: null, sources, mode: "context-only",
          metadata: { provider: "local", mode: "context-only", retrieval_count: sources.length, duration_ms: Date.now() - ragStartMs },
        };
      } else {
        throw err;
      }
    }
  } else {
    const sources = keywordHitsToSources(userMessage, config.CHAT_CONTEXT_K);
    result = {
      answer: null, sources, mode: "context-only",
      metadata: { provider: "local", mode: "context-only", retrieval_count: sources.length, duration_ms: Date.now() - ragStartMs },
    };
  }

  // 4. Save assistant message
  const assistantMsg = {
    role: "assistant" as const,
    content: result.answer ?? "",
    sources: result.sources,
    created_at: new Date().toISOString().replace(/(\.\d{3})\d*Z$/, "$1Z"),
    ...(result.metadata ? { metadata: result.metadata } : {}),
  };

  session = await sessionStore.addMessage(sessionId, assistantMsg);
  if (!session) {
    return c.json(fail("Failed to save assistant response"), 500);
  }

  return c.json(
    ok({
      answer: result.answer,
      sources: result.sources,
      mode: result.mode,
      session: toDetail(session),
      execution_context: formatCapabilityTag(caps),
    }),
  );
});

sessionsRoute.delete("/:session_id", async (c) => {
  const sessionId = c.req.param("session_id");
  if (!sessionIdSchema.safeParse(sessionId).success) {
    return c.json(fail("Invalid session ID format"), 400);
  }
  const deleted = await sessionStore.deleteSession(sessionId);

  if (!deleted) {
    return c.json(fail("Session not found"), 404);
  }

  return c.json(ok({ deleted: true, session_id: sessionId }));
});
