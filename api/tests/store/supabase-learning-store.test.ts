/**
 * Tests for SupabaseLearningStore — feedback and miss recording.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../src/config.js", () => ({
  config: {
    SUPABASE_URL: "https://test.supabase.co",
    SUPABASE_ANON_KEY: "test-anon-key",
    SEO_API_KEY: "",
    CORS_ORIGINS: ["*"],
    RATE_LIMIT_DEFAULT: 1000,
    RATE_LIMIT_CHAT: 1000,
    RATE_LIMIT_GENERATE: 1000,
    PORT: 8002,
    CHAT_CONTEXT_K: 5,
  },
  paths: { outputDir: "/tmp" },
}));

vi.mock("../../src/store/supabase-client.js", () => ({
  hasSupabase: () => true,
  supabaseHeaders: () => ({
    apikey: "test",
    Authorization: "Bearer test",
    "Content-Type": "application/json",
  }),
  SUPABASE_TIMEOUT_MS: 10_000,
}));

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

import {
  recordFeedbackSupabase,
  recordMissSupabase,
} from "../../src/store/supabase-learning-store.js";

describe("SupabaseLearningStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("recordFeedbackSupabase", () => {
    it("posts feedback to Supabase", async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

      await recordFeedbackSupabase({
        query: "What is SEO?",
        qa_id: "abc123",
        feedback: "helpful",
        top_score: 0.95,
      });

      expect(mockFetch).toHaveBeenCalledWith(
        "https://test.supabase.co/rest/v1/learnings",
        expect.objectContaining({ method: "POST" }),
      );
      const body = JSON.parse(mockFetch.mock.calls[0]![1].body);
      expect(body.type).toBe("feedback");
      expect(body.query).toBe("What is SEO?");
      expect(body.qa_id).toBe("abc123");
      expect(body.top_score).toBe(0.95);
    });

    it("handles missing top_score", async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

      await recordFeedbackSupabase({
        query: "test",
        qa_id: "id1",
        feedback: "not helpful",
      });

      const body = JSON.parse(mockFetch.mock.calls[0]![1].body);
      expect(body.top_score).toBeNull();
    });

    it("does not throw on HTTP error", async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });
      // Should not throw — just logs a warning
      await expect(
        recordFeedbackSupabase({
          query: "test",
          qa_id: "id1",
          feedback: "bad",
        }),
      ).resolves.toBeUndefined();
    });
  });

  describe("recordMissSupabase", () => {
    it("posts miss to Supabase", async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });

      await recordMissSupabase({
        query: "Unknown topic",
        top_score: 0.15,
        context: "low relevance",
      });

      const body = JSON.parse(mockFetch.mock.calls[0]![1].body);
      expect(body.type).toBe("miss");
      expect(body.query).toBe("Unknown topic");
      expect(body.top_score).toBe(0.15);
    });

    it("does not throw on HTTP error", async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 400 });

      await expect(
        recordMissSupabase({
          query: "test",
          top_score: 0.1,
          context: "test",
        }),
      ).resolves.toBeUndefined();
    });
  });
});
