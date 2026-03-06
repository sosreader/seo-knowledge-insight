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
import { hasOpenAI } from "../utils/mode-detect.js";
import { qaStore } from "../store/qa-store.js";
import { config } from "../config.js";

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

function toDetail(s: Session): SessionDetailOut {
  return {
    id: s.id,
    title: s.title,
    created_at: s.created_at,
    updated_at: s.updated_at,
    messages: s.messages.map((m) => ({
      role: m.role,
      content: m.content,
      sources: m.sources,
      created_at: m.created_at,
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

  // 1. Save user message
  const userMsg = {
    role: "user" as const,
    content: parsed.data.message,
    sources: [] as Record<string, unknown>[],
    created_at: new Date().toISOString().replace(/(\.\d{3})\d*Z$/, "$1Z"),
  };

  session = await sessionStore.addMessage(sessionId, userMsg);
  if (!session) {
    return c.json(fail("Failed to add message (session full or conflict)"), 409);
  }

  // 2. Build history from existing messages (exclude the just-added user msg)
  const history = session.messages.slice(0, -1).map((m) => ({
    role: m.role,
    content: m.content,
  }));

  // 3. Call RAG chat (with context-only fallback when no OpenAI)
  let result: { answer: string | null; sources: Record<string, unknown>[]; mode: string };

  if (hasOpenAI()) {
    try {
      const ragResult = await ragChat(parsed.data.message, history.length > 0 ? history : null);
      result = {
        answer: ragResult.answer,
        sources: ragResult.sources as unknown as Record<string, unknown>[],
        mode: ragResult.mode ?? "full",
      };
    } catch (err: unknown) {
      const status = (err as { status?: number }).status;
      if (status === 401 || status === 403 || status === 429) {
        const sources = keywordHitsToSources(parsed.data.message, config.CHAT_CONTEXT_K);
        result = { answer: null, sources, mode: "context-only" };
      } else {
        throw err;
      }
    }
  } else {
    const sources = keywordHitsToSources(parsed.data.message, config.CHAT_CONTEXT_K);
    result = { answer: null, sources, mode: "context-only" };
  }

  // 4. Save assistant message
  const assistantMsg = {
    role: "assistant" as const,
    content: result.answer ?? "",
    sources: result.sources,
    created_at: new Date().toISOString().replace(/(\.\d{3})\d*Z$/, "$1Z"),
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
