import { describe, it, expect, vi, beforeEach } from "vitest";
import { SessionSyncer } from "../../src/sync/session-sync.js";

// Mock supabase-client
vi.mock("../../src/store/supabase-client.js", () => ({
  supabaseSelect: vi.fn(),
  supabaseInsert: vi.fn(),
  hasSupabase: vi.fn(() => true),
  supabaseHeaders: vi.fn(() => ({})),
  SUPABASE_TIMEOUT_MS: 10_000,
}));

// Mock fs
vi.mock("node:fs", () => ({
  readdirSync: vi.fn(() => []),
  readFileSync: vi.fn(() => "{}"),
  existsSync: vi.fn(() => true),
  statSync: vi.fn(() => ({ size: 100, mtimeMs: Date.now() })),
  mkdirSync: vi.fn(),
  writeFileSync: vi.fn(),
  unlinkSync: vi.fn(),
  openSync: vi.fn(() => 3),
  readSync: vi.fn(),
  closeSync: vi.fn(),
}));

import { readdirSync, readFileSync } from "node:fs";
import { supabaseSelect, supabaseInsert } from "../../src/store/supabase-client.js";

const SESSION_A = {
  id: "09c22b06-2713-4d32-9b1d-63136ab4a34b",
  title: "Test Session A",
  messages: [],
  created_at: "2026-03-05T19:29:30.419Z",
  updated_at: "2026-03-05T19:29:49.869Z",
};

const SESSION_B = {
  id: "1bb169c8-37e1-464f-a705-824601858cf3",
  title: "Test Session B",
  messages: [{ role: "user", content: "hello", sources: [], created_at: "2026-03-05T19:30:00Z" }],
  created_at: "2026-03-05T19:30:00Z",
  updated_at: "2026-03-05T19:30:10Z",
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("SessionSyncer.computeDiff", () => {
  it("identifies local-only, remote-only, and both items", async () => {
    vi.mocked(readdirSync).mockReturnValue([
      `${SESSION_A.id}.json`,
      `${SESSION_B.id}.json`,
    ] as any);
    vi.mocked(readFileSync).mockImplementation((path: any) => {
      if (String(path).includes(SESSION_A.id)) return JSON.stringify(SESSION_A);
      if (String(path).includes(SESSION_B.id)) return JSON.stringify(SESSION_B);
      return "{}";
    });

    vi.mocked(supabaseSelect).mockResolvedValue([
      { id: SESSION_A.id },
      { id: "c2cc1ba8-528e-404c-832a-3a51efd755c6" },
    ]);

    const syncer = new SessionSyncer();
    const diff = await syncer.computeDiff();

    expect(diff.localOnly).toHaveLength(1);
    expect(diff.localOnly[0]!.key).toBe(SESSION_B.id);

    expect(diff.remoteOnly).toHaveLength(1);
    expect(diff.remoteOnly[0]!.key).toBe("c2cc1ba8-528e-404c-832a-3a51efd755c6");

    expect(diff.both).toHaveLength(1);
    expect(diff.both[0]!.key).toBe(SESSION_A.id);
  });

  it("handles empty local directory", async () => {
    vi.mocked(readdirSync).mockReturnValue([] as any);
    vi.mocked(supabaseSelect).mockResolvedValue([{ id: SESSION_A.id }]);

    const syncer = new SessionSyncer();
    const diff = await syncer.computeDiff();

    expect(diff.localOnly).toHaveLength(0);
    expect(diff.remoteOnly).toHaveLength(1);
    expect(diff.both).toHaveLength(0);
  });

  it("skips malformed JSON files", async () => {
    vi.mocked(readdirSync).mockReturnValue(["bad-file.json"] as any);
    vi.mocked(readFileSync).mockReturnValue("not valid json {{{");
    vi.mocked(supabaseSelect).mockResolvedValue([]);

    const syncer = new SessionSyncer();
    const diff = await syncer.computeDiff();

    // bad-file.json has no valid UUID so it's filtered out
    expect(diff.localOnly).toHaveLength(0);
  });
});

describe("SessionSyncer.upload", () => {
  it("uploads local-only sessions", async () => {
    vi.mocked(readdirSync).mockReturnValue([
      `${SESSION_A.id}.json`,
      `${SESSION_B.id}.json`,
    ] as any);
    vi.mocked(readFileSync).mockImplementation((path: any) => {
      if (String(path).includes(SESSION_A.id)) return JSON.stringify(SESSION_A);
      if (String(path).includes(SESSION_B.id)) return JSON.stringify(SESSION_B);
      return "{}";
    });

    // SESSION_A is already in Supabase, SESSION_B is local-only
    vi.mocked(supabaseSelect).mockResolvedValue([{ id: SESSION_A.id }]);
    vi.mocked(supabaseInsert).mockResolvedValue([]);

    const syncer = new SessionSyncer();
    const result = await syncer.upload({ dryRun: false, force: false });

    expect(result.uploaded).toBe(1);
    expect(result.skipped).toBe(1);
    expect(result.errors).toHaveLength(0);
    expect(supabaseInsert).toHaveBeenCalledTimes(1);

    const insertCall = vi.mocked(supabaseInsert).mock.calls[0]!;
    expect(insertCall[0]).toBe("sessions");
    expect((insertCall[1] as any)[0].id).toBe(SESSION_B.id);
    expect(insertCall[2]).toEqual({ upsert: true, onConflict: "id" });
  });

  it("uploads all when force=true", async () => {
    vi.mocked(readdirSync).mockReturnValue([
      `${SESSION_A.id}.json`,
      `${SESSION_B.id}.json`,
    ] as any);
    vi.mocked(readFileSync).mockImplementation((path: any) => {
      if (String(path).includes(SESSION_A.id)) return JSON.stringify(SESSION_A);
      if (String(path).includes(SESSION_B.id)) return JSON.stringify(SESSION_B);
      return "{}";
    });

    vi.mocked(supabaseSelect).mockResolvedValue([{ id: SESSION_A.id }]);
    vi.mocked(supabaseInsert).mockResolvedValue([]);

    const syncer = new SessionSyncer();
    const result = await syncer.upload({ dryRun: false, force: true });

    expect(result.uploaded).toBe(2);
    expect(result.skipped).toBe(0);
    expect(supabaseInsert).toHaveBeenCalledTimes(2);
  });

  it("returns zero uploads on dry-run", async () => {
    vi.mocked(readdirSync).mockReturnValue([`${SESSION_B.id}.json`] as any);
    vi.mocked(readFileSync).mockReturnValue(JSON.stringify(SESSION_B));
    vi.mocked(supabaseSelect).mockResolvedValue([]);

    const syncer = new SessionSyncer();
    const result = await syncer.upload({ dryRun: true, force: false });

    expect(result.uploaded).toBe(0);
    expect(supabaseInsert).not.toHaveBeenCalled();
  });

  it("collects errors without stopping", async () => {
    vi.mocked(readdirSync).mockReturnValue([
      `${SESSION_A.id}.json`,
      `${SESSION_B.id}.json`,
    ] as any);
    vi.mocked(readFileSync).mockImplementation((path: any) => {
      if (String(path).includes(SESSION_A.id)) return JSON.stringify(SESSION_A);
      if (String(path).includes(SESSION_B.id)) return JSON.stringify(SESSION_B);
      return "{}";
    });

    vi.mocked(supabaseSelect).mockResolvedValue([]);
    vi.mocked(supabaseInsert)
      .mockRejectedValueOnce(new Error("Supabase timeout"))
      .mockResolvedValueOnce([]);

    const syncer = new SessionSyncer();
    const result = await syncer.upload({ dryRun: false, force: false });

    expect(result.uploaded).toBe(1);
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0]).toContain("Supabase timeout");
  });
});
