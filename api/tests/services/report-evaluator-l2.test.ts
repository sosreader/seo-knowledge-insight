import { describe, it, expect } from "vitest";
import {
  crossMetricReasoning,
  actionSpecificity,
  dataEvidenceRatio,
  citationIntegration,
  quadrantJudgment,
  sectionDepthVariance,
  temporalDualFrame,
  priorityBalance,
  causalChain,
  topRecommendation,
  evaluateReportL2,
  type ReportEvalL2Result,
} from "../../src/services/report-evaluator-l2.js";

// ── Test fixtures ─────────────────────────────────────────────────────

/** High-quality report with cross-metric reasoning, specific actions, data evidence */
const GOOD_REPORT = `## 一、本週 SEO 情勢快照

SEO 健康評分：72/100（需關注）

| 指標 | 本週 | 上週 | 變動 |
|------|------|------|------|
| 曝光 | 125,000 | 118,000 | +5.9% |
| 點擊 | 4,200 | 4,800 | -12.5% |
| CTR | 3.36% | 4.07% | -0.71pp |

## 二、流量信號解讀

CTR 從 4.07% 下降至 3.36%（-17.4%），然而曝光同期成長 5.9%，這表示曝光增加並未轉化為等比的點擊成長。根據 [1] 的分析，此現象可能源自排名位置下移——當頁面從 Position 3 滑落至 Position 5-7 時，CTR 會出現斷崖式下降（First Page Sage 2024 數據顯示 Position 3 CTR 約 11% vs Position 7 僅 3.5%）。

Discover 流量月減 24.1%（從 8,500 降至 6,452），但有機搜尋點擊僅減 12.5%，導致 Discover 佔比從 64% 下降至 60.6%。這意味著 Discover 的衰退速度快於搜尋，需特別關注內容新鮮度與 E-E-A-T 信號 [2]。

## 三、技術 SEO 健康度

索引覆蓋率維持 82.3%（上週 83.1%，-0.8pp）。檢索未索引頁面增加 15 頁（從 340 到 355），主要集中在 /tag/ 路徑。

Core Web Vitals：LCP 2.1s（良好）、FID 45ms（良好）、CLS 0.08（需改善，上週 0.06）。CLS 惡化可能與新部署的 lazy-load 圖片組件有關 [3]。

## 四、搜尋意圖對映

高曝光低點擊象限（需優化標題）：
- 「SEO 教學」：曝光 3,200 / 點擊 48 / CTR 1.5% — 位於高曝光低點擊象限，建議重寫標題加入 2026 年份標記，因為用戶傾向點擊含有最新年份的結果
- 「網站速度優化」：曝光 2,100 / 點擊 35 / CTR 1.67%

低曝光高點擊象限（利基優勢）：
- 「Core Web Vitals 檢測工具」：曝光 450 / 點擊 89 / CTR 19.8%

## 五、本週優先行動清單

- 🔴 **P0：CTR 下滑修復**
  - 在 GSC 的效能報表中篩選 CTR 下降 > 20% 的查詢，逐一檢查標題標籤是否含有過時年份或缺少吸引力詞彙
  - 針對 Position 4-7 的頁面，在 title 前方加入觸發詞（數字 + 方括號格式），預期 CTR 提升 15-25%
- 🟡 **P1：CLS 惡化排查**
  - 使用 Chrome DevTools Performance 面板，檢查 lazy-load 圖片是否缺少 width/height 屬性
  - 部署後 48 小時內於 PageSpeed Insights 驗證 CLS 是否回落至 < 0.1
- 🟢 **P2：Discover 流量恢復**
  - 檢查最近 7 天發布的文章是否都有設定 og:image（1200×630），缺少者補上

## 六、AI 可見度分析

AI Overview 出現率本週 18.5%（上週 16.2%，+2.3pp）。在 12 個追蹤關鍵字中，有 5 個觸發 AI Overview，其中 3 個引用了我方內容。

## 七、知識庫引用

[1] CTR 與排名位置的關聯分析 — [知識庫 →](/admin/seoInsight/abc1234567890abc)
[2] Discover 流量影響因素 — [知識庫 →](/admin/seoInsight/def4567890123def)
[3] Core Web Vitals 最佳實踐 — [知識庫 →](/admin/seoInsight/ghi7890123456ghi)
[4] AI Overview 競爭策略 — [知識庫 →](/admin/seoInsight/jkl0123456789jkl)
`;

/** Low-quality report: just lists numbers, vague actions, no reasoning */
const POOR_REPORT = `## 一、本週 SEO 情勢快照

本週表現需要關注。

## 二、流量信號解讀

流量有下降趨勢，需持續觀察。

## 三、技術 SEO 健康度

技術面大致正常。

## 四、搜尋意圖對映

搜尋意圖分析中。

## 五、本週優先行動清單

- 注意 CTR
- 持續觀察流量
- 關注技術面

## 六、AI 可見度分析

AI 可見度持續觀察中。

## 七、知識庫引用

無相關引用。
`;

// ── crossMetricReasoning ──────────────────────────────────────────────

describe("crossMetricReasoning()", () => {
  it("returns high score for content with causal reasoning linking multiple metrics", () => {
    const content = `CTR 從 4.07% 下降至 3.36%，然而曝光同期成長 5.9%，這表示曝光增加並未轉化為點擊成長。
因此排名位置下移導致 CTR 斷崖式下降。
Discover 流量月減 24.1%，但有機搜尋點擊僅減 12.5%，導致 Discover 佔比下降。`;
    const score = crossMetricReasoning(content);
    // 3 qualifying lines / 15 = 0.2
    expect(score).toBeGreaterThanOrEqual(0.1);
    expect(score).toBeLessThanOrEqual(0.3);
  });

  it("returns 0 for content with no cross-metric reasoning", () => {
    const content = `本週表現需要關注。流量有下降趨勢。技術面大致正常。`;
    const score = crossMetricReasoning(content);
    expect(score).toBe(0);
  });

  it("returns 0 for empty content", () => {
    expect(crossMetricReasoning("")).toBe(0);
  });

  it("requires both causal connector AND multiple metric names in proximity", () => {
    // Has causal word but only one metric
    const singleMetric = `CTR 下降了，因此需要處理這個問題。`;
    expect(crossMetricReasoning(singleMetric)).toBe(0);
  });

  it("scores higher with more cross-metric reasoning instances", () => {
    const one = `CTR 下降導致曝光品質下滑。`;
    const three = `CTR 下降導致曝光品質下滑。
索引覆蓋率下降因此點擊也受影響。
Discover 流量下降表示排名位置有波動。`;
    expect(crossMetricReasoning(three)).toBeGreaterThanOrEqual(
      crossMetricReasoning(one),
    );
  });
});

// ── actionSpecificity ────────────────────────────────────────────────

describe("actionSpecificity()", () => {
  it("returns high score for specific, actionable items", () => {
    const content = `- 在 GSC 的效能報表中篩選 CTR 下降 > 20% 的查詢，逐一檢查標題標籤
- 使用 Chrome DevTools Performance 面板，檢查 lazy-load 圖片是否缺少 width/height
- 部署後 48 小時內於 PageSpeed Insights 驗證 CLS 是否回落至 < 0.1`;
    const score = actionSpecificity(content);
    expect(score).toBeGreaterThanOrEqual(0.6);
  });

  it("returns low score for vague actions", () => {
    const content = `- 注意 CTR 變化
- 持續觀察流量趨勢
- 關注技術面狀況
- 需要改善 SEO`;
    const score = actionSpecificity(content);
    expect(score).toBeLessThanOrEqual(0.4);
  });

  it("returns 0 for empty content", () => {
    expect(actionSpecificity("")).toBe(0);
  });

  it("returns 0 for content with no action items", () => {
    const content = `本週流量表現如下：曝光 12,500 次，點擊 450 次。`;
    expect(actionSpecificity(content)).toBe(0);
  });

  it("handles mixed specific and vague actions", () => {
    const content = `- 在 GSC 篩選 CTR < 2% 的頁面並優化標題
- 注意流量變化
- 使用 Screaming Frog 檢查 /tag/ 路徑的 canonical 設定`;
    const score = actionSpecificity(content);
    // Mixed: not too high, not too low
    expect(score).toBeGreaterThan(0.3);
    expect(score).toBeLessThan(0.9);
  });
});

// ── dataEvidenceRatio ────────────────────────────────────────────────

describe("dataEvidenceRatio()", () => {
  it("returns score based on paragraph-level data coverage (/70)", () => {
    const content = `CTR 從 4.07% 下降至 3.36%。

Discover 流量月減 24.1%。

索引覆蓋率 82.3%。

Position 3 CTR 約 11%。

曝光 125,000 次。

點擊 -12.5%。

Core Web Vitals LCP 2.1s（+15%）。

有機搜尋成長 +5.9%。`;
    const score = dataEvidenceRatio(content);
    // 8 paragraphs with data / 70 ≈ 0.114
    expect(score).toBeGreaterThan(0);
    expect(score).toBeLessThan(0.3);
  });

  it("returns low score for content with no data", () => {
    const content = `流量有下降趨勢，需持續觀察。技術面大致正常。搜尋意圖分析中。`;
    const score = dataEvidenceRatio(content);
    expect(score).toBeLessThanOrEqual(0.2);
  });

  it("returns 0 for empty content", () => {
    expect(dataEvidenceRatio("")).toBe(0);
  });

  it("caps at 1.0 for extremely data-rich content", () => {
    // Generate content with many data points
    const lines = Array.from(
      { length: 30 },
      (_, i) => `指標${i}: ${(i * 3.7).toFixed(1)}%（${(i + 1) * 1000} 次）`,
    );
    const score = dataEvidenceRatio(lines.join("\n"));
    expect(score).toBeLessThanOrEqual(1.0);
  });

  it("counts both percentage patterns and large numbers", () => {
    const percentOnly = `CTR 3.36%，增長 5.9%，下降 17.4%。`;
    const numbersOnly = `曝光 125,000 次，點擊 4,200 次，索引 340 頁。`;
    const both = `CTR 3.36%，曝光 125,000 次，點擊 4,200 次，增長 5.9%。`;
    expect(dataEvidenceRatio(both)).toBeGreaterThanOrEqual(
      dataEvidenceRatio(percentOnly),
    );
    expect(dataEvidenceRatio(both)).toBeGreaterThanOrEqual(
      dataEvidenceRatio(numbersOnly),
    );
  });
});

// ── citationIntegration ──────────────────────────────────────────────

describe("citationIntegration()", () => {
  it("returns high score when inline citations spread across sections", () => {
    const content = `## 一、情勢快照
根據 [1] 的分析，CTR 趨勢顯示下滑。

## 二、流量解讀
另外 [2] 指出 Discover 流量受季節影響。

## 三、技術健康
技術面參考 [3] 建議的 CLS 優化方式。

## 七、知識庫引用
[1] CTR 分析
[2] Discover 研究
[3] CLS 優化`;
    const score = citationIntegration(content);
    // inline: 3/3=1.0, diversity: 3/7≈0.43, product ≈ 0.43
    expect(score).toBeGreaterThanOrEqual(0.3);
  });

  it("returns low score for citations only stacked at the end", () => {
    const content = `本週流量下降，需要關注。技術面也有問題。

## 七、知識庫引用
[1] 參考資料一
[2] 參考資料二
[3] 參考資料三`;
    const score = citationIntegration(content);
    expect(score).toBeLessThanOrEqual(0.3);
  });

  it("returns 0 for content with no citations", () => {
    const content = `本週流量下降，需要關注。無任何引用。`;
    expect(citationIntegration(content)).toBe(0);
  });

  it("returns 0 for empty content", () => {
    expect(citationIntegration("")).toBe(0);
  });

  it("distinguishes inline usage from tail-only stacking", () => {
    const inline = `分析顯示 [1] CTR 下降與 [2] 排名下移有關。
## 七、知識庫引用
[1] CTR 分析 [2] 排名研究`;
    const tailOnly = `分析顯示 CTR 下降與排名下移有關。
## 七、知識庫引用
[1] CTR 分析 [2] 排名研究`;
    expect(citationIntegration(inline)).toBeGreaterThan(
      citationIntegration(tailOnly),
    );
  });
});

// ── quadrantJudgment ─────────────────────────────────────────────────

describe("quadrantJudgment()", () => {
  it("returns 1.0 for content with quadrant keyword + explanation", () => {
    const content = `「SEO 教學」位於高曝光低點擊象限，建議重寫標題加入年份標記。
「Core Web Vitals」位於低曝光高點擊象限，這是利基優勢。`;
    const score = quadrantJudgment(content);
    expect(score).toBe(1.0);
  });

  it("returns 0.5 for quadrant keyword without explanation", () => {
    const content = `高曝光低點擊象限的查詢有 3 個。低曝光高點擊象限有 1 個。`;
    const score = quadrantJudgment(content);
    expect(score).toBe(0.5);
  });

  it("returns 0 for content without quadrant analysis", () => {
    const content = `本週流量下降，CTR 需要關注。`;
    const score = quadrantJudgment(content);
    expect(score).toBe(0);
  });

  it("returns 0 for empty content", () => {
    expect(quadrantJudgment("")).toBe(0);
  });

  it("detects various quadrant keyword patterns", () => {
    const patterns = [
      "高曝光低點擊象限",
      "低曝光高點擊象限",
      "高曝光高點擊象限",
      "低曝光低點擊象限",
    ];
    for (const pattern of patterns) {
      const content = `${pattern}需要關注，因為這表示排名位置不穩定。`;
      expect(quadrantJudgment(content)).toBeGreaterThan(0);
    }
  });
});

// ── sectionDepthVariance ─────────────────────────────────────────────

describe("sectionDepthVariance()", () => {
  it("returns high score for balanced sections", () => {
    const content = `## 一、本週 SEO 情勢快照
${"這是一段分析文字。".repeat(10)}

## 二、流量信號解讀
${"這是流量解讀內容。".repeat(10)}

## 三、技術 SEO 健康度
${"這是技術分析文字。".repeat(10)}

## 四、搜尋意圖對映
${"這是意圖對映分析。".repeat(10)}

## 五、本週優先行動清單
${"這是行動建議文字。".repeat(10)}

## 六、AI 可見度分析
${"這是可見度分析文。".repeat(10)}`;
    const score = sectionDepthVariance(content);
    expect(score).toBeGreaterThanOrEqual(0.8);
  });

  it("returns low score for highly unbalanced sections", () => {
    const content = `## 一、本週 SEO 情勢快照
${"深入分析。".repeat(50)}

## 二、流量信號解讀
短。

## 三、技術 SEO 健康度
短。

## 四、搜尋意圖對映
${"深入分析。".repeat(50)}

## 五、本週優先行動清單
短。

## 六、AI 可見度分析
短。`;
    const score = sectionDepthVariance(content);
    expect(score).toBeLessThanOrEqual(0.6);
  });

  it("returns 0 for empty content", () => {
    expect(sectionDepthVariance("")).toBe(0);
  });

  it("returns 0 for content with fewer than 2 sections", () => {
    const content = `## 一、本週 SEO 情勢快照\n一些內容。`;
    expect(sectionDepthVariance(content)).toBe(0);
  });

  it("score is between 0 and 1", () => {
    const score = sectionDepthVariance(GOOD_REPORT);
    expect(score).toBeGreaterThanOrEqual(0);
    expect(score).toBeLessThanOrEqual(1.0);
  });
});

// ── temporalDualFrame ─────────────────────────────────────────────────

describe("temporalDualFrame()", () => {
  it("scores based on lines with both weekly AND monthly percentages", () => {
    const content = `Discover 週崩 -55.4%（月 -24.1%）
外部連結月跌 -30.5% / 週跌 -21.3%
「電影」關鍵字月跌 -25.5% / 週跌 -37.0%
Video 月漲 +293.2% / 週漲 +42.2%
AI 流量佔比月漲 +20.9% / 週漲 +29.9%`;
    const score = temporalDualFrame(content);
    expect(score).toBeGreaterThan(0.3);
    expect(score).toBeLessThanOrEqual(1.0);
  });

  it("returns 0 when only one timeframe mentioned", () => {
    expect(temporalDualFrame("本週流量下降 10%。")).toBe(0);
  });

  it("returns 0 for empty content", () => {
    expect(temporalDualFrame("")).toBe(0);
  });

  it("partial score for fewer lines (denominator is 15)", () => {
    const content = `Discover 週跌 -55% 且月跌 -24%。`;
    const score = temporalDualFrame(content);
    expect(score).toBeCloseTo(1 / 15, 2);
  });
});

// ── priorityBalance ──────────────────────────────────────────────────

describe("priorityBalance()", () => {
  it("scores 1.0 for well-balanced emoji distribution", () => {
    const content = `🔴 A\n🔴 B\n🔴 C\n🔴 D\n🟡 E\n🟡 F\n🟡 G\n🟢 H\n🟢 I`;
    expect(priorityBalance(content)).toBeCloseTo(1.0);
  });

  it("partial score when 🟡 is underrepresented", () => {
    // 🔴=4, 🟡=1, 🟢=3 → (1 + 0.33 + 1) / 3 ≈ 0.78
    const content = `🔴 A\n🔴 B\n🔴 C\n🔴 D\n🟡 E\n🟢 F\n🟢 G\n🟢 H`;
    const score = priorityBalance(content);
    expect(score).toBeGreaterThan(0.7);
    expect(score).toBeLessThan(0.9);
  });

  it("returns 0 for no priority markers", () => {
    expect(priorityBalance("一般內容，沒有優先級標記。")).toBe(0);
  });

  it("returns 0 for empty content", () => {
    expect(priorityBalance("")).toBe(0);
  });
});

// ── causalChain ──────────────────────────────────────────────────────

describe("causalChain()", () => {
  it("partial score for 3 blocks (denominator is 5)", () => {
    const content = `> **現象** 流量下降
> **原因** 演算法更新
> **行動** 調整內容

> **現象** CTR 下滑
> **原因** 標題過時
> **行動** 重寫標題

> **現象** 索引減少
> **原因** 內容稀薄
> **行動** 充實內容`;
    expect(causalChain(content)).toBeCloseTo(0.6);
  });

  it("scores 1.0 for 5+ blocks", () => {
    const blocks = Array.from({ length: 5 }, (_, i) =>
      `> **現象** 問題${i}\n> **原因** 原因${i}\n> **行動** 處理${i}`
    ).join("\n\n");
    expect(causalChain(blocks)).toBe(1.0);
  });

  it("returns 0 for no structured blocks", () => {
    expect(causalChain("流量下降了，原因不明。")).toBe(0);
  });

  it("returns 0 for empty content", () => {
    expect(causalChain("")).toBe(0);
  });
});

// ── topRecommendation ────────────────────────────────────────────────

describe("topRecommendation()", () => {
  it("returns 1.0 when marker + justification present", () => {
    expect(topRecommendation("💡 **最值得投入時間的 1 項**：修復索引問題。雖然 Discover 跌幅最大，但索引問題更關鍵。")).toBe(1.0);
  });

  it("returns 0.5 when marker present but no justification", () => {
    expect(topRecommendation("💡 修復索引")).toBe(0.5);
  });

  it("returns 0 when neither marker is present", () => {
    expect(topRecommendation("一般報告內容。")).toBe(0);
  });

  it("returns 0 for empty content", () => {
    expect(topRecommendation("")).toBe(0);
  });
});

// ── evaluateReportL2 (aggregate) ─────────────────────────────────────

describe("evaluateReportL2()", () => {
  it("returns all 10 fields in ReportEvalL2Result", () => {
    const result = evaluateReportL2(GOOD_REPORT);
    expect(result).toHaveProperty("cross_metric_reasoning");
    expect(result).toHaveProperty("action_specificity");
    expect(result).toHaveProperty("data_evidence_ratio");
    expect(result).toHaveProperty("citation_integration");
    expect(result).toHaveProperty("quadrant_judgment");
    expect(result).toHaveProperty("section_depth_variance");
    expect(result).toHaveProperty("temporal_dual_frame");
    expect(result).toHaveProperty("priority_balance");
    expect(result).toHaveProperty("causal_chain");
    expect(result).toHaveProperty("top_recommendation");
  });

  it("good report scores higher than poor report across original dimensions", () => {
    const good = evaluateReportL2(GOOD_REPORT);
    const poor = evaluateReportL2(POOR_REPORT);

    expect(good.cross_metric_reasoning).toBeGreaterThan(
      poor.cross_metric_reasoning,
    );
    expect(good.action_specificity).toBeGreaterThan(poor.action_specificity);
    expect(good.data_evidence_ratio).toBeGreaterThan(poor.data_evidence_ratio);
    expect(good.citation_integration).toBeGreaterThan(
      poor.citation_integration,
    );
    expect(good.quadrant_judgment).toBeGreaterThan(poor.quadrant_judgment);
    // section_depth_variance may not differ much — both have 7 sections
  });

  it("returns all zeros for empty content", () => {
    const result = evaluateReportL2("");
    expect(result.cross_metric_reasoning).toBe(0);
    expect(result.action_specificity).toBe(0);
    expect(result.data_evidence_ratio).toBe(0);
    expect(result.citation_integration).toBe(0);
    expect(result.quadrant_judgment).toBe(0);
    expect(result.section_depth_variance).toBe(0);
    expect(result.temporal_dual_frame).toBe(0);
    expect(result.priority_balance).toBe(0);
    expect(result.causal_chain).toBe(0);
    expect(result.top_recommendation).toBe(0);
  });

  it("all scores are in [0, 1] range", () => {
    const result = evaluateReportL2(GOOD_REPORT);
    for (const [key, value] of Object.entries(result)) {
      expect(value, `${key} should be >= 0`).toBeGreaterThanOrEqual(0);
      expect(value, `${key} should be <= 1`).toBeLessThanOrEqual(1);
    }
  });
});
