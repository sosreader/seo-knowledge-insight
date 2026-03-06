/**
 * Tests for SupabaseReportStore.
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

import { SupabaseReportStore } from "../../src/store/supabase-report-store.js";

const FAKE_ROW = {
  id: 1,
  date_key: "20260301",
  filename: "report_20260301.md",
  content: "# Report",
  size_bytes: 8,
  meta: { source: "test" },
  created_at: "2026-03-01T00:00:00Z",
};

describe("SupabaseReportStore", () => {
  let store: SupabaseReportStore;

  beforeEach(() => {
    vi.clearAllMocks();
    store = new SupabaseReportStore();
  });

  describe("list", () => {
    it("returns formatted report summaries", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([FAKE_ROW]);
      const reports = await store.list();
      expect(reports).toHaveLength(1);
      expect(reports[0]!.date).toBe("20260301");
      expect(reports[0]!.filename).toBe("report_20260301.md");
    });

    it("handles null meta", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([{ ...FAKE_ROW, meta: null }]);
      const reports = await store.list();
      expect(reports[0]!.meta).toBeUndefined();
    });
  });

  describe("getByDate", () => {
    it("returns report with content", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([FAKE_ROW]);
      const result = await store.getByDate("20260301");
      expect(result).toBeDefined();
      expect(result!.content).toBe("# Report");
      expect(result!.summary.date).toBe("20260301");
    });

    it("returns null when not found", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([]);
      const result = await store.getByDate("99999999");
      expect(result).toBeNull();
    });
  });

  describe("exists", () => {
    it("returns true when report exists", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([{ date_key: "20260301" }]);
      expect(await store.exists("20260301")).toBe(true);
    });

    it("returns false when not found", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([]);
      expect(await store.exists("99999999")).toBe(false);
    });
  });

  describe("save", () => {
    it("upserts report with correct data", async () => {
      mockSupabaseInsert.mockResolvedValueOnce([]);
      await store.save("20260301", "# Report Content", { source: "test" });
      expect(mockSupabaseInsert).toHaveBeenCalledWith(
        "reports",
        [expect.objectContaining({
          date_key: "20260301",
          filename: "report_20260301.md",
          content: "# Report Content",
        })],
        { upsert: true, onConflict: "date_key" },
      );
    });

    it("handles missing meta", async () => {
      mockSupabaseInsert.mockResolvedValueOnce([]);
      await store.save("20260301", "content");
      const insertedRow = mockSupabaseInsert.mock.calls[0]![1][0];
      expect(insertedRow.meta).toBeNull();
    });
  });

  describe("delete", () => {
    it("deletes existing report", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([{ date_key: "20260301" }]);
      mockSupabaseDelete.mockResolvedValueOnce(undefined);
      expect(await store.delete("20260301")).toBe(true);
    });

    it("returns false when report does not exist", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([]);
      expect(await store.delete("99999999")).toBe(false);
    });
  });
});
