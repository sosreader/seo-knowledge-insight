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
      id: "abc123",
      question: "What is SEO?",
      answer: "SEO is Search Engine Optimization",
      keywords: ["SEO"],
      category: "basics",
      source_title: "Meeting 1",
      source_date: "2024-05-02",
      source_type: "meeting",
      source_collection: "seo-meetings",
      source_url: "",
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
      id: "abc123",
      question: "What is SEO?",
      category: "basics",
      source_title: "Meeting 1",
      source_date: "2024-05-02",
      source_type: "meeting",
      source_collection: "seo-meetings",
      source_url: "",
      score: 0.85,
    },
  ],
  mode: "full",
  metadata: {
    model: "gpt-5.2",
    provider: "openai",
    mode: "full",
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
  answer: "Agent mode answer",
  sources: [{ id: "abc123", question: "What is SEO?", category: "basics", source_title: "Meeting 1", source_date: "2024-05-02", source_type: "meeting", source_collection: "seo-meetings", source_url: "", score: 0.85 }],
  mode: "agent",
  metadata: { model: "gpt-5.2", provider: "openai", mode: "agent", input_tokens: 200, output_tokens: 100, total_tokens: 300, duration_ms: 2000, retrieval_count: 1, reranker_used: false, tool_calls_count: 2, agent_turns: 2, tool_calls: [] },
});

vi.mock("../../src/agent/agent-loop.js", () => ({
  agentChat: (...args: unknown[]) => mockAgentChat(...args),
  agentChatObserved: (...args: unknown[]) => mockAgentChat(...args),
}));

vi.mock("../../src/agent/agent-deps.js", () => ({
  createAgentDeps: () => ({}),
}));

import { Hono } from "hono";
import { chatRoute } from "../../src/routes/chat.js";
import { config } from "../../src/config.js";

function buildApp() {
  const app = new Hono();
  app.route("/api/v1/chat", chatRoute);
  return app;
}

describe("POST /api/v1/chat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns context-only mode when no OpenAI key", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "What is SEO?" }),
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.mode).toBe("context-only");
    expect(body.data.answer).toBeNull();
    expect(body.data.sources).toHaveLength(1);
    expect(body.data.sources[0].question).toBe("What is SEO?");
    expect(mockKeywordSearch).toHaveBeenCalledWith("What is SEO?", 5);
  });

  it("returns full mode when OpenAI key is set", async () => {
    const original = config.OPENAI_API_KEY;
    (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test-key";

    try {
      const app = buildApp();
      const res = await app.request("/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "What is SEO?" }),
      });
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.data.mode).toBe("full");
      expect(body.data.answer).toBe("SEO is important for visibility");
      expect(mockRagChat).toHaveBeenCalled();
    } finally {
      (config as Record<string, unknown>).OPENAI_API_KEY = original;
    }
  });

  it("returns 400 for empty message", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "" }),
    });
    expect(res.status).toBe(400);
  });

  it("returns 400 for missing message field", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(400);
  });

  it("context-only mode includes score rounded to 4 decimal places", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "SEO basics" }),
    });
    const body = await res.json();
    expect(body.data.sources[0].score).toBe(0.5);
  });

  it("falls back to context-only on OpenAI 429 error", async () => {
    const original = config.OPENAI_API_KEY;
    (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test-key";
    mockRagChat.mockRejectedValueOnce(Object.assign(new Error("rate limited"), { status: 429 }));

    try {
      const app = buildApp();
      const res = await app.request("/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "What is SEO?" }),
      });
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.data.mode).toBe("context-only");
      expect(body.data.answer).toBeNull();
    } finally {
      (config as Record<string, unknown>).OPENAI_API_KEY = original;
    }
  });

  it("falls back to context-only on OpenAI 401 error", async () => {
    const original = config.OPENAI_API_KEY;
    (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test-key";
    mockRagChat.mockRejectedValueOnce(Object.assign(new Error("unauthorized"), { status: 401 }));

    try {
      const app = buildApp();
      const res = await app.request("/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "test" }),
      });
      const body = await res.json();
      expect(body.data.mode).toBe("context-only");
    } finally {
      (config as Record<string, unknown>).OPENAI_API_KEY = original;
    }
  });

  it("context-only mode includes metadata with provider and retrieval_count", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "What is SEO?" }),
    });
    const body = await res.json();
    expect(body.data.metadata).toBeDefined();
    expect(body.data.metadata.provider).toBe("local");
    expect(body.data.metadata.mode).toBe("context-only");
    expect(body.data.metadata.retrieval_count).toBe(1);
    expect(typeof body.data.metadata.duration_ms).toBe("number");
  });

  it("full mode includes metadata with model and tokens", async () => {
    const original = config.OPENAI_API_KEY;
    (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test-key";

    try {
      const app = buildApp();
      const res = await app.request("/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "What is SEO?" }),
      });
      const body = await res.json();
      expect(body.data.metadata).toBeDefined();
      expect(body.data.metadata.model).toBe("gpt-5.2");
      expect(body.data.metadata.provider).toBe("openai");
      expect(body.data.metadata.input_tokens).toBe(150);
      expect(body.data.metadata.output_tokens).toBe(80);
      expect(body.data.metadata.total_tokens).toBe(230);
      expect(body.data.metadata.duration_ms).toBe(1200);
      expect(body.data.metadata.retrieval_count).toBe(1);
      expect(body.data.metadata.reranker_used).toBe(false);
    } finally {
      (config as Record<string, unknown>).OPENAI_API_KEY = original;
    }
  });

  it("sources include source_type, source_collection, source_url", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "What is SEO?" }),
    });
    const body = await res.json();
    const source = body.data.sources[0];
    expect(source.source_type).toBe("meeting");
    expect(source.source_collection).toBe("seo-meetings");
    expect(source).toHaveProperty("source_url");
  });

  it("returns agent mode when AGENT_ENABLED is true", async () => {
    const originalKey = config.OPENAI_API_KEY;
    const originalAgent = config.AGENT_ENABLED;
    (config as Record<string, unknown>).OPENAI_API_KEY = "sk-test-key";
    (config as Record<string, unknown>).AGENT_ENABLED = true;

    try {
      const app = buildApp();
      const res = await app.request("/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "What is SEO?" }),
      });
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.data.mode).toBe("agent");
      expect(body.data.answer).toBe("Agent mode answer");
      expect(body.data.tool_calls_count).toBe(2);
      expect(mockAgentChat).toHaveBeenCalled();
      expect(mockRagChat).not.toHaveBeenCalled();
    } finally {
      (config as Record<string, unknown>).OPENAI_API_KEY = originalKey;
      (config as Record<string, unknown>).AGENT_ENABLED = originalAgent;
    }
  });
});
