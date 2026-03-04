"""Structured execution log for CLI commands.

Appends JSONL records to ``output/execution_log.jsonl`` so every
``qa_tools.py`` invocation is tracked — independent of Laminar.

Usage::

    from utils.execution_log import log_execution

    log_execution(
        command="search",
        args={"query": "SEO", "top_k": 5},
        result={"results_count": 3, "top_score": 12.0},
        duration_ms=42.1,
    )
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_LOG_DIR = Path(__file__).resolve().parent.parent / "output"
_LOG_PATH = _LOG_DIR / "execution_log.jsonl"


def log_execution(
    command: str,
    args: dict[str, Any],
    result: dict[str, Any],
    duration_ms: float,
) -> None:
    """Append a structured execution record to JSONL.

    Never raises — logging failures are silently swallowed so they
    cannot affect the main CLI flow.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "args": _sanitize(args),
        "duration_ms": round(duration_ms, 1),
        "result": result,
    }
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.debug("log_execution failed: %s", exc)


_STRIP_KEYS: frozenset[str] = frozenset({"cmd"})
_REDACT_URL_KEYS: frozenset[str] = frozenset({"source"})


def _sanitize(args: dict[str, Any]) -> dict[str, Any]:
    """Strip potentially sensitive or oversized values from args."""
    sanitized: dict[str, Any] = {}
    for key, val in args.items():
        if key in _STRIP_KEYS:
            continue
        if isinstance(val, str):
            # Redact URL query strings that may contain tokens
            if key in _REDACT_URL_KEYS and val.startswith("http"):
                base = val.split("?")[0]
                sanitized[key] = base + ("?<redacted>" if "?" in val else "")
                continue
            if len(val) > 500:
                sanitized[key] = val[:500] + "..."
                continue
        sanitized[key] = val
    return sanitized
