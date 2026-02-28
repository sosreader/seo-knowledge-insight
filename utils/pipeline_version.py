"""
Pipeline immutable artifact version registry.

Design principles:
- Immutable artifacts：每次 pipeline run 產生不可變的帶版本 JSON，寫入後不覆蓋
- Content-addressed version ID：{step}_{date}_{sha256[:16]}，相同內容冪等
- Registry file：output/.versions/registry.json 記錄所有版本 metadata
- qa_final.json stays as the "latest" copy that the API reads
- Zero external deps：純 stdlib

目錄結構：
    output/
      .versions/
        registry.json          ← 所有版本的索引（需納入 git）
        step2/
          2026-02-28_a3f8bc1d.json   ← Q&A raw artifact（gitignored）
        step3/
          2026-02-28_b1c2d3e4.json   ← Q&A final artifact（gitignored）
        step4/
          report_2026-02-28_c1e3g5h7.md ← 週報 artifact（gitignored）
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_VERSIONS_DIR = Path(__file__).resolve().parent.parent / "output" / ".versions"
_REGISTRY_FILE = _VERSIONS_DIR / "registry.json"


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────

def _load_registry() -> dict:
    if _REGISTRY_FILE.exists():
        try:
            return json.loads(_REGISTRY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Registry read error: %s", exc)
    return {"versions": [], "latest": {}}


def _save_registry(registry: dict) -> None:
    _REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _REGISTRY_FILE.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(_REGISTRY_FILE)
    except OSError as exc:
        logger.error("Registry write error: %s", exc)


# ──────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────

def content_hash(data: Any) -> str:
    """
    Deterministic 16-char hash of any JSON-serialisable object.
    Keys are sorted to ensure stability across Python dict orderings.
    """
    serialized = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def record_artifact(
    step: int,
    data: Any,
    metadata: Optional[dict] = None,
    tokens_used: int = 0,
    tokens_saved: int = 0,
) -> dict:
    """
    Store an immutable artifact and register it in the version registry.

    Idempotent: if a version with the same content_hash already exists for
    this step, the existing entry is returned without writing a new file.

    Args:
        step:         pipeline step number (2, 3, 4, …)
        data:         the artifact payload (JSON-serialisable)
        metadata:     optional extra fields merged into the registry entry
        tokens_used:  LLM tokens consumed producing this artifact
        tokens_saved: LLM tokens saved by cache hits during this run

    Returns:
        The registry entry dict for this artifact.
    """
    ch = content_hash(data)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    step_dir = _VERSIONS_DIR / f"step{step}"
    step_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = step_dir / f"{today}_{ch}.json"

    # ── Idempotency: same hash already recorded? ──────────────
    registry = _load_registry()
    existing = next(
        (v for v in registry["versions"] if v.get("content_hash") == ch and v.get("step") == step),
        None,
    )
    if existing:
        logger.debug("record_artifact: step=%d already at %s", step, existing["version_id"])
        return existing

    # ── Write immutable artifact ──────────────────────────────
    try:
        artifact_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("Artifact write error: %s", exc)

    # ── Update registry ───────────────────────────────────────
    entry: dict = {
        "step": step,
        "version_id": f"step{step}_{today}_{ch}",
        "content_hash": ch,
        "artifact_path": str(artifact_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tokens_used": tokens_used,
        "tokens_saved": tokens_saved,
        **(metadata or {}),
    }
    registry["versions"].append(entry)
    registry.setdefault("latest", {})[f"step{step}"] = entry["version_id"]
    _save_registry(registry)

    logger.info(
        "record_artifact: step=%d version_id=%s tokens_used=%d tokens_saved=%d",
        step, entry["version_id"], tokens_used, tokens_saved,
    )
    return entry


def get_latest_version(step: int) -> Optional[dict]:
    """Return the most recent registry entry for step, or None."""
    registry = _load_registry()
    version_id = registry.get("latest", {}).get(f"step{step}")
    if not version_id:
        return None
    return next(
        (v for v in registry["versions"] if v.get("version_id") == version_id),
        None,
    )


def get_version_history(step: int) -> list[dict]:
    """Return all registry entries for step, newest first."""
    registry = _load_registry()
    versions = [v for v in registry["versions"] if v.get("step") == step]
    return sorted(versions, key=lambda v: v.get("timestamp", ""), reverse=True)


def get_all_token_stats() -> dict:
    """
    Aggregate token usage and savings across all steps.

    Returns:
        {"total_used": int, "total_saved": int, "by_step": {step: {used, saved}}}
    """
    registry = _load_registry()
    by_step: dict[int, dict] = {}
    for entry in registry["versions"]:
        s = entry.get("step", 0)
        by_step.setdefault(s, {"used": 0, "saved": 0})
        by_step[s]["used"] += entry.get("tokens_used", 0)
        by_step[s]["saved"] += entry.get("tokens_saved", 0)

    total_used = sum(v["used"] for v in by_step.values())
    total_saved = sum(v["saved"] for v in by_step.values())
    return {
        "total_used": total_used,
        "total_saved": total_saved,
        "by_step": by_step,
    }
