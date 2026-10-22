"""sync_db_gate.py — /sync-db 的發布閘門（fail-closed）。

語意移植自 api/src/sync/publication-gate.ts（2026-09-12 本地版）：
  - 帳冊 data/content-publication-review.json 以 filename＋SHA-256 綁定「被核准的那個版本」。
  - 只有 status=approved 且檔案 hash 與帳冊相符才可發布；pending／historical／未登記／hash 漂移
    一律擋下，帳冊破損或讀不到時整體關閉。
  - force 只影響遠端「已存在要不要覆寫」，不能略過本關卡。
  - 帳冊是受控設定，不是數位簽章；能改帳冊的人就能改變決策。

本模組只做純判斷與帳冊載入，不讀報告檔、不連網。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

MANIFEST_RELPATH = "data/content-publication-review.json"
MAX_MANIFEST_BYTES = 1_000_000
MANIFEST_VERSION = 1

FILENAME_RE = re.compile(r"^(?:report_\d{8}(?:_[0-9a-f]{8})?|meeting_prep_\d{8}_[0-9a-f]{8})\.md$")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 正規式一律用 fullmatch：Python 的 `$` 會接受結尾換行，JS 不會（TS 版遇到會讓帳冊失效）
STATUSES = frozenset({"approved", "pending", "historical"})


class PublicationBlocked(Exception):
    """閘門拒絕；reason 為固定代碼，不夾帶帳冊或檔案內容。"""

    def __init__(self, reason: str) -> None:
        super().__init__(f"publication: {reason}")
        self.reason = reason


@dataclass(frozen=True)
class ReviewEntry:
    filename: str
    sha256: str
    status: str
    reviewed_by: str
    reviewed_at: str
    reason: str


@dataclass(frozen=True)
class GateDecision:
    """reason 為 None 表示可發布；sha256 是本機檔案的實際 hash。"""

    filename: str
    sha256: str
    reason: str | None
    entry: ReviewEntry | None


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _valid_day(value: Any) -> bool:
    if not isinstance(value, str) or not DAY_RE.fullmatch(value):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _parse_entry(raw: Any) -> ReviewEntry | None:
    if not isinstance(raw, dict):
        return None
    filename, sha256, status = raw.get("filename"), raw.get("sha256"), raw.get("status")
    if not (isinstance(filename, str) and FILENAME_RE.fullmatch(filename)):
        return None
    if not (isinstance(sha256, str) and HASH_RE.fullmatch(sha256)):
        return None
    if not (isinstance(status, str) and status in STATUSES):
        return None
    if not (_nonempty(raw.get("reviewed_by")) and _valid_day(raw.get("reviewed_at")) and _nonempty(raw.get("reason"))):
        return None
    return ReviewEntry(filename=filename, sha256=sha256, status=status, reviewed_by=raw["reviewed_by"],
                       reviewed_at=raw["reviewed_at"], reason=raw["reason"])


def parse_manifest(value: Any) -> tuple[ReviewEntry, ...] | None:
    """整份帳冊驗證；任何一筆不合法或檔名重複就回 None（整體關閉）。"""
    if not isinstance(value, dict) or value.get("version") != MANIFEST_VERSION:
        return None
    raw_entries = value.get("entries")
    if not isinstance(raw_entries, list):
        return None
    entries = tuple(_parse_entry(raw) for raw in raw_entries)
    if any(entry is None for entry in entries):
        return None
    if len({entry.filename for entry in entries}) != len(entries):  # type: ignore[union-attr]
        return None
    return entries  # type: ignore[return-value]


def load_manifest(path: Path) -> tuple[ReviewEntry, ...]:
    """讀帳冊；讀不到／超量／非 JSON → review_manifest_unavailable，結構不合法 → invalid_review_manifest。"""
    try:
        raw = path.read_bytes()
        if len(raw) > MAX_MANIFEST_BYTES:
            raise ValueError("oversized")
        value = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):
        raise PublicationBlocked("review_manifest_unavailable") from None
    entries = parse_manifest(value)
    if entries is None:
        raise PublicationBlocked("invalid_review_manifest")
    return entries


def evaluate(entries: tuple[ReviewEntry, ...], filename: str, content: bytes) -> GateDecision:
    sha256 = hashlib.sha256(content).hexdigest()
    if not FILENAME_RE.fullmatch(filename):
        return GateDecision(filename, sha256, "invalid_filename", None)
    entry = next((item for item in entries if item.filename == filename), None)
    if entry is None:
        return GateDecision(filename, sha256, "missing_review", None)
    if entry.status != "approved":
        return GateDecision(filename, sha256, entry.status, entry)
    reason = None if sha256 == entry.sha256 else "content_changed"
    return GateDecision(filename, sha256, reason, entry)


def publication_block_reason(manifest: Any, filename: str, content: bytes) -> str | None:
    """與 publication-gate.ts 的 publicationBlockReason 同語意的純函式。"""
    if not FILENAME_RE.fullmatch(filename):
        return "invalid_filename"
    entries = parse_manifest(manifest)
    if entries is None:
        return "invalid_review_manifest"
    return evaluate(entries, filename, content).reason
