import { describe, it, expect, vi, beforeEach } from "vitest";
import { generateReportLocal, getAlertMetricNames } from "../../src/services/report-generator-local.js";

// Mock qaStore to avoid file-system dependency
vi.mock("../../src/store/qa-store.js", () => ({
  qaStore: {
    loaded: true,
    count: 100,
    load: vi.fn(),
    keywordSearch: vi.fn().mockReturnValue([]),
  },
}));

// Mock config paths
vi.mock("../../src/config.js", () => ({
  paths: {
    rootDir: "/tmp/test",
    outputDir: "/tmp/test/output",
    qaJsonPath: "/tmp/test/qa.json",
    scriptsDir: "/tmp/test/scripts",
    metricsSnapshotsDir: "/tmp/test/snapshots",
  },
}));

describe("report-generator-local", () => {
  // Note: CORE_METRICS (AMP Article, CTR, etc.) always get flag="CORE", not ALERT_DOWN.
  // To test upgrade labels on action items, include non-CORE metrics that:
  //  1. trigger ALERT_DOWN (monthly < -15% or weekly < -20%)
  //  2. substring-match a METRIC_MATURITY_DIMENSION_MAP key
  const baseMetrics = {
    "AMP Article": { latest: 100, monthly: -0.5, weekly: -0.3 },
    "CTR": { latest: 0.05, monthly: -0.02, weekly: -0.01 },
    "曝光": { latest: 50000, monthly: 0.05, weekly: 0.02 },
    "點擊": { latest: 2500, monthly: -0.03, weekly: -0.01 },
    "有效 (Coverage)": { latest: 5000, monthly: 0.01, weekly: 0.0 },
    "Organic Search (工作階段)": { latest: 10000, monthly: 0.03, weekly: 0.01 },
    // Non-CORE metric that triggers ALERT_DOWN + maps to "process" via "AMP Article" substring
    "AMP Article 內頁": { latest: 50, monthly: -0.4, weekly: -0.25 },
  };

  const maturity = {
    strategy: "L2",
    process: "L2",
    keywords: "L3",
    metrics: "L2",
  };

  describe("maturity callout placement", () => {
    it("inserts callout before high priority actions when maturity is present", async () => {
      const report = await generateReportLocal(
        baseMetrics,
        "2026/03/16",
        100,
        null,
        1,
        null,
        maturity,
      );

      const section5Start = report.indexOf("## 五、本週優先行動清單");
      const calloutPos = report.indexOf("> 成熟度參考：");
      const highPriorityPos = report.indexOf("**高優先（需立即處理）**");

      expect(section5Start).toBeGreaterThan(-1);
      expect(calloutPos).toBeGreaterThan(section5Start);
      expect(calloutPos).toBeLessThan(highPriorityPos);
    });

    it("does not include callout when maturity is null", async () => {
      const report = await generateReportLocal(
        baseMetrics,
        "2026/03/16",
        100,
        null,
        1,
        null,
        null,
      );

      expect(report).not.toContain("> 成熟度參考：");
    });
  });

  describe("maturity upgrade labels on actions", () => {
    it("adds upgrade label to AMP Article down action", async () => {
      const report = await generateReportLocal(
        baseMetrics,
        "2026/03/16",
        100,
        null,
        1,
        null,
        maturity,
      );

      // "AMP Article 內頁" substring-matches "AMP Article" → "process", maturity.process = L2
      expect(report).toContain("**[流程 L2→L3]**");
    });

    it("does not add upgrade label when maturity is null (zero regression)", async () => {
      const report = await generateReportLocal(
        baseMetrics,
        "2026/03/16",
        100,
        null,
        1,
        null,
        null,
      );

      expect(report).not.toContain("**[");
      expect(report).not.toContain("→L");
    });

    it("does not add label for L4 dimension", async () => {
      const maturityWithL4 = { ...maturity, process: "L4" };
      const report = await generateReportLocal(
        baseMetrics,
        "2026/03/16",
        100,
        null,
        1,
        null,
        maturityWithL4,
      );

      // "AMP Article 內頁" maps to "process", but process is L4 — no upgrade label
      expect(report).not.toContain("**[流程");
    });
  });

  describe("old maturity block removal", () => {
    it("does not contain the old maturity heading", async () => {
      const report = await generateReportLocal(
        baseMetrics,
        "2026/03/16",
        100,
        null,
        1,
        null,
        maturity,
      );

      // Old format had "### 成熟度對標" heading with buildReportMaturityBlock
      expect(report).not.toContain("### 成熟度對標");
    });
  });

  describe("getAlertMetricNames", () => {
    it("returns alert metric names", () => {
      const names = getAlertMetricNames(baseMetrics);
      expect(names).toContain("AMP Article");
      expect(names).toContain("CTR");
    });
  });
});
