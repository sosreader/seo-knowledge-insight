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
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)

_VERSIONS_DIR = Path(__file__).resolve().parent.parent / "output" / ".versions"
_REGISTRY_FILE = _VERSIONS_DIR / "registry.json"

# ── Step 命名映射（描述性名稱 ↔ 數字）────────────────
STEP_NAMES: dict[int, str] = {
    1: "fetch-notion",
    2: "extract-qa",
    3: "dedupe-classify",
    4: "generate-report",
    5: "evaluate-qa",
}
_NAME_TO_STEP: dict[str, int] = {v: k for k, v in STEP_NAMES.items()}


def resolve_step(step_or_name: Union[int, str]) -> int:
    """
    將 step 整數或描述性名稱統一轉換為步驟編號。

    Args:
        step_or_name: 整數（2）、描述性名稱（"extract-qa"）或數字字串（"2"）

    Returns:
        步驟編號整數

    Raises:
        TypeError:  傳入非 int / str 型別
        ValueError: 字串名稱不在 STEP_NAMES 中，且不是合法數字
    """
    if isinstance(step_or_name, int):
        return step_or_name
    if isinstance(step_or_name, str):
        if step_or_name in _NAME_TO_STEP:
            return _NAME_TO_STEP[step_or_name]
        try:
            return int(step_or_name)
        except ValueError:
            raise ValueError(
                f"未知的 step 名稱 {step_or_name!r}。"
                f"可用名稱：{list(_NAME_TO_STEP.keys())} 或整數 1-5。"
            )
    raise TypeError(f"step_or_name 必須是 int 或 str，收到：{type(step_or_name).__name__!r}")


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
    step: Union[int, str],
    data: Any,
    metadata: Optional[dict] = None,
    tokens_used: int = 0,
    tokens_saved: int = 0,
    label: Optional[str] = None,
) -> dict:
    """
    Store an immutable artifact and register it in the version registry.

    Idempotent: if a version with the same content_hash already exists for
    this step, the existing entry is returned without writing a new file.

    Args:
        step:         pipeline step number (int/str, e.g. 2 or "extract-qa")
        data:         the artifact payload (JSON-serialisable)
        metadata:     optional extra fields merged into the registry entry
        tokens_used:  LLM tokens consumed producing this artifact
        tokens_saved: LLM tokens saved by cache hits during this run
        label:        optional semantic label（如 "全量重跑@2026-03-02"）

    Returns:
        The registry entry dict for this artifact.
    """
    step_int = resolve_step(step)
    step_name = STEP_NAMES.get(step_int, f"step{step_int}")

    ch = content_hash(data)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    step_dir = _VERSIONS_DIR / f"step{step_int}"
    step_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = step_dir / f"{today}_{ch}.json"

    # ── Idempotency: same hash already recorded? ──────────────
    registry = _load_registry()
    existing = next(
        (v for v in registry["versions"] if v.get("content_hash") == ch and v.get("step") == step_int),
        None,
    )
    if existing:
        logger.debug("record_artifact: step=%d already at %s", step_int, existing["version_id"])
        return existing

    # ── Write immutable artifact ──────────────────────────────
    try:
        artifact_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.error("Artifact write error: %s", exc)
        raise  # 寫入失敗時不更新 registry，保持資料完整性

    # ── Update registry ───────────────────────────────────────
    entry: dict = {
        "step": step_int,
        "step_name": step_name,
        "version_id": f"step{step_int}_{today}_{ch}",
        "content_hash": ch,
        "artifact_path": str(artifact_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tokens_used": tokens_used,
        "tokens_saved": tokens_saved,
        **(metadata or {}),
    }
    if label is not None:
        entry["label"] = label

    registry["versions"].append(entry)
    registry.setdefault("latest", {})[f"step{step_int}"] = entry["version_id"]
    _save_registry(registry)

    logger.info(
        "record_artifact: step=%d(%s) version_id=%s tokens_used=%d tokens_saved=%d",
        step_int, step_name, entry["version_id"], tokens_used, tokens_saved,
    )
    return entry


def get_latest_version(step: Union[int, str]) -> Optional[dict]:
    """Return the most recent registry entry for step, or None."""
    step_int = resolve_step(step)
    registry = _load_registry()
    version_id = registry.get("latest", {}).get(f"step{step_int}")
    if not version_id:
        return None
    return next(
        (v for v in registry["versions"] if v.get("version_id") == version_id),
        None,
    )


def get_version_history(step: Union[int, str]) -> list[dict]:
    """Return all registry entries for step, newest first."""
    step_int = resolve_step(step)
    registry = _load_registry()
    versions = [v for v in registry["versions"] if v.get("step") == step_int]
    return sorted(versions, key=lambda v: v.get("timestamp", ""), reverse=True)


def label_version(version_id: str, label: str) -> Optional[dict]:
    """
    為已存在的版本加上語意標籤。

    Args:
        version_id: 版本 ID（如 "step2_2026-03-02_abc123"）
        label:      語意標籤（如 "全量重跑@2026-03-02"）

    Returns:
        更新後的 registry entry，若 version_id 不存在則回傳 None
    """
    registry = _load_registry()
    idx = next(
        (i for i, v in enumerate(registry["versions"]) if v.get("version_id") == version_id),
        None,
    )
    if idx is None:
        logger.warning("label_version: version_id %r 不存在", version_id)
        return None

    # 建立新 dict（不修改原始物件，符合 immutability 原則）
    updated = {**registry["versions"][idx], "label": label}
    new_versions = [
        updated if i == idx else v
        for i, v in enumerate(registry["versions"])
    ]
    step_int = updated.get("step", 0)
    new_registry = {
        **registry,
        "versions": new_versions,
        "latest": {**registry.get("latest", {}), f"step{step_int}": updated["version_id"]},
    }
    _save_registry(new_registry)
    logger.info("label_version: %s → %r", version_id, label)
    return updated


def register_existing_file(
    step: Union[int, str],
    file_path: Path,
    metadata: Optional[dict] = None,
    label: Optional[str] = None,
) -> dict:
    """
    將既有的輸出檔案補登入 version registry（不重寫檔案）。

    適用於繞過 record_artifact() 直接輸出的歷史版本。

    Args:
        step:      pipeline step（int 或描述性名稱）
        file_path: 已存在的檔案路徑（必須存在）
        metadata:  可選的額外 metadata
        label:     可選的語意標籤

    Returns:
        Registry entry dict

    Raises:
        FileNotFoundError: 若 file_path 不存在
    """
    if not file_path.exists():
        raise FileNotFoundError(f"register_existing_file: 檔案不存在 {file_path}")

    step_int = resolve_step(step)
    step_name = STEP_NAMES.get(step_int, f"step{step_int}")

    file_content = file_path.read_bytes()
    ch = hashlib.sha256(file_content).hexdigest()[:16]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    registry = _load_registry()
    existing = next(
        (v for v in registry["versions"] if v.get("content_hash") == ch and v.get("step") == step_int),
        None,
    )
    if existing:
        logger.debug("register_existing_file: step=%d already at %s", step_int, existing["version_id"])
        return existing

    entry: dict = {
        "step": step_int,
        "step_name": step_name,
        "version_id": f"step{step_int}_{today}_{ch}",
        "content_hash": ch,
        "artifact_path": str(file_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tokens_used": 0,
        "tokens_saved": 0,
        **(metadata or {}),
    }
    if label is not None:
        entry["label"] = label

    registry["versions"].append(entry)
    registry.setdefault("latest", {})[f"step{step_int}"] = entry["version_id"]
    _save_registry(registry)

    logger.info(
        "register_existing_file: step=%d(%s) version_id=%s",
        step_int, step_name, entry["version_id"],
    )
    return entry


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
