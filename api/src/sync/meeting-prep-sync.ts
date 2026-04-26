/**
 * MeetingPrepSyncer — upload local meeting-prep files to Supabase.
 *
 * Compares local output/meeting_prep_*.md against Supabase `meeting_prep` table,
 * then upserts missing or (with --force) existing items.
 */

import { meetingPrepStore as defaultStore } from "../store/store-registry.js";
import type { SupabaseMeetingPrepStore } from "../store/supabase-meeting-prep-store.js";
import { listMeetingPrepFiles, readMeetingPrepFile } from "../utils/meeting-prep-file.js";
import type { SyncDiff, SyncDiffItem, SyncOptions, SyncResult } from "./sync-types.js";

/**
 * Minimal store contract used by the syncer.
 *
 * Uses `list()` (which returns raw `date_key` as `date`) rather than `listWithMeta()`
 * — the latter formats the date and filters out rows with incomplete meta, which
 * would cause the sync diff to miss legitimately-stored rows.
 */
export interface MeetingPrepSyncStore {
  list: SupabaseMeetingPrepStore["list"];
  save: SupabaseMeetingPrepStore["save"];
}

export class MeetingPrepSyncer {
  private readonly store: MeetingPrepSyncStore;

  constructor(store?: MeetingPrepSyncStore | null) {
    const resolved = store ?? defaultStore;
    if (!resolved) {
      throw new Error("Supabase not configured (SUPABASE_URL/SUPABASE_ANON_KEY missing)");
    }
    this.store = resolved;
  }

  private requireStore() {
    return this.store;
  }

  /** Compare local meeting-prep files vs Supabase meeting_prep table. */
  async computeDiff(): Promise<SyncDiff> {
    const store = this.requireStore();
    const local = listMeetingPrepFiles();
    const remote = await store.list();

    const localKeys = new Set(local.map((f) => f.dateKey));
    const remoteKeys = new Set(remote.map((r) => r.date));

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

  /** Upload local-only meeting-prep files (and optionally force-overwrite existing). */
  async upload(options: SyncOptions): Promise<SyncResult> {
    const store = this.requireStore();
    const diff = await this.computeDiff();
    const toUploadKeys = new Set(
      options.force
        ? [...diff.localOnly.map((i) => i.key), ...diff.both.map((i) => i.key)]
        : diff.localOnly.map((i) => i.key),
    );

    if (options.dryRun || toUploadKeys.size === 0) {
      return { uploaded: 0, skipped: diff.both.length, errors: [] };
    }

    const local = listMeetingPrepFiles();
    let uploaded = 0;
    const errors: string[] = [];

    for (const file of local) {
      if (!toUploadKeys.has(file.dateKey)) continue;
      try {
        const { content, meta } = readMeetingPrepFile(file);
        await store.save(file.dateKey, file.filename, content, meta);
        uploaded++;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        errors.push(`meeting-prep ${file.dateKey}: ${msg}`);
      }
    }

    const skipped = options.force ? 0 : diff.both.length;
    return { uploaded, skipped, errors };
  }
}
