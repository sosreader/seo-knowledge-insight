/**
 * sync-meeting-prep.ts — Upload local meeting-prep reports to Supabase.
 *
 * Usage:
 *   cd api && npx tsx scripts/sync-meeting-prep.ts
 *   cd api && npx tsx scripts/sync-meeting-prep.ts --file ../output/meeting_prep_20260406_ae0691ae.md
 */

import { SupabaseMeetingPrepStore } from "../src/store/supabase-meeting-prep-store.js";
import { readFileSync, readdirSync } from "fs";
import { resolve, basename } from "path";

const META_RE = /<!-- meeting_prep_meta ({.*?}) -->/;
const FILENAME_RE = /^meeting_prep_(\d{8})_([0-9a-f]{8})\.md$/;

function parseMeta(content: string): Record<string, unknown> {
  const m = content.match(META_RE);
  return m ? JSON.parse(m[1]!) : {};
}

async function uploadFile(store: SupabaseMeetingPrepStore, filepath: string): Promise<"uploaded" | "skipped" | "error"> {
  const filename = basename(filepath);
  const match = filename.match(FILENAME_RE);
  if (!match) {
    console.error(`  SKIP: ${filename} — invalid filename format`);
    return "skipped";
  }

  const dateKey = `${match[1]}_${match[2]}`;

  const exists = await store.exists(dateKey);
  if (exists) {
    console.log(`  SKIP: ${filename} — already in Supabase`);
    return "skipped";
  }

  const content = readFileSync(filepath, "utf-8");
  const meta = parseMeta(content);

  await store.save(dateKey, filename, content, meta as never);
  console.log(`  UPLOADED: ${filename} (${Buffer.byteLength(content, "utf-8")} bytes)`);
  return "uploaded";
}

async function main(): Promise<void> {
  const store = new SupabaseMeetingPrepStore();
  const args = process.argv.slice(2);

  let files: string[];

  const fileIdx = args.indexOf("--file");
  if (fileIdx !== -1 && args[fileIdx + 1]) {
    files = [resolve(args[fileIdx + 1]!)];
  } else {
    const outputDir = resolve(import.meta.dirname ?? ".", "../../output");
    files = readdirSync(outputDir)
      .filter((f) => FILENAME_RE.test(f))
      .map((f) => resolve(outputDir, f));
  }

  console.log(`\n=== Sync Meeting-Prep (skip existing) ===\n`);

  let uploaded = 0;
  let skipped = 0;
  let errors = 0;

  for (const f of files) {
    try {
      const result = await uploadFile(store, f);
      if (result === "uploaded") uploaded++;
      else if (result === "skipped") skipped++;
    } catch (e) {
      console.error(`  ERROR: ${basename(f)} — ${e}`);
      errors++;
    }
  }

  console.log(`\n  Meeting-Prep  uploaded: ${uploaded} | skipped: ${skipped} | errors: ${errors}\n`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
