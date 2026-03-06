/**
 * File-based session store — one JSON file per session.
 *
 * Translated from Python app/core/session_store.py
 */

import {
  readFileSync,
  writeFileSync,
  readdirSync,
  unlinkSync,
  existsSync,
  mkdirSync,
  statSync,
} from "node:fs";
import { join } from "node:path";
import { v4 as uuidv4 } from "uuid";
import { paths } from "../config.js";
import { escapeHtml } from "../utils/sanitize.js";

const MAX_MESSAGES_PER_SESSION = 100;

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

function nowIso(): string {
  const now = new Date();
  return now.toISOString().replace(/(\.\d{3})\d*Z$/, "$1Z");
}

function sanitizeTitle(raw: string): string {
  return escapeHtml(raw.slice(0, 50)).trim();
}

export interface SessionMessage {
  readonly role: string;
  readonly content: string;
  readonly sources: readonly Record<string, unknown>[];
  readonly created_at: string;
  readonly metadata?: Record<string, unknown>;
}

export interface Session {
  readonly id: string;
  readonly title: string;
  readonly messages: readonly SessionMessage[];
  readonly created_at: string;
  readonly updated_at: string;
}

export class FileSessionStore {
  private readonly baseDir: string;

  constructor(baseDir?: string) {
    this.baseDir = baseDir ?? paths.sessionsDir;
    if (!existsSync(this.baseDir)) {
      mkdirSync(this.baseDir, { recursive: true });
    }
  }

  private validateId(sessionId: string): void {
    if (!UUID_RE.test(sessionId)) {
      throw new Error(`Invalid session_id format: ${sessionId}`);
    }
  }

  private filePath(sessionId: string): string {
    this.validateId(sessionId);
    return join(this.baseDir, `${sessionId}.json`);
  }

  private readSession(sessionId: string): Session | null {
    try {
      const fp = this.filePath(sessionId);
      if (!existsSync(fp)) return null;
      const data = JSON.parse(readFileSync(fp, "utf-8"));
      return data as Session;
    } catch {
      return null;
    }
  }

  private writeSession(session: Session): void {
    const fp = this.filePath(session.id);
    writeFileSync(fp, JSON.stringify(session, null, 2), "utf-8");
  }

  listSessions(
    limit: number = 20,
    offset: number = 0,
  ): { sessions: readonly Session[]; total: number } {
    if (!existsSync(this.baseDir)) return { sessions: [], total: 0 };

    const files = readdirSync(this.baseDir)
      .filter((f) => f.endsWith(".json"))
      .map((f) => ({
        name: f,
        mtime: statSync(join(this.baseDir, f)).mtimeMs,
      }))
      .sort((a, b) => b.mtime - a.mtime);

    const allSessions: Session[] = [];
    for (const { name } of files) {
      const stem = name.replace(".json", "");
      const s = this.readSession(stem);
      if (s) allSessions.push(s);
    }

    return {
      sessions: allSessions.slice(offset, offset + limit),
      total: allSessions.length,
    };
  }

  getSession(sessionId: string): Session | null {
    return this.readSession(sessionId);
  }

  createSession(title: string = ""): Session {
    const session: Session = {
      id: uuidv4(),
      title: title ? sanitizeTitle(title) : "New Chat",
      messages: [],
      created_at: nowIso(),
      updated_at: nowIso(),
    };
    this.writeSession(session);
    return session;
  }

  addMessage(sessionId: string, msg: SessionMessage): Session | null {
    const session = this.readSession(sessionId);
    if (!session) return null;

    if (session.messages.length >= MAX_MESSAGES_PER_SESSION) {
      console.warn(
        `session_store: session ${sessionId} reached max messages (${MAX_MESSAGES_PER_SESSION})`,
      );
      return null;
    }

    let newTitle = session.title;
    if (newTitle === "New Chat" && msg.role === "user") {
      newTitle = sanitizeTitle(msg.content);
    }

    const updated: Session = {
      id: session.id,
      title: newTitle,
      messages: [...session.messages, msg],
      created_at: session.created_at,
      updated_at: nowIso(),
    };
    this.writeSession(updated);
    return updated;
  }

  deleteSession(sessionId: string): boolean {
    try {
      const fp = this.filePath(sessionId);
      if (!existsSync(fp)) return false;
      unlinkSync(fp);
      return true;
    } catch {
      return false;
    }
  }
}

import { hasSupabase } from "./supabase-client.js";
import { SupabaseSessionStore } from "./supabase-session-store.js";

/**
 * Unified async session store interface.
 * FileSessionStore methods are sync but wrapped in Promise for compatibility.
 */
export interface AsyncSessionStore {
  listSessions(limit?: number, offset?: number): Promise<{ sessions: readonly Session[]; total: number }>;
  getSession(sessionId: string): Promise<Session | null>;
  createSession(title?: string): Promise<Session>;
  addMessage(sessionId: string, msg: SessionMessage): Promise<Session | null>;
  deleteSession(sessionId: string): Promise<boolean>;
}

function wrapFileStore(fs: FileSessionStore): AsyncSessionStore {
  return {
    listSessions: (limit, offset) => Promise.resolve(fs.listSessions(limit, offset)),
    getSession: (id) => Promise.resolve(fs.getSession(id)),
    createSession: (title) => Promise.resolve(fs.createSession(title)),
    addMessage: (id, msg) => Promise.resolve(fs.addMessage(id, msg)),
    deleteSession: (id) => Promise.resolve(fs.deleteSession(id)),
  };
}

/** Factory: returns SupabaseSessionStore or FileSessionStore (async wrapper). */
export function createSessionStore(): AsyncSessionStore {
  if (hasSupabase()) {
    console.log("SessionStore: using Supabase");
    return new SupabaseSessionStore();
  }
  console.log("SessionStore: using file-based");
  return wrapFileStore(new FileSessionStore());
}

export const sessionStore = createSessionStore();
