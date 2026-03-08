import { describe, it, expect } from "vitest";
import { evaluateCrawledNotIndexedAnalysis } from "../../src/services/crawled-not-indexed-evaluator.js";
import { parseCrawledNotIndexedTsv } from "../../src/services/crawled-not-indexed-parser.js";
import { analyzeCrawledNotIndexed } from "../../src/services/crawled-not-indexed-analyzer.js";

const SAMPLE_TSV = [
  "全網域\t19.69%\t0\t1,014,769\t409,827\t\t843,969",
  "檢索未索引 (全部)\t32.19%\t0\t715,813\t46,287\t\t433,875",
  "/article/\t52.59%\t0\t374,127\t12,604\t\t99,887",
  "/en/\t-31.51%\t0\t22,891\t950\t\t950",
  "/post\t49.79%\t1\t2,461\t446\t\t2,461",
  "/salon/\t133.71%\t0\t94,803\t11,659\t\t94,803",
  "/tag/\t-11.99%\t0\t34,171\t10,625\t\t27,020",
  "/user/\t-3.05%\t0\t4,197\t1,352\t\t3,391",
  "總合\t61.99%\t-1\t442,033\t42,819\t\t",
  "總合/全網域\t44.66%\t-1\t43.56%\t10.45%\t\t",
  "差距\t\t\t\t\t\t",
].join("\n");

describe("evaluateCrawledNotIndexedAnalysis", () => {
  const data = parseCrawledNotIndexedTsv(SAMPLE_TSV);

  it("returns zero scores for empty content", () => {
    const result = evaluateCrawledNotIndexedAnalysis("", data);
    expect(result.overall).toBe(0);
    expect(result.path_coverage).toBe(0);
  });

  it("scores well for analyzer-generated markdown", () => {
    const insight = analyzeCrawledNotIndexed(data);
    const result = evaluateCrawledNotIndexedAnalysis(insight.markdown, data);
    expect(result.path_coverage).toBeGreaterThanOrEqual(0.8);
    expect(result.has_severity_assessment).toBe(1);
    expect(result.overall).toBeGreaterThan(0.5);
  });

  it("detects path coverage correctly", () => {
    const partialContent = "分析 /article/ 和 /salon/ 的索引問題，需要檢查 GSC";
    const result = evaluateCrawledNotIndexedAnalysis(partialContent, data);
    // Only 2 of 6 paths mentioned
    expect(result.path_coverage).toBeCloseTo(2 / 6, 1);
  });

  it("detects severity assessment", () => {
    const withSeverity = "索引狀態：警示。/article/ 惡化嚴重。建議檢查 GSC。";
    const result = evaluateCrawledNotIndexedAnalysis(withSeverity, data);
    expect(result.has_severity_assessment).toBe(1);

    const withoutSeverity = "一些路徑的資料如下。";
    const result2 = evaluateCrawledNotIndexedAnalysis(withoutSeverity, data);
    expect(result2.has_severity_assessment).toBe(0);
  });

  it("scores recommendation specificity", () => {
    const insight = analyzeCrawledNotIndexed(data);
    const result = evaluateCrawledNotIndexedAnalysis(insight.markdown, data);
    expect(result.recommendation_specificity).toBeGreaterThan(0);
  });

  it("handles data with no paths", () => {
    const emptyData = parseCrawledNotIndexedTsv("全網域\t10%\t0\t100\t50\t\t80");
    const result = evaluateCrawledNotIndexedAnalysis("全網域分析", emptyData);
    // No paths to check → defaults to 1
    expect(result.path_coverage).toBe(1);
  });
});
