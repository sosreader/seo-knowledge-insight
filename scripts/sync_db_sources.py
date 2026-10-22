"""sync_db_sources.py — 本機 output/ 的候選清單、content_hash 演算法與上傳 payload。

content_hash（寫入端計算，伺服器只比對相等；寫入 docs 與 PR）：
  - reports／meeting_prep：`sha256:` ＋ 檔案原始位元組（UTF-8）的 SHA-256 hex。
    與發布帳冊的 sha256 是同一個值，所以「帳冊核准的版本」＝「倉儲裡的 content_hash」。
  - sessions：`sha256:` ＋ `{"title", "messages"}` 以 sort_keys、separators=(",", ":")、
    ensure_ascii=False 序列化後 UTF-8 的 SHA-256 hex。舊版 session-sync 不送 metadata，這裡沿用，
    因此 metadata 不納入 hash。
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sync_db_gate import ReviewEntry
from sync_db_meta import parse_meeting_prep_meta, parse_report_meta

__all__ = [
    "LocalDocument", "LocalSession", "build_item", "build_session_item", "list_documents", "list_sessions",
    "parse_meeting_prep_meta", "parse_report_meta", "session_content_hash", "text_content_hash",
]

logger = logging.getLogger(__name__)

HASH_PREFIX = "sha256:"
DOCUMENT_PATTERNS = {
    "reports": re.compile(r"^report_(\d{8}(?:_[0-9a-f]{8})?)\.md$"),
    "meeting_prep": re.compile(r"^meeting_prep_(\d{8}_[0-9a-f]{8})\.md$"),
}
# 與 api/src/sync/session-sync.ts 相同：只收 UUID v4
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


@dataclass(frozen=True)
class LocalDocument:
    kind: str
    key: str
    filename: str
    content: bytes


@dataclass(frozen=True)
class LocalSession:
    id: str
    title: str
    messages: tuple[dict[str, Any], ...]
    created_at: str
    updated_at: str


def text_content_hash(content: bytes) -> str:
    return HASH_PREFIX + hashlib.sha256(content).hexdigest()


def session_content_hash(title: str, messages: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> str:
    canonical = json.dumps({"title": title, "messages": list(messages)},
                           sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return HASH_PREFIX + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def list_documents(output_dir: Path, kind: str) -> tuple[LocalDocument, ...]:
    """列出 output/ 下符合檔名規則的報告；依檔名排序，結果與 mtime 無關。"""
    pattern = DOCUMENT_PATTERNS[kind]
    if not output_dir.is_dir():
        return ()
    docs = []
    for path in sorted(output_dir.iterdir()):
        match = pattern.match(path.name)
        if match and path.is_file():
            docs.append(LocalDocument(kind=kind, key=match.group(1), filename=path.name, content=path.read_bytes()))
    return tuple(docs)


def _aware_iso(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _parse_session(raw: Any) -> LocalSession | None:
    if not isinstance(raw, dict):
        return None
    sid, title, messages = raw.get("id"), raw.get("title"), raw.get("messages")
    if not (isinstance(sid, str) and UUID_RE.match(sid) and isinstance(title, str)):
        return None
    if not (isinstance(messages, list) and all(isinstance(m, dict) for m in messages)):
        return None
    if not (_aware_iso(raw.get("created_at")) and _aware_iso(raw.get("updated_at"))):
        return None
    return LocalSession(id=sid, title=title, messages=tuple(messages),
                        created_at=raw["created_at"], updated_at=raw["updated_at"])


def list_sessions(sessions_dir: Path) -> tuple[tuple[LocalSession, ...], tuple[tuple[str, str], ...]]:
    """回 (合法 sessions, 被略過的 (檔名, 原因))；格式不符的檔不中止整批（同舊版行為）。"""
    if not sessions_dir.is_dir():
        return (), ()
    sessions: list[LocalSession] = []
    skipped: list[tuple[str, str]] = []
    for path in sorted(sessions_dir.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            skipped.append((path.name, "malformed_json"))
            continue
        session = _parse_session(raw)
        if session is None:
            skipped.append((path.name, "invalid_session"))
            continue
        sessions.append(session)
    return tuple(sessions), tuple(skipped)


def build_item(doc: LocalDocument, entry: ReviewEntry) -> dict[str, Any]:
    """reports／meeting_prep 的單筆 body；呼叫前必須已過閘門（entry 為 approved 且 hash 相符）。"""
    text = doc.content.decode("utf-8")
    if doc.kind == "reports":
        meta: Any = parse_report_meta(text)
    else:
        meta = parse_meeting_prep_meta(text) or {}
    return {
        "date_key": doc.key,
        "filename": doc.filename,
        "content": text,
        "meta": meta,
        "content_hash": text_content_hash(doc.content),
        "approved_version": f"review:{entry.reviewed_at}:{entry.sha256}",
    }


def build_session_item(session: LocalSession) -> dict[str, Any]:
    messages = list(session.messages)
    return {
        "id": session.id,
        "title": session.title,
        "messages": messages,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "content_hash": session_content_hash(session.title, messages),
    }
