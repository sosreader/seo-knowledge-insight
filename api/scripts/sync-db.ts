/**
 * sync-db.ts — Upload local reports & sessions to Supabase.
 *
 * Usage:
 *   cd api && npx tsx scripts/sync-db.ts status
 *   cd api && npx tsx scripts/sync-db.ts upload
 *   cd api && npx tsx scripts/sync-db.ts upload --dry-run
 *   cd api && npx tsx scripts/sync-db.ts upload --force
 *   cd api && npx tsx scripts/sync-db.ts upload --type reports
 */

import { parseArgs } from "node:util";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { config as dotenvConfig } from "dotenv";

// Load env vars before importing config-dependent modules
const __dir = dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = resolve(__dir, "../..");
dotenvConfig({ path: resolve(__dir, "../.env") });
dotenvConfig({ path: resolve(ROOT_DIR, ".env") });

import { hasSupabase } from "../src/store/supabase-client.js";
import { ReportSyncer } from "../src/sync/report-sync.js";
import { SessionSyncer } from "../src/sync/session-sync.js";
import type { SyncDiff, SyncResult } from "../src/sync/sync-types.js";

// ────────────────────────────────────────────────────────────
// CLI parsing
// ────────────────────────────────────────────────────────────

const { values: flags, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    "dry-run": { type: "boolean", default: false },
    force: { type: "boolean", default: false },
    type: { type: "string", default: "all" },
    help: { type: "boolean", short: "h", default: false },
  },
});

const subcommand = positionals[0] ?? "status";

if (flags.help || !["status", "upload"].includes(subcommand)) {
  console.log(`
sync-db — Upload local reports & sessions to Supabase

Usage:
  npx tsx scripts/sync-db.ts status              Show diff summary
  npx tsx scripts/sync-db.ts upload              Upload local-only items
  npx tsx scripts/sync-db.ts upload --dry-run    Show what would be uploaded
  npx tsx scripts/sync-db.ts upload --force      Overwrite existing items
  npx tsx scripts/sync-db.ts upload --type reports  Only sync reports

Options:
  --type <reports|sessions|all>   Resource type (default: all)
  --dry-run                       Preview without writing
  --force                         Overwrite existing items in Supabase
  -h, --help                      Show this help
`.trim());
  process.exit(0);
}

// ────────────────────────────────────────────────────────────
// Output helpers
// ────────────────────────────────────────────────────────────

function printDiff(label: string, diff: SyncDiff): void {
  const total = diff.localOnly.length + diff.remoteOnly.length + diff.both.length;
  console.log(
    `  ${label.padEnd(10)} total: ${String(total).padStart(3)} | ` +
    `local-only: ${String(diff.localOnly.length).padStart(2)} | ` +
    `remote-only: ${String(diff.remoteOnly.length).padStart(2)} | ` +
    `both: ${String(diff.both.length).padStart(2)}`,
  );
}

function printResult(label: string, result: SyncResult): void {
  console.log(
    `  ${label.padEnd(10)} uploaded: ${result.uploaded} | skipped: ${result.skipped} | errors: ${result.errors.length}`,
  );
  for (const err of result.errors) {
    console.error(`    [ERROR] ${err}`);
  }
}

// ────────────────────────────────────────────────────────────
// Main
// ────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  if (!hasSupabase()) {
    console.error("SUPABASE_URL and SUPABASE_ANON_KEY are required. Check .env");
    process.exit(1);
  }

  const syncType = flags.type as string;
  const VALID_TYPES = new Set(["all", "reports", "sessions"]);
  if (!VALID_TYPES.has(syncType)) {
    console.error(`Invalid --type "${syncType}". Expected: all, reports, sessions`);
    process.exit(1);
  }
  const includeReports = syncType === "all" || syncType === "reports";
  const includeSessions = syncType === "all" || syncType === "sessions";

  const reportSyncer = new ReportSyncer();
  const sessionSyncer = new SessionSyncer();

  if (subcommand === "status") {
    console.log("\n=== Sync Status (Local vs Supabase) ===\n");

    if (includeReports) {
      const diff = await reportSyncer.computeDiff();
      printDiff("Reports", diff);
      if (diff.localOnly.length > 0) {
        console.log(`    local-only: ${diff.localOnly.map((i) => i.key).join(", ")}`);
      }
    }

    if (includeSessions) {
      const diff = await sessionSyncer.computeDiff();
      printDiff("Sessions", diff);
      if (diff.localOnly.length > 0) {
        console.log(`    local-only: ${diff.localOnly.map((i) => i.key).join(", ")}`);
      }
    }

    console.log();
    return;
  }

  // subcommand === "upload"
  const options = {
    dryRun: flags["dry-run"] as boolean,
    force: flags.force as boolean,
  };

  if (options.dryRun) {
    console.log("\n=== Sync Dry Run (no writes) ===\n");
  } else if (options.force) {
    console.log("\n=== Sync Upload (force overwrite) ===\n");
  } else {
    console.log("\n=== Sync Upload (skip existing) ===\n");
  }

  if (includeReports) {
    if (options.dryRun) {
      const diff = await reportSyncer.computeDiff();
      const count = options.force ? diff.localOnly.length + diff.both.length : diff.localOnly.length;
      console.log(`  Reports: would upload ${count} items`);
      if (diff.localOnly.length > 0) {
        console.log(`    new: ${diff.localOnly.map((i) => i.key).join(", ")}`);
      }
      if (options.force && diff.both.length > 0) {
        console.log(`    overwrite: ${diff.both.length} items`);
      }
    } else {
      const result = await reportSyncer.upload(options);
      printResult("Reports", result);
    }
  }

  if (includeSessions) {
    if (options.dryRun) {
      const diff = await sessionSyncer.computeDiff();
      const count = options.force ? diff.localOnly.length + diff.both.length : diff.localOnly.length;
      console.log(`  Sessions: would upload ${count} items`);
      if (diff.localOnly.length > 0) {
        console.log(`    new: ${diff.localOnly.map((i) => i.key).join(", ")}`);
      }
    } else {
      const result = await sessionSyncer.upload(options);
      printResult("Sessions", result);
    }
  }

  console.log();
}

main().catch((err) => {
  console.error("[sync-db] Fatal error:", err);
  process.exit(1);
});
