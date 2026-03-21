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

  return Math.min(crossMetricCount / 5, 1.0);
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
    .filter((line) => /^\s*-\s/.test(line))
    .map((line) => line.trim());

  if (actionLines.length === 0) return 0;

  let specificCount = 0;
  let vagueCount = 0;

  for (const line of actionLines) {
    const isSpecific = SPECIFIC_ACTION_PATTERNS.some((p) => p.test(line));
    const isVague = VAGUE_ACTION_PATTERNS.some((p) => p.test(line));

    if (isSpecific) {
      specificCount++;
    } else if (isVague) {
      vagueCount++;
    }
    // Lines matching neither are neutral — don't count toward either side
  }

  const scoredTotal = specificCount + vagueCount;
  if (scoredTotal === 0) return 0.5; // All neutral → middle score

  return specificCount / scoredTotal;
}

/**
 * Measure data evidence density.
 *
 * Counts percentage patterns (N%, +N%, -N.N%) and large numbers (≥100)
 * in the content. Returns count / 20 (capped at 1.0).
 */
export function dataEvidenceRatio(content: string): number {
  if (!content || content.trim().length === 0) return 0;

  // Count percentage patterns: 3.36%, +5.9%, -17.4%, 82.3%
  const percentMatches = content.match(/[+-]?\d+(?:\.\d+)?%/g) ?? [];

  // Count large numbers: 125,000 or 4200 (≥100), excluding those followed by %
  const numberMatches =
    content.match(/\b(?:\d{1,3}(?:,\d{3})+|\d{3,})\b(?!%)/g) ?? [];
  // Filter to numbers ≥ 100
  const largeNumbers = numberMatches.filter((n) => {
    const num = parseInt(n.replace(/,/g, ""), 10);
    return num >= 100;
  });

  const totalEvidence = percentMatches.length + largeNumbers.length;
  return Math.min(totalEvidence / 20, 1.0);
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

  return uniqueBodyCitations.size / uniqueAllCitations.size;
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

// ── Aggregate ─────────────────────────────────────────────────────────

/**
 * Run all 6 L2 metrics on a report and return the result.
 */
export function evaluateReportL2(content: string): ReportEvalL2Result {
  return {
    cross_metric_reasoning: crossMetricReasoning(content),
    action_specificity: actionSpecificity(content),
    data_evidence_ratio: dataEvidenceRatio(content),
    citation_integration: citationIntegration(content),
    quadrant_judgment: quadrantJudgment(content),
    section_depth_variance: sectionDepthVariance(content),
  };
}
