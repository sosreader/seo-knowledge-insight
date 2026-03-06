/**
 * Tests for learning-store — factory pattern (Supabase vs local JSONL).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { appendFileSync, existsSync, mkdirSync } from "node:fs";

vi.mock("node:fs", () => ({
  appendFileSync: vi.fn(),
  existsSync: vi.fn(),
  mkdirSync: vi.fn(),
}));

// Default: Supabase disabled → local mode
vi.mock("../../src/config.js", () => ({
  config: {
    SUPABASE_URL: "",
    SUPABASE_ANON_KEY: "",
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

const _hasSupabase = vi.fn(() => false);
vi.mock("../../src/store/supabase-client.js", () => ({
  hasSupabase: (...args: unknown[]) => _hasSupabase(...args),
}));

vi.mock("../../src/store/supabase-learning-store.js", () => ({
  recordFeedbackSupabase: vi.fn(),
  recordMissSupabase: vi.fn(),
}));

import { recordFeedback, recordMiss } from "../../src/store/learning-store.js";
import { recordFeedbackSupabase, recordMissSupabase } from "../../src/store/supabase-learning-store.js";

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

describe("learning-store (supabase mode)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    _hasSupabase.mockReturnValue(true);
    vi.mocked(recordFeedbackSupabase).mockResolvedValue(undefined as never);
    vi.mocked(recordMissSupabase).mockResolvedValue(undefined as never);
  });

  afterEach(() => {
    _hasSupabase.mockReturnValue(false);
  });

  it("recordFeedback delegates to Supabase", () => {
    recordFeedback({
      query: "What is SEO?",
      qa_id: "id1",
      feedback: "helpful",
      top_score: 0.9,
    });
    expect(recordFeedbackSupabase).toHaveBeenCalledOnce();
    expect(appendFileSync).not.toHaveBeenCalled();
  });

  it("recordMiss delegates to Supabase", () => {
    recordMiss({
      query: "Unknown",
      top_score: 0.1,
      context: "no match",
    });
    expect(recordMissSupabase).toHaveBeenCalledOnce();
    expect(appendFileSync).not.toHaveBeenCalled();
  });

  it("recordFeedback swallows Supabase errors gracefully", async () => {
    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.mocked(recordFeedbackSupabase).mockRejectedValue(new Error("network"));
    recordFeedback({ query: "test", qa_id: "id1", feedback: "ok" });
    // Wait for the .catch() to fire
    await new Promise((r) => setTimeout(r, 10));
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining("Failed to record feedback"),
      expect.any(Error),
    );
    consoleSpy.mockRestore();
  });

  it("recordMiss swallows Supabase errors gracefully", async () => {
    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.mocked(recordMissSupabase).mockRejectedValue(new Error("network"));
    recordMiss({ query: "test", top_score: 0.1, context: "x" });
    await new Promise((r) => setTimeout(r, 10));
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining("Failed to record miss"),
      expect.any(Error),
    );
    consoleSpy.mockRestore();
  });
});
