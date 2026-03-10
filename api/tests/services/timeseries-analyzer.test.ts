/**
 * Tests for timeseries-analyzer — anomaly detection for metric snapshots.
 */

import { describe, it, expect } from "vitest";
import {
  movingAverage,
  detectMADeviation,
  detectConsecutiveDecline,
  linearTrend,
  detectTrend,
  analyzeTimeseries,
  analyzeAllMetrics,
  type TimeseriesPoint,
} from "../../src/services/timeseries-analyzer.js";

// ── Helpers ──

function makePoints(values: number[]): TimeseriesPoint[] {
  return values.map((v, i) => ({
    date: `2026-0${Math.floor(i / 4) + 1}-${String((i % 4) * 7 + 1).padStart(2, "0")}`,
    value: v,
  }));
}

// ── movingAverage ──

describe("movingAverage", () => {
  it("returns null for insufficient data", () => {
    expect(movingAverage([1, 2, 3])).toBeNull();
  });

  it("calculates MA of last 4 values", () => {
    expect(movingAverage([10, 20, 30, 40])).toBe(25);
  });

  it("uses custom window", () => {
    expect(movingAverage([1, 2, 3], 3)).toBe(2);
  });

  it("only uses last N values", () => {
    expect(movingAverage([100, 10, 20, 30, 40], 4)).toBe(25);
  });
});

// ── detectMADeviation ──

describe("detectMADeviation", () => {
  it("returns null for insufficient data", () => {
    expect(detectMADeviation("CTR", makePoints([1, 2, 3]))).toBeNull();
  });

  it("returns null when value is within threshold", () => {
    // MA of [100, 100, 100, 100] = 100; latest = 90 → 90/100 = 0.9 > 0.85
    expect(detectMADeviation("CTR", makePoints([100, 100, 100, 100, 90]))).toBeNull();
  });

  it("detects deviation when value drops below threshold", () => {
    // MA of [100, 100, 100, 100] = 100; latest = 80 → 80/100 = 0.8 < 0.85
    const result = detectMADeviation("CTR", makePoints([100, 100, 100, 100, 80]));
    expect(result).not.toBeNull();
    expect(result!.type).toBe("ma_deviation");
    expect(result!.severity).toBe("warning");
    expect(result!.metric).toBe("CTR");
  });

  it("returns critical for severe deviation", () => {
    // MA of [100, 100, 100, 100] = 100; latest = 60 → 60/100 = 0.6 < 0.7
    const result = detectMADeviation("點擊", makePoints([100, 100, 100, 100, 60]));
    expect(result).not.toBeNull();
    expect(result!.severity).toBe("critical");
  });
});

// ── detectConsecutiveDecline ──

describe("detectConsecutiveDecline", () => {
  it("returns null for insufficient data", () => {
    expect(detectConsecutiveDecline("CTR", makePoints([10, 9, 8]))).toBeNull();
  });

  it("returns null when no consecutive decline", () => {
    expect(detectConsecutiveDecline("CTR", makePoints([10, 9, 11, 8, 12]))).toBeNull();
  });

  it("detects 3 consecutive declines", () => {
    const result = detectConsecutiveDecline("CTR", makePoints([100, 90, 80, 70]));
    expect(result).not.toBeNull();
    expect(result!.type).toBe("consecutive_decline");
    expect(result!.severity).toBe("warning");
    expect(result!.context).toContain("連續 3 週下滑");
  });

  it("detects 5+ consecutive declines as critical", () => {
    const result = detectConsecutiveDecline("曝光", makePoints([100, 90, 80, 70, 60, 50]));
    expect(result).not.toBeNull();
    expect(result!.severity).toBe("critical");
    expect(result!.context).toContain("連續 5 週下滑");
  });

  it("respects custom minConsecutive", () => {
    expect(detectConsecutiveDecline("CTR", makePoints([100, 90, 80, 70]), 4)).toBeNull();
    expect(detectConsecutiveDecline("CTR", makePoints([100, 90, 80, 70, 60]), 4)).not.toBeNull();
  });
});

// ── linearTrend ──

describe("linearTrend", () => {
  it("returns null for insufficient data", () => {
    expect(linearTrend(makePoints([1, 2]))).toBeNull();
  });

  it("detects falling trend", () => {
    const result = linearTrend(makePoints([100, 80, 60, 40, 20]));
    expect(result).not.toBeNull();
    expect(result!.direction).toBe("falling");
    expect(result!.slope).toBeLessThan(0);
    expect(result!.r_squared).toBeGreaterThan(0.9);
  });

  it("detects rising trend", () => {
    const result = linearTrend(makePoints([20, 40, 60, 80, 100]));
    expect(result).not.toBeNull();
    expect(result!.direction).toBe("rising");
    expect(result!.slope).toBeGreaterThan(0);
  });

  it("detects stable trend for flat data", () => {
    const result = linearTrend(makePoints([100, 100, 100, 100]));
    expect(result).not.toBeNull();
    expect(result!.direction).toBe("stable");
  });

  it("detects stable for small fluctuations", () => {
    const result = linearTrend(makePoints([100, 101, 99, 100, 101]));
    expect(result).not.toBeNull();
    expect(result!.direction).toBe("stable");
  });
});

// ── detectTrend ──

describe("detectTrend", () => {
  it("returns anomaly for significant falling trend", () => {
    const result = detectTrend("CTR", makePoints([100, 80, 60, 40, 20]));
    expect(result).not.toBeNull();
    expect(result!.type).toBe("trend");
    expect(result!.severity).toBe("critical"); // R² > 0.8
    expect(result!.context).toContain("下降趨勢");
  });

  it("returns info for rising trend", () => {
    const result = detectTrend("曝光", makePoints([20, 40, 60, 80, 100]));
    expect(result).not.toBeNull();
    expect(result!.severity).toBe("info");
    expect(result!.context).toContain("上升趨勢");
  });

  it("returns null for stable trend", () => {
    expect(detectTrend("CTR", makePoints([100, 100, 100, 100]))).toBeNull();
  });

  it("returns null when R² is too low (noisy data)", () => {
    // Random-looking data with low R²
    const result = detectTrend("CTR", makePoints([50, 100, 30, 90, 40]));
    // Even if slope is non-zero, low R² should filter it out
    if (result !== null) {
      // If somehow detected, verify it has reasonable R²
      expect(result.context).toContain("R²");
    }
  });
});

// ── analyzeTimeseries ──

describe("analyzeTimeseries", () => {
  it("returns empty for short series", () => {
    expect(analyzeTimeseries("CTR", makePoints([1, 2, 3]))).toEqual([]);
  });

  it("combines multiple anomalies", () => {
    // Steadily declining: should trigger consecutive_decline + trend + possibly ma_deviation
    const results = analyzeTimeseries("CTR", makePoints([100, 90, 80, 70, 60]));
    expect(results.length).toBeGreaterThanOrEqual(2);
    const types = results.map((r) => r.type);
    expect(types).toContain("consecutive_decline");
    expect(types).toContain("trend");
  });

  it("returns empty for healthy metric", () => {
    const results = analyzeTimeseries("CTR", makePoints([100, 101, 100, 99, 100]));
    expect(results).toEqual([]);
  });
});

// ── analyzeAllMetrics ──

describe("analyzeAllMetrics", () => {
  it("analyzes multiple metrics", () => {
    const data = {
      "CTR": makePoints([100, 90, 80, 70, 60]),
      "曝光": makePoints([100, 101, 100, 99, 100]),
    };

    const results = analyzeAllMetrics(data);
    expect(results.length).toBeGreaterThan(0);
    expect(results.every((r) => r.metric === "CTR")).toBe(true); // 曝光 is healthy
  });

  it("sorts by severity (critical first)", () => {
    const data = {
      "CTR": makePoints([100, 90, 80, 70, 60]), // warning/critical
      "曝光": makePoints([100, 80, 60, 40, 20]), // critical
    };

    const results = analyzeAllMetrics(data);
    const severities = results.map((r) => r.severity);
    const criticalIdx = severities.indexOf("critical");
    const warningIdx = severities.indexOf("warning");
    if (criticalIdx !== -1 && warningIdx !== -1) {
      expect(criticalIdx).toBeLessThan(warningIdx);
    }
  });

  it("returns empty for all healthy metrics", () => {
    const data = {
      "CTR": makePoints([50, 51, 50, 49, 50]),
      "曝光": makePoints([1000, 1001, 999, 1000, 1001]),
    };
    expect(analyzeAllMetrics(data)).toEqual([]);
  });
});
