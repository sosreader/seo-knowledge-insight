/**
 * PgSessionStore — chat session（app_session，warehouse_rag 有 SELECT／INSERT／UPDATE）。
 *
 * - 有 deleted_at（VW 無 RLS）：每個 SELECT／UPDATE 明寫 deleted_at IS NULL；刪除為軟刪除。
 * - content_hash NOT NULL：寫入 title／messages 時一併重算（見 session-content-hash.ts）。
 * - addMessage／updateMetadata 在單一交易內 SELECT ... FOR UPDATE 後 UPDATE，
 *   同一 session 併發送訊息不會互相覆蓋（Supabase 版是讀後 PATCH，有 lost update）。
 * - 時間欄位以 PostgREST 相同的 ISO 字串輸出，回應形狀不變。
 */

import { isoColumn, pgQuery, withPgTransaction, type Queryable } from "./pg-client.js";
import { escapeHtml } from "../utils/sanitize.js";
import { sessionContentHash } from "./session-content-hash.js";
import type { Session, SessionMessage, SessionMetadata } from "./session-store.js";

const MAX_MESSAGES_PER_SESSION = 100;
const DEFAULT_TITLE = "New Chat";
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const COLUMNS = `id, title, messages, metadata, ${isoColumn("created_at")}, ${isoColumn("updated_at")}`;

interface SessionRow {
  readonly id: string;
  readonly title: string;
  readonly messages: readonly SessionMessage[] | null;
  readonly metadata: SessionMetadata | null;
  readonly created_at: string;
  readonly updated_at: string;
}

function sanitizeTitle(raw: string): string {
  return escapeHtml(raw.slice(0, 50)).trim();
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

async function lockSession(client: Queryable, sessionId: string): Promise<Session | null> {
  const res = await client.query<SessionRow>(
    `SELECT ${COLUMNS} FROM app_session WHERE id = $1 AND deleted_at IS NULL FOR UPDATE`,
    [sessionId],
  );
  return res.rows[0] ? rowToSession(res.rows[0]) : null;
}

export class PgSessionStore {
  async listSessions(
    limit: number = 20,
    offset: number = 0,
  ): Promise<{ sessions: readonly Session[]; total: number }> {
    const [rows, countRows] = await Promise.all([
      pgQuery<SessionRow>(
        `SELECT ${COLUMNS} FROM app_session WHERE deleted_at IS NULL
          ORDER BY updated_at DESC, id ASC LIMIT $1 OFFSET $2`,
        [limit, offset],
      ),
      pgQuery<{ total: string }>("SELECT count(*) AS total FROM app_session WHERE deleted_at IS NULL"),
    ]);
    return { sessions: rows.map(rowToSession), total: Number(countRows[0]?.total ?? 0) };
  }

  async getSession(sessionId: string): Promise<Session | null> {
    if (!UUID_RE.test(sessionId)) return null;
    const rows = await pgQuery<SessionRow>(
      `SELECT ${COLUMNS} FROM app_session WHERE id = $1 AND deleted_at IS NULL LIMIT 1`,
      [sessionId],
    );
    return rows[0] ? rowToSession(rows[0]) : null;
  }

  async createSession(title: string = ""): Promise<Session> {
    const finalTitle = title ? sanitizeTitle(title) : DEFAULT_TITLE;
    const rows = await pgQuery<SessionRow>(
      `INSERT INTO app_session (title, messages, metadata, content_hash)
       VALUES ($1, '[]'::jsonb, '{}'::jsonb, $2)
       RETURNING ${COLUMNS}`,
      [finalTitle, sessionContentHash(finalTitle, [])],
    );
    return rowToSession(rows[0]!);
  }

  /** 附加一則訊息；session 不存在、已軟刪或已達上限回 null（路由回 404／409）。 */
  async addMessage(sessionId: string, msg: SessionMessage): Promise<Session | null> {
    if (!UUID_RE.test(sessionId)) return null;
    return withPgTransaction(async (client) => {
      const session = await lockSession(client, sessionId);
      if (!session) return null;
      if (session.messages.length >= MAX_MESSAGES_PER_SESSION) {
        console.warn(
          `PgSessionStore: session ${sessionId} reached max messages (${MAX_MESSAGES_PER_SESSION})`,
        );
        return null;
      }
      const title =
        session.title === DEFAULT_TITLE && msg.role === "user" ? sanitizeTitle(msg.content) : session.title;
      const messages = [...session.messages, msg];
      const res = await client.query<SessionRow>(
        `UPDATE app_session
            SET title = $2, messages = $3::jsonb, content_hash = $4, updated_at = now()
          WHERE id = $1 AND deleted_at IS NULL
          RETURNING ${COLUMNS}`,
        [sessionId, title, JSON.stringify(messages), sessionContentHash(title, messages)],
      );
      return res.rows[0] ? rowToSession(res.rows[0]) : null;
    });
  }

  async updateMetadata(sessionId: string, metadata: Partial<SessionMetadata>): Promise<Session | null> {
    if (!UUID_RE.test(sessionId)) return null;
    return withPgTransaction(async (client) => {
      const session = await lockSession(client, sessionId);
      if (!session) return null;
      const merged = { ...(session.metadata ?? {}), ...metadata };
      const res = await client.query<SessionRow>(
        `UPDATE app_session SET metadata = $2::jsonb, updated_at = now()
          WHERE id = $1 AND deleted_at IS NULL
          RETURNING ${COLUMNS}`,
        [sessionId, JSON.stringify(merged)],
      );
      return res.rows[0] ? rowToSession(res.rows[0]) : null;
    });
  }

  /** 軟刪除（deleted_at = now()）；不存在或已刪回 false。 */
  async deleteSession(sessionId: string): Promise<boolean> {
    if (!UUID_RE.test(sessionId)) return false;
    const rows = await pgQuery<{ id: string }>(
      `UPDATE app_session SET deleted_at = now()
        WHERE id = $1 AND deleted_at IS NULL RETURNING id`,
      [sessionId],
    );
    return rows.length > 0;
  }
}
