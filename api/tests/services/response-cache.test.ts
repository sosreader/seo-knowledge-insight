import { describe, it, expect, vi, beforeEach } from "vitest";
import { normalizeQuery, hashQuery, lookupCache, saveCache } from "../../src/services/response-cache.js";

// Mock supabase-client
vi.mock("../../src/store/supabase-client.js", () => ({
  hasSupabase: vi.fn(() => true),
  supabaseSelect: vi.fn(),
  supabaseInsert: vi.fn(),
}));

// Mock laminar-scoring
vi.mock("../../src/utils/laminar-scoring.js", () => ({
  scoreEvent: vi.fn(),
}));

import { hasSupabase, supabaseSelect, supabaseInsert } from "../../src/store/supabase-client.js";

const mockHasSupabase = vi.mocked(hasSupabase);
const mockSelect = vi.mocked(supabaseSelect);
const mockInsert = vi.mocked(supabaseInsert);

beforeEach(() => {
  vi.clearAllMocks();
  mockHasSupabase.mockReturnValue(true);
});

describe("normalizeQuery", () => {
  it("lowercases and trims", () => {
    expect(normalizeQuery("  Hello World  ")).toBe("hello world");
  });

  it("collapses multiple spaces", () => {
    expect(normalizeQuery("foo   bar")).toBe("foo bar");
  });

  it("handles CJK characters", () => {
    expect(normalizeQuery("  SEO 優化技巧  ")).toBe("seo 優化技巧");
  });
});

describe("hashQuery", () => {
  it("returns a 64-char hex string", () => {
    const hash = hashQuery("hello world");
    expect(hash).toMatch(/^[0-9a-f]{64}$/);
  });

  it("is deterministic", () => {
    expect(hashQuery("test")).toBe(hashQuery("test"));
  });

  it("differs for different inputs", () => {
    expect(hashQuery("a")).not.toBe(hashQuery("b"));
  });
});

describe("lookupCache", () => {
  it("returns null when Supabase is not configured", async () => {
    mockHasSupabase.mockReturnValue(false);
    const result = await lookupCache("abc123");
    expect(result).toBeNull();
    expect(mockSelect).not.toHaveBeenCalled();
  });

  it("returns cached response on hit", async () => {
    const cachedResponse = { answer: "cached answer", sources: [] };
    mockSelect.mockResolvedValue([{ response: cachedResponse }]);

    const result = await lookupCache("abc123");
    expect(result).toEqual(cachedResponse);
    expect(mockSelect).toHaveBeenCalledWith(
      "response_cache",
      expect.stringContaining("query_hash=eq.abc123"),
    );
  });

  it("returns null on cache miss", async () => {
    mockSelect.mockResolvedValue([]);
    const result = await lookupCache("missing");
    expect(result).toBeNull();
  });

  it("returns null on error (no crash)", async () => {
    mockSelect.mockRejectedValue(new Error("network error"));
    const result = await lookupCache("error");
    expect(result).toBeNull();
  });
});

describe("saveCache", () => {
  it("skips when Supabase is not configured", async () => {
    mockHasSupabase.mockReturnValue(false);
    await saveCache("test query", "hash123", { answer: "test" });
    expect(mockInsert).not.toHaveBeenCalled();
  });

  it("upserts with correct parameters", async () => {
    mockInsert.mockResolvedValue([]);
    await saveCache("test query", "hash123", { answer: "test" }, 4);

    expect(mockInsert).toHaveBeenCalledWith(
      "response_cache",
      [expect.objectContaining({
        query_hash: "hash123",
        query_text: "test query",
        response: { answer: "test" },
        hit_count: 0,
      })],
      { upsert: true, onConflict: "query_hash" },
    );

    // Check expires_at is approximately 4 hours from now
    const row = mockInsert.mock.calls[0][1][0] as Record<string, unknown>;
    const expiresAt = new Date(row.expires_at as string);
    const expectedMs = Date.now() + 4 * 60 * 60 * 1000;
    expect(Math.abs(expiresAt.getTime() - expectedMs)).toBeLessThan(5000);
  });

  it("does not throw on error", async () => {
    mockInsert.mockRejectedValue(new Error("write failed"));
    await expect(saveCache("q", "h", { a: 1 })).resolves.toBeUndefined();
  });
});
