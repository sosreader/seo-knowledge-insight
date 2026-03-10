/**
 * Rule-based report quality evaluator — no LLM API required.
 *
 * Scores a generated report across 5 dimensions and returns an overall score.
 * Used for online scoring (Laminar scoreEvent) immediately after generation.
 */

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
  /** Proportion of alert metric names mentioned in section 五 (0–1) */
  alert_coverage: number;
  /** Average of the 5 scores above */
  overall: number;
  /** 1 if report contains Claude Code LLM-augmented sections, else 0 (not counted in overall) */
  llm_augmented: number;
  /** 1 if report contains ## 檢索未索引分析 section, else 0 (independent metric, not counted in overall) */
  has_crawled_not_indexed_section: number;
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

  // 5. alert_coverage: alert names appearing in 五、本週優先行動清單
  // alertNames should be only the metrics that triggered alerts (CORE + threshold breach),
  // not all metric keys. When no alerts exist, coverage defaults to 1 (nothing to cover).
  // Uses fuzzy matching: "AMP Article" matches "AMP Article Ratio", partial substring OK.
  const actionSection = extractSection(body, "## 五、");
  let alert_coverage = 0;
  if (alertNames.length === 0) {
    alert_coverage = 1; // No alerts → nothing to cover → full credit
  } else {
    const sectionLower = actionSection.toLowerCase();
    const mentioned = alertNames.filter((name) => {
      const nameLower = name.toLowerCase();
      // Exact match or fuzzy: alert name is substring of section content
      if (sectionLower.includes(nameLower)) return true;
      // Reverse: section contains a word-level match (e.g. "News(new)" → "News")
      const coreName = nameLower.replace(/\s*\(.*?\)\s*/g, "").trim();
      if (coreName.length >= 2 && sectionLower.includes(coreName)) return true;
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

  const llm_augmented =
    body.includes("AI 輔助") || body.includes("AI 解讀") ? 1 : 0;

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
