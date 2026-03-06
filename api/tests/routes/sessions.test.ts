import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock config — no OpenAI key by default
vi.mock("../../src/config.js", () => ({
  config: {
    OPENAI_API_KEY: "",
    SEO_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
    CHAT_CONTEXT_K: 5,
    OPENAI_MODEL: "gpt-5.2",
    OPENAI_EMBEDDING_MODEL: "text-embedding-3-small",
    AGENT_ENABLED: false,
    AGENT_MAX_TURNS: 5,
    AGENT_TIMEOUT_MS: 90000,
  },
  paths: {
    rootDir: "/tmp",
    outputDir: "/tmp/output",
    rawDataDir: "/tmp/raw_data",
    fetchLogsDir: "/tmp/output/fetch_logs",
    qaJsonPath: "/tmp/output/qa_final.json",
    qaEnrichedJsonPath: "/tmp/output/qa_enriched.json",
    qaEmbeddingsPath: "/tmp/output/qa_embeddings.npy",
    sessionsDir: "/tmp/output/sessions",
    scriptsDir: "/tmp/scripts",
    accessLogsDir: "/tmp/output/access_logs",
    evalsDir: "/tmp/output/evals",
  },
}));

const mockKeywordSearch = vi.fn().mockReturnValue([
  {
    item: {
      id: "abc123def456",
      question: "What is SEO?",
      answer: "SEO is Search Engine Optimization",
      keywords: ["SEO"],
      category: "basics",
      source_title: "Meeting 1",
      source_date: "2024-05-02",
    },
    score: 0.5,
  },
]);

vi.mock("../../src/store/qa-store.js", () => ({
  qaStore: {
    loaded: true,
    count: 10,
    keywordSearch: (...args: unknown[]) => mockKeywordSearch(...args),
  },
}));

const mockRagChat = vi.fn().mockResolvedValue({
  answer: "SEO is important for visibility",
  sources: [
    {
      id: "abc123def456",
      question: "What is SEO?",
      category: "basics",
      source_title: "Meeting 1",
      source_date: "2024-05-02",
      score: 0.85,
    },
  ],
  mode: "rag",
  metadata: {
    model: "gpt-5.2",
    provider: "openai",
    mode: "rag",
    embedding_model: "text-embedding-3-small",
    input_tokens: 150,
    output_tokens: 80,
    total_tokens: 230,
    duration_ms: 1200,
    retrieval_count: 1,
    reranker_used: false,
  },
});

vi.mock("../../src/services/rag-chat.js", () => ({
  ragChat: (...args: unknown[]) => mockRagChat(...args),
  ragChatObserved: (...args: unknown[]) => mockRagChat(...args),
}));

const mockAgentChat = vi.fn().mockResolvedValue({
  answer: "Agent session answer",
  sources: [{ id: "abc123def456", question: "What is SEO?", category: "basics", source_title: "Meeting 1", source_date: "2024-05-02", score: 0.85 }],
  mode: "agent",
  metadata: { model: "gpt-5.2", provider: "openai", mode: "agent", input_tokens: 200, output_tokens: 100, total_tokens: 300, duration_ms: 2000, retrieval_count: 1, reranker_used: false, tool_calls_count: 1, agent_turns: 1, tool_calls: [] },
});

vi.mock("../../src/agent/agent-loop.js", () => ({
  agentChat: (...args: unknown[]) => mockAgentChat(...args),
  agentChatObserved: (...args: unknown[]) => mockAgentChat(...args),
}));

vi.mock("../../src/agent/agent-deps.js", () => ({
  createAgentDeps: () => ({}),
}));

// Mock session-store with in-memory store
vi.mock("../../src/store/session-store.js", () => {
  const sessions = new Map<string, Record<string, unknown>>();
  let counter = 0;
  const fakeUUID = (n: number) =>
    `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
  return {
    sessionStore: {
      createSession: (title: string) => {
        counter++;
        const id = fakeUUID(counter);
        const session = {
          id,
          title: title || `Session ${counter}`,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          messages: [],
        };
        sessions.set(id, session);
        return session;
      },
      getSession: (id: string) => sessions.get(id) ?? null,
      listSessions: (limit = 20, offset = 0) => {
        const all = [...sessions.values()];
        return { sessions: all.slice(offset, offset + limit), total: all.length };
      },
      addMessage: (id: string, msg: Record<string, unknown>) => {
        const session = sessions.get(id);
        if (!session) return null;
        (session.messages as Record<string, unknown>[]).push(msg);
        session.updated_at = new Date().toISOString();
        return session;
      },
      deleteSession: (id: string) => {
        if (!sessions.has(id)) return false;
        sessions.delete(id);
        return true;
      },
      _reset: () => {
        sessions.clear();
        counter = 0;
      },
    },
  };
});

import { Hono } from "hono";
import { sessionsRoute } from "../../src/routes/sessions.js";
import { config } from "../../src/config.js";
import { sessionStore } from "../../src/store/session-store.js";

function buildApp() {
  const app = new Hono();
  app.route("/api/v1/sessions", sessionsRoute);
  return app;
}

describe("Sessions API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (sessionStore as unknown as { _reset: () => void })._reset();
  });

  describe("POST /api/v1/sessions", () => {
    it("creates a new session", async () => {
      const app = buildApp();
      const res = await app.request("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Test Session" }),
      });
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.data.id).toBeTruthy();
      expect(body.data.messages).toEqual([]);
    });
  });

  describe("GET /api/v1/sessions", () => {
    it("lists sessions", async () => {
      const app = buildApp();
      // Create two sessions
      await app.request("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Session 1" }),
      });
      await app.request("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Session 2" }),
      });

      const res = await app.request("/api/v1/sessions?limit=10&offset=0");
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.data.items).toHaveLength(2);
      expect(body.data.total).toBe(2);
    });
  });

  describe("POST /:session_id/messages — context-only mode", () => {
    it("returns context-only when no OpenAI key", async () => {
      const app = buildApp();

      // Create session first
      const createRes = await app.request("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Test" }),
      });
      const { data: session } = await createRes.json();

      // Send message
      const res = await app.request(
        `/api/v1/sessions/${session.id}/messages`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: "What is SEO?" }),
        },
      );

      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.data.mode).toBe("context-only");
      expect(body.data.answer).toBeNull();
      expect(body.data.sources).toHaveLength(1);
      expect(body.data.sources[0].question).toBe("What is SEO?");
      expect(mockKeywordSearch).toHaveBeenCalledWith("What is SEO?", 5);
      expect(mockRagChat).not.toHaveBeenCalled();
    });

    it("saves empty content for assistant message in context-only mode", async () => {
      const app = buildApp();

      const createRes = await app.request("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Test" }),
      });
      const { data: session } = await createRes.json();

      await app.request(`/api/v1/sessions/${session.id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "What is SEO?" }),
      });

      // Check session detail has correct messages
      const detailRes = await app.request(
        `/api/v1/sessions/${session.id}`,
      );
      const detail = await detailRes.json();
      const msgs = detail.data.messages;

      expect(msgs).toHaveLength(2);
      expect(msgs[0].role).toBe("user");
      expect(msgs[0].content).toBe("What is SEO?");
      expect(msgs[1].role).toBe("assistant");
      expect(msgs[1].content).toBe(""); // empty string, not null
    });
  });

  describe("POST /:session_id/messages — rag mode", () => {
    it("returns rag mode when OpenAI key is set", async () => {
      const original = config.OPENAI_API_KEY;
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test-key";

      try {
        const app = buildApp();

        const createRes = await app.request("/api/v1/sessions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: "Full Mode Test" }),
        });
        const { data: session } = await createRes.json();

        const res = await app.request(
          `/api/v1/sessions/${session.id}/messages`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: "What is SEO?" }),
          },
        );

        expect(res.status).toBe(200);
        const body = await res.json();
        expect(body.data.mode).toBe("rag");
        expect(body.data.answer).toBe("SEO is important for visibility");
        expect(mockRagChat).toHaveBeenCalled();
      } finally {
        (config as Record<string, unknown>).OPENAI_API_KEY = original;
      }
    });
  });

  describe("POST /:session_id/messages — metadata", () => {
    it("saves metadata on assistant message in context-only mode", async () => {
      const app = buildApp();

      const createRes = await app.request("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Meta Test" }),
      });
      const { data: session } = await createRes.json();

      await app.request(`/api/v1/sessions/${session.id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "What is SEO?" }),
      });

      const detailRes = await app.request(`/api/v1/sessions/${session.id}`);
      const detail = await detailRes.json();
      const msgs = detail.data.messages;

      expect(msgs).toHaveLength(2);
      // user message has no metadata
      expect(msgs[0].metadata).toBeUndefined();
      // assistant message has metadata
      expect(msgs[1].metadata).toBeDefined();
      expect(msgs[1].metadata.provider).toBe("local");
      expect(msgs[1].metadata.mode).toBe("context-only");
      expect(msgs[1].metadata.retrieval_count).toBe(1);
      expect(typeof msgs[1].metadata.duration_ms).toBe("number");
    });

    it("saves metadata on assistant message in full mode", async () => {
      const original = config.OPENAI_API_KEY;
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test-key";

      try {
        const app = buildApp();

        const createRes = await app.request("/api/v1/sessions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: "Full Meta Test" }),
        });
        const { data: session } = await createRes.json();

        await app.request(`/api/v1/sessions/${session.id}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: "What is SEO?" }),
        });

        const detailRes = await app.request(`/api/v1/sessions/${session.id}`);
        const detail = await detailRes.json();
        const assistantMsg = detail.data.messages[1];

        expect(assistantMsg.metadata).toBeDefined();
        expect(assistantMsg.metadata.model).toBe("gpt-5.2");
        expect(assistantMsg.metadata.provider).toBe("openai");
        expect(assistantMsg.metadata.input_tokens).toBe(150);
        expect(assistantMsg.metadata.output_tokens).toBe(80);
        expect(assistantMsg.metadata.total_tokens).toBe(230);
        expect(assistantMsg.metadata.retrieval_count).toBe(1);
      } finally {
        (config as Record<string, unknown>).OPENAI_API_KEY = original;
      }
    });
  });

  describe("POST /:session_id/messages — error handling", () => {
    it("returns 400 for invalid session ID format", async () => {
      const app = buildApp();
      const res = await app.request(
        "/api/v1/sessions/nonexistent/messages",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: "Hello" }),
        },
      );
      expect(res.status).toBe(400);
    });

    it("returns 404 for non-existent session with valid UUID", async () => {
      const app = buildApp();
      const res = await app.request(
        "/api/v1/sessions/00000000-0000-4000-8000-999999999999/messages",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: "Hello" }),
        },
      );
      expect(res.status).toBe(404);
    });

    it("returns 400 for empty message", async () => {
      const app = buildApp();

      const createRes = await app.request("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Test" }),
      });
      const { data: session } = await createRes.json();

      const res = await app.request(
        `/api/v1/sessions/${session.id}/messages`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: "" }),
        },
      );
      expect(res.status).toBe(400);
    });
  });

  describe("POST /:session_id/messages — request-level mode", () => {
    it("mode: agent forces agent path even when AGENT_ENABLED=false", async () => {
      const originalKey = config.OPENAI_API_KEY;
      const originalAgent = config.AGENT_ENABLED;
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test-key";
      (config as Record<string, unknown>).AGENT_ENABLED = false;

      try {
        const app = buildApp();
        const createRes = await app.request("/api/v1/sessions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: "Agent Override" }),
        });
        const { data: session } = await createRes.json();

        const res = await app.request(`/api/v1/sessions/${session.id}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: "What is SEO?", mode: "agent" }),
        });
        expect(res.status).toBe(200);
        const body = await res.json();
        expect(body.data.mode).toBe("agent");
        expect(mockAgentChat).toHaveBeenCalled();
        expect(mockRagChat).not.toHaveBeenCalled();
      } finally {
        (config as Record<string, unknown>).OPENAI_API_KEY = originalKey;
        (config as Record<string, unknown>).AGENT_ENABLED = originalAgent;
      }
    });

    it("mode: rag forces rag path even when AGENT_ENABLED=true", async () => {
      const originalKey = config.OPENAI_API_KEY;
      const originalAgent = config.AGENT_ENABLED;
      (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test-key";
      (config as Record<string, unknown>).AGENT_ENABLED = true;

      try {
        const app = buildApp();
        const createRes = await app.request("/api/v1/sessions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: "RAG Override" }),
        });
        const { data: session } = await createRes.json();

        const res = await app.request(`/api/v1/sessions/${session.id}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: "What is SEO?", mode: "rag" }),
        });
        expect(res.status).toBe(200);
        const body = await res.json();
        expect(body.data.mode).toBe("rag");
        expect(mockRagChat).toHaveBeenCalled();
        expect(mockAgentChat).not.toHaveBeenCalled();
      } finally {
        (config as Record<string, unknown>).OPENAI_API_KEY = originalKey;
        (config as Record<string, unknown>).AGENT_ENABLED = originalAgent;
      }
    });

    it("returns 400 for invalid mode value", async () => {
      const app = buildApp();
      const createRes = await app.request("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Invalid Mode" }),
      });
      const { data: session } = await createRes.json();

      const res = await app.request(`/api/v1/sessions/${session.id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "What is SEO?", mode: "invalid" }),
      });
      expect(res.status).toBe(400);
    });
  });

  describe("DELETE /api/v1/sessions/:id", () => {
    it("returns 400 for invalid session ID format", async () => {
      const app = buildApp();
      const res = await app.request("/api/v1/sessions/invalid-id", {
        method: "DELETE",
      });
      expect(res.status).toBe(400);
    });

    it("returns 404 for non-existent session with valid UUID", async () => {
      const app = buildApp();
      const res = await app.request(
        "/api/v1/sessions/00000000-0000-4000-8000-999999999999",
        { method: "DELETE" },
      );
      expect(res.status).toBe(404);
    });

    it("deletes a session", async () => {
      const app = buildApp();

      const createRes = await app.request("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Delete Me" }),
      });
      const { data: session } = await createRes.json();

      const res = await app.request(
        `/api/v1/sessions/${session.id}`,
        { method: "DELETE" },
      );
      expect(res.status).toBe(200);

      // Confirm it's gone
      const getRes = await app.request(
        `/api/v1/sessions/${session.id}`,
      );
      expect(getRes.status).toBe(404);
    });
  });
});
