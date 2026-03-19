/**
 * Store Registry — centralized store singleton creation.
 *
 * Eliminates duplicate hasSupabase() + new SupabaseXxxStore() calls
 * scattered across route modules (reports.ts:21-22, pipeline.ts:46).
 */

import { hasSupabase } from "./supabase-client.js";
import { SupabaseReportStore } from "./supabase-report-store.js";
import { SupabaseSnapshotStore } from "./supabase-snapshot-store.js";

export const reportStore = hasSupabase() ? new SupabaseReportStore() : null;
export const snapshotStore = hasSupabase() ? new SupabaseSnapshotStore() : null;
