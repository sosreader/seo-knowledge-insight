import { beforeEach, describe, expect, it, vi } from "vitest";
import { PgSessionStore } from "../../src/store/pg-session-store.js";
import { sessionContentHash } from "../../src/store/session-content-hash.js";
import type { SessionMessage } from "../../src/store/session-store.js";
import { pgAvailable, usePgFixture } from "../pg/pg-fixture.js";

const fx = usePgFixture("sess");
const ISO_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+00:00$/;
const MISSING_ID = "00000000-0000-4000-8000-000000000000";

function msg(role: string, content: string): SessionMessage {
  return { role, content, sources: [], created_at: "2026-10-23T00:00:00.000Z" };
}

async function storedHash(id: string): Promise<string> {
  const { rows } = await fx.admin().query("SELECT content_hash FROM app_session WHERE id = $1", [id]);
  return rows[0].content_hash;
}

describe.skipIf(!pgAvailable)("PgSessionStore against app_session (warehouse_rag)", () => {
  const store = new PgSessionStore();

  beforeEach(async () => {
    await fx.activate();
    await fx.admin().query("TRUNCATE app_session");
  });

  it("creates a session with a valid content_hash and ISO timestamps", async () => {
    const s = await store.createSession("");
    expect(s).toMatchObject({ title: "New Chat", messages: [], metadata: {} });
    expect(s.id).toMatch(/^[0-9a-f-]{36}$/);
    expect(s.created_at).toMatch(ISO_RE);
    expect(s.updated_at).toMatch(ISO_RE);
    expect(await storedHash(s.id)).toBe(sessionContentHash("New Chat", []));
  });

  it("sanitises and truncates the title", async () => {
    const s = await store.createSession("<b>" + "x".repeat(80));
    expect(s.title).not.toContain("<b>");
    expect(s.title.length).toBeLessThanOrEqual(60);
  });

  it("adds messages, auto-titles from the first user message and rehashes", async () => {
    const s = await store.createSession();
    const after = await store.addMessage(s.id, msg("user", "什麼是 LCP？"));
    expect(after?.title).toBe("什麼是 LCP？");
    const final = await store.addMessage(s.id, msg("assistant", "答"));
    expect(final?.messages.map((m) => m.role)).toEqual(["user", "assistant"]);
    expect(final?.title).toBe("什麼是 LCP？");
    expect(await storedHash(s.id)).toBe(sessionContentHash(final!.title, final!.messages));
  });

  it("serialises concurrent addMessage calls (no lost update)", async () => {
    const s = await store.createSession("t");
    await Promise.all(Array.from({ length: 8 }, (_, i) => store.addMessage(s.id, msg("user", `m${i}`))));
    const got = await store.getSession(s.id);
    expect(got?.messages).toHaveLength(8);
  });

  it("refuses to add beyond 100 messages", async () => {
    const s = await store.createSession("full");
    const many = Array.from({ length: 100 }, (_, i) => msg("user", `m${i}`));
    await fx.admin().query("UPDATE app_session SET messages = $2::jsonb WHERE id = $1", [s.id, JSON.stringify(many)]);
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    expect(await store.addMessage(s.id, msg("user", "overflow"))).toBeNull();
    warn.mockRestore();
  });

  it("merges metadata without touching messages", async () => {
    const s = await store.createSession("meta");
    await store.updateMetadata(s.id, { maturity_level: "L2" });
    const got = await store.updateMetadata(s.id, { other: 1 });
    expect(got?.metadata).toEqual({ maturity_level: "L2", other: 1 });
  });

  it("lists newest first with total, excluding soft-deleted sessions", async () => {
    const a = await store.createSession("a");
    const b = await store.createSession("b");
    const c = await store.createSession("c");
    await fx.admin().query("UPDATE app_session SET updated_at = now() + interval '1 minute' WHERE id = $1", [a.id]);
    await fx.admin().query("UPDATE app_session SET deleted_at = now() WHERE id = $1", [b.id]);
    const page = await store.listSessions(10, 0);
    expect(page.total).toBe(2);
    expect(page.sessions.map((s) => s.id)).toEqual([a.id, c.id]);
    const second = await store.listSessions(1, 1);
    expect(second.sessions.map((s) => s.id)).toEqual([c.id]);
    expect(second.total).toBe(2);
  });

  it("soft-deletes; deleted sessions are invisible to every read and write path", async () => {
    const s = await store.createSession("bye");
    expect(await store.deleteSession(s.id)).toBe(true);
    expect(await store.deleteSession(s.id)).toBe(false);
    expect(await store.getSession(s.id)).toBeNull();
    expect(await store.addMessage(s.id, msg("user", "x"))).toBeNull();
    expect(await store.updateMetadata(s.id, { a: 1 })).toBeNull();
    const { rows } = await fx.admin().query("SELECT deleted_at FROM app_session WHERE id = $1", [s.id]);
    expect(rows[0].deleted_at).not.toBeNull();
  });

  it("returns null/false for unknown or malformed ids without hitting a cast error", async () => {
    expect(await store.getSession(MISSING_ID)).toBeNull();
    expect(await store.getSession("not-a-uuid")).toBeNull();
    expect(await store.addMessage("not-a-uuid", msg("user", "x"))).toBeNull();
    expect(await store.updateMetadata("not-a-uuid", {})).toBeNull();
    expect(await store.deleteSession("not-a-uuid")).toBe(false);
    expect(await store.addMessage(MISSING_ID, msg("user", "x"))).toBeNull();
    expect(await store.updateMetadata(MISSING_ID, {})).toBeNull();
  });
});
