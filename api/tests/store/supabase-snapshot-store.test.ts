/**
 * Tests for SupabaseSnapshotStore.
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

import { SupabaseSnapshotStore } from "../../src/store/supabase-snapshot-store.js";

const FAKE_SNAPSHOT = {
  id: "snap-001",
  label: "Weekly Snapshot",
  source: "Google Sheets",
  tab: "Overview",
  weeks: 4,
  metrics: { impressions: 1000, clicks: 50 },
  created_at: "2026-03-01T00:00:00Z",
};

describe("SupabaseSnapshotStore", () => {
  let store: SupabaseSnapshotStore;

  beforeEach(() => {
    vi.clearAllMocks();
    store = new SupabaseSnapshotStore();
  });

  describe("list", () => {
    it("returns snapshot metadata", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([FAKE_SNAPSHOT]);
      const items = await store.list();
      expect(items).toHaveLength(1);
      expect(items[0]!.id).toBe("snap-001");
      expect(items[0]!.label).toBe("Weekly Snapshot");
    });

    it("returns empty array when no snapshots", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([]);
      expect(await store.list()).toEqual([]);
    });
  });

  describe("getById", () => {
    it("returns snapshot with metrics", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([FAKE_SNAPSHOT]);
      const snap = await store.getById("snap-001");
      expect(snap).toBeDefined();
      expect(snap!.metrics).toEqual({ impressions: 1000, clicks: 50 });
    });

    it("returns null when not found", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([]);
      expect(await store.getById("nonexistent")).toBeNull();
    });
  });

  describe("save", () => {
    it("upserts snapshot", async () => {
      mockSupabaseInsert.mockResolvedValueOnce([]);
      await store.save(FAKE_SNAPSHOT);
      expect(mockSupabaseInsert).toHaveBeenCalledWith(
        "metrics_snapshots",
        [expect.objectContaining({ id: "snap-001" })],
        { upsert: true, onConflict: "id" },
      );
    });
  });

  describe("delete", () => {
    it("deletes existing snapshot", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([FAKE_SNAPSHOT]);
      mockSupabaseDelete.mockResolvedValueOnce(undefined);
      expect(await store.delete("snap-001")).toBe(true);
    });

    it("returns false when snapshot does not exist", async () => {
      mockSupabaseSelect.mockResolvedValueOnce([]);
      expect(await store.delete("nonexistent")).toBe(false);
    });
  });
});
