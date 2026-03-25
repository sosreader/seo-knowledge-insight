/**
 * report-llm — LLM-powered SEO report generation (pure TypeScript, no Python)
 *
 * Replaces the Python 04_generate_report.py for Lambda/serverless environments.
 * Uses OpenAI API via Node.js SDK with the same system prompt and ECC 6-dimension framework.
 */

import OpenAI from "openai";
import { config } from "../config.js";
import { qaStore } from "../store/qa-store.js";
import type { QAItem } from "../store/qa-store.js";

// ── System Prompt (same as Python REPORT_SYSTEM_PROMPT) ──

const REPORT_SYSTEM_PROMPT = `你是資深 SEO 分析師，任務是把本週指標變化「翻譯成意義」，用 Q&A 知識庫作為佐證。

## 核心原則
- 用戶可以直接看 Google Sheets，**不要重複數字**——聚焦「代表什麼」「為什麼」「怎麼做」。
- 每個 insight 盡量引用 Q&A 知識庫，格式：「（參考：「{關鍵句}」— {source_title}、{source_date}）」
- 知識庫沒有直接對應時，根據 SEO 原理推論，標明「（推論）」。
- 避免泛泛 SEO 建議；結合本週具體變化給出針對性分析。

## Health Score v2 演算法
\`\`\`
core_penalty = core_alert_down_count × 10      # CORE 觸發 ALERT_DOWN
non_core_penalty = non_core_alert_down_count × 3  # 非 CORE ALERT_DOWN
core_bonus = min(core_healthy_count × 2, 20)   # CORE 月趨勢 > 0% 的加分
all_core_penalty = 15 if ALL core monthly < 0%
score = clamp(100 - core_penalty - non_core_penalty + core_bonus - all_core_penalty, 0, 100)
≥80 良好 / ≥60 需關注 / <60 警示
\`\`\`

## 異常閾值
- ALERT_DOWN：月趨勢 < -15% 或週趨勢 < -20%
- ALERT_UP：月趨勢 > +15% 或週趨勢 > +20%
- CORE：曝光、點擊、CTR、有效(Coverage)、檢索未索引、工作階段總數、Organic Search、Discover、AMP(non-Rich)、AMP Article、Google News、News(new)、Image

## 業界研究（推理時引用）
- CTR 基準：Backlinko 2024（67K 關鍵字）Position 1 平均 CTR 27.6%，Position 2 降至 15.8%
- SERP Features：arxiv 2306.01785 Knowledge Panel 使 CTR 降低 ~8pp；Featured Snippet 可提升 ~20%
- NavBoost：Google 排名洩露（2024）以 13 個月滾動視窗聚合用戶點擊
- E-E-A-T：Google 2024 Experience = 作者署名 + About 頁 + 可查核外部聲譽
- Discover：First Page Sage 2025 高品質內容為首要因素；參與度為第 5 大信號
- 搜尋意圖：Semrush 2025 Awareness / Consideration / Conversion 漏斗

## 報告格式（Markdown，繁體中文，術語保留英文）

### 一、本週 SEO 情勢快照
- Health Score 與標籤（良好/需關注/警示），列出扣分明細表
- **5 大現象**：down 前 3（🔴 高）+ up 前 2（🟢 低），每個說明月/週趨勢 + 意義
- **異常指標逐項解讀**：每個 ALERT_DOWN 的推理（結合 KB 知識庫佐證）
- 跨指標關聯分析：不只描述，要有推理鏈（「我看到 X → 判斷 Y，因為 Z」）

### 二、流量信號解讀
根據 CTR / 曝光 / 點擊 / Discover / Organic Search 判斷屬於哪個象限：
- 高曝光 / 低 CTR → Title 吸引力問題或 SERP Feature 搶走點擊
- 低曝光 / 高 CTR → 排名後退，觸及縮小
- 雙低（曝光 + 點擊同降）→ NavBoost 惡化循環
- 雙穩或雙升 → 正常，找驅動因素
Discover 單獨分析，引用 First Page Sage 2025。

### 三、技術 SEO 健康度
- Coverage 有效率趨勢
- 檢索未索引增加是爬蟲預算問題還是內容品質問題？
- AMP Article vs AMP (non-Rich) 差異分析
- 結合 KB 技術相關 QA

### 四、搜尋意圖對映
- 意圖漏斗對映表（Awareness / Consideration / Conversion / Discovery 各對應指標與本期狀況）
- E-E-A-T 信號觀察

### 五、本週優先行動清單
三級行動，基於實際 down 指標和推理：
- 🔴 高優先（需立即處理）：每個 ALERT_DOWN 一條具體行動 + KB 連結
- 🟡 中優先（本週內）：CTR 優化 / 上升指標延伸
- 🟢 低優先（下週規劃）：E-E-A-T 強化 / 內容行事曆
解釋行動優先序的推理（為什麼某項比其他更緊急，考慮絕對流量影響）

**重要**：section 五必須逐一提及每個 ALERT_DOWN 指標的**完整名稱**（與指標摘要中一致），即使判斷影響不大也要列出，可歸類至低優先並註明原因。不可遺漏任何 ALERT_DOWN 指標。

### 六、AI 可見度分析
- AI Overview / SGE 出現頻率觀察
- AI 引用率（網站內容被 AI 引用的跡象）
- AI 流量佔比趨勢（若有 GA4 Referral 來源）
- 若無具體 AI visibility 資料，提供改善建議：
  - 結構化資料（JSON-LD Schema.org）完整度
  - E-E-A-T 信號強化方向
  - 內容是否適合 AI 引用（權威性、可引用段落）
  - robots.txt 中 AI bot 設定建議

### 七、來源
列出最相關的 KB Q&A（max 8），格式：
\`\`\`
[知識庫N →](/admin/seoInsight/{id}) **{source_title}、{source_date}** — {answer 前 80 字}…
\`\`\`

## Citation 規則（Perplexity 風格）
body text 引用 KB 後，句末加 \`[N]\`（同一 QA 重複引用用同一 N）。

### 知識庫引用格式（重要）
在各 section 引用 Q&A 時，使用四層分類 blockquote：
> **現象** {What 或觀察摘要}
> **原因** {Why 或機制解釋}
> **行動** {How 或具體步驟}
> **依據** {Evidence 或佐證資料}
>
> — {source_title}、{source_date}  [知識庫N →](/admin/seoInsight/{id})

若 QA 答案含 [What]/[Why]/[How]/[Evidence] 標籤，直接對應填入。
若不含標籤，根據答案內容拆分為四層。
每個 section 至少一個知識庫引用應使用此格式。`;

// ── Types ──

interface MetricData {
  readonly monthly?: number | null;
  readonly weekly?: number | null;
  readonly max?: number | null;
  readonly min?: number | null;
  readonly latest?: number | null;
  readonly previous?: number | null;
  readonly latest_date?: string;
  readonly previous_date?: string;
}

interface AlertMetric extends MetricData {
  readonly name: string;
  readonly flag: "CORE" | "ALERT_UP" | "ALERT_DOWN";
}

// ── Constants (same as metrics-parser) ──

const CORE_METRICS = new Set([
  "曝光", "點擊", "CTR", "有效 (Coverage)", "檢索未索引",
  "工作階段總數（七天）", "Organic Search (工作階段)",
  "Discover", "AMP (non-Rich)", "AMP Article",
  "Google News", "News(new)", "Image",
]);

const ALERT_THRESHOLD_MONTHLY = 0.15;
const ALERT_THRESHOLD_WEEKLY = 0.20;

// ── Helpers ──

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "N/A";
  return `${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)}%`;
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
      alerts.push({ ...m, name, flag: monthly >= 0 ? "ALERT_UP" : "ALERT_DOWN" });
    }
  }
  return alerts;
}

function buildMetricsSummary(metrics: Record<string, MetricData>): string {
  const alerts = detectAlerts(metrics);
  const lines: string[] = [];

  const core = alerts.filter((a) => a.flag === "CORE");
  const down = alerts.filter((a) => a.flag === "ALERT_DOWN").sort((a, b) => (a.monthly ?? 0) - (b.monthly ?? 0));
  const up = alerts.filter((a) => a.flag === "ALERT_UP").sort((a, b) => (b.monthly ?? 0) - (a.monthly ?? 0));

  lines.push("=== CORE 指標 ===");
  for (const m of core) {
    lines.push(`${m.name}: 月${fmtPct(m.monthly)} 週${fmtPct(m.weekly)}`);
  }

  if (down.length > 0) {
    lines.push("\n=== ALERT_DOWN（月 < -15% 或 週 < -20%）===");
    for (const m of down) {
      lines.push(`${m.name}: 月${fmtPct(m.monthly)} 週${fmtPct(m.weekly)}`);
    }
  }

  if (up.length > 0) {
    lines.push("\n=== ALERT_UP（月 > +15% 或 週 > +20%）===");
    for (const m of up) {
      lines.push(`${m.name}: 月${fmtPct(m.monthly)} 週${fmtPct(m.weekly)}`);
    }
  }

  return lines.join("\n");
}

function buildQaContext(metrics: Record<string, MetricData>): { context: string; qas: QAItem[] } {
  if (!qaStore.loaded) {
    try { qaStore.load(); } catch { /* graceful */ }
  }

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

  const seen = new Map<string, QAItem & { _queries: string[] }>();
  for (const q of queries) {
    const results = qaStore.keywordSearch(q, 5);
    for (const { item } of results) {
      if (seen.has(item.id)) {
        seen.get(item.id)!._queries.push(q);
      } else {
        seen.set(item.id, { ...item, _queries: [q] });
      }
      if (seen.size >= 12) break;
    }
    if (seen.size >= 12) break;
  }

  const qas = [...seen.values()].slice(0, 12);
  if (qas.length === 0) return { context: "", qas: [] };

  const lines = [
    "\n\n【Q&A 知識庫（來自歷次 SEO 顧問會議記錄）】",
    "（以下知識由指標異常查詢匹配，括號內是觸發此 Q&A 的指標信號）",
  ];

  for (let i = 0; i < qas.length; i++) {
    const qa = qas[i]!;
    const triggered = qa._queries.slice(0, 3).join("、");
    const snippet = qa.answer.slice(0, 600) + (qa.answer.length > 600 ? "..." : "");
    const source = [qa.source_title, qa.source_date].filter(Boolean).join("、");
    const sourceInfo = source ? `來源：${source}\n` : "";
    lines.push(
      `\n[${i + 1}] 觸發信號：${triggered}`,
      sourceInfo + `Q: ${qa.question}`,
      `A: ${snippet}`,
    );
  }

  return { context: lines.join("\n"), qas };
}

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

function buildCitationsBlock(qas: QAItem[]): string {
  if (qas.length === 0) return "";
  const items: CitationItem[] = qas.slice(0, 12).map((qa, i) => {
    const title = [qa.source_title, qa.source_date].filter(Boolean).join("、") || qa.question.slice(0, 40);
    const answerClean = qa.answer
      .replace(/\[(What|Why|How|Evidence)\]\s*/g, " ")
      .trim()
      .slice(0, 120);
    return {
      n: i + 1,
      id: qa.id,
      title,
      category: qa.category ?? "",
      date: qa.source_date ?? "",
      snippet: answerClean,
      chunk_url: `/admin/seoInsight/${qa.id}`,
      source_url: qa.source_url ?? null,
    };
  });
  const json = JSON.stringify(items).replace(/-->/g, "--\u200B>");
  return `\n<!-- citations ${json} -->`;
}

// ── Main ──

export interface LlmReportResult {
  readonly content: string;
  readonly model: string;
}

export async function generateReportLlm(
  metrics: Record<string, unknown>,
  weeks: number,
): Promise<LlmReportResult> {
  const typedMetrics = metrics as Record<string, MetricData>;
  const model = config.REPORT_MODEL;
  const client = new OpenAI({ apiKey: config.OPENAI_API_KEY });

  // Build context
  const metricsSummary = buildMetricsSummary(typedMetrics);
  const { context: qaContext, qas } = buildQaContext(typedMetrics);

  const metricsDate = new Date().toLocaleDateString("zh-TW", {
    year: "numeric", month: "2-digit", day: "2-digit",
  }).replace(/\//g, "/");

  const userMsg = [
    `報告日期：${metricsDate}`,
    "",
    "【本週指標摘要】（數字僅供 LLM 判斷方向，報告中請勿重複羅列）",
    metricsSummary,
    qaContext,
  ].join("\n");

  const response = await client.chat.completions.create({
    model,
    messages: [
      { role: "system", content: REPORT_SYSTEM_PROMPT },
      { role: "user", content: userMsg },
    ],
    max_completion_tokens: 16384,
  });

  const msg = response.choices[0]?.message;
  let reportBody = msg?.content ?? "";

  // gpt-5 series may put content in reasoning_content
  if (!reportBody) {
    const reasoning = (msg as unknown as Record<string, unknown>)?.reasoning_content;
    if (typeof reasoning === "string" && reasoning.length > 0) {
      reportBody = reasoning;
    }
  }

  if (!reportBody) {
    throw new Error(`LLM returned empty content (finish_reason: ${response.choices[0]?.finish_reason})`);
  }

  // Build meta
  const qaCount = qaStore.count;
  const sourceCollections = new Set(
    qaStore.loaded ? qaStore.allItems.map((q) => q.source_collection).filter(Boolean) : [],
  ).size || 4;

  const generatedAt = new Date().toISOString();
  const metaBlock = `---
**報告資訊**
- 生成方式：OpenAI ${model} 生成
- 知識庫版本：${qaCount} Q&A，${sourceCollections} 個來源集合
- 分析框架：Semrush 2025 / GSC 官方指引 / First Page Sage 2025 排名因素
- 分析維度：7 維度（情勢 / 流量 / 技術 / 意圖 / 行動 / AI 可見度 / 知識庫）
- 生成日期：${metricsDate}
---
`;

  const reportMeta = {
    weeks,
    generated_at: generatedAt,
    generation_mode: "openai",
    generation_label: `OpenAI ${model} 生成`,
    model,
  };

  const citationsBlock = buildCitationsBlock(qas);
  const metaComment = `\n<!-- report_meta ${JSON.stringify(reportMeta)} -->`;

  return {
    content: metaBlock + reportBody + citationsBlock + metaComment,
    model,
  };
}
