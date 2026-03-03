"""
notion_url_map.py — 建立 source_file → Notion URL 映射

從 raw_data/meetings_index.json 讀取會議索引，
建立 md_file（去除 markdown/ 前綴）→ Notion URL 的映射。

Fallback：若 meetings_index.json 不存在，遍歷 raw_data/markdown/*.md
         從 Markdown 檔案開頭的 metadata 擷取 Notion URL。
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_INDEX_PATH = _ROOT / "raw_data" / "meetings_index.json"
_MARKDOWN_DIR = _ROOT / "raw_data" / "markdown"

_NOTION_URL_RE = re.compile(r"https://www\.notion\.so/[\w\-]+(?:/[\w\-]+)*")


def _validate_notion_url(url: str) -> bool:
    """驗證 URL 是否為合法的 Notion URL（scheme + domain + 非空 path）。"""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.netloc == "www.notion.so"
        and bool(parsed.path.strip("/"))
    )


def _build_from_index(index_path: Path) -> dict[str, str]:
    """從 meetings_index.json 建立 source_file → Notion URL 映射。"""
    try:
        raw = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("meetings_index.json 讀取失敗：%s", exc)
        return {}
    if not isinstance(raw, list):
        logger.warning("meetings_index.json 格式錯誤：預期 list，得到 %s", type(raw).__name__)
        return {}
    mapping: dict[str, str] = {}
    for entry in raw:
        md_file = entry.get("md_file", "")
        url = entry.get("url", "")
        if not md_file or not url:
            continue
        # md_file 格式："markdown/SEO_會議_2024_05_02.md" → "SEO_會議_2024_05_02.md"
        filename = md_file.replace("markdown/", "", 1)
        if _validate_notion_url(url):
            mapping[filename] = url
        else:
            logger.warning("無效 Notion URL（跳過）：%s → %s", filename, url)
    return mapping


def _build_from_markdown(markdown_dir: Path) -> dict[str, str]:
    """Fallback：遍歷 Markdown 檔案，從 metadata 擷取 Notion URL。"""
    mapping: dict[str, str] = {}
    if not markdown_dir.exists():
        return mapping
    for md_file in sorted(markdown_dir.glob("*.md")):
        # 只讀前 10 行（metadata 通常在最前面）
        try:
            lines = md_file.read_text(encoding="utf-8").splitlines()[:10]
        except OSError as exc:
            logger.warning("讀取失敗（跳過）：%s — %s", md_file.name, exc)
            continue
        for line in lines:
            match = _NOTION_URL_RE.search(line)
            if match:
                url = match.group(0)
                if _validate_notion_url(url):
                    mapping[md_file.name] = url
                break
    return mapping


def build_source_to_notion_url(
    index_path: Path = _INDEX_PATH,
    markdown_dir: Path = _MARKDOWN_DIR,
) -> dict[str, str]:
    """
    建立 source_file → Notion URL 映射。

    優先使用 meetings_index.json（完整且結構化）。
    若不存在，fallback 到遍歷 markdown 檔案 metadata。

    Args:
        index_path:   meetings_index.json 路徑
        markdown_dir: raw_data/markdown/ 目錄路徑

    Returns:
        dict[str, str]：{source_file: notion_url}
    """
    if index_path.exists():
        mapping = _build_from_index(index_path)
        logger.info(
            "Notion URL 映射：從 %s 載入 %d 筆",
            index_path.name,
            len(mapping),
        )
        return mapping

    logger.warning(
        "%s 不存在，fallback 到 Markdown metadata 擷取",
        index_path,
    )
    mapping = _build_from_markdown(markdown_dir)
    logger.info("Notion URL 映射：從 Markdown 擷取 %d 筆", len(mapping))
    return mapping
