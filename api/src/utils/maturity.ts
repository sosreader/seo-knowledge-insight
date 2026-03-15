/**
 * Maturity-level utilities — shared across chat, search, report, and session features.
 *
 * SEO maturity levels (L1-L4) describe a client's SEO sophistication:
 *   L1 起步期 — basic awareness, manual processes
 *   L2 建置期 — structured processes, systematic tracking
 *   L3 優化期 — data-driven optimization, automated workflows
 *   L4 領先期 — predictive analytics, cross-channel integration
 */

import type { QAItem } from "../store/qa-store.js";

import { z } from "zod";

export type MaturityLevel = "L1" | "L2" | "L3" | "L4";

export type MaturityDimension = "strategy" | "process" | "keywords" | "metrics";

export const maturityLevelSchema = z.enum(["L1", "L2", "L3", "L4"]);

const VALID_LEVELS: ReadonlySet<string> = new Set(["L1", "L2", "L3", "L4"]);

/** Maturity dimensions shared across report and search features. */
export const DIMENSIONS: ReadonlyArray<{ key: MaturityDimension; label: string }> = [
  { key: "strategy", label: "策略" },
  { key: "process", label: "流程" },
  { key: "keywords", label: "關鍵字" },
  { key: "metrics", label: "指標" },
];

/**
 * Maps metric name substrings to maturity dimensions.
 * Unknown metrics return null (no label) — conservative by design.
 *
 * Note: "strategy" has no metric mappings intentionally — GSC/GA4 metrics
 * are operational, not strategic. Strategy upgrade labels come from the
 * Claude Code full-generation mode where the LLM makes that judgment.
 */
export const METRIC_MATURITY_DIMENSION_MAP: Readonly<Record<string, MaturityDimension>> = {
  "AMP Article": "process",
  "AMP (non-Rich)": "process",
  "Google News": "process",
  "News(new)": "process",
  "CTR": "keywords",
  "曝光": "keywords",
  "點擊": "keywords",
  "Discover": "keywords",
  "Image": "keywords",
  "有效 (Coverage)": "metrics",
  "檢索未索引": "metrics",
  "工作階段總數（七天）": "metrics",
  "Organic Search (工作階段)": "metrics",
};

export const MATURITY_LEVEL_DESCRIPTIONS: Readonly<Record<MaturityLevel, string>> = {
  L1: "起步期：SEO 基礎認知階段，手動操作為主，尚未建立系統化流程",
  L2: "建置期：已有結構化流程，開始系統性追蹤關鍵指標",
  L3: "優化期：數據驅動的優化決策，部分流程已自動化",
  L4: "領先期：預測性分析能力，跨通路整合，持續創新",
};

/**
 * Parse and validate a maturity level string.
 * Returns null for invalid/missing input (never throws).
 */
export function parseMaturityLevel(raw: string | undefined | null): MaturityLevel | null {
  if (!raw) return null;
  const upper = raw.trim().toUpperCase();
  return VALID_LEVELS.has(upper) ? (upper as MaturityLevel) : null;
}

/**
 * Build maturity context string for injection into chat system prompts.
 * Guides the LLM to adjust response depth based on the client's maturity level.
 */
const MATURITY_CONTEXT: Readonly<Record<MaturityLevel, string>> = {
  L1: [
    "目前客戶處於 SEO 起步期（L1）。",
    "請用淺顯易懂的語言說明，避免使用進階術語（如「歸因分析」「預測性模型」）。",
    "聚焦在「為什麼要做」和「第一步怎麼開始」，提供具體的入門建議。",
    "建議的行動應是低門檻、立即可執行的。",
  ].join("\n"),
  L2: [
    "目前客戶處於 SEO 建置期（L2）。",
    "客戶已理解基礎概念，可使用標準 SEO 術語。",
    "聚焦在「如何系統化」和「建立可追蹤的流程」。",
    "建議應包含具體的 KPI 設定和追蹤方法。",
  ].join("\n"),
  L3: [
    "目前客戶處於 SEO 優化期（L3）。",
    "客戶熟悉數據分析，可深入討論進階策略。",
    "聚焦在「如何用數據優化」和「自動化流程設計」。",
    "建議應包含 A/B 測試、數據分析框架、自動化工具整合。",
  ].join("\n"),
  L4: [
    "目前客戶處於 SEO 領先期（L4）。",
    "客戶具備預測性分析能力，討論可涵蓋前沿話題。",
    "聚焦在「跨通路整合」「AI 驅動策略」和「行業趨勢預判」。",
    "建議應涵蓋預測模型、競爭情報、技術架構最佳實踐。",
  ].join("\n"),
};

export function buildMaturityContext(level: MaturityLevel): string {
  return MATURITY_CONTEXT[level];
}

/**
 * Apply maturity boost to search results.
 * Items matching the specified maturity level get a 1.15x score multiplier.
 * Returns a new sorted array (immutable — original is not mutated).
 *
 * When maturityLevel is null, returns the input unchanged.
 */
export function applyMaturityBoost(
  hits: ReadonlyArray<{ item: QAItem; score: number }>,
  maturityLevel: MaturityLevel | null,
): ReadonlyArray<{ item: QAItem; score: number }> {
  if (!maturityLevel) return hits;

  const BOOST_FACTOR = 1.15;

  const boosted = hits.map(({ item, score }) => ({
    item,
    score: item.maturity_relevance === maturityLevel ? score * BOOST_FACTOR : score,
  }));

  return [...boosted].sort((a, b) => b.score - a.score);
}

/**
 * Look up the maturity dimension for a given metric name.
 * Tries exact match first, then substring match.
 * Returns null for unrecognized metrics (conservative — no label).
 */
export function getDimensionForMetric(metricName: string): MaturityDimension | null {
  if (metricName in METRIC_MATURITY_DIMENSION_MAP) {
    return METRIC_MATURITY_DIMENSION_MAP[metricName]!;
  }
  for (const [key, dim] of Object.entries(METRIC_MATURITY_DIMENSION_MAP)) {
    if (metricName.includes(key)) return dim;
  }
  return null;
}

/**
 * Build an inline upgrade label like `**[流程 L2→L3]**` for a given dimension.
 * Returns null when:
 *  - dimension not found in maturity data
 *  - dimension is already at L4 (no upgrade target)
 *  - maturity level format is invalid
 */
export function buildMaturityUpgradeLabel(
  dimension: MaturityDimension,
  maturity: Readonly<Record<string, string>>,
): string | null {
  const level = maturity[dimension];
  if (!level) return null;
  const match = /^L(\d+)$/i.exec(level);
  if (!match) return null;
  const currentNum = parseInt(match[1]!, 10);
  if (currentNum >= 4) return null;
  const dimLabel = DIMENSIONS.find((d) => d.key === dimension)?.label ?? dimension;
  return `**[${dimLabel} ${level}→L${currentNum + 1}]**`;
}

/**
 * Build a single-line blockquote callout summarizing maturity levels.
 * Placed at the top of Section 5 (priority actions), before the action list.
 * Returns null when maturity data is empty or has no valid levels.
 */
export function buildMaturityCallout(
  maturity: Readonly<Record<string, string>>,
): string | null {
  const parts: string[] = [];
  for (const { key, label } of DIMENSIONS) {
    const level = maturity[key];
    if (level && /^L\d+$/i.test(level)) {
      parts.push(`${label} ${level}`);
    }
  }
  if (parts.length === 0) return null;
  return `> 成熟度參考：${parts.join(" / ")}`;
}

/**
 * Build maturity reference block for report S5 (action checklist) section.
 * Outputs formatted maturity context with dimension levels and upgrade labels.
 *
 * @deprecated Prefer `buildMaturityCallout()` (compact 1-line blockquote) +
 * `buildMaturityUpgradeLabel()` (inline action labels) for report S5.
 * Retained for external consumers (e.g. Claude Code full-generation fallback).
 */
export function buildReportMaturityBlock(
  maturity: Readonly<Record<string, string>>,
): string {
  const lines: string[] = ["**成熟度參考**："];

  const levelParts: string[] = [];
  for (const { key, label } of DIMENSIONS) {
    const level = maturity[key];
    if (level && /^L\d+$/i.test(level)) {
      levelParts.push(`${label} ${level}`);
    }
  }

  if (levelParts.length > 0) {
    lines.push(levelParts.join(" / "));
  }

  // Generate upgrade labels [LX→LY] for dimensions not at L4
  const upgrades: string[] = [];
  for (const { key, label } of DIMENSIONS) {
    const level = maturity[key];
    if (!level) continue;
    const match = /^L(\d+)$/i.exec(level);
    if (!match) continue; // skip invalid values like "LNaN"
    const currentNum = parseInt(match[1]!, 10);
    if (currentNum >= 4) continue;
    const nextLevel = `L${currentNum + 1}`;
    upgrades.push(`[${label} ${level}→${nextLevel}]`);
  }

  if (upgrades.length > 0) {
    lines.push(`升級目標：${upgrades.join(" ")}`);
  }

  return lines.join("\n");
}
