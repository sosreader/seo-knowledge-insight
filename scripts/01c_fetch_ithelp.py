#!/usr/bin/env python3
"""
步驟 1c：從 iThome 鐵人賽擷取 Gene Hong 的 Search Console KPI 系列文章

功能：
- 從系列頁面解析所有文章 URL
- 逐篇抓取文章內容 HTML
- 轉換為 Markdown 存入 raw_data/ithelp_markdown/
- 更新 raw_data/ithelp_articles_index.json

rate limiting：每篇間隔 1-2 秒，避免被 iThome 封鎖。

用法：
    python scripts/01c_fetch_ithelp.py
    python scripts/01c_fetch_ithelp.py --force   # 重新擷取所有
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

try:
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

from utils.html_to_markdown import html_to_markdown, add_metadata_header


AUTHOR = "Gene Hong"
SOURCE_COLLECTION = "ithelp-sc-kpi"
INDEX_PATH = config.ROOT_DIR / "raw_data" / "ithelp_articles_index.json"

# iThome article page pattern
ARTICLE_URL_PATTERN = re.compile(r'href="(https://ithelp\.ithome\.com\.tw/articles/(\d+))"')
# Article content selector pattern
ARTICLE_CONTENT_PATTERN = re.compile(
    r'<div\s+class="qa-markdown"[^>]*>(.*?)</div>\s*(?=<div\s+class="(?:qa-footer|bottomBox|tags-group))',
    re.DOTALL,
)
ARTICLE_TITLE_PATTERN = re.compile(r'<h3[^>]*class="qa-header[^"]*"[^>]*>\s*(.*?)\s*</h3>', re.DOTALL)


def _load_index() -> list[dict]:
    """Load existing article index."""
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return []


def _save_index(index: list[dict]) -> None:
    """Save article index."""
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _fetch_series_article_urls(series_url: str) -> list[dict]:
    """Fetch all article URLs from the iThome series page (multi-page).

    Returns list of dicts with: article_id, url, day
    """
    articles = []
    seen_ids: set[str] = set()

    for page in range(1, 5):  # up to 4 pages (30 articles / ~10 per page)
        url = f"{series_url}?page={page}"
        print(f"  擷取系列頁面: {url}")

        try:
            resp = httpx.get(url, follow_redirects=True, timeout=30)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            print(f"  ⚠️  頁面 {page} 擷取失敗: {e}")
            break

        matches = ARTICLE_URL_PATTERN.findall(resp.text)
        new_count = 0
        for article_url, article_id in matches:
            if article_id not in seen_ids:
                seen_ids.add(article_id)
                articles.append({
                    "article_id": article_id,
                    "url": article_url,
                    "day": len(articles) + 1,
                })
                new_count += 1

        if new_count == 0:
            break  # No new articles on this page

        time.sleep(1)  # rate limiting between pages

    print(f"  找到 {len(articles)} 篇文章")
    return articles


def _fetch_article_content(url: str) -> dict:
    """Fetch a single iThome article and extract content.

    Returns dict with: title, html_content, published
    """
    resp = httpx.get(url, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    html = resp.text

    # Extract title
    title = "Untitled"
    title_match = ARTICLE_TITLE_PATTERN.search(html)
    if title_match:
        # Strip HTML tags from title
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()

    # Extract article content
    content_match = ARTICLE_CONTENT_PATTERN.search(html)
    html_content = content_match.group(1) if content_match else ""

    # Try to extract published date
    published = ""
    date_match = re.search(r'<span[^>]*class="ir-article-info__time"[^>]*>(\d{4}-\d{2}-\d{2})', html)
    if date_match:
        published = date_match.group(1)

    return {
        "title": title,
        "html_content": html_content,
        "published": published,
    }


def fetch_ithelp_articles(
    series_url: str = config.ITHELP_SERIES_URL,
    force: bool = False,
) -> dict:
    """Fetch iThome series articles and save as Markdown.

    Returns:
        {"fetched": int, "skipped": int, "total": int}
    """
    output_dir = config.RAW_ITHELP_MD_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    index = _load_index()
    existing_ids = {entry["article_id"] for entry in index}

    # Get all article URLs
    article_metas = _fetch_series_article_urls(series_url)

    fetched = 0
    skipped = 0

    for meta in article_metas:
        article_id = meta["article_id"]

        if not force and article_id in existing_ids:
            skipped += 1
            continue

        try:
            article = _fetch_article_content(meta["url"])
        except Exception as e:
            print(f"  ⚠️  Day {meta['day']} 擷取失敗: {e}")
            continue

        # Convert HTML to Markdown
        md_content = html_to_markdown(article["html_content"])

        # Clean title for filename
        safe_title = re.sub(r'[^\w\u4e00-\u9fff-]', '_', article["title"])[:60]
        filename = f"day{meta['day']:02d}_{safe_title}"

        # Add metadata header
        full_md = add_metadata_header(
            md_content,
            title=article["title"],
            published=article["published"],
            author=AUTHOR,
            source_url=meta["url"],
            source_type="article",
            source_collection=SOURCE_COLLECTION,
        )

        md_path = output_dir / f"{filename}.md"
        md_path.write_text(full_md, encoding="utf-8")

        # Update index
        index_entry = {
            "article_id": article_id,
            "day": meta["day"],
            "title": article["title"],
            "url": meta["url"],
            "published": article["published"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "md_file": md_path.name,
            "source_collection": SOURCE_COLLECTION,
        }

        # Replace if force, otherwise append
        if force:
            index = [e for e in index if e["article_id"] != article_id]
        index.append(index_entry)
        existing_ids.add(article_id)

        print(f"  ✅ Day {meta['day']:02d}: {article['title'][:50]}")
        fetched += 1

        # Rate limiting: 1-2 second delay
        time.sleep(1.5)

    # Sort index by day
    index.sort(key=lambda e: e.get("day", 0))
    _save_index(index)

    return {"fetched": fetched, "skipped": skipped, "total": len(index)}


def main() -> None:
    parser = argparse.ArgumentParser(description="從 iThome 鐵人賽擷取文章")
    parser.add_argument("--force", action="store_true", help="強制重新擷取所有文章")
    args = parser.parse_args()

    print("=" * 60)
    print("📰 步驟 1c：擷取 iThome 鐵人賽文章")
    print(f"   系列 URL: {config.ITHELP_SERIES_URL}")
    print("=" * 60)

    result = fetch_ithelp_articles(force=args.force)

    print(f"\n{'=' * 60}")
    print(f"✅ 完成！")
    print(f"   新擷取: {result['fetched']} 篇")
    print(f"   跳過（已存在）: {result['skipped']} 篇")
    print(f"   索引總計: {result['total']} 篇")
    print(f"   輸出目錄: {config.RAW_ITHELP_MD_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
