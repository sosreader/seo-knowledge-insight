/**
 * update-freshness：週更 app_qa_item.freshness_score（取代 SKI 的 GitHub workflow update-freshness.yml，
 * 該 workflow 寫 Supabase qa_items；本實作寫 vocus-warehouse RDS，由 K8s CronJob 執行）。
 *
 * 權限：連線身分是 warehouse_rag，對 app_qa_item 只有 SELECT 與 UPDATE (search_hit_count, freshness_score)
 * （vocus-warehouse db/roles-matrix.md）。本檔只 UPDATE freshness_score，不碰 updated_at 與其他欄。
 *
 * 流程：讀取（可選 --since／--limit）→ 在記憶體算出要改的列（freshness.ts，與 Python 版一致）→
 * 非 dry-run 才分批 UPDATE（100 列一批，一批一個 UPDATE ... FROM unnest）→ 讀回驗證。
 * 一批失敗不中斷其他批（DB 連不上除外：直接放棄剩餘批次），最後 failed > 0 由呼叫端轉成非零 exit code。
 */

import { pgQuery, pgQueryResult } from "../store/pg-client.js";
import { DbUnavailableError } from "../store/store-errors.js";
import {
  type FreshnessRow,
  type FreshnessUpdate,
  type ScoreSummary,
  planUpdates,
  scoresAfter,
  summarizeScores,
} from "./freshness.js";

export const BATCH_SIZE = 100;
const READ_TIMEOUT_MS = 120_000;
const WRITE_TIMEOUT_MS = 60_000;
const SAMPLE_SIZE = 5;
/** Python verify 的檢查範圍：2024-01-01 之前、非 evergreen 的列分數不該還停在 1.0。 */
const LEGACY_CUTOFF = "2024-01-01";
const LEGACY_FLOOR = "1900-01-01";

export interface UpdateFreshnessOptions {
  readonly dryRun: boolean;
  /** YYYY-MM-DD；只處理 source_date >= since 的列。 */
  readonly since?: string;
  /** 只處理前 N 列（依 seq）；0 或省略 = 全部。 */
  readonly limit?: number;
  /** 參考時間；省略 = 現在（UTC）。測試用。 */
  readonly now?: Date;
  readonly batchSize?: number;
}

export interface Readback {
  readonly table_rows: number;
  readonly min: number | null;
  readonly avg: number | null;
  readonly max: number | null;
  /** 非 evergreen、source_date 在 2024-01-01 以前、分數仍 >= 1.0 的列數（Python --verify 的檢查，應為 0 或極少）。 */
  readonly legacy_at_full_score: number;
}

export interface UpdateFreshnessResult {
  readonly dry_run: boolean;
  readonly reference_time: string;
  readonly since: string | null;
  readonly limit: number;
  readonly processed: number;
  readonly evergreen: number;
  readonly need_update: number;
  readonly skipped: number;
  readonly updated: number;
  readonly failed: number;
  readonly distribution: { readonly before: ScoreSummary; readonly planned_after: ScoreSummary };
  readonly sample: readonly { id: string; source_date: string | null; from: number | null; to: number }[];
  readonly readback: Readback | null;
  readonly duration_ms: number;
}

interface RawRow {
  id: string;
  source_date: string | null;
  evergreen: boolean | null;
  freshness_score: number | null;
}

const SELECT_SQL = `
  SELECT id, source_date, evergreen, freshness_score
    FROM app_qa_item
   WHERE ($1::text IS NULL OR source_date >= $1::text)
   ORDER BY seq ASC, id ASC
   LIMIT $2::int`;

const UPDATE_SQL = `
  UPDATE app_qa_item AS t
     SET freshness_score = v.score
    FROM unnest($1::text[], $2::float8[]) AS v(id, score)
   WHERE t.id = v.id`;

const READBACK_SQL = `
  SELECT count(*)::int AS table_rows,
         min(freshness_score)::float8 AS min,
         avg(freshness_score)::float8 AS avg,
         max(freshness_score)::float8 AS max,
         (count(*) FILTER (
            WHERE evergreen = false
              AND source_date >= $1 AND source_date < $2
              AND freshness_score >= 1.0))::int AS legacy_at_full_score
    FROM app_qa_item`;

async function fetchRows(since: string | undefined, limit: number): Promise<FreshnessRow[]> {
  // freshness_score 是 real：不要在 SQL 轉 float8，否則 0.2625 會變成 0.26249998807907104
  const rows = await pgQuery<RawRow>(SELECT_SQL, [since ?? null, limit > 0 ? limit : null], {
    timeoutMs: READ_TIMEOUT_MS,
  });
  return rows.map((r) => ({
    id: r.id,
    source_date: r.source_date,
    evergreen: r.evergreen,
    freshness_score: r.freshness_score === null ? null : Number(r.freshness_score),
  }));
}

function chunk<T>(items: readonly T[], size: number): T[][] {
  return Array.from({ length: Math.ceil(items.length / size) }, (_, i) => items.slice(i * size, (i + 1) * size));
}

async function writeBatch(batch: readonly FreshnessUpdate[]): Promise<number> {
  const result = await pgQueryResult(
    UPDATE_SQL,
    [batch.map((u) => u.id), batch.map((u) => u.to)],
    { timeoutMs: WRITE_TIMEOUT_MS },
  );
  return result.rowCount ?? 0;
}

interface WriteOutcome {
  readonly updated: number;
  readonly failed: number;
}

async function writeAll(updates: readonly FreshnessUpdate[], batchSize: number): Promise<WriteOutcome> {
  const batches = chunk(updates, batchSize);
  let updated = 0;
  let failed = 0;
  for (const [index, batch] of batches.entries()) {
    try {
      updated += await writeBatch(batch);
    } catch (err) {
      const remaining = batches.slice(index).reduce((n, b) => n + b.length, 0);
      if (err instanceof DbUnavailableError) {
        // 連線層級故障：後面的批次只會逐批等連線逾時，直接放棄
        failed += remaining;
        break;
      }
      failed += batch.length;
    }
  }
  return { updated, failed };
}

async function readback(): Promise<Readback> {
  const [row] = await pgQuery<{
    table_rows: number;
    min: number | null;
    avg: number | null;
    max: number | null;
    legacy_at_full_score: number;
  }>(READBACK_SQL, [LEGACY_FLOOR, LEGACY_CUTOFF], { timeoutMs: READ_TIMEOUT_MS });
  const round = (v: number | null): number | null => (v === null ? null : Number(Number(v).toFixed(4)));
  return {
    table_rows: row?.table_rows ?? 0,
    min: round(row?.min ?? null),
    avg: round(row?.avg ?? null),
    max: round(row?.max ?? null),
    legacy_at_full_score: row?.legacy_at_full_score ?? 0,
  };
}

export async function updateFreshness(options: UpdateFreshnessOptions): Promise<UpdateFreshnessResult> {
  const started = Date.now();
  const reference = options.now ?? new Date();
  const limit = options.limit ?? 0;

  const rows = await fetchRows(options.since, limit);
  const plan = planUpdates(rows, reference);
  const base = {
    dry_run: options.dryRun,
    reference_time: reference.toISOString(),
    since: options.since ?? null,
    limit,
    processed: rows.length,
    evergreen: plan.evergreen,
    need_update: plan.updates.length,
    skipped: plan.skipped,
    distribution: {
      before: summarizeScores(rows.map((r) => r.freshness_score ?? 1)),
      planned_after: summarizeScores(scoresAfter(rows, plan.updates)),
    },
    sample: plan.updates.slice(0, SAMPLE_SIZE).map((u) => ({
      id: u.id,
      source_date: u.source_date,
      from: u.from,
      to: u.to,
    })),
  };

  if (options.dryRun) {
    return { ...base, updated: 0, failed: 0, readback: null, duration_ms: Date.now() - started };
  }

  const outcome = await writeAll(plan.updates, options.batchSize ?? BATCH_SIZE);
  const back = await readback();
  return { ...base, ...outcome, readback: back, duration_ms: Date.now() - started };
}
