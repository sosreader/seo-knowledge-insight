/**
 * indexing-parser — 「檢索未索引」路徑分段資料解析器
 *
 * 解析 Google Sheets 中的索引覆蓋率分段表，識別 URL 路徑、
 * 全網域/總合等特殊列，產出結構化資料供 indexing-analyzer 消費。
 */

import { fetchFromSheets, parseValue } from "./metrics-parser.js";

// ── Row type classification ─────────────────────────────────────────

type RowType = "domain" | "not_indexed_total" | "path" | "sum" | "ratio" | "gap" | "header" | "other";

function classifyRow(segment: string): RowType {
  const s = segment.trim();
  if (!s) return "other";
  if (s === "全網域") return "domain";
  if (s.includes("檢索未索引")) return "not_indexed_total";
  if (s === "總合") return "sum";
  if (s.startsWith("總合/")) return "ratio";
  if (s === "差距") return "gap";
  if (s.startsWith("/")) return "path";
  return "other";
}

// ── Types ────────────────────────────────────────────────────────────

export interface IndexingRow {
  readonly segment: string;
  readonly change_pct: number | null;
  readonly delta: number | null;
  readonly value_a: number | null;
  readonly value_b: number | null;
  readonly baseline: number | null;
  readonly row_type: RowType;
}

export interface IndexingResult {
  readonly domain: IndexingRow | null;
  readonly not_indexed_total: IndexingRow | null;
  readonly paths: readonly IndexingRow[];
  readonly sum: IndexingRow | null;
  readonly ratio: IndexingRow | null;
  readonly gap: IndexingRow | null;
  readonly all_rows: readonly IndexingRow[];
}

// ── Header detection ─────────────────────────────────────────────────

const HEADER_KEYWORDS = ["變化", "趨勢", "差異", "總頁", "頁數", "基準", "Sparklines"];

function isHeaderRow(cols: readonly string[]): boolean {
  return cols.some((c) => HEADER_KEYWORDS.some((kw) => c.includes(kw)));
}

// ── Section extraction ──────────────────────────────────────────────
// When parsing the full sheet (gid=0), the indexing section is at the bottom.
// Pattern: 全網域 → 檢索未索引 (全部) → /path/ rows → 總合 → 總合/全網域 → 差距

function extractIndexingSection(lines: readonly string[]): readonly string[] {
  // Find "檢索未索引 (全部)" — the anchor for the section
  let anchorIdx = -1;
  for (let i = lines.length - 1; i >= 0; i--) {
    const col0 = (lines[i]!.split("\t")[0] ?? "").trim();
    if (col0.includes("檢索未索引") && col0.includes("全部")) {
      anchorIdx = i;
      break;
    }
  }

  if (anchorIdx === -1) return lines; // Not found — treat entire input as indexing data

  // Look backwards from anchor to find "全網域" (domain row, at most 3 lines before)
  let startIdx = anchorIdx;
  for (let i = anchorIdx - 1; i >= Math.max(0, anchorIdx - 3); i--) {
    const col0 = (lines[i]!.split("\t")[0] ?? "").trim();
    if (col0 === "全網域") {
      startIdx = i;
      break;
    }
  }

  // Look forwards from anchor to find "差距" or end
  let endIdx = lines.length;
  for (let i = anchorIdx + 1; i < lines.length; i++) {
    const col0 = (lines[i]!.split("\t")[0] ?? "").trim();
    if (col0 === "差距") {
      endIdx = i + 1;
      break;
    }
  }

  return lines.slice(startIdx, endIdx);
}

// ── Parser ───────────────────────────────────────────────────────────

function parseRow(line: string): IndexingRow | null {
  const cols = line.split("\t");
  const segment = (cols[0] ?? "").trim();
  if (!segment) return null;

  const rowType = classifyRow(segment);
  if (rowType === "header" || rowType === "other") return null;

  return {
    segment,
    change_pct: cols.length > 1 ? parseValue(cols[1]!) : null,
    delta: cols.length > 2 ? parseValue(cols[2]!) : null,
    value_a: cols.length > 3 ? parseValue(cols[3]!) : null,
    value_b: cols.length > 4 ? parseValue(cols[4]!) : null,
    baseline: cols.length > 6 ? parseValue(cols[6]!) : null,
    row_type: rowType,
  };
}

const EMPTY: IndexingResult = {
  domain: null, not_indexed_total: null, paths: [], sum: null, ratio: null, gap: null, all_rows: [],
};

export function parseIndexingTsv(text: string): IndexingResult {
  const allLines = text.split("\n").filter((l) => l.trim());
  if (allLines.length === 0) return EMPTY;

  // Skip header if present
  let lines = allLines;
  for (let i = 0; i < allLines.length; i++) {
    if (isHeaderRow(allLines[i]!.split("\t"))) {
      lines = allLines.slice(i + 1);
      break;
    }
  }

  // Extract indexing section from full sheet data
  const section = extractIndexingSection(lines);

  const rows: IndexingRow[] = [];
  for (const line of section) {
    const row = parseRow(line);
    if (row) rows.push(row);
  }

  if (rows.length === 0) return EMPTY;

  return {
    domain: rows.find((r) => r.row_type === "domain") ?? null,
    not_indexed_total: rows.find((r) => r.row_type === "not_indexed_total") ?? null,
    paths: rows.filter((r) => r.row_type === "path"),
    sum: rows.find((r) => r.row_type === "sum") ?? null,
    ratio: rows.find((r) => r.row_type === "ratio") ?? null,
    gap: rows.find((r) => r.row_type === "gap") ?? null,
    all_rows: rows,
  };
}

// ── Main entry ───────────────────────────────────────────────────────

export async function loadIndexing(
  source: string,
  tab = "vocus",
): Promise<IndexingResult> {
  const rawTsv = await fetchFromSheets(source, tab);
  return parseIndexingTsv(rawTsv);
}
