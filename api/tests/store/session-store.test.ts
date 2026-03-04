import { describe, it, expect, beforeEach } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { FileSessionStore } from "../../src/store/session-store.js";

let store: FileSessionStore;
let tmpDir: string;

beforeEach(() => {
  tmpDir = mkdtempSync(join(tmpdir(), "session-test-"));
  store = new FileSessionStore(tmpDir);
});

describe("FileSessionStore", () => {
  it("creates a session with default title", () => {
    const session = store.createSession();
    expect(session.title).toBe("New Chat");
    expect(session.messages).toHaveLength(0);
    expect(session.id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    );
  });

  it("creates a session with custom title", () => {
    const session = store.createSession("My SEO Session");
    expect(session.title).toBe("My SEO Session");
  });

  it("gets session by id", () => {
    const created = store.createSession("Test");
    const retrieved = store.getSession(created.id);
    expect(retrieved).not.toBeNull();
    expect(retrieved!.id).toBe(created.id);
    expect(retrieved!.title).toBe("Test");
  });

  it("returns null for non-existent session", () => {
    const result = store.getSession("00000000-0000-4000-8000-000000000000");
    expect(result).toBeNull();
  });

  it("returns null for invalid session ID format", () => {
    const result = store.getSession("invalid-id");
    expect(result).toBeNull();
  });

  it("adds message to session", () => {
    const session = store.createSession();
    const updated = store.addMessage(session.id, {
      role: "user",
      content: "What is SEO?",
      sources: [],
      created_at: new Date().toISOString(),
    });
    expect(updated).not.toBeNull();
    expect(updated!.messages).toHaveLength(1);
    expect(updated!.messages[0]!.content).toBe("What is SEO?");
  });

  it("auto-updates title from first user message", () => {
    const session = store.createSession();
    const updated = store.addMessage(session.id, {
      role: "user",
      content: "How to improve Core Web Vitals?",
      sources: [],
      created_at: new Date().toISOString(),
    });
    expect(updated!.title).toBe("How to improve Core Web Vitals?");
  });

  it("sanitizes title (HTML escape)", () => {
    const session = store.createSession();
    const updated = store.addMessage(session.id, {
      role: "user",
      content: '<script>alert("xss")</script>',
      sources: [],
      created_at: new Date().toISOString(),
    });
    expect(updated!.title).not.toContain("<script>");
  });

  it("lists sessions sorted by mtime descending", () => {
    store.createSession("First");
    store.createSession("Second");
    store.createSession("Third");

    const { sessions, total } = store.listSessions(10, 0);
    expect(total).toBe(3);
    expect(sessions).toHaveLength(3);
  });

  it("deletes session", () => {
    const session = store.createSession("To Delete");
    expect(store.deleteSession(session.id)).toBe(true);
    expect(store.getSession(session.id)).toBeNull();
  });

  it("returns false when deleting non-existent session", () => {
    expect(store.deleteSession("00000000-0000-4000-8000-000000000000")).toBe(false);
  });

  it("paginates sessions", () => {
    for (let i = 0; i < 5; i++) {
      store.createSession(`Session ${i}`);
    }
    const { sessions, total } = store.listSessions(2, 1);
    expect(total).toBe(5);
    expect(sessions).toHaveLength(2);
  });
});
