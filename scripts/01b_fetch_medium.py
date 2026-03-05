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
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from scrapling.fetchers import StealthyFetcher, DynamicFetcher

logger = logging.getLogger(__name__)

# URL allowlist for SSRF prevention
_ALLOWED_MEDIUM_HOSTS = frozenset({"medium.com", "genehong.medium.com"})


def _validate_medium_url(url: str) -> None:
    """Validate URL against the Medium domain allowlist."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
    host = (parsed.hostname or "").lower()
    if not any(host == h or host.endswith("." + h) for h in _ALLOWED_MEDIUM_HOSTS):
        raise ValueError(f"URL domain not in allowlist: {host!r}")

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

    logger.info("擷取 RSS feed: %s", feed_url)
    feed = feedparser.parse(feed_url)

    if feed.bozo and not feed.entries:
        exc = getattr(feed, "bozo_exception", None)
        raise ValueError(f"RSS 解析失敗: {exc or 'unknown error'}")

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

    logger.info("RSS 回傳 %d 篇文章", len(articles))
    return articles


def _fetch_single_url(url: str, use_playwright: bool = False) -> dict:
    """Fetch a single Medium article by URL.

    Uses StealthyFetcher (TLS fingerprint spoofing) to bypass Medium 403.
    Falls back to DynamicFetcher (headless browser) on failure.

    Returns dict with: guid, title, url, published, html_content
    """
    _validate_medium_url(url)
    logger.info("擷取單篇文章: %s", url)

    if use_playwright:
        return _fetch_single_url_playwright(url)

    try:
        page = StealthyFetcher(auto_match=False).fetch(url, timeout=30000)
        if page.status != 200:
            raise ValueError(f"HTTP {page.status}")
        html = page.html_content
        result = _parse_article_html(url, html)
        # Medium uses React SSR: StealthyFetcher may return the JS shell without article body.
        # Detect shell by checking title ("Medium") or thin article content.
        if result["title"] in ("Medium", "Untitled") or _is_paywalled(result["html_content"]):
            raise ValueError(f"JS shell detected (title={result['title']!r}), needs browser render")
        return result
    except Exception as e:
        logger.info("  StealthyFetcher 失敗 (%s)，改用 DynamicFetcher: %s", e, url)
        return _fetch_single_url_playwright(url)


def _fetch_single_url_playwright(url: str) -> dict:
    """Fallback: DynamicFetcher (Scrapling's Playwright wrapper, JS-rendered)."""
    page = DynamicFetcher(auto_match=False).fetch(
        url, timeout=60000, network_idle=True, render_wait=2.0,
    )
    return _parse_article_html(url, page.html_content)


def _strip_medium_ui_elements(soup: "BeautifulSoup", base_url: str) -> None:
    """Remove Medium UI elements from parsed article soup (in-place).

    Cleans:
    - Author byline / signature blocks
    - "Press enter or click to view image in full size" accessibility text
    - Subscription CTA ("Join Medium for free", "stories in your inbox")
    - Relative URL fragments → absolute Medium URLs
    """
    from bs4 import NavigableString

    # 1. Fix relative URLs before cleaning (avoid broken links in output)
    medium_base = "https://medium.com"
    for tag in soup.find_all(href=True):
        href = tag.attrs.get("href") if tag.attrs else None
        if not href:
            continue
        if href.startswith("/?") or href.startswith("/@"):
            tag["href"] = medium_base + href
        elif href.startswith("/") and not href.startswith("//"):
            tag["href"] = medium_base + href

    # 2. Remove byline/author blocks: links containing "byline" in /?source= pattern
    #    Tightened to avoid removing author-curated "延伸閱讀" article links.
    #    Byline hrefs look like: /?source=post_page---byline--<hash>
    #    Stop list includes h1-h3 to avoid walking past headings into article content.
    _BYLINE_PATTERNS = re.compile(r'/\?source=.*byline|/@[a-zA-Z0-9_]+\?source=')
    _BLOCK_STOP = ("article", "section", "div", "header", "footer", "p", "h1", "h2", "h3")
    for a_tag in soup.find_all("a", href=True):
        href = a_tag.attrs.get("href") if a_tag.attrs else None
        if not href:
            continue
        if _BYLINE_PATTERNS.search(href):
            parent = a_tag.parent
            while parent and parent.name not in _BLOCK_STOP:
                parent = parent.parent
            if parent and parent.name in ("div", "section", "header", "footer", "h1", "h2", "h3"):
                parent.decompose()
            else:
                a_tag.decompose()

    # 3. Remove "Press enter or click to view image in full size" nodes
    _PRESS_ENTER_RE = re.compile(r'Press enter or click to view image in full size', re.IGNORECASE)
    for text_node in soup.find_all(string=_PRESS_ENTER_RE):
        parent = text_node.parent
        if parent and parent.name in ("span", "p", "div", "figcaption", "button"):
            parent.decompose()
        elif isinstance(text_node, NavigableString):
            text_node.extract()

    # 4. Remove subscription CTA blocks
    _CTA_PATTERNS = re.compile(
        r'Join Medium for free|stories in your inbox|Follow to never miss|Get unlimited access|'
        r'Read every story from|Already a member',
        re.IGNORECASE,
    )
    # 4a. Handle headings with mixed markup (e.g. <h2>Get <a>Author</a>'s stories in your inbox</h2>)
    #     find_all(string=...) only matches leaf NavigableString nodes, missing cross-tag text.
    #     Normalize whitespace (replace \xa0 non-breaking spaces) before matching.
    for heading in list(soup.find_all(["h1", "h2", "h3"])):
        normalized = heading.get_text().replace("\xa0", " ")
        if _CTA_PATTERNS.search(normalized):
            heading.decompose()

    # 4b. Handle CTA in div/section/p containers via leaf text node matching
    for text_node in soup.find_all(string=_CTA_PATTERNS):
        parent = text_node.parent
        for _ in range(4):  # max 4 levels up
            if parent is None:
                break
            if parent.name in ("div", "section", "aside", "p", "blockquote"):
                parent.decompose()
                break
            parent = parent.parent


def _parse_article_html(url: str, html: str) -> dict:
    """Parse article HTML into a metadata dict."""
    from bs4 import BeautifulSoup

    # Extract title from HTML
    title_match = re.search(r'<title[^>]*>(.+?)</title>', html, re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Untitled"
    # Clean Medium title suffix
    title = re.sub(r'\s*\|\s*by\s+.*$', '', title)
    title = re.sub(r'\s*[-–—]\s*Medium\s*$', '', title)

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

    # Extract article content using BeautifulSoup for proper DOM parsing
    soup = BeautifulSoup(html, "html.parser")
    article_tag = soup.find("article")
    if article_tag:
        article_soup = article_tag
    else:
        article_soup = soup

    # Strip Medium UI elements before converting to Markdown
    _strip_medium_ui_elements(article_soup, base_url=url)

    html_content = str(article_soup)

    return {
        "guid": url,
        "title": title,
        "url": url,
        "published": published,
        "html_content": html_content,
    }


def _scrape_article_urls_sitemap(
    sitemap_url: str = "https://genehong.medium.com/sitemap/sitemap.xml",
) -> list[str]:
    """Fetch all article URLs from Medium's sitemap.xml (fast, no JS needed)."""
    import httpx as _httpx
    _validate_medium_url(sitemap_url)
    logger.info("[Sitemap] 從 sitemap 取得完整文章清單: %s", sitemap_url)

    resp = _httpx.get(sitemap_url, follow_redirects=True, timeout=30)
    resp.raise_for_status()

    # Extract <loc> URLs that look like articles (have a slug path)
    _SKIP_PATHS = frozenset({"", "about", "followers", "following", "lists", "membership", "newsletter", "sitemap"})
    urls = []
    for loc in re.findall(r'<loc>(https://genehong\.medium\.com[^<]*)</loc>', resp.text):
        from urllib.parse import urlparse, unquote
        path = urlparse(loc).path.strip("/")
        if path and path.split("/")[0] not in _SKIP_PATHS:
            urls.append(unquote(loc))

    logger.info("[Sitemap] 共找到 %d 篇文章 URL", len(urls))
    return urls


def _scrape_article_urls_playwright(profile_url: str = "https://genehong.medium.com/") -> list[str]:
    """Use Playwright headless browser to scrape all article URLs from a Medium profile.

    Scrolls the infinite-scroll page until no new articles load, then
    returns a deduplicated list of article URLs.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
    except ImportError:
        raise RuntimeError("playwright not installed. Run: pip install playwright && playwright install chromium")

    logger.info("[Playwright] 開啟 headless browser 抓取完整文章清單: %s", profile_url)

    # Non-article paths to skip
    _SKIP_PATHS = frozenset({
        "", "about", "followers", "following", "lists",
        "membership", "newsletter", "sitemap",
    })

    def _is_article_url(href: str) -> bool:
        """Return True if href looks like a genehong Medium article."""
        try:
            from urllib.parse import urlparse
            p = urlparse(href)
            if p.netloc != "genehong.medium.com":
                return False
            path = p.path.strip("/")
            if not path:
                return False
            first_segment = path.split("/")[0]
            if first_segment in _SKIP_PATHS:
                return False
            # Skip Medium-internal UI paths
            if first_segment.startswith(("m", "_", "@")):
                return False
            return True
        except Exception:
            return False

    seen_urls: set[str] = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-TW",
        )
        page = context.new_page()
        page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)

        # Dismiss any cookie / membership popups
        try:
            page.click("text=Sign in", timeout=2000)
        except Exception:
            pass

        prev_count = -1
        stale_rounds = 0

        while stale_rounds < 3:
            # Collect all article links currently on page
            hrefs = page.eval_on_selector_all(
                "a[href]",
                "els => els.map(e => e.href)",
            )
            for href in hrefs:
                # Strip query string for dedup, keep clean URL
                clean = href.split("?")[0].rstrip("/")
                if _is_article_url(clean):
                    seen_urls.add(clean)

            current_count = len(seen_urls)
            logger.info("[Playwright] 目前找到 %d 篇（捲動中...）", current_count)

            if current_count == prev_count:
                stale_rounds += 1
            else:
                stale_rounds = 0
            prev_count = current_count

            # Scroll to bottom
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except PWTimeoutError:
                pass
            time.sleep(1.5)

        browser.close()

    results = sorted(seen_urls)
    logger.info("[Playwright] 共找到 %d 篇文章 URL", len(results))
    return results


_PAYWALL_MIN_CHARS = 500  # articles below this plain-text length are likely paywalled


def _is_paywalled(html_content: str) -> bool:
    """Return True if the article content looks like a paywall stub (< 500 plain-text chars)."""
    import re as _re
    text = _re.sub(r'<[^>]+>', ' ', html_content)
    text = _re.sub(r'\s+', ' ', text).strip()
    return len(text) < _PAYWALL_MIN_CHARS


def fetch_medium_articles(
    feed_url: str = config.MEDIUM_RSS_URL,
    extra_urls: list[str] | None = None,
    use_playwright: bool = False,
    force: bool = False,
) -> dict:
    """Fetch Medium articles and save as Markdown.

    Returns:
        {"fetched": int, "skipped": int, "paywalled": int, "total": int}
    """
    output_dir = config.RAW_MEDIUM_MD_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    index = _load_index()
    existing_guids: set[str] = set() if force else {entry["guid"] for entry in index}

    # Collect articles from RSS or full-scrape mode (sitemap → playwright fallback)
    if use_playwright:
        # 1. Try sitemap first (fast, no JS)
        try:
            all_urls = _scrape_article_urls_sitemap()
        except Exception as e:
            logger.warning("[Sitemap] 失敗 (%s)，改用 Playwright headless…", e)
            all_urls = _scrape_article_urls_playwright()

        # RSS still used to get pre-rendered content for recent articles
        articles = _parse_rss_feed(feed_url)
        rss_urls = {a["url"].split("?")[0].rstrip("/") for a in articles}
        # Only add URLs not already covered by RSS
        extra_only = [u for u in all_urls if u.split("?")[0].rstrip("/") not in rss_urls]
        extra_urls = [*(extra_urls or []), *extra_only]
    else:
        articles = _parse_rss_feed(feed_url)

    # Add extra URLs (manual additions)
    if extra_urls:
        for url in extra_urls:
            if url not in existing_guids:
                try:
                    article = _fetch_single_url(url, use_playwright=use_playwright)
                    articles.append(article)
                    time.sleep(1)  # rate limiting
                except (ValueError, RuntimeError) as e:
                    logger.warning("擷取失敗: %s — %s", url, e)
                except Exception as e:
                    logger.error("擷取意外錯誤: %s", url, exc_info=True)

    fetched = 0
    skipped = 0
    paywalled = 0

    for article in articles:
        guid = article["guid"]

        # Skip already fetched (unless --force)
        if guid in existing_guids:
            skipped += 1
            continue

        # Phase 2: Paywall detection — skip articles with too little content
        if _is_paywalled(article["html_content"]):
            logger.warning("付費牆文章，跳過: %s (%d bytes)", article["title"], len(article["html_content"]))
            paywalled += 1
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
        if force:
            # In force mode: always overwrite the canonical file
            pass
        else:
            # Incremental mode: avoid overwriting a file belonging to a different article
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

        logger.info("已擷取: %s", article["title"])
        fetched += 1

    _save_index(index)

    return {"fetched": fetched, "skipped": skipped, "paywalled": paywalled, "total": len(index)}


def main() -> None:
    parser = argparse.ArgumentParser(description="從 Medium RSS 擷取 SEO 文章")
    parser.add_argument("--url", nargs="*", default=[], help="手動加入的文章 URL")
    parser.add_argument("--playwright", action="store_true", help="用 headless browser 抓完整文章清單（突破 RSS 10 篇限制）")
    parser.add_argument("--force", action="store_true", help="重新擷取所有文章（忽略現有 index）")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logger.info("步驟 1b：擷取 Medium 文章")

    result = fetch_medium_articles(
        extra_urls=args.url or None,
        use_playwright=args.playwright,
        force=args.force,
    )

    logger.info(
        "完成 — 新擷取: %d, 跳過: %d, 付費牆: %d, 索引總計: %d",
        result["fetched"], result["skipped"], result["paywalled"], result["total"],
    )


if __name__ == "__main__":
    main()
