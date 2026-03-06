import { describe, it, expect } from "vitest";
import { parseMetricsTsv, detectAnomalies } from "../../src/services/metrics-parser.js";

const SAMPLE_TSV = [
  "\t月趨勢\t上週\tMax\tMin\tSparklines\t2/28/2026\t2/21/2026",
  "曝光\t-3.61%\t-26.09%\t65,358,724\t48,305,965\t\t48,305,965\t65,358,724",
  "點擊\t5.00%\t10.00%\t1,000,000\t500,000\t\t900,000\t800,000",
  "CTR\t#N/A\t#N/A\t#N/A\t#N/A\t\t#N/A\t#N/A",
  "外部連結\t30.00%\t-5.00%\t200\t100\t\t180\t150",
  "小指標\t2.00%\t3.00%\t50\t10\t\t40\t35",
  "Sparklines\t\t\t\t\t\t\t",
].join("\n");

describe("parseMetricsTsv", () => {
  it("parses header dates and metric rows", () => {
    const result = parseMetricsTsv(SAMPLE_TSV);
    expect(result["曝光"]).toBeDefined();
    expect(result["曝光"].monthly).toBeCloseTo(-0.0361);
    expect(result["曝光"].weekly).toBeCloseTo(-0.2609);
    expect(result["曝光"].max).toBe(65358724);
    expect(result["曝光"].latest).toBe(48305965);
    expect(result["曝光"].latest_date).toBe("2/28/2026");
    expect(result["曝光"].previous_date).toBe("2/21/2026");
  });

  it("parses numeric values with commas", () => {
    const result = parseMetricsTsv(SAMPLE_TSV);
    expect(result["點擊"].max).toBe(1000000);
    expect(result["點擊"].latest).toBe(900000);
  });

  it("handles #N/A as null", () => {
    const result = parseMetricsTsv(SAMPLE_TSV);
    expect(result["CTR"].monthly).toBeNull();
    expect(result["CTR"].weekly).toBeNull();
    expect(result["CTR"].max).toBeNull();
  });

  it("skips Sparklines row", () => {
    const result = parseMetricsTsv(SAMPLE_TSV);
    expect(result["Sparklines"]).toBeUndefined();
  });

  it("returns empty for empty input", () => {
    expect(parseMetricsTsv("")).toEqual({});
    expect(parseMetricsTsv("  \n  ")).toEqual({});
  });
});

describe("detectAnomalies", () => {
  it("flags CORE metrics regardless of trend", () => {
    const metrics = parseMetricsTsv(SAMPLE_TSV);
    const anomalies = detectAnomalies(metrics);
    const coreNames = anomalies.filter((a) => a.flag === "CORE").map((a) => a.name);
    expect(coreNames).toContain("曝光");
    expect(coreNames).toContain("點擊");
    expect(coreNames).toContain("CTR");
  });

  it("flags ALERT_UP for large positive monthly trend", () => {
    const metrics = parseMetricsTsv(SAMPLE_TSV);
    const anomalies = detectAnomalies(metrics);
    const alertUp = anomalies.find((a) => a.name === "外部連結");
    expect(alertUp).toBeDefined();
    expect(alertUp!.flag).toBe("ALERT_UP");
  });

  it("does not flag small metrics", () => {
    const metrics = parseMetricsTsv(SAMPLE_TSV);
    const anomalies = detectAnomalies(metrics);
    const small = anomalies.find((a) => a.name === "小指標");
    expect(small).toBeUndefined();
  });

  it("returns immutable array", () => {
    const metrics = parseMetricsTsv(SAMPLE_TSV);
    const anomalies = detectAnomalies(metrics);
    expect(Array.isArray(anomalies)).toBe(true);
  });
});
