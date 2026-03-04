import { describe, it, expect, vi, beforeAll } from "vitest";
import { Hono } from "hono";

// Mock learning store
vi.mock("../../src/store/learning-store.js", () => ({
  recordFeedback: vi.fn(),
  recordMiss: vi.fn(),
}));

vi.mock("../../src/store/qa-store.js", () => ({
  qaStore: { loaded: false, count: 0 },
}));

vi.mock("../../src/config.js", () => ({
  config: {
    SEO_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
  },
  paths: { outputDir: "/tmp", sessionsDir: "/tmp/sessions" },
}));

let app: Hono;

beforeAll(async () => {
  const { app: mainApp } = await import("../../src/index.js");
  app = mainApp;
});

describe("POST /api/v1/feedback", () => {
  it("returns 200 on valid feedback", async () => {
    const res = await app.request("/api/v1/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: "how to improve SEO",
        qa_id: "a1b2c3d4e5f67890",
        feedback: "helpful",
        top_score: 0.85,
      }),
    });
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.data.recorded).toBe(true);
    expect(body.data.feedback).toBe("helpful");
  });

  it("returns 400 on invalid qa_id", async () => {
    const res = await app.request("/api/v1/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: "test",
        qa_id: "invalid",
        feedback: "helpful",
      }),
    });
    expect(res.status).toBe(400);
  });

  it("returns 400 on invalid feedback type", async () => {
    const res = await app.request("/api/v1/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: "test",
        qa_id: "a1b2c3d4e5f67890",
        feedback: "invalid_type",
      }),
    });
    expect(res.status).toBe(400);
  });
});
