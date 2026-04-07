#!/usr/bin/env python3
"""
步驟 1h：從 Google Search Central Blog 擷取官方 SEO 公告

功能：
- 從 Blog index 頁面解析所有文章連結（Google 無 RSS feed）
- 逐篇抓取完整 HTML 內容 → Markdown
- 存入 raw_data/google_blog_markdown/
- 更新 raw_data/google_blog_articles_index.json

Google 官方第一手公告：演算法更新、E-E-A-T、Spam Policy 等。

rate limiting：每篇間隔 2 秒。

用法：
    python scripts/01h_fetch_google_blog.py
    python scripts/01h_fetch_google_blog.py --force   # 重新擷取所有
    python scripts/01h_fetch_google_blog.py --limit 10 # 只抓前 10 篇
    python scripts/01h_fetch_google_blog.py --since 2024 # 只抓 2024 年起
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


LANG_EN = "en"
LANG_ZH_TW = "zh-tw"
SOURCE_COLLECTION_EN = "google-search-central"
SOURCE_COLLECTION_ZH = "google-search-central-zh"
SOURCE_COLLECTION = SOURCE_COLLECTION_EN
AUTHOR = "Google Search Central"
INDEX_PATH = config.ROOT_DIR / "raw_data" / "google_blog_articles_index.json"
INDEX_PATH_ZH = config.ROOT_DIR / "raw_data" / "google_blog_zhtw_articles_index.json"
OUTPUT_DIR = config.ROOT_DIR / "raw_data" / "google_blog_markdown"
OUTPUT_DIR_ZH = config.RAW_GOOGLE_BLOG_ZHTW_MD_DIR

# Blog index page (Google Search Central has no RSS feed)
BLOG_INDEX_URL = "https://developers.google.com/search/blog"
_BLOG_POST_PATTERN = re.compile(
    r'href="(/search/blog/(\d{4})/(\d{2})/([^"?]+))(?:\?[^\"]*)?"'
)

# SSRF protection
_ALLOWED_HOSTS = frozenset({
    "developers.google.com",
})

_HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SEOInsightBot/1.0)"}


def _get_lang_resources(lang: str) -> tuple[Path, Path, str]:
    if lang == LANG_ZH_TW:
        return OUTPUT_DIR_ZH, INDEX_PATH_ZH, SOURCE_COLLECTION_ZH
    return OUTPUT_DIR, INDEX_PATH, SOURCE_COLLECTION_EN


def _build_listing_url(lang: str) -> str:
    if lang == LANG_ZH_TW:
        return f"{BLOG_INDEX_URL}?hl=zh-tw"
    return BLOG_INDEX_URL


def _build_post_url(path: str, lang: str) -> str:
    url = f"https://developers.google.com{path}"
    if lang == LANG_ZH_TW:
        return f"{url}?hl=zh-tw"
    return url


def _slug_with_lang_prefix(slug: str, lang: str) -> str:
    if lang == LANG_ZH_TW:
        return f"zhtw-{slug}"
    return slug


def _validate_url(url: str) -> None:
    """Validate URL against Google developer domain allowlist."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
    host = (parsed.hostname or "").lower()
    if not any(host == h or host.endswith("." + h) for h in _ALLOWED_HOSTS):
        raise ValueError(f"URL domain not in allowlist: {host!r}")


def _load_index(index_path: Path = INDEX_PATH) -> list[dict]:
    if index_path.exists():
        return json.loads(index_path.read_text(encoding="utf-8"))
    return []


def _save_index(index: list[dict], index_path: Path = INDEX_PATH) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _sanitize_slug(slug: str) -> str:
    slug = re.sub(r"[^\w\-]", "", slug)
    return slug[:200]


def _discover_blog_posts(since_year: int = 2020, lang: str = LANG_EN) -> list[dict]:
    """Scrape blog index page to discover all post URLs.

    Google Search Central Blog renders all post links server-side.

    Returns list of dicts with: url, slug, year, month
    """
    listing_url = _build_listing_url(lang)
    logger.info("Fetching blog index: %s", listing_url)
    resp = httpx.get(
        listing_url, follow_redirects=True, timeout=30, headers=_HTTP_HEADERS,
    )
    resp.raise_for_status()

    seen: set[str] = set()
    posts: list[dict] = []

    for match in _BLOG_POST_PATTERN.finditer(resp.text):
        path, year, month, raw_slug = match.groups()
        year_int = int(year)

        if year_int < since_year:
            continue

        url = _build_post_url(path, lang)
        if url in seen:
            continue
        seen.add(url)

        slug = _slug_with_lang_prefix(f"{year}-{month}-{raw_slug}", lang)

        posts.append({
            "url": url,
            "slug": slug,
            "year": year_int,
            "month": int(month),
            "published_approx": f"{year}-{month}-01",
        })

    # Sort newest first
    posts.sort(key=lambda p: (p["year"], p["month"]), reverse=True)
    logger.info(
        "Discovered %d blog posts (since %d)", len(posts), since_year,
    )
    return posts


def _fetch_article_content(url: str) -> dict:
    """Fetch a single Google blog page and extract content.

    Google devsite uses <div class="devsite-article-body"> for content.

    Returns dict with: title, html_content, author, published
    """
    _validate_url(url)
    resp = httpx.get(
        url, follow_redirects=True, timeout=30, headers=_HTTP_HEADERS,
    )
    resp.raise_for_status()
    html = resp.text

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # Google devsite content container
    article_tag = soup.find("div", class_="devsite-article-body")
    if not article_tag:
        article_tag = soup.find("article")
    if not article_tag:
        article_tag = soup.find("main")

    html_content = str(article_tag) if article_tag else ""

    # Extract author
    author = AUTHOR
    author_tag = soup.find("span", class_=re.compile(r"devsite-byline-author-name"))
    if author_tag:
        author = author_tag.get_text(strip=True)

    # Extract published date from meta or time element
    published = ""
    time_tag = soup.find("time")
    if time_tag and time_tag.get("datetime"):
        raw_dt = time_tag["datetime"]
        try:
            dt = datetime.fromisoformat(str(raw_dt).replace("Z", "+00:00"))
            published = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    if not published:
        meta_date = soup.find("meta", {"name": "date"})
        if meta_date and meta_date.get("content"):
            published = str(meta_date["content"])[:10]

    # Extract title
    title = "Untitled"
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)

    return {
        "title": title,
        "html_content": html_content,
        "author": author,
        "published": published,
    }


_MIN_CONTENT_CHARS = 200


def _has_sufficient_content(html_content: str) -> bool:
    text = re.sub(r"<[^>]+>", " ", html_content)
    text = re.sub(r"\s+", " ", text).strip()
    return len(text) >= _MIN_CONTENT_CHARS


def fetch_google_blog_articles(
    force: bool = False,
    limit: int = 0,
    since_year: int = 2020,
    lang: str = LANG_EN,
) -> dict:
    """Fetch Google Search Central Blog articles and save as Markdown.

    Args:
        force: Re-fetch all articles
        limit: Max articles to fetch (0 = unlimited)
        since_year: Only fetch articles from this year onward

    Returns:
        {"fetched": int, "skipped": int, "insufficient": int, "total": int}
    """
    output_dir, index_path, source_collection = _get_lang_resources(lang)
    output_dir.mkdir(parents=True, exist_ok=True)

    index = _load_index(index_path=index_path)
    existing_slugs = {entry["slug"] for entry in index}

    discovered = _discover_blog_posts(since_year=since_year, lang=lang)

    fetched = 0
    skipped = 0
    insufficient = 0

    for post_meta in discovered:
        slug = post_meta["slug"]

        if not force and slug in existing_slugs:
            skipped += 1
            continue

        if limit and fetched >= limit:
            logger.info("Reached limit of %d articles", limit)
            break

        try:
            page_data = _fetch_article_content(post_meta["url"])
        except httpx.HTTPError as e:
            logger.warning("%s fetch failed: %s", slug, e)
            continue
        except Exception:
            logger.error("%s unexpected error", slug, exc_info=True)
            continue

        if not _has_sufficient_content(page_data["html_content"]):
            logger.warning("%s insufficient content, skipping", slug)
            insufficient += 1
            continue

        published = page_data["published"] or post_meta["published_approx"]

        md_content = html_to_markdown(page_data["html_content"])
        full_md = add_metadata_header(
            md_content,
            title=page_data["title"],
            published=published,
            author=page_data["author"],
            source_url=post_meta["url"],
            source_type="article",
            source_collection=source_collection,
        )

        safe_slug = _sanitize_slug(slug)
        if not safe_slug:
            logger.warning("Slug sanitized to empty for %s, skipping", slug)
            continue
        md_path = output_dir / f"{safe_slug}.md"
        if not md_path.resolve().is_relative_to(output_dir.resolve()):
            logger.error("Path traversal detected for slug %r, skipping", slug)
            continue
        md_path.write_text(full_md, encoding="utf-8")

        index_entry = {
            "slug": slug,
            "title": page_data["title"],
            "url": post_meta["url"],
            "published": published,
            "author": page_data["author"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "md_file": md_path.name,
            "source_collection": source_collection,
        }

        if force:
            index = [e for e in index if e["slug"] != slug]
        index.append(index_entry)
        existing_slugs.add(slug)

        logger.info("Done: %s", page_data["title"][:60])
        fetched += 1

        time.sleep(2)

    index.sort(key=lambda e: e.get("slug", ""))
    _save_index(index, index_path=index_path)

    return {
        "fetched": fetched,
        "skipped": skipped,
        "insufficient": insufficient,
        "total": len(index),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch Google Search Central Blog articles"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-fetch all articles"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Max articles to fetch (0=unlimited)"
    )
    parser.add_argument(
        "--since", type=int, default=2020,
        help="Only fetch articles from this year onward (default: 2020)",
    )
    parser.add_argument(
        "--lang",
        choices=[LANG_EN, LANG_ZH_TW],
        default=LANG_EN,
        help="Fetch English or zh-TW localized articles (default: en)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    logger.info("Step 1h: Fetch Google Search Central Blog")

    result = fetch_google_blog_articles(
        force=args.force, limit=args.limit, since_year=args.since, lang=args.lang,
    )

    logger.info(
        "Done — fetched: %d, skipped: %d, insufficient: %d, total: %d",
        result["fetched"],
        result["skipped"],
        result["insufficient"],
        result["total"],
    )


if __name__ == "__main__":
    main()
