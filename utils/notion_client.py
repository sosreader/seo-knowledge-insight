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
import logging
import re
import time
from pathlib import Path
from typing import Any

import httpx

import config
from utils import audit_logger

logger = logging.getLogger(__name__)


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
                logger.warning("Rate limited, waiting %ss ...", wait)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if attempt == retries - 1:
                raise
            logger.warning("HTTP %d, retrying (%d/%d) ...", e.response.status_code, attempt+1, retries)
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
                logger.warning("Rate limited, waiting %ss ...", wait)
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if attempt == retries - 1:
                raise
            logger.warning("HTTP %d, retrying (%d/%d) ...", e.response.status_code, attempt+1, retries)
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
    自動偵測 parent_page_id 是頁面還是資料庫：
    - 資料庫 → 用 POST /databases/{id}/query 查詢所有紀錄
    - 頁面 → 列出所有 child_page 類型 block
    回傳 [{id, title}]
    """
    # 先試資料庫 API
    db_url = f"{config.NOTION_BASE_URL}/databases/{parent_page_id}"
    db_check = await _api_get(client, db_url)

    if db_check.get("object") == "database":
        logger.info("偵測到資料庫，使用 Database Query API ...")
        return await _list_database_pages(client, parent_page_id)
    else:
        logger.info("偵測到頁面，使用 Blocks Children API ...")
        return await _list_page_children(client, parent_page_id)


async def _list_database_pages(
    client: httpx.AsyncClient,
    database_id: str,
) -> list[dict[str, str]]:
    """查詢資料庫中所有 page records"""
    pages: list[dict[str, str]] = []
    url = f"{config.NOTION_BASE_URL}/databases/{database_id}/query"
    cursor: str | None = None

    while True:
        body: dict[str, Any] = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor

        data = await _api_post(client, url, body)
        for record in data.get("results", []):
            if record.get("object") != "page":
                continue
            # 找 title 欄位
            title = ""
            for prop in record.get("properties", {}).values():
                if prop.get("type") == "title":
                    title = "".join(
                        t.get("plain_text", "") for t in prop.get("title", [])
                    )
                    break
            pages.append({"id": record["id"], "title": title or record["id"]})

        if data.get("has_more"):
            cursor = data["next_cursor"]
        else:
            break

    return pages


async def _list_page_children(
    client: httpx.AsyncClient,
    parent_page_id: str,
) -> list[dict[str, str]]:
    """列出頁面下所有 child_page 類型 block"""
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
    max_depth: int = 3,
) -> list[dict]:
    """
    遞迴取得 block 底下所有 children（含巢狀 block）。
    每個 block dict 會新增 "children_blocks" 鍵。
    404 表示 Integration 沒有該 block 的存取權，直接回傳空列表。
    
    Args:
        client: httpx AsyncClient
        block_id: 要讀取的 block ID
        depth: 當前遞迴深度
        max_depth: 最大遞迴深度（預設 3，減少 API 調用）
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

        try:
            data = await _api_get(client, url, params)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("跳過（無存取權）: %s", block_id)
                return []
            raise

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
    """取得頁面 meta：標題、建立/更新時間，也嘗試從資料庫 Date 欄位取得會議日期"""
    url = f"{config.NOTION_BASE_URL}/pages/{page_id}"
    data = await _api_get(client, url)

    title = ""
    meeting_date = ""

    for _, prop in data.get("properties", {}).items():
        ptype = prop.get("type", "")
        if ptype == "title":
            title = "".join(
                t.get("plain_text", "") for t in prop.get("title", [])
            )
        elif ptype == "date" and not meeting_date:
            date_val = prop.get("date") or {}
            meeting_date = date_val.get("start", "")
        elif ptype == "created_time" and not meeting_date:
            meeting_date = prop.get("created_time", "")

    return {
        "id": data.get("id", page_id),
        "title": title,
        "created_time": data.get("created_time", ""),
        "last_edited_time": data.get("last_edited_time", ""),
        "meeting_date": meeting_date or data.get("created_time", "")[:10],
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
        logger.warning("Failed to download image: %s", e)
        return f"[DOWNLOAD_FAILED: {image_url}]"


# ──────────────────────────────────────────────────────
# 高層：抓取整個母頁面下的所有會議紀錄
# ──────────────────────────────────────────────────────

async def fetch_all_meetings(
    parent_page_id: str | None = None,
    filter_keyword: str | None = None,
    block_max_depth: int = 3,
    since_time: str | None = None,
    session_id: str | None = None,
) -> list[dict]:
    """
    主入口：列出母頁面下所有子頁面，逐一抓取完整 blocks 並存為 JSON。
    
    Args:
        parent_page_id: 母頁面或資料庫 ID（覆蓋 config.NOTION_PARENT_PAGE_ID）
        filter_keyword: 篩選標題包含此關鍵字的頁面
        block_max_depth: 最大 block 遞迴深度（預設 3）
        since_time: ISO 時間戳（例如 "2026-02-27T00:00:00.000Z"），只抓此時間後更新的頁面
        session_id: 稽核日誌 session ID（由 01_fetch_notion.py 生成並傳入）
    
    回傳：[{meta: {...}, blocks: [...]}]
    """
    parent_id = parent_page_id or config.NOTION_PARENT_PAGE_ID
    if not parent_id:
        raise ValueError("請設定 NOTION_PARENT_PAGE_ID（在 .env 或參數傳入）")

    results: list[dict] = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        logger.info("正在列出子頁面 ...")
        child_pages = await list_child_pages(client, parent_id)
        logger.info("找到 %d 個子頁面", len(child_pages))

        # 篩選：關鍵字
        if filter_keyword:
            child_pages = [
                p for p in child_pages
                if filter_keyword in p["title"]
            ]
            logger.info("篩選後剩 %d 個（含 '%s'）", len(child_pages), filter_keyword)

        # 篩選：時間戳（如果指定）
        # 此時需要查詢 meta 來比對 last_edited_time，所以預先做過濾
        if since_time:
            logger.info("篩選：只抓 %s 後更新的頁面 ...", since_time)
            filtered = []
            for page in child_pages:
                meta = await fetch_page_meta(client, page["id"])
                if meta.get("last_edited_time", "") >= since_time:
                    filtered.append((page, meta))  # 儲存 meta 以避免重複查詢
                else:
                    logger.info("跳過 %s（未更新）", page['title'])
                    # 記錄跳過事件
                    if session_id:
                        audit_logger.log_fetch_skip(
                            session_id=session_id,
                            page_id=meta.get("id", page["id"]),
                            page_title=page["title"],
                            last_edited_time=meta.get("last_edited_time", ""),
                            reason="since_time_filter",
                        )
            child_pages = filtered
            logger.info("保留 %d 份", len(child_pages))
        else:
            # 沒有 since_time 過濾時，頁面中只有 id 和 title，meta 稍後查
            child_pages = [(p, None) for p in child_pages]

        for i, (page, cached_meta) in enumerate(child_pages, 1):
            page_id = page["id"]
            title = page["title"]
            logger.info("[%d/%d] %s", i, len(child_pages), title)

            # 取得 meta（使用快取或新查詢）
            if cached_meta:
                meta = cached_meta
            else:
                meta = await fetch_page_meta(client, page_id)

            # 取得完整 blocks
            logger.info("  正在讀取 blocks (max_depth=%d) ...", block_max_depth)
            blocks = await fetch_blocks_recursive(
                client, page_id, depth=0, max_depth=block_max_depth
            )
            logger.info("  共 %d 個頂層 blocks", len(blocks))

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
            logger.info("  已存: %s", json_path.name)

            # 稽核日誌：記錄成功 fetch 頁面
            if session_id:
                audit_logger.log_fetch_page(
                    session_id=session_id,
                    page_id=meta.get("id", ""),
                    page_title=title,
                    last_edited_time=meta.get("last_edited_time", ""),
                    block_count=len(blocks),
                )

            # 避免打太快
            await asyncio.sleep(0.3)

    return results
