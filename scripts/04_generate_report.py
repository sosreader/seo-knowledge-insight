"""
步驟 4：依據每週 SEO 指標 + Q&A 知識庫，產生分析報告

使用方式：
    # 直接串 Google Sheets URL（最簡）：
    python scripts/04_generate_report.py --input "https://docs.google.com/spreadsheets/d/..."

    # 指定分頁（預設取 vocus）：
    python scripts/04_generate_report.py --input "https://..." --tab vocus

    # 從本機檔案讀（手動從試算表複製存檔用）：
    python scripts/04_generate_report.py --input metrics.tsv

    # 輸出到指定路徑：
    python scripts/04_generate_report.py --input "https://..." --output report.md
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
import csv
import io
import urllib.error
import urllib.request
from urllib.parse import urlparse

import numpy as np

logger = logging.getLogger(__name__)

# ── 路徑修正 ─────────────────────────────────────────
try:
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

from utils.openai_helper import get_embeddings
from utils.pipeline_deps import preflight_check, StepDependency
from utils.observability import init_laminar, flush_laminar, observe
from utils.search_engine import compute_keyword_boost
from utils.pipeline_cache import cache_get, cache_set
from utils.pipeline_version import record_artifact, get_latest_version

from openai import OpenAI

from utils.metrics_parser import (
    DEFAULT_SHEETS_URL,
    ALERT_THRESHOLD_MONTHLY,
    ALERT_THRESHOLD_WEEKLY,
    CORE_METRICS,
    SKIP_METRICS,
    METRIC_QUERY_MAP,
)

# 注意：ALERT_THRESHOLD_MONTHLY / ALERT_THRESHOLD_WEEKLY / CORE_METRICS /
#       SKIP_METRICS / METRIC_QUERY_MAP 常數來自 utils/metrics_parser.py
#       fetch_from_sheets / parse_metrics_tsv / detect_anomalies 在本檔案本地定義
#       （含有本地 helper 函式：_parse_sheets_url、_validate_sheet_id 等）



# ──────────────────────────────────────────────────────
# Google Sheets 自動擷取
# ──────────────────────────────────────────────────────

_SHEET_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{10,60}$")
_GID_RE = re.compile(r"^\d{1,10}$")
_MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB 上限
_ALLOWED_HOST = "docs.google.com"


def _validate_sheet_id(sheet_id: str) -> None:
    """驗證 sheet_id 格式，防止注入攻擊。"""
    if not _SHEET_ID_RE.match(sheet_id):
        raise ValueError(f"sheet_id 格式不合法：{sheet_id!r}")


def _validate_gid(gid: str) -> None:
    """驗證 gid 為純數字，防止注入攻擊。"""
    if not _GID_RE.match(gid):
        raise ValueError(f"gid 格式不合法：{gid!r}")


def _parse_sheets_url(url: str) -> tuple[str, str]:
    """從 Google Sheets URL 解析 sheet_id 與 gid"""
    parsed = urlparse(url)
    if parsed.netloc != _ALLOWED_HOST:
        raise ValueError(f"不允許的 Sheets 主機：{parsed.netloc!r}，僅允許 {_ALLOWED_HOST!r}")
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not m:
        raise ValueError(f"無法從 URL 解析 sheet ID：{url}")
    sheet_id = m.group(1)
    _validate_sheet_id(sheet_id)
    gid_match = re.search(r"[?&#]gid=([0-9]+)", url)
    gid = gid_match.group(1) if gid_match else "0"
    _validate_gid(gid)
    return sheet_id, gid


def _find_gid_by_tab_name(sheet_id: str, tab: str) -> str | None:
    """在 Sheets HTML 裡找 tab 名稱對應的 gid（不需 OAuth）"""
    _validate_sheet_id(sheet_id)
    try:
        url = f"https://{_ALLOWED_HOST}/spreadsheets/d/{sheet_id}/edit"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return None
            html = resp.read(_MAX_RESPONSE_BYTES).decode("utf-8", errors="ignore")
        # 格式："sheetId":123456,"title":"vocus"
        m = re.search(
            r'"sheetId":(\d+)[^}]*"title":"' + re.escape(tab) + r'"',
            html,
        )
        if m:
            gid = m.group(1)
            _validate_gid(gid)
            return gid
        # 備案：title 在前
        m2 = re.search(
            r'"title":"' + re.escape(tab) + r'"[^}]*"sheetId":(\d+)',
            html,
        )
        if m2:
            gid = m2.group(1)
            _validate_gid(gid)
            return gid
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
        logger.warning("_find_gid_by_tab_name 失敗，tab=%r，err=%s", tab, e)
    return None


def fetch_from_sheets(url_or_id: str, tab: str = "vocus") -> str:
    """
    從 Google Sheets 下載指定分頁的 CSV 並轉為 TSV 字串。
    試算表須設為「任何知道連結者可檢視」。
    """
    if url_or_id.startswith("http"):
        sheet_id, url_gid = _parse_sheets_url(url_or_id)
        # URL 已含非預設 gid → 直接用；否則依 tab 名稱查
        if url_gid != "0":
            gid = url_gid
        else:
            gid = _find_gid_by_tab_name(sheet_id, tab) or "0"
    else:
        _validate_sheet_id(url_or_id)
        sheet_id = url_or_id
        gid = _find_gid_by_tab_name(sheet_id, tab) or "0"

    _validate_gid(gid)
    csv_url = (
        f"https://{_ALLOWED_HOST}/spreadsheets/d/{sheet_id}"
        f"/export?format=csv&id={sheet_id}&gid={gid}"
    )
    logger.info("下載: %s", csv_url)
    req = urllib.request.Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status != 200:
            raise ValueError(f"Google Sheets 回應異常，HTTP 狀態碼：{resp.status}")
        raw = resp.read(_MAX_RESPONSE_BYTES)
    # Sheets CSV 為 UTF-8-BOM
    text = raw.decode("utf-8-sig")

    # CSV → TSV：使用 csv 模組正確處理含逗號的數值（如 "1,234,567"）
    reader = csv.reader(io.StringIO(text))
    lines = ["\t".join(row) for row in reader]
    return "\n".join(lines)


# ──────────────────────────────────────────────────────
# TSV 解析
# ──────────────────────────────────────────────────────

def _parse_value(raw: str) -> float | str | None:
    """把試算表格子的原始字串轉成數值 / None"""
    v = raw.strip()
    if v in ("#N/A", "#DIV/0!", "#REF!", "#VALUE!", ""):
        return None
    # 百分比
    if v.endswith("%"):
        try:
            return float(v.rstrip("%")) / 100
        except ValueError:
            return None
    # 數字（可能含逗號）
    try:
        return float(v.replace(",", ""))
    except ValueError:
        return v  # 保留原始字串（如日期）


def parse_metrics_tsv(text: str) -> dict[str, dict]:
    """
    解析從 Google 試算表複製的 TSV。

    期望格式（第一行為 header，之後每行 metric_name + 數值）：
        （空）\t月趨勢\t上週\tMax\tMin\tSparklines\t日期1\t日期2
        曝光\t-3.61%\t-26.09%\t65,358,724\t48,305,965\t\t48,305,965\t65,358,724

    回傳 dict： metric_name → {monthly, weekly, max, min, latest, previous, latest_date, previous_date}
    """
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return {}

    # 找 header 行（包含「月趨勢」或「上週」）
    header_idx = 0
    for i, line in enumerate(lines):
        if "月趨勢" in line or "上週" in line:
            header_idx = i
            break

    header_cols = lines[header_idx].split("\t")
    # 找日期欄（通常是 col 5, 6，即 header_cols[5], header_cols[6]）
    date_cols = [c.strip() for c in header_cols if re.match(r"\d+/\d+/\d+", c.strip())]
    latest_date = date_cols[0] if date_cols else ""
    previous_date = date_cols[1] if len(date_cols) > 1 else ""

    def _safe_col(cols: list[str], idx: int):
        return _parse_value(cols[idx]) if idx < len(cols) else None

    metrics: dict[str, dict] = {}
    for line in lines[header_idx + 1:]:
        cols = line.split("\t")
        if not cols or not cols[0].strip():
            continue
        name = cols[0].strip()
        if name in SKIP_METRICS:
            continue

        metrics[name] = {
            "monthly":      _safe_col(cols, 1),
            "weekly":       _safe_col(cols, 2),
            "max":          _safe_col(cols, 3),
            "min":          _safe_col(cols, 4),
            "latest":       _safe_col(cols, 6) if len(cols) > 6 else None,
            "previous":     _safe_col(cols, 7) if len(cols) > 7 else None,
            "latest_date":  latest_date,
            "previous_date": previous_date,
        }

    return metrics


# ──────────────────────────────────────────────────────
# 異常偵測
# ──────────────────────────────────────────────────────

def detect_anomalies(metrics: dict[str, dict]) -> list[dict]:
    """
    找出需要關注的指標，分為：
    - CORE：核心指標（不管趨勢都納入）
    - ALERT_UP / ALERT_DOWN：月趨勢或週趨勢超過閾值
    """
    alerts = []

    for name, m in metrics.items():
        monthly = m.get("monthly")
        weekly = m.get("weekly")

        # 核心指標：一定加入
        if name in CORE_METRICS:
            alerts.append({**m, "name": name, "flag": "CORE"})
            continue

        # 趨勢異常
        monthly_abs = abs(monthly) if isinstance(monthly, float) else 0
        weekly_abs = abs(weekly) if isinstance(weekly, float) else 0

        if monthly_abs >= ALERT_THRESHOLD_MONTHLY or weekly_abs >= ALERT_THRESHOLD_WEEKLY:
            flag = "ALERT_UP" if (monthly or 0) > 0 else "ALERT_DOWN"
            alerts.append({**m, "name": name, "flag": flag})

    return alerts


# ──────────────────────────────────────────────────────
# Q&A 語意搜尋
# ──────────────────────────────────────────────────────

def _load_qa_database() -> list[dict]:
    """優先讀最終版，否則用原始版"""
    final = config.OUTPUT_DIR / "qa_final.json"
    raw = config.OUTPUT_DIR / "qa_all_raw.json"

    if final.exists():
        data = json.loads(final.read_text(encoding="utf-8"))
        qas = data.get("qa_database", [])
        # 若只跑了測試批次（<50），改用原始版
        if len(qas) >= 50:
            return qas

    if raw.exists():
        data = json.loads(raw.read_text(encoding="utf-8"))
        return data.get("qa_pairs", [])

    return []


def _load_persisted_embeddings(qa_count: int) -> np.ndarray | None:
    """載入 Step 3 持久化的 embedding，若不存在或數量不匹配則回傳 None。"""
    emb_path = config.OUTPUT_DIR / "qa_embeddings.npy"
    if not emb_path.exists():
        return None
    emb = np.load(emb_path)
    if emb.shape[0] != qa_count:
        logger.warning("Embedding 數量 (%d) 與 Q&A 數量 (%d) 不匹配，重新計算", emb.shape[0], qa_count)
        return None
    return emb


# _compute_keyword_boost 已移至 utils/search_engine.py 作為模組級函式。
# 以 _compute_keyword_boost 作為 shim，維持內部呼叫點不變。
def _compute_keyword_boost(
    queries: list[str],
    qa_pairs: list[dict],
    boost: float | None = None,
    max_hits: int | None = None,
) -> np.ndarray:
    """Thin wrapper → delegates to compute_keyword_boost in utils/search_engine."""
    return compute_keyword_boost(queries, qa_pairs, boost=boost, max_hits=max_hits)


@observe(name="find_relevant_qas_multi")
def find_relevant_qas_multi(
    queries: list[str],
    qa_pairs: list[dict],
    top_k_per_query: int = 3,
    total_max: int = 15,
    min_score: float = 0.28,
) -> list[dict]:
    """
    多查詢版（Hybrid Search）：針對每個異常指標分別做 embedding 搜尋，
    並結合關鍵字精確匹配 boost，取各查詢 top_k 結果後合併去重。
    回傳的每筆 Q&A 帶有 `_queries` 欄位，記錄哪些查詢命中了它。
    """
    if not qa_pairs or not queries:
        return []

    # 嘗試載入持久化 embedding（避免重算）
    persisted_embs = _load_persisted_embeddings(len(qa_pairs))
    if persisted_embs is not None:
        logger.info("   ✨ 使用持久化 embedding（免重算）")
        # 只需 embed queries
        query_embeddings = get_embeddings(queries)
        query_embs = np.array(query_embeddings)
        qa_embs = persisted_embs
    else:
        # Fallback: 一次批次 embed 所有 queries + 所有 QA 問題
        questions = [qa.get("question", "") for qa in qa_pairs]
        all_texts = queries + questions
        all_embeddings = get_embeddings(all_texts)
        query_embs = np.array(all_embeddings[: len(queries)])
        qa_embs = np.array(all_embeddings[len(queries) :])

    qa_norm = qa_embs / (np.linalg.norm(qa_embs, axis=1, keepdims=True) + 1e-8)
    q_norm = query_embs / (np.linalg.norm(query_embs, axis=1, keepdims=True) + 1e-8)
    # 語意相似度矩陣
    score_matrix = q_norm @ qa_norm.T  # (n_queries, n_qa)

    # Hybrid: 加上關鍵字 boost
    keyword_boost = _compute_keyword_boost(queries, qa_pairs)
    score_matrix = score_matrix + keyword_boost

    # 收集每個 query 的 top-k
    collected: dict[int, dict] = {}  # qa_index -> 結果 dict
    for qi, query in enumerate(queries):
        scores = score_matrix[qi]
        top_indices = np.argsort(scores)[::-1][:top_k_per_query]
        for idx in top_indices:
            if scores[idx] < min_score:
                continue
            if idx not in collected:
                collected[idx] = {
                    **qa_pairs[idx],
                    "_score": float(scores[idx]),
                    "_queries": [query],
                }
            else:
                # 同一 Q&A 被多個 query 命中 → 更新最高分 + 累積 queries
                if scores[idx] > collected[idx]["_score"]:
                    collected[idx]["_score"] = float(scores[idx])
                collected[idx]["_queries"].append(query)

    # 依最高分排序，取前 total_max
    results = sorted(collected.values(), key=lambda x: -x["_score"])
    return results[:total_max]


@observe(name="_rerank_qas")
def _rerank_qas(
    candidates: list[dict],
    context_summary: str,
    top_k: int,
) -> list[dict]:
    """
    LLM Reranker：用 gpt-5-mini 從候選 Q&A 中選出對當週指標摘要最有幫助的 top_k 筆。
    以結構化輸出回傳排序後的 index 陣列，失敗時 fallback 回原有排序。
    """
    if len(candidates) <= top_k:
        return candidates  # 候選數量不足，不須 rerank

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    # 建立候選清單（截短 answer 節省 token）
    numbered = []
    for i, qa in enumerate(candidates):
        ans_snippet = (qa.get("answer") or "")[:200].replace("\n", " ")
        numbered.append(f"[{i}] Q: {qa['question']}\n    A（節錄）: {ans_snippet}")
    candidates_text = "\n\n".join(numbered)

    # 截短 context 避免 token 過多
    ctx = context_summary[:600] if len(context_summary) > 600 else context_summary

    prompt = (
        f"本週 SEO 指標摘要：\n{ctx}\n\n"
        f"以下是 {len(candidates)} 筆候選 Q&A（編號 0–{len(candidates)-1}）：\n\n"
        f"{candidates_text}\n\n"
        f"請從中選出對解讀本週指標最有直接幫助的 {top_k} 筆，"
        f"以重要性遞減順序回傳 index 陣列（JSON），例如 {{\"ranked\": [3, 0, 5, ...]}}。"
        "只回傳 JSON，不要說明。"
    )

    try:
        resp = client.chat.completions.create(
            model=config.EVAL_JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=256,
        )
        raw = resp.choices[0].message.content or "{}"
        ranked_indices: list[int] = json.loads(raw).get("ranked", [])
        # 過濾合法 index，補足 top_k
        valid = [i for i in ranked_indices if isinstance(i, int) and 0 <= i < len(candidates)]
        # 補入未被選中的（按原分數順序），確保回傳剛好 top_k 筆
        seen = set(valid)
        for i in range(len(candidates)):
            if i not in seen:
                valid.append(i)
        reranked = [candidates[i] for i in valid[:top_k]]
        logger.info(f"   🎯 Reranker 完成：{len(candidates)} → {len(reranked)} 筆")
        return reranked
    except Exception as e:
        logger.warning(f"   ⚠️  Reranker 失敗（{e}），使用原始排序")
        return candidates[:top_k]


# ──────────────────────────────────────────────────────
# 格式化輔助
# ──────────────────────────────────────────────────────

def _fmt_pct(v) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        sign = "+" if v > 0 else ""
        return f"{sign}{v*100:.1f}%"
    return str(v)


def _fmt_num(v) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        if v >= 1_000_000:
            return f"{v/1_000_000:.2f}M"
        if v >= 1_000:
            return f"{v:,.0f}"
        # 判斷是比例還是數值
        if abs(v) <= 5:
            return f"{v:.4f}"
        return f"{v:.1f}"
    return str(v)


def _build_metrics_summary(alerts: list[dict]) -> str:
    """把關注指標整理成文字摘要，供 LLM 閱讀"""
    lines = []

    core = [a for a in alerts if a["flag"] == "CORE"]
    alert_down = [a for a in alerts if a["flag"] == "ALERT_DOWN"]
    alert_up = [a for a in alerts if a["flag"] == "ALERT_UP"]

    if core:
        lines.append("【核心指標】")
        for m in core:
            lines.append(
                f"  {m['name']}: 最新 {_fmt_num(m['latest'])} | "
                f"月趨勢 {_fmt_pct(m['monthly'])} | 週趨勢 {_fmt_pct(m['weekly'])}"
            )

    if alert_down:
        lines.append("\n【顯著下滑（月趨勢）】")
        for m in sorted(alert_down, key=lambda x: (x.get("monthly") or 0)):
            lines.append(
                f"  {m['name']}: {_fmt_pct(m['monthly'])} (月) / {_fmt_pct(m['weekly'])} (週)"
            )

    if alert_up:
        lines.append("\n【顯著上升（月趨勢）】")
        for m in sorted(alert_up, key=lambda x: -(x.get("monthly") or 0)):
            lines.append(
                f"  {m['name']}: {_fmt_pct(m['monthly'])} (月) / {_fmt_pct(m['weekly'])} (週)"
            )

    return "\n".join(lines)


# ──────────────────────────────────────────────────────
# LLM 報告產生
# ──────────────────────────────────────────────────────

REPORT_SYSTEM_PROMPT = """\
你是資深 SEO 分析師，任務是把本週的指標變化「翻譯成意義」，並用過去顧問會議累積的 Q&A 知識庫作為佐證。

重要原則：
- 用戶可以直接看 Google Sheets，**不需要你重複數字**。
- 每一個觀察必須說明「這代表什麼」「為什麼發生」「應該怎麼做」。
- 每個 insight 都應盡量引用【Q&A 知識庫】的具體內容作為依據，格式：（參考：「{Q&A 的關鍵句}」）
- 如果知識庫沒有直接對應，請根據 SEO 原理推論，並標明「（推論）」。
- 避免泛泛的 SEO 建議；結合本週資料的具體變化給出針對性意見。
- 引用知識庫時，請同時標註原始會議來源（標題+日期）。若來源附有 Notion 連結，保留 Markdown 超連結格式，方便讀者一鍵回到原始頁面。

報告格式（Markdown，用繁體中文，技術術語保留英文）：

## 本週核心訊號
（3-4 點，每點說明一個重要的「現象 → 意義 → 知識庫怎麼說」，不提數字）

## 異常指標解讀
（針對顯著上升 / 下滑的指標，逐一解釋可能的因果機制，重點引用知識庫）

## 本週行動清單
（3 條具體 Todo，每條注明依據是哪個 Q&A 的建議或觀察）

## 直接引用知識庫
（原文引用 1-2 個本週最相關的 Q&A 問答，格式：**Q**：… / **A（節錄）**：… / **來源**：…）
"""


@observe(name="generate_report")
def generate_report(metrics_summary: str, relevant_qas: list[dict], metrics_date: str) -> str:
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    # ─ Meta 前置（動態取出 KB 大小）─
    _qa_path = config.OUTPUT_DIR / "qa_final.json"
    _total_qa = 0
    try:
        with open(_qa_path, encoding="utf-8") as _f:
            _total_qa = len(json.load(_f))
    except Exception as e:
        logger.warning("無法讀取 qa_final.json 以取得 KB 大小：%s", e)
    _kb_label = f"{_total_qa} Q&A" if _total_qa else "知識庫"
    meta_block = f"""---
**Meta 資訊**
- **生成方式**：Claude Code 本地推理（不需要 OpenAI API）
- **知識庫支撐**：{_kb_label}（來自過去 SEO 顧問會議記錄）
- **生成日期**：{metrics_date}
- **特性**：零捏造數字、知識庫驗證、具體行動步驟

---
"""

    # 知識庫：讓每條 Q&A 盡量完整，並標示被哪些指標查詢命中（幫助 LLM 知道關聯性）
    qa_context = ""
    if relevant_qas:
        qa_context = "\n\n【Q&A 知識庫（來自歷次 SEO 顧問會議記錄）】\n"
        qa_context += "（以下知識由指標異常查詢匹配，括號內是觸發此 Q&A 的指標信號）\n"
        for i, qa in enumerate(relevant_qas[:12], 1):
            triggered = "、".join(qa.get("_queries", [])[:3])
            snippet = qa["answer"][:600] + ("..." if len(qa["answer"]) > 600 else "")
            # 溯源資訊：讓報告讀者可以追溯到原始會議
            source_title = qa.get("source_title", "")
            source_date = qa.get("source_date", "")
            notion_url = qa.get("_enrichment", {}).get("notion_url", "")
            source_info = ""
            if source_title or source_date:
                source_text = "、".join(p for p in [source_title, source_date] if p)
                if notion_url:
                    source_info = f"來源：[{source_text}]({notion_url})\n"
                else:
                    source_info = f"來源：{source_text}\n"
            qa_context += (
                f"\n[{i}] 觸發信號：{triggered}\n"
                f"{source_info}"
                f"Q: {qa['question']}\n"
                f"A: {snippet}\n"
            )

    user_msg = (
        f"報告日期：{metrics_date}\n\n"
        "【本週指標摘要】（數字僅供 LLM 判斷方向，報告中請勿重複羅列）\n"
        f"{metrics_summary}"
        f"{qa_context}"
    )

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        max_completion_tokens=16384,  # gpt-5 推理模型：reasoning + output 共享，需預留足夠空間
    )

    msg = response.choices[0].message
    content = msg.content

    # gpt-5 系列可能將內容放在 reasoning_content（thinking output）
    if not content:
        reasoning = getattr(msg, "reasoning_content", None)
        if reasoning:
            logger.warning(f"   ⚠️  content 為空，嘗試使用 reasoning_content（{len(reasoning)} chars）")
            content = reasoning
        else:
            logger.error(f"   ❌ finish_reason={response.choices[0].finish_reason}")
            logger.error(f"   ❌ refusal={getattr(msg, 'refusal', None)}")
            logger.error(f"   ❌ msg fields: {getattr(msg, 'model_fields_set', None)}")

    # 將 meta_block 加入報告開頭
    full_report = meta_block + (content or "（報告產生失敗）")
    
    # ─ Laminar metadata 記錄 ─
    try:
        from lmnr import current_span
        span = current_span()
        if span:
            span.set_metadata({
                "step": "generate_report",
                "execution_mode": "openai_api",
                "knowledge_base_size": _total_qa,
                "generation_timestamp": metrics_date,
                "character_count": len(full_report),
                "qa_used_count": len(relevant_qas),
            })
    except Exception:
        pass  # Laminar not available or span not in context
    
    return full_report


# ──────────────────────────────────────────────────────
# 主程式
# ──────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="產生每週 SEO 分析報告")
    parser.add_argument(
        "--input", "-i",
        type=str,
        default=None,
        help="Google Sheets URL 或本機 TSV 路徑。不指定則用 config.SHEETS_URL 或預設 URL。",
    )
    parser.add_argument(
        "--tab",
        type=str,
        default="vocus",
        help="Google Sheets 分頁名稱（預設: vocus）",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="輸出 Markdown 報告路徑。預設：output/report_YYYYMMDD.md",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=15,
        help="從知識庫最多取幾個相關 Q&A（預設 15）",
    )
    parser.add_argument(
        "--no-qa",
        action="store_true",
        help="不使用 Q&A 知識庫（單純分析指標）",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只檢查依賴是否就緒，不實際執行",
    )
    args = parser.parse_args()

    init_laminar()

    # ── Preflight dependency check ───────────────────────────
    deps = []
    if not args.no_qa:
        deps = [
            StepDependency(
                path=config.OUTPUT_DIR / "qa_final.json",
                required=False,
                max_age_days=7,
                hint="請先執行 python scripts/03_dedupe_classify.py（或用 --no-qa 略過）",
            ),
            StepDependency(
                path=config.OUTPUT_DIR / "qa_embeddings.npy",
                required=False,
                max_age_days=7,
            ),
        ]
    preflight_check(
        deps=deps,
        env_keys=["OPENAI_API_KEY"],
        step_name="Step 4: 週報生成",
        check_only=args.check,
    )
    if args.check:
        return

    logger.info("=" * 60)
    logger.info("📊 SEO 週報產生器")
    logger.info("=" * 60)

    # 決定資料來源（優先順序：--input > .env SHEETS_URL > 預設 URL）
    source = args.input or getattr(config, "SHEETS_URL", "") or DEFAULT_SHEETS_URL

    if source.startswith("http"):
        logger.info(f"\n📥 從 Google Sheets 擷取（tab: {args.tab}）...")
        try:
            tsv_text = fetch_from_sheets(source, tab=args.tab)
        except Exception as e:
            logger.error(f"❌ 下載失敗：{e}")
            logger.info("💡 請確認該試算表權限為「任何知道連結者可檢視」")
            sys.exit(1)
    elif source:
        tsv_text = Path(source).read_text(encoding="utf-8")
    else:
        logger.info("📋 請貼上試算表資料（完成後按 Ctrl+D）：")
        tsv_text = sys.stdin.read()

    if not tsv_text.strip():
        logger.error("❌ 沒有收到資料")
        sys.exit(1)

    # 解析
    logger.info("\n🔍 解析指標資料 ...")
    metrics = parse_metrics_tsv(tsv_text)
    if not metrics:
        logger.error("❌ 無法解析指標，請確認格式是從 Google 試算表直接複製的 TSV")
        sys.exit(1)
    logger.info(f"   解析到 {len(metrics)} 個指標")

    # 異常偵測
    alerts = detect_anomalies(metrics)
    alert_down = [a for a in alerts if a["flag"] == "ALERT_DOWN"]
    alert_up = [a for a in alerts if a["flag"] == "ALERT_UP"]
    logger.info(f"   核心指標: {len([a for a in alerts if a['flag']=='CORE'])} 個")
    logger.info(f"   顯著下滑: {len(alert_down)} 個 | 顯著上升: {len(alert_up)} 個")

    metrics_summary = _build_metrics_summary(alerts)

    # 語意搜尋相關 Q&A（多查詢策略：每個異常指標獨立查詢）
    relevant_qas = []
    if not args.no_qa:
        logger.info("\n🔎 搜尋相關 Q&A 知識庫 ...")
        qa_pairs = _load_qa_database()
        if qa_pairs:
            logger.info(f"   知識庫共 {len(qa_pairs)} 個 Q&A")
            # 為每個需要解釋的指標建立語意查詢
            queries: list[str] = []
            seen: set[str] = set()

            def _add_query(q: str) -> None:
                if q not in seen:
                    seen.add(q)
                    queries.append(q)

            for a in alerts:
                name = a["name"]
                monthly = a.get("monthly") or 0
                weekly = a.get("weekly") or 0
                direction = "下降" if (monthly < 0 or weekly < 0) else "上升"

                # 優先使用 METRIC_QUERY_MAP 的精確查詢
                if name in METRIC_QUERY_MAP:
                    for q in METRIC_QUERY_MAP[name]:
                        _add_query(q)
                else:
                    # 通用退回模板
                    if a["flag"] == "CORE":
                        _add_query(f"{name} {direction} 代表什麼 SEO 含義")
                    elif a["flag"] == "ALERT_DOWN":
                        _add_query(f"{name} 大幅下降 原因 怎麼處理")
                    elif a["flag"] == "ALERT_UP":
                        _add_query(f"{name} 大幅上升 代表什麼 注意事項")

            # 固定補充：確保核心知識庫場景必然覆蓋
            for q in [
                "CTR 持續下降 搜尋結果外觀 如何改善",
                "檢索未索引增加 WAF 封鎖 Googlebot",
                "Discover 流量波動 探索演算法",
                "AMP Article 流量下降 焦點新聞",
                "伺服器回應時間 爬蟲抓取 索引影響",
            ]:
                _add_query(q)

            # 先取較大的候選池（top_k 的 2 倍，最多 30），再用 LLM Reranker 精選
            candidate_pool = max(args.top_k * 2, 20)
            candidates = find_relevant_qas_multi(
                queries, qa_pairs,
                top_k_per_query=3,
                total_max=candidate_pool,
            )
            logger.info(f"   使用 {len(queries)} 個查詢，候選 {len(candidates)} 個 Q&A")
            relevant_qas = _rerank_qas(candidates, metrics_summary, args.top_k)
            logger.info(f"   使用 {len(queries)} 個查詢，找到 {len(relevant_qas)} 個相關 Q&A（已 Rerank）")
        else:
            logger.warning("   ⚠️  找不到 Q&A 知識庫，跳過（先執行步驟 2-3 建立知識庫）")

    # 取得日期，標準化為 YYYYMMDD
    sample_metric = next((m for m in metrics.values() if m.get("latest_date")), {})
    raw_date = sample_metric.get("latest_date", "")
    try:
        # 解析 M/D/YYYY → YYYYMMDD
        dt = datetime.strptime(raw_date, "%m/%d/%Y")
        date_str = dt.strftime("%Y%m%d")
        report_date = dt.strftime("%Y/%m/%d")
    except ValueError:
        date_str = datetime.today().strftime("%Y%m%d")
        report_date = raw_date or datetime.today().strftime("%Y/%m/%d")

    # 產生報告
    logger.info(f"\n✍️  產生報告（日期：{report_date}）...")

    # ── Layer 1: Report cache ───────────────────────────────
    # Key = metrics_summary + qa 版本 ID
    qa_ver = get_latest_version(3)
    qa_version_id = qa_ver["version_id"] if qa_ver else "no-qa"
    report_cache_key = f"{metrics_summary}\n---QA_VER={qa_version_id}---"
    cached_report = cache_get("report", report_cache_key)
    if cached_report is not None:
        report_md = cached_report["report_text"]
        logger.info("   [cache hit] 直接使用緩存報告")
    else:
        report_md = generate_report(metrics_summary, relevant_qas, report_date)
        cache_set("report", report_cache_key, {"report_text": report_md})

    # 輸出
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = config.OUTPUT_DIR / f"report_{date_str}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_md, encoding="utf-8")

    # ── Layer 2: Version Registry ──────────────────────────────
    version_entry = record_artifact(
        step=4,
        data={"report_text": report_md, "date": date_str},
        metadata={"report_date": report_date, "output_path": str(out_path)},
    )
    logger.info(f"   🔖 版本記録: {version_entry['version_id']}")

    logger.info("\n" + "=" * 60)
    logger.info("✅ 報告完成！")
    logger.info(f"   📄 {out_path}")
    logger.info("=" * 60)

    # 直接印到 console
    logger.info("\n" + "─" * 60)
    logger.info(report_md)

    flush_laminar()


if __name__ == "__main__":
    main()
