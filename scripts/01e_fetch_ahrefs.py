#!/usr/bin/env python3
"""
步驟 1e：從 Ahrefs Blog 擷取進階 SEO 文章（L4 高密度來源）

功能：
- 透過 WordPress REST API 取得 L4 相關分類的文章
- 分類篩選：technical-seo, ai-search, enterprise-seo, data-studies
- 逐篇 HTML 內容 → Markdown
- 存入 raw_data/ahrefs_markdown/
- 更新 raw_data/ahrefs_articles_index.json

rate limiting：每篇間隔 2 秒，避免被封鎖。

用法：
    python scripts/01e_fetch_ahrefs.py
    python scripts/01e_fetch_ahrefs.py --force   # 重新擷取所有
    python scripts/01e_fetch_ahrefs.py --limit 10 # 只抓前 10 篇
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


SOURCE_COLLECTION = "ahrefs-blog"
AUTHOR = "Ahrefs"
INDEX_PATH = config.ROOT_DIR / "raw_data" / "ahrefs_articles_index.json"
OUTPUT_DIR = config.ROOT_DIR / "raw_data" / "ahrefs_markdown"

# WordPress REST API base
WP_API_BASE = "https://ahrefs.com/blog/wp-json/wp/v2"

# SSRF protection: only allow ahrefs.com
_ALLOWED_HOSTS = frozenset({"ahrefs.com", "www.ahrefs.com"})

# L4 category IDs (from WP API /categories endpoint)
# technical-seo=329, ai-search=469, enterprise-seo=461, data-studies=414
_L4_CATEGORY_IDS = (329, 469, 461, 414)

_HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SEOInsightBot/1.0)"}


def _validate_url(url: str) -> None:
    """Validate URL against Ahrefs domain allowlist."""
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
    """Extract slug from Ahrefs blog URL (last path segment)."""
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] if path else ""


def _fetch_wp_posts_page(category_ids: str, page: int) -> tuple[list[dict], int]:
    """Fetch one page of WP posts for given category IDs.

    Returns (posts_list, total_pages).
    """
    url = (
        f"{WP_API_BASE}/posts"
        f"?categories={category_ids}&per_page=50&page={page}"
        f"&_fields=id,slug,title,link,date_gmt,content"
    )
    _validate_url(url)
    resp = httpx.get(url, follow_redirects=True, timeout=30, headers=_HTTP_HEADERS)
    resp.raise_for_status()

    total_pages = int(resp.headers.get("X-WP-TotalPages", "1"))
    return resp.json(), total_pages


def _fetch_all_l4_posts() -> list[dict]:
    """Fetch all L4 blog posts via WP REST API (paginated).

    Returns list of dicts with: slug, url, title, published, html_content
    """
    cat_ids = ",".join(str(c) for c in _L4_CATEGORY_IDS)
    all_posts: list[dict] = []
    page = 1

    while True:
        posts, total_pages = _fetch_wp_posts_page(cat_ids, page)
        logger.info("WP API page %d/%d — %d posts", page, total_pages, len(posts))

        for post in posts:
            slug = post.get("slug", "")
            if not slug:
                continue
            all_posts.append({
                "slug": slug,
                "url": post.get("link", f"https://ahrefs.com/blog/{slug}/"),
                "title": _clean_wp_title(post.get("title", {}).get("rendered", "")),
                "published": _parse_wp_date(post.get("date_gmt", "")),
                "html_content": post.get("content", {}).get("rendered", ""),
            })

        if page >= total_pages:
            break
        page += 1
        time.sleep(1)  # rate limit between API pages

    logger.info("Total L4 posts from WP API: %d", len(all_posts))
    return all_posts


def _clean_wp_title(raw: str) -> str:
    """Clean WP rendered title (strip HTML entities and tags)."""
    import html
    title = html.unescape(raw)
    return re.sub(r"<[^>]+>", "", title).strip() or "Untitled"


def _parse_wp_date(date_gmt: str) -> str:
    """Parse WP date_gmt string to YYYY-MM-DD."""
    if not date_gmt:
        return ""
    try:
        dt = datetime.fromisoformat(date_gmt + "+00:00")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _process_article(post: dict) -> str:
    """Convert a single post dict to full Markdown content."""
    md_content = html_to_markdown(post["html_content"])
    return add_metadata_header(
        md_content,
        title=post["title"],
        published=post["published"],
        author=AUTHOR,
        source_url=post["url"],
        source_type="article",
        source_collection=SOURCE_COLLECTION,
    )


def fetch_ahrefs_articles(
    force: bool = False,
    limit: int = 0,
) -> dict:
    """Fetch Ahrefs blog articles and save as Markdown.

    Returns:
        {"fetched": int, "skipped": int, "total": int}
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    index = _load_index()
    existing_slugs = {entry["slug"] for entry in index}

    all_posts = _fetch_all_l4_posts()

    fetched = 0
    skipped = 0

    for post in all_posts:
        slug = post["slug"]

        if not force and slug in existing_slugs:
            skipped += 1
            continue

        if limit and fetched >= limit:
            logger.info("Reached limit of %d articles", limit)
            break

        if not post["html_content"]:
            logger.warning("%s has no content, skipping", slug)
            continue

        full_md = _process_article(post)
        md_path = OUTPUT_DIR / f"{slug}.md"
        md_path.write_text(full_md, encoding="utf-8")

        index_entry = {
            "slug": slug,
            "title": post["title"],
            "url": post["url"],
            "published": post["published"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "md_file": md_path.name,
            "source_collection": SOURCE_COLLECTION,
        }

        if force:
            index = [e for e in index if e["slug"] != slug]
        index.append(index_entry)
        existing_slugs.add(slug)

        logger.info("Done: %s", post["title"][:60])
        fetched += 1

    # Sort index by slug
    index.sort(key=lambda e: e.get("slug", ""))
    _save_index(index)

    return {"fetched": fetched, "skipped": skipped, "total": len(index)}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch Ahrefs Blog articles (L4 SEO content)"
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
    logger.info("Step 1e: Fetch Ahrefs Blog (L4 SEO content)")

    result = fetch_ahrefs_articles(force=args.force, limit=args.limit)

    logger.info(
        "Done — fetched: %d, skipped: %d, total: %d",
        result["fetched"],
        result["skipped"],
        result["total"],
    )


if __name__ == "__main__":
    main()
