/**
 * Shared types for sync-db operations.
 */

export interface SyncOptions {
  /** Only show diff, do not write. */
  readonly dryRun: boolean;
  /** Overwrite existing items in Supabase. */
  readonly force: boolean;
}

export interface SyncDiffItem {
  /** Identity key (date_key for reports, UUID for sessions). */
  readonly key: string;
  /** True if item exists only in local filesystem. */
  readonly localOnly: boolean;
  /** True if item exists only in Supabase. */
  readonly remoteOnly: boolean;
  /** True if item exists in both local and Supabase. */
  readonly both: boolean;
}

export interface SyncDiff {
  readonly localOnly: readonly SyncDiffItem[];
  readonly remoteOnly: readonly SyncDiffItem[];
  readonly both: readonly SyncDiffItem[];
}

export interface SyncResult {
  readonly uploaded: number;
  readonly skipped: number;
  readonly errors: readonly string[];
}
