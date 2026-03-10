/**
 * Timeseries Analyzer — anomaly detection for multi-week metric snapshots.
 *
 * Detects:
 * 1. Moving Average Deviation — value < MA(4w) * threshold
 * 2. Consecutive Decline — >= N consecutive weeks declining
 * 3. Trend Detection — linear regression slope significantly negative/positive
 */

// ── Types ──

export type AnomalySeverity = "info" | "warning" | "critical";
export type AnomalyType = "ma_deviation" | "consecutive_decline" | "trend";

export interface AnomalyResult {
  readonly metric: string;
  readonly type: AnomalyType;
  readonly severity: AnomalySeverity;
  readonly context: string;
}

export interface TimeseriesPoint {
  readonly date: string;
  readonly value: number;
}

export interface TrendResult {
  readonly slope: number;
  readonly direction: "rising" | "falling" | "stable";
  readonly r_squared: number;
}

// ── Constants ──

const MA_WINDOW = 4;
const MA_DEVIATION_THRESHOLD = 0.85; // value < MA * 0.85 → anomaly
const CONSECUTIVE_DECLINE_MIN = 3;
const TREND_SLOPE_THRESHOLD = 0.05; // |slope/mean| > 5% per period → significant

// ── Core Functions ──

/**
 * Compute simple moving average for the last `window` values.
 * Returns null if not enough data points.
 */
export function movingAverage(values: readonly number[], window: number = MA_WINDOW): number | null {
  if (values.length < window) return null;
  const slice = values.slice(-window);
  return slice.reduce((sum, v) => sum + v, 0) / window;
}

/**
 * Detect MA deviation: latest value significantly below moving average.
 */
export function detectMADeviation(
  metric: string,
  points: readonly TimeseriesPoint[],
): AnomalyResult | null {
  if (points.length < MA_WINDOW + 1) return null;

  const values = points.map((p) => p.value);
  // MA of the preceding values (excluding latest)
  const precedingValues = values.slice(0, -1);
  const ma = movingAverage(precedingValues, MA_WINDOW);
  if (ma === null || ma === 0) return null;

  const latest = values[values.length - 1]!;
  const ratio = latest / ma;

  if (ratio < MA_DEVIATION_THRESHOLD) {
    const dropPct = ((1 - ratio) * 100).toFixed(1);
    const severity: AnomalySeverity = ratio < 0.7 ? "critical" : "warning";
    return {
      metric,
      type: "ma_deviation",
      severity,
      context: `${metric} 最新值較 ${MA_WINDOW} 週移動平均低 ${dropPct}%（MA: ${ma.toFixed(1)}, 最新: ${latest.toFixed(1)}）`,
    };
  }

  return null;
}

/**
 * Detect consecutive decline: >= N consecutive weeks where value decreases.
 */
export function detectConsecutiveDecline(
  metric: string,
  points: readonly TimeseriesPoint[],
  minConsecutive: number = CONSECUTIVE_DECLINE_MIN,
): AnomalyResult | null {
  if (points.length < minConsecutive + 1) return null;

  const values = points.map((p) => p.value);
  let consecutiveDeclines = 0;
  let maxConsecutive = 0;

  for (let i = 1; i < values.length; i++) {
    if (values[i]! < values[i - 1]!) {
      consecutiveDeclines++;
      maxConsecutive = Math.max(maxConsecutive, consecutiveDeclines);
    } else {
      consecutiveDeclines = 0;
    }
  }

  if (maxConsecutive >= minConsecutive) {
    const severity: AnomalySeverity = maxConsecutive >= 5 ? "critical" : "warning";
    return {
      metric,
      type: "consecutive_decline",
      severity,
      context: `${metric} 連續 ${maxConsecutive} 週下滑`,
    };
  }

  return null;
}

/**
 * Simple linear regression: y = slope * x + intercept.
 * Returns slope, direction, and R-squared.
 */
export function linearTrend(points: readonly TimeseriesPoint[]): TrendResult | null {
  if (points.length < 3) return null;

  const n = points.length;
  const values = points.map((p) => p.value);

  // x = 0, 1, 2, ..., n-1
  let sumX = 0;
  let sumY = 0;
  let sumXY = 0;
  let sumX2 = 0;

  for (let i = 0; i < n; i++) {
    sumX += i;
    sumY += values[i]!;
    sumXY += i * values[i]!;
    sumX2 += i * i;
  }

  const denominator = n * sumX2 - sumX * sumX;
  if (denominator === 0) return null;

  const slope = (n * sumXY - sumX * sumY) / denominator;
  const mean = sumY / n;

  // R-squared
  const intercept = (sumY - slope * sumX) / n;
  let ssTot = 0;
  let ssRes = 0;
  for (let i = 0; i < n; i++) {
    const predicted = slope * i + intercept;
    ssTot += (values[i]! - mean) ** 2;
    ssRes += (values[i]! - predicted) ** 2;
  }
  const rSquared = ssTot === 0 ? 0 : 1 - ssRes / ssTot;

  // Normalize slope relative to mean
  const normalizedSlope = mean !== 0 ? slope / Math.abs(mean) : 0;

  let direction: TrendResult["direction"] = "stable";
  if (normalizedSlope > TREND_SLOPE_THRESHOLD) direction = "rising";
  if (normalizedSlope < -TREND_SLOPE_THRESHOLD) direction = "falling";

  return { slope, direction, r_squared: Math.max(0, rSquared) };
}

/**
 * Detect significant trend via linear regression.
 */
export function detectTrend(
  metric: string,
  points: readonly TimeseriesPoint[],
): AnomalyResult | null {
  const trend = linearTrend(points);
  if (!trend || trend.direction === "stable") return null;
  if (trend.r_squared < 0.5) return null; // Low confidence, skip

  if (trend.direction === "falling") {
    const severity: AnomalySeverity = trend.r_squared > 0.8 ? "critical" : "warning";
    return {
      metric,
      type: "trend",
      severity,
      context: `${metric} 呈下降趨勢（R²=${trend.r_squared.toFixed(2)}, slope=${trend.slope.toFixed(3)}/週）`,
    };
  }

  return {
    metric,
    type: "trend",
    severity: "info",
    context: `${metric} 呈上升趨勢（R²=${trend.r_squared.toFixed(2)}, slope=${trend.slope.toFixed(3)}/週）`,
  };
}

// ── Main Entry ──

/**
 * Analyze a metric's timeseries data for anomalies.
 * Runs all 3 detectors and returns combined results.
 */
export function analyzeTimeseries(
  metric: string,
  points: readonly TimeseriesPoint[],
): readonly AnomalyResult[] {
  if (points.length < 4) return [];

  const results: AnomalyResult[] = [];

  const maAnomaly = detectMADeviation(metric, points);
  if (maAnomaly) results.push(maAnomaly);

  const declineAnomaly = detectConsecutiveDecline(metric, points);
  if (declineAnomaly) results.push(declineAnomaly);

  const trendAnomaly = detectTrend(metric, points);
  if (trendAnomaly) results.push(trendAnomaly);

  return results;
}

/**
 * Analyze multiple metrics at once.
 * Input: Record<metricName, TimeseriesPoint[]>
 */
export function analyzeAllMetrics(
  metricsData: Readonly<Record<string, readonly TimeseriesPoint[]>>,
): readonly AnomalyResult[] {
  const allResults: AnomalyResult[] = [];

  for (const [metric, points] of Object.entries(metricsData)) {
    const anomalies = analyzeTimeseries(metric, points);
    allResults.push(...anomalies);
  }

  // Sort: critical first, then warning, then info
  const severityOrder: Record<AnomalySeverity, number> = { critical: 0, warning: 1, info: 2 };
  return [...allResults].sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);
}
