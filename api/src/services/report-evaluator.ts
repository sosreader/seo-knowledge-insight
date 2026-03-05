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
  /** 1 if report contains /admin/seoInsight/chunk/ links, else 0 */
  has_kb_links: number;
  /** Proportion of alert metric names mentioned in section 五 (0–1) */
  alert_coverage: number;
  /** Average of the 5 scores above */
  overall: number;
  /** 1 if report contains Claude Code LLM-augmented sections, else 0 (not counted in overall) */
  llm_augmented: number;
}

// ── Constants ─────────────────────────────────────────────────────────

const SECTION_MARKERS = [
  "## 一、",
  "## 二、",
  "## 三、",
  "## 四、",
  "## 五、",
  "## 六、",
] as const;

const RESEARCH_KEYWORDS = [
  "Semrush",
  "GSC",
  "Backlinko",
  "First Page Sage",
  "NavBoost",
  "E-E-A-T",
  "arxiv",
] as const;

const KB_LINK_RE = /\/admin\/seoInsight\/chunk\/[0-9a-f]+/g;

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
    };
  }

  // 1. section_coverage: count ## 一、 through ## 六、
  const sectionsFound = SECTION_MARKERS.filter((marker) =>
    content.includes(marker),
  ).length;
  const section_coverage = sectionsFound / SECTION_MARKERS.length;

  // 2. kb_citation_count: count unique /admin/seoInsight/chunk/{id} links
  const kbMatches = content.match(KB_LINK_RE) ?? [];
  const uniqueKbLinks = new Set(kbMatches).size;
  // Also count http/https external links in 知識庫引用 section
  const externalLinkRe = /https?:\/\/[^\s)>]+/g;
  const kbSection = extractSection(content, "## 六、");
  const externalLinks = kbSection.match(externalLinkRe) ?? [];
  const totalCitations = uniqueKbLinks + externalLinks.length;
  const kb_citation_count = Math.min(totalCitations / 6, 1);

  // 3. has_research_citations: any known research keyword present
  const has_research_citations = RESEARCH_KEYWORDS.some((kw) =>
    content.includes(kw),
  )
    ? 1
    : 0;

  // 4. has_kb_links: /admin/seoInsight/chunk/ pattern anywhere
  const has_kb_links = KB_LINK_RE.test(content) ? 1 : 0;

  // 5. alert_coverage: alert names appearing in 五、本週優先行動清單
  const actionSection = extractSection(content, "## 五、");
  let alert_coverage = 0;
  if (alertNames.length > 0) {
    const mentioned = alertNames.filter((name) =>
      actionSection.includes(name),
    ).length;
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
    content.includes("AI 輔助") || content.includes("AI 解讀") ? 1 : 0;

  return {
    section_coverage,
    kb_citation_count,
    has_research_citations,
    has_kb_links,
    alert_coverage,
    overall,
    llm_augmented,
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
