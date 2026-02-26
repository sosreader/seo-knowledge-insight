#!/usr/bin/env python3
"""
步驟 1：從 Notion API 擷取所有 SEO 會議紀錄

功能：
- 列出母頁面下所有子頁面
- 遞迴擷取每頁的 blocks（含巢狀內容）
- 存原始 JSON 到 raw_data/notion_json/
- 轉 Markdown（含下載圖片）存到 raw_data/markdown/

用法：
    python scripts/01_fetch_notion.py
    python scripts/01_fetch_notion.py --filter "SEO 會議"
    python scripts/01_fetch_notion.py --parent-id xxxxx
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

# 把專案根目錄加到 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from utils.notion_client import fetch_all_meetings
from utils.block_to_markdown import blocks_to_markdown


async def main(args: argparse.Namespace) -> None:
    parent_id = args.parent_id or config.NOTION_PARENT_PAGE_ID
    if not parent_id:
        print("❌ 請設定 NOTION_PARENT_PAGE_ID（在 .env 或 --parent-id 參數）")
        sys.exit(1)

    if not config.NOTION_TOKEN:
        print("❌ 請設定 NOTION_TOKEN（在 .env）")
        sys.exit(1)

    print("=" * 60)
    print("📥 步驟 1：從 Notion 擷取 SEO 會議紀錄")
    print("=" * 60)

    # 擷取所有會議
    meetings = await fetch_all_meetings(
        parent_page_id=parent_id,
        filter_keyword=args.filter,
    )

    print(f"\n✅ 共擷取 {len(meetings)} 份會議紀錄")

    # 轉 Markdown
    print("\n📝 正在轉換為 Markdown ...")
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

    # 建立索引
    index = []
    for meeting in meetings:
        meta = meeting["meta"]
        safe_title = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', meta.get("title", "Untitled"))[:80]
        index.append({
            "title": meta.get("title", ""),
            "id": meta.get("id", ""),
            "created_time": meta.get("created_time", ""),
            "last_edited_time": meta.get("last_edited_time", ""),
            "url": meta.get("url", ""),
            "json_file": f"notion_json/{safe_title}.json",
            "md_file": f"markdown/{safe_title}.md",
        })

    index_path = config.RAW_JSON_DIR.parent / "meetings_index.json"
    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\n📋 索引已儲存: {index_path}")
    print(f"📁 Raw JSON: {config.RAW_JSON_DIR}")
    print(f"📁 Markdown:  {config.RAW_MD_DIR}")
    print(f"📁 圖片:      {config.IMAGES_DIR}")
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
    args = parser.parse_args()
    asyncio.run(main(args))
