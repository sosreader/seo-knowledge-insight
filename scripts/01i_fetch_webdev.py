#!/usr/bin/env python3
"""
步驟 1i：從 Web.dev 擷取 Core Web Vitals / Performance 技術文章

功能：
- 解析 Web.dev RSS feed
- 篩選 Performance / CWV / Rendering 相關文章
- 逐篇抓取完整 HTML 內容 → Markdown
- 存入 raw_data/webdev_markdown/
- 更新 raw_data/webdev_articles_index.json

Chrome 團隊第一手技術規格：CWV、INP、Rendering、JavaScript SEO 等。

rate limiting：每篇間隔 1.5 秒。

用法：
    python scripts/01i_fetch_webdev.py
    python scripts/01i_fetch_webdev.py --force   # 重新擷取所有
    python scripts/01i_fetch_webdev.py --limit 10 # 只抓前 10 篇
    python scripts/01i_fetch_webdev.py --filter    # 只抓 Performance/CWV 相關
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


SOURCE_COLLECTION = "web-dev"
AUTHOR = "web.dev"
INDEX_PATH = config.ROOT_DIR / "raw_data" / "webdev_articles_index.json"
OUTPUT_DIR = config.ROOT_DIR / "raw_data" / "webdev_markdown"

FEED_URL = "https://web.dev/feed.xml"

# SSRF protection — web.dev and its Chrome DevRel sibling
_ALLOWED_HOSTS = frozenset({
    "web.dev",
    "www.web.dev",
    "developer.chrome.com",
})

_HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SEOInsightBot/1.0)"}

# Category/tag filter for SEO-relevant performance content
_RELEVANT_TAGS = re.compile(
    r"performance|web-vitals|core-web-vitals|cwv|"
    r"lcp|cls|inp|fid|ttfb|"
    r"rendering|javascript|js|ssr|"
    r"lighthouse|pagespeed|speed|"
    r"seo|crawl|index|"
    r"html|css|accessibility|"
    r"image|font|loading|lazy|prefetch|preload|"
    r"service-worker|caching|cdn|compression",
    re.IGNORECASE,
)

# Slug-level keywords for secondary filtering
_RELEVANT_SLUG_KEYWORDS = frozenset({
    "performance", "vitals", "lcp", "cls", "inp", "fid", "ttfb",
    "render", "javascript", "lighthouse", "pagespeed", "speed",
    "seo", "crawl", "index", "lazy", "prefetch", "preload",
    "optimize", "fast", "slow", "metric", "core-web",
    "image", "font", "compress", "cache", "service-worker",
})


def _validate_url(url: str) -> None:
    """Validate URL against web.dev domain allowlist."""
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
    """Extract slug from web.dev URL.

    Patterns: /articles/some-slug, /blog/some-slug, /some-slug
    """
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    return parts[-1] if parts else ""


def _matches_relevant_tag(tags: list[str]) -> bool:
    """Return True if any tag matches the relevance filter."""
    return any(_RELEVANT_TAGS.search(tag) for tag in tags)


def _matches_relevant_slug(slug: str) -> bool:
    """Return True if slug contains any relevant keyword."""
    return any(kw in slug for kw in _RELEVANT_SLUG_KEYWORDS)


def _parse_rss_feed(feed_url: str) -> list[dict]:
    """Parse web.dev RSS feed.

    Returns list of dicts with: guid, title, url, published, tags, html_content
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
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            published = dt.strftime("%Y-%m-%d")

        tags: list[str] = []
        if hasattr(entry, "tags"):
            tags = [t.get("term", "") for t in entry.tags if t.get("term")]

        html_content = ""
        if hasattr(entry, "content") and entry.content:
            html_content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            html_content = entry.summary

        url = entry.get("link", "")
        guid = entry.get("id", url)

        raw_title = entry.get("title", "Untitled")
        articles.append({
            "guid": guid,
            "title": _clean_webdev_title(raw_title),
            "url": url,
            "published": published,
            "tags": tags,
            "html_content": html_content,
        })

    logger.info("RSS returned %d articles", len(articles))
    return articles


# web.dev pages append UI noise to titles and author sections
_WEBDEV_TITLE_NOISE = re.compile(
    r"Stay organized with collections.*$", re.IGNORECASE,
)
_WEBDEV_AUTHOR_SOCIAL = re.compile(
    r"(GitHub|LinkedIn|Homepage|Mastodon|Bluesky|X\b|Twitter)", re.IGNORECASE,
)


def _clean_webdev_title(raw: str) -> str:
    """Strip web.dev UI noise from title text."""
    title = _WEBDEV_TITLE_NOISE.sub("", raw).strip()
    return title or "Untitled"


def _clean_webdev_author(raw: str) -> str:
    """Extract author name from web.dev byline (strip social link labels)."""
    # Split on social keywords and take the first part
    parts = _WEBDEV_AUTHOR_SOCIAL.split(raw)
    name = parts[0].strip() if parts else raw.strip()
    return name or AUTHOR


def _fetch_article_content(url: str) -> dict:
    """Fetch a single web.dev article page and extract content.

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

    # web.dev content containers
    article_tag = soup.find("article")
    if not article_tag:
        article_tag = soup.find("div", class_=re.compile(r"article|content|post"))
    if not article_tag:
        article_tag = soup.find("main")

    # Remove navigation, TOC, feedback, and author bio elements
    if article_tag:
        for unwanted in article_tag.find_all(
            class_=re.compile(
                r"toc|breadcrumb|nav|feedback|share|newsletter|"
                r"related|sidebar|comment|footer|"
                r"collection-banner|authors"
            )
        ):
            unwanted.decompose()

    # Remove the first h1 (already captured in metadata header)
    if article_tag:
        first_h1 = article_tag.find("h1")
        if first_h1:
            first_h1.decompose()

    html_content = str(article_tag) if article_tag else ""
    # Strip "Stay organized with collections..." noise from body
    html_content = _WEBDEV_TITLE_NOISE.sub("", html_content)

    author = AUTHOR
    author_tag = soup.find(class_=re.compile(r"author|byline"))
    if author_tag:
        name = _clean_webdev_author(author_tag.get_text(strip=True))
        if name:
            author = name

    title = "Untitled"
    h1 = soup.find("h1")
    if h1:
        title = _clean_webdev_title(h1.get_text(strip=True))

    return {"title": title, "html_content": html_content, "author": author}


_MIN_CONTENT_CHARS = 200


def _has_sufficient_content(html_content: str) -> bool:
    text = re.sub(r"<[^>]+>", " ", html_content)
    text = re.sub(r"\s+", " ", text).strip()
    return len(text) >= _MIN_CONTENT_CHARS


def fetch_webdev_articles(
    feed_url: str = FEED_URL,
    force: bool = False,
    limit: int = 0,
    use_filter: bool = False,
) -> dict:
    """Fetch web.dev articles and save as Markdown.

    Args:
        feed_url: RSS feed URL
        force: Re-fetch all articles
        limit: Max articles to fetch (0 = unlimited)
        use_filter: Apply category/slug filtering (default: fetch all,
            since web.dev RSS is already curated and has no tags)

    Returns:
        {"fetched": int, "skipped": int, "filtered": int, "insufficient": int, "total": int}
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    index = _load_index()
    existing_guids = {entry["guid"] for entry in index}

    rss_articles = _parse_rss_feed(feed_url)

    fetched = 0
    skipped = 0
    filtered = 0
    insufficient = 0

    for article_meta in rss_articles:
        guid = article_meta["guid"]
        url = article_meta["url"]
        slug = _slug_from_url(url)

        if not slug:
            logger.warning("Empty slug for URL %s, skipping", url)
            filtered += 1
            continue

        # Category filtering (only when --filter is explicitly set)
        if use_filter:
            if not _matches_relevant_tag(article_meta["tags"]) and not _matches_relevant_slug(slug):
                filtered += 1
                continue

        if not force and guid in existing_guids:
            skipped += 1
            continue

        if limit and fetched >= limit:
            logger.info("Reached limit of %d articles", limit)
            break

        html_content = article_meta["html_content"]
        title = article_meta["title"]
        author = AUTHOR

        # If feed content is insufficient, fetch the full page
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
            "tags": article_meta["tags"],
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
        "filtered": filtered,
        "insufficient": insufficient,
        "total": len(index),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch web.dev articles (CWV / Performance / Rendering)"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-fetch all articles"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Max articles to fetch (0=unlimited)"
    )
    parser.add_argument(
        "--filter", action="store_true",
        help="Only fetch Performance/CWV related articles (slug-based)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    logger.info("Step 1i: Fetch web.dev (CWV / Performance / Rendering)")

    result = fetch_webdev_articles(
        force=args.force, limit=args.limit, use_filter=args.filter,
    )

    logger.info(
        "Done — fetched: %d, skipped: %d, filtered: %d, insufficient: %d, total: %d",
        result["fetched"],
        result["skipped"],
        result["filtered"],
        result["insufficient"],
        result["total"],
    )


if __name__ == "__main__":
    main()
