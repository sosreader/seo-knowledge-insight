#!/usr/bin/env python3
"""
步驟 1j：從 Screaming Frog Blog 擷取技術 SEO 深度文章

功能：
- 解析 Screaming Frog Blog RSS feed
- 逐篇抓取完整 HTML 內容 → Markdown
- 存入 raw_data/screamingfrog_markdown/
- 更新 raw_data/screamingfrog_articles_index.json

技術 SEO 工具操作深度文章：Log File Analysis、Crawl Budget、Custom Extraction 等。
L4 密度接近 100%，不設分類篩選。

rate limiting：每篇間隔 1.5 秒。

用法：
    python scripts/01j_fetch_screaming_frog.py
    python scripts/01j_fetch_screaming_frog.py --force   # 重新擷取所有
    python scripts/01j_fetch_screaming_frog.py --limit 10 # 只抓前 10 篇
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


SOURCE_COLLECTION = "screaming-frog"
AUTHOR = "Screaming Frog"
INDEX_PATH = config.ROOT_DIR / "raw_data" / "screamingfrog_articles_index.json"
OUTPUT_DIR = config.ROOT_DIR / "raw_data" / "screamingfrog_markdown"

FEED_URL = "https://www.screamingfrog.co.uk/feed/"

# SSRF protection
_ALLOWED_HOSTS = frozenset({
    "screamingfrog.co.uk",
    "www.screamingfrog.co.uk",
})

_HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SEOInsightBot/1.0)"}


def _validate_url(url: str) -> None:
    """Validate URL against Screaming Frog domain allowlist."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
    host = (parsed.hostname or "").lower()
    if not any(host == h or host.endswith("." + h) for h in _ALLOWED_HOSTS):
        raise ValueError(f"URL domain not in allowlist: {host!r}")


def _load_index() -> list[dict]:
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return []


def _save_index(index: list[dict]) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _sanitize_slug(slug: str) -> str:
    slug = re.sub(r"[^\w\-]", "", slug)
    return slug[:200]


def _slug_from_url(url: str) -> str:
    """Extract slug from Screaming Frog blog URL."""
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    return parts[-1] if parts else ""


def _parse_rss_feed(feed_url: str) -> list[dict]:
    """Parse Screaming Frog RSS feed.

    Returns list of dicts with: guid, title, url, published, html_content, author
    """
    import feedparser

    logger.info("Fetching RSS feed: %s", feed_url)
    feed = feedparser.parse(feed_url, request_headers=_HTTP_HEADERS)

    if feed.bozo and not feed.entries:
        exc = getattr(feed, "bozo_exception", None)
        raise ValueError(f"RSS parse failed: {exc or 'unknown error'}")

    articles: list[dict] = []
    for entry in feed.entries:
        published = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            published = dt.strftime("%Y-%m-%d")

        # WordPress RSS typically includes full content
        html_content = ""
        if hasattr(entry, "content") and entry.content:
            html_content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            html_content = entry.summary

        # WordPress RSS may include author
        author = AUTHOR
        if hasattr(entry, "author") and entry.author:
            author = entry.author

        url = entry.get("link", "")
        guid = entry.get("id", url)

        articles.append({
            "guid": guid,
            "title": entry.get("title", "Untitled"),
            "url": url,
            "published": published,
            "html_content": html_content,
            "author": author,
        })

    logger.info("RSS returned %d articles", len(articles))
    return articles


def _fetch_article_content(url: str) -> dict:
    """Fetch a single Screaming Frog blog page and extract content.

    Screaming Frog uses WordPress with standard entry-content class.

    Returns dict with: title, html_content, author
    """
    _validate_url(url)
    resp = httpx.get(
        url, follow_redirects=True, timeout=30, headers=_HTTP_HEADERS,
    )
    resp.raise_for_status()
    html = resp.text

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # WordPress content containers
    article_tag = soup.find("div", class_=re.compile(r"entry-content|post-content"))
    if not article_tag:
        article_tag = soup.find("article")
    if not article_tag:
        article_tag = soup.find("main")

    # Remove unwanted elements
    if article_tag:
        for unwanted in article_tag.find_all(
            class_=re.compile(
                r"ad-|advert|related|share|social|newsletter|"
                r"sidebar|comment|author-bio|navigation"
            )
        ):
            unwanted.decompose()

    html_content = str(article_tag) if article_tag else ""

    # Extract author
    author = AUTHOR
    author_tag = soup.find(class_=re.compile(r"author|byline"))
    if author_tag:
        name = author_tag.get_text(strip=True)
        if name:
            author = name

    # Extract title
    title = "Untitled"
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    return {"title": title, "html_content": html_content, "author": author}


_MIN_CONTENT_CHARS = 300


def _has_sufficient_content(html_content: str) -> bool:
    text = re.sub(r"<[^>]+>", " ", html_content)
    text = re.sub(r"\s+", " ", text).strip()
    return len(text) >= _MIN_CONTENT_CHARS


def fetch_screaming_frog_articles(
    feed_url: str = FEED_URL,
    force: bool = False,
    limit: int = 0,
) -> dict:
    """Fetch Screaming Frog Blog articles and save as Markdown.

    Returns:
        {"fetched": int, "skipped": int, "insufficient": int, "total": int}
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    index = _load_index()
    existing_guids = {entry["guid"] for entry in index}

    rss_articles = _parse_rss_feed(feed_url)

    fetched = 0
    skipped = 0
    insufficient = 0

    for article_meta in rss_articles:
        guid = article_meta["guid"]
        url = article_meta["url"]
        slug = _slug_from_url(url)

        if not slug:
            logger.warning("Empty slug for URL %s, skipping", url)
            insufficient += 1
            continue

        if not force and guid in existing_guids:
            skipped += 1
            continue

        if limit and fetched >= limit:
            logger.info("Reached limit of %d articles", limit)
            break

        html_content = article_meta["html_content"]
        title = article_meta["title"]
        author = article_meta["author"]

        # If RSS content is insufficient, fetch the full page
        if not _has_sufficient_content(html_content):
            try:
                page_data = _fetch_article_content(url)
                html_content = page_data["html_content"]
                author = page_data["author"]
                if page_data["title"] != "Untitled":
                    title = page_data["title"]
                time.sleep(1.5)
            except httpx.HTTPError as e:
                logger.warning("%s page fetch failed: %s", slug, e)
            except Exception:
                logger.error("%s unexpected error", slug, exc_info=True)

        if not _has_sufficient_content(html_content):
            logger.warning("%s insufficient content, skipping", slug)
            insufficient += 1
            continue

        md_content = html_to_markdown(html_content)
        full_md = add_metadata_header(
            md_content,
            title=title,
            published=article_meta["published"],
            author=author,
            source_url=url,
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

        index_entry = {
            "guid": guid,
            "slug": slug,
            "title": title,
            "url": url,
            "published": article_meta["published"],
            "author": author,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "md_file": md_path.name,
            "source_collection": SOURCE_COLLECTION,
        }

        if force:
            index = [e for e in index if e["guid"] != guid]
        index.append(index_entry)
        existing_guids.add(guid)

        logger.info("Done: %s", title[:60])
        fetched += 1

        time.sleep(1.5)

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
        description="Fetch Screaming Frog Blog articles (technical SEO deep-dives)"
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
    logger.info("Step 1j: Fetch Screaming Frog Blog (technical SEO deep-dives)")

    result = fetch_screaming_frog_articles(force=args.force, limit=args.limit)

    logger.info(
        "Done — fetched: %d, skipped: %d, insufficient: %d, total: %d",
        result["fetched"],
        result["skipped"],
        result["insufficient"],
        result["total"],
    )


if __name__ == "__main__":
    main()
