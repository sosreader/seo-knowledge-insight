import { describe, expect, it } from "vitest";
import {
  DECAY_RATE,
  HALF_LIFE_DAYS,
  MIN_DIFF,
  computeFreshnessScore,
  planUpdates,
  scoresAfter,
  summarizeScores,
} from "../../src/jobs/freshness.js";
import { REFERENCE, golden } from "./golden.js";

describe("constants match the Python version", () => {
  it("uses a 540-day half life and 0.001 skip threshold", () => {
    expect(HALF_LIFE_DAYS).toBe(golden.half_life_days);
    expect(MIN_DIFF).toBe(golden.min_diff);
    expect(DECAY_RATE).toBeCloseTo(Math.LN2 / 540, 15);
  });
});

describe("computeFreshnessScore parity with Python (golden)", () => {
  it("matches every grid point exactly", () => {
    expect(golden.grid.length).toBeGreaterThan(500);
    const mismatches = golden.grid
      .map((g) => ({ g, actual: computeFreshnessScore(g.source_date, g.evergreen, REFERENCE) }))
      .filter(({ g, actual }) => actual !== g.score);
    expect(mismatches).toEqual([]);
  });
});

describe("computeFreshnessScore branches", () => {
  const ref = new Date("2026-10-26T02:00:00Z");

  it("evergreen is always 1.0", () => {
    expect(computeFreshnessScore("2000-01-01", true, ref)).toBe(1);
  });

  it("unknown or malformed dates are treated as fresh", () => {
    for (const value of ["", null, undefined, "2024", "abcdefghij", "2024-13-45", "2023-02-29", "0000-01-01", "2024-5-1 ab"]) {
      expect(computeFreshnessScore(value, false, ref)).toBe(1);
    }
  });

  it("today and future dates score 1.0", () => {
    expect(computeFreshnessScore("2026-10-26", false, ref)).toBe(1);
    expect(computeFreshnessScore("2099-01-01", false, ref)).toBe(1);
  });

  it("accepts a leap day and ignores anything after the first 10 characters", () => {
    expect(computeFreshnessScore("2024-02-29", false, ref)).toBeLessThan(1);
    expect(computeFreshnessScore("2024-05-01T12:00:00Z", false, ref)).toBe(computeFreshnessScore("2024-05-01", false, ref));
  });

  it("is 0.5 at the half life and floors at 0.01", () => {
    expect(computeFreshnessScore("2025-05-04", false, ref)).toBe(0.5);
    expect(computeFreshnessScore("2000-01-01", false, ref)).toBe(0.01);
  });

  it("uses whole UTC days regardless of the time of day", () => {
    const morning = new Date("2026-10-26T00:00:01Z");
    const night = new Date("2026-10-26T23:59:59Z");
    expect(computeFreshnessScore("2026-10-25", false, morning)).toBe(computeFreshnessScore("2026-10-25", false, night));
  });
});

describe("planUpdates parity with Python _compute_updates (golden)", () => {
  const plan = planUpdates(golden.items, REFERENCE);

  it("selects exactly the rows Python selects, with the same scores", () => {
    expect(Object.fromEntries(plan.updates.map((u) => [u.id, u.to]))).toEqual(golden.expected_updates);
  });

  it("counts skipped and evergreen rows like Python", () => {
    expect(plan.skipped).toBe(golden.expected_skipped);
    expect(plan.evergreen).toBe(golden.expected_evergreen);
  });

  it("does not mutate its input", () => {
    const before = JSON.stringify(golden.items);
    planUpdates(golden.items, REFERENCE);
    expect(JSON.stringify(golden.items)).toBe(before);
  });
});

describe("scoresAfter / summarizeScores", () => {
  it("applies updates without touching other rows and treats NULL as 1.0", () => {
    const rows = [
      { id: "a", source_date: "2020-01-01", evergreen: false, freshness_score: 1 },
      { id: "b", source_date: null, evergreen: false, freshness_score: null },
      { id: "c", source_date: "2020-01-01", evergreen: false, freshness_score: 0.4 },
    ];
    const after = scoresAfter(rows, [{ id: "a", from: 1, to: 0.25, source_date: "2020-01-01" }]);
    expect(after).toEqual([0.25, 1, 0.4]);
    expect(rows[0]!.freshness_score).toBe(1);
  });

  it("summarizes min / avg / max and handles empty input", () => {
    expect(summarizeScores([0.2, 0.4, 1])).toEqual({ count: 3, min: 0.2, avg: 0.5333, max: 1 });
    expect(summarizeScores([])).toEqual({ count: 0, min: null, avg: null, max: null });
  });
});
