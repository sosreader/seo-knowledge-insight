#!/usr/bin/env python3
"""
meeting_prep_helper.py — 顧問會議準備輔助腳本

子命令：
  list-consultant-articles  掃描 medium_markdown，去重，輸出顧問文章清單
  extract-recent-topics     從最近 N 份會議抽取主題詞
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEDIUM_MD_DIR = PROJECT_ROOT / "raw_data" / "medium_markdown"
RAW_MD_DIR = PROJECT_ROOT / "raw_data" / "markdown"
QA_PER_MEETING_DIR = PROJECT_ROOT / "output" / "qa_per_meeting"

# 重複版本模式：檔名末尾 _1.md, _2.md 等（限 1-2 位數，避免誤判年份）
DUPLICATE_SUFFIX_RE = re.compile(r"_\d{1,2}\.md$")


def _is_duplicate_version(filename: str) -> bool:
    """判斷檔案是否為重複版本（如 article_1.md, article_2.md）。"""
    return bool(DUPLICATE_SUFFIX_RE.search(filename))


def _clean_title(filename: str) -> str:
    """從檔名還原文章標題（去底線、去副檔名）。"""
    name = Path(filename).stem
    # 移除末尾的 _Gene_Hong_還是黑貘 等作者標記
    name = re.sub(r"_-_Gene_Hong.*$", "", name)
    return name.replace("_", " ").strip()


def cmd_list_consultant_articles(args: argparse.Namespace) -> None:
    """掃描 medium_markdown，去重，輸出顧問文章清單。"""
    if not MEDIUM_MD_DIR.exists():
        logger.error("目錄不存在：%s", MEDIUM_MD_DIR)
        sys.exit(1)

    query = getattr(args, "query", None)
    output_json = getattr(args, "json", False)

    all_files = sorted(MEDIUM_MD_DIR.glob("*.md"))
    # 過濾重複版本
    unique_files = [f for f in all_files if not _is_duplicate_version(f.name)]

    # 若有 query，做關鍵字篩選
    if query:
        query_lower = query.lower()
        filtered = [
            f for f in unique_files
            if query_lower in f.name.lower()
            or query_lower in _clean_title(f.name).lower()
        ]
    else:
        filtered = unique_files

    if output_json:
        items = [
            {
                "filename": f.name,
                "title": _clean_title(f.name),
                "size_bytes": f.stat().st_size,
                "path": str(f),
            }
            for f in filtered
        ]
        result = {
            "total": len(items),
            "total_before_dedup": len(all_files),
            "duplicates_removed": len(all_files) - len(unique_files),
            "query": query,
            "items": items,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"顧問文章清單（共 {len(filtered)} 篇，已去除 {len(all_files) - len(unique_files)} 篇重複）")
    if query:
        print(f"篩選條件：{query}")
    print()

    for f in filtered:
        title = _clean_title(f.name)
        size_kb = f.stat().st_size / 1024
        print(f"  {title[:70]:<72s} {size_kb:>6.1f} KB")
        print(f"    → {f.name}")
        print()


def cmd_extract_recent_topics(args: argparse.Namespace) -> None:
    """從最近 N 份會議的 Q&A 中抽取主題詞。"""
    n = getattr(args, "n", 3)
    output_json = getattr(args, "json", False)

    # 嘗試從 qa_per_meeting 目錄讀取
    if QA_PER_MEETING_DIR.exists():
        meeting_files = sorted(
            QA_PER_MEETING_DIR.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
    else:
        meeting_files = []

    # Fallback: 從 raw_data/markdown 讀取會議紀錄
    if not meeting_files and RAW_MD_DIR.exists():
        meeting_files = sorted(
            RAW_MD_DIR.glob("*.md"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

    if not meeting_files:
        logger.error("找不到會議紀錄或 Q&A 檔案。")
        sys.exit(1)

    recent = meeting_files[:n]
    topic_counter: Counter[str] = Counter()
    meeting_topics: list[dict] = []

    for f in recent:
        keywords: list[str] = []
        if f.suffix == ".json":
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                qas = data.get("qa_pairs", data.get("qa_database", []))
                for qa in qas:
                    keywords.extend(qa.get("keywords", []))
            except (json.JSONDecodeError, KeyError):
                continue
        else:
            # Markdown: 簡單抽取標題詞
            content = f.read_text(encoding="utf-8")
            for line in content.splitlines():
                if line.startswith("#"):
                    words = re.findall(r"[\w\u4e00-\u9fff]+", line)
                    keywords.extend(w for w in words if len(w) > 1)

        topic_counter.update(kw.lower() for kw in keywords)
        meeting_topics.append({
            "file": f.name,
            "keyword_count": len(keywords),
            "top_keywords": [kw for kw, _ in Counter(keywords).most_common(5)],
        })

    top_topics = topic_counter.most_common(20)

    if output_json:
        result = {
            "recent_meetings": n,
            "files_analyzed": len(recent),
            "top_topics": [{"topic": t, "count": c} for t, c in top_topics],
            "per_meeting": meeting_topics,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"最近 {len(recent)} 份會議的主題詞（共 {len(top_topics)} 個）：\n")
    for rank, (topic, count) in enumerate(top_topics, 1):
        print(f"  [{rank:2d}] {topic:<30s} (出現 {count} 次)")

    print("\n各會議明細：")
    for mt in meeting_topics:
        print(f"  {mt['file']}: {', '.join(mt['top_keywords'][:5])}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="meeting_prep_helper.py — 顧問會議準備輔助腳本"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser(
        "list-consultant-articles",
        help="掃描 medium_markdown，去重，輸出顧問文章清單",
    )
    p_list.add_argument("--query", help="關鍵字篩選")
    p_list.add_argument("--json", action="store_true", help="輸出 JSON 格式")

    p_topics = sub.add_parser(
        "extract-recent-topics",
        help="從最近 N 份會議抽取主題詞",
    )
    p_topics.add_argument("--n", type=int, default=3, help="最近 N 份（預設 3）")
    p_topics.add_argument("--json", action="store_true", help="輸出 JSON 格式")

    args = parser.parse_args()

    dispatch = {
        "list-consultant-articles": cmd_list_consultant_articles,
        "extract-recent-topics": cmd_extract_recent_topics,
    }

    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
