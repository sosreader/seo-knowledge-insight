/**
 * crawled-not-indexed-evaluator — 「已檢索 — 目前未建立索引」分析品質評估器
 *
 * Rule-based，5 個維度 + overall，與 report-evaluator 同風格。
 */

import type { CrawledNotIndexedResult } from "./crawled-not-indexed-parser.js";

// ── Types ────────────────────────────────────────────────────────────

export interface CrawledNotIndexedEvalResult {
  /** 所有路徑是否都被提及（0-1） */
  path_coverage: number;
  /** 趨勢方向描述是否正確（0-1） */
  trend_accuracy: number;
  /** 是否有嚴重度分級（0 或 1） */
  has_severity_assessment: number;
  /** 是否有路徑專屬建議（0-1） */
  recommendation_specificity: number;
  /** 數據引用正確性——分析中是否正確引用原始數據（0-1） */
  data_fidelity: number;
  /** 5 維度平均 */
  overall: number;
}

// ── Severity keywords ────────────────────────────────────────────────

const SEVERITY_KEYWORDS = [
  "critical", "warning", "stable", "improving",
  "警示", "嚴重", "需關注", "穩定", "改善",
  "🔴", "🟡", "🟢",
];

// ── Evaluator ────────────────────────────────────────────────────────

export function evaluateCrawledNotIndexedAnalysis(
  content: string,
  data: CrawledNotIndexedResult,
): CrawledNotIndexedEvalResult {
  if (!content || content.trim().length === 0) {
    return {
      path_coverage: 0,
      trend_accuracy: 0,
      has_severity_assessment: 0,
      recommendation_specificity: 0,
      data_fidelity: 0,
      overall: 0,
    };
  }

  const lower = content.toLowerCase();

  // 1. path_coverage: proportion of path segments mentioned
  const pathsMentioned = data.paths.filter((p) =>
    content.includes(p.segment),
  ).length;
  const path_coverage = data.paths.length > 0
    ? pathsMentioned / data.paths.length
    : 1;

  // 2. trend_accuracy: correct up/down description for mentioned paths
  let trendCorrect = 0;
  let trendChecked = 0;
  for (const p of data.paths) {
    if (!content.includes(p.segment)) continue;
    trendChecked++;
    if (p.change_pct == null) {
      trendCorrect++;
      continue;
    }
    // Check if the analysis correctly identifies direction
    const segIdx = content.indexOf(p.segment);
    const nearby = content.slice(segIdx, segIdx + 300).toLowerCase();
    const isUp = p.change_pct > 0;
    const mentionsUp = nearby.includes("上升") || nearby.includes("增加") || nearby.includes("惡化") || nearby.includes("+");
    const mentionsDown = nearby.includes("下降") || nearby.includes("減少") || nearby.includes("改善") || nearby.includes("-");
    if ((isUp && mentionsUp) || (!isUp && mentionsDown)) {
      trendCorrect++;
    }
  }
  const trend_accuracy = trendChecked > 0 ? trendCorrect / trendChecked : 1;

  // 3. has_severity_assessment: any severity keyword present
  const has_severity_assessment = SEVERITY_KEYWORDS.some((kw) =>
    lower.includes(kw.toLowerCase()),
  ) ? 1 : 0;

  // 4. recommendation_specificity: path-specific recommendations
  const actionKeywords = ["GSC", "canonical", "noindex", "robots", "hreflang", "合併", "檢查", "建議", "行動"];
  const hasPathSpecificAdvice = data.paths.filter((p) => {
    if (!content.includes(p.segment)) return false;
    const segIdx = content.indexOf(p.segment);
    const nearby = content.slice(segIdx, segIdx + 500);
    return actionKeywords.some((kw) => nearby.includes(kw));
  }).length;
  const recommendation_specificity = data.paths.length > 0
    ? Math.min(hasPathSpecificAdvice / Math.max(data.paths.length / 2, 1), 1)
    : 1;

  // 5. data_fidelity: correct numbers cited
  let dataCorrect = 0;
  let dataChecked = 0;
  for (const p of data.paths) {
    if (p.value_a != null) {
      dataChecked++;
      const numStr = p.value_a.toLocaleString("en-US");
      if (content.includes(numStr) || content.includes(String(p.value_a))) {
        dataCorrect++;
      }
    }
  }
  const data_fidelity = dataChecked > 0 ? dataCorrect / dataChecked : 1;

  const overall = (
    path_coverage +
    trend_accuracy +
    has_severity_assessment +
    recommendation_specificity +
    data_fidelity
  ) / 5;

  return {
    path_coverage,
    trend_accuracy,
    has_severity_assessment,
    recommendation_specificity,
    data_fidelity,
    overall,
  };
}
