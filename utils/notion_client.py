"""
Notion API 封裝
- 列出母頁面下所有子頁面
- 遞迴讀取頁面的所有 blocks（含巢狀）
- 下載圖片到本地
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

import config


# ──────────────────────────────────────────────────────
# 低層 API 呼叫
# ──────────────────────────────────────────────────────

def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.NOTION_TOKEN}",
        "Notion-Version": config.NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


async def _api_get(
    client: httpx.AsyncClient,
    url: str,
    params: dict | None = None,
    retries: int = 3,
) -> dict:
    """帶重試的 GET 請求"""
    for attempt in range(retries):
        try:
            resp = await client.get(url, headers=_headers(), params=params)
            if resp.status_code == 429:
                wait = float(resp.headers.get("Retry-After", 2))
                print(f"  ⏳ Rate limited, waiting {wait}s ...")
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if attempt == retries - 1:
                raise
            print(f"  ⚠️  HTTP {e.response.status_code}, retrying ({attempt+1}/{retries}) ...")
            await asyncio.sleep(1.5 ** attempt)
    return {}


async def _api_post(
    client: httpx.AsyncClient,
    url: str,
    body: dict | None = None,
    retries: int = 3,
) -> dict:
    """帶重試的 POST 請求"""
    for attempt in range(retries):
        try:
            resp = await client.post(url, headers=_headers(), json=body or {})
            if resp.status_code == 429:
                wait = float(resp.headers.get("Retry-After", 2))
                print(f"  ⏳ Rate limited, waiting {wait}s ...")
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if attempt == retries - 1:
                raise
            print(f"  ⚠️  HTTP {e.response.status_code}, retrying ({attempt+1}/{retries}) ...")
            await asyncio.sleep(1.5 ** attempt)
    return {}


# ──────────────────────────────────────────────────────
# 頁面列表
# ──────────────────────────────────────────────────────

async def list_child_pages(
    client: httpx.AsyncClient,
    parent_page_id: str,
) -> list[dict[str, str]]:
    """
    列出 parent_page_id 下所有 child_page 類型的 block，
    回傳 [{id, title}]
    """
    pages: list[dict[str, str]] = []
    url = f"{config.NOTION_BASE_URL}/blocks/{parent_page_id}/children"
    cursor: str | None = None

    while True:
        params: dict[str, Any] = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor

        data = await _api_get(client, url, params)
        for block in data.get("results", []):
            if block.get("type") == "child_page":
                title = block["child_page"]["title"]
                pages.append({"id": block["id"], "title": title})

        if data.get("has_more"):
            cursor = data["next_cursor"]
        else:
            break

    return pages


# ──────────────────────────────────────────────────────
# 遞迴讀取 Blocks
# ──────────────────────────────────────────────────────

async def fetch_blocks_recursive(
    client: httpx.AsyncClient,
    block_id: str,
    depth: int = 0,
    max_depth: int = 10,
) -> list[dict]:
    """
    遞迴取得 block 底下所有 children（含巢狀 block）。
    每個 block dict 會新增 "children_blocks" 鍵。
    """
    if depth > max_depth:
        return []

    all_blocks: list[dict] = []
    url = f"{config.NOTION_BASE_URL}/blocks/{block_id}/children"
    cursor: str | None = None

    while True:
        params: dict[str, Any] = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor

        data = await _api_get(client, url, params)

        for block in data.get("results", []):
            # 如果這個 block 有 children，遞迴抓取
            if block.get("has_children"):
                children = await fetch_blocks_recursive(
                    client, block["id"], depth + 1, max_depth
                )
                block["children_blocks"] = children
            else:
                block["children_blocks"] = []
            all_blocks.append(block)

        if data.get("has_more"):
            cursor = data["next_cursor"]
        else:
            break

    return all_blocks


# ──────────────────────────────────────────────────────
# 取得頁面屬性（標題、建立時間等）
# ──────────────────────────────────────────────────────

async def fetch_page_meta(
    client: httpx.AsyncClient,
    page_id: str,
) -> dict:
    """取得頁面 meta：標題、建立/更新時間"""
    url = f"{config.NOTION_BASE_URL}/pages/{page_id}"
    data = await _api_get(client, url)

    # 從 properties 裡找 title
    title = ""
    for prop in data.get("properties", {}).values():
        if prop.get("type") == "title":
            title = "".join(
                t.get("plain_text", "") for t in prop.get("title", [])
            )
            break

    return {
        "id": data.get("id", page_id),
        "title": title,
        "created_time": data.get("created_time", ""),
        "last_edited_time": data.get("last_edited_time", ""),
        "url": data.get("url", ""),
    }


# ──────────────────────────────────────────────────────
# 下載圖片
# ──────────────────────────────────────────────────────

async def download_image(
    client: httpx.AsyncClient,
    image_url: str,
    dest_dir: Path,
) -> str:
    """
    下載圖片到本地，回傳相對路徑。
    用 URL hash 做檔名以避免重複下載。
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    # 用 hash 做穩定檔名
    url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
    # 嘗試從 URL 取得副檔名
    ext = ".png"
    match = re.search(r"\.(png|jpg|jpeg|gif|webp|svg)", image_url, re.IGNORECASE)
    if match:
        ext = f".{match.group(1).lower()}"
    filename = f"{url_hash}{ext}"
    filepath = dest_dir / filename

    if filepath.exists():
        return filename

    try:
        resp = await client.get(image_url, follow_redirects=True, timeout=30.0)
        resp.raise_for_status()
        filepath.write_bytes(resp.content)
        return filename
    except Exception as e:
        print(f"  ⚠️  Failed to download image: {e}")
        return f"[DOWNLOAD_FAILED: {image_url}]"


# ──────────────────────────────────────────────────────
# 高層：抓取整個母頁面下的所有會議紀錄
# ──────────────────────────────────────────────────────

async def fetch_all_meetings(
    parent_page_id: str | None = None,
    filter_keyword: str | None = None,
) -> list[dict]:
    """
    主入口：列出母頁面下所有子頁面，逐一抓取完整 blocks 並存為 JSON。
    
    回傳：[{meta: {...}, blocks: [...]}]
    """
    parent_id = parent_page_id or config.NOTION_PARENT_PAGE_ID
    if not parent_id:
        raise ValueError("請設定 NOTION_PARENT_PAGE_ID（在 .env 或參數傳入）")

    results: list[dict] = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        print("📋 正在列出子頁面 ...")
        child_pages = await list_child_pages(client, parent_id)
        print(f"   找到 {len(child_pages)} 個子頁面")

        # 過濾（可選）
        if filter_keyword:
            child_pages = [
                p for p in child_pages
                if filter_keyword in p["title"]
            ]
            print(f"   篩選後剩 {len(child_pages)} 個（含 '{filter_keyword}'）")

        for i, page in enumerate(child_pages, 1):
            page_id = page["id"]
            title = page["title"]
            print(f"\n[{i}/{len(child_pages)}] 📄 {title}")

            # 取得 meta
            meta = await fetch_page_meta(client, page_id)

            # 取得完整 blocks
            print(f"  ↳ 正在讀取 blocks ...")
            blocks = await fetch_blocks_recursive(client, page_id)
            print(f"  ↳ 共 {len(blocks)} 個頂層 blocks")

            record = {"meta": meta, "blocks": blocks}
            results.append(record)

            # 存原始 JSON
            safe_title = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', title)[:80]
            json_path = config.RAW_JSON_DIR / f"{safe_title}.json"
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(
                json.dumps(record, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"  ↳ 已存: {json_path.name}")

            # 避免打太快
            await asyncio.sleep(0.3)

    return results
