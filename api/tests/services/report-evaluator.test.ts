import { describe, it, expect } from "vitest";
import { evaluateReport } from "../../src/services/report-evaluator.js";

// ── Test fixtures ─────────────────────────────────────────────────────

const FULL_SIX_SECTION_REPORT = `---
**報告資訊**
- 知識庫版本：v2026.03.05
- 分析框架：Semrush 2025 / GSC 官方指引
---

## 一、本週 SEO 情勢快照

SEO 健康評分：70/100（需關注）

## 二、流量信號解讀

Backlinko 2024：Position 1 平均 CTR 27.6%

## 三、技術 SEO 健康度

索引覆蓋率下滑。NavBoost 聚合點擊信號。

## 四、搜尋意圖對映

E-E-A-T 信號觀察。

## 五、本週優先行動清單

- 🔴 CTR 下滑立即處理
- 🟡 曝光 CTR 優化
- 🟢 低優先規劃

## 六、知識庫引用

**Q**：如何改善 CTR？
**A（節錄）**：優化 Title 與 Description…
**連結**：[知識庫 →](/admin/seoInsight/abc1234567890abc)
`;

const EMPTY_REPORT = "";

const REPORT_WITH_LINKS = `## 一、本週 SEO 情勢快照
## 二、流量信號解讀
## 三、技術 SEO 健康度
## 四、搜尋意圖對映
## 五、本週優先行動清單
CTR 出現下滑
## 六、知識庫引用
[知識庫 →](/admin/seoInsight/aabbccdd11223344)
[知識庫 →](/admin/seoInsight/1122334455667788)
`;

// ── Tests ──────────────────────────────────────────────────────────────

describe("evaluateReport()", () => {
  it("returns all-zero scores for empty content", () => {
    const result = evaluateReport(EMPTY_REPORT, []);
    expect(result.section_coverage).toBe(0);
    expect(result.kb_citation_count).toBe(0);
    expect(result.has_research_citations).toBe(0);
    expect(result.has_kb_links).toBe(0);
    expect(result.alert_coverage).toBe(0);
    expect(result.overall).toBe(0);
  });

  it("returns section_coverage: 1.0 for full 6-section report", () => {
    const result = evaluateReport(FULL_SIX_SECTION_REPORT, []);
    expect(result.section_coverage).toBe(1.0);
  });

  it("detects research citations (Semrush / GSC / Backlinko)", () => {
    const result = evaluateReport(FULL_SIX_SECTION_REPORT, []);
    expect(result.has_research_citations).toBe(1);
  });

  it("detects KB links in report", () => {
    const result = evaluateReport(REPORT_WITH_LINKS, []);
    expect(result.has_kb_links).toBe(1);
  });

  it("counts KB citation links correctly (capped at 1.0)", () => {
    const result = evaluateReport(REPORT_WITH_LINKS, []);
    // 2 links / 6 ≈ 0.333
    expect(result.kb_citation_count).toBeCloseTo(2 / 6, 3);
  });

  it("returns 0 has_research_citations for report without any research keyword", () => {
    const plain = "## 一、\n## 二、\n## 三、\n## 四、\n## 五、\n## 六、\n";
    const result = evaluateReport(plain, []);
    expect(result.has_research_citations).toBe(0);
  });

  it("computes alert_coverage: 1.0 when all alert names appear in section 五", () => {
    const result = evaluateReport(REPORT_WITH_LINKS, ["CTR"]);
    expect(result.alert_coverage).toBe(1.0);
  });

  it("computes alert_coverage: 0.0 when no alert names appear in section 五", () => {
    const result = evaluateReport(REPORT_WITH_LINKS, ["NonExistentMetric"]);
    expect(result.alert_coverage).toBe(0);
  });

  it("computes alert_coverage: 1 (full credit) when alertNames is empty", () => {
    const result = evaluateReport(FULL_SIX_SECTION_REPORT, []);
    expect(result.alert_coverage).toBe(1);
  });

  it("fuzzy matches alert names with parenthetical suffix", () => {
    const report = `## 五、本週優先行動清單
- AMP Article 修復
- News 流量恢復策略
- GPT 工作階段追蹤
`;
    const result = evaluateReport(report, [
      "AMP Article",
      "News(new)",
      "GPT (工作階段)",
      "週平均回應時間",
    ]);
    // AMP Article: exact match, News(new) → "News" fuzzy, GPT (工作階段) → "GPT" fuzzy
    // 週平均回應時間: not found → 3/4
    expect(result.alert_coverage).toBeCloseTo(0.75, 5);
  });

  it("overall is average of all 5 dimension scores", () => {
    const result = evaluateReport(FULL_SIX_SECTION_REPORT, []);
    const expected =
      (result.section_coverage +
        result.kb_citation_count +
        result.has_research_citations +
        result.has_kb_links +
        result.alert_coverage) /
      5;
    expect(result.overall).toBeCloseTo(expected, 5);
  });

  it("returns section_coverage: 0.5 for half-complete report", () => {
    const partial = "## 一、\n## 二、\n## 三、\n";
    const result = evaluateReport(partial, []);
    expect(result.section_coverage).toBeCloseTo(3 / 6, 5);
  });

  it("llm_augmented: 1 when report contains AI 輔助 marker", () => {
    const hybridReport = FULL_SIX_SECTION_REPORT + "\n### 跨指標關聯分析（AI 輔助）\n分析內容";
    const result = evaluateReport(hybridReport, []);
    expect(result.llm_augmented).toBe(1);
  });

  it("llm_augmented: 1 when report contains AI 解讀 marker", () => {
    const hybridReport = FULL_SIX_SECTION_REPORT + "\n### 流量信號 AI 解讀\n分析內容";
    const result = evaluateReport(hybridReport, []);
    expect(result.llm_augmented).toBe(1);
  });

  it("llm_augmented: 0 for standard template report", () => {
    const result = evaluateReport(FULL_SIX_SECTION_REPORT, []);
    expect(result.llm_augmented).toBe(0);
  });

  it("llm_augmented: 0 for empty report", () => {
    const result = evaluateReport(EMPTY_REPORT, []);
    expect(result.llm_augmented).toBe(0);
  });

  it("overall is not affected by llm_augmented field", () => {
    const hybridReport = FULL_SIX_SECTION_REPORT + "\n### 跨指標關聯分析（AI 輔助）\n分析內容";
    const templateResult = evaluateReport(FULL_SIX_SECTION_REPORT, []);
    const hybridResult = evaluateReport(hybridReport, []);
    // overall should be the same (llm_augmented not counted), section_coverage slightly differs
    expect(hybridResult.llm_augmented).toBe(1);
    expect(templateResult.llm_augmented).toBe(0);
    // Both should use the same 5-dimension formula
    const expectedTemplate =
      (templateResult.section_coverage +
        templateResult.kb_citation_count +
        templateResult.has_research_citations +
        templateResult.has_kb_links +
        templateResult.alert_coverage) /
      5;
    expect(templateResult.overall).toBeCloseTo(expectedTemplate, 5);
  });
});
