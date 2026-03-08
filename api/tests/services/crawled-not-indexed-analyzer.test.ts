import { describe, it, expect } from "vitest";
import { analyzeCrawledNotIndexed, buildCrawledNotIndexedContext } from "../../src/services/crawled-not-indexed-analyzer.js";
import { parseCrawledNotIndexedTsv } from "../../src/services/crawled-not-indexed-parser.js";

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

describe("analyzeCrawledNotIndexed", () => {
  const data = parseCrawledNotIndexedTsv(SAMPLE_TSV);

  it("returns critical severity when paths have >50% increase", () => {
    const insight = analyzeCrawledNotIndexed(data);
    expect(insight.overall_severity).toBe("critical");
  });

  it("identifies worsening paths correctly", () => {
    const insight = analyzeCrawledNotIndexed(data);
    expect(insight.worsening_paths.length).toBeGreaterThan(0);
    const segments = insight.worsening_paths.map((p) => p.segment);
    expect(segments).toContain("/salon/");
    expect(segments).toContain("/article/");
  });

  it("identifies improving paths correctly", () => {
    const insight = analyzeCrawledNotIndexed(data);
    const segments = insight.improving_paths.map((p) => p.segment);
    expect(segments).toContain("/en/");
  });

  it("sorts worsening by change_pct descending", () => {
    const insight = analyzeCrawledNotIndexed(data);
    for (let i = 1; i < insight.worsening_paths.length; i++) {
      expect(insight.worsening_paths[i - 1]!.change_pct)
        .toBeGreaterThanOrEqual(insight.worsening_paths[i]!.change_pct);
    }
  });

  it("provides path-specific recommendations", () => {
    const insight = analyzeCrawledNotIndexed(data);
    const salon = insight.worsening_paths.find((p) => p.segment === "/salon/");
    expect(salon?.recommendation).toContain("UGC");
    const tag = insight.stable_paths.find((p) => p.segment === "/tag/") ??
      insight.improving_paths.find((p) => p.segment === "/tag/");
    // /tag/ has -11.99% so it's improving
    expect(tag?.recommendation).toContain("tag") ;
  });

  it("includes domain and not_indexed change percentages", () => {
    const insight = analyzeCrawledNotIndexed(data);
    expect(insight.domain_change_pct).toBeCloseTo(0.1969);
    expect(insight.not_indexed_change_pct).toBeCloseTo(0.3219);
  });

  it("generates non-empty summary_text", () => {
    const insight = analyzeCrawledNotIndexed(data);
    expect(insight.summary_text.length).toBeGreaterThan(10);
    expect(insight.summary_text).toContain("警示");
  });

  it("generates markdown with section heading", () => {
    const insight = analyzeCrawledNotIndexed(data);
    expect(insight.markdown).toContain("## 檢索未索引分析");
    expect(insight.markdown).toContain("惡化路徑");
    expect(insight.markdown).toContain("行動建議");
  });

  it("handles empty data gracefully", () => {
    const empty = parseCrawledNotIndexedTsv("");
    const insight = analyzeCrawledNotIndexed(empty);
    expect(insight.overall_severity).toBe("stable");
    expect(insight.worsening_paths).toHaveLength(0);
    expect(insight.markdown).toContain("穩定");
  });
});

describe("buildCrawledNotIndexedContext", () => {
  it("returns markdown table with all rows", () => {
    const data = parseCrawledNotIndexedTsv(SAMPLE_TSV);
    const ctx = buildCrawledNotIndexedContext(data);
    expect(ctx).toContain("| 路徑 |");
    expect(ctx).toContain("/article/");
    expect(ctx).toContain("全網域");
    expect(ctx).toContain("domain");
    expect(ctx).toContain("path");
  });
});
