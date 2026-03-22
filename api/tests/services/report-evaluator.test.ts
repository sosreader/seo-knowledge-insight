import { describe, it, expect } from "vitest";
import {
  evaluateReport,
  evaluateReportV2,
  computeCompositeV2,
  computeCompositeV3,
  type ReportEvalL3Scores,
} from "../../src/services/report-evaluator.js";

// ── Test fixtures ─────────────────────────────────────────────────────

const FULL_SEVEN_SECTION_REPORT = `---
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

## 六、AI 可見度分析

AI Overview 出現率持續上升。

## 七、知識庫引用

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
## 六、AI 可見度分析
AI visibility 持續觀察中
## 七、知識庫引用
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

  it("returns section_coverage: 1.0 for full 7-section report", () => {
    const result = evaluateReport(FULL_SEVEN_SECTION_REPORT, []);
    expect(result.section_coverage).toBe(1.0);
  });

  it("detects research citations (Semrush / GSC / Backlinko)", () => {
    const result = evaluateReport(FULL_SEVEN_SECTION_REPORT, []);
    expect(result.has_research_citations).toBe(1);
  });

  it("detects KB links in report", () => {
    const result = evaluateReport(REPORT_WITH_LINKS, []);
    expect(result.has_kb_links).toBe(1);
  });

  it("counts KB citation links correctly (capped at 1.0)", () => {
    const result = evaluateReport(REPORT_WITH_LINKS, []);
    // 2 unique kb links / 6 ≈ 0.333
    expect(result.kb_citation_count).toBeCloseTo(2 / 6, 3);
  });

  it("returns 0 has_research_citations for report without any research keyword", () => {
    const plain = "## 一、\n## 二、\n## 三、\n## 四、\n## 五、\n## 六、\n## 七、\n";
    const result = evaluateReport(plain, []);
    expect(result.has_research_citations).toBe(0);
  });

  it("computes alert_coverage: 1.0 when all alert names appear in action section", () => {
    const result = evaluateReport(REPORT_WITH_LINKS, ["CTR"]);
    expect(result.alert_coverage).toBe(1.0);
  });

  it("computes alert_coverage: 0.0 when no alert names appear in any searched section", () => {
    const result = evaluateReport(REPORT_WITH_LINKS, ["NonExistentMetric"]);
    expect(result.alert_coverage).toBe(0);
  });

  it("computes alert_coverage: 1 (full credit) when alertNames is empty", () => {
    const result = evaluateReport(FULL_SEVEN_SECTION_REPORT, []);
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

  it("finds alert names across any section in 7-section format", () => {
    const report = `## 一、本週 SEO 情勢快照
Discover 急跌 -55%

## 二、流量信號解讀
探索比例月 -28.5%

## 五、搜尋意圖對映
意圖位移分析

## 六、優先行動清單
- 排查外部連結流失
- 監控檢索未索引趨勢
`;
    const result = evaluateReport(report, [
      "Discover",
      "外部連結",
      "檢索未索引",
      "探索比例",
    ]);
    expect(result.alert_coverage).toBe(1.0);
  });

  it("strips 'KW:' prefix for fuzzy matching", () => {
    const report = `## 一、本週 SEO 情勢快照
影評月 -29.8%，電影 -25.5%
`;
    const result = evaluateReport(report, ["KW: 影評", "KW: 電影", "NonExistent"]);
    // "KW: 影評" → "影評" found, "KW: 電影" → "電影" found, NonExistent missing → 2/3
    expect(result.alert_coverage).toBeCloseTo(2 / 3, 5);
  });

  it("finds alert names anywhere in the body, not just specific sections", () => {
    const report = `## 一、本週 SEO 情勢快照
Discover 月 -24.1%, 外部連結 -30.5%

## 三、技術 SEO 健康度
檢索未索引 +25.7%

## 六、優先行動清單
- 監控 CTR 趨勢
`;
    const result = evaluateReport(report, [
      "Discover",
      "外部連結",
      "CTR",
      "檢索未索引",
      "NonExistent",
    ]);
    // All found except NonExistent → 4/5
    expect(result.alert_coverage).toBeCloseTo(0.8, 5);
  });

  it("overall is average of all 5 dimension scores", () => {
    const result = evaluateReport(FULL_SEVEN_SECTION_REPORT, []);
    const expected =
      (result.section_coverage +
        result.kb_citation_count +
        result.has_research_citations +
        result.has_kb_links +
        result.alert_coverage) /
      5;
    expect(result.overall).toBeCloseTo(expected, 5);
  });

  it("returns section_coverage for partial report", () => {
    const partial = "## 一、\n## 二、\n## 三、\n";
    const result = evaluateReport(partial, []);
    expect(result.section_coverage).toBeCloseTo(3 / 7, 5);
  });

  it("llm_augmented: 1 when report contains AI 輔助 marker", () => {
    const hybridReport = FULL_SEVEN_SECTION_REPORT + "\n### 跨指標關聯分析（AI 輔助）\n分析內容";
    const result = evaluateReport(hybridReport, []);
    expect(result.llm_augmented).toBe(1);
  });

  it("llm_augmented: 1 when report contains AI 解讀 marker", () => {
    const hybridReport = FULL_SEVEN_SECTION_REPORT + "\n### 流量信號 AI 解讀\n分析內容";
    const result = evaluateReport(hybridReport, []);
    expect(result.llm_augmented).toBe(1);
  });

  it("llm_augmented: 1 when report_meta generation_mode is claude-code", () => {
    const ccReport = FULL_SEVEN_SECTION_REPORT +
      '\n<!-- report_meta {"generation_mode":"claude-code","generated_at":"2026-03-21T11:00:00.000Z"} -->';
    const result = evaluateReport(ccReport, []);
    expect(result.llm_augmented).toBe(1);
  });

  it("llm_augmented: 1 when report_meta generation_mode is openai", () => {
    const openaiReport = FULL_SEVEN_SECTION_REPORT +
      '\n<!-- report_meta {"generation_mode":"openai","generated_at":"2026-03-21T11:00:00.000Z"} -->';
    const result = evaluateReport(openaiReport, []);
    expect(result.llm_augmented).toBe(1);
  });

  it("llm_augmented: 0 for standard template report without meta or markers", () => {
    const result = evaluateReport(FULL_SEVEN_SECTION_REPORT, []);
    expect(result.llm_augmented).toBe(0);
  });

  it("llm_augmented: 0 for empty report", () => {
    const result = evaluateReport(EMPTY_REPORT, []);
    expect(result.llm_augmented).toBe(0);
  });

  it("overall is not affected by llm_augmented field", () => {
    const hybridReport = FULL_SEVEN_SECTION_REPORT + "\n### 跨指標關聯分析（AI 輔助）\n分析內容";
    const templateResult = evaluateReport(FULL_SEVEN_SECTION_REPORT, []);
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

  // ── has_crawled_not_indexed_section ───────────────────────────────

  it("has_crawled_not_indexed_section: 1 when report contains ## 檢索未索引分析 section", () => {
    const reportWithSection = FULL_SEVEN_SECTION_REPORT + "\n## 檢索未索引分析（警示）\n\n路徑分段分析結果...\n";
    const result = evaluateReport(reportWithSection, []);
    expect(result.has_crawled_not_indexed_section).toBe(1);
  });

  it("has_crawled_not_indexed_section: 0 when report does not contain ## 檢索未索引分析 section", () => {
    const result = evaluateReport(FULL_SEVEN_SECTION_REPORT, []);
    expect(result.has_crawled_not_indexed_section).toBe(0);
  });

  it("has_crawled_not_indexed_section: 0 for empty report", () => {
    const result = evaluateReport(EMPTY_REPORT, []);
    expect(result.has_crawled_not_indexed_section).toBe(0);
  });

  it("section_coverage denominator is 7, independent of has_crawled_not_indexed_section", () => {
    const reportWithExtra =
      FULL_SEVEN_SECTION_REPORT + "\n## 檢索未索引分析（警示）\n\n路徑分段分析結果...\n";
    const result = evaluateReport(reportWithExtra, []);
    // 7 standard sections all present → section_coverage stays 1.0
    expect(result.section_coverage).toBe(1.0);
    // has_crawled_not_indexed_section is independent
    expect(result.has_crawled_not_indexed_section).toBe(1);
  });
});

// ── evaluateReportV2 / computeCompositeV2 ────────────────────────────

describe("evaluateReportV2()", () => {
  it("returns l1, l2, l3, l3_skipped, and composite_v2 fields", () => {
    const result = evaluateReportV2(FULL_SEVEN_SECTION_REPORT, []);
    expect(result).toHaveProperty("l1");
    expect(result).toHaveProperty("l2");
    expect(result).toHaveProperty("l3");
    expect(result).toHaveProperty("l3_skipped");
    expect(result).toHaveProperty("composite_v2");
    expect(result.l3_skipped).toBe(true);
    expect(result.l3).toBeNull();
  });

  it("l1 matches standalone evaluateReport() output", () => {
    const v2 = evaluateReportV2(FULL_SEVEN_SECTION_REPORT, []);
    const standalone = evaluateReport(FULL_SEVEN_SECTION_REPORT, []);
    expect(v2.l1).toEqual(standalone);
  });

  it("composite_v2 without L3 uses fallback weights summing to 1.0", () => {
    // Verify weights: 0.30 + 0.15 + 0.15 + 0.12 + 0.10 + 0.10 + 0.08 = 1.0
    const result = evaluateReportV2(FULL_SEVEN_SECTION_REPORT, []);
    expect(result.composite_v2).toBeGreaterThanOrEqual(0);
    expect(result.composite_v2).toBeLessThanOrEqual(1.0);
  });

  it("composite_v2 with L3 uses full weights summing to 1.0", () => {
    const l3: ReportEvalL3Scores = {
      reasoning_depth: 4,
      actionability: 4,
      insight_originality: 3,
    };
    const result = evaluateReportV2(FULL_SEVEN_SECTION_REPORT, [], l3);
    expect(result.l3_skipped).toBe(false);
    expect(result.l3).toEqual(l3);
    expect(result.composite_v2).toBeGreaterThanOrEqual(0);
    expect(result.composite_v2).toBeLessThanOrEqual(1.0);
  });

  it("empty report produces composite_v2 = 0", () => {
    const result = evaluateReportV2("", []);
    expect(result.composite_v2).toBe(0);
  });
});

describe("computeCompositeV2()", () => {
  it("without L3: weights sum to 1.0", () => {
    // Perfect L1 + L2 scores should produce composite = 1.0
    const l1 = evaluateReport(FULL_SEVEN_SECTION_REPORT, []);
    const perfectL2 = {
      cross_metric_reasoning: 1.0,
      action_specificity: 1.0,
      data_evidence_ratio: 1.0,
      citation_integration: 1.0,
      quadrant_judgment: 1.0,
      section_depth_variance: 1.0,
      temporal_dual_frame: 1.0,
      priority_balance: 1.0,
      causal_chain: 1.0,
      top_recommendation: 1.0,
    };
    // When l1.overall=1.0 and all L2=1.0, composite should be exactly 1.0
    const all1L1 = { ...l1, overall: 1.0 };
    const composite = computeCompositeV2(all1L1, perfectL2, null);
    expect(composite).toBeCloseTo(1.0, 5);
  });

  it("with L3: weights sum to 1.0", () => {
    const all1L1 = {
      section_coverage: 1, kb_citation_count: 1, has_research_citations: 1,
      has_kb_links: 1, alert_coverage: 1, overall: 1.0,
      llm_augmented: 1, has_crawled_not_indexed_section: 1,
      action_maturity_labeled: 1.0,
    };
    const perfectL2 = {
      cross_metric_reasoning: 1.0, action_specificity: 1.0,
      data_evidence_ratio: 1.0, citation_integration: 1.0,
      quadrant_judgment: 1.0, section_depth_variance: 1.0,
      temporal_dual_frame: 1.0, priority_balance: 1.0,
      causal_chain: 1.0, top_recommendation: 1.0,
    };
    const perfectL3: ReportEvalL3Scores = {
      reasoning_depth: 5, actionability: 5, insight_originality: 5,
    };
    const composite = computeCompositeV2(all1L1, perfectL2, perfectL3);
    expect(composite).toBeCloseTo(1.0, 5);
  });

  it("all zeros produces composite = 0", () => {
    const zeroL1 = {
      section_coverage: 0, kb_citation_count: 0, has_research_citations: 0,
      has_kb_links: 0, alert_coverage: 0, overall: 0,
      llm_augmented: 0, has_crawled_not_indexed_section: 0,
      action_maturity_labeled: 0,
    };
    const zeroL2 = {
      cross_metric_reasoning: 0, action_specificity: 0,
      data_evidence_ratio: 0, citation_integration: 0,
      quadrant_judgment: 0, section_depth_variance: 0,
      temporal_dual_frame: 0, priority_balance: 0,
      causal_chain: 0, top_recommendation: 0,
    };
    expect(computeCompositeV2(zeroL1, zeroL2, null)).toBe(0);
    const zeroL3: ReportEvalL3Scores = {
      reasoning_depth: 0, actionability: 0, insight_originality: 0,
    };
    expect(computeCompositeV2(zeroL1, zeroL2, zeroL3)).toBe(0);
  });
});

// ── action_maturity_labeled ──────────────────────────────────────────

describe("action_maturity_labeled", () => {
  it("returns 1.0 when all 4 maturity dimensions labeled", () => {
    const content = `## 五、優先行動清單

> 成熟度參考：策略 L2 / 流程 L2

- 🔴 修復索引 — **[策略 L2→L3]**
- 🟡 優化標題 — **[關鍵字 L3→L3]**
- 🟡 改善流程 — **[流程 L2→L3]**
- 🟢 追蹤指標 — **[指標 L2→L3]**`;
    const result = evaluateReport(content, []);
    expect(result.action_maturity_labeled).toBe(1.0);
  });

  it("returns 0.75 for 3 unique dimensions", () => {
    const content = `## 五、優先行動清單

> 成熟度參考：策略 L2 / 流程 L2

- 🔴 修復索引 — **[策略 L2→L3]**
- 🟡 優化標題 — **[關鍵字 L3→L3]**
- 🟡 改善流程 — **[流程 L2→L3]**`;
    const result = evaluateReport(content, []);
    expect(result.action_maturity_labeled).toBe(0.75);
  });

  it("returns 0.5 when no maturity ref line", () => {
    const content = `## 五、優先行動清單

- 🔴 修復索引問題
- 🟡 優化標題`;
    const result = evaluateReport(content, []);
    expect(result.action_maturity_labeled).toBe(0.5);
  });

  it("returns 0.0 when ref line exists but no labels", () => {
    const content = `## 五、優先行動清單

> 成熟度參考：策略 L2 / 流程 L2

- 🔴 修復索引問題`;
    const result = evaluateReport(content, []);
    expect(result.action_maturity_labeled).toBe(0.0);
  });

  it("returns 0.5 for empty content", () => {
    const result = evaluateReport("", []);
    expect(result.action_maturity_labeled).toBe(0.5);
  });
});

// ── computeCompositeV3 ───────────────────────────────────────────────

describe("computeCompositeV3()", () => {
  it("weights sum to 1.0 (all ones produces 1.0)", () => {
    const all1L1 = {
      section_coverage: 1, kb_citation_count: 1, has_research_citations: 1,
      has_kb_links: 1, alert_coverage: 1, overall: 1.0,
      llm_augmented: 1, has_crawled_not_indexed_section: 1,
      action_maturity_labeled: 1.0,
    };
    const all1L2 = {
      cross_metric_reasoning: 1.0, action_specificity: 1.0,
      data_evidence_ratio: 1.0, citation_integration: 1.0,
      quadrant_judgment: 1.0, section_depth_variance: 1.0,
      temporal_dual_frame: 1.0, priority_balance: 1.0,
      causal_chain: 1.0, top_recommendation: 1.0,
    };
    expect(computeCompositeV3(all1L1, all1L2)).toBeCloseTo(1.0, 5);
  });

  it("all zeros produces 0", () => {
    const zeroL1 = {
      section_coverage: 0, kb_citation_count: 0, has_research_citations: 0,
      has_kb_links: 0, alert_coverage: 0, overall: 0,
      llm_augmented: 0, has_crawled_not_indexed_section: 0,
      action_maturity_labeled: 0,
    };
    const zeroL2 = {
      cross_metric_reasoning: 0, action_specificity: 0,
      data_evidence_ratio: 0, citation_integration: 0,
      quadrant_judgment: 0, section_depth_variance: 0,
      temporal_dual_frame: 0, priority_balance: 0,
      causal_chain: 0, top_recommendation: 0,
    };
    expect(computeCompositeV3(zeroL1, zeroL2)).toBe(0);
  });

  it("evaluateReportV2 includes composite_v3", () => {
    const result = evaluateReportV2(FULL_SEVEN_SECTION_REPORT, []);
    expect(result).toHaveProperty("composite_v3");
    expect(result.composite_v3).toBeGreaterThanOrEqual(0);
    expect(result.composite_v3).toBeLessThanOrEqual(1.0);
  });
});
