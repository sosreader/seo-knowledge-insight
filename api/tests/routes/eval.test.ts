import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../src/store/qa-store.js", () => ({
  qaStore: { loaded: false, count: 0 },
}));

vi.mock("../../src/config.js", () => ({
  config: {
    SEO_API_KEY: "",
    OPENAI_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
    CHAT_CONTEXT_K: 5,
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

const mockExecQaTools = vi.fn();

vi.mock("../../src/services/pipeline-runner.js", () => ({
  execPython: vi.fn().mockResolvedValue({ success: true, output: "OK", duration_ms: 100 }),
  execQaTools: (...args: unknown[]) => mockExecQaTools(...args),
}));

import { Hono } from "hono";
import { evalRoute } from "../../src/routes/eval.js";

function buildApp() {
  const app = new Hono();
  app.route("/api/v1/eval", evalRoute);
  return app;
}

describe("POST /api/v1/eval/sample", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockExecQaTools.mockResolvedValue({
      success: true,
      output: JSON.stringify({ sample_size: 20, items: [] }),
      duration_ms: 100,
    });
  });

  it("calls eval-sample with default params", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/eval/sample", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.sample_size).toBe(20);
    expect(mockExecQaTools).toHaveBeenCalledWith("eval-sample", [
      "--size", "20", "--seed", "42",
    ]);
  });

  it("passes custom size and seed", async () => {
    const app = buildApp();
    await app.request("/api/v1/eval/sample", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ size: 10, seed: 123, with_golden: true }),
    });
    expect(mockExecQaTools).toHaveBeenCalledWith("eval-sample", [
      "--size", "10", "--seed", "123", "--with-golden",
    ]);
  });

  it("returns 500 on script failure", async () => {
    mockExecQaTools.mockResolvedValueOnce({
      success: false, output: "Error", duration_ms: 100,
    });
    const app = buildApp();
    const res = await app.request("/api/v1/eval/sample", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(500);
  });
});

describe("POST /api/v1/eval/retrieval", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockExecQaTools.mockResolvedValue({
      success: true,
      output: JSON.stringify({ search_engine: "keyword", avg_keyword_hit_rate: 0.74 }),
      duration_ms: 200,
    });
  });

  it("calls eval-retrieval-local with default params", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/eval/retrieval", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(200);
    expect(mockExecQaTools).toHaveBeenCalledWith("eval-retrieval-local", [
      "--top-k", "5",
    ]);
  });

  it("passes use_enriched flag", async () => {
    const app = buildApp();
    await app.request("/api/v1/eval/retrieval", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ top_k: 10, use_enriched: true }),
    });
    expect(mockExecQaTools).toHaveBeenCalledWith("eval-retrieval-local", [
      "--top-k", "10", "--use-enriched",
    ]);
  });
});

describe("GET /api/v1/eval/compare", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockExecQaTools.mockResolvedValue({
      success: true,
      output: JSON.stringify({ runs: [], baseline: {} }),
      duration_ms: 50,
    });
  });

  it("calls eval-compare --json", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/eval/compare");
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.runs).toEqual([]);
    expect(mockExecQaTools).toHaveBeenCalledWith("eval-compare", ["--json"]);
  });
});

describe("POST /api/v1/eval/save", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockExecQaTools.mockResolvedValue({
      success: true, output: "Saved", duration_ms: 100,
    });
  });

  it("saves eval with valid filename", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/eval/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: "eval-2026-03-04.json" }),
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.saved).toBe(true);
    expect(body.data.filename).toBe("eval-2026-03-04.json");
  });

  it("rejects path traversal with ..", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/eval/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: "../../etc/passwd" }),
    });
    expect(res.status).toBe(400);
  });

  it("rejects path with forward slash", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/eval/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: "subdir/file.json" }),
    });
    expect(res.status).toBe(400);
  });

  it("rejects non-.json filename", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/eval/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: "file.txt" }),
    });
    expect(res.status).toBe(400);
  });

  it("rejects empty input", async () => {
    const app = buildApp();
    const res = await app.request("/api/v1/eval/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input: "" }),
    });
    expect(res.status).toBe(400);
  });

  it("passes extraction_engine and update_baseline", async () => {
    const app = buildApp();
    await app.request("/api/v1/eval/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input: "result.json",
        extraction_engine: "gpt-5",
        update_baseline: true,
      }),
    });
    expect(mockExecQaTools).toHaveBeenCalledWith("eval-save", [
      "--input", "/tmp/output/evals/result.json",
      "--extraction-engine", "gpt-5",
      "--update-baseline",
    ]);
  });
});
