"""
稽核日誌模組 — 記錄所有資料存取與 Notion Fetch 操作

設計原則：
- 不可變 — 只追加，不修改既有日誌
- 零副作用 — 日誌失敗不影響業務邏輯（靜默失敗，僅 logging.warning）
- JSONL 格式 — 每行一筆，方便 grep / jq / 程式解析
- 分類兩種日誌：
  - fetch_logs/   Notion fetch 操作記錄（誰抓了哪些頁面）
  - access_logs/  API 查詢記錄（哪些 QA 被讀取）

目錄結構：
  output/
    fetch_logs/
      fetch_2026-02-28.jsonl    # 每天一個檔案
    access_logs/
      access_2026-02-28.jsonl   # 每天一個檔案

Event Schema（fetch_logs）：
  {
    "event": "fetch_start|fetch_page|fetch_complete|fetch_skip",
    "session_id": "uuid4",
    "ts": "2026-02-28T10:00:00.000Z",
    "mode": "incremental|force|since",
    "since_time": "...",  // 若有
    "page_id": "...",
    "page_title": "...",
    "last_edited_time": "...",
    "block_count": 12,
    "skipped_reason": "no_change"  // 若 skip
  }

Event Schema（access_logs）：
  {
    "event": "search|chat|list_qa",
    "ts": "2026-02-28T10:00:00.000Z",
    "query": "...",
    "top_k": 5,
    "returned_ids": [1, 23, 45],      // QA IDs
    "source_titles": ["SEO 會議_2023/10/04", ...],
    "ip": "...",
    "session_id": "..."  // 若有
  }
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── 路徑 ─────────────────────────────────────────────
# 支援從 config 載入或使用預設值（避免循環 import）
try:
    import config as _root_config
    _OUTPUT_DIR = _root_config.OUTPUT_DIR
except (ImportError, AttributeError):
    _OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

FETCH_LOGS_DIR = _OUTPUT_DIR / "fetch_logs"
ACCESS_LOGS_DIR = _OUTPUT_DIR / "access_logs"


# ── 內部工具 ──────────────────────────────────────────

def _now_iso() -> str:
    """回傳 UTC ISO 時間戳 2026-02-28T10:00:00.000Z"""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _today_str() -> str:
    """回傳今天日期字串 2026-02-28（UTC）"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """追加一行 JSON 到 JSONL 檔案，失敗時 warning 靜默不拋出"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.warning("audit_logger: 寫入日誌失敗 %s — %s", path, exc)


def _fetch_log_path() -> Path:
    return FETCH_LOGS_DIR / f"fetch_{_today_str()}.jsonl"


def _access_log_path() -> Path:
    return ACCESS_LOGS_DIR / f"access_{_today_str()}.jsonl"


# ── Fetch 事件 ────────────────────────────────────────

def log_fetch_start(
    session_id: str,
    mode: str,
    total_pages: int,
    since_time: str | None,
    block_max_depth: int,
) -> None:
    """記錄 fetch 開始"""
    _append_jsonl(_fetch_log_path(), {
        "event": "fetch_start",
        "session_id": session_id,
        "ts": _now_iso(),
        "mode": mode,
        "total_pages_listed": total_pages,
        "since_time": since_time,
        "block_max_depth": block_max_depth,
    })


def log_fetch_page(
    session_id: str,
    page_id: str,
    page_title: str,
    last_edited_time: str,
    block_count: int,
) -> None:
    """記錄成功擷取一個頁面"""
    _append_jsonl(_fetch_log_path(), {
        "event": "fetch_page",
        "session_id": session_id,
        "ts": _now_iso(),
        "page_id": page_id,
        "page_title": page_title,
        "last_edited_time": last_edited_time,
        "block_count": block_count,
    })


def log_fetch_skip(
    session_id: str,
    page_id: str,
    page_title: str,
    last_edited_time: str,
    reason: str,
) -> None:
    """記錄跳過一個頁面（無更新）"""
    _append_jsonl(_fetch_log_path(), {
        "event": "fetch_skip",
        "session_id": session_id,
        "ts": _now_iso(),
        "page_id": page_id,
        "page_title": page_title,
        "last_edited_time": last_edited_time,
        "skipped_reason": reason,
    })


def log_fetch_complete(
    session_id: str,
    fetched_count: int,
    skipped_count: int,
    duration_sec: float,
) -> None:
    """記錄 fetch 完成"""
    _append_jsonl(_fetch_log_path(), {
        "event": "fetch_complete",
        "session_id": session_id,
        "ts": _now_iso(),
        "fetched_count": fetched_count,
        "skipped_count": skipped_count,
        "duration_sec": round(duration_sec, 2),
    })


# ── Access 事件 ───────────────────────────────────────

def log_search(
    query: str,
    top_k: int,
    category: str | None,
    returned_ids: list[int],
    source_titles: list[str],
    client_ip: str | None = None,
) -> None:
    """記錄語意搜尋請求"""
    _append_jsonl(_access_log_path(), {
        "event": "search",
        "ts": _now_iso(),
        "query": query,
        "top_k": top_k,
        "category": category,
        "returned_ids": returned_ids,
        "source_titles": source_titles,
        "client_ip": client_ip,
    })


def log_chat(
    message: str,
    returned_ids: list[int],
    source_titles: list[str],
    client_ip: str | None = None,
) -> None:
    """記錄 RAG 問答請求（哪些 QA 被用來生成回答）"""
    _append_jsonl(_access_log_path(), {
        "event": "chat",
        "ts": _now_iso(),
        "message": message,
        "returned_ids": returned_ids,
        "source_titles": source_titles,
        "client_ip": client_ip,
    })


def log_list_qa(
    filters: dict[str, Any],
    returned_ids: list[int],
    total: int,
    client_ip: str | None = None,
) -> None:
    """記錄 QA 列表查詢"""
    _append_jsonl(_access_log_path(), {
        "event": "list_qa",
        "ts": _now_iso(),
        "filters": filters,
        "returned_ids": returned_ids,
        "returned_count": len(returned_ids),
        "total_matched": total,
        "client_ip": client_ip,
    })


# ── 工具函式（供外部使用）────────────────────────────────

def new_session_id() -> str:
    """產生新的 session ID"""
    return str(uuid.uuid4())[:8]
