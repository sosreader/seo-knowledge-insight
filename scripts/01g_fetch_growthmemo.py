#!/usr/bin/env python3
"""
步驟 1g：從 Kevin Indig's Growth Memo 擷取程式化 SEO 文章（Substack）

功能：
- 解析 Growth Memo Substack RSS feed
- Kevin Indig 專精程式化 SEO，幾乎每篇都是 L4 內容
- 逐篇抓取完整 HTML 內容 → Markdown
- 存入 raw_data/growthmemo_markdown/
- 更新 raw_data/growthmemo_articles_index.json

rate limiting：每篇間隔 1 秒。

用法：
    python scripts/01g_fetch_growthmemo.py
    python scripts/01g_fetch_growthmemo.py --force   # 重新擷取所有
    python scripts/01g_fetch_growthmemo.py --limit 10 # 只抓前 10 篇
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
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

try:
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

from utils.html_to_markdown import html_to_markdown, add_metadata_header


SOURCE_COLLECTION = "growth-memo"
AUTHOR = "Kevin Indig"
INDEX_PATH = config.ROOT_DIR / "raw_data" / "growthmemo_articles_index.json"
OUTPUT_DIR = config.ROOT_DIR / "raw_data" / "growthmemo_markdown"

# Kevin Indig's Growth Memo RSS (Substack-based, custom domain)
FEED_URL = "https://www.growth-memo.com/feed"

# SSRF protection
_ALLOWED_HOSTS = frozenset({
    "growth-memo.com",
    "www.growth-memo.com",
    "kevin-indig.com",
    "www.kevin-indig.com",
    "growthmemo.substack.com",
})


def _validate_url(url: str) -> None:
    """Validate URL against Growth Memo domain allowlist."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
    host = (parsed.hostname or "").lower()
    if not any(host == h or host.endswith("." + h) for h in _ALLOWED_HOSTS):
        raise ValueError(f"URL domain not in allowlist: {host!r}")


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


def _sanitize_slug(slug: str) -> str:
    """Strip path separators and dangerous characters from slug."""
    slug = re.sub(r"[^\w\-]", "", slug)
    return slug[:200]


def _slug_from_url(url: str) -> str:
    """Extract slug from article URL."""
    path = urlparse(url).path.strip("/")
    # Substack URLs: /p/article-slug
    parts = path.split("/")
    return parts[-1] if parts else ""


def _parse_rss_feed(feed_url: str) -> list[dict]:
    """Parse Growth Memo RSS feed and return list of article metadata.

    Substack RSS includes full HTML content in the feed, so we don't
    need a second HTTP request for most articles.

    Returns list of dicts with: guid, title, url, published, html_content
    """
    import feedparser

    _validate_url(feed_url)
    logger.info("Fetching RSS feed: %s", feed_url)
    feed = feedparser.parse(feed_url)

    if feed.bozo and not feed.entries:
        exc = getattr(feed, "bozo_exception", None)
        raise ValueError(f"RSS parse failed: {exc or 'unknown error'}")

    articles = []
    for entry in feed.entries:
        # Extract publication date
        published = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            published = dt.strftime("%Y-%m-%d")

        # Substack includes full content in RSS
        html_content = ""
        if hasattr(entry, "content") and entry.content:
            html_content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            html_content = entry.summary

        url = entry.get("link", "")
        guid = entry.get("id", url)

        articles.append({
            "guid": guid,
            "title": entry.get("title", "Untitled"),
            "url": url,
            "published": published,
            "html_content": html_content,
        })

    logger.info("RSS returned %d articles", len(articles))
    return articles


def _fetch_article_page(url: str) -> str:
    """Fetch article page HTML when RSS content is insufficient.

    Returns HTML content string.
    """
    _validate_url(url)
    resp = httpx.get(
        url,
        follow_redirects=True,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0 (compatible; SEOInsightBot/1.0)"},
    )
    resp.raise_for_status()
    html = resp.text

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # Substack uses <div class="body markup"> or <div class="available-content">
    article_tag = soup.find("div", class_=re.compile(r"body|available-content"))
    if not article_tag:
        article_tag = soup.find("article")
    if not article_tag:
        article_tag = soup.find("main")

    return str(article_tag) if article_tag else ""


_MIN_CONTENT_CHARS = 300  # Minimum plain-text chars for valid content


def _has_sufficient_content(html_content: str) -> bool:
    """Return True if article content has enough text (not just a teaser)."""
    text = re.sub(r"<[^>]+>", " ", html_content)
    text = re.sub(r"\s+", " ", text).strip()
    return len(text) >= _MIN_CONTENT_CHARS


def fetch_growthmemo_articles(
    feed_url: str = FEED_URL,
    force: bool = False,
    limit: int = 0,
) -> dict:
    """Fetch Growth Memo articles and save as Markdown.

    Args:
        feed_url: RSS feed URL
        force: Re-fetch all articles (ignore existing index)
        limit: Max number of articles to fetch (0 = unlimited)

    Returns:
        {"fetched": int, "skipped": int, "insufficient": int, "total": int}
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    index = _load_index()
    existing_guids = {entry["guid"] for entry in index}

    # Parse RSS feed (Substack includes full content)
    rss_articles = _parse_rss_feed(feed_url)

    fetched = 0
    skipped = 0
    insufficient = 0

    for rss_meta in rss_articles:
        guid = rss_meta["guid"]
        slug = _slug_from_url(rss_meta["url"])

        if not slug:
            logger.warning("Empty slug for URL %s, skipping", rss_meta["url"])
            insufficient += 1
            continue

        if not force and guid in existing_guids:
            skipped += 1
            continue

        if limit and fetched >= limit:
            logger.info("Reached limit of %d articles", limit)
            break

        html_content = rss_meta["html_content"]

        # If RSS content is too short, try fetching the full page
        if not _has_sufficient_content(html_content):
            try:
                html_content = _fetch_article_page(rss_meta["url"])
                time.sleep(1)  # rate limiting for page fetch
            except httpx.HTTPError as e:
                logger.warning("%s page fetch failed: %s", slug, e)
            except Exception:
                logger.error("%s unexpected error fetching page", slug, exc_info=True)

        # Final content check
        if not _has_sufficient_content(html_content):
            logger.warning("%s insufficient content, skipping", slug)
            insufficient += 1
            continue

        # Convert HTML to Markdown
        md_content = html_to_markdown(html_content)

        # Add metadata header
        full_md = add_metadata_header(
            md_content,
            title=rss_meta["title"],
            published=rss_meta["published"],
            author=AUTHOR,
            source_url=rss_meta["url"],
            source_type="article",
            source_collection=SOURCE_COLLECTION,
        )

        safe_slug = _sanitize_slug(slug)
        if not safe_slug:
            logger.warning("Slug sanitized to empty for %s, skipping", slug)
            continue
        md_path = OUTPUT_DIR / f"{safe_slug}.md"
        if not md_path.resolve().is_relative_to(OUTPUT_DIR.resolve()):
            logger.error("Path traversal detected for slug %r, skipping", slug)
            continue
        md_path.write_text(full_md, encoding="utf-8")

        # Update index
        index_entry = {
            "guid": guid,
            "slug": slug,
            "title": rss_meta["title"],
            "url": rss_meta["url"],
            "published": rss_meta["published"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "md_file": md_path.name,
            "source_collection": SOURCE_COLLECTION,
        }

        if force:
            index = [e for e in index if e["guid"] != guid]
        index.append(index_entry)
        existing_guids.add(guid)

        logger.info("Done: %s", rss_meta["title"][:60])
        fetched += 1

    # Sort index by slug
    index.sort(key=lambda e: e.get("slug", ""))
    _save_index(index)

    return {
        "fetched": fetched,
        "skipped": skipped,
        "insufficient": insufficient,
        "total": len(index),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch Growth Memo articles (Kevin Indig, programmatic SEO)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-fetch all articles"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Max articles to fetch (0=unlimited)"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    logger.info("Step 1g: Fetch Growth Memo (Kevin Indig, programmatic SEO)")

    result = fetch_growthmemo_articles(force=args.force, limit=args.limit)

    logger.info(
        "Done — fetched: %d, skipped: %d, insufficient: %d, total: %d",
        result["fetched"],
        result["skipped"],
        result["insufficient"],
        result["total"],
    )


if __name__ == "__main__":
    main()
