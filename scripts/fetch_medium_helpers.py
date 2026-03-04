"""Helpers for 01b_fetch_medium.py — extracted for testability."""
from __future__ import annotations

import re


def _safe_filename(title: str) -> str:
    """Convert title to safe filename."""
    safe = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', title)
    safe = re.sub(r'\s+', '_', safe.strip())
    return safe[:80] if safe else "untitled"
