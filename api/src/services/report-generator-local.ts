/**
 * Local report generator — ECC multi-perspective analysis, no LLM API required.
 * Activated when OPENAI_API_KEY is absent OR snapshot_id is provided.
 *
 * Structure: 6-section report driven by dedicated section builders,
 * each following Anthropic-style 4-layer narrative:
 *   Observation → Mechanism → Implication → Action
 */

import { writeFileSync, mkdirSync, existsSync, statSync } from "node:fs";
import { join } from "node:path";
import { paths } from "../config.js";
import { qaStore } from "../store/qa-store.js";
import type { QAItem } from "../store/qa-store.js";
import { buildReportMaturityBlock } from "../utils/maturity.js";

// ── Industry Research Citations ────────────────────────────────────────
// Pre-loaded constants referencing peer-reviewed / industry studies.
// Each section builder draws from this library for evidence-based claims.

const RESEARCH_CITATIONS = {
  ctr_baseline:
    "Backlinko 2024（樣本 67K 關鍵字、2400 萬次曝光）：Position 1 平均 CTR 27.6%，Position 2 降至 15.8%",
  ctr_serp_features:
    "arxiv 2306.01785（SERP Features & CTR）：Knowledge Panel 使目標頁 CTR 降低 ~8pp；Featured Snippet 可提升 CTR ~20%",
  navboost:
    "Google 排名因素洩露（2024）：NavBoost 以 13 個月滾動視窗聚合用戶點擊，為核心排名信號之一",
  causal_attribution:
    "SEOCausal / CausalImpact（Bayesian Structural Time Series）：SEO 無法 A/B 測試，貝氏時間序列是因果歸因的業界標準",
  eeeat_2024:
    "Google E-E-A-T 2024 更新：體驗（Experience）= 作者署名 + About 頁 + 可查核的外部聲譽",
  discover_signal:
    "First Page Sage 2025：持續發佈高品質內容為 Discover 首要因素；搜尋者參與度（點擊）為第 5 大信號",
  intent_framework:
    "Semrush 2025 SEO Report Framework：將意圖分為 Awareness / Consideration / Conversion 漏斗，各自對應不同 CTR 基準",
} as const;

// ── Constants ─────────────────────────────────────────────────────────

const CORE_METRICS = new Set([
  "曝光", "點擊", "CTR", "有效 (Coverage)", "檢索未索引",
  "工作階段總數（七天）", "Organic Search (工作階段)",
  "Discover", "AMP (non-Rich)", "AMP Article",
  "Google News", "News(new)", "Image",
]);

const ALERT_THRESHOLD_MONTHLY = 0.15;
const ALERT_THRESHOLD_WEEKLY = 0.20;

const SECTION_HEADINGS = [
  "## 一、", "## 二、", "## 三、",
  "## 四、", "## 五、", "## 六、", "## 七、",
] as const;

// ── Types ──────────────────────────────────────────────────────────────

interface MetricData {
  readonly latest?: number | null;
  readonly monthly?: number | null;
  readonly weekly?: number | null;
  readonly latest_date?: string;
  readonly previous_date?: string;
  readonly max?: number | null;
  readonly min?: number | null;
}

interface AlertMetric extends MetricData {
  readonly name: string;
  readonly flag: "CORE" | "ALERT_UP" | "ALERT_DOWN";
}

// ── Formatting helpers ────────────────────────────────────────────────

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "N/A";
  const sign = v >= 0 ? "+" : "";
  return `${sign}${(v * 100).toFixed(1)}%`;
}

function fmtNum(v: number | null | undefined): string {
  if (v == null) return "N/A";
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return v.toLocaleString("en-US", { maximumFractionDigits: 0 });
  if (Math.abs(v) <= 5) return v.toFixed(4);
  return v.toFixed(1);
}

function detectAlerts(metrics: Record<string, MetricData>): AlertMetric[] {
  const alerts: AlertMetric[] = [];
  for (const [name, m] of Object.entries(metrics)) {
    const monthly = m.monthly ?? 0;
    const weekly = m.weekly ?? 0;
    if (CORE_METRICS.has(name)) {
      alerts.push({ ...m, name, flag: "CORE" });
      continue;
    }
    if (
      Math.abs(monthly) >= ALERT_THRESHOLD_MONTHLY ||
      Math.abs(weekly) >= ALERT_THRESHOLD_WEEKLY
    ) {
      const flag = monthly >= 0 ? "ALERT_UP" : "ALERT_DOWN";
      alerts.push({ ...m, name, flag });
    }
  }
  return alerts;
}

/**
 * Return metric names that qualify as alerts (CORE + significant change).
 * Used by the online evaluator to compute alert_coverage correctly.
 */
export function getAlertMetricNames(metrics: Record<string, unknown>): string[] {
  const typed = metrics as Record<string, MetricData>;
  return detectAlerts(typed).map((a) => a.name);
}

// ── KB Link helper ────────────────────────────────────────────────────

function kbLink(qa: QAItem): string {
  return qa.source_url
    ? `[查看原文 →](${qa.source_url})`
    : `[知識庫 →](/admin/seoInsight/${qa.id})`;
}

// ── Citation tracker ──────────────────────────────────────────────────

interface CitationItem {
  readonly n: number;
  readonly id: string;
  readonly title: string;
  readonly category: string;
  readonly date: string;
  readonly snippet: string;
  readonly chunk_url: string;
  readonly source_url: string | null;
}

class CitationTracker {
  private readonly map = new Map<string, CitationItem>();
  private counter = 0;

  /** Register QA, return citation number */
  cite(qa: QAItem): number {
    if (!this.map.has(qa.id)) {
      this.counter += 1;
      this.map.set(qa.id, {
        n: this.counter,
        id: qa.id,
        title: [qa.source_title, qa.source_date].filter(Boolean).join("、"),
        category: qa.category ?? "",
        date: qa.source_date ?? "",
        snippet: qa.answer
          .replace(/\[(What|Why|How|Evidence)\]\s*/g, " ")
          .trim()
          .slice(0, 120),
        chunk_url: `/admin/seoInsight/${qa.id}`,
        source_url: qa.source_url ?? null,
      });
    }
    return this.map.get(qa.id)!.n;
  }

  /** `<!-- citations [...] -->` block appended at end of report */
  toBlock(): string {
    if (this.map.size === 0) return "";
    const items = [...this.map.values()].sort((a, b) => a.n - b.n);
    return `\n<!-- citations ${JSON.stringify(items)} -->`;
  }
}

// ── KB Citation formatter ─────────────────────────────────────────────

/**
 * Parse [What]/[Why]/[How]/[Evidence] structured QA answer into a readable blockquote.
 *
 * Structured output (when tags present):
 *   > **現象** …
 *   > **原因** …
 *   > **行動** …
 *   > **依據** …
 *   >
 *   > — SEO 1018、2023-10-18 ｜ [知識庫 →](link)  [N]
 *
 * Fallback (no tags): plain snippet in blockquote with attribution.
 *
 * Label map (based on RAGAS / NVIDIA 4-layer narrative):
 *   [What] → 現象 (observation)
 *   [Why]  → 原因 (mechanism)
 *   [How]  → 行動 (action)
 *   [Evidence] → 依據 (evidence)
 */
const TAG_LABEL_MAP: Record<string, string> = {
  What: "現象",
  Why: "原因",
  How: "行動",
  Evidence: "依據",
};

function formatKbCitation(qa: QAItem, tracker: CitationTracker, snippetLimit = 350): string {
  const segments = qa.answer.split(/\[(What|Why|How|Evidence)\]\s*/);
  const source = [qa.source_title, qa.source_date].filter(Boolean).join("、");
  const n = tracker.cite(qa);
  const chunkLink = `[知識庫${n} →](/admin/seoInsight/${qa.id})`;
  const attribution = [source ? `— ${source}` : "", chunkLink]
    .filter(Boolean)
    .join("  ");

  // Structured path: segments alternates ["prefix?", "Tag", "text", "Tag", "text", ...]
  if (segments.length > 1) {
    const parts: string[] = [];
    for (let i = 1; i < segments.length; i += 2) {
      const tag = segments[i]!;
      const text = (segments[i + 1] ?? "").trim();
      if (!text) continue;
      const label = TAG_LABEL_MAP[tag] ?? tag;
      const truncated = text.slice(0, snippetLimit) + (text.length > snippetLimit ? "…" : "");
      parts.push(`**${label}** ${truncated}`);
    }
    if (parts.length > 0) {
      return [...parts.map(p => `> ${p}`), "", attribution].join("\n");
    }
  }

  // Fallback: plain blockquote with attribution below
  const snippet =
    qa.answer.slice(0, snippetLimit) + (qa.answer.length > snippetLimit ? "…" : "");
  return [`> ${snippet}`, "", attribution].join("\n");
}

// ── Health score ──────────────────────────────────────────────────────

interface HealthDeduction {
  readonly metric: string;
  readonly reason: string;
  readonly points: number;
}

interface HealthScore {
  readonly score: number;
  readonly label: string;
  readonly deductions: readonly HealthDeduction[];
}

function calcHealthScore(
  down: readonly AlertMetric[],
  core: readonly AlertMetric[],
): HealthScore {
  const deductions: HealthDeduction[] = [];

  // CORE metrics that breach alert thresholds (prioritized)
  const coreAlertDown = core
    .filter(
      (m) =>
        (m.monthly ?? 0) < -ALERT_THRESHOLD_MONTHLY ||
        (m.weekly ?? 0) < -ALERT_THRESHOLD_WEEKLY,
    )
    .sort((a, b) => (a.monthly ?? 0) - (b.monthly ?? 0));

  for (const m of coreAlertDown) {
    deductions.push({
      metric: m.name,
      reason: `MoM ${fmtPct(m.monthly)}`,
      points: 10,
    });
  }

  // Non-CORE ALERT_DOWN (fill remaining slots up to 5 total)
  const remaining = 5 - deductions.length;
  for (const m of down.slice(0, Math.max(0, remaining))) {
    deductions.push({
      metric: m.name,
      reason: `MoM ${fmtPct(m.monthly)}`,
      points: 10,
    });
  }

  // Extra penalty when all core metrics are declining
  const coreDown = core.filter((m) => (m.monthly ?? 0) < 0);
  if (coreDown.length > 0 && coreDown.length === core.length && core.length > 0) {
    deductions.push({
      metric: "全 CORE 同時下滑",
      reason: `${coreDown.length} 個核心指標月趨勢皆為負`,
      points: 20,
    });
  }

  const totalDeduction = deductions.reduce((sum, d) => sum + d.points, 0);
  const score = Math.max(0, 100 - totalDeduction);

  const label = score >= 80 ? "良好" : score >= 60 ? "需關注" : "警示";
  return { score, label, deductions };
}

// ── Section builders ──────────────────────────────────────────────────

/** 一、本週 SEO 情勢快照 */
function buildSituationSnapshot(
  alerts: readonly AlertMetric[],
  core: readonly AlertMetric[],
  down: readonly AlertMetric[],
  qaMap: Map<string, readonly QAItem[]>,
  tracker: CitationTracker,
  llmAnalysis?: string | null,
): string {
  const { score, label, deductions } = calcHealthScore(down, core);
  const lines: string[] = [
    `${SECTION_HEADINGS[0]}本週 SEO 情勢快照\n`,
    `**SEO 健康評分：${score}/100（${label}）**\n`,
  ];

  if (deductions.length > 0) {
    lines.push("| 扣分原因 | 趨勢 | 扣分 |");
    lines.push("| --- | --- | ---: |");
    for (const d of deductions) {
      lines.push(`| ${d.metric} | ${d.reason} | -${d.points} |`);
    }
    lines.push("");
  }

  if (llmAnalysis) {
    lines.push("### 跨指標關聯分析（AI 輔助）\n", llmAnalysis, "");
  }

  // Top phenomena summary
  const phenomena = [
    ...down.slice(0, 3).map((m) => ({
      urgency: "🔴 高",
      observation: `**${m.name}** 月趨勢 ${fmtPct(m.monthly)}，週趨勢 ${fmtPct(m.weekly)}。`,
      implication: `指標持續下滑代表搜尋可見度或使用者互動品質惡化，需優先介入。`,
    })),
    ...alerts
      .filter((a) => a.flag === "ALERT_UP")
      .slice(0, 2)
      .map((m) => ({
        urgency: "🟢 低",
        observation: `**${m.name}** 月趨勢 ${fmtPct(m.monthly)}，週趨勢 ${fmtPct(m.weekly)}。`,
        implication: `正向成長，建議深入分析驅動因素以複製策略。`,
      })),
  ].slice(0, 5);

  if (phenomena.length === 0) {
    lines.push("本週無重大異常（月趨勢閾值 ±15%，週趨勢閾值 ±20%）。核心指標整體穩定。\n");
  } else {
    lines.push(`**本週 ${phenomena.length} 大現象：**\n`);
    phenomena.forEach((p, i) => {
      lines.push(
        `${i + 1}. ${p.urgency} | ${p.observation}`,
        `   意義：${p.implication}`,
        "",
      );
    });
  }

  // ── Per-indicator deep-dive with KB citations ─────────────────────
  if (down.length > 0) {
    lines.push("### 異常指標逐項解讀\n");
    for (const m of down) {
      lines.push(
        `#### ${m.name}（${fmtPct(m.monthly)} 月趨勢 / ${fmtPct(m.weekly)} 週趨勢）\n`,
        `【可能原因】此指標持續下滑，常見因素包含頁面品質下降、競爭者強化或 Google 演算法調整。`,
      );
      const related = qaMap.get(m.name) ?? [];
      if (related.length > 0) {
        lines.push("**知識庫佐證**\n");
        lines.push(formatKbCitation(related[0]!, tracker, 350), "");
        if (related.length > 1) {
          lines.push("**延伸參考**\n");
          lines.push(formatKbCitation(related[1]!, tracker, 200), "");
        }
      } else {
        lines.push(
          `【行動建議】立即在 GSC 確認 ${m.name} 相關頁面近期變化，比對演算法更新時間軸。`,
          "",
        );
      }
    }
  }

  return lines.join("\n");
}

/** 二、流量信號解讀 */
function buildTrafficSignals(
  core: readonly AlertMetric[],
  down: readonly AlertMetric[],
  qaMap: Map<string, readonly QAItem[]>,
  llmAnalysis?: string | null,
): string {
  const lines: string[] = [`${SECTION_HEADINGS[1]}流量信號解讀\n`];

  const ctr = core.find((m) => m.name === "CTR");
  const imp = core.find((m) => m.name === "曝光");
  const click = core.find((m) => m.name === "點擊");
  const discover = core.find((m) => m.name === "Discover");
  const organic = core.find((m) => m.name === "Organic Search (工作階段)");

  // CTR 三象限分析
  lines.push("### CTR 三象限分析\n");
  if (ctr || imp || click) {
    const ctrVal = ctr?.latest;
    const impMonthly = imp?.monthly ?? 0;
    const clickMonthly = click?.monthly ?? 0;
    const ctrMonthly = ctr?.monthly ?? 0;

    // Classify quadrant
    if (impMonthly >= 0 && ctrMonthly < -0.05) {
      lines.push(
        `**象限：高曝光 / 低 CTR 警示**`,
        `【觀察】曝光 ${fmtPct(impMonthly)} MoM，CTR ${fmtPct(ctrMonthly)} MoM，點擊絕對值 ${fmtNum(click?.latest)}。`,
        `【機制】曝光穩定但 CTR 下滑，代表排名位置未變，但 Title/Description 吸引力不足，或 SERP Feature（Knowledge Panel）搶走點擊。${RESEARCH_CITATIONS.ctr_serp_features}`,
        `【意涵】使用者看到頁面但不點擊，意圖對映可能錯位，或標題競爭力下降。`,
        `【行動】針對曝光 Top 20 但 CTR < ${ctrVal ? (ctrVal * 100).toFixed(1) : "5"}% 的頁面，A/B 測試 Title 加入數字、年份後綴或情緒觸發詞。`,
        "",
      );
    } else if (impMonthly < -0.1 && ctrMonthly >= 0) {
      lines.push(
        `**象限：低曝光 / 高 CTR 模式**`,
        `【觀察】曝光 ${fmtPct(impMonthly)} MoM，但 CTR ${fmtPct(ctrMonthly)} MoM。`,
        `【機制】曝光下滑代表排名後退或索引量縮減；CTR 相對提升可能來自 SERP 位置移至競爭較少的利基詞。`,
        `【意涵】整體觸及範圍縮小，即使 CTR 好看，絕對流量仍受壓縮。`,
        `【行動】優先檢查 Coverage 有效率趨勢，確認是否有頁面被 noindex 或遭爬蟲降頻。`,
        "",
      );
    } else if (impMonthly < -0.05 && clickMonthly < -0.05) {
      lines.push(
        `**象限：雙低警示（曝光 + CTR 同步下滑）**`,
        `【觀察】曝光 ${fmtPct(impMonthly)} MoM，點擊 ${fmtPct(clickMonthly)} MoM，雙重下行壓力。`,
        `【機制】${RESEARCH_CITATIONS.navboost}`,
        `【意涵】NavBoost 聚合的用戶點擊信號持續惡化，可能引發排名進一步下降的負向循環。`,
        `【行動】立即審查近 3 個月 CTR < 1% 的低效頁面，考慮合併或重新定向。`,
        "",
      );
    } else {
      lines.push(
        `**整體流量：**曝光 ${fmtPct(impMonthly)} MoM | 點擊 ${fmtPct(clickMonthly)} MoM | CTR ${fmtPct(ctrMonthly)} MoM。`,
        `${RESEARCH_CITATIONS.ctr_baseline}`,
        "",
      );
    }
  } else {
    lines.push("（本期無 CTR / 曝光 / 點擊核心指標數據）\n");
  }

  if (llmAnalysis) {
    lines.push("### 流量信號 AI 解讀\n", llmAnalysis, "");
  }

  // 各流量來源趨勢
  lines.push("### 各流量來源趨勢\n");
  const sources = [discover, organic].filter(Boolean) as AlertMetric[];
  const discoverDown = down.find((m) => m.name === "Discover");

  if (discoverDown) {
    const relatedQas = qaMap.get("Discover") ?? [];
    lines.push(
      `**Discover**：${fmtPct(discoverDown.monthly)} MoM。`,
      `【機制】${RESEARCH_CITATIONS.discover_signal}`,
    );
    if (relatedQas.length > 0) {
      const qa = relatedQas[0]!;
      lines.push(`【知識庫】${qa.answer.slice(0, 150)}… ${kbLink(qa)}`);
    }
    lines.push("");
  } else if (sources.length > 0) {
    for (const m of sources) {
      const trend = (m.monthly ?? 0) >= 0 ? "▲" : "▼";
      lines.push(`- **${m.name}**：${trend} ${fmtPct(m.monthly)} MoM`);
    }
    lines.push("");
  } else {
    lines.push("（本期無細分流量來源數據）\n");
  }

  return lines.join("\n");
}

/** 三、技術 SEO 健康度 */
function buildTechnicalHealth(
  metrics: Record<string, MetricData>,
  down: readonly AlertMetric[],
  qaMap: Map<string, readonly QAItem[]>,
  llmAnalysis?: string | null,
): string {
  const lines: string[] = [`${SECTION_HEADINGS[2]}技術 SEO 健康度\n`];

  if (llmAnalysis) {
    lines.push("### 技術面 AI 判讀\n", llmAnalysis, "");
  }

  const coverage = (metrics["有效 (Coverage)"] ?? {}) as MetricData;
  const unindexed = (metrics["檢索未索引"] ?? {}) as MetricData;

  // Coverage 索引健康
  lines.push("### Coverage 索引健康\n");
  if (coverage.latest != null || coverage.monthly != null) {
    const trend = (coverage.monthly ?? 0) >= 0 ? "正向" : "下滑";
    lines.push(
      `【觀察】有效索引率 ${fmtNum(coverage.latest)}，月趨勢 ${fmtPct(coverage.monthly)}（${trend}）。`,
    );
    if ((coverage.monthly ?? 0) < -0.1) {
      lines.push(
        `【機制】索引覆蓋率下滑通常來自：(1) 新增 noindex 標記、(2) 爬蟲頻率降低、(3) 重複內容被系統降權。`,
        `【行動】登入 GSC → 索引 → 頁面，檢查「未索引原因」分佈變化，重點排查「已編目，目前未索引」項目。`,
      );
    } else {
      lines.push(`索引健康狀況穩定，建議每週定期確認 Coverage 趨勢。`);
    }
  } else {
    lines.push("（本期無 Coverage 數據）");
  }
  lines.push("");

  // 爬取信號
  lines.push("### 爬取信號 × 知識庫交叉比對\n");
  const technicalDown = down.filter((m) =>
    ["檢索未索引", "AMP (non-Rich)", "AMP Article"].includes(m.name),
  );

  if (technicalDown.length > 0) {
    for (const m of technicalDown) {
      const relatedQas = qaMap.get(m.name) ?? [];
      lines.push(`**${m.name}**：${fmtPct(m.monthly)} MoM | 週趨勢 ${fmtPct(m.weekly)}`);
      if (relatedQas.length > 0) {
        const qa = relatedQas[0]!;
        lines.push(`> ${qa.answer.slice(0, 200)}… ${kbLink(qa)}`);
      }
      lines.push("");
    }
  } else if (unindexed.monthly != null && (unindexed.monthly ?? 0) > 0.1) {
    lines.push(
      `**「檢索未索引」上升 ${fmtPct(unindexed.monthly)}**：此為技術 SEO 警訊，代表 Google 爬蟲已抓取但未收錄的頁面增加。`,
      `【行動】優先檢查 robots.txt、Canonical 設定，以及是否有大量薄內容頁面被系統判定為低品質。`,
      "",
    );
  } else {
    lines.push("本週無顯著技術 SEO 告警。建議持續監控 AMP 索引與爬取頻率。\n");
  }

  return lines.join("\n");
}

/** 四、搜尋意圖對映 */
function buildIntentMapping(
  core: readonly AlertMetric[],
  down: readonly AlertMetric[],
  qaMap: Map<string, readonly QAItem[]>,
  llmAnalysis?: string | null,
): string {
  const lines: string[] = [`${SECTION_HEADINGS[3]}搜尋意圖對映\n`];

  if (llmAnalysis) {
    lines.push("### 意圖位移 AI 判讀\n", llmAnalysis, "");
  }

  lines.push(
    `> ${RESEARCH_CITATIONS.intent_framework}\n`,
  );

  // Map metrics to intent funnel
  lines.push("### 指標 × 意圖漏斗對映\n");

  const organic = core.find((m) => m.name.includes("工作階段") || m.name.includes("Organic"));
  const discover = core.find((m) => m.name === "Discover");
  const ctr = core.find((m) => m.name === "CTR");
  const impression = core.find((m) => m.name === "曝光");

  lines.push("| 意圖階段 | 對應指標 | 本期狀況 | 解讀 |");
  lines.push("|---------|---------|---------|------|");
  lines.push(
    `| Awareness | 曝光 | ${fmtPct(impression?.monthly)} MoM | ${(impression?.monthly ?? 0) >= 0 ? "觸及穩定，品牌可見度維持" : "觸及下滑，內容或排名受壓"} |`,
    `| Consideration | CTR | ${fmtPct(ctr?.monthly)} MoM | ${(ctr?.monthly ?? 0) >= 0 ? "點擊意願提升" : "Title/Desc 吸引力待優化"} |`,
    `| Conversion | 工作階段 | ${fmtPct(organic?.monthly)} MoM | ${(organic?.monthly ?? 0) >= 0 ? "流量轉換順暢" : "轉換漏損，需排查落地頁"} |`,
    `| Discovery | Discover | ${fmtPct(discover?.monthly)} MoM | ${(discover?.monthly ?? 0) >= 0 ? "演算法推播穩定" : "主動發現流量下滑"} |`,
    "",
  );

  // E-E-A-T signals
  lines.push("### E-E-A-T 信號觀察\n");
  lines.push(`${RESEARCH_CITATIONS.eeeat_2024}\n`);

  const contentDown = down.filter((m) =>
    m.name.includes("CTR") || m.name.includes("曝光") || m.name.includes("點擊")
  );

  if (contentDown.length > 0) {
    lines.push(
      "核心流量指標下滑時，E-E-A-T 信號尤為關鍵：",
      "- **體驗（Experience）**：確認作者署名頁與 About 頁資訊完整",
      "- **專業性（Expertise）**：文章引用可查核的外部數據來源",
      "- **權威性（Authoritativeness）**：監控外部反向連結質量",
      "- **可信賴度（Trustworthiness）**：確保隱私政策與聯絡資訊清晰",
      "",
    );
  } else {
    lines.push(
      "本週核心指標穩定，E-E-A-T 層面無急迫修正需求。",
      "建議：持續維護作者 Schema 標記與結構化資料，為長期排名建立競爭壁壘。",
      "",
    );
  }

  const relatedQas = qaMap.get("CTR") ?? qaMap.get("搜尋意圖") ?? [];
  if (relatedQas.length > 0) {
    const qa = relatedQas[0]!;
    lines.push(`**知識庫補充**：${qa.question}`, `> ${qa.answer.slice(0, 150)}… ${kbLink(qa)}`, "");
  }

  return lines.join("\n");
}

// Metric-specific action templates keyed by substring match
const ACTION_TEMPLATES: ReadonlyArray<{
  readonly match: string;
  readonly action: string;
}> = [
  { match: "AMP Article", action: "在 GSC → AMP 報告檢查驗證錯誤數量；排查 CSS `!important` 違規；確認 AMP 版頁面的 canonical 指向正確" },
  { match: "Google News", action: "在 Google News Publisher Center 確認出版品狀態正常；檢查近 7 天新聞類文章發佈頻率是否下降；評估是否依主題拆分出版品" },
  { match: "News(new)", action: "檢查近 7 天文章是否有跟上熱門時事話題；確認新聞類文章的 datePublished 結構化資料正確" },
  { match: "Organic Search", action: "在 GSC → 成效 → 查詢，篩選近 28 天點擊下降 > 20% 的查詢詞，找出流失最多的 Top 10 關鍵字" },
  { match: "工作階段", action: "在 GA4 → 流量獲取 → 工作階段預設管道分群，比對 Organic/Direct/Social 各管道增減，定位流量流失管道" },
  { match: "Discover", action: "檢查 GSC Discover 報告的每日展示次數趨勢；確認近期文章是否有大圖（1200px+）及吸引點擊的標題" },
  { match: "CTR", action: "在 GSC 篩選曝光 > 1,000 但 CTR < 1% 的查詢，針對 Top 10 改寫 Title/Description" },
  { match: "檢索未索引", action: "在 GSC → 索引 → 網頁，匯出「已檢索 — 目前未建立索引」的 URL 清單，按目錄分群找出問題集中區" },
  { match: "曝光", action: "在 GSC 按查詢篩選新增曝光來源，確認是否為品牌相關查詢或泛流量長尾字段" },
  { match: "點擊", action: "交叉比對 GSC 點擊與 GA4 工作階段，確認數據一致性；若差距擴大，檢查追蹤碼是否遺漏" },
  { match: "Image", action: "檢查圖片 alt 屬性與檔名是否包含目標關鍵字；確認圖片 sitemap 已提交" },
  { match: "有效", action: "在 GSC → 索引 → 網頁，監控「有效」頁面數量趨勢；若下降，檢查是否有頁面被意外加入 noindex" },
];

function getActionForMetric(name: string): string {
  const template = ACTION_TEMPLATES.find((t) => name.includes(t.match));
  return template?.action ?? `在 GSC 對應報告中檢查 ${name} 的細項數據，找出下滑集中的頁面或查詢`;
}

function extractHowFromQa(qa: QAItem): string | null {
  const howMatch = qa.answer.match(/\[How\]\s*([^[]+)/);
  if (howMatch?.[1]) {
    const text = howMatch[1].trim();
    return text.length > 200 ? `${text.slice(0, 200)}…` : text;
  }
  return null;
}

/** 五、本週優先行動清單 */
function buildPriorityActions(
  down: readonly AlertMetric[],
  up: readonly AlertMetric[],
  topQas: readonly QAItem[],
  llmAnalysis?: string | null,
  maturity?: Readonly<Record<string, string>> | null,
): string {
  const lines: string[] = [`${SECTION_HEADINGS[4]}本週優先行動清單\n`];

  const highPriority: string[] = [];
  const midPriority: string[] = [];
  const lowPriority: string[] = [];

  // High priority: down alerts with specific actions (max 3)
  for (const m of down.slice(0, 3)) {
    const action = getActionForMetric(m.name);
    const relatedQa = topQas.find(
      (q) => q.question.includes(m.name) || q.answer.includes(m.name),
    );
    const howTip = relatedQa ? extractHowFromQa(relatedQa) : null;
    const linkPart = relatedQa ? ` ${kbLink(relatedQa)}` : "";
    let item = `**${m.name} 下滑 ${fmtPct(m.monthly)}**：${action}。${linkPart}`;
    if (howTip) {
      item += `\n  > KB 建議：${howTip}`;
    }
    highPriority.push(item);
  }

  // Always include a core technical check if no high priority items
  if (highPriority.length === 0) {
    highPriority.push(
      "**定期技術健康確認**：在 GSC 確認 Coverage 錯誤未增加、Sitemap 已更新、Core Web Vitals 無退步。",
    );
  }

  // Mid priority: CTR optimization + up metrics follow-through
  midPriority.push(
    "**CTR 優化**：在 GSC 篩選曝光 Top 20 但 CTR < 5% 的頁面，A/B 測試 Title 加入數字、年份或括號重點。",
  );

  for (const m of up.slice(0, 1)) {
    midPriority.push(
      `**${m.name} 上升 ${fmtPct(m.monthly)}**：分析表現成長的頁面或查詢，找出驅動因素並複製策略至同類頁面。`,
    );
  }

  // Low priority: E-E-A-T + content calendar
  lowPriority.push(
    "**E-E-A-T 強化**：確認作者署名頁有完整經歷與外部可查核連結；補充 Person Schema 結構化資料。",
    "**內容行事曆**：根據本週上升的關鍵字主題，規劃 1-2 篇延伸長文，鎖定 Consideration 漏斗。",
  );

  const redItems = highPriority.map((s) => `- 🔴 ${s}`).join("\n");
  const yellowItems = midPriority.map((s) => `- 🟡 ${s}`).join("\n");
  const greenItems = lowPriority.map((s) => `- 🟢 ${s}`).join("\n");

  lines.push(
    "**高優先（需立即處理）**\n",
    redItems,
    "",
    "**中優先（本週內）**\n",
    yellowItems,
    "",
    "**低優先（下週規劃）**\n",
    greenItems,
    "",
  );

  if (maturity && Object.keys(maturity).length > 0) {
    lines.push("### 成熟度對標\n", buildReportMaturityBlock(maturity), "");
  }

  if (llmAnalysis) {
    lines.push("### 行動優先序 AI 判讀\n", llmAnalysis, "");
  }

  return lines.join("\n");
}

/** 六、AI 可見度分析 */
function buildAiVisibility(): string {
  const lines: string[] = [`${SECTION_HEADINGS[5]}AI 可見度分析\n`];

  lines.push(
    "**目前狀態**：AI visibility 資料尚未整合，以下為建議改善方向。\n",
    "- **結構化資料**：確保 JSON-LD Schema.org 標記完整（FAQPage、HowTo、Article 等）",
    "- **E-E-A-T 強化**：確認作者署名、About 頁面、外部可查核聲譽",
    "- **可引用性**：關鍵段落採用清晰的問答格式，方便 AI 引用",
    "- **AI Bot 設定**：透過 `robots.txt` 管理 GPTBot、ClaudeBot 等 AI 爬蟲存取權限",
    "",
    "> 建議使用 `make check-ai-crawlers URL=<your-site>` 檢查 AI 爬蟲設定。",
  );

  return lines.join("\n");
}

/** 七、來源 */
function buildKbCitations(topQas: readonly QAItem[], tracker: CitationTracker): string {
  const lines: string[] = [`${SECTION_HEADINGS[6]}來源\n`];

  if (topQas.length === 0) {
    lines.push("（本週指標未找到直接對應的 Q&A）");
    return lines.join("\n");
  }

  const cited = topQas.slice(0, 8);
  for (const qa of cited) {
    const n = tracker.cite(qa);
    const title = [qa.source_title, qa.source_date].filter(Boolean).join("、") || qa.question.slice(0, 40);
    const snippet = qa.answer.replace(/\[(What|Why|How|Evidence)\]\s*/g, " ").trim().slice(0, 80);
    lines.push(`[知識庫${n} →](/admin/seoInsight/${qa.id}) **${title}** — ${snippet}…`);
  }

  return lines.join("\n");
}

// ── KB version from mtime ─────────────────────────────────────────────

function getKbVersion(): string {
  try {
    const mtime = statSync(paths.qaJsonPath).mtime;
    const y = mtime.getFullYear();
    const m = String(mtime.getMonth() + 1).padStart(2, "0");
    const d = String(mtime.getDate()).padStart(2, "0");
    return `v${y}.${m}.${d}`;
  } catch {
    return "v(unknown)";
  }
}

// ── Search helpers ────────────────────────────────────────────────────

function buildSearchQueries(metrics: Record<string, MetricData>): string[] {
  const alerts = detectAlerts(metrics);
  const queries = new Set<string>();

  for (const m of alerts) {
    queries.add(m.name);
    if (m.flag === "ALERT_DOWN") queries.add(`${m.name} 下降`);
    if (m.flag === "ALERT_UP") queries.add(`${m.name} 上升`);
  }

  for (const q of ["CTR 下降 改善", "索引覆蓋 問題", "Discover 演算法", "爬蟲 抓取"]) {
    queries.add(q);
  }

  return [...queries].slice(0, 15);
}

// ── Public API ────────────────────────────────────────────────────────

/**
 * Generate a 6-section SEO report using template + keyword search.
 * No LLM API required.
 */
export interface LlmAnalyses {
  readonly situation?: string | null;
  readonly traffic?: string | null;
  readonly technical?: string | null;
  readonly crawledNotIndexed?: string | null;
  readonly intent?: string | null;
  readonly action?: string | null;
}

export async function generateReportLocal(
  metrics: Record<string, unknown>,
  reportDate: string,
  qaCount: number,
  llmAnalyses?: LlmAnalyses | null,
  weeks?: number | null,
  crawledNotIndexed?: import("./crawled-not-indexed-parser.js").CrawledNotIndexedResult | null,
  maturity?: Readonly<Record<string, string>> | null,
): Promise<string> {
  const typedMetrics = metrics as Record<string, MetricData>;
  const alerts = detectAlerts(typedMetrics);
  const core = alerts.filter((a) => a.flag === "CORE");
  const down = alerts
    .filter((a) => a.flag === "ALERT_DOWN")
    .sort((a, b) => (a.monthly ?? 0) - (b.monthly ?? 0));
  const up = alerts
    .filter((a) => a.flag === "ALERT_UP")
    .sort((a, b) => (b.monthly ?? 0) - (a.monthly ?? 0));

  // Ensure QA store is loaded (lazy init when called outside the full server startup)
  if (!qaStore.loaded) {
    try {
      qaStore.load();
    } catch {
      // Continue without KB citations — graceful degradation
    }
  }

  // Keyword search for relevant Q&As
  const queries = buildSearchQueries(typedMetrics);
  const seen = new Map<string, QAItem>();
  for (const q of queries) {
    const results = qaStore.keywordSearch(q, 5);
    for (const { item } of results) {
      if (!seen.has(item.id)) seen.set(item.id, item);
      if (seen.size >= 20) break;
    }
    if (seen.size >= 20) break;
  }
  const topQas = [...seen.values()].slice(0, 8);

  // Per-metric Q&A map for inline references (3 per metric for richer citations)
  const qaMap = new Map<string, readonly QAItem[]>();
  for (const m of alerts) {
    const results = qaStore.keywordSearch(m.name, 3);
    if (results.length > 0) {
      qaMap.set(m.name, results.map((r) => r.item));
    }
  }
  // Also search broader topic terms
  for (const term of ["CTR", "曝光", "索引", "AMP", "Discover", "工作階段"]) {
    if (!qaMap.has(term)) {
      const results = qaStore.keywordSearch(term, 2);
      if (results.length > 0) {
        qaMap.set(term, results.map((r) => r.item));
      }
    }
  }

  // Build sections (6 core + optional crawled-not-indexed = up to 7)
  const tracker = new CitationTracker();
  const analyses = llmAnalyses ?? {};
  const s1 = buildSituationSnapshot(alerts, core, down, qaMap, tracker, analyses.situation);
  const s2 = buildTrafficSignals(core, down, qaMap, analyses.traffic);
  const s3 = buildTechnicalHealth(typedMetrics, down, qaMap, analyses.technical);

  // Optional crawled-not-indexed section — inserted between 技術 SEO and 搜尋意圖
  let crawledNotIndexedSection = "";
  if (crawledNotIndexed && crawledNotIndexed.paths.length > 0) {
    const { analyzeCrawledNotIndexed } = await import("./crawled-not-indexed-analyzer.js");
    const insight = analyzeCrawledNotIndexed(crawledNotIndexed);
    crawledNotIndexedSection = insight.markdown;
    if (analyses.crawledNotIndexed) {
      crawledNotIndexedSection += `\n### 檢索未索引 AI 判讀\n\n${analyses.crawledNotIndexed}\n`;
    }
  }

  const s4 = buildIntentMapping(core, down, qaMap, analyses.intent);
  const s5 = buildPriorityActions(down, up, topQas, analyses.action, maturity);
  const s6 = buildAiVisibility();
  const s7 = buildKbCitations(topQas, tracker);

  const hasCrawledNotIndexed = crawledNotIndexedSection.length > 0;
  const dimensionCount = hasCrawledNotIndexed ? 8 : 7;
  const dimensionLabel = hasCrawledNotIndexed
    ? "8 維度（情勢 / 流量 / 技術 / 索引覆蓋 / 意圖 / 行動 / AI 可見度 / 知識庫）"
    : "7 維度（情勢 / 流量 / 技術 / 意圖 / 行動 / AI 可見度 / 知識庫）";

  // Meta block
  const kbVersion = getKbVersion();
  const kbLabel = qaCount > 0 ? `${qaCount} Q&A` : "知識庫";
  const llmUsed = Object.values(analyses).some((v) => !!v);
  const generationMode = llmUsed
    ? "Hybrid Mode（本地模板 + Claude Code 語意輔助）"
    : "Template Mode（本地模板引擎，不呼叫任何 LLM API）";
  const generatedAt = new Date().toISOString();
  const metaBlock = `---
**報告資訊**
- 生成方式：${generationMode}
- 知識庫版本：${kbVersion}（${kbLabel}，4 個來源集合）
- 分析框架：Semrush 2025 / GSC 官方指引 / First Page Sage 2025 排名因素
- 分析維度：${dimensionCount} 維度（${dimensionLabel}）
- 生成日期：${reportDate}
---
`;

  // Structured metadata block (machine-readable, appended after citations)
  const reportMeta = {
    weeks: weeks ?? 1,
    generated_at: generatedAt,
    generation_mode: llmUsed ? "hybrid" : "template",
    generation_label: generationMode,
    model: llmUsed ? "claude-code" : "none",
    has_crawled_not_indexed: hasCrawledNotIndexed,
  };
  const metaComment = `\n<!-- report_meta ${JSON.stringify(reportMeta)} -->`;

  const sections = [metaBlock, s1, s2, s3];
  if (crawledNotIndexedSection) sections.push(crawledNotIndexedSection);
  sections.push(s4, s5, s6, s7);

  return sections.join("\n") + tracker.toBlock() + metaComment;
}

/**
 * Save report to output/report_{YYYYMMDD}.md
 */
export function saveReport(content: string, reportDate: string): void {
  const dir = paths.outputDir;
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
  const filename = `report_${reportDate.replace(/\//g, "")}.md`;
  writeFileSync(join(dir, filename), content, "utf-8");
}
