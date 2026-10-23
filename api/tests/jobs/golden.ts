import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { FreshnessRow } from "../../src/jobs/freshness.js";

/** Python 版（scripts/update_freshness.py）實跑產生的 golden；產生方式見 generate_golden.py。 */
export interface Golden {
  readonly reference_time: string;
  readonly half_life_days: number;
  readonly min_diff: number;
  readonly grid: readonly { source_date: string; evergreen: boolean; score: number }[];
  readonly items: readonly (FreshnessRow & { seq: number })[];
  readonly expected_updates: Readonly<Record<string, number>>;
  readonly expected_skipped: number;
  readonly expected_evergreen: number;
  readonly expected_final: Readonly<Record<string, number | null>>;
}

const file = join(dirname(fileURLToPath(import.meta.url)), "../fixtures/freshness-parity/golden.json");

export const golden: Golden = JSON.parse(readFileSync(file, "utf-8"));
export const REFERENCE = new Date(golden.reference_time);
