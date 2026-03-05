/**
 * Local report generator — pure template-based, no LLM API required.
 * Activated when OPENAI_API_KEY is absent.
 * Uses keyword search against the QA knowledge base + metric analysis.
 */

import { writeFileSync, mkdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import { paths } from "../config.js";
import { qaStore } from "../store/qa-store.js";
import type { QAItem } from "../store/qa-store.js";

// ── Constants (mirrors Python utils/metrics_parser.py) ──────────────

const CORE_METRICS = new Set([
  "曝光", "點擊", "CTR", "有效 (Coverage)", "檢索未索引",
  "工作階段總數（七天）", "Organic Search (工作階段)",
  "Discover", "AMP (non-Rich)", "AMP Article",
  "Google News", "News(new)", "Image",
]);

const ALERT_THRESHOLD_MONTHLY = 0.15;
const ALERT_THRESHOLD_WEEKLY = 0.20;

// ── Metric types ───────────────────────────────────────────────────

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

// ── Helpers ─────────────────────────────────────────────────────────

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
    if (Math.abs(monthly) >= ALERT_THRESHOLD_MONTHLY || Math.abs(weekly) >= ALERT_THRESHOLD_WEEKLY) {
      const flag = monthly >= 0 ? "ALERT_UP" : "ALERT_DOWN";
      alerts.push({ ...m, name, flag });
    }
  }
  return alerts;
}

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

// ── Template builder ─────────────────────────────────────────────────

function buildCoreSignals(
  core: readonly AlertMetric[],
  down: readonly AlertMetric[],
  up: readonly AlertMetric[],
  qaMap: Map<string, readonly QAItem[]>,
): string {
  const lines: string[] = ["## 本週核心訊號\n"];

  // Significant changes first (most actionable)
  for (const m of [...down.slice(0, 2), ...up.slice(0, 2)]) {
    const dir = m.flag === "ALERT_DOWN" ? "下滑" : "上升";
    const relatedQas = qaMap.get(m.name) ?? [];
    const qaRef = relatedQas.length > 0
      ? `（參考：「${relatedQas[0]!.question.slice(0, 40)}」）`
      : "（推論）";
    lines.push(`- **${m.name}** 出現顯著${dir}（月趨勢 ${fmtPct(m.monthly)}）：此指標變化可能影響整體 SEO 表現，需優先關注。${qaRef}`);
  }

  // Core metrics summary
  if (core.length > 0) {
    const ctrMetric = core.find((m) => m.name === "CTR");
    const impressionMetric = core.find((m) => m.name === "曝光");
    const clickMetric = core.find((m) => m.name === "點擊");

    if (impressionMetric || clickMetric || ctrMetric) {
      const parts = [
        impressionMetric ? `曝光 ${fmtNum(impressionMetric.latest)}（${fmtPct(impressionMetric.monthly)} MoM）` : null,
        clickMetric ? `點擊 ${fmtNum(clickMetric.latest)}（${fmtPct(clickMetric.monthly)} MoM）` : null,
        ctrMetric ? `CTR ${fmtNum(ctrMetric.latest)}（${fmtPct(ctrMetric.monthly)} MoM）` : null,
      ].filter(Boolean);
      if (parts.length > 0) {
        lines.push(`- **整體流量表現**：${parts.join("、")}。`);
      }
    }
  }

  // Pad to at least 2 signals
  if (lines.length <= 1) {
    lines.push("- 本週指標整體穩定，無重大異常。建議持續監控核心指標趨勢。");
  }

  return lines.join("\n");
}

function buildAnomaliesSection(
  down: readonly AlertMetric[],
  up: readonly AlertMetric[],
  qaMap: Map<string, readonly QAItem[]>,
): string {
  const lines: string[] = ["## 異常指標解讀\n"];

  if (down.length === 0 && up.length === 0) {
    lines.push("本週無顯著異常指標（月趨勢閾值 ±15%，週趨勢閾值 ±20%）。");
    return lines.join("\n");
  }

  for (const m of down) {
    const relatedQas = qaMap.get(m.name) ?? [];
    lines.push(`### ${m.name}（${fmtPct(m.monthly)} 月趨勢 / ${fmtPct(m.weekly)} 週趨勢）`);
    lines.push(`**可能原因**：此指標持續下滑，常見因素包含頁面品質下降、競爭者強化或 Google 演算法調整。`);
    if (relatedQas.length > 0) {
      const qa = relatedQas[0]!;
      const snippet = qa.answer.slice(0, 200) + (qa.answer.length > 200 ? "…" : "");
      lines.push(`**知識庫佐證**：${snippet}`);
      const source = [qa.source_title, qa.source_date].filter(Boolean).join("、");
      if (source) lines.push(`*來源：${source}*`);
    } else {
      lines.push(`**知識庫佐證**：（無直接對應，以下為 SEO 原理推論）建議檢查近期內容品質與技術健康度。`);
    }
    lines.push("");
  }

  for (const m of up) {
    const relatedQas = qaMap.get(m.name) ?? [];
    lines.push(`### ${m.name}（${fmtPct(m.monthly)} 月趨勢 / ${fmtPct(m.weekly)} 週趨勢）`);
    lines.push(`**可能原因**：此指標顯著上升，可能來自內容優化奏效、新頁面索引增加或季節性需求提升。`);
    if (relatedQas.length > 0) {
      const qa = relatedQas[0]!;
      const snippet = qa.answer.slice(0, 200) + (qa.answer.length > 200 ? "…" : "");
      lines.push(`**知識庫佐證**：${snippet}`);
    }
    lines.push("");
  }

  return lines.join("\n");
}

function buildActionList(
  down: readonly AlertMetric[],
  up: readonly AlertMetric[],
  topQas: readonly QAItem[],
): string {
  const lines: string[] = ["## 本週行動清單\n"];
  let idx = 1;

  for (const m of down.slice(0, 2)) {
    const relatedQa = topQas.find((q) =>
      q.question.includes(m.name) || q.answer.includes(m.name)
    );
    const basis = relatedQa
      ? `（依據：「${relatedQa.question.slice(0, 35)}」）`
      : "（依據：SEO 原理）";
    lines.push(`${idx}. **${m.name} 下滑因應**：審查近期相關頁面內容品質，確認 Meta 與 Schema 標記無誤，並比較上期差異。${basis}`);
    idx++;
  }

  for (const m of up.slice(0, 1)) {
    lines.push(`${idx}. **${m.name} 上升延伸**：分析流量來源，找出表現較佳的頁面類型，複製成功策略至其他同類頁面。（依據：SEO 最佳實踐）`);
    idx++;
  }

  if (idx <= 2) {
    lines.push(`${idx}. **定期健康檢查**：使用 Google Search Console 確認 Coverage 錯誤無增加，Sitemap 是否最新。（依據：技術 SEO 基礎）`);
    idx++;
  }

  // Ensure at least 3 items
  if (idx <= 3) {
    lines.push(`${idx}. **CTR 優化**：針對曝光高但點擊率低的關鍵字，優化 Title 與 Description 的吸引力與相關性。（依據：CTR 改善策略）`);
  }

  return lines.join("\n");
}

function buildKbSection(topQas: readonly QAItem[]): string {
  const lines: string[] = ["## 直接引用知識庫\n"];

  if (topQas.length === 0) {
    lines.push("（本週指標未找到直接對應的 Q&A）");
    return lines.join("\n");
  }

  for (const qa of topQas.slice(0, 2)) {
    const snippet = qa.answer.slice(0, 400) + (qa.answer.length > 400 ? "…" : "");
    const source = [qa.source_title, qa.source_date].filter(Boolean).join("、");
    lines.push(`**Q**：${qa.question}`);
    lines.push(`**A（節錄）**：${snippet}`);
    if (source) lines.push(`**來源**：${source}`);
    lines.push("");
  }

  return lines.join("\n");
}

// ── Public API ───────────────────────────────────────────────────────

/**
 * Generate SEO report using template + keyword search.
 * No LLM API required.
 */
export async function generateReportLocal(
  metrics: Record<string, unknown>,
  reportDate: string,
  qaCount: number,
): Promise<string> {
  const typedMetrics = metrics as Record<string, MetricData>;
  const alerts = detectAlerts(typedMetrics);
  const core = alerts.filter((a) => a.flag === "CORE");
  const down = alerts.filter((a) => a.flag === "ALERT_DOWN").sort((a, b) => (a.monthly ?? 0) - (b.monthly ?? 0));
  const up = alerts.filter((a) => a.flag === "ALERT_UP").sort((a, b) => (b.monthly ?? 0) - (a.monthly ?? 0));

  // Keyword search for relevant Q&As
  const queries = buildSearchQueries(typedMetrics);
  const seen = new Map<string, QAItem>();
  for (const q of queries) {
    const results = qaStore.keywordSearch(q, 3);
    for (const { item } of results) {
      if (!seen.has(item.id)) seen.set(item.id, item);
      if (seen.size >= 15) break;
    }
    if (seen.size >= 15) break;
  }
  const topQas = [...seen.values()].slice(0, 6);

  // Build per-metric Q&A map for inline references
  const qaMap = new Map<string, QAItem[]>();
  for (const m of alerts) {
    const results = qaStore.keywordSearch(m.name, 2);
    if (results.length > 0) {
      qaMap.set(m.name, results.map((r) => r.item));
    }
  }

  const coreSection = buildCoreSignals(core, down, up, qaMap);
  const anomalySection = buildAnomaliesSection(down, up, qaMap);
  const actionSection = buildActionList(down, up, topQas);
  const kbSection = buildKbSection(topQas);

  const kbLabel = qaCount > 0 ? `${qaCount} Q&A` : "知識庫";
  const metaBlock = `---
**Meta 資訊**
- **生成方式**：Template 模式（不需要 LLM API）
- **知識庫支撐**：${kbLabel}（來自過去 SEO 顧問會議記錄）
- **生成日期**：${reportDate}
- **特性**：純本地生成、知識庫關鍵字檢索、無 API 費用

---
`;

  return [metaBlock, coreSection, "", anomalySection, "", actionSection, "", kbSection].join("\n");
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
