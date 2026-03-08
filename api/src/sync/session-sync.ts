/**
 * SessionSyncer — upload local session files to Supabase.
 *
 * Compares local output/sessions/*.json against Supabase `sessions` table,
 * then upserts missing or (with --force) existing items.
 */

import { readdirSync, readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { paths } from "../config.js";
import { supabaseSelect, supabaseInsert } from "../store/supabase-client.js";
import type { Session } from "../store/session-store.js";
import type { SyncDiff, SyncDiffItem, SyncOptions, SyncResult } from "./sync-types.js";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

interface SessionIdRow {
  readonly id: string;
}

/** Read local session files from output/sessions/. */
function listLocalSessions(): readonly Session[] {
  const dir = paths.sessionsDir;
  if (!existsSync(dir)) return [];

  return readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => {
      try {
        const content = readFileSync(join(dir, f), "utf-8");
        const session = JSON.parse(content) as Session;
        if (!UUID_RE.test(session.id)) return null;
        return session;
      } catch (err) {
        console.warn(`[session-sync] Skipping malformed file ${f}: ${err instanceof Error ? err.message : err}`);
        return null;
      }
    })
    .filter((s): s is Session => s !== null);
}

export class SessionSyncer {
  /** Compare local session files vs Supabase sessions table. */
  async computeDiff(): Promise<SyncDiff> {
    const localSessions = listLocalSessions();
    const remoteSessions = await supabaseSelect<SessionIdRow>(
      "sessions",
      "?select=id",
    );

    const localKeys = new Set(localSessions.map((s) => s.id));
    const remoteKeys = new Set(remoteSessions.map((s) => s.id));

    const localOnly: SyncDiffItem[] = [];
    const remoteOnly: SyncDiffItem[] = [];
    const both: SyncDiffItem[] = [];

    for (const key of localKeys) {
      if (remoteKeys.has(key)) {
        both.push({ key, localOnly: false, remoteOnly: false, both: true });
      } else {
        localOnly.push({ key, localOnly: true, remoteOnly: false, both: false });
      }
    }

    for (const key of remoteKeys) {
      if (!localKeys.has(key)) {
        remoteOnly.push({ key, localOnly: false, remoteOnly: true, both: false });
      }
    }

    return { localOnly, remoteOnly, both };
  }

  /** Upload local-only sessions (and optionally force-overwrite existing). */
  async upload(options: SyncOptions): Promise<SyncResult> {
    const localSessions = listLocalSessions();
    const remoteIds = await supabaseSelect<SessionIdRow>("sessions", "?select=id");
    const remoteKeys = new Set(remoteIds.map((s) => s.id));

    const localOnly = localSessions.filter((s) => !remoteKeys.has(s.id));
    const bothCount = localSessions.length - localOnly.length;

    const toUpload = options.force ? localSessions : localOnly;

    if (options.dryRun || toUpload.length === 0) {
      return { uploaded: 0, skipped: bothCount, errors: [] };
    }

    const rows = toUpload.map((s) => ({
      id: s.id,
      title: s.title,
      messages: s.messages,
      created_at: s.created_at,
      updated_at: s.updated_at,
    }));

    let uploaded = 0;
    const errors: string[] = [];

    // Upload one by one to isolate errors
    for (const row of rows) {
      try {
        await supabaseInsert("sessions", [row], { upsert: true, onConflict: "id" });
        uploaded++;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        errors.push(`session ${row.id}: ${msg}`);
      }
    }

    const skipped = options.force ? 0 : bothCount;
    return { uploaded, skipped, errors };
  }
}
