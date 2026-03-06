import { describe, it, expect, vi } from "vitest";

vi.mock("../src/config.js", () => ({
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
    metricsSnapshotsDir: "/tmp/output/metrics_snapshots",
    synonymCustomJsonPath: "/tmp/output/synonyms_custom.json",
  },
}));

vi.mock("../src/utils/observability.js", () => ({
  initLaminar: vi.fn(),
  flushLaminar: vi.fn(),
  observe: (name: string, fn: Function) => fn,
}));

vi.mock("../src/store/supabase-client.js", () => ({
  hasSupabase: () => false,
  getSupabaseClient: () => null,
}));

import app from "../src/index.js";
import { buildOpenAPISpec } from "../src/openapi.js";

describe("OpenAPI Spec", () => {
  it("GET /openapi.json returns valid OpenAPI 3.1 spec", async () => {
    const res = await app.request("/openapi.json");
    expect(res.status).toBe(200);

    const spec = await res.json();
    expect(spec.openapi).toBe("3.1.0");
    expect(spec.info.title).toBe("SEO Knowledge Insight API");
    expect(spec.info.version).toBeDefined();
  });

  it("spec contains all expected paths", () => {
    const spec = buildOpenAPISpec();
    const pathKeys = Object.keys(spec.paths as Record<string, unknown>);

    // 31 unique path patterns covering 34 HTTP operations
    expect(pathKeys.length).toBe(31);

    // Verify key paths exist
    const expected = [
      "/health",
      "/api/v1/qa",
      "/api/v1/qa/categories",
      "/api/v1/qa/collections",
      "/api/v1/qa/{item_id}",
      "/api/v1/search",
      "/api/v1/chat",
      "/api/v1/reports",
      "/api/v1/reports/{date}",
      "/api/v1/reports/generate",
      "/api/v1/sessions",
      "/api/v1/sessions/{session_id}",
      "/api/v1/sessions/{session_id}/messages",
      "/api/v1/feedback",
      "/api/v1/synonyms",
      "/api/v1/synonyms/{term}",
      "/api/v1/pipeline/status",
      "/api/v1/pipeline/meetings",
      "/api/v1/pipeline/source-docs",
      "/api/v1/pipeline/unprocessed",
      "/api/v1/pipeline/logs",
      "/api/v1/pipeline/fetch",
      "/api/v1/pipeline/fetch-articles",
      "/api/v1/pipeline/extract-qa",
      "/api/v1/pipeline/dedupe-classify",
      "/api/v1/pipeline/metrics",
      "/api/v1/pipeline/metrics/save",
      "/api/v1/pipeline/metrics/snapshots",
      "/api/v1/pipeline/metrics/snapshots/{id}",
    ];

    for (const path of expected) {
      expect(pathKeys).toContain(path);
    }
  });

  it("spec has correct security scheme", () => {
    const spec = buildOpenAPISpec();
    const components = spec.components as Record<string, unknown>;
    const securitySchemes = components.securitySchemes as Record<string, Record<string, unknown>>;

    expect(securitySchemes.apiKey).toBeDefined();
    expect(securitySchemes.apiKey.type).toBe("apiKey");
    expect(securitySchemes.apiKey.in).toBe("header");
    expect(securitySchemes.apiKey.name).toBe("X-API-Key");
  });

  it("spec has all 9 tags", () => {
    const spec = buildOpenAPISpec();
    const tags = spec.tags as Array<{ name: string }>;

    expect(tags).toHaveLength(9);
    const tagNames = tags.map((t) => t.name);
    expect(tagNames).toEqual([
      "Health", "QA", "Search", "Chat", "Reports",
      "Sessions", "Feedback", "Synonyms", "Pipeline",
    ]);
  });

  it("health endpoint has no security requirement", () => {
    const spec = buildOpenAPISpec();
    const pathsObj = spec.paths as Record<string, Record<string, Record<string, unknown>>>;
    const healthGet = pathsObj["/health"]?.get;

    expect(healthGet?.security).toEqual([]);
  });

  it("spec schemas reference correctly", () => {
    const spec = buildOpenAPISpec();
    const components = spec.components as Record<string, unknown>;
    const schemaNames = Object.keys(components.schemas as Record<string, unknown>);

    expect(schemaNames).toContain("QAItem");
    expect(schemaNames).toContain("ChatRequest");
    expect(schemaNames).toContain("ChatResponse");
    expect(schemaNames).toContain("SourceItem");
    expect(schemaNames).toContain("SessionDetail");
    expect(schemaNames).toContain("ReportSummary");
    expect(schemaNames).toContain("SynonymEntry");
    expect(schemaNames).toContain("PipelineRunResult");
  });
});

describe("Scalar Docs", () => {
  it("GET /docs returns HTML page", async () => {
    const res = await app.request("/docs");
    expect(res.status).toBe(200);

    const contentType = res.headers.get("content-type") || "";
    expect(contentType).toContain("text/html");
  });
});
