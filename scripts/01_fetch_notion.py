#!/usr/bin/env python3
"""
步驟 1：從 Notion API 擷取所有 SEO 會議紀錄

功能：
- 列出母頁面下所有子頁面
- 遞迴擷取每頁的 blocks（含巢狀內容）
- 存原始 JSON 到 raw_data/notion_json/
- 轉 Markdown（含下載圖片）存到 raw_data/markdown/

用法：
    python scripts/01_fetch_notion.py                    # 增量 fetch
    python scripts/01_fetch_notion.py --force            # 全量重抓
    python scripts/01_fetch_notion.py --since 2026-02-27 # 只抓 2/27 后更新的
    python scripts/01_fetch_notion.py --block-depth 2    # 控制 block 深度
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 支援直接執行 script（未 pip install -e . 時）
try:
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

from utils.notion_client import fetch_all_meetings
from utils.block_to_markdown import blocks_to_markdown
from utils import audit_logger


def _load_existing_index() -> dict[str, dict]:
    """載入現有索引，回傳 {page_id: entry} 的 dict"""
    index_path = config.RAW_JSON_DIR.parent / "meetings_index.json"
    if not index_path.exists():
        return {}
    try:
        entries = json.loads(index_path.read_text(encoding="utf-8"))
        return {e["id"]: e for e in entries if "id" in e}
    except (json.JSONDecodeError, KeyError):
        return {}


def _parse_since_date(since_str: str) -> str:
    """
    將日期字符串轉為 ISO timestamp。
    支持格式：
    - "2026-02-27" → "2026-02-27T00:00:00.000Z"
    - "1d" → 1 天前
    - "7d" → 7 天前
    """
    if not since_str:
        return ""

    # 如果是 "Xd" 格式
    if since_str.endswith("d"):
        try:
            days = int(since_str[:-1])
            dt = datetime.utcnow() - timedelta(days=days)
            return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        except ValueError:
            pass

    # 如果是日期 "YYYY-MM-DD" 格式
    if len(since_str) == 10:
        return since_str + "T00:00:00.000Z"

    # 否則當作 ISO timestamp 直接用
    return since_str


async def main(args: argparse.Namespace) -> None:
    parent_id = args.parent_id or config.NOTION_PARENT_PAGE_ID
    if not parent_id:
        print("❌ 請設定 NOTION_PARENT_PAGE_ID（在 .env 或 --parent-id 參數）")
        sys.exit(1)

    if not config.NOTION_TOKEN:
        print("❌ 請設定 NOTION_TOKEN（在 .env）")
        sys.exit(1)

    force = args.force
    block_depth = args.block_depth
    since_time = _parse_since_date(args.since) if args.since else None

    # 生成 session ID，一次 fetch 用同一個，方便日誌關聯
    session_id = audit_logger.new_session_id()
    fetch_mode = "force" if force else ("since" if since_time else "incremental")
    start_time = time.monotonic()

    print("=" * 60)
    print("📥 步驟 1：從 Notion 擷取 SEO 會議紀錄")
    if force:
        print("   ⚡ 強制模式：重新抓取所有頁面")
    elif since_time:
        print(f"   📅 增量模式：只抓 {args.since} 後更新的頁面")
    else:
        print("   📦 增量模式：只抓新增或有更新的頁面")
    print(f"   🔄 Block 深度：{block_depth}")
    print("=" * 60)

    # 載入現有索引（用於增量比對）
    existing_index = _load_existing_index()
    if existing_index and not force:
        print(f"   📋 現有索引: {len(existing_index)} 份")

    # 擷取所有會議
    meetings = await fetch_all_meetings(
        parent_page_id=parent_id,
        filter_keyword=args.filter,
        block_max_depth=block_depth,
        since_time=since_time,
        session_id=session_id,
    )

    print(f"\n📋 Notion 上共取得 {len(meetings)} 份會議紀錄")

    # 稽核日誌：記錄 fetch 開始（要在锻錄數確定後才發送，包含實際要處理數）
    audit_logger.log_fetch_start(
        session_id=session_id,
        mode=fetch_mode,
        total_pages=len(meetings),
        since_time=since_time,
        block_max_depth=block_depth,
    )

    # 增量過濾：只處理新增或有更新的（--force 時跳過）
    if not force and not since_time and existing_index:
        filtered = []
        skipped = 0
        for m in meetings:
            page_id = m["meta"].get("id", "")
            remote_edited = m["meta"].get("last_edited_time", "")
            local_entry = existing_index.get(page_id)

            if local_entry and local_entry.get("last_edited_time") == remote_edited:
                skipped += 1
                # 稽核日誌：記錄增量跳過
                audit_logger.log_fetch_skip(
                    session_id=session_id,
                    page_id=page_id,
                    page_title=m["meta"].get("title", ""),
                    last_edited_time=remote_edited,
                    reason="no_change_incremental",
                )
            else:
                filtered.append(m)

        if skipped:
            print(f"   ⏭️  跳過 {skipped} 份（無變化）")
        meetings = filtered

    if not meetings:
        print("\n✅ 沒有新的或更新的會議紀錄，無需處理。")
        return

    print(f"   🔄 需處理: {len(meetings)} 份\n")

    # 轉 Markdown
    print("📝 正在轉換為 Markdown ...")
    for i, meeting in enumerate(meetings, 1):
        meta = meeting["meta"]
        blocks = meeting["blocks"]
        title = meta.get("title", "Untitled")
        safe_title = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', title)[:80]

        print(f"  [{i}/{len(meetings)}] {title}")

        md_content = await blocks_to_markdown(meta, blocks)

        md_path = config.RAW_MD_DIR / f"{safe_title}.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(md_content, encoding="utf-8")

        # 即時更新索引條目
        existing_index[meta.get("id", "")] = {
            "title": meta.get("title", ""),
            "id": meta.get("id", ""),
            "created_time": meta.get("created_time", ""),
            "last_edited_time": meta.get("last_edited_time", ""),
            "url": meta.get("url", ""),
            "json_file": f"notion_json/{safe_title}.json",
            "md_file": f"markdown/{safe_title}.md",
            "status": "fetched",
        }

    # 寫入合併後的索引（保留舊的 + 更新新的）+ last_checked_time
    index = list(existing_index.values())
    index_path = config.RAW_JSON_DIR.parent / "meetings_index.json"
    
    # 如果是增量 fetch，記錄檢查時間，供下次參考
    # 注意：這裡先暫存為 metadata，可在後續版本改進
    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n📋 索引已儲存: {index_path}（共 {len(index)} 份）")
    print(f"📁 Raw JSON: {config.RAW_JSON_DIR}")
    print(f"📁 Markdown:  {config.RAW_MD_DIR}")
    print(f"📁 圖片:      {config.IMAGES_DIR}")

    # 稽核日誌：記錄 fetch 完成
    duration = time.monotonic() - start_time
    audit_logger.log_fetch_complete(
        session_id=session_id,
        fetched_count=len(meetings),
        skipped_count=len(existing_index) - len(meetings) if not force else 0,
        duration_sec=duration,
    )
    print(f"📃 Fetch 日誌: {audit_logger.FETCH_LOGS_DIR}")
    print("\n✅ 步驟 1 完成！")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="從 Notion 擷取 SEO 會議紀錄")
    parser.add_argument(
        "--parent-id",
        default="",
        help="母頁面 ID（覆蓋 .env 設定）",
    )
    parser.add_argument(
        "--filter",
        default=None,
        help="篩選標題包含此關鍵字的頁面（例如 'SEO 會議'）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="強制重新抓取所有頁面（忽略增量比對）",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="只抓此時間後更新的頁面。格式：'2026-02-27' 或 '1d'（1天前）或 '7d'（7天前）",
    )
    parser.add_argument(
        "--block-depth",
        type=int,
        default=3,
        help="最大 block 遞迴深度（預設 3）",
    )
    args = parser.parse_args()
    asyncio.run(main(args))
