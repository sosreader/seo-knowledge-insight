/**
 * Tests for learning-store — factory pattern (vocus-warehouse vs local JSONL).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { appendFileSync, existsSync, mkdirSync } from "node:fs";

vi.mock("node:fs", () => ({
  appendFileSync: vi.fn(),
  existsSync: vi.fn(),
  mkdirSync: vi.fn(),
}));

// Default: PG disabled → local mode
vi.mock("../../src/config.js", () => ({
  config: {
    VW_DB_SECRET_FILE_RAG: "",
    SEO_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
    CHAT_CONTEXT_K: 5,
  },
  paths: { outputDir: "/tmp/test-output" },
}));

const _hasPg = vi.fn(() => false);
vi.mock("../../src/store/pg-client.js", () => ({
  hasPg: (...args: unknown[]) => _hasPg(...args),
}));

vi.mock("../../src/store/pg-learning-store.js", () => ({
  recordFeedbackPg: vi.fn(),
  recordMissPg: vi.fn(),
}));

import { recordFeedback, recordMiss } from "../../src/store/learning-store.js";
import { recordFeedbackPg, recordMissPg } from "../../src/store/pg-learning-store.js";

describe("learning-store (local mode)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("recordFeedback writes to JSONL file", () => {
    vi.mocked(existsSync).mockReturnValue(true);
    recordFeedback({
      query: "What is SEO?",
      qa_id: "id1",
      feedback: "helpful",
      top_score: 0.9,
    });

    expect(appendFileSync).toHaveBeenCalledOnce();
    const [, content] = vi.mocked(appendFileSync).mock.calls[0]!;
    const parsed = JSON.parse((content as string).trim());
    expect(parsed.type).toBe("feedback");
    expect(parsed.query).toBe("What is SEO?");
  });

  it("recordMiss writes to JSONL file", () => {
    vi.mocked(existsSync).mockReturnValue(true);
    recordMiss({
      query: "Unknown topic",
      top_score: 0.1,
      context: "no match",
    });

    expect(appendFileSync).toHaveBeenCalledOnce();
    const [, content] = vi.mocked(appendFileSync).mock.calls[0]!;
    const parsed = JSON.parse((content as string).trim());
    expect(parsed.type).toBe("miss");
  });

  it("creates directory when it does not exist", () => {
    vi.mocked(existsSync).mockReturnValue(false);
    recordFeedback({
      query: "test",
      qa_id: "id1",
      feedback: "ok",
    });
    expect(mkdirSync).toHaveBeenCalledWith(
      expect.any(String),
      { recursive: true },
    );
  });
});

describe("learning-store (PG mode)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    _hasPg.mockReturnValue(true);
    vi.mocked(recordFeedbackPg).mockResolvedValue(undefined as never);
    vi.mocked(recordMissPg).mockResolvedValue(undefined as never);
  });

  afterEach(() => {
    _hasPg.mockReturnValue(false);
  });

  it("recordFeedback delegates to vocus-warehouse", () => {
    recordFeedback({
      query: "What is SEO?",
      qa_id: "id1",
      feedback: "helpful",
      top_score: 0.9,
    });
    expect(recordFeedbackPg).toHaveBeenCalledOnce();
    expect(appendFileSync).not.toHaveBeenCalled();
  });

  it("recordMiss delegates to vocus-warehouse", () => {
    recordMiss({
      query: "Unknown",
      top_score: 0.1,
      context: "no match",
    });
    expect(recordMissPg).toHaveBeenCalledOnce();
    expect(appendFileSync).not.toHaveBeenCalled();
  });

  it("recordFeedback returns the row read back from vocus-warehouse", async () => {
    const stored = {
      id: "42",
      query: "test",
      qa_id: "id1",
      feedback: "ok",
      top_score: null,
      created_at: "2026-10-23T00:00:00.000Z",
    };
    vi.mocked(recordFeedbackPg).mockResolvedValue(stored);
    await expect(recordFeedback({ query: "test", qa_id: "id1", feedback: "ok" })).resolves.toEqual(stored);
  });

  it("recordFeedback propagates DB errors (route maps them to 503/504)", async () => {
    vi.mocked(recordFeedbackPg).mockRejectedValue(new Error("network"));
    await expect(recordFeedback({ query: "test", qa_id: "id1", feedback: "ok" })).rejects.toThrow("network");
  });

  it("recordMiss swallows DB errors gracefully", async () => {
    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.mocked(recordMissPg).mockRejectedValue(new Error("network"));
    recordMiss({ query: "test", top_score: 0.1, context: "x" });
    await new Promise((r) => setTimeout(r, 10));
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining("Failed to record miss"),
      expect.any(Error),
    );
    consoleSpy.mockRestore();
  });
});
