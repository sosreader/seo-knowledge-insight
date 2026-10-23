/**
 * freshness_score 計算（純函式）。
 *
 * 逐行對應 SKI Python 版 scripts/update_freshness.py（compute_freshness_score／_compute_updates）：
 *   score = exp(-ln2 * age_days / 540)；evergreen 一律 1.0；日期空白或無法解析視為 1.0（未知日期當作新鮮）；
 *   下限 0.01、四捨五入到 4 位；與現值差 ≤ 0.001 的列跳過。
 * 時間基準一律 UTC：age_days 是「參考時間 − 該日 00:00 UTC」取整天數（向下取整），與 Python 的 timedelta.days 相同。
 *
 * parity 由 tests/jobs/freshness.test.ts 對 tests/fixtures/freshness-parity/golden.json 驗證
 * （golden 由 Python 版實跑產生）。
 */

export const HALF_LIFE_DAYS = 540;
export const DECAY_RATE = Math.LN2 / HALF_LIFE_DAYS;
export const MIN_DIFF = 0.001;
export const SCORE_FLOOR = 0.01;
export const SCORE_DECIMALS = 4;

const DAY_MS = 86_400_000;
const DATE_PREFIX_LENGTH = 10;
const ISO_DAY = /^(\d{4})-(\d{2})-(\d{2})$/;

export interface FreshnessRow {
  readonly id: string;
  readonly source_date: string | null;
  readonly evergreen: boolean | null;
  readonly freshness_score: number | null;
}

export interface FreshnessUpdate {
  readonly id: string;
  readonly from: number | null;
  readonly to: number;
  readonly source_date: string | null;
}

export interface FreshnessPlan {
  readonly updates: readonly FreshnessUpdate[];
  readonly skipped: number;
  readonly evergreen: number;
}

export interface ScoreSummary {
  readonly count: number;
  readonly min: number | null;
  readonly avg: number | null;
  readonly max: number | null;
}

/** 'YYYY-MM-DD' → 該日 00:00 UTC 的 epoch ms；不是真實存在的日期（例如 2023-02-29）回 null。 */
function parseUtcDay(value: string): number | null {
  const m = ISO_DAY.exec(value);
  if (!m) return null;
  const [year, month, day] = [Number(m[1]), Number(m[2]), Number(m[3])];
  if (year < 1) return null;
  // setUTCFullYear 避開 Date.UTC 把 0–99 年當成 1900–1999 的行為
  const d = new Date(0);
  d.setUTCFullYear(year, month - 1, day);
  const valid = d.getUTCFullYear() === year && d.getUTCMonth() === month - 1 && d.getUTCDate() === day;
  return valid ? d.getTime() : null;
}

/** 四捨五入到 4 位（toFixed 以精確十進位展開取整，與 Python round() 在實際分數上一致）。 */
function roundScore(score: number): number {
  return Number(score.toFixed(SCORE_DECIMALS));
}

export function computeFreshnessScore(
  sourceDate: string | null | undefined,
  evergreen: boolean,
  reference: Date,
): number {
  if (evergreen) return 1;
  if (!sourceDate || sourceDate.length < DATE_PREFIX_LENGTH) return 1;
  const parsed = parseUtcDay(sourceDate.slice(0, DATE_PREFIX_LENGTH));
  if (parsed === null) return 1;
  const ageDays = Math.floor((reference.getTime() - parsed) / DAY_MS);
  if (ageDays <= 0) return 1;
  return roundScore(Math.max(Math.exp(-DECAY_RATE * ageDays), SCORE_FLOOR));
}

/** 與 Python `item.get("freshness_score", 1.0) or 1.0` 相同：NULL 與 0 都當 1.0。 */
function storedScore(row: FreshnessRow): number {
  return row.freshness_score || 1;
}

export function planUpdates(rows: readonly FreshnessRow[], reference: Date): FreshnessPlan {
  const updates: FreshnessUpdate[] = [];
  let skipped = 0;
  let evergreen = 0;
  for (const row of rows) {
    const isEvergreen = row.evergreen === true;
    const target = computeFreshnessScore(row.source_date, isEvergreen, reference);
    const current = storedScore(row);
    if (isEvergreen) evergreen += 1;
    if (Math.abs(target - current) > MIN_DIFF) {
      updates.push({ id: row.id, from: row.freshness_score, to: target, source_date: row.source_date });
    } else {
      skipped += 1;
    }
  }
  return { updates, skipped, evergreen };
}

/**
 * 套用更新後各列的分數（NULL 視為 1.0，與搜尋端 `?? 1.0` 一致）。
 * 回傳新陣列，不改動輸入。
 */
export function scoresAfter(rows: readonly FreshnessRow[], updates: readonly FreshnessUpdate[]): number[] {
  const target = new Map(updates.map((u) => [u.id, u.to]));
  return rows.map((row) => target.get(row.id) ?? row.freshness_score ?? 1);
}

export function summarizeScores(scores: readonly number[]): ScoreSummary {
  if (scores.length === 0) return { count: 0, min: null, avg: null, max: null };
  const sum = scores.reduce((acc, s) => acc + s, 0);
  return {
    count: scores.length,
    min: roundScore(Math.min(...scores)),
    avg: roundScore(sum / scores.length),
    max: roundScore(Math.max(...scores)),
  };
}
