#!/usr/bin/env python3
"""
步骤 1d：从 Google Search Central 撷取 Case Studies

功能：
- 从列表页面解析所有 case study URL
- 逐篇抓取文章内容 HTML
- 转换为 Markdown 存入 raw_data/google_cases_markdown/
- 更新 raw_data/google_cases_index.json

rate limiting：每篇间隔 1.5 秒，避免被封锁。

用法：
    python scripts/01d_fetch_google_cases.py
    python scripts/01d_fetch_google_cases.py --force   # 重新撷取所有
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

import httpx

logger = logging.getLogger(__name__)

try:
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

from utils.html_to_markdown import html_to_markdown, add_metadata_header


SERIES_URL = "https://developers.google.com/search/case-studies?hl=zh-tw"
SOURCE_COLLECTION = "google-case-studies"
AUTHOR = "Google Search Central"
INDEX_PATH = config.ROOT_DIR / "raw_data" / "google_cases_index.json"

# Matches case study links like /search/case-studies/saramin-case-study
CASE_STUDY_LINK_PATTERN = re.compile(
    r'href="(/search/case-studies/([a-z0-9-]+-case-study))[^"]*"'
)

# devsite-article-body is the main content container on Google Developers pages
ARTICLE_BODY_PATTERN = re.compile(
    r'<div[^>]*class="[^"]*devsite-article-body[^"]*"[^>]*>(.*)',
    re.DOTALL,
)

ARTICLE_TITLE_PATTERN = re.compile(
    r'<h1[^>]*>(.*?)</h1>',
    re.DOTALL,
)


def _load_index() -> list[dict]:
    """Load existing case study index."""
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return []


def _save_index(index: list[dict]) -> None:
    """Save case study index."""
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _fetch_case_study_urls(series_url: str) -> list[dict]:
    """Fetch all case study URLs from the listing page.

    Returns list of dicts with: slug, url
    """
    logger.info("Fetching listing page: %s", series_url)

    resp = httpx.get(series_url, follow_redirects=True, timeout=30)
    resp.raise_for_status()

    seen_slugs: set[str] = set()
    cases: list[dict] = []

    for _path, slug in CASE_STUDY_LINK_PATTERN.findall(resp.text):
        if slug not in seen_slugs:
            seen_slugs.add(slug)
            full_url = f"https://developers.google.com/search/case-studies/{slug}?hl=zh-tw"
            cases.append({
                "slug": slug,
                "url": full_url,
            })

    logger.info("Found %d case studies", len(cases))
    return cases


def _extract_article_body(html: str) -> str:
    """Extract the main article body HTML from a Google Developers page."""
    match = ARTICLE_BODY_PATTERN.search(html)
    if not match:
        return ""

    body = match.group(1)

    # Find the end of devsite-article-body div by tracking nesting
    # Simple heuristic: cut at common footer markers
    for marker in [
        '<devsite-feedback',
        '<div class="devsite-content-footer',
        '<footer',
    ]:
        idx = body.find(marker)
        if idx != -1:
            body = body[:idx]
            break

    return body


def _fetch_case_study(url: str) -> dict:
    """Fetch a single case study page and extract content.

    Returns dict with: title, html_content
    """
    resp = httpx.get(url, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    html = resp.text

    # Extract title
    title = "Untitled"
    title_match = ARTICLE_TITLE_PATTERN.search(html)
    if title_match:
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()

    # Extract article body
    html_content = _extract_article_body(html)

    return {
        "title": title,
        "html_content": html_content,
    }


def fetch_google_cases(
    series_url: str = SERIES_URL,
    force: bool = False,
) -> dict:
    """Fetch Google case studies and save as Markdown.

    Returns:
        {"fetched": int, "skipped": int, "total": int}
    """
    output_dir = config.RAW_GOOGLE_CASES_MD_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    index = _load_index()
    existing_slugs = {entry["slug"] for entry in index}

    # Get all case study URLs
    case_metas = _fetch_case_study_urls(series_url)

    fetched = 0
    skipped = 0

    for meta in case_metas:
        slug = meta["slug"]

        if not force and slug in existing_slugs:
            skipped += 1
            continue

        try:
            case = _fetch_case_study(meta["url"])
        except httpx.HTTPError as e:
            logger.warning("%s fetch failed: %s", slug, e)
            continue
        except Exception as e:
            logger.error("%s unexpected error", slug, exc_info=True)
            continue

        if not case["html_content"]:
            logger.warning("%s has no content, skipping", slug)
            continue

        # Convert HTML to Markdown
        md_content = html_to_markdown(case["html_content"])

        # Add metadata header
        full_md = add_metadata_header(
            md_content,
            title=case["title"],
            published="",  # Google doesn't show publish date on case studies
            author=AUTHOR,
            source_url=meta["url"],
            source_type="article",
            source_collection=SOURCE_COLLECTION,
        )

        md_path = output_dir / f"{slug}.md"
        md_path.write_text(full_md, encoding="utf-8")

        # Update index
        index_entry = {
            "slug": slug,
            "title": case["title"],
            "url": meta["url"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "md_file": md_path.name,
            "source_collection": SOURCE_COLLECTION,
        }

        # Replace if force, otherwise append
        if force:
            index = [e for e in index if e["slug"] != slug]
        index.append(index_entry)
        existing_slugs.add(slug)

        logger.info("Done: %s", case["title"][:60])
        fetched += 1

        # Rate limiting
        time.sleep(1.5)

    # Sort index by slug
    index.sort(key=lambda e: e.get("slug", ""))
    _save_index(index)

    return {"fetched": fetched, "skipped": skipped, "total": len(index)}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch Google Search Central case studies"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-fetch all case studies"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logger.info("Step 1d: Fetch Google Search Central Case Studies")

    result = fetch_google_cases(force=args.force)

    logger.info(
        "Done — fetched: %d, skipped: %d, total: %d",
        result["fetched"], result["skipped"], result["total"],
    )


if __name__ == "__main__":
    main()
