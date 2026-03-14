#!/usr/bin/env python3
"""
步驟 1f：從 Search Engine Journal (SEJ) 擷取進階 SEO 文章

功能：
- 解析 SEJ RSS feed
- 依分類篩選 Technical SEO / Advanced / AI 相關文章
- 逐篇抓取完整 HTML 內容 → Markdown
- 存入 raw_data/sej_markdown/
- 更新 raw_data/sej_articles_index.json

rate limiting：每篇間隔 1.5 秒。

用法：
    python scripts/01f_fetch_sej.py
    python scripts/01f_fetch_sej.py --force   # 重新擷取所有
    python scripts/01f_fetch_sej.py --limit 10 # 只抓前 10 篇
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


SOURCE_COLLECTION = "sej"
AUTHOR = "Search Engine Journal"
INDEX_PATH = config.ROOT_DIR / "raw_data" / "sej_articles_index.json"
OUTPUT_DIR = config.ROOT_DIR / "raw_data" / "sej_markdown"

# SEJ RSS feed URL
FEED_URL = "https://www.searchenginejournal.com/feed/"

# SSRF protection
_ALLOWED_HOSTS = frozenset({
    "searchenginejournal.com",
    "www.searchenginejournal.com",
})

# Category filter — only fetch articles in these categories (case-insensitive)
_L4_CATEGORIES = re.compile(
    r"technical.seo|advanced|artificial.intelligence|ai|"
    r"algorithm|google.update|machine.learning|"
    r"javascript|structured.data|core.web.vitals|"
    r"international.seo|enterprise|crawl|index|"
    r"site.architecture|migration|automation|"
    r"log.file|rendering|edge.seo|"
    r"programmatic|schema|hreflang",
    re.IGNORECASE,
)

# Slug-level L4 keywords for secondary filtering
_L4_SLUG_KEYWORDS = frozenset({
    "technical-seo", "advanced", "programmatic",
    "automation", "automate", "predictive",
    "attribution", "machine-learning", "ai-seo",
    "log-file", "crawl-budget", "javascript-seo",
    "structured-data", "schema", "hreflang",
    "core-web-vitals", "edge-seo", "enterprise",
    "site-migration", "indexing-api", "rendering",
    "a-b-testing", "seo-testing", "python",
    "large-scale", "competitive-intelligence",
})


def _validate_url(url: str) -> None:
    """Validate URL against SEJ domain allowlist."""
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


def _slug_from_url(url: str) -> str:
    """Extract slug from SEJ article URL."""
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] if path else ""


def _matches_l4_category(categories: list[str]) -> bool:
    """Return True if any RSS category matches L4 filter."""
    for cat in categories:
        if _L4_CATEGORIES.search(cat):
            return True
    return False


def _matches_l4_slug(slug: str) -> bool:
    """Return True if slug contains any L4 keyword."""
    for kw in _L4_SLUG_KEYWORDS:
        if kw in slug:
            return True
    return False


def _parse_rss_feed(feed_url: str) -> list[dict]:
    """Parse SEJ RSS feed and return list of article metadata.

    Returns list of dicts with: guid, title, url, published, categories
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

        # Extract categories/tags
        categories = []
        if hasattr(entry, "tags"):
            categories = [t.get("term", "") for t in entry.tags if t.get("term")]

        url = entry.get("link", "")
        guid = entry.get("id", url)

        articles.append({
            "guid": guid,
            "title": entry.get("title", "Untitled"),
            "url": url,
            "published": published,
            "categories": categories,
        })

    logger.info("RSS returned %d articles", len(articles))
    return articles


def _fetch_article_content(url: str) -> dict:
    """Fetch a single SEJ article page and extract content.

    Returns dict with: title, html_content, author
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

    # Extract author from meta or byline
    author = AUTHOR
    author_match = re.search(
        r'<meta[^>]*name="author"[^>]*content="([^"]+)"', html
    )
    if author_match:
        author = author_match.group(1).strip()

    # Extract article body using BeautifulSoup
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # SEJ uses <div class="post-content"> or <article> for main content
    article_tag = soup.find("div", class_=re.compile(r"post-content|entry-content"))
    if not article_tag:
        article_tag = soup.find("article")
    if not article_tag:
        article_tag = soup.find("main")

    # Remove ad blocks, related articles, author bio from article content
    if article_tag:
        for unwanted in article_tag.find_all(
            class_=re.compile(
                r"ad-|advertisement|related-|author-bio|social-share|"
                r"newsletter|sidebar|comment"
            )
        ):
            unwanted.decompose()

    html_content = str(article_tag) if article_tag else ""

    # Extract title from article or <title>
    title = "Untitled"
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)
    else:
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
            title = re.sub(r"\s*[-–—|]\s*Search Engine Journal.*$", "", title)

    return {
        "title": title,
        "html_content": html_content,
        "author": author,
    }


def fetch_sej_articles(
    feed_url: str = FEED_URL,
    force: bool = False,
    limit: int = 0,
) -> dict:
    """Fetch SEJ articles and save as Markdown.

    Args:
        feed_url: RSS feed URL
        force: Re-fetch all articles (ignore existing index)
        limit: Max number of articles to fetch (0 = unlimited)

    Returns:
        {"fetched": int, "skipped": int, "filtered": int, "total": int}
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    index = _load_index()
    existing_guids = {entry["guid"] for entry in index}

    # Parse RSS feed
    rss_articles = _parse_rss_feed(feed_url)

    fetched = 0
    skipped = 0
    filtered = 0

    for rss_meta in rss_articles:
        guid = rss_meta["guid"]
        slug = _slug_from_url(rss_meta["url"])

        if not slug:
            logger.warning("Empty slug for URL %s, skipping", rss_meta["url"])
            filtered += 1
            continue

        # Category-based L4 filter
        if not _matches_l4_category(rss_meta["categories"]) and not _matches_l4_slug(slug):
            filtered += 1
            continue

        if not force and guid in existing_guids:
            skipped += 1
            continue

        if limit and fetched >= limit:
            logger.info("Reached limit of %d articles", limit)
            break

        try:
            article = _fetch_article_content(rss_meta["url"])
        except httpx.HTTPError as e:
            logger.warning("%s fetch failed: %s", slug, e)
            continue
        except Exception:
            logger.error("%s unexpected error", slug, exc_info=True)
            continue

        if not article["html_content"]:
            logger.warning("%s has no content, skipping", slug)
            continue

        # Convert HTML to Markdown
        md_content = html_to_markdown(article["html_content"])

        # Add metadata header
        full_md = add_metadata_header(
            md_content,
            title=article["title"],
            published=rss_meta["published"],
            author=article["author"],
            source_url=rss_meta["url"],
            source_type="article",
            source_collection=SOURCE_COLLECTION,
        )

        md_path = OUTPUT_DIR / f"{slug}.md"
        md_path.write_text(full_md, encoding="utf-8")

        # Update index
        index_entry = {
            "guid": guid,
            "slug": slug,
            "title": article["title"],
            "url": rss_meta["url"],
            "published": rss_meta["published"],
            "author": article["author"],
            "categories": rss_meta["categories"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "md_file": md_path.name,
            "source_collection": SOURCE_COLLECTION,
        }

        if force:
            index = [e for e in index if e["guid"] != guid]
        index.append(index_entry)
        existing_guids.add(guid)

        logger.info("Done: %s", article["title"][:60])
        fetched += 1

        # Rate limiting
        time.sleep(1.5)

    # Sort index by slug
    index.sort(key=lambda e: e.get("slug", ""))
    _save_index(index)

    return {
        "fetched": fetched,
        "skipped": skipped,
        "filtered": filtered,
        "total": len(index),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch Search Engine Journal articles (L4 SEO content)"
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
    logger.info("Step 1f: Fetch Search Engine Journal (L4 SEO content)")

    result = fetch_sej_articles(force=args.force, limit=args.limit)

    logger.info(
        "Done — fetched: %d, skipped: %d, filtered: %d, total: %d",
        result["fetched"],
        result["skipped"],
        result["filtered"],
        result["total"],
    )


if __name__ == "__main__":
    main()
