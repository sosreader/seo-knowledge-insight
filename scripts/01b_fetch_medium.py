#!/usr/bin/env python3
"""
步驟 1b：從 Medium RSS feed 擷取 Gene Hong 的 SEO 文章

功能：
- 解析 Medium RSS feed（https://genehong.medium.com/feed）
- 將 HTML 文章內容轉為 Markdown
- 存入 raw_data/medium_markdown/
- 更新 raw_data/medium_articles_index.json

增量模式：比對 index 中的 guid，跳過已擷取的。

用法：
    python scripts/01b_fetch_medium.py
    python scripts/01b_fetch_medium.py --url https://genehong.medium.com/some-article  # 手動加入
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
from scripts.fetch_medium_helpers import _safe_filename


AUTHOR = "Gene Hong"
SOURCE_COLLECTION = "genehong-medium"
INDEX_PATH = config.ROOT_DIR / "raw_data" / "medium_articles_index.json"


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


def _parse_rss_feed(feed_url: str) -> list[dict]:
    """Parse Medium RSS feed and return list of article metadata.

    Returns list of dicts with: guid, title, url, published, html_content
    """
    import feedparser

    print(f"  擷取 RSS feed: {feed_url}")
    feed = feedparser.parse(feed_url)

    if feed.bozo and not feed.entries:
        raise ValueError(f"RSS 解析失敗: {feed.bozo_exception}")

    articles = []
    for entry in feed.entries:
        # Extract publication date
        published = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            dt = datetime(*entry.published_parsed[:6])
            published = dt.strftime("%Y-%m-%d")

        # Get full content (Medium uses content:encoded)
        html_content = ""
        if hasattr(entry, "content") and entry.content:
            html_content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            html_content = entry.summary

        articles.append({
            "guid": entry.get("id", entry.get("link", "")),
            "title": entry.get("title", "Untitled"),
            "url": entry.get("link", ""),
            "published": published,
            "html_content": html_content,
        })

    print(f"  RSS 回傳 {len(articles)} 篇文章")
    return articles


def _fetch_single_url(url: str) -> dict:
    """Fetch a single Medium article by URL.

    Returns dict with: guid, title, url, published, html_content
    """
    print(f"  擷取單篇文章: {url}")
    resp = httpx.get(url, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    html = resp.text

    # Extract title from HTML
    title_match = re.search(r'<title[^>]*>(.+?)</title>', html, re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Untitled"
    # Clean Medium title suffix
    title = re.sub(r'\s*\|\s*by\s+.*$', '', title)
    title = re.sub(r'\s*[-–—]\s*Medium\s*$', '', title)

    # Extract article content (Medium uses <article> tag)
    article_match = re.search(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
    html_content = article_match.group(1) if article_match else html

    # Try to extract published date from meta tags
    published = ""
    date_match = re.search(
        r'<meta[^>]*property="article:published_time"[^>]*content="([^"]+)"',
        html,
    )
    if date_match:
        try:
            dt = datetime.fromisoformat(date_match.group(1).replace("Z", "+00:00"))
            published = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return {
        "guid": url,
        "title": title,
        "url": url,
        "published": published,
        "html_content": html_content,
    }


def fetch_medium_articles(
    feed_url: str = config.MEDIUM_RSS_URL,
    extra_urls: list[str] | None = None,
) -> dict:
    """Fetch Medium articles and save as Markdown.

    Returns:
        {"fetched": int, "skipped": int, "total": int}
    """
    output_dir = config.RAW_MEDIUM_MD_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    index = _load_index()
    existing_guids = {entry["guid"] for entry in index}

    # Collect articles from RSS
    articles = _parse_rss_feed(feed_url)

    # Add extra URLs (manual additions)
    if extra_urls:
        for url in extra_urls:
            if url not in existing_guids:
                try:
                    article = _fetch_single_url(url)
                    articles.append(article)
                    time.sleep(1)  # rate limiting
                except Exception as e:
                    print(f"  ⚠️  擷取失敗: {url} — {e}")

    fetched = 0
    skipped = 0

    for article in articles:
        guid = article["guid"]

        # Skip already fetched
        if guid in existing_guids:
            skipped += 1
            continue

        # Convert HTML to Markdown
        md_content = html_to_markdown(article["html_content"])

        # Add metadata header
        full_md = add_metadata_header(
            md_content,
            title=article["title"],
            published=article["published"],
            author=AUTHOR,
            source_url=article["url"],
            source_type="article",
            source_collection=SOURCE_COLLECTION,
        )

        # Write Markdown file
        filename = _safe_filename(article["title"])
        md_path = output_dir / f"{filename}.md"
        # Avoid overwriting
        counter = 1
        while md_path.exists():
            md_path = output_dir / f"{filename}_{counter}.md"
            counter += 1

        md_path.write_text(full_md, encoding="utf-8")

        # Update index
        index_entry = {
            "guid": guid,
            "title": article["title"],
            "url": article["url"],
            "published": article["published"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "md_file": md_path.name,
            "source_collection": SOURCE_COLLECTION,
        }
        index.append(index_entry)
        existing_guids.add(guid)

        print(f"  ✅ {article['title']}")
        fetched += 1

    _save_index(index)

    return {"fetched": fetched, "skipped": skipped, "total": len(index)}


def main() -> None:
    parser = argparse.ArgumentParser(description="從 Medium RSS 擷取 SEO 文章")
    parser.add_argument("--url", nargs="*", default=[], help="手動加入的文章 URL")
    args = parser.parse_args()

    print("=" * 60)
    print("📰 步驟 1b：擷取 Medium 文章")
    print("=" * 60)

    result = fetch_medium_articles(extra_urls=args.url or None)

    print(f"\n{'=' * 60}")
    print(f"✅ 完成！")
    print(f"   新擷取: {result['fetched']} 篇")
    print(f"   跳過（已存在）: {result['skipped']} 篇")
    print(f"   索引總計: {result['total']} 篇")
    print(f"   輸出目錄: {config.RAW_MEDIUM_MD_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
