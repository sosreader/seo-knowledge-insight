/**
 * SupabaseSessionStore — Supabase-backed session persistence.
 *
 * Drop-in replacement for FileSessionStore when SUPABASE_URL is set.
 * Uses the same Session/SessionMessage interfaces.
 */

import { supabaseSelect, supabaseHeaders, supabasePatch, SUPABASE_TIMEOUT_MS } from "./supabase-client.js";
import { config } from "../config.js";
import { escapeHtml } from "../utils/sanitize.js";
import type { Session, SessionMessage, SessionMetadata } from "./session-store.js";

const MAX_MESSAGES_PER_SESSION = 100;

function sanitizeTitle(raw: string): string {
  return escapeHtml(raw.slice(0, 50)).trim();
}

function nowIso(): string {
  return new Date().toISOString().replace(/(\.\d{3})\d*Z$/, "$1Z");
}

interface SessionRow {
  id: string;
  title: string;
  messages: readonly SessionMessage[];
  metadata: SessionMetadata;
  created_at: string;
  updated_at: string;
}

function rowToSession(row: SessionRow): Session {
  return {
    id: row.id,
    title: row.title,
    messages: row.messages ?? [],
    metadata: row.metadata ?? {},
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

export class SupabaseSessionStore {
  async listSessions(
    limit: number = 20,
    offset: number = 0,
  ): Promise<{ sessions: readonly Session[]; total: number }> {
    // Get total count via HEAD
    const countResp = await fetch(
      `${config.SUPABASE_URL}/rest/v1/sessions?select=id`,
      {
        method: "HEAD",
        headers: { ...supabaseHeaders(), Prefer: "count=exact" },
        signal: AbortSignal.timeout(SUPABASE_TIMEOUT_MS),
      },
    );
    const range = countResp.headers.get("content-range") ?? "*/0";
    const total = parseInt(range.split("/")[1] ?? "0", 10);

    const rows = await supabaseSelect<SessionRow>(
      "sessions",
      `?select=id,title,messages,metadata,created_at,updated_at&order=updated_at.desc&limit=${limit}&offset=${offset}`,
    );

    return { sessions: rows.map(rowToSession), total };
  }

  async getSession(sessionId: string): Promise<Session | null> {
    const rows = await supabaseSelect<SessionRow>(
      "sessions",
      `?select=id,title,messages,metadata,created_at,updated_at&id=eq.${sessionId}&limit=1`,
    );
    return rows.length > 0 ? rowToSession(rows[0]!) : null;
  }

  async createSession(title: string = ""): Promise<Session> {
    const now = nowIso();
    const body = {
      title: title ? sanitizeTitle(title) : "New Chat",
      messages: [],
      metadata: {},
      created_at: now,
      updated_at: now,
    };

    const resp = await fetch(`${config.SUPABASE_URL}/rest/v1/sessions`, {
      method: "POST",
      headers: { ...supabaseHeaders(), Prefer: "return=representation" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(SUPABASE_TIMEOUT_MS),
    });

    if (!resp.ok) {
      throw new Error(`Failed to create session (${resp.status})`);
    }

    const rows = (await resp.json()) as SessionRow[];
    return rowToSession(rows[0]!);
  }

  async addMessage(
    sessionId: string,
    msg: SessionMessage,
  ): Promise<Session | null> {
    const session = await this.getSession(sessionId);
    if (!session) return null;

    if (session.messages.length >= MAX_MESSAGES_PER_SESSION) {
      console.warn(
        `SupabaseSessionStore: session ${sessionId} reached max messages (${MAX_MESSAGES_PER_SESSION})`,
      );
      return null;
    }

    let newTitle = session.title;
    if (newTitle === "New Chat" && msg.role === "user") {
      newTitle = sanitizeTitle(msg.content);
    }

    const updatedMessages = [...session.messages, msg];

    const resp = await fetch(
      `${config.SUPABASE_URL}/rest/v1/sessions?id=eq.${sessionId}`,
      {
        method: "PATCH",
        headers: { ...supabaseHeaders(), Prefer: "return=representation" },
        body: JSON.stringify({
          title: newTitle,
          messages: updatedMessages,
          updated_at: nowIso(),
        }),
        signal: AbortSignal.timeout(SUPABASE_TIMEOUT_MS),
      },
    );

    if (!resp.ok) {
      throw new Error(`Failed to update session (${resp.status})`);
    }

    const rows = (await resp.json()) as SessionRow[];
    return rows.length > 0 ? rowToSession(rows[0]!) : null;
  }

  async updateMetadata(
    sessionId: string,
    metadata: Partial<SessionMetadata>,
  ): Promise<Session | null> {
    const session = await this.getSession(sessionId);
    if (!session) return null;

    const merged = { ...(session.metadata ?? {}), ...metadata };

    const resp = await fetch(
      `${config.SUPABASE_URL}/rest/v1/sessions?id=eq.${sessionId}`,
      {
        method: "PATCH",
        headers: { ...supabaseHeaders(), Prefer: "return=representation" },
        body: JSON.stringify({
          metadata: merged,
          updated_at: nowIso(),
        }),
        signal: AbortSignal.timeout(SUPABASE_TIMEOUT_MS),
      },
    );

    if (!resp.ok) {
      throw new Error(`Failed to update session metadata (${resp.status})`);
    }

    const rows = (await resp.json()) as SessionRow[];
    return rows.length > 0 ? rowToSession(rows[0]!) : null;
  }

  /** Soft-delete a session (sets deleted_at via service key). */
  async deleteSession(sessionId: string): Promise<boolean> {
    const session = await this.getSession(sessionId);
    if (!session) return false;
    await supabasePatch(
      "sessions",
      `?id=eq.${encodeURIComponent(sessionId)}`,
      { deleted_at: new Date().toISOString() },
    );
    return true;
  }
}
