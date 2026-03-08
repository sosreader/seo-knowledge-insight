/**
 * ReportSyncer — upload local report files to Supabase.
 *
 * Compares local output/report_*.md against Supabase `reports` table,
 * then upserts missing or (with --force) existing items.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { paths } from "../config.js";
import { SupabaseReportStore } from "../store/supabase-report-store.js";
import { listReportFiles, parseReportMeta } from "../utils/report-file.js";
import type { SyncDiff, SyncDiffItem, SyncOptions, SyncResult } from "./sync-types.js";

export class ReportSyncer {
  private readonly store: SupabaseReportStore;

  constructor(store?: SupabaseReportStore) {
    this.store = store ?? new SupabaseReportStore();
  }

  /** Compare local report files vs Supabase reports table. */
  async computeDiff(): Promise<SyncDiff> {
    const localReports = listReportFiles();
    const remoteReports = await this.store.list();

    const localKeys = new Set(localReports.map((r) => r.date));
    const remoteKeys = new Set(remoteReports.map((r) => r.date));

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

  /** Upload local-only reports (and optionally force-overwrite existing). */
  async upload(options: SyncOptions): Promise<SyncResult> {
    const diff = await this.computeDiff();
    const toUpload = options.force
      ? [...diff.localOnly, ...diff.both]
      : diff.localOnly;

    if (options.dryRun || toUpload.length === 0) {
      return { uploaded: 0, skipped: diff.both.length, errors: [] };
    }

    let uploaded = 0;
    const errors: string[] = [];

    for (const item of toUpload) {
      try {
        const filepath = join(paths.outputDir, `report_${item.key}.md`);
        const content = readFileSync(filepath, "utf-8");
        const meta = parseReportMeta(content);
        await this.store.save(item.key, content, meta);
        uploaded++;
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        errors.push(`report ${item.key}: ${msg}`);
      }
    }

    const skipped = options.force ? 0 : diff.both.length;
    return { uploaded, skipped, errors };
  }
}
