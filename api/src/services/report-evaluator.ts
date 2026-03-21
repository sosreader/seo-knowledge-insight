/**
 * Rule-based report quality evaluator — no LLM API required.
 *
 * L1: 5 binary/near-binary dimensions (section_coverage, kb_citation_count, etc.)
 * L2: 6 continuous rule-based dimensions (cross_metric_reasoning, action_specificity, etc.)
 * L3: 3 LLM-as-Judge dimensions (reasoning_depth, actionability, insight_originality) — external
 *
 * composite_v2 replaces saturated `overall` with a weighted blend of L1+L2 (+ optional L3).
 */

import { evaluateReportL2, type ReportEvalL2Result } from "./report-evaluator-l2.js";

// ── Types ─────────────────────────────────────────────────────────────

export interface ReportEvalResult {
  /** Proportion of the 6 expected section headings present (0–1) */
  section_coverage: number;
  /** KB citation links found / 6, capped at 1.0 */
  kb_citation_count: number;
  /** 1 if report contains industry research references, else 0 */
  has_research_citations: number;
  /** 1 if report contains /admin/seoInsight/{id} links, else 0 */
  has_kb_links: number;
  /** Proportion of alert metric names mentioned in action list + situation snapshot (0–1) */
  alert_coverage: number;
  /** Average of the 5 scores above */
  overall: number;
  /** 1 if report contains Claude Code LLM-augmented sections, else 0 (not counted in overall) */
  llm_augmented: number;
  /** 1 if report contains ## 檢索未索引分析 section, else 0 (independent metric, not counted in overall) */
  has_crawled_not_indexed_section: number;
}

/** L3 LLM-as-Judge scores (injected externally, e.g. from /evaluate-report-quality) */
export interface ReportEvalL3Scores {
  /** Multi-step causal reasoning depth (1–5) */
  reasoning_depth: number;
  /** Actionability of recommendations (1–5) */
  actionability: number;
  /** Non-obvious insight originality (1–5) */
  insight_originality: number;
}

/** Full V2 evaluation result: L1 + L2 + optional L3 + composite_v2 */
export interface ReportEvalV2Result {
  /** L1 result (backward-compatible) */
  l1: ReportEvalResult;
  /** L2 continuous rule-based metrics */
  l2: ReportEvalL2Result;
  /** L3 LLM-as-Judge scores (null if not provided) */
  l3: ReportEvalL3Scores | null;
  /** Whether L3 was skipped (true when l3 is null) */
  l3_skipped: boolean;
  /** Weighted composite replacing saturated `overall` */
  composite_v2: number;
}

// ── Constants ─────────────────────────────────────────────────────────

const SECTION_MARKERS = [
  "## 一、",
  "## 二、",
  "## 三、",
  "## 四、",
  "## 五、",
  "## 六、",
  "## 七、",
] as const;

// "GSC" is intentionally excluded — it appears in every SEO report and would
// cause this metric to be always 1, defeating its purpose.
const RESEARCH_KEYWORDS = [
  "Semrush",
  "Backlinko",
  "First Page Sage",
  "NavBoost",
  "E-E-A-T",
  "arxiv",
] as const;

// Factory to avoid shared lastIndex state across calls (global flag regex).
const kbLinkRe = (): RegExp => /\/admin\/seoInsight\/(?:[0-9a-f]{16}|\d+)/g;

// Strip trailing HTML comment blocks so they don't pollute section extraction.
const TRAILING_COMMENTS_RE = /\n<!--[\s\S]*?-->\s*$/g;

// ── Evaluator ─────────────────────────────────────────────────────────

/**
 * Evaluate report quality using rule-based heuristics.
 *
 * @param content      Generated report Markdown string
 * @param alertNames   Names of alert metrics detected in this report cycle
 */
export function evaluateReport(
  content: string,
  alertNames: readonly string[],
): ReportEvalResult {
  if (!content || content.trim().length === 0) {
    return {
      section_coverage: 0,
      kb_citation_count: 0,
      has_research_citations: 0,
      has_kb_links: 0,
      alert_coverage: 0,
      overall: 0,
      llm_augmented: 0,
      has_crawled_not_indexed_section: 0,
    };
  }

  // Strip trailing HTML comment blocks (<!-- citations [...] -->, <!-- report_meta {...} -->)
  // so they don't inflate link counts or pollute section extraction.
  const body = content.replace(TRAILING_COMMENTS_RE, "");

  // 1. section_coverage: count ## 一、 through ## 六、
  const sectionsFound = SECTION_MARKERS.filter((marker) =>
    body.includes(marker),
  ).length;
  const section_coverage = sectionsFound / SECTION_MARKERS.length;

  // 2. kb_citation_count: count unique /admin/seoInsight/{id} links in body
  const kbMatches = body.match(kbLinkRe()) ?? [];
  const uniqueKbLinks = new Set(kbMatches).size;
  // Also count http/https external links in 知識庫引用 section (body only, no comments)
  const externalLinkRe = /https?:\/\/[^\s)>]+/g;
  const kbSection = extractSection(body, "## 七、");
  const externalLinks = kbSection.match(externalLinkRe) ?? [];
  const totalCitations = uniqueKbLinks + externalLinks.length;
  const kb_citation_count = Math.min(totalCitations / 6, 1);

  // 3. has_research_citations: any known research keyword present
  const has_research_citations = RESEARCH_KEYWORDS.some((kw) =>
    body.includes(kw),
  )
    ? 1
    : 0;

  // 4. has_kb_links: /admin/seoInsight/{id} pattern anywhere in body
  const has_kb_links = kbLinkRe().test(body) ? 1 : 0;

  // 5. alert_coverage: alert names appearing anywhere in the report body
  // Search full body — alert names are specific enough to avoid false positives.
  const searchText = body.toLowerCase();

  let alert_coverage = 0;
  if (alertNames.length === 0) {
    alert_coverage = 1; // No alerts → nothing to cover → full credit
  } else {
    const mentioned = alertNames.filter((name) => {
      const nameLower = name.toLowerCase();
      if (searchText.includes(nameLower)) return true;
      // Strip parenthetical suffix: "News(new)" → "News"
      const coreName = nameLower.replace(/\s*\(.*?\)\s*/g, "").trim();
      if (coreName.length >= 2 && searchText.includes(coreName)) return true;
      // Strip "KW:" / "KW: " prefix: "KW: 影評" → "影評"
      const kwStripped = nameLower.replace(/^kw:\s*/, "").trim();
      if (
        kwStripped !== nameLower &&
        kwStripped.length >= 2 &&
        searchText.includes(kwStripped)
      )
        return true;
      return false;
    }).length;
    alert_coverage = mentioned / alertNames.length;
  }

  const overall =
    (section_coverage +
      kb_citation_count +
      has_research_citations +
      has_kb_links +
      alert_coverage) /
    5;

  // Detect LLM augmentation via report_meta generation_mode OR legacy markers
  let llm_augmented = 0;
  const metaMatch = content.match(/<!--\s*report_meta\s+(\{.*?\})\s*-->/);
  if (metaMatch) {
    try {
      const meta = JSON.parse(metaMatch[1]);
      if (meta.generation_mode === "claude-code" || meta.generation_mode === "openai") {
        llm_augmented = 1;
      }
    } catch {
      // ignore parse errors
    }
  }
  // Fallback: legacy API template markers
  if (llm_augmented === 0 && (body.includes("AI 輔助") || body.includes("AI 解讀"))) {
    llm_augmented = 1;
  }

  const has_crawled_not_indexed_section = body.includes("## 檢索未索引分析") ? 1 : 0;

  return {
    section_coverage,
    kb_citation_count,
    has_research_citations,
    has_kb_links,
    alert_coverage,
    overall,
    llm_augmented,
    has_crawled_not_indexed_section,
  };
}

// ── V2 Evaluator ─────────────────────────────────────────────────────

/**
 * Compute composite_v2 score from L1, L2, and optional L3.
 *
 * With L3:
 *   L1_overall×0.20 + cross_metric×0.10 + action_specificity×0.10
 *   + data_evidence×0.08 + citation_integration×0.07
 *   + quadrant_judgment×0.05 + section_depth_var×0.05
 *   + reasoning_depth/5×0.15 + actionability/5×0.10
 *   + insight_originality/5×0.10
 *
 * Without L3 (auto fallback):
 *   L1_overall×0.30 + cross_metric×0.15 + action_specificity×0.15
 *   + data_evidence×0.12 + citation_integration×0.10
 *   + quadrant_judgment×0.10 + section_depth_var×0.08
 */
export function computeCompositeV2(
  l1: ReportEvalResult,
  l2: ReportEvalL2Result,
  l3: ReportEvalL3Scores | null,
): number {
  if (l3) {
    // Clamp L3 scores to [0, 5] to prevent composite exceeding [0, 1]
    const rd = Math.max(0, Math.min(5, l3.reasoning_depth));
    const ac = Math.max(0, Math.min(5, l3.actionability));
    const io = Math.max(0, Math.min(5, l3.insight_originality));
    return (
      l1.overall * 0.20 +
      l2.cross_metric_reasoning * 0.10 +
      l2.action_specificity * 0.10 +
      l2.data_evidence_ratio * 0.08 +
      l2.citation_integration * 0.07 +
      l2.quadrant_judgment * 0.05 +
      l2.section_depth_variance * 0.05 +
      (rd / 5) * 0.15 +
      (ac / 5) * 0.10 +
      (io / 5) * 0.10
    );
  }

  // No L3 — redistribute weights to L1+L2 only
  return (
    l1.overall * 0.30 +
    l2.cross_metric_reasoning * 0.15 +
    l2.action_specificity * 0.15 +
    l2.data_evidence_ratio * 0.12 +
    l2.citation_integration * 0.10 +
    l2.quadrant_judgment * 0.10 +
    l2.section_depth_variance * 0.08
  );
}

/**
 * Full V2 evaluation: L1 + L2 + composite_v2.
 *
 * L3 is not computed here (requires LLM) — pass it in via `l3Scores` param
 * or leave null for auto-fallback composite weights.
 */
export function evaluateReportV2(
  content: string,
  alertNames: readonly string[],
  l3Scores?: ReportEvalL3Scores | null,
): ReportEvalV2Result {
  const l1 = evaluateReport(content, alertNames);
  const l2 = evaluateReportL2(content);
  const l3 = l3Scores ?? null;

  return {
    l1,
    l2,
    l3,
    l3_skipped: l3 === null,
    composite_v2: computeCompositeV2(l1, l2, l3),
  };
}

// ── Helpers ───────────────────────────────────────────────────────────

/**
 * Extract text from a given section heading until the next ## heading.
 */
function extractSection(content: string, heading: string): string {
  const startIdx = content.indexOf(heading);
  if (startIdx === -1) return "";
  const nextHeadingIdx = content.indexOf("\n## ", startIdx + heading.length);
  return nextHeadingIdx === -1
    ? content.slice(startIdx)
    : content.slice(startIdx, nextHeadingIdx);
}
