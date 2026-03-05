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
  "## 四、", "## 五、", "## 六、",
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

// ── KB Link helper ────────────────────────────────────────────────────

function kbLink(qa: QAItem): string {
  return qa.source_url
    ? `[查看原文 →](${qa.source_url})`
    : `[知識庫 →](/admin/seoInsight/chunk/${qa.id})`;
}

// ── Health score ──────────────────────────────────────────────────────

interface HealthScore {
  readonly score: number;
  readonly label: string;
}

function calcHealthScore(
  down: readonly AlertMetric[],
  core: readonly AlertMetric[],
): HealthScore {
  let score = 100;
  score -= Math.min(down.length * 10, 50);

  // Extra penalty when all core metrics are declining
  const coreDown = core.filter((m) => (m.monthly ?? 0) < 0);
  if (coreDown.length > 0 && coreDown.length === core.length && core.length > 0) {
    score -= 20;
  }

  score = Math.max(0, score);

  const label = score >= 80 ? "良好" : score >= 60 ? "需關注" : "警示";
  return { score, label };
}

// ── Section builders ──────────────────────────────────────────────────

/** 一、本週 SEO 情勢快照 */
function buildSituationSnapshot(
  alerts: readonly AlertMetric[],
  core: readonly AlertMetric[],
  down: readonly AlertMetric[],
  qaMap: Map<string, readonly QAItem[]>,
): string {
  const { score, label } = calcHealthScore(down, core);
  const lines: string[] = [
    `${SECTION_HEADINGS[0]}本週 SEO 情勢快照\n`,
    `**SEO 健康評分：${score}/100（${label}）**\n`,
  ];

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
        const qa = related[0]!;
        const snippet = qa.answer.slice(0, 350) + (qa.answer.length > 350 ? "…" : "");
        const source = [qa.source_title, qa.source_date].filter(Boolean).join("、");
        lines.push(
          `【知識庫佐證】${snippet}`,
          source ? `來源：${source}` : "",
          `${kbLink(qa)}`,
          "",
        );
        // Second citation if available
        if (related.length > 1) {
          const qa2 = related[1]!;
          const snippet2 = qa2.answer.slice(0, 200) + (qa2.answer.length > 200 ? "…" : "");
          const source2 = [qa2.source_title, qa2.source_date].filter(Boolean).join("、");
          lines.push(
            `【延伸參考】${snippet2}`,
            source2 ? `來源：${source2}` : "",
            `${kbLink(qa2)}`,
            "",
          );
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
): string {
  const lines: string[] = [`${SECTION_HEADINGS[2]}技術 SEO 健康度\n`];

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
): string {
  const lines: string[] = [`${SECTION_HEADINGS[3]}搜尋意圖對映\n`];

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

/** 五、本週優先行動清單 */
function buildPriorityActions(
  down: readonly AlertMetric[],
  up: readonly AlertMetric[],
  topQas: readonly QAItem[],
): string {
  const lines: string[] = [`${SECTION_HEADINGS[4]}本週優先行動清單\n`];

  const highPriority: string[] = [];
  const midPriority: string[] = [];
  const lowPriority: string[] = [];

  // High priority: all down alerts (max 3)
  for (const m of down.slice(0, 3)) {
    const relatedQa = topQas.find(
      (q) => q.question.includes(m.name) || q.answer.includes(m.name),
    );
    const linkPart = relatedQa ? ` ${kbLink(relatedQa)}` : "";
    highPriority.push(
      `**${m.name} 下滑 ${fmtPct(m.monthly)}**：立即審查近期相關頁面內容品質，確認 Meta 標記與 Schema 正確。${linkPart}`,
    );
  }

  // Always include a core technical check if no high priority items
  if (highPriority.length === 0) {
    highPriority.push(
      "**定期技術健康確認**：使用 GSC 確認 Coverage 錯誤未增加、Sitemap 已更新、Core Web Vitals 無退步。",
    );
  }

  // Mid priority: CTR optimization + up metrics follow-through
  midPriority.push(
    "**CTR 優化**：針對曝光 Top 20 但 CTR < 5% 的頁面，A/B 測試 Title 加入數字或年份後綴。",
  );

  for (const m of up.slice(0, 1)) {
    midPriority.push(
      `**${m.name} 上升 ${fmtPct(m.monthly)} 延伸**：分析表現較佳頁面，複製成功策略至同類頁面。`,
    );
  }

  // Low priority: E-E-A-T + content calendar
  lowPriority.push(
    "**E-E-A-T 強化**：確認作者署名頁與 About 頁資訊完整，補充結構化資料（Person Schema）。",
    "**內容行事曆**：規劃下週發佈 1-2 篇高意圖關鍵字長文，目標 Consideration 漏斗。",
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

  return lines.join("\n");
}

/** 六、知識庫引用 */
function buildKbCitations(topQas: readonly QAItem[]): string {
  const lines: string[] = [`${SECTION_HEADINGS[5]}知識庫引用\n`];

  if (topQas.length === 0) {
    lines.push("（本週指標未找到直接對應的 Q&A）");
    return lines.join("\n");
  }

  const cited = topQas.slice(0, 6);
  for (const qa of cited) {
    const snippet = qa.answer.slice(0, 400) + (qa.answer.length > 400 ? "…" : "");
    const source = [qa.source_title, qa.source_date].filter(Boolean).join("、");
    lines.push(
      `**Q**：${qa.question}`,
      `**A（節錄）**：${snippet}`,
      source ? `**來源**：${source}` : "",
      `**連結**：${kbLink(qa)}`,
      "",
    );
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
export async function generateReportLocal(
  metrics: Record<string, unknown>,
  reportDate: string,
  qaCount: number,
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

  // Build all 6 sections
  const s1 = buildSituationSnapshot(alerts, core, down, qaMap);
  const s2 = buildTrafficSignals(core, down, qaMap);
  const s3 = buildTechnicalHealth(typedMetrics, down, qaMap);
  const s4 = buildIntentMapping(core, down, qaMap);
  const s5 = buildPriorityActions(down, up, topQas);
  const s6 = buildKbCitations(topQas);

  // Meta block
  const kbVersion = getKbVersion();
  const kbLabel = qaCount > 0 ? `${qaCount} Q&A` : "知識庫";
  const metaBlock = `---
**報告資訊**
- 生成方式：本地模板引擎 v1.0（Template Mode，不呼叫任何 LLM API）
- 知識庫版本：${kbVersion}（${kbLabel}，4 個來源集合）
- 分析框架：Semrush 2025 / GSC 官方指引 / First Page Sage 2025 排名因素
- 分析維度：6 維度（情勢 / 流量 / 技術 / 意圖 / 行動 / 知識庫）
- 生成日期：${reportDate}
---
`;

  return [metaBlock, s1, s2, s3, s4, s5, s6].join("\n");
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
