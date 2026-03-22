/**
 * L2 Rule-based report quality evaluator — continuous metrics.
 *
 * 6 pure functions producing 0–1 scores that discriminate report quality
 * better than the binary L1 metrics (which saturate at 0.97–1.0).
 *
 * No external API required.
 */

// ── Types ─────────────────────────────────────────────────────────────

export interface ReportEvalL2Result {
  /** Cross-metric causal reasoning density (0–1) */
  cross_metric_reasoning: number;
  /** Ratio of specific vs vague action items (0–1) */
  action_specificity: number;
  /** Data evidence density: percentages + large numbers (0–1) */
  data_evidence_ratio: number;
  /** Inline citation usage vs tail-only stacking (0–1) */
  citation_integration: number;
  /** Quadrant analysis presence + explanation (0 / 0.5 / 1.0) */
  quadrant_judgment: number;
  /** Section word-count balance: 1 - (std / mean) (0–1) */
  section_depth_variance: number;
  /** Paragraphs comparing both weekly and monthly trends (0–1) */
  temporal_dual_frame: number;
  /** 🔴/🟡/🟢 action item distribution balance (0–1) */
  priority_balance: number;
  /** Structured 現象→原因→行動 analysis blocks (0–1) */
  causal_chain: number;
  /** Single "most important" recommendation summary present (0 or 1) */
  top_recommendation: number;
}

// ── SEO metric vocabulary ─────────────────────────────────────────────

const SEO_METRICS = [
  "CTR",
  "曝光",
  "點擊",
  "排名",
  "索引",
  "Discover",
  "CLS",
  "LCP",
  "FID",
  "INP",
  "Core Web Vitals",
  "反向連結",
  "外部連結",
  "內部連結",
  "跳出率",
  "停留時間",
  "轉換率",
  "流量",
  "有機搜尋",
  "AI Overview",
  "檢索未索引",
  "收錄",
  "爬取",
  "網頁速度",
  "Position",
  "E-E-A-T",
  "佔比",
  "覆蓋率",
] as const;

/** Causal connectors that signal cross-metric reasoning */
const CAUSAL_CONNECTORS = [
  "導致",
  "因此",
  "因為",
  "表示",
  "意味著",
  "這表示",
  "這意味",
  "由於",
  "造成",
  "然而",
  "但",
  "儘管",
  "雖然",
  "進而",
  "以致",
  "所以",
  "反映",
  "顯示",
  "源自",
  "歸因",
] as const;

/** Specific action verbs/tools that indicate actionable advice */
const SPECIFIC_ACTION_PATTERNS = [
  /在\s*(?:GSC|Search Console|PageSpeed|Chrome|Screaming Frog|Ahrefs|Semrush)/,
  /篩選/,
  /檢查/,
  /驗證/,
  /使用\s*\S+\s*(?:面板|報表|工具)/,
  /部署後\s*\d+/,
  /設定\s*\S+/,
  /加入\s*\S+/,
  /移除\s*\S+/,
  /重寫/,
  /優化\s*(?:title|標題|description|meta)/i,
  /補上/,
  /修復/,
  /排查/,
  /測試/,
] as const;

/** Vague/passive action patterns */
const VAGUE_ACTION_PATTERNS = [
  /^-?\s*注意/,
  /^-?\s*持續觀察/,
  /^-?\s*關注/,
  /^-?\s*需要(?:改善|注意|觀察)/,
  /^-?\s*觀察/,
  /^-?\s*留意/,
  /^-?\s*追蹤(?!.*(?:工具|報表|面板))/,
] as const;

/** Quadrant keywords */
const QUADRANT_KEYWORDS = [
  "高曝光低點擊",
  "低曝光高點擊",
  "高曝光高點擊",
  "低曝光低點擊",
] as const;

/** Explanation signal after quadrant keyword */
const QUADRANT_EXPLANATION_SIGNALS = [
  "建議",
  "表示",
  "因為",
  "利基",
  "優勢",
  "需要",
  "應該",
  "代表",
  "意味",
] as const;

// ── Section heading markers ───────────────────────────────────────────

const SECTION_MARKERS = [
  "## 一、",
  "## 二、",
  "## 三、",
  "## 四、",
  "## 五、",
  "## 六、",
  "## 七、",
] as const;

// ── Pure functions ────────────────────────────────────────────────────

/**
 * Measure cross-metric causal reasoning density.
 *
 * Scans for paragraphs containing a causal connector AND ≥2 distinct SEO metric names
 * in the same paragraph. Returns count / 5 (capped at 1.0).
 */
export function crossMetricReasoning(content: string): number {
  if (!content || content.trim().length === 0) return 0;

  const paragraphs = content.split(/\n{1,}/).filter((p) => p.trim().length > 0);
  let crossMetricCount = 0;

  for (const para of paragraphs) {
    const hasCausal = CAUSAL_CONNECTORS.some((c) => para.includes(c));
    if (!hasCausal) continue;

    const metricsFound = new Set<string>();
    for (const metric of SEO_METRICS) {
      if (para.includes(metric)) {
        metricsFound.add(metric);
      }
    }

    if (metricsFound.size >= 2) {
      crossMetricCount++;
    }
  }

  return Math.min(crossMetricCount / 15, 1.0);
}

/**
 * Measure action item specificity.
 *
 * Extracts lines starting with `-` (action items), then scores each as
 * specific (matches tool/verb patterns) or vague (matches passive patterns).
 * Returns specific / total ratio.
 */
export function actionSpecificity(content: string): number {
  if (!content || content.trim().length === 0) return 0;

  const actionLines = content
    .split("\n")
    .filter((line) => /^\s*(?:-|\d+\.)\s/.test(line))
    .map((line) => line.trim());

  if (actionLines.length === 0) return 0;

  let specificCount = 0;

  for (const line of actionLines) {
    if (SPECIFIC_ACTION_PATTERNS.some((p) => p.test(line))) {
      specificCount++;
    }
  }

  // All action lines count as denominator (not just specific + vague)
  return specificCount / actionLines.length;
}

const PERCENT_RE = /[+-]?\d+(?:\.\d+)?%/;
const LARGE_NUMBER_RE = /\b(?:\d{1,3}(?:,\d{3})+|\d{3,})\b(?!%)/g;

/**
 * Measure data evidence density at paragraph level.
 *
 * Splits content into paragraphs, counts paragraphs containing a percentage
 * pattern OR a large number (≥100). Returns count / 15 (capped at 1.0).
 */
export function dataEvidenceRatio(content: string): number {
  if (!content || content.trim().length === 0) return 0;

  const paragraphs = content.split(/\n\n+/).filter((p) => p.trim().length > 0);

  let count = 0;
  for (const para of paragraphs) {
    if (PERCENT_RE.test(para)) {
      count++;
      continue;
    }
    const numberMatches = para.match(LARGE_NUMBER_RE) ?? [];
    const hasLargeNumber = numberMatches.some((n) => {
      const num = parseInt(n.replace(/,/g, ""), 10);
      return num >= 100;
    });
    if (hasLargeNumber) {
      count++;
    }
  }

  return Math.min(count / 70, 1.0);
}

/**
 * Measure citation integration quality.
 *
 * Compares inline `[N]` references (in body, before ## 七、) vs total `[N]` references.
 * High score = citations woven into analysis; Low score = all stacked at the end.
 */
export function citationIntegration(content: string): number {
  if (!content || content.trim().length === 0) return 0;

  // Find all [N] citation markers in entire content
  const allCitations = content.match(/\[(\d+)\]/g) ?? [];
  if (allCitations.length === 0) return 0;

  // Split at ## 七、(knowledge base section) to separate body from references
  const refSectionIdx = content.indexOf("## 七、");
  const body = refSectionIdx === -1 ? content : content.slice(0, refSectionIdx);

  // Count unique inline citations in body
  const bodyCitations = body.match(/\[(\d+)\]/g) ?? [];
  const uniqueBodyCitations = new Set(bodyCitations);
  const uniqueAllCitations = new Set(allCitations);

  if (uniqueAllCitations.size === 0) return 0;

  const inline_ratio = uniqueBodyCitations.size / uniqueAllCitations.size;

  // Section diversity: how many of the 7 sections contain a [N] citation
  let sectionsWithCitation = 0;
  for (let i = 0; i < SECTION_MARKERS.length; i++) {
    const marker = SECTION_MARKERS[i];
    const startIdx = content.indexOf(marker);
    if (startIdx === -1) continue;
    const nextIdx =
      i + 1 < SECTION_MARKERS.length
        ? content.indexOf(SECTION_MARKERS[i + 1], startIdx + marker.length)
        : -1;
    const sectionText =
      nextIdx === -1
        ? content.slice(startIdx)
        : content.slice(startIdx, nextIdx);
    if (/\[\d+\]/.test(sectionText)) {
      sectionsWithCitation++;
    }
  }
  const section_diversity = sectionsWithCitation / SECTION_MARKERS.length;

  return inline_ratio * section_diversity;
}

/**
 * Detect quadrant analysis with explanation.
 *
 * Returns:
 * - 1.0 if quadrant keyword + explanation signal found
 * - 0.5 if quadrant keyword found without explanation
 * - 0.0 if no quadrant keyword found
 */
export function quadrantJudgment(content: string): number {
  if (!content || content.trim().length === 0) return 0;

  let hasQuadrant = false;
  let hasExplanation = false;

  for (const kw of QUADRANT_KEYWORDS) {
    if (!content.includes(kw)) continue;
    hasQuadrant = true;

    // Check if explanation follows within the same paragraph or nearby text
    const idx = content.indexOf(kw);
    const nearby = content.slice(idx, idx + 200);
    if (QUADRANT_EXPLANATION_SIGNALS.some((sig) => nearby.includes(sig))) {
      hasExplanation = true;
      break;
    }
  }

  if (!hasQuadrant) return 0;
  return hasExplanation ? 1.0 : 0.5;
}

/**
 * Measure section depth variance (word-count balance).
 *
 * Extracts text for each ## section, counts characters, then computes
 * 1 - (std / mean). Balanced sections → high score, lopsided → low score.
 */
export function sectionDepthVariance(content: string): number {
  if (!content || content.trim().length === 0) return 0;

  const sectionLengths: number[] = [];

  for (let i = 0; i < SECTION_MARKERS.length; i++) {
    const marker = SECTION_MARKERS[i];
    const startIdx = content.indexOf(marker);
    if (startIdx === -1) continue;

    // Find end: next ## heading or end of content
    const afterMarker = startIdx + marker.length;
    const nextHeadingIdx = content.indexOf("\n## ", afterMarker);
    const sectionText =
      nextHeadingIdx === -1
        ? content.slice(afterMarker)
        : content.slice(afterMarker, nextHeadingIdx);

    // Use character count (Chinese text doesn't split well on spaces)
    const charCount = sectionText.replace(/\s/g, "").length;
    sectionLengths.push(charCount);
  }

  if (sectionLengths.length < 2) return 0;

  const mean =
    sectionLengths.reduce((sum, n) => sum + n, 0) / sectionLengths.length;
  if (mean === 0) return 0;

  const variance =
    sectionLengths.reduce((sum, n) => sum + (n - mean) ** 2, 0) /
    sectionLengths.length;
  const std = Math.sqrt(variance);

  // Coefficient of variation: std / mean
  // Score = 1 - CV, clamped to [0, 1]
  const cv = std / mean;
  return Math.max(0, Math.min(1, 1 - cv));
}

// ── New L2 metrics (v3) ──────────────────────────────────────────────

const WEEK_PCT_RE = /週.*?[+-]?\d+(?:\.\d+)?%|[+-]?\d+(?:\.\d+)?%.*?週/;
const MONTH_PCT_RE = /月.*?[+-]?\d+(?:\.\d+)?%|[+-]?\d+(?:\.\d+)?%.*?月/;

/**
 * Measure temporal dual-frame analysis.
 *
 * Counts LINES with BOTH weekly AND monthly percentage data.
 * Returns count / 12 (capped at 1.0). Stricter than paragraph-level matching.
 */
export function temporalDualFrame(content: string): number {
  if (!content || content.trim().length === 0) return 0;

  let count = 0;
  for (const line of content.split("\n")) {
    if (WEEK_PCT_RE.test(line) && MONTH_PCT_RE.test(line)) {
      count++;
    }
  }
  return Math.min(count / 15, 1.0);
}

/**
 * Measure action priority balance — count lines containing each emoji.
 *
 * Thresholds: 🔴≥4, 🟡≥3, 🟢≥2 (higher than v2 to increase discrimination).
 */
export function priorityBalance(content: string): number {
  if (!content || content.trim().length === 0) return 0;

  const lines = content.split("\n");
  let red = 0;
  let yellow = 0;
  let green = 0;

  for (const ln of lines) {
    if (ln.includes("🔴")) red++;
    if (ln.includes("🟡")) yellow++;
    if (ln.includes("🟢")) green++;
  }

  const total = red + yellow + green;
  if (total === 0) return 0;

  return (
    (Math.min(red / 4, 1.0) + Math.min(yellow / 3, 1.0) + Math.min(green / 2, 1.0)) / 3
  );
}

/**
 * Count structured **現象** → **原因** → **行動** analysis blocks.
 *
 * Returns count / 5 (capped at 1.0).
 */
export function causalChain(content: string): number {
  if (!content || content.trim().length === 0) return 0;

  const blocks = content.match(/\*\*現象\*\*[\s\S]*?\*\*原因\*\*[\s\S]*?\*\*行動\*\*/g) ?? [];
  return Math.min(blocks.length / 5, 1.0);
}

const TOP_REC_REASON_PATTERNS = [
  /雖然/, /因為/, /理由/, /原因/, /而/, /但/, /相比/, /優先/,
] as const;

/**
 * Graded: has 💡/最值得投入 (0.5) + has justification reason (0.5).
 */
export function topRecommendation(content: string): number {
  if (!content || content.trim().length === 0) return 0;

  const hasMarker =
    content.includes("最值得投入") || content.includes("💡");
  if (!hasMarker) return 0;

  let idx = content.indexOf("最值得投入");
  if (idx === -1) idx = content.indexOf("💡");
  const nearby = content.slice(idx, idx + 300);
  const hasReason = TOP_REC_REASON_PATTERNS.some((p) => p.test(nearby));
  return hasReason ? 1.0 : 0.5;
}

// ── Aggregate ─────────────────────────────────────────────────────────

/**
 * Run all 10 L2 metrics on a report and return the result.
 */
export function evaluateReportL2(content: string): ReportEvalL2Result {
  return {
    cross_metric_reasoning: crossMetricReasoning(content),
    action_specificity: actionSpecificity(content),
    data_evidence_ratio: dataEvidenceRatio(content),
    citation_integration: citationIntegration(content),
    quadrant_judgment: quadrantJudgment(content),
    section_depth_variance: sectionDepthVariance(content),
    temporal_dual_frame: temporalDualFrame(content),
    priority_balance: priorityBalance(content),
    causal_chain: causalChain(content),
    top_recommendation: topRecommendation(content),
  };
}
