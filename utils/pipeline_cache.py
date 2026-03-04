"""
Pipeline disk-based content-addressed cache.

Design principles:
- Cache key = SHA256(input content)：與時間、檔名無關，相同輸入永遠命中
- Atomic write：先寫 .tmp 再 rename，防止 partial write 污染 cache
- Two-level directory：{namespace}/{hash[:2]}/{hash}.json 避免單目錄檔案爆炸
- No TTL：pipeline LLM 結果是確定性的，只要輸入沒變結果就有效
- No external deps：純 stdlib，零部署依賴

Cache 目錄：output/.cache/{namespace}/{hash[:2]}/{hash}.json

Namespace 對應：
    extraction   Step 2 per-meeting / per-chunk Q&A 萃取結果
    embedding    文字 → 向量 (base64 encoded float32)
    classify     Q&A → category/difficulty/evergreen 分類結果
    merge        相似 Q&A group → 合併後的 Q&A
    report       metrics_tsv + qa_version → 週報 Markdown
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# output/.cache/ — gitignored, project-relative
_CACHE_DIR = Path(__file__).resolve().parent.parent / "output" / ".cache"


def _key(content: str, *, model: str | None = None) -> str:
    """SHA256 hex digest of UTF-8 content, optionally scoped to a model.

    When ``model`` is provided the key becomes ``SHA256(model::content)``
    so that different models produce separate cache entries for the same input.
    """
    payload = f"{model}::{content}" if model else content
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cache_path(namespace: str, content: str, *, model: str | None = None) -> Path:
    """Return the full path for a cache entry (file may not exist)."""
    h = _key(content, model=model)
    return _CACHE_DIR / namespace / h[:2] / f"{h}.json"


def cache_get(namespace: str, content: str, *, model: str | None = None) -> Optional[Any]:
    """
    Retrieve a cached value.

    Args:
        namespace: logical bucket (e.g. "extraction", "embedding")
        content:   the raw input whose hash is used as the key
        model:     optional model name to scope cache per-model

    Returns:
        Parsed JSON value, or None on miss.
    """
    path = cache_path(namespace, content, model=model)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Cache read error (%s/%s): %s", namespace, path.name, exc)
        return None


def cache_set(namespace: str, content: str, value: Any, *, model: str | None = None) -> None:
    """
    Store a value in the cache (atomic write via temp file + rename).

    Args:
        namespace: logical bucket
        content:   the raw input whose hash determines the key
        value:     any JSON-serialisable object
        model:     optional model name to scope cache per-model
    """
    path = cache_path(namespace, content, model=model)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)  # atomic on POSIX; best-effort on Windows
    except OSError as exc:
        logger.error("Cache write error (%s/%s): %s", namespace, path.name, exc)
        # Best-effort cleanup of the temp file
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def cache_exists(namespace: str, content: str, *, model: str | None = None) -> bool:
    """Return True if a cache entry exists for the given input."""
    return cache_path(namespace, content, model=model).exists()


def cache_stats(namespace: str) -> dict:
    """
    Return count and total size for a namespace.

    Returns:
        {"count": int, "size_bytes": int}
    """
    ns_dir = _CACHE_DIR / namespace
    if not ns_dir.exists():
        return {"count": 0, "size_bytes": 0}
    files = list(ns_dir.rglob("*.json"))
    return {
        "count": len(files),
        "size_bytes": sum(f.stat().st_size for f in files),
    }


def cache_clear(namespace: str) -> int:
    """
    Delete all entries in a namespace.

    Returns:
        Number of files deleted.
    """
    import shutil

    ns_dir = _CACHE_DIR / namespace
    if not ns_dir.exists():
        return 0
    files = list(ns_dir.rglob("*.json"))
    shutil.rmtree(ns_dir, ignore_errors=True)
    return len(files)
