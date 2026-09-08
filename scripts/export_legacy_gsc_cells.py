"""export_legacy_gsc_cells.py — 舊爬蟲「20 格等價匯出」

用 GSC Search Analytics API 直接產出與舊爬蟲 `seo-automation` 讀 GSC 網頁介面卡片
完全相同的 20 個「總點擊次數」（G20~G34 共 15 格、G38~G42 共 5 格），供外部顧問拿
與舊批次同口徑的資料，也用來驗證「API 抽樣值」與「網頁介面卡片值」是否等價。

只呼叫 Search Analytics API 讀資料，**不寫 Supabase**——這支跟
`ingest_gsc_search_analytics.py` 的抽樣寫入管線是平行的兩條路，互不影響。


═══ 舊爬蟲怎麼做，本腳本照抄語意 ═══

`seo-automation/config.mjs` 的 `SEARCH_PERFORMANCE` 定義兩組共 20 筆：

  queryPage（15 筆，G20~G34）：7 筆 `type: "page"` + 8 筆 `type: "query"`，各帶一個
    `pattern`。舊爬蟲把 URL 開成
    `performance/search-analytics?resource_id=…&num_of_days=7&page=~<pattern>`
    （或 `&query=~<pattern>`）——`~` 前綴是 GSC 介面「自訂（規則運算式）」語法，
    讀卡片「總點擊次數」。這就是 Search Analytics API 的
    `dimensionFilterGroups=[{filters:[{dimension:"page"|"query",
    operator:"includingRegex", expression:<pattern>}]}]`，不帶 `dimensions`
    （不分組，回傳即該規則運算式命中範圍內的加總）。

  multiType（5 筆，G38~G42）：image / video / news 三個 `search_type` 的整體卡片、
    加上探索（`performance/discover`）與 Google News（`performance/google-news`）。
    這五筆**沒有 pattern**——是該 search type 在整個 property 上的總點擊，對應 API
    的 `type` 參數分別是 `image`/`video`/`news`/`discover`/`googleNews`（後兩者是
    Search Analytics API 為這兩個介面頁面保留的 `type` 值，不是走不同的 endpoint）。

  兩組都用同一個 7 天視窗（`days: 7`），介面卡片的「總點擊次數」在不分組查詢時
  就是聚合值，`aggregationType` 用 `auto`（介面卡片預設就是這個）。


═══ config.mjs 用 regex 解析，不跑 node、不硬寫死一份新常量 ═══

15 個 pattern 與 5 個 surface 是舊爬蟲的事實來源，寫死在本檔會在 config.mjs 改了
以後悄悄失準且沒有任何錯誤訊號。改用 regex 從 `SEARCH_PERFORMANCE` 與 `CELL` 兩個
區塊抽取，解析失敗（找不到區塊、entry 數量不對、pattern 是空字串）一律拋
`ConfigParseError` 中止，不落回一份預設值悄悄跑錯資料。

pattern 在 .mjs 原始碼裡是雙引號字串常量（例如 `"^https://vocus\\.cc/$"`，檔案裡
是**兩個**反斜線字元，JS 剖析後才變成一個）。JSON 字串跳脫規則在 `\\`、`\"` 這個子集
上與 JS 雙引號字串跳脫規則相同，借 `json.loads` 現成的解碼器換算，不必自己重寫一份
跳脫表（見 `_js_string`）。


═══ 視窗規則：--start/--end 明給，或 --days/--end-offset 推算 ═══

已知一例：舊爬蟲 09-04 18:20 台北跑的批次，經三角反推視窗是 2026-08-26~2026-09-01
（7 天、end-offset=3，即「跑批日 -3 天」為視窗終點）。`--days`/`--end-offset` 的預設值
就是這組反推值，`--start`/`--end` 可整組覆寫（兩者需同時給，或都不給）。


═══ 為什麼預設是 dry-run（只印計畫，不打 API）═══

本機沒有 `GSC_READONLY_KEY`（只在 GitHub Actions secret，見 `.github/workflows/
gsc-search-analytics.yml`）。跟 repo 內其他 ingest_*.py 一致的 `--execute` 才真的
打 API 這個慣例，讓沒有金鑰的環境也能跑通 config 解析、視窗計算、request body 組法
這幾件事並被測試覆蓋，不必等到有金鑰才能驗證邏輯正不正確。


═══ 429/5xx 重試，配額錯誤致命中止 ═══

參考 `ai_sov_providers.py` 的分類精神（見該檔設計決定 5）：401/403（金鑰失效／
權限不足）與帶 dailyLimitExceeded／quotaExceeded 字樣的 429（每日配額耗盡）
一律 fatal、不重試——對 20 次呼叫各重試到底沒有意義，只是徒勞。其餘 429 與
408/500/502/503/504 視為暫時性，退避重試 `MAX_ATTEMPTS` 次。
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    # 主腳本以 `python scripts/export_legacy_gsc_cells.py` 直接執行時，
    # sys.path[0] 是 scripts/ 而非 repo root，見 gsc_surfaces.py 同款注意事項。
    sys.path.insert(0, str(ROOT_DIR))

from scripts.gsc_surfaces import ALLOWED_SEARCH_TYPES, PROPERTY  # noqa: E402
from scripts.ingest_gsc_search_analytics import (  # noqa: E402
    GSC_QUERY_URL,
    HTTP_TIMEOUT_SECONDS,
    gsc_access_token,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("export_legacy_gsc_cells")

# ══════════════════════════════════════════════════════════════════════
# 常數
# ══════════════════════════════════════════════════════════════════════

# 舊爬蟲 repo 與本 repo 是本機同層的手足目錄（~/Documents/seo-automation、
# ~/Documents/seo-knowledge-insight），這是目前唯一已知的部署佈局，非 CI 假設。
# 找不到就要求 --config 明給，不猜第二個路徑。
DEFAULT_CONFIG_PATH = ROOT_DIR.parent / "seo-automation" / "config.mjs"

DEFAULT_OUT_DIR = ROOT_DIR / "output" / "legacy-cells"

DEFAULT_DAYS = 7
DEFAULT_END_OFFSET = 3  # 已知例：跑批日 09-04 → 視窗終點 09-01

USER_AGENT = "seo-knowledge-insight-legacy-gsc-export/1.0"

MULTI_TYPE_PATH_SEARCH_TYPE = {
    "performance/discover": "discover",
    "performance/google-news": "googleNews",
}

RETRYABLE_STATUS = (408, 429, 500, 502, 503, 504)
FATAL_HTTP_STATUS = (401, 403)
# 429 的 body 若帶這些字樣視為「每日配額耗盡」，重試沒有意義；其餘 429（速率限制）
# 仍走一般重試。Google API 的配額錯誤格式不只一種（errors[].reason 或純文字
# message），用字串包含判斷是刻意從寬的啟發式，寧可誤判成可重試（頂多多等幾次）
# 也不要誤判成 fatal 而漏掉真正暫時性的限流。
FATAL_QUOTA_MARKERS = ("dailyLimitExceeded", "quotaExceeded", "RESOURCE_EXHAUSTED")
MAX_ATTEMPTS = 4
RETRY_BACKOFF_SECONDS = (2.0, 8.0, 20.0)  # 長度必須 = MAX_ATTEMPTS - 1


class ConfigParseError(RuntimeError):
    """config.mjs 解析失敗——找不到區塊、entry 數量不對、或欄位缺漏。"""


class LegacyExportError(RuntimeError):
    """呼叫 Search Analytics API 失敗，且不是可重試的暫時性錯誤。"""


# ══════════════════════════════════════════════════════════════════════
# 資料結構
# ══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LegacyCell:
    """一個「舊爬蟲卡片」= 一次不分組的 Search Analytics API 查詢。"""

    cell: str            # "G20"
    label: str            # 舊爬蟲的中文標籤
    kind: str             # "page" | "query" | "surface"
    search_type: str      # API 的 type 參數：web/image/video/news/discover/googleNews
    dimension: str | None  # 有 pattern 時的過濾維度："page" | "query"；surface 類為 None
    pattern: str | None    # includingRegex 的 expression；surface 類為 None


@dataclass(frozen=True)
class ResultRow:
    cell: LegacyCell
    start: date
    end: date
    clicks: int | None    # dry-run 時為 None（未呼叫 API）
    operator: str = "includingRegex"

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell": self.cell.cell,
            "label": self.cell.label,
            "kind": self.cell.kind,
            "search_type": self.cell.search_type,
            "dimension": self.cell.dimension,
            "pattern": self.cell.pattern,
            "operator": self.operator,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "clicks": self.clicks,
        }


CSV_FIELDS = ["cell", "label", "kind", "search_type", "dimension", "pattern",
              "operator", "start", "end", "clicks"]


# ══════════════════════════════════════════════════════════════════════
# config.mjs 解析
# ══════════════════════════════════════════════════════════════════════

_BLOCK_RE_TEMPLATE = r"{name}\s*=\s*\{{(.*?)\n\}};"

_QUERY_PAGE_ENTRY_RE = re.compile(
    r'\{\s*label:\s*"((?:[^"\\]|\\.)*)"\s*,\s*type:\s*"((?:[^"\\]|\\.)*)"\s*,'
    r'\s*pattern:\s*"((?:[^"\\]|\\.)*)"\s*\}'
)
_MULTI_TYPE_ENTRY_RE = re.compile(
    r'\{\s*label:\s*"((?:[^"\\]|\\.)*)"\s*,\s*path:\s*"((?:[^"\\]|\\.)*)"\s*'
    r'(?:,\s*searchType:\s*"((?:[^"\\]|\\.)*)"\s*)?\}'
)


def _js_string(raw: str) -> str:
    """把 .mjs 原始碼裡雙引號字串常量的原始字元，換算成 JS 執行後的實際字串值。

    JSON 字串跳脫規則與 JS 雙引號字串跳脫規則在 `\\\\`／`\\"` 這個子集上相同，
    借 json.loads 現成的解碼器，不必自己重寫一份跳脫表。
    """
    try:
        decoded = json.loads(f'"{raw}"')
    except json.JSONDecodeError as exc:
        raise ConfigParseError(f"無法解析 config.mjs 裡的字串常量：{raw!r}") from exc
    if not decoded:
        raise ConfigParseError("config.mjs 裡出現空字串常量，這在 label/type/pattern 都不合法")
    return decoded


def _extract_block(text: str, name: str) -> str:
    match = re.search(_BLOCK_RE_TEMPLATE.format(name=re.escape(name)), text, re.S)
    if not match:
        raise ConfigParseError(f"config.mjs 找不到 `{name}` 區塊（改了變數名稱或格式？）")
    return match.group(1)


def _parse_query_page(block: str) -> list[dict[str, str]]:
    entries = [
        {"label": _js_string(m.group(1)), "type": _js_string(m.group(2)),
         "pattern": _js_string(m.group(3))}
        for m in _QUERY_PAGE_ENTRY_RE.finditer(block)
    ]
    if len(entries) != 15:
        raise ConfigParseError(
            f"queryPage 解析出 {len(entries)} 筆，預期 15 筆（7 page + 8 query）；"
            "config.mjs 格式可能變了，需要更新 regex"
        )
    for entry in entries:
        if entry["type"] not in ("page", "query"):
            raise ConfigParseError(f"queryPage 出現未知 type：{entry['type']!r}（label={entry['label']!r}）")
    return entries


def _parse_multi_type(block: str) -> list[dict[str, str | None]]:
    entries = [
        {"label": _js_string(m.group(1)), "path": _js_string(m.group(2)),
         "search_type_raw": _js_string(m.group(3)) if m.group(3) is not None else None}
        for m in _MULTI_TYPE_ENTRY_RE.finditer(block)
    ]
    if len(entries) != 5:
        raise ConfigParseError(
            f"multiType 解析出 {len(entries)} 筆，預期 5 筆；config.mjs 格式可能變了，需要更新 regex"
        )
    return entries


def _resolve_multi_type_search_type(entry: Mapping[str, str | None]) -> str:
    if entry["search_type_raw"]:
        return str(entry["search_type_raw"])
    path = str(entry["path"])
    search_type = MULTI_TYPE_PATH_SEARCH_TYPE.get(path)
    if search_type is None:
        raise ConfigParseError(
            f"multiType 的 path={path!r}（label={entry['label']!r}）既沒有 searchType 也不在"
            f"已知對應表 {sorted(MULTI_TYPE_PATH_SEARCH_TYPE)} 裡，無法判斷 API type"
        )
    return search_type


def _parse_cell_start(text: str, key: str, default: int) -> int:
    """從 CELL 區塊抽 `queryPage: 20,` / `multiType: 38,` 這類鍵值；找不到就用預設值
    並明顯警告——不是靜默 fallback。"""
    try:
        cell_block = _extract_block(text, "CELL")
    except ConfigParseError:
        logger.warning("config.mjs 找不到 CELL 區塊，%s 起始格號用預設值 %d", key, default)
        return default
    match = re.search(rf"{re.escape(key)}:\s*(\d+)\s*,", cell_block)
    if not match:
        logger.warning("CELL 區塊找不到 `%s` 鍵，起始格號用預設值 %d", key, default)
        return default
    return int(match.group(1))


def parse_legacy_cells(config_text: str) -> list[LegacyCell]:
    """把 config.mjs 全文解析成 20 個 LegacyCell，順序即 cell 順序。"""
    search_perf_block = _extract_block(config_text, "SEARCH_PERFORMANCE")
    query_page_entries = _parse_query_page(search_perf_block)
    multi_type_entries = _parse_multi_type(search_perf_block)

    query_page_start = _parse_cell_start(config_text, "queryPage", 20)
    multi_type_start = _parse_cell_start(config_text, "multiType", 38)

    cells: list[LegacyCell] = []
    for i, entry in enumerate(query_page_entries):
        cells.append(LegacyCell(
            cell=f"G{query_page_start + i}",
            label=entry["label"],
            kind=entry["type"],
            search_type="web",
            dimension=entry["type"],
            pattern=entry["pattern"],
        ))
    for i, entry in enumerate(multi_type_entries):
        cells.append(LegacyCell(
            cell=f"G{multi_type_start + i}",
            label=entry["label"],
            kind="surface",
            search_type=_resolve_multi_type_search_type(entry),
            dimension=None,
            pattern=None,
        ))

    unknown_types = {c.search_type for c in cells} - set(ALLOWED_SEARCH_TYPES)
    if unknown_types:
        raise ConfigParseError(
            f"解析出的 search_type {sorted(unknown_types)} 不在本 repo 已知的 "
            f"{sorted(ALLOWED_SEARCH_TYPES)} 裡——GSC API 可能不支援，需要人工確認"
        )
    return cells


def load_config_text(config_path: Path) -> str:
    if not config_path.exists():
        raise ConfigParseError(
            f"找不到 config.mjs：{config_path}（改用 --config 指定正確路徑）"
        )
    return config_path.read_text(encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════
# 視窗計算
# ══════════════════════════════════════════════════════════════════════

def resolve_window(
    *, start: str | None, end: str | None, days: int, end_offset: int, run_date: date,
) -> tuple[date, date]:
    """--start/--end 需同時給或都不給；都不給則用 run_date - end_offset 當終點，
    往前推 days 天（含終點，與 GSC UI 的『最近 N 天』一致）。"""
    if days < 1:
        raise ValueError(f"--days 必須 >= 1，收到 {days}")
    if bool(start) != bool(end):
        raise ValueError("--start 與 --end 必須同時提供，或都不提供（改用 --days/--end-offset）")
    if start and end:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        if start_date > end_date:
            raise ValueError(f"--start（{start}）晚於 --end（{end}）")
        return start_date, end_date
    end_date = run_date - timedelta(days=end_offset)
    start_date = end_date - timedelta(days=days - 1)
    return start_date, end_date


# ══════════════════════════════════════════════════════════════════════
# Search Analytics API
# ══════════════════════════════════════════════════════════════════════

def build_request_body(cell: LegacyCell, start: date, end: date, *, operator: str = "includingRegex") -> dict[str, Any]:
    body: dict[str, Any] = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "type": cell.search_type,
        "aggregationType": "auto",
    }
    if cell.dimension is not None and cell.pattern is not None:
        body["dimensionFilterGroups"] = [{
            "filters": [{"dimension": cell.dimension, "operator": operator, "expression": cell.pattern}],
        }]
    return body


def extract_clicks(payload: Mapping[str, Any]) -> int:
    """不分組查詢最多回一列（聚合值）；沒有列＝該視窗內這個過濾條件零點擊。"""
    rows = payload.get("rows") or []
    if not rows:
        return 0
    return int(round(float(rows[0].get("clicks", 0))))


def _is_fatal_quota_error(status: int, raw_body: str) -> bool:
    if status != 429:
        return False
    return any(marker in raw_body for marker in FATAL_QUOTA_MARKERS)


def _post_json(url: str, body: Mapping[str, Any], headers: Mapping[str, str], timeout: int) -> tuple[int, str]:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=dict(headers), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")
    except urllib.error.URLError as exc:
        raise LegacyExportError(f"連線失敗：{exc.reason}") from exc


def query_cell(token: str, cell: LegacyCell, start: date, end: date, *, operator: str = "includingRegex") -> int:
    """對單一 cell 打一次 API（含重試），回傳總點擊次數。"""
    url = GSC_QUERY_URL.format(site=urllib.parse.quote(PROPERTY, safe=""))
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    body = build_request_body(cell, start, end, operator=operator)
    label = f"{cell.cell} {cell.label}"
    last_error = ""
    for attempt in range(MAX_ATTEMPTS):
        status, raw = _post_json(url, body, headers, HTTP_TIMEOUT_SECONDS)
        if status == 200:
            return extract_clicks(json.loads(raw))
        last_error = f"HTTP {status}：{raw[:300]}"
        if status in FATAL_HTTP_STATUS or _is_fatal_quota_error(status, raw):
            raise LegacyExportError(f"{label} 呼叫失敗（不可重試）：{last_error}")
        if status not in RETRYABLE_STATUS or attempt == MAX_ATTEMPTS - 1:
            raise LegacyExportError(f"{label} 呼叫失敗：{last_error}")
        wait = RETRY_BACKOFF_SECONDS[attempt]
        logger.warning("%s 回 %s，%.0fs 後重試（第 %d/%d 次）", label, status, wait, attempt + 2, MAX_ATTEMPTS)
        time.sleep(wait)
    raise LegacyExportError(f"{label} 呼叫失敗：{last_error}")


# ══════════════════════════════════════════════════════════════════════
# 輸出
# ══════════════════════════════════════════════════════════════════════

def write_outputs(results: Sequence[ResultRow], out_dir: Path, end: date,
                   controls: Sequence[ResultRow] = ()) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{end.isoformat()}.json"
    csv_path = out_dir / f"{end.isoformat()}.csv"

    payload = {
        "start": results[0].start.isoformat() if results else None,
        "end": end.isoformat(),
        "cells": [r.to_dict() for r in results],
        "controls": [r.to_dict() for r in controls],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in results:
            writer.writerow(row.to_dict())

    return json_path, csv_path


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

def run_export(
    *, cells: Sequence[LegacyCell], start: date, end: date, execute: bool,
    token_provider=gsc_access_token,
) -> list[ResultRow]:
    token = token_provider() if execute else None
    results: list[ResultRow] = []
    for cell in cells:
        clicks: int | None = None
        if execute:
            assert token is not None
            clicks = query_cell(token, cell, start, end)
        row = ResultRow(cell=cell, start=start, end=end, clicks=clicks)
        results.append(row)
        if execute:
            print(f"{cell.cell} {cell.label} {clicks}")
        else:
            print(f"[dry-run] {cell.cell} {cell.label} type={cell.search_type} "
                  f"dimension={cell.dimension} pattern={cell.pattern}")
    return results


def run_equals_control(
    *, cells: Sequence[LegacyCell], labels: Sequence[str], start: date, end: date,
    token_provider=gsc_access_token,
) -> list[ResultRow]:
    """對指定 label（例如「保養」）額外打一次 `operator: equals` 當對照組，
    判讀 includingRegex 在介面與 API 之間的口徑是否一致。不進 20 格的 JSON/CSV
    主體，只進 `controls`。"""
    wanted = set(labels)
    matched = [c for c in cells if c.label in wanted and c.dimension is not None]
    missing = wanted - {c.label for c in matched}
    if missing:
        raise ValueError(f"--equals-control 指定的 label 在 20 格裡找不到或不是 page/query 類：{sorted(missing)}")
    token = token_provider()
    controls: list[ResultRow] = []
    for cell in matched:
        clicks = query_cell(token, cell, start, end, operator="equals")
        row = ResultRow(cell=cell, start=start, end=end, clicks=clicks, operator="equals")
        controls.append(row)
        print(f"[control:equals] {cell.cell} {cell.label} {clicks}")
    return controls


def main() -> None:
    parser = argparse.ArgumentParser(
        description="舊爬蟲 20 格等價匯出：用 Search Analytics API 產出與舊爬蟲讀 GSC 介面卡片相同的 20 個總點擊次數"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH,
                        help=f"seo-automation/config.mjs 路徑（預設 {DEFAULT_CONFIG_PATH}）")
    parser.add_argument("--start", default=None, help="視窗起點 YYYY-MM-DD（需與 --end 同時給）")
    parser.add_argument("--end", default=None, help="視窗終點 YYYY-MM-DD（需與 --start 同時給）")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        help=f"視窗天數（預設 {DEFAULT_DAYS}，與 --start/--end 二擇一）")
    parser.add_argument("--end-offset", type=int, default=DEFAULT_END_OFFSET,
                        help=f"視窗終點 = 今天 - N 天（預設 {DEFAULT_END_OFFSET}）")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                        help=f"輸出目錄（預設 {DEFAULT_OUT_DIR}）")
    parser.add_argument("--execute", action="store_true",
                        help="實際打 API 並寫出 JSON/CSV；不給則只印計畫（dry-run，預設）")
    parser.add_argument("--equals-control", default=None,
                        help="逗號分隔的 label 清單，額外用 operator=equals 打一次當對照組"
                             "（需搭配 --execute；例如 --equals-control 保養）")
    args = parser.parse_args()

    try:
        config_text = load_config_text(args.config)
        cells = parse_legacy_cells(config_text)
        start, end = resolve_window(
            start=args.start, end=args.end, days=args.days,
            end_offset=args.end_offset, run_date=date.today(),
        )
    except (ConfigParseError, ValueError) as exc:
        logger.error("%s", exc)
        sys.exit(2)

    logger.info("視窗 %s ~ %s（%d 格：15 queryPage + 5 multiType），property=%s",
                start.isoformat(), end.isoformat(), len(cells), PROPERTY)
    if not args.execute:
        logger.info("預設為 dry-run，只印計畫；加 --execute 才會打 API 並寫出 JSON/CSV。")

    try:
        results = run_export(cells=cells, start=start, end=end, execute=args.execute)
        controls: list[ResultRow] = []
        if args.execute and args.equals_control:
            labels = [s.strip() for s in args.equals_control.split(",") if s.strip()]
            controls = run_equals_control(cells=cells, labels=labels, start=start, end=end)
    except LegacyExportError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    if args.execute:
        json_path, csv_path = write_outputs(results, args.out_dir, end, controls=controls)
        logger.info("已寫出 %s、%s", json_path, csv_path)

    sys.exit(0)


if __name__ == "__main__":
    main()
