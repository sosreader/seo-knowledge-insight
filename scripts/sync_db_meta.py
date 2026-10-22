"""sync_db_meta.py — 從報告內文解析 metadata（移植 api/src/utils/{report-file,meeting-prep-file}.ts）。

舊版 sync-db.ts 上傳時就是用這兩個函式算 `meta` 欄位；倉儲讀取路由與 maturity-trend
依賴同一個形狀，因此逐欄照搬，包含預設值（weeks=1、maturity 缺值補 L1 等）。
JS 的 `typeof x === "number"` 不含布林，這裡以 _is_number 排除 bool。
"""
from __future__ import annotations

import json
import re
from typing import Any

REPORT_META_RE = re.compile(r"<!-- report_meta ({[\s\S]*?}) -->")
MEETING_PREP_JSON_BLOCK_RE = re.compile(r'```json\s*\n(\{[\s\S]*?"meeting_prep_meta"[\s\S]*?\})\s*\n```')
MEETING_PREP_HTML_COMMENT_RE = re.compile(r"<!-- meeting_prep_meta ({[\s\S]*?}) -->")
SOURCE_REPORT_DATE_RE = re.compile(r"report_(\d{8})")

EEAT_FIELDS = ("experience", "expertise", "authoritativeness", "trustworthiness")
EEAT_SHORTHAND = ("eeat_e", "eeat_ex", "eeat_a", "eeat_t")
MATURITY_FIELDS = ("strategy", "process", "keywords", "metrics")
DEFAULT_MATURITY = "L1"
DEFAULT_GENERATION_MODE = "claude-code-semantic"


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _num_or(value: Any, default: Any) -> Any:
    return value if _is_number(value) else default


def _str_or(value: Any, default: Any) -> Any:
    return value if isinstance(value, str) else default


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_object(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def parse_report_meta(content: str) -> dict[str, Any] | None:
    match = REPORT_META_RE.search(content)
    if not match:
        return None
    raw = _load_object(match.group(1))
    if raw is None:
        return None
    meta: dict[str, Any] = {
        "weeks": _num_or(raw.get("weeks"), 1),
        "generated_at": _str_or(raw.get("generated_at"), ""),
        "generation_mode": _str_or(raw.get("generation_mode"), "template"),
        "generation_label": _str_or(raw.get("generation_label"), ""),
    }
    if isinstance(raw.get("model"), str):
        meta = {**meta, "model": raw["model"]}
    if isinstance(raw.get("experiment_tag"), str):
        meta = {**meta, "experiment_tag": raw["experiment_tag"]}
    return meta


def _eeat(raw: dict[str, Any]) -> dict[str, Any]:
    canonical = _as_dict(raw.get("scores")).get("eeat")
    if isinstance(canonical, dict):
        return {field: _num_or(canonical.get(field), 0) for field in EEAT_FIELDS}
    if any(_is_number(raw.get(key)) for key in EEAT_SHORTHAND):
        return {field: _num_or(raw.get(key), 0) for field, key in zip(EEAT_FIELDS, EEAT_SHORTHAND)}
    avg = _num_or(raw.get("eeat_avg"), 0)
    return {field: avg for field in EEAT_FIELDS}


def _maturity(raw: dict[str, Any]) -> dict[str, str]:
    scores_maturity = _as_dict(raw.get("scores")).get("maturity")
    source = scores_maturity if scores_maturity is not None else raw.get("maturity")
    source = _as_dict(source)
    return {field: _str_or(source.get(field), DEFAULT_MATURITY) for field in MATURITY_FIELDS}


def _source_report_date(raw: dict[str, Any]) -> str | None:
    if isinstance(raw.get("source_report_date"), str):
        return raw["source_report_date"]
    if isinstance(raw.get("source_report"), str):
        match = SOURCE_REPORT_DATE_RE.search(raw["source_report"])
        if match:
            return match.group(1)
    return None


def _raw_meeting_prep_meta(content: str) -> dict[str, Any] | None:
    block = MEETING_PREP_JSON_BLOCK_RE.search(content)
    if block:
        wrapped = _load_object(block.group(1))
        if wrapped is not None and isinstance(wrapped.get("meeting_prep_meta"), dict):
            return wrapped["meeting_prep_meta"]
    comment = MEETING_PREP_HTML_COMMENT_RE.search(content)
    if comment:
        return _load_object(comment.group(1))
    return None


def parse_meeting_prep_meta(content: str) -> dict[str, Any] | None:
    raw = _raw_meeting_prep_meta(content)
    if raw is None or not isinstance(raw.get("date"), str):
        return None
    question_count = raw.get("question_count")
    if not _is_number(question_count):
        question_count = _num_or(raw.get("s9_questions"), 0)
    meta: dict[str, Any] = {
        "date": raw["date"],
        "scores": {"eeat": _eeat(raw), "maturity": _maturity(raw)},
        "alert_down_count": _num_or(raw.get("alert_down_count"), 0),
        "question_count": question_count,
        "generation_mode": _str_or(raw.get("generation_mode"), DEFAULT_GENERATION_MODE),
    }
    source_date = _source_report_date(raw)
    return {**meta, "source_report_date": source_date} if source_date else meta
