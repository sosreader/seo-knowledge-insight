"""
Notion Block → Markdown 轉換器

支援的 block 類型：
- paragraph, heading_1/2/3
- bulleted_list_item, numbered_list_item, to_do
- code, quote, callout, divider
- image（下載到本地）
- toggle, table, column_list
- bookmark, embed, link_preview
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx

import config
from utils.notion_client import download_image


# ──────────────────────────────────────────────────────
# Rich Text → plain / markdown text
# ──────────────────────────────────────────────────────

def _rich_text_to_md(rich_texts: list[dict]) -> str:
    """把 Notion rich_text 陣列轉成 Markdown 字串"""
    parts: list[str] = []
    for rt in rich_texts:
        text = rt.get("plain_text", "")
        annot = rt.get("annotations", {})

        # 套用格式
        if annot.get("code"):
            text = f"`{text}`"
        if annot.get("bold"):
            text = f"**{text}**"
        if annot.get("italic"):
            text = f"*{text}*"
        if annot.get("strikethrough"):
            text = f"~~{text}~~"
        if annot.get("underline"):
            text = f"<u>{text}</u>"

        # 連結
        href = rt.get("href") or (rt.get("text", {}) or {}).get("link", {})
        if isinstance(href, dict):
            href = href.get("url")
        if href:
            text = f"[{text}]({href})"

        parts.append(text)
    return "".join(parts)


# ──────────────────────────────────────────────────────
# 單個 Block → Markdown
# ──────────────────────────────────────────────────────

async def _block_to_md(
    block: dict,
    client: httpx.AsyncClient,
    images_dir: Path,
    indent: int = 0,
    list_counter: dict | None = None,
) -> str:
    """把單個 block 轉成 Markdown 文字，回傳一行或多行"""
    btype = block.get("type", "")
    prefix = "  " * indent  # 巢狀的縮排
    content = block.get(btype, {})

    lines: list[str] = []

    # ── 文字類 ──
    if btype == "paragraph":
        text = _rich_text_to_md(content.get("rich_text", []))
        lines.append(f"{prefix}{text}")

    elif btype.startswith("heading_"):
        level = int(btype[-1])
        text = _rich_text_to_md(content.get("rich_text", []))
        lines.append(f"{'#' * level} {text}")

    elif btype == "bulleted_list_item":
        text = _rich_text_to_md(content.get("rich_text", []))
        lines.append(f"{prefix}- {text}")

    elif btype == "numbered_list_item":
        text = _rich_text_to_md(content.get("rich_text", []))
        # 用簡單的 1. 即可，Markdown 會自動排序
        lines.append(f"{prefix}1. {text}")

    elif btype == "to_do":
        text = _rich_text_to_md(content.get("rich_text", []))
        checked = "x" if content.get("checked") else " "
        lines.append(f"{prefix}- [{checked}] {text}")

    elif btype == "quote":
        text = _rich_text_to_md(content.get("rich_text", []))
        for line in text.split("\n"):
            lines.append(f"{prefix}> {line}")

    elif btype == "callout":
        icon = ""
        icon_data = content.get("icon", {})
        if icon_data.get("type") == "emoji":
            icon = icon_data.get("emoji", "") + " "
        text = _rich_text_to_md(content.get("rich_text", []))
        lines.append(f"{prefix}> {icon}{text}")

    elif btype == "code":
        text = _rich_text_to_md(content.get("rich_text", []))
        lang = content.get("language", "")
        lines.append(f"{prefix}```{lang}")
        lines.append(text)
        lines.append(f"{prefix}```")

    elif btype == "divider":
        lines.append(f"{prefix}---")

    elif btype == "toggle":
        text = _rich_text_to_md(content.get("rich_text", []))
        lines.append(f"{prefix}<details>")
        lines.append(f"{prefix}<summary>{text}</summary>")
        lines.append(f"{prefix}</details>")

    # ── 圖片 ──
    elif btype == "image":
        img_type = content.get("type", "")
        img_url = ""
        if img_type == "file":
            img_url = content.get("file", {}).get("url", "")
        elif img_type == "external":
            img_url = content.get("external", {}).get("url", "")

        if img_url:
            local_name = await download_image(client, img_url, images_dir)
            caption_text = _rich_text_to_md(content.get("caption", []))
            alt = caption_text or "image"
            lines.append(f"{prefix}![{alt}](../images/{local_name})")
            if caption_text:
                lines.append(f"{prefix}*{caption_text}*")
        else:
            lines.append(f"{prefix}[圖片無法取得]")

    # ── 表格 ──
    elif btype == "table":
        children = block.get("children_blocks", [])
        if children:
            for row_i, row_block in enumerate(children):
                if row_block.get("type") == "table_row":
                    cells = row_block.get("table_row", {}).get("cells", [])
                    row_text = " | ".join(
                        _rich_text_to_md(cell) for cell in cells
                    )
                    lines.append(f"{prefix}| {row_text} |")
                    # 表頭分隔線
                    if row_i == 0:
                        sep = " | ".join("---" for _ in cells)
                        lines.append(f"{prefix}| {sep} |")

    # ── 嵌入類 ──
    elif btype == "bookmark":
        url = content.get("url", "")
        caption = _rich_text_to_md(content.get("caption", []))
        label = caption or url
        lines.append(f"{prefix}🔗 [{label}]({url})")

    elif btype in ("embed", "link_preview"):
        url = content.get("url", "")
        lines.append(f"{prefix}🔗 {url}")

    elif btype == "video":
        vid_type = content.get("type", "")
        vid_url = ""
        if vid_type == "external":
            vid_url = content.get("external", {}).get("url", "")
        elif vid_type == "file":
            vid_url = content.get("file", {}).get("url", "")
        lines.append(f"{prefix}🎬 影片: {vid_url}")

    elif btype == "file":
        file_type = content.get("type", "")
        file_url = ""
        if file_type == "file":
            file_url = content.get("file", {}).get("url", "")
        elif file_type == "external":
            file_url = content.get("external", {}).get("url", "")
        caption = _rich_text_to_md(content.get("caption", []))
        label = caption or "附件"
        lines.append(f"{prefix}📎 [{label}]({file_url})")

    elif btype == "child_page":
        title = content.get("title", "")
        lines.append(f"{prefix}📄 子頁面: {title}")

    elif btype == "child_database":
        title = content.get("title", "")
        lines.append(f"{prefix}📊 子資料庫: {title}")

    # ── 未知類型紀錄 ──
    else:
        lines.append(f"{prefix}<!-- unsupported block type: {btype} -->")

    # ── 處理巢狀 children ──
    children = block.get("children_blocks", [])
    if children and btype != "table":  # table 已在上面處理
        for child in children:
            child_md = await _block_to_md(
                child, client, images_dir, indent + 1
            )
            lines.append(child_md)

    return "\n".join(lines)


# ──────────────────────────────────────────────────────
# 整份會議 → Markdown
# ──────────────────────────────────────────────────────

async def blocks_to_markdown(
    meta: dict,
    blocks: list[dict],
    images_dir: Path | None = None,
) -> str:
    """
    把一份會議的 meta + blocks 轉成完整的 Markdown 文件。
    """
    images_dir = images_dir or config.IMAGES_DIR

    md_parts: list[str] = []

    # 前言 metadata
    md_parts.append(f"# {meta.get('title', 'Untitled')}")
    md_parts.append("")
    md_parts.append(f"- **會議日期**: {meta.get('meeting_date', meta.get('created_time', 'N/A'))[:10]}")
    md_parts.append(f"- **建立時間**: {meta.get('created_time', 'N/A')}")
    md_parts.append(f"- **最後編輯**: {meta.get('last_edited_time', 'N/A')}")
    md_parts.append(f"- **Notion URL**: {meta.get('url', 'N/A')}")
    md_parts.append(f"- **Page ID**: {meta.get('id', 'N/A')}")
    md_parts.append("")
    md_parts.append("---")
    md_parts.append("")

    async with httpx.AsyncClient(timeout=30.0) as client:
        for block in blocks:
            block_md = await _block_to_md(block, client, images_dir)
            md_parts.append(block_md)
            md_parts.append("")  # 段落間空行

    return "\n".join(md_parts)


def blocks_to_markdown_sync(meta: dict, blocks: list[dict]) -> str:
    """同步版本的 blocks_to_markdown"""
    return asyncio.run(blocks_to_markdown(meta, blocks))
