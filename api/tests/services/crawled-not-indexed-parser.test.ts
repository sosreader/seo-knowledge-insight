import { describe, it, expect } from "vitest";
import { parseIndexingTsv } from "../../src/services/indexing-parser.js";

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

const SAMPLE_WITH_HEADER = [
  "\t變化率\t差異\t總頁數\t未索引\tSparklines\t基準值",
  ...SAMPLE_TSV.split("\n"),
].join("\n");

describe("parseIndexingTsv", () => {
  it("parses domain row", () => {
    const result = parseIndexingTsv(SAMPLE_TSV);
    expect(result.domain).not.toBeNull();
    expect(result.domain!.segment).toBe("全網域");
    expect(result.domain!.change_pct).toBeCloseTo(0.1969);
    expect(result.domain!.delta).toBe(0);
    expect(result.domain!.value_a).toBe(1014769);
    expect(result.domain!.value_b).toBe(409827);
    expect(result.domain!.baseline).toBe(843969);
  });

  it("parses not_indexed_total row", () => {
    const result = parseIndexingTsv(SAMPLE_TSV);
    expect(result.not_indexed_total).not.toBeNull();
    expect(result.not_indexed_total!.segment).toBe("檢索未索引 (全部)");
    expect(result.not_indexed_total!.change_pct).toBeCloseTo(0.3219);
    expect(result.not_indexed_total!.value_a).toBe(715813);
  });

  it("parses path rows", () => {
    const result = parseIndexingTsv(SAMPLE_TSV);
    expect(result.paths).toHaveLength(6);
    const article = result.paths.find((p) => p.segment === "/article/");
    expect(article).toBeDefined();
    expect(article!.change_pct).toBeCloseTo(0.5259);
    expect(article!.value_a).toBe(374127);
    expect(article!.value_b).toBe(12604);
    expect(article!.baseline).toBe(99887);
  });

  it("parses negative trends correctly", () => {
    const result = parseIndexingTsv(SAMPLE_TSV);
    const en = result.paths.find((p) => p.segment === "/en/");
    expect(en!.change_pct).toBeCloseTo(-0.3151);
    const tag = result.paths.find((p) => p.segment === "/tag/");
    expect(tag!.change_pct).toBeCloseTo(-0.1199);
  });

  it("parses summary rows", () => {
    const result = parseIndexingTsv(SAMPLE_TSV);
    expect(result.sum).not.toBeNull();
    expect(result.sum!.segment).toBe("總合");
    expect(result.sum!.change_pct).toBeCloseTo(0.6199);
    expect(result.sum!.delta).toBe(-1);

    expect(result.ratio).not.toBeNull();
    expect(result.ratio!.segment).toBe("總合/全網域");
    expect(result.ratio!.change_pct).toBeCloseTo(0.4466);

    expect(result.gap).not.toBeNull();
    expect(result.gap!.segment).toBe("差距");
  });

  it("handles header row correctly", () => {
    const result = parseIndexingTsv(SAMPLE_WITH_HEADER);
    expect(result.domain).not.toBeNull();
    expect(result.paths).toHaveLength(6);
    expect(result.domain!.change_pct).toBeCloseTo(0.1969);
  });

  it("returns empty result for empty input", () => {
    const result = parseIndexingTsv("");
    expect(result.domain).toBeNull();
    expect(result.paths).toHaveLength(0);
    expect(result.all_rows).toHaveLength(0);
  });

  it("returns all_rows with correct count", () => {
    const result = parseIndexingTsv(SAMPLE_TSV);
    // domain + not_indexed_total + 6 paths + sum + ratio + gap = 11
    expect(result.all_rows).toHaveLength(11);
  });

  it("classifies row_type correctly for all rows", () => {
    const result = parseIndexingTsv(SAMPLE_TSV);
    const types = result.all_rows.map((r) => r.row_type);
    expect(types).toContain("domain");
    expect(types).toContain("not_indexed_total");
    expect(types).toContain("path");
    expect(types).toContain("sum");
    expect(types).toContain("ratio");
    expect(types).toContain("gap");
  });

  it("extracts indexing section from full sheet with preceding metrics", () => {
    // Simulate full sheet: header + main metrics + indexing section at bottom
    const fullSheet = [
      "\t月趨勢\t上週\tMax\tMin\tSparklines\t3/6/2026",
      "曝光\t-3.61%\t-26.09%\t65,358,724\t48,305,965\t\t48,305,965",
      "點擊\t5.00%\t10.00%\t1,000,000\t500,000\t\t900,000",
      "/article/\t3.39%\t-3.30%\t697,966\t470,933\t\t524,467",
      "/post\t118.44%\t67.60%\t2,865\t425\t\t1,862",
      "",
      "檢索未索引失敗數目\t53.16%\t-1\t15,596\t493\t\t",
      "",
      ...SAMPLE_TSV.split("\n"),
    ].join("\n");

    const result = parseIndexingTsv(fullSheet);
    expect(result.domain).not.toBeNull();
    expect(result.domain!.segment).toBe("全網域");
    expect(result.domain!.change_pct).toBeCloseTo(0.1969);
    expect(result.paths).toHaveLength(6);
    expect(result.not_indexed_total).not.toBeNull();
    expect(result.sum).not.toBeNull();
  });
});
