/**
 * Tests for supabase-client — REST API wrapper functions.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("../../src/config.js", () => ({
  config: {
    SUPABASE_URL: "https://test.supabase.co",
    SUPABASE_ANON_KEY: "test-anon-key",
    SUPABASE_SERVICE_KEY: "test-service-key",
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

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

import {
  hasSupabase,
  supabaseHeaders,
  supabaseRpc,
  supabaseSelect,
  supabaseInsert,
  supabaseDelete,
  supabaseCount,
  SUPABASE_TIMEOUT_MS,
} from "../../src/store/supabase-client.js";

describe("supabase-client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("hasSupabase", () => {
    it("returns true when URL and key are set", () => {
      expect(hasSupabase()).toBe(true);
    });
  });

  describe("supabaseHeaders", () => {
    it("returns headers with default anon key", () => {
      const headers = supabaseHeaders();
      expect(headers.apikey).toBe("test-anon-key");
      expect(headers.Authorization).toBe("Bearer test-anon-key");
      expect(headers["Content-Type"]).toBe("application/json");
    });

    it("accepts custom key", () => {
      const headers = supabaseHeaders("custom-key");
      expect(headers.apikey).toBe("custom-key");
    });
  });

  describe("SUPABASE_TIMEOUT_MS", () => {
    it("is 10 seconds", () => {
      expect(SUPABASE_TIMEOUT_MS).toBe(10_000);
    });
  });

  describe("supabaseRpc", () => {
    it("calls RPC endpoint and returns data", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [{ id: "1" }],
      });

      const result = await supabaseRpc("match_qa_items", { match_count: 5 });
      expect(result).toEqual([{ id: "1" }]);
      expect(mockFetch).toHaveBeenCalledWith(
        "https://test.supabase.co/rest/v1/rpc/match_qa_items",
        expect.objectContaining({ method: "POST" }),
      );
    });

    it("throws on HTTP error", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => "rpc body",
      });
      await expect(supabaseRpc("bad_fn", {})).rejects.toThrow(
        "Supabase RPC bad_fn failed (500): rpc body",
      );
    });
  });

  describe("supabaseSelect", () => {
    it("queries table and returns data", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [{ id: "1", question: "Q" }],
      });

      const result = await supabaseSelect("qa_items", "?select=id,question");
      expect(result).toEqual([{ id: "1", question: "Q" }]);
      expect(mockFetch).toHaveBeenCalledWith(
        "https://test.supabase.co/rest/v1/qa_items?select=id,question",
        expect.objectContaining({ method: "GET" }),
      );
    });

    it("throws on HTTP error", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => "select body",
      });
      await expect(supabaseSelect("nonexistent")).rejects.toThrow(
        "Supabase SELECT nonexistent failed (404): select body",
      );
    });
  });

  describe("supabaseInsert", () => {
    it("inserts rows and returns representation", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [{ id: "new" }],
      });

      const result = await supabaseInsert("qa_items", [{ question: "Q" }]);
      expect(result).toEqual([{ id: "new" }]);
    });

    it("supports upsert with onConflict", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

      await supabaseInsert("qa_items", [{ id: "1" }], {
        upsert: true,
        onConflict: "id",
      });

      const headers = mockFetch.mock.calls[0]![1].headers;
      expect(headers.Prefer).toContain("resolution=merge-duplicates");
      expect(headers.Prefer).toContain("on_conflict=id");
    });

    it("throws on HTTP error with body", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 409,
        text: async () => "conflict",
      });

      await expect(supabaseInsert("qa_items", [{ id: "dup" }])).rejects.toThrow(
        "Supabase INSERT qa_items failed (409): conflict",
      );
    });
  });

  describe("supabaseDelete", () => {
    it("deletes rows", async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      await supabaseDelete("qa_items", "?id=eq.123");
      expect(mockFetch).toHaveBeenCalledWith(
        "https://test.supabase.co/rest/v1/qa_items?id=eq.123",
        expect.objectContaining({ method: "DELETE" }),
      );
    });

    it("throws on HTTP error", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => "server error",
      });

      await expect(supabaseDelete("qa_items", "?id=eq.1")).rejects.toThrow(
        "Supabase DELETE qa_items failed (500): server error",
      );
    });
  });

  describe("supabaseCount", () => {
    it("returns count from content-range header", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-range": "0-9/42" }),
      });

      expect(await supabaseCount("qa_items")).toBe(42);
    });

    it("returns -1 on HTTP error", async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      expect(await supabaseCount("qa_items")).toBe(-1);
    });

    it("returns 0 when content-range header is missing", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({}),
      });
      // Default fallback "*/0" → total = "0" → 0
      expect(await supabaseCount("qa_items")).toBe(0);
    });
  });
});
