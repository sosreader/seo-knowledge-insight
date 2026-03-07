/**
 * indexing-analyzer — 「檢索未索引」洞察分析引擎
 *
 * 兩種模式：
 * 1. Rule-based template（無 LLM）：formatIndexingSection()
 * 2. LLM prompt 輔助：INDEXING_ANALYSIS_PROMPT + buildIndexingContext()
 */

import type { IndexingResult, IndexingRow } from "./indexing-parser.js";

// ── Constants ────────────────────────────────────────────────────────

const SEVERITY_THRESHOLDS = {
  critical: 0.5,   // >50% 上升 → 嚴重惡化
  warning: 0.15,   // >15% 上升 → 需關注
  improving: -0.1, // <-10% → 改善中
} as const;

// ── Types ────────────────────────────────────────────────────────────

export interface PathInsight {
  readonly segment: string;
  readonly change_pct: number;
  readonly severity: "critical" | "warning" | "stable" | "improving";
  readonly recommendation: string;
}

export interface IndexingInsight {
  readonly overall_severity: "critical" | "warning" | "stable" | "improving";
  readonly domain_change_pct: number | null;
  readonly not_indexed_change_pct: number | null;
  readonly worsening_paths: readonly PathInsight[];
  readonly improving_paths: readonly PathInsight[];
  readonly stable_paths: readonly PathInsight[];
  readonly summary_text: string;
  readonly markdown: string;
}

// ── Path-specific recommendations ────────────────────────────────────

const PATH_RECOMMENDATIONS: ReadonlyArray<{
  readonly match: string;
  readonly advice: string;
}> = [
  { match: "/article/", advice: "文章頁是核心內容資產。檢查是否有重複/薄內容被 Google 判定低品質，優先合併或補充深度內容。" },
  { match: "/tag/", advice: "Tag 頁面常因內容稀薄被判定為低品質。考慮 noindex 低流量 tag 頁，或為高流量 tag 補充策展內容。" },
  { match: "/en/", advice: "多語系路徑。確認 hreflang 設定正確、canonical 未衝突，避免被視為重複內容。" },
  { match: "/post", advice: "檢查文章是否有足夠獨特內容。若與 /article/ 重疊，確認 canonical 設定避免自我競爭。" },
  { match: "/salon/", advice: "UGC（使用者生成內容）路徑。高未索引率可能源自內容品質不一，考慮設定品質門檻或 noindex 低品質頁面。" },
  { match: "/user/", advice: "使用者個人頁面通常內容稀薄。建議 noindex 處理，將爬蟲資源集中在高價值內容頁。" },
];

function getRecommendation(segment: string, severity: string): string {
  const specific = PATH_RECOMMENDATIONS.find((r) => segment.includes(r.match));
  if (specific) return specific.advice;

  if (severity === "critical") {
    return `此路徑未索引率劇增，立即在 GSC → 索引 → 網頁中篩選此路徑，檢查「已檢索 — 目前未建立索引」的具體 URL。`;
  }
  if (severity === "improving") {
    return `此路徑狀況改善中，持續監控確認趨勢穩定。`;
  }
  return `定期檢查此路徑的索引狀態，確認無異常波動。`;
}

// ── Severity classification ──────────────────────────────────────────

function classifySeverity(changePct: number | null): PathInsight["severity"] {
  if (changePct == null) return "stable";
  if (changePct >= SEVERITY_THRESHOLDS.critical) return "critical";
  if (changePct >= SEVERITY_THRESHOLDS.warning) return "warning";
  if (changePct <= SEVERITY_THRESHOLDS.improving) return "improving";
  return "stable";
}

// ── Formatting helpers ───────────────────────────────────────────────

function fmtPct(v: number | null): string {
  if (v == null) return "N/A";
  const sign = v >= 0 ? "+" : "";
  return `${sign}${(v * 100).toFixed(1)}%`;
}

function fmtNum(v: number | null): string {
  if (v == null) return "N/A";
  return v.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

// ── Analyzer ─────────────────────────────────────────────────────────

function buildPathInsight(row: IndexingRow): PathInsight {
  const severity = classifySeverity(row.change_pct);
  return {
    segment: row.segment,
    change_pct: row.change_pct ?? 0,
    severity,
    recommendation: getRecommendation(row.segment, severity),
  };
}

export function analyzeIndexing(data: IndexingResult): IndexingInsight {
  const pathInsights = data.paths.map(buildPathInsight);

  const worsening = pathInsights
    .filter((p) => p.severity === "critical" || p.severity === "warning")
    .sort((a, b) => b.change_pct - a.change_pct);

  const improving = pathInsights
    .filter((p) => p.severity === "improving")
    .sort((a, b) => a.change_pct - b.change_pct);

  const stable = pathInsights.filter((p) => p.severity === "stable");

  const overallSeverity = worsening.some((p) => p.severity === "critical")
    ? "critical"
    : worsening.length > 0
      ? "warning"
      : improving.length > pathInsights.length / 2
        ? "improving"
        : "stable";

  const domainPct = data.domain?.change_pct ?? null;
  const notIndexedPct = data.not_indexed_total?.change_pct ?? null;

  const summary = buildSummaryText(overallSeverity, worsening, improving, domainPct, notIndexedPct);
  const markdown = formatIndexingSection(data, { worsening, improving, stable }, overallSeverity, summary);

  return {
    overall_severity: overallSeverity,
    domain_change_pct: domainPct,
    not_indexed_change_pct: notIndexedPct,
    worsening_paths: worsening,
    improving_paths: improving,
    stable_paths: stable,
    summary_text: summary,
    markdown,
  };
}

// ── Summary text ─────────────────────────────────────────────────────

function buildSummaryText(
  severity: IndexingInsight["overall_severity"],
  worsening: readonly PathInsight[],
  improving: readonly PathInsight[],
  domainPct: number | null,
  notIndexedPct: number | null,
): string {
  const parts: string[] = [];

  if (severity === "critical") {
    parts.push(`索引覆蓋率處於警示狀態。`);
  } else if (severity === "warning") {
    parts.push(`索引覆蓋率需要關注。`);
  } else if (severity === "improving") {
    parts.push(`索引覆蓋率整體改善中。`);
  } else {
    parts.push(`索引覆蓋率整體穩定。`);
  }

  if (domainPct != null) {
    parts.push(`全網域變化率 ${fmtPct(domainPct)}。`);
  }
  if (notIndexedPct != null) {
    parts.push(`檢索未索引整體變化 ${fmtPct(notIndexedPct)}。`);
  }

  if (worsening.length > 0) {
    const worst = worsening[0]!;
    parts.push(`最嚴重路徑：${worst.segment}（${fmtPct(worst.change_pct)}）。`);
  }
  if (improving.length > 0) {
    parts.push(`${improving.length} 個路徑趨勢改善。`);
  }

  return parts.join("");
}

// ── Markdown formatter ───────────────────────────────────────────────

function formatIndexingSection(
  data: IndexingResult,
  classified: {
    worsening: readonly PathInsight[];
    improving: readonly PathInsight[];
    stable: readonly PathInsight[];
  },
  severity: IndexingInsight["overall_severity"],
  summary: string,
): string {
  const lines: string[] = [];

  // Section header
  const severityLabel = severity === "critical" ? "警示"
    : severity === "warning" ? "需關注"
    : severity === "improving" ? "改善中"
    : "穩定";

  lines.push(`## 檢索未索引分析（${severityLabel}）\n`);
  lines.push(`${summary}\n`);

  // Domain overview table
  lines.push("### 總覽\n");
  lines.push("| 區段 | 變化率 | 數值 A | 數值 B | 基準值 |");
  lines.push("|------|--------|--------|--------|--------|");

  if (data.domain) {
    lines.push(
      `| ${data.domain.segment} | ${fmtPct(data.domain.change_pct)} | ${fmtNum(data.domain.value_a)} | ${fmtNum(data.domain.value_b)} | ${fmtNum(data.domain.baseline)} |`,
    );
  }
  if (data.not_indexed_total) {
    lines.push(
      `| ${data.not_indexed_total.segment} | ${fmtPct(data.not_indexed_total.change_pct)} | ${fmtNum(data.not_indexed_total.value_a)} | ${fmtNum(data.not_indexed_total.value_b)} | ${fmtNum(data.not_indexed_total.baseline)} |`,
    );
  }
  lines.push("");

  // Worsening paths (high priority)
  if (classified.worsening.length > 0) {
    lines.push("### 惡化路徑（需優先處理）\n");
    for (const p of classified.worsening) {
      const icon = p.severity === "critical" ? "🔴" : "🟡";
      const row = data.paths.find((r) => r.segment === p.segment);
      lines.push(
        `#### ${icon} ${p.segment}（${fmtPct(p.change_pct)}）\n`,
        `- **數值**：A=${fmtNum(row?.value_a ?? null)} / B=${fmtNum(row?.value_b ?? null)} / 基準=${fmtNum(row?.baseline ?? null)}`,
        `- **建議**：${p.recommendation}`,
        "",
      );
    }
  }

  // Improving paths
  if (classified.improving.length > 0) {
    lines.push("### 改善中路徑\n");
    for (const p of classified.improving) {
      lines.push(`- **${p.segment}**（${fmtPct(p.change_pct)}）：${p.recommendation}`);
    }
    lines.push("");
  }

  // Stable paths
  if (classified.stable.length > 0) {
    lines.push("### 穩定路徑\n");
    for (const p of classified.stable) {
      lines.push(`- ${p.segment}（${fmtPct(p.change_pct)}）`);
    }
    lines.push("");
  }

  // Summary ratio
  if (data.ratio) {
    lines.push("### 總合 / 全網域比率\n");
    lines.push(
      `- 變化率：${fmtPct(data.ratio.change_pct)}`,
      `- 數值 A 佔比：${data.ratio.value_a != null ? fmtPct(data.ratio.value_a) : "N/A"}`,
      `- 數值 B 佔比：${data.ratio.value_b != null ? fmtPct(data.ratio.value_b) : "N/A"}`,
      "",
    );
  }

  // Action items
  lines.push("### 行動建議\n");
  if (severity === "critical" || severity === "warning") {
    lines.push(
      "1. **立即**：在 GSC → 索引 → 網頁，匯出「已檢索 — 目前未建立索引」的 URL 清單，按目錄分群找出問題集中區",
      "2. **本週**：針對惡化最嚴重的路徑，檢查 robots.txt、canonical、內容品質",
      "3. **持續**：建立每週索引覆蓋率監控儀表板，追蹤各路徑趨勢",
      "",
    );
  } else {
    lines.push(
      "1. 持續監控各路徑索引覆蓋率趨勢",
      "2. 定期檢查新增頁面的索引狀態",
      "",
    );
  }

  return lines.join("\n");
}

// ── LLM Prompt ───────────────────────────────────────────────────────

export const INDEXING_ANALYSIS_PROMPT = `你是 SEO 技術分析師，專精 Google Search Console 索引覆蓋率分析。

## 任務
分析以下「檢索未索引」（Crawled - Currently Not Indexed）路徑分段資料，產出可操作的洞察。

## 分析框架（必須涵蓋）
1. **嚴重度評估**：整體索引健康度（critical/warning/stable/improving）
2. **路徑優先序**：依影響力和惡化速度排序，指出最需優先處理的路徑
3. **根因假設**：每個惡化路徑提出 2-3 個可能原因（薄內容、重複、canonical 錯誤、robots 封鎖等）
4. **交叉比對**：路徑間的關聯性（如 /tag/ 和 /article/ 是否共享相同問題）
5. **具體行動**：每個路徑至少一個可在 GSC 驗證的具體步驟

## 背景知識
- 「已檢索 — 目前未建立索引」代表 Google 已爬取但選擇不收錄
- 常見原因：內容品質不足、重複內容、canonical 衝突、crawl budget 浪費
- /tag/ /user/ 等路徑常因內容稀薄被排除索引
- /article/ /post 等核心內容路徑的未索引率上升是嚴重警訊
- 變化率為正代表未索引頁面增加（惡化），為負代表改善

## 輸出格式
使用繁體中文，Markdown 格式，包含：
- 總結段落（2-3 句）
- 優先處理清單（按嚴重度排序）
- 每個路徑的根因假設 + 驗證步驟
- 整體建議（短期/中期/長期）
`;

/**
 * Build structured context string for the LLM prompt.
 */
export function buildIndexingContext(data: IndexingResult): string {
  const lines: string[] = ["## 檢索未索引路徑分段資料\n"];

  lines.push("| 路徑 | 變化率 | Delta | 數值A | 數值B | 基準值 | 類型 |");
  lines.push("|------|--------|-------|-------|-------|--------|------|");

  for (const row of data.all_rows) {
    lines.push(
      `| ${row.segment} | ${fmtPct(row.change_pct)} | ${row.delta ?? "-"} | ${fmtNum(row.value_a)} | ${fmtNum(row.value_b)} | ${fmtNum(row.baseline)} | ${row.row_type} |`,
    );
  }

  return lines.join("\n");
}
