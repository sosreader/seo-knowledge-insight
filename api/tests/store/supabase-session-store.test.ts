/**
 * Tests for SupabaseSessionStore.
 * Uses mocked fetch to avoid real network calls.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock config
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

vi.mock("../../src/store/supabase-client.js", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../../src/store/supabase-client.js")>();
  return {
    ...mod,
    hasSupabase: () => true,
    supabaseHeaders: () => ({
      apikey: "test",
      Authorization: "Bearer test",
      "Content-Type": "application/json",
    }),
    supabaseSelect: vi.fn(),
  };
});

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

import { SupabaseSessionStore } from "../../src/store/supabase-session-store.js";
import { supabaseSelect } from "../../src/store/supabase-client.js";

const FAKE_SESSION_ROW = {
  id: "00000000-0000-4000-8000-000000000001",
  title: "Test Chat",
  messages: [{ role: "user" as const, content: "Hello" }],
  created_at: "2026-03-01T00:00:00.000Z",
  updated_at: "2026-03-01T00:00:00.000Z",
};

describe("SupabaseSessionStore", () => {
  let store: SupabaseSessionStore;

  beforeEach(() => {
    vi.clearAllMocks();
    store = new SupabaseSessionStore();
  });

  describe("listSessions", () => {
    it("returns sessions with total count", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ "content-range": "0-0/3" }),
      });
      vi.mocked(supabaseSelect).mockResolvedValueOnce([FAKE_SESSION_ROW]);

      const { sessions, total } = await store.listSessions(20, 0);
      expect(total).toBe(3);
      expect(sessions.length).toBe(1);
      expect(sessions[0]!.id).toBe(FAKE_SESSION_ROW.id);
      expect(sessions[0]!.title).toBe("Test Chat");
    });

    it("handles empty content-range", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({}),
      });
      vi.mocked(supabaseSelect).mockResolvedValueOnce([]);

      const { sessions, total } = await store.listSessions();
      expect(total).toBe(0);
      expect(sessions).toEqual([]);
    });
  });

  describe("getSession", () => {
    it("returns session when found", async () => {
      vi.mocked(supabaseSelect).mockResolvedValueOnce([FAKE_SESSION_ROW]);

      const session = await store.getSession(FAKE_SESSION_ROW.id);
      expect(session).toBeDefined();
      expect(session!.title).toBe("Test Chat");
      expect(session!.messages).toHaveLength(1);
    });

    it("returns null when not found", async () => {
      vi.mocked(supabaseSelect).mockResolvedValueOnce([]);

      const session = await store.getSession("nonexistent");
      expect(session).toBeNull();
    });
  });

  describe("createSession", () => {
    it("creates session with title", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [FAKE_SESSION_ROW],
      });

      const session = await store.createSession("Test Chat");
      expect(session.title).toBe("Test Chat");
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/rest/v1/sessions"),
        expect.objectContaining({ method: "POST" }),
      );
    });

    it("uses 'New Chat' when no title provided", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [{ ...FAKE_SESSION_ROW, title: "New Chat" }],
      });

      const session = await store.createSession();
      expect(session.title).toBe("New Chat");
    });

    it("throws on HTTP error", async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

      await expect(store.createSession("Test")).rejects.toThrow(
        "Failed to create session (500)",
      );
    });
  });

  describe("addMessage", () => {
    it("appends message and updates title for first user message", async () => {
      // getSession call
      vi.mocked(supabaseSelect).mockResolvedValueOnce([
        { ...FAKE_SESSION_ROW, title: "New Chat", messages: [] },
      ]);
      // PATCH call
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => [
          { ...FAKE_SESSION_ROW, title: "User question", messages: [{ role: "user", content: "User question" }] },
        ],
      });

      const session = await store.addMessage(FAKE_SESSION_ROW.id, {
        role: "user",
        content: "User question",
      });
      expect(session).toBeDefined();
      expect(session!.title).toBe("User question");
    });

    it("returns null when session not found", async () => {
      vi.mocked(supabaseSelect).mockResolvedValueOnce([]);

      const session = await store.addMessage("nonexistent", {
        role: "user",
        content: "Hello",
      });
      expect(session).toBeNull();
    });

    it("returns null when max messages reached", async () => {
      const fullSession = {
        ...FAKE_SESSION_ROW,
        messages: Array.from({ length: 100 }, (_, i) => ({
          role: "user" as const,
          content: `msg ${i}`,
        })),
      };
      vi.mocked(supabaseSelect).mockResolvedValueOnce([fullSession]);

      const session = await store.addMessage(FAKE_SESSION_ROW.id, {
        role: "user",
        content: "one more",
      });
      expect(session).toBeNull();
    });

    it("throws on PATCH failure", async () => {
      vi.mocked(supabaseSelect).mockResolvedValueOnce([
        { ...FAKE_SESSION_ROW, messages: [] },
      ]);
      mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

      await expect(
        store.addMessage(FAKE_SESSION_ROW.id, { role: "user", content: "Hi" }),
      ).rejects.toThrow("Failed to update session (500)");
    });
  });

  describe("deleteSession", () => {
    it("returns true on success", async () => {
      mockFetch.mockResolvedValueOnce({ ok: true });
      expect(await store.deleteSession(FAKE_SESSION_ROW.id)).toBe(true);
    });

    it("returns false on failure", async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });
      expect(await store.deleteSession(FAKE_SESSION_ROW.id)).toBe(false);
    });
  });
});
