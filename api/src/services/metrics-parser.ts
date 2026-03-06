/**
 * metrics-parser — Google Sheets 指標擷取與解析（純 Node.js，無 Python 依賴）
 *
 * 移植自 Python utils/metrics_parser.py，讓 Lambda 環境也能解析指標。
 */

// ── 閾值常數 ──
const ALERT_THRESHOLD_MONTHLY = 0.15;
const ALERT_THRESHOLD_WEEKLY = 0.20;

const CORE_METRICS = new Set([
  "曝光", "點擊", "CTR", "有效 (Coverage)", "檢索未索引",
  "工作階段總數（七天）", "Organic Search (工作階段)",
  "Discover", "AMP (non-Rich)", "AMP Article",
  "Google News", "News(new)", "Image",
]);

const SKIP_METRICS = new Set(["Sparklines", "#N/A", ""]);

const ALLOWED_HOST = "docs.google.com";
const SHEET_ID_RE = /^[a-zA-Z0-9_-]{10,60}$/;
const GID_RE = /^\d{1,10}$/;
const MAX_RESPONSE_BYTES = 10 * 1024 * 1024;

// ── Types ──

export interface MetricData {
  monthly: number | null;
  weekly: number | null;
  max: number | null;
  min: number | null;
  latest: number | null;
  previous: number | null;
  latest_date: string;
  previous_date: string;
}

export interface AnomalyData extends MetricData {
  name: string;
  flag: "CORE" | "ALERT_UP" | "ALERT_DOWN";
}

export interface MetricsResult {
  metrics: Record<string, MetricData>;
  anomalies: readonly AnomalyData[];
  total_metrics: number;
  total_anomalies: number;
}

// ── URL 解析 ──

function parseSheetId(url: string): { sheetId: string; gid: string } {
  const parsed = new URL(url);
  if (parsed.hostname !== ALLOWED_HOST && parsed.hostname !== "sheets.google.com") {
    throw new Error(`不允許的 Sheets 主機：${parsed.hostname}`);
  }
  const m = url.match(/\/spreadsheets\/d\/([a-zA-Z0-9_-]+)/);
  if (!m) throw new Error(`無法從 URL 解析 sheet ID`);
  const sheetId = m[1];
  if (!SHEET_ID_RE.test(sheetId)) throw new Error(`sheet_id 格式不合法：${sheetId}`);
  const gidMatch = url.match(/[?&#]gid=([0-9]+)/);
  const gid = gidMatch ? gidMatch[1] : "0";
  if (!GID_RE.test(gid)) throw new Error(`gid 格式不合法：${gid}`);
  return { sheetId, gid };
}

async function findGidByTabName(sheetId: string, tab: string): Promise<string | null> {
  if (!SHEET_ID_RE.test(sheetId)) throw new Error(`sheet_id 格式不合法`);
  try {
    const url = `https://${ALLOWED_HOST}/spreadsheets/d/${sheetId}/edit`;
    const resp = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0" },
      signal: AbortSignal.timeout(10_000),
    });
    if (!resp.ok) return null;
    const html = await resp.text();
    const escaped = tab.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const r1 = new RegExp(`"sheetId":(\\d+)[^}]*"title":"${escaped}"`);
    const m1 = html.match(r1);
    if (m1 && GID_RE.test(m1[1])) return m1[1];
    const r2 = new RegExp(`"title":"${escaped}"[^}]*"sheetId":(\\d+)`);
    const m2 = html.match(r2);
    if (m2 && GID_RE.test(m2[1])) return m2[1];
  } catch {
    // silent fail, return null
  }
  return null;
}

// ── Google Sheets 下載 ──

export async function fetchFromSheets(urlOrId: string, tab = "vocus"): Promise<string> {
  let sheetId: string;
  let gid: string;

  if (urlOrId.startsWith("http")) {
    const parsed = parseSheetId(urlOrId);
    sheetId = parsed.sheetId;
    if (parsed.gid !== "0") {
      gid = parsed.gid;
    } else {
      gid = (await findGidByTabName(sheetId, tab)) ?? "0";
    }
  } else {
    if (!SHEET_ID_RE.test(urlOrId)) throw new Error(`sheet_id 格式不合法`);
    sheetId = urlOrId;
    gid = (await findGidByTabName(sheetId, tab)) ?? "0";
  }

  if (!GID_RE.test(gid)) throw new Error(`gid 格式不合法：${gid}`);

  const csvUrl =
    `https://${ALLOWED_HOST}/spreadsheets/d/${sheetId}/export?format=csv&id=${sheetId}&gid=${gid}`;

  const resp = await fetch(csvUrl, {
    headers: { "User-Agent": "Mozilla/5.0" },
    signal: AbortSignal.timeout(30_000),
  });
  if (!resp.ok) {
    throw new Error(`Google Sheets 回應異常，HTTP ${resp.status}`);
  }
  const buf = await resp.arrayBuffer();
  if (buf.byteLength > MAX_RESPONSE_BYTES) {
    throw new Error(`回應超過 ${MAX_RESPONSE_BYTES} bytes`);
  }
  const text = new TextDecoder("utf-8").decode(buf).replace(/^\uFEFF/, "");

  // CSV → TSV
  const lines = parseCSV(text);
  return lines.map((row) => row.join("\t")).join("\n");
}

// ── 簡易 CSV parser（處理引號內逗號與換行）──

function parseCSV(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (i + 1 < text.length && text[i + 1] === '"') {
          cell += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        cell += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(cell);
      cell = "";
    } else if (ch === "\n" || (ch === "\r" && text[i + 1] === "\n")) {
      if (ch === "\r") i++;
      row.push(cell);
      cell = "";
      rows.push(row);
      row = [];
    } else if (ch === "\r") {
      row.push(cell);
      cell = "";
      rows.push(row);
      row = [];
    } else {
      cell += ch;
    }
  }
  if (cell || row.length > 0) {
    row.push(cell);
    rows.push(row);
  }
  return rows;
}

// ── TSV 解析 ──

function parseValue(raw: string): number | null {
  const v = raw.trim();
  if (["#N/A", "#DIV/0!", "#REF!", "#VALUE!", ""].includes(v)) return null;
  if (v.endsWith("%")) {
    const n = parseFloat(v.replace("%", ""));
    return isNaN(n) ? null : n / 100;
  }
  const n = parseFloat(v.replace(/,/g, ""));
  return isNaN(n) ? null : n;
}

export function parseMetricsTsv(text: string): Record<string, MetricData> {
  const lines = text.split("\n").filter((l) => l.trim());
  if (lines.length === 0) return {};

  let headerIdx = 0;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes("月趨勢") || lines[i].includes("上週")) {
      headerIdx = i;
      break;
    }
  }

  const headerCols = lines[headerIdx].split("\t");
  const dateCols = headerCols
    .map((c) => c.trim())
    .filter((c) => /^\d+\/\d+\/\d+/.test(c));
  const latestDate = dateCols[0] ?? "";
  const previousDate = dateCols[1] ?? "";

  const safeCol = (cols: string[], idx: number): number | null =>
    idx < cols.length ? parseValue(cols[idx]) : null;

  const metrics: Record<string, MetricData> = {};
  for (const line of lines.slice(headerIdx + 1)) {
    const cols = line.split("\t");
    if (!cols[0]?.trim()) continue;
    const name = cols[0].trim();
    if (SKIP_METRICS.has(name)) continue;

    metrics[name] = {
      monthly: safeCol(cols, 1),
      weekly: safeCol(cols, 2),
      max: safeCol(cols, 3),
      min: safeCol(cols, 4),
      latest: cols.length > 6 ? safeCol(cols, 6) : null,
      previous: cols.length > 7 ? safeCol(cols, 7) : null,
      latest_date: latestDate,
      previous_date: previousDate,
    };
  }
  return metrics;
}

// ── 異常偵測 ──

export function detectAnomalies(metrics: Record<string, MetricData>): readonly AnomalyData[] {
  const alerts: AnomalyData[] = [];

  for (const [name, m] of Object.entries(metrics)) {
    if (CORE_METRICS.has(name)) {
      alerts.push({ ...m, name, flag: "CORE" });
      continue;
    }
    const monthlyAbs = typeof m.monthly === "number" ? Math.abs(m.monthly) : 0;
    const weeklyAbs = typeof m.weekly === "number" ? Math.abs(m.weekly) : 0;

    if (monthlyAbs >= ALERT_THRESHOLD_MONTHLY || weeklyAbs >= ALERT_THRESHOLD_WEEKLY) {
      const flag = (m.monthly ?? 0) > 0 ? "ALERT_UP" : "ALERT_DOWN";
      alerts.push({ ...m, name, flag });
    }
  }
  return alerts;
}

// ── 主入口 ──

export async function loadMetrics(source: string, tab = "vocus"): Promise<MetricsResult> {
  const rawTsv = await fetchFromSheets(source, tab);
  const metrics = parseMetricsTsv(rawTsv);
  const anomalies = detectAnomalies(metrics);
  return {
    metrics,
    anomalies,
    total_metrics: Object.keys(metrics).length,
    total_anomalies: anomalies.length,
  };
}
