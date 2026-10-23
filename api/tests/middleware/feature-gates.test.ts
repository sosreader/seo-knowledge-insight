/**
 * 501 類 gate：llm_disabled（線上無 LLM）、run_locally（rag-api 不執行 pipeline／不讀本機檔案）。
 * 回應沿用 { data, error, meta } 信封，多一個給人看的 message。
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Hono } from "hono";

const mockConfig: Record<string, unknown> = {};
vi.mock("../../src/config.js", () => ({ config: mockConfig }));

const { requireLlm, runLocallyInRagApi } = await import("../../src/middleware/feature-gates.js");
const { errorHandler } = await import("../../src/middleware/error-handler.js");
const { FeatureUnavailableError, FEATURE_MESSAGES, featureUnavailableBody, isFeatureUnavailableError } =
  await import("../../src/utils/feature-errors.js");

function buildApp(): Hono {
  const app = new Hono();
  app.onError(errorHandler);
  app.use("/llm", requireLlm);
  app.get("/llm", (c) => c.json({ ok: true }));
  app.use("/local", runLocallyInRagApi);
  app.get("/local", (c) => c.json({ ok: true }));
  app.get("/throw", () => {
    throw new FeatureUnavailableError("llm_disabled");
  });
  return app;
}

function setConfig(values: Record<string, unknown>): void {
  for (const k of Object.keys(mockConfig)) delete mockConfig[k];
  Object.assign(mockConfig, values);
}

describe("feature gates", () => {
  beforeEach(() => setConfig({}));

  it("requireLlm → 501 llm_disabled with message when no key and no base URL", async () => {
    const res = await buildApp().request("/llm");
    expect(res.status).toBe(501);
    const body = (await res.json()) as Record<string, unknown>;
    expect(body.error).toBe("llm_disabled");
    expect(body.message).toBe("線上未啟用 LLM，請在本機模式執行");
    expect(body.data).toBeNull();
  });

  it("requireLlm passes through when LLM_BASE_URL is set", async () => {
    setConfig({ LLM_BASE_URL: "http://localhost:11434/v1" });
    const res = await buildApp().request("/llm");
    expect(res.status).toBe(200);
  });

  it("runLocallyInRagApi → 501 run_locally in PG mode", async () => {
    setConfig({ VW_DB_SECRET_FILE_RAG: "/var/run/secrets/db-rag" });
    const res = await buildApp().request("/local");
    expect(res.status).toBe(501);
    const body = (await res.json()) as Record<string, unknown>;
    expect(body.error).toBe("run_locally");
    expect(body.message).toBe("此流程在本機執行，請用 make pipeline");
  });

  it("runLocallyInRagApi passes through in local file mode", async () => {
    const res = await buildApp().request("/local");
    expect(res.status).toBe(200);
  });

  it("error handler maps a thrown FeatureUnavailableError to 501", async () => {
    const res = await buildApp().request("/throw");
    expect(res.status).toBe(501);
    const body = (await res.json()) as Record<string, unknown>;
    expect(body.error).toBe("llm_disabled");
    expect(body.message).toBe(FEATURE_MESSAGES.llm_disabled);
  });

  it("helpers expose code, status and body shape", () => {
    const err = new FeatureUnavailableError("run_locally");
    expect(isFeatureUnavailableError(err)).toBe(true);
    expect(isFeatureUnavailableError(new Error("x"))).toBe(false);
    expect(err.status).toBe(501);
    expect(err.message).toContain("run_locally");
    const body = featureUnavailableBody("run_locally");
    expect(body).toMatchObject({ data: null, error: "run_locally", message: FEATURE_MESSAGES.run_locally });
    expect(body.meta.request_id).toBeTruthy();
  });
});
