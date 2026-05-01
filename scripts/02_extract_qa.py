#!/usr/bin/env python3
"""
步驟 2：用 OpenAI 從每份會議 Markdown 中萃取 Q&A pairs

功能：
- 讀取 raw_data/markdown/ 下所有 .md 檔
- 逐一呼叫 OpenAI API 萃取 Q&A
- 每份會議的 Q&A 存到 output/qa_per_meeting/
- 合併成一份完整的 Q&A 列表

用法：
    python scripts/02_extract_qa.py
    python scripts/02_extract_qa.py --limit 5          # 先試 5 份
    python scripts/02_extract_qa.py --file xxx.md      # 只處理指定檔案
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

from utils.openai_helper import extract_qa_from_text
from utils.pipeline_cache import cache_get, cache_set
from utils.pipeline_deps import preflight_check, StepDependency
from utils.pipeline_version import record_artifact
from utils.observability import init_laminar, flush_laminar, observe
from scripts.extract_qa_helpers import (
    _extract_date_from_title,
    _extract_date_from_content,
    _split_content,
)

logger = logging.getLogger(__name__)


def _is_completed_qa_artifact(data: dict) -> bool:
    """Treat empty-but-successful artifacts as completed; retry only explicit failures."""
    return isinstance(data.get("qa_pairs"), list) and "處理失敗" not in str(
        data.get("meeting_summary", "")
    )


def _canonical_qa_artifact_path(md_path: Path) -> Path:
    """Return the canonical artifact path for a source markdown file."""
    if md_path.parent.name == "markdown":
        return config.QA_PER_MEETING_DIR / f"{md_path.stem}_qa.json"
    return config.QA_PER_ARTICLE_DIR / f"{md_path.stem}_qa.json"


def _qa_artifact_candidates(md_path: Path) -> tuple[Path, ...]:
    """Check both canonical and legacy artifact locations for incremental compatibility."""
    canonical = _canonical_qa_artifact_path(md_path)
    if md_path.parent.name == "markdown":
        return (canonical,)
    legacy = config.QA_PER_MEETING_DIR / f"{md_path.stem}_qa.json"
    return (canonical, legacy)


def _has_completed_qa_artifact(md_path: Path) -> bool:
    """Return True when any canonical or legacy artifact already represents a completed run."""
    for qa_path in _qa_artifact_candidates(md_path):
        if not qa_path.exists():
            continue
        try:
            existing = json.loads(qa_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if _is_completed_qa_artifact(existing):
            return True
    return False


def _detect_source_metadata(md_path: Path) -> dict:
    """從 Markdown 目錄名稱推斷 source_type 和 source_collection。"""
    dir_name = md_path.parent.name
    source_type, source_collection = config.DIR_COLLECTION_MAP.get(
        dir_name, ("article", dir_name)
    )

    # 嘗試從 Markdown metadata 取 source_url
    content = md_path.read_text(encoding="utf-8")
    source_url = ""
    url_match = re.search(r'\*\*來源 URL\*\*:\s*(.+)', content)
    if url_match:
        source_url = url_match.group(1).strip()

    return {
        "source_type": source_type,
        "source_collection": source_collection,
        "source_url": source_url,
    }


@observe(name="process_single_meeting")
def process_single_meeting(md_path: Path) -> dict:
    """處理單份會議紀錄或文章（LLM 呼叫有 content-addressed cache 保護）"""
    content = md_path.read_text(encoding="utf-8")
    filename = md_path.stem

    # 從 Markdown 內容中擷取標題和日期
    title = filename
    title_match = re.match(r'^# (.+)', content)
    if title_match:
        title = title_match.group(1)

    # 優先從 metadata 區取日期，其次從標題
    date = (
        _extract_date_from_content(content)
        or _extract_date_from_title(title)
        or _extract_date_from_title(filename)
    )

    # 偵測來源 metadata（source_type, source_collection, source_url）
    source_meta = _detect_source_metadata(md_path)

    logger.info("  %s", title)
    logger.info("     字數: %d, 來源: %s", len(content), source_meta['source_collection'])

    # ── Layer 1 cache check ──────────────────────────────────
    # Key = markdown content（title/date 均由 content 衍生，deterministic）
    # Value = extract_qa_from_text() 的 LLM 輸出（不含 source 欄位）
    cached = cache_get("extraction", content, model=config.OPENAI_MODEL)
    if cached is not None:
        qa_count = len(cached.get("qa_pairs", []))
        logger.info("     [cache hit] %d Q&A", qa_count)
        # Immutable enrichment — no mutation of cached data
        cache_enriched = [
            {
                **qa,
                "source_file": md_path.name,
                "source_title": title,
                "source_date": date,
                "source_type": source_meta["source_type"],
                "source_collection": source_meta["source_collection"],
                "source_url": source_meta["source_url"],
                "extraction_model": config.OPENAI_MODEL,
                "extraction_timestamp": datetime.now(timezone.utc).isoformat(),
            }
            for qa in cached.get("qa_pairs", [])
        ]
        return {**cached, "qa_pairs": cache_enriched}

    # ── Cache miss：呼叫 OpenAI ──────────────────────────────
    # 如果內容太長，分段處理
    max_chars = config.MAX_TOKENS_PER_CHUNK * 3  # 大約 3 chars per token
    if len(content) > max_chars:
        logger.warning("     內容較長，分段處理 ...")
        chunks = _split_content(content, max_chars)
        all_qa_pairs = []
        for chunk_i, chunk in enumerate(chunks, 1):
            logger.info("     段落 %d/%d ...", chunk_i, len(chunks))
            result = extract_qa_from_text(chunk, title, date)
            all_qa_pairs.extend(result.get("qa_pairs", []))
            time.sleep(0.5)  # 避免 rate limit

        meeting_result = {
            "qa_pairs": all_qa_pairs,
            "meeting_summary": f"（分 {len(chunks)} 段處理）",
        }
    else:
        meeting_result = extract_qa_from_text(content, title, date)

    # ── 寫入 cache（source 欄位不在 cache 中，以保持 content-addressable）
    cache_set("extraction", content, meeting_result, model=config.OPENAI_MODEL)

    # ── 為每個 Q&A 加上來源資訊 + model provenance（immutable）────
    extraction_ts = datetime.now(timezone.utc).isoformat()
    enriched_pairs = [
        {
            **qa,
            "source_file": md_path.name,
            "source_title": title,
            "source_date": date,
            "source_type": source_meta["source_type"],
            "source_collection": source_meta["source_collection"],
            "source_url": source_meta["source_url"],
            "extraction_model": config.OPENAI_MODEL,
            "extraction_timestamp": extraction_ts,
        }
        for qa in meeting_result.get("qa_pairs", [])
    ]
    meeting_result = {**meeting_result, "qa_pairs": enriched_pairs}

    qa_count = len(enriched_pairs)
    logger.info("     萃取 %d 個 Q&A", qa_count)

    return meeting_result


def _rebuild_merged_from_per_meeting() -> dict:
    """
    從 qa_per_meeting/ 和 qa_per_article/ 下所有已完成的 JSON 重新組合 qa_all_raw.json。
    確保即使中途 crash，已處理的結果不會遺失。
    """
    all_qa: list[dict] = []
    summary: list[dict] = []
    qa_dirs = [config.QA_PER_MEETING_DIR, config.QA_PER_ARTICLE_DIR]

    for qa_dir in qa_dirs:
        if not qa_dir.exists():
            continue
        for f in sorted(qa_dir.glob("*_qa.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if not _is_completed_qa_artifact(data):
                    continue
                pairs = data["qa_pairs"]
                all_qa.extend(pairs)
                summary.append({
                    "file": f.stem.replace("_qa", "") + ".md",
                    "qa_count": len(pairs),
                    "summary": data.get("meeting_summary", ""),
                })
            except (json.JSONDecodeError, KeyError):
                continue

    return {
        "total_qa_count": len(all_qa),
        "meetings_processed": len(summary),
        "qa_pairs": all_qa,
        "processing_summary": summary,
    }


def main(args: argparse.Namespace) -> None:
    init_laminar()

    # ── Pre-flight 依賴檢查 ──
    preflight_check(
        deps=[
            StepDependency(
                path=config.RAW_MD_DIR,
                required=True,
                min_count=1,
                glob_pattern="*.md",
                max_age_days=14,
                hint="請先執行 python scripts/01_fetch_notion.py",
            ),
        ],
        env_keys=["OPENAI_API_KEY"],
        step_name="Step 2: Q&A 萃取",
        check_only=getattr(args, "check", False),
    )
    if getattr(args, "check", False):
        return

    force = args.force

    logger.info("步驟 2：用 OpenAI 萃取 Q&A")
    logger.info("模型: %s", config.OPENAI_MODEL)
    if force:
        logger.info("強制模式：重新處理所有檔案")
    else:
        logger.info("增量模式：跳過已完成的檔案")

    # 收集要處理的檔案（多來源目錄）
    source_dirs = list(config.get_all_markdown_source_dirs())

    if args.file:
        # 在所有來源目錄中搜尋指定檔案
        found = None
        for d in source_dirs:
            candidate = d / args.file
            if candidate.exists():
                found = candidate
                break
        if found is None:
            logger.error("找不到: %s（已搜尋 %d 個目錄）", args.file, len(source_dirs))
            sys.exit(1)
        md_files = [found]
    else:
        md_files = []
        for d in source_dirs:
            if d.exists():
                md_files.extend(sorted(d.glob("*.md")))

    if not md_files:
        logger.error("所有來源目錄下沒有 .md 檔案，請先執行步驟 1")
        sys.exit(1)

    if args.limit:
        md_files = md_files[: args.limit]

    # 增量過濾：跳過已經有成功結果的
    if not force:
        filtered = []
        skipped = 0
        for md_path in md_files:
            if _has_completed_qa_artifact(md_path):
                skipped += 1
                continue
            filtered.append(md_path)

        if skipped:
            logger.info("跳過 %d 份（已完成）", skipped)
        md_files = filtered

    if not md_files:
        logger.info("所有檔案已處理完畢，無需重跑。")
        logger.info("使用 --force 可強制全部重新處理")
        # 確保合併檔存在
        merged = _rebuild_merged_from_per_meeting()
        merged_path = config.OUTPUT_DIR / "qa_all_raw.json"
        merged_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        qa_count = merged["total_qa_count"]
        logger.info("合併結果已更新: %d 個 Q&A", qa_count)
        version_entry = record_artifact(
            step=2,
            data=merged,
            metadata={
                "qa_count": merged["total_qa_count"],
                "meetings_processed": merged["meetings_processed"],
                "extraction_model": config.OPENAI_MODEL,
            },
        )
        logger.info("版本記録: %s", version_entry['version_id'])
        return

    total_files = len(md_files)
    logger.info("共 %d 份待處理", total_files)

    # 逐一處理
    newly_processed = 0

    for i, md_path in enumerate(md_files, 1):
        logger.info("[%d/%d]", i, total_files)

        try:
            result = process_single_meeting(md_path)
        except Exception as e:
            logger.error("     錯誤: %s", e)
            result = {"qa_pairs": [], "meeting_summary": f"處理失敗: {e}"}

        # 存單份結果（依來源目錄決定輸出位置）
        out_path = _canonical_qa_artifact_path(md_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        newly_processed += 1

        # 簡單的 rate limit 保護
        time.sleep(1)

    # 從所有 per-meeting 結果重建合併檔（包含增量前已處理的）
    merged_output = _rebuild_merged_from_per_meeting()

    merged_path = config.OUTPUT_DIR / "qa_all_raw.json"
    merged_path.write_text(
        json.dumps(merged_output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ── Layer 2: Version Registry ──────────────────────────────
    version_entry = record_artifact(
        step=2,
        data=merged_output,
        metadata={
            "qa_count": merged_output["total_qa_count"],
            "meetings_processed": merged_output["meetings_processed"],
            "extraction_model": config.OPENAI_MODEL,
        },
    )
    logger.info("版本記録: %s", version_entry['version_id'])

    logger.info("步驟 2 完成")
    logger.info("本次處理: %d 份", newly_processed)
    logger.info("總計 Q&A: %d 個", merged_output['total_qa_count'])
    logger.info("單份結果: %s", config.QA_PER_MEETING_DIR)
    logger.info("合併結果: %s", merged_path)

    flush_laminar()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="用 OpenAI 萃取 Q&A")
    parser.add_argument("--limit", type=int, default=0, help="只處理前 N 份")
    parser.add_argument("--file", default="", help="只處理指定檔案名稱")
    parser.add_argument("--force", action="store_true", help="強制重新處理所有檔案（忽略已完成的）")
    parser.add_argument("--check", action="store_true", help="只執行依賴檢查，不實際執行")
    args = parser.parse_args()
    main(args)
