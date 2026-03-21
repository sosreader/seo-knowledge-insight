/**
 * Tests for SupabaseMeetingPrepStore.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

const mockSupabaseSelect = vi.fn();
const mockSupabaseInsert = vi.fn();
const mockSupabaseDelete = vi.fn();

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
  supabaseSelect: (...args: unknown[]) => mockSupabaseSelect(...args),
  supabaseInsert: (...args: unknown[]) => mockSupabaseInsert(...args),
  supabaseDelete: (...args: unknown[]) => mockSupabaseDelete(...args),
}));

import { SupabaseMeetingPrepStore } from "../../src/store/supabase-meeting-prep-store.js";

const FAKE_META = {
  date: "2026-03-21",
  scores: {
    eeat: { experience: 3, expertise: 3, authoritativeness: 2, trustworthiness: 3 },
    maturity: { strategy: "L2", process: "L2", keywords: "L3", metrics: "L2" },
  },
  alert_down_count: 15,
  question_count: 16,
  generation_mode: "claude-code",
};

const FAKE_ROW = {
  date_key: "20260321_ecc2ca31",
  filename: "meeting_prep_20260321_ecc2ca31.md",
  content: "# Meeting Prep Report",
  size_bytes: 21,
  meta: FAKE_META,
  created_at: "2026-03-21T12:00:00Z",
};

describe("SupabaseMeetingPrepStore", () => {
  let store: SupabaseMeetingPrepStore;

  beforeEach(() => {
    vi.clearAllMocks();
    store = new SupabaseMeetingPrepStore();
  });

  describe("list", () => {
    it("returns formatted meeting-prep summaries", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([FAKE_ROW]);
      const items = await store.list();
      expect(items).toHaveLength(1);
      expect(items[0]!.date).toBe("20260321_ecc2ca31");
      expect(items[0]!.filename).toBe("meeting_prep_20260321_ecc2ca31.md");
      expect(items[0]!.meta).toEqual(FAKE_META);
    });

    it("handles empty meta object", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([{ ...FAKE_ROW, meta: {} }]);
      const items = await store.list();
      expect(items[0]!.meta).toEqual({});
    });

    it("returns empty array when no reports", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([]);
      const items = await store.list();
      expect(items).toHaveLength(0);
    });
  });

  describe("getByDate", () => {
    it("returns report with content on exact match", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([FAKE_ROW]);
      const result = await store.getByDate("20260321_ecc2ca31");
      expect(result).toBeDefined();
      expect(result!.content).toBe("# Meeting Prep Report");
      expect(result!.summary.date).toBe("20260321_ecc2ca31");
    });

    it("falls back to fuzzy match when exact fails", async () => {
      // First call (exact match) returns empty
      mockSupabaseSelect.mockResolvedValueOnce([]);
      // Second call (fuzzy match with LIKE) returns result
      mockSupabaseSelect.mockResolvedValueOnce([FAKE_ROW]);
      const result = await store.getByDate("20260321");
      expect(result).toBeDefined();
      expect(result!.summary.date).toBe("20260321_ecc2ca31");
      // Verify fuzzy query uses LIKE
      expect(mockSupabaseSelect.mock.calls[1]![1]).toContain("like.");
    });

    it("returns null when not found (exact + fuzzy)", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([]);
      mockSupabaseSelect.mockResolvedValueOnce([]);
      const result = await store.getByDate("99999999");
      expect(result).toBeNull();
    });
  });

  describe("exists", () => {
    it("returns true when report exists", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([{ date_key: "20260321_ecc2ca31" }]);
      expect(await store.exists("20260321_ecc2ca31")).toBe(true);
    });

    it("returns false when not found", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([]);
      expect(await store.exists("99999999")).toBe(false);
    });
  });

  describe("save", () => {
    it("upserts with correct data", async () => {
      mockSupabaseInsert.mockResolvedValueOnce([]);
      await store.save("20260321_ecc2ca31", "meeting_prep_20260321_ecc2ca31.md", "# Content", FAKE_META);
      expect(mockSupabaseInsert).toHaveBeenCalledWith(
        "meeting_prep",
        [expect.objectContaining({
          date_key: "20260321_ecc2ca31",
          filename: "meeting_prep_20260321_ecc2ca31.md",
          content: "# Content",
          meta: FAKE_META,
        })],
        { upsert: true, onConflict: "date_key" },
      );
    });

    it("defaults meta to empty object when not provided", async () => {
      mockSupabaseInsert.mockResolvedValueOnce([]);
      await store.save("20260321_ecc2ca31", "file.md", "content");
      const insertedRow = mockSupabaseInsert.mock.calls[0]![1][0];
      expect(insertedRow.meta).toEqual({});
    });

    it("calculates size_bytes from content", async () => {
      mockSupabaseInsert.mockResolvedValueOnce([]);
      const content = "Hello 世界"; // 11 bytes in UTF-8
      await store.save("20260321", "file.md", content);
      const insertedRow = mockSupabaseInsert.mock.calls[0]![1][0];
      expect(insertedRow.size_bytes).toBe(Buffer.byteLength(content, "utf-8"));
    });
  });

  describe("delete", () => {
    it("deletes existing report", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([{ date_key: "20260321_ecc2ca31" }]);
      mockSupabaseDelete.mockResolvedValueOnce(undefined);
      expect(await store.delete("20260321_ecc2ca31")).toBe(true);
      expect(mockSupabaseDelete).toHaveBeenCalledWith(
        "meeting_prep",
        expect.stringContaining("20260321_ecc2ca31"),
      );
    });

    it("returns false when report does not exist", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([]);
      expect(await store.delete("99999999")).toBe(false);
      expect(mockSupabaseDelete).not.toHaveBeenCalled();
    });
  });

  describe("listWithMeta", () => {
    it("returns maturity data points in date-ascending order", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([
        { ...FAKE_ROW, date_key: "20260309_abc12345" },
        { ...FAKE_ROW, date_key: "20260321_ecc2ca31" },
      ]);
      const points = await store.listWithMeta();
      expect(points).toHaveLength(2);
      expect(points[0]!.date).toBe("2026-03-09");
      expect(points[1]!.date).toBe("2026-03-21");
      expect(points[0]!.maturity.strategy).toBe("L2");
      expect(points[0]!.eeat.experience).toBe(3);
    });

    it("filters out rows with null meta", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([
        FAKE_ROW,
        { ...FAKE_ROW, date_key: "20260315_00000000", meta: null },
      ]);
      const points = await store.listWithMeta();
      expect(points).toHaveLength(1);
    });

    it("returns empty array when no data", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([]);
      const points = await store.listWithMeta();
      expect(points).toHaveLength(0);
    });
  });
});
