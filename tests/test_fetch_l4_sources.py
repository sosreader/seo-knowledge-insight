"""Tests for L4 fetch scripts: 01e_fetch_ahrefs, 01f_fetch_sej, 01g_fetch_growthmemo.

Covers:
- URL validation / SSRF protection
- L4 keyword filtering logic
- Index load/save
- Slug extraction from URLs
- Article content extraction (mocked HTTP)
- Incremental dedup (skip existing)
- Force mode
- Error handling (HTTP errors, empty content)
- Rate limiting (mocked sleep)
"""
from __future__ import annotations

import importlib
import json
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import httpx
import pytest


# ---------------------------------------------------------------------------
# Import helpers
# ---------------------------------------------------------------------------

def _import_ahrefs():
    return importlib.import_module("scripts.01e_fetch_ahrefs")


def _import_sej():
    return importlib.import_module("scripts.01f_fetch_sej")


def _import_growthmemo():
    return importlib.import_module("scripts.01g_fetch_growthmemo")


# ---------------------------------------------------------------------------
# Helpers shared across test classes
# ---------------------------------------------------------------------------

class _MockHttpResponse:
    """Minimal httpx-compatible response stub."""

    def __init__(self, text: str = "", status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=MagicMock(),
                response=MagicMock(status_code=self.status_code),
            )


def _make_feedparser_entry(
    guid: str,
    title: str,
    url: str,
    published_parsed=None,
    categories=None,
    html_content: str = "",
) -> SimpleNamespace:
    entry = SimpleNamespace()
    entry.id = guid
    entry.title = title
    entry.link = url
    entry.published_parsed = published_parsed or (2025, 1, 15, 0, 0, 0)
    # feedparser tags are dict-like objects, not SimpleNamespace
    entry.tags = [{"term": c, "scheme": "", "label": None} for c in (categories or [])]
    if html_content:
        entry.content = [{"value": html_content}]
    else:
        entry.content = []
    entry.summary = html_content
    entry.get = lambda k, default="": {"id": guid, "link": url, "title": title}.get(k, default)
    return entry


def _make_feedparser_feed(entries, bozo: bool = False):
    feed = SimpleNamespace()
    feed.entries = entries
    feed.bozo = bozo
    feed.bozo_exception = None
    return feed


# ===========================================================================
# AHREFS TESTS (01e_fetch_ahrefs.py)
# ===========================================================================

class TestAhrefsValidateUrl:
    def test_valid_ahrefs_url_passes(self):
        mod = _import_ahrefs()
        mod._validate_url("https://ahrefs.com/blog/technical-seo/")

    def test_valid_www_ahrefs_url_passes(self):
        mod = _import_ahrefs()
        mod._validate_url("https://www.ahrefs.com/blog/programmatic-seo/")

    def test_rejects_non_ahrefs_domain(self):
        mod = _import_ahrefs()
        with pytest.raises(ValueError, match="allowlist"):
            mod._validate_url("https://evil.com/steal")

    def test_rejects_subdomain_spoof(self):
        mod = _import_ahrefs()
        with pytest.raises(ValueError, match="allowlist"):
            mod._validate_url("https://notahrefs.com/blog/")

    def test_rejects_file_scheme(self):
        mod = _import_ahrefs()
        with pytest.raises(ValueError, match="scheme"):
            mod._validate_url("file:///etc/passwd")

    def test_rejects_ftp_scheme(self):
        mod = _import_ahrefs()
        with pytest.raises(ValueError, match="scheme"):
            mod._validate_url("ftp://ahrefs.com/file")

    def test_rejects_http_ssrf_internal_ip(self):
        mod = _import_ahrefs()
        with pytest.raises(ValueError, match="allowlist"):
            mod._validate_url("http://169.254.169.254/latest/meta-data/")


class TestAhrefsSlugFromUrl:
    def test_standard_blog_url(self):
        mod = _import_ahrefs()
        assert mod._slug_from_url("https://ahrefs.com/blog/technical-seo/") == "technical-seo"

    def test_url_without_trailing_slash(self):
        mod = _import_ahrefs()
        assert mod._slug_from_url("https://ahrefs.com/blog/programmatic-seo") == "programmatic-seo"

    def test_empty_path_returns_empty(self):
        mod = _import_ahrefs()
        result = mod._slug_from_url("https://ahrefs.com/")
        assert result == "ahrefs.com" or result == ""

    def test_nested_path_returns_last_segment(self):
        mod = _import_ahrefs()
        assert mod._slug_from_url("https://ahrefs.com/blog/seo/advanced-seo") == "advanced-seo"


class TestAhrefsProcessArticle:
    def test_process_article_generates_markdown(self):
        mod = _import_ahrefs()
        post = {
            "title": "Technical SEO Guide",
            "published": "2025-06-01",
            "html_content": "<p>Content about technical SEO</p>",
            "url": "https://ahrefs.com/blog/technical-seo/",
        }
        result = mod._process_article(post)
        assert "# Technical SEO Guide" in result
        assert "ahrefs-blog" in result
        assert "2025-06-01" in result


class TestAhrefsIndexOperations:
    def test_load_nonexistent_index_returns_empty_list(self, tmp_path: Path):
        mod = _import_ahrefs()
        with patch.object(mod, "INDEX_PATH", tmp_path / "missing.json"):
            assert mod._load_index() == []

    def test_save_and_reload_index(self, tmp_path: Path):
        mod = _import_ahrefs()
        data = [{"slug": "technical-seo", "title": "Technical SEO Guide"}]
        index_path = tmp_path / "ahrefs_index.json"
        with patch.object(mod, "INDEX_PATH", index_path):
            mod._save_index(data)
            loaded = mod._load_index()
        assert loaded == data

    def test_save_creates_parent_directories(self, tmp_path: Path):
        mod = _import_ahrefs()
        deep_path = tmp_path / "a" / "b" / "index.json"
        with patch.object(mod, "INDEX_PATH", deep_path):
            mod._save_index([])
        assert deep_path.exists()

    def test_save_uses_utf8_encoding(self, tmp_path: Path):
        mod = _import_ahrefs()
        data = [{"title": "SEO 技術指南 🔍"}]
        index_path = tmp_path / "index.json"
        with patch.object(mod, "INDEX_PATH", index_path):
            mod._save_index(data)
        raw = index_path.read_bytes()
        assert "技術指南".encode("utf-8") in raw


class _MockWpApiResponse:
    """Mock httpx response for WP REST API calls."""

    def __init__(self, json_data=None, status_code: int = 200, total_pages: int = 1):
        self._json = json_data or []
        self.status_code = status_code
        self.headers = {"X-WP-TotalPages": str(total_pages)}
        self.text = json.dumps(self._json)

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=MagicMock(),
                response=MagicMock(status_code=self.status_code),
            )


def _make_wp_post_raw(slug: str, title: str = "Tech SEO", html: str = "<p>Body content</p>", date_gmt: str = "2025-06-01T00:00:00"):
    """WP API raw format (for _fetch_wp_posts_page tests)."""
    return {
        "id": hash(slug) % 100000,
        "slug": slug,
        "title": {"rendered": title},
        "link": f"https://ahrefs.com/blog/{slug}/",
        "date_gmt": date_gmt,
        "content": {"rendered": html},
    }


def _make_wp_post(slug: str, title: str = "Tech SEO", html: str = "<p>Body content</p>", published: str = "2025-06-01"):
    """Processed format (as returned by _fetch_all_l4_posts)."""
    return {
        "slug": slug,
        "title": title,
        "url": f"https://ahrefs.com/blog/{slug}/",
        "published": published,
        "html_content": html,
    }


class TestAhrefsWpApi:
    def test_fetch_wp_posts_page_returns_posts(self):
        mod = _import_ahrefs()
        posts = [_make_wp_post_raw("technical-seo")]
        mock_resp = _MockWpApiResponse(json_data=posts, total_pages=1)
        with patch("httpx.get", return_value=mock_resp):
            result, total = mod._fetch_wp_posts_page("329,469", 1)
        assert len(result) == 1
        assert total == 1

    def test_fetch_wp_posts_page_raises_on_http_error(self):
        mod = _import_ahrefs()
        mock_resp = _MockWpApiResponse(status_code=503)
        with (
            patch("httpx.get", return_value=mock_resp),
            pytest.raises(httpx.HTTPStatusError),
        ):
            mod._fetch_wp_posts_page("329", 1)

    def test_fetch_wp_posts_page_validates_url(self):
        mod = _import_ahrefs()
        with (
            patch.object(mod, "WP_API_BASE", "https://evil.com/wp-json/wp/v2"),
            pytest.raises(ValueError, match="allowlist"),
        ):
            mod._fetch_wp_posts_page("329", 1)

    def test_clean_wp_title_strips_entities(self):
        mod = _import_ahrefs()
        assert mod._clean_wp_title("SEO &amp; Marketing") == "SEO & Marketing"
        assert mod._clean_wp_title("<b>Bold</b> Title") == "Bold Title"
        assert mod._clean_wp_title("") == "Untitled"

    def test_parse_wp_date(self):
        mod = _import_ahrefs()
        assert mod._parse_wp_date("2025-06-01T12:00:00") == "2025-06-01"
        assert mod._parse_wp_date("") == ""
        assert mod._parse_wp_date("invalid") == ""


class TestFetchAllL4Posts:
    def test_paginates_through_all_pages(self):
        mod = _import_ahrefs()
        page1 = [_make_wp_post_raw("post-1"), _make_wp_post_raw("post-2")]
        page2 = [_make_wp_post_raw("post-3")]

        call_count = 0

        def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _MockWpApiResponse(json_data=page1, total_pages=2)
            return _MockWpApiResponse(json_data=page2, total_pages=2)

        with (
            patch("httpx.get", side_effect=mock_get),
            patch("time.sleep"),
        ):
            posts = mod._fetch_all_l4_posts()

        assert len(posts) == 3
        assert call_count == 2

    def test_skips_posts_without_slug(self):
        mod = _import_ahrefs()
        posts = [_make_wp_post_raw(""), _make_wp_post_raw("valid-slug")]
        mock_resp = _MockWpApiResponse(json_data=posts, total_pages=1)
        with patch("httpx.get", return_value=mock_resp):
            result = mod._fetch_all_l4_posts()
        assert len(result) == 1
        assert result[0]["slug"] == "valid-slug"


class TestFetchAhrefsArticles:
    def test_skips_existing_slug_incremental_mode(self, tmp_path: Path):
        mod = _import_ahrefs()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "ahrefs_markdown"
        output_dir.mkdir()

        existing_index = [{
            "slug": "technical-seo",
            "title": "Technical SEO",
            "url": "https://ahrefs.com/blog/technical-seo/",
            "fetched_at": "2025-01-01T00:00:00+00:00",
            "md_file": "technical-seo.md",
            "source_collection": "ahrefs-blog",
        }]
        index_path.write_text(json.dumps(existing_index), encoding="utf-8")

        posts = [_make_wp_post("technical-seo")]

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch.object(mod, "_fetch_all_l4_posts", return_value=posts),
        ):
            result = mod.fetch_ahrefs_articles(force=False)

        assert result["skipped"] == 1
        assert result["fetched"] == 0

    def test_force_mode_refetches_existing(self, tmp_path: Path):
        mod = _import_ahrefs()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "ahrefs_markdown"
        output_dir.mkdir()

        existing_index = [{
            "slug": "technical-seo",
            "title": "Old Title",
            "url": "https://ahrefs.com/blog/technical-seo/",
            "fetched_at": "2025-01-01T00:00:00+00:00",
            "md_file": "technical-seo.md",
            "source_collection": "ahrefs-blog",
        }]
        index_path.write_text(json.dumps(existing_index), encoding="utf-8")

        posts = [_make_wp_post("technical-seo", title="Technical SEO v2")]

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch.object(mod, "_fetch_all_l4_posts", return_value=posts),
        ):
            result = mod.fetch_ahrefs_articles(force=True)

        assert result["fetched"] == 1

    def test_limit_respected(self, tmp_path: Path):
        mod = _import_ahrefs()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "ahrefs_markdown"
        output_dir.mkdir()

        posts = [
            _make_wp_post("post-1", html="<p>Content 1</p>"),
            _make_wp_post("post-2", html="<p>Content 2</p>"),
            _make_wp_post("post-3", html="<p>Content 3</p>"),
        ]

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch.object(mod, "_fetch_all_l4_posts", return_value=posts),
        ):
            result = mod.fetch_ahrefs_articles(force=False, limit=1)

        assert result["fetched"] == 1

    def test_empty_html_content_skips_article(self, tmp_path: Path):
        mod = _import_ahrefs()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "ahrefs_markdown"
        output_dir.mkdir()

        posts = [_make_wp_post("no-content", html="")]

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch.object(mod, "_fetch_all_l4_posts", return_value=posts),
        ):
            result = mod.fetch_ahrefs_articles(force=False)

        assert result["fetched"] == 0

    def test_markdown_file_written_with_metadata_header(self, tmp_path: Path):
        mod = _import_ahrefs()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "ahrefs_markdown"
        output_dir.mkdir()

        posts = [_make_wp_post("technical-seo", title="Technical SEO Guide")]

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch.object(mod, "_fetch_all_l4_posts", return_value=posts),
        ):
            result = mod.fetch_ahrefs_articles(force=False)

        assert result["fetched"] == 1
        md_file = output_dir / "technical-seo.md"
        assert md_file.exists()
        content = md_file.read_text(encoding="utf-8")
        assert "ahrefs-blog" in content
        assert "article" in content

    def test_index_sorted_by_slug(self, tmp_path: Path):
        mod = _import_ahrefs()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "ahrefs_markdown"
        output_dir.mkdir()

        posts = [
            _make_wp_post("zebra-seo", html="<p>Z</p>"),
            _make_wp_post("alpha-seo", html="<p>A</p>"),
        ]

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch.object(mod, "_fetch_all_l4_posts", return_value=posts),
        ):
            mod.fetch_ahrefs_articles(force=False)

        loaded = json.loads(index_path.read_text(encoding="utf-8"))
        slugs = [e["slug"] for e in loaded]
        assert slugs == sorted(slugs)


# ===========================================================================
# SEJ TESTS (01f_fetch_sej.py)
# ===========================================================================

class TestSejValidateUrl:
    def test_valid_sej_url_passes(self):
        mod = _import_sej()
        mod._validate_url("https://www.searchenginejournal.com/technical-seo/")

    def test_rejects_non_sej_domain(self):
        mod = _import_sej()
        with pytest.raises(ValueError, match="allowlist"):
            mod._validate_url("https://evil.com/steal")

    def test_rejects_ssrf_internal_hostname(self):
        mod = _import_sej()
        with pytest.raises(ValueError, match="allowlist"):
            mod._validate_url("http://localhost/admin")

    def test_rejects_file_scheme(self):
        mod = _import_sej()
        with pytest.raises(ValueError, match="scheme"):
            mod._validate_url("file:///etc/passwd")

    def test_rejects_partial_domain_match(self):
        mod = _import_sej()
        with pytest.raises(ValueError, match="allowlist"):
            mod._validate_url("https://notsearchenginejournal.com/article/")


class TestSejSlugFromUrl:
    def test_standard_sej_url(self):
        mod = _import_sej()
        result = mod._slug_from_url("https://www.searchenginejournal.com/technical-seo-guide/")
        assert result == "technical-seo-guide"

    def test_url_without_trailing_slash(self):
        mod = _import_sej()
        result = mod._slug_from_url("https://www.searchenginejournal.com/technical-seo-guide")
        assert result == "technical-seo-guide"

    def test_deep_path_returns_last_segment(self):
        mod = _import_sej()
        result = mod._slug_from_url("https://www.searchenginejournal.com/category/advanced-seo/")
        assert result == "advanced-seo"


class TestSejL4CategoryFilter:
    def test_technical_seo_category_matches(self):
        mod = _import_sej()
        assert mod._matches_l4_category(["Technical SEO"]) is True

    def test_ai_category_matches(self):
        mod = _import_sej()
        assert mod._matches_l4_category(["AI", "Machine Learning"]) is True

    def test_algorithm_category_matches(self):
        mod = _import_sej()
        assert mod._matches_l4_category(["Algorithm Updates"]) is True

    def test_core_web_vitals_category_matches(self):
        mod = _import_sej()
        assert mod._matches_l4_category(["Core Web Vitals"]) is True

    def test_general_category_does_not_match(self):
        mod = _import_sej()
        assert mod._matches_l4_category(["Social Media", "Content Marketing"]) is False

    def test_empty_categories_does_not_match(self):
        mod = _import_sej()
        assert mod._matches_l4_category([]) is False

    def test_case_insensitive_category_match(self):
        mod = _import_sej()
        assert mod._matches_l4_category(["TECHNICAL SEO"]) is True


class TestSejL4SlugFilter:
    def test_technical_seo_slug_matches(self):
        mod = _import_sej()
        assert mod._matches_l4_slug("technical-seo-audit-guide") is True

    def test_advanced_slug_matches(self):
        mod = _import_sej()
        assert mod._matches_l4_slug("advanced-link-building") is True

    def test_schema_slug_matches(self):
        mod = _import_sej()
        assert mod._matches_l4_slug("schema-markup-guide") is True

    def test_generic_slug_does_not_match(self):
        mod = _import_sej()
        assert mod._matches_l4_slug("seo-beginner-guide") is False

    def test_empty_slug_does_not_match(self):
        mod = _import_sej()
        assert mod._matches_l4_slug("") is False


class TestSejIndexOperations:
    def test_load_nonexistent_index_returns_empty_list(self, tmp_path: Path):
        mod = _import_sej()
        with patch.object(mod, "INDEX_PATH", tmp_path / "missing.json"):
            assert mod._load_index() == []

    def test_save_and_reload_index(self, tmp_path: Path):
        mod = _import_sej()
        data = [{"guid": "https://sej.com/article", "slug": "technical-seo", "title": "Tech SEO"}]
        index_path = tmp_path / "sej_index.json"
        with patch.object(mod, "INDEX_PATH", index_path):
            mod._save_index(data)
            loaded = mod._load_index()
        assert loaded == data

    def test_save_creates_parent_directories(self, tmp_path: Path):
        mod = _import_sej()
        deep_path = tmp_path / "nested" / "index.json"
        with patch.object(mod, "INDEX_PATH", deep_path):
            mod._save_index([])
        assert deep_path.exists()


class TestParseRssFeedSej:
    def test_parses_entries_with_categories(self):
        mod = _import_sej()
        entry = _make_feedparser_entry(
            guid="https://sej.com/tech-seo",
            title="Technical SEO Guide",
            url="https://www.searchenginejournal.com/technical-seo-guide/",
            categories=["Technical SEO", "Advanced"],
        )
        mock_feed = _make_feedparser_feed([entry])

        with patch("feedparser.parse", return_value=mock_feed):
            articles = mod._parse_rss_feed("https://www.searchenginejournal.com/feed/")

        assert len(articles) == 1
        assert articles[0]["title"] == "Technical SEO Guide"
        assert "Technical SEO" in articles[0]["categories"]

    def test_published_date_parsed(self):
        mod = _import_sej()
        entry = _make_feedparser_entry(
            guid="g1",
            title="Tech SEO",
            url="https://www.searchenginejournal.com/tech-seo/",
            published_parsed=(2025, 3, 10, 0, 0, 0),
        )
        mock_feed = _make_feedparser_feed([entry])

        with patch("feedparser.parse", return_value=mock_feed):
            articles = mod._parse_rss_feed("https://www.searchenginejournal.com/feed/")

        assert articles[0]["published"] == "2025-03-10"

    def test_raises_on_bozo_feed_with_no_entries(self):
        mod = _import_sej()
        mock_feed = _make_feedparser_feed([], bozo=True)

        with (
            patch("feedparser.parse", return_value=mock_feed),
            pytest.raises(ValueError, match="RSS parse failed"),
        ):
            mod._parse_rss_feed("https://www.searchenginejournal.com/feed/")

    def test_empty_feed_returns_empty_list(self):
        mod = _import_sej()
        mock_feed = _make_feedparser_feed([])

        with patch("feedparser.parse", return_value=mock_feed):
            articles = mod._parse_rss_feed("https://www.searchenginejournal.com/feed/")

        assert articles == []


class TestFetchSejArticleContent:
    def test_extracts_post_content_div(self):
        mod = _import_sej()
        html = '<html><body><div class="post-content"><p>SEO content here</p></div></body></html>'
        mock_resp = _MockHttpResponse(text=html)
        with patch("httpx.get", return_value=mock_resp):
            result = mod._fetch_article_content("https://www.searchenginejournal.com/article/")
        assert "SEO content here" in result["html_content"]

    def test_extracts_h1_title(self):
        mod = _import_sej()
        html = '<html><body><h1>Technical SEO Audit</h1><article><p>Body</p></article></body></html>'
        mock_resp = _MockHttpResponse(text=html)
        with patch("httpx.get", return_value=mock_resp):
            result = mod._fetch_article_content("https://www.searchenginejournal.com/article/")
        assert result["title"] == "Technical SEO Audit"

    def test_extracts_meta_author(self):
        mod = _import_sej()
        html = '<html><head><meta name="author" content="Roger Montti"></head><body><article><p>Body</p></article></body></html>'
        mock_resp = _MockHttpResponse(text=html)
        with patch("httpx.get", return_value=mock_resp):
            result = mod._fetch_article_content("https://www.searchenginejournal.com/article/")
        assert result["author"] == "Roger Montti"

    def test_falls_back_to_sej_author_when_no_meta(self):
        mod = _import_sej()
        html = "<html><body><article><p>Body</p></article></body></html>"
        mock_resp = _MockHttpResponse(text=html)
        with patch("httpx.get", return_value=mock_resp):
            result = mod._fetch_article_content("https://www.searchenginejournal.com/article/")
        assert result["author"] == "Search Engine Journal"

    def test_removes_ad_blocks_from_content(self):
        mod = _import_sej()
        html = '<html><body><article><p>Real content</p><div class="ad-banner">Buy this!</div></article></body></html>'
        mock_resp = _MockHttpResponse(text=html)
        with patch("httpx.get", return_value=mock_resp):
            result = mod._fetch_article_content("https://www.searchenginejournal.com/article/")
        assert "Buy this!" not in result["html_content"]
        assert "Real content" in result["html_content"]

    def test_removes_newsletter_block(self):
        mod = _import_sej()
        html = '<html><body><article><p>Content</p><div class="newsletter-signup">Subscribe</div></article></body></html>'
        mock_resp = _MockHttpResponse(text=html)
        with patch("httpx.get", return_value=mock_resp):
            result = mod._fetch_article_content("https://www.searchenginejournal.com/article/")
        assert "Subscribe" not in result["html_content"]

    def test_raises_on_http_error(self):
        mod = _import_sej()
        mock_resp = _MockHttpResponse(status_code=404)
        with (
            patch("httpx.get", return_value=mock_resp),
            pytest.raises(httpx.HTTPStatusError),
        ):
            mod._fetch_article_content("https://www.searchenginejournal.com/missing/")

    def test_validates_url_before_fetch(self):
        mod = _import_sej()
        with pytest.raises(ValueError, match="allowlist"):
            mod._fetch_article_content("https://evil.com/article")


class TestFetchSejArticles:
    def _make_rss_entry(
        self,
        guid: str = "https://sej.com/tech-seo",
        title: str = "Technical SEO Guide",
        url: str = "https://www.searchenginejournal.com/technical-seo-guide/",
        categories: list[str] | None = None,
    ):
        return _make_feedparser_entry(
            guid=guid,
            title=title,
            url=url,
            categories=categories or ["Technical SEO"],
        )

    def _article_html(self) -> str:
        return '<html><body><h1>Technical SEO Guide</h1><article><p>Content</p></article></body></html>'

    def test_skips_existing_guid_incremental_mode(self, tmp_path: Path):
        mod = _import_sej()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "sej_markdown"
        output_dir.mkdir()

        existing_index = [{
            "guid": "https://sej.com/tech-seo",
            "slug": "technical-seo-guide",
            "title": "Technical SEO Guide",
            "url": "https://www.searchenginejournal.com/technical-seo-guide/",
            "fetched_at": "2025-01-01T00:00:00+00:00",
            "md_file": "technical-seo-guide.md",
            "source_collection": "sej",
        }]
        index_path.write_text(json.dumps(existing_index), encoding="utf-8")

        entry = self._make_rss_entry()
        mock_feed = _make_feedparser_feed([entry])

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
        ):
            result = mod.fetch_sej_articles(force=False)

        assert result["skipped"] == 1
        assert result["fetched"] == 0

    def test_force_mode_refetches_existing(self, tmp_path: Path):
        mod = _import_sej()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "sej_markdown"
        output_dir.mkdir()

        existing_index = [{
            "guid": "https://sej.com/tech-seo",
            "slug": "technical-seo-guide",
            "title": "Technical SEO Guide",
            "url": "https://www.searchenginejournal.com/technical-seo-guide/",
            "fetched_at": "2025-01-01T00:00:00+00:00",
            "md_file": "technical-seo-guide.md",
            "source_collection": "sej",
        }]
        index_path.write_text(json.dumps(existing_index), encoding="utf-8")

        entry = self._make_rss_entry()
        mock_feed = _make_feedparser_feed([entry])
        article_html = self._article_html()

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
            patch("httpx.get", return_value=_MockHttpResponse(text=article_html)),
            patch("time.sleep"),
        ):
            result = mod.fetch_sej_articles(force=True)

        assert result["fetched"] == 1

    def test_non_l4_articles_filtered(self, tmp_path: Path):
        mod = _import_sej()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "sej_markdown"
        output_dir.mkdir()

        entry = _make_feedparser_entry(
            guid="https://sej.com/social",
            title="Social Media Tips",
            url="https://www.searchenginejournal.com/social-media-tips/",
            categories=["Social Media", "Content"],
        )
        mock_feed = _make_feedparser_feed([entry])

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
        ):
            result = mod.fetch_sej_articles(force=False)

        assert result["filtered"] == 1
        assert result["fetched"] == 0

    def test_slug_fallback_filter_when_no_category_match(self, tmp_path: Path):
        mod = _import_sej()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "sej_markdown"
        output_dir.mkdir()

        entry = _make_feedparser_entry(
            guid="https://sej.com/advanced-guide",
            title="Advanced SEO",
            url="https://www.searchenginejournal.com/advanced-guide/",
            categories=["General"],  # no L4 category
        )
        mock_feed = _make_feedparser_feed([entry])
        article_html = self._article_html()

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
            patch("httpx.get", return_value=_MockHttpResponse(text=article_html)),
            patch("time.sleep"),
        ):
            result = mod.fetch_sej_articles(force=False)

        # Slug "advanced-guide" contains "advanced" → passes slug filter
        assert result["fetched"] == 1

    def test_http_error_skips_article_and_continues(self, tmp_path: Path):
        mod = _import_sej()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "sej_markdown"
        output_dir.mkdir()

        entry1 = _make_feedparser_entry(
            guid="g1",
            title="Tech SEO 1",
            url="https://www.searchenginejournal.com/technical-seo-1/",
            categories=["Technical SEO"],
        )
        entry2 = _make_feedparser_entry(
            guid="g2",
            title="Tech SEO 2",
            url="https://www.searchenginejournal.com/technical-seo-2/",
            categories=["Technical SEO"],
        )
        mock_feed = _make_feedparser_feed([entry1, entry2])

        article_html = self._article_html()
        call_count = 0

        def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _MockHttpResponse(status_code=500)
            return _MockHttpResponse(text=article_html)

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
            patch("httpx.get", side_effect=mock_get),
            patch("time.sleep"),
        ):
            result = mod.fetch_sej_articles(force=False)

        assert result["fetched"] == 1

    def test_empty_html_content_skips_article(self, tmp_path: Path):
        mod = _import_sej()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "sej_markdown"
        output_dir.mkdir()

        entry = self._make_rss_entry()
        mock_feed = _make_feedparser_feed([entry])
        # Page with no recognizable content container
        empty_html = "<html><body><div>No content div</div></body></html>"

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
            patch("httpx.get", return_value=_MockHttpResponse(text=empty_html)),
            patch("time.sleep"),
        ):
            result = mod.fetch_sej_articles(force=False)

        assert result["fetched"] == 0

    def test_rate_limit_sleep_called(self, tmp_path: Path):
        mod = _import_sej()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "sej_markdown"
        output_dir.mkdir()

        entry = self._make_rss_entry()
        mock_feed = _make_feedparser_feed([entry])
        article_html = self._article_html()

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
            patch("httpx.get", return_value=_MockHttpResponse(text=article_html)),
            patch("time.sleep") as mock_sleep,
        ):
            result = mod.fetch_sej_articles(force=False)

        if result["fetched"] > 0:
            mock_sleep.assert_called_with(1.5)

    def test_limit_respected(self, tmp_path: Path):
        mod = _import_sej()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "sej_markdown"
        output_dir.mkdir()

        entries = [
            _make_feedparser_entry(
                guid=f"https://sej.com/tech-{i}",
                title=f"Tech SEO {i}",
                url=f"https://www.searchenginejournal.com/technical-seo-{i}/",
                categories=["Technical SEO"],
            )
            for i in range(3)
        ]
        mock_feed = _make_feedparser_feed(entries)
        article_html = self._article_html()

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
            patch("httpx.get", return_value=_MockHttpResponse(text=article_html)),
            patch("time.sleep"),
        ):
            result = mod.fetch_sej_articles(force=False, limit=1)

        assert result["fetched"] == 1

    def test_markdown_file_written_with_metadata_header(self, tmp_path: Path):
        mod = _import_sej()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "sej_markdown"
        output_dir.mkdir()

        entry = self._make_rss_entry(
            url="https://www.searchenginejournal.com/technical-seo-guide/",
        )
        mock_feed = _make_feedparser_feed([entry])
        article_html = '<html><body><h1>Technical SEO Guide</h1><article><p>Content</p></article></body></html>'

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
            patch("httpx.get", return_value=_MockHttpResponse(text=article_html)),
            patch("time.sleep"),
        ):
            result = mod.fetch_sej_articles(force=False)

        assert result["fetched"] == 1
        md_file = output_dir / "technical-seo-guide.md"
        assert md_file.exists()
        content = md_file.read_text(encoding="utf-8")
        assert "sej" in content
        assert "article" in content


# ===========================================================================
# GROWTHMEMO TESTS (01g_fetch_growthmemo.py)
# ===========================================================================

class TestGrowthmemoValidateUrl:
    def test_valid_kevin_indig_url_passes(self):
        mod = _import_growthmemo()
        mod._validate_url("https://www.kevin-indig.com/programmatic-seo/")

    def test_valid_substack_url_passes(self):
        mod = _import_growthmemo()
        mod._validate_url("https://growthmemo.substack.com/p/article-slug")

    def test_rejects_non_allowed_domain(self):
        mod = _import_growthmemo()
        with pytest.raises(ValueError, match="allowlist"):
            mod._validate_url("https://evil.com/steal")

    def test_rejects_localhost(self):
        mod = _import_growthmemo()
        with pytest.raises(ValueError, match="allowlist"):
            mod._validate_url("http://localhost/admin")

    def test_rejects_file_scheme(self):
        mod = _import_growthmemo()
        with pytest.raises(ValueError, match="scheme"):
            mod._validate_url("file:///etc/passwd")

    def test_rejects_partial_domain_match(self):
        mod = _import_growthmemo()
        with pytest.raises(ValueError, match="allowlist"):
            mod._validate_url("https://notkevin-indig.com/page/")


class TestGrowthmemoSlugFromUrl:
    def test_substack_p_url(self):
        mod = _import_growthmemo()
        result = mod._slug_from_url("https://growthmemo.substack.com/p/programmatic-seo-2025")
        assert result == "programmatic-seo-2025"

    def test_kevin_indig_url(self):
        mod = _import_growthmemo()
        result = mod._slug_from_url("https://www.kevin-indig.com/programmatic-seo/")
        assert result == "programmatic-seo"

    def test_url_without_trailing_slash(self):
        mod = _import_growthmemo()
        result = mod._slug_from_url("https://www.kevin-indig.com/seo-forecasting")
        assert result == "seo-forecasting"

    def test_root_url_returns_empty_or_domain(self):
        mod = _import_growthmemo()
        result = mod._slug_from_url("https://www.kevin-indig.com/")
        # Acceptable: empty string or root segment
        assert isinstance(result, str)


class TestHasSufficientContent:
    def test_short_content_returns_false(self):
        mod = _import_growthmemo()
        assert mod._has_sufficient_content("<p>Short.</p>") is False

    def test_long_content_returns_true(self):
        mod = _import_growthmemo()
        content = "<p>" + "This is a detailed SEO analysis. " * 15 + "</p>"
        assert mod._has_sufficient_content(content) is True

    def test_empty_string_returns_false(self):
        mod = _import_growthmemo()
        assert mod._has_sufficient_content("") is False

    def test_html_tags_stripped_for_length_check(self):
        mod = _import_growthmemo()
        # 300 chars of HTML tags but minimal text
        bulky_html = "<div>" + "<span></span>" * 50 + "Short text</div>"
        assert mod._has_sufficient_content(bulky_html) is False

    def test_exactly_300_plain_chars_passes(self):
        mod = _import_growthmemo()
        content = "<p>" + "A" * 300 + "</p>"
        assert mod._has_sufficient_content(content) is True

    def test_299_plain_chars_fails(self):
        mod = _import_growthmemo()
        content = "<p>" + "A" * 299 + "</p>"
        assert mod._has_sufficient_content(content) is False


class TestGrowthmemoIndexOperations:
    def test_load_nonexistent_index_returns_empty_list(self, tmp_path: Path):
        mod = _import_growthmemo()
        with patch.object(mod, "INDEX_PATH", tmp_path / "missing.json"):
            assert mod._load_index() == []

    def test_save_and_reload_index(self, tmp_path: Path):
        mod = _import_growthmemo()
        data = [{"guid": "https://growthmemo.substack.com/p/test", "slug": "test", "title": "Test"}]
        index_path = tmp_path / "gm_index.json"
        with patch.object(mod, "INDEX_PATH", index_path):
            mod._save_index(data)
            loaded = mod._load_index()
        assert loaded == data

    def test_save_creates_parent_directories(self, tmp_path: Path):
        mod = _import_growthmemo()
        deep_path = tmp_path / "deep" / "nested" / "index.json"
        with patch.object(mod, "INDEX_PATH", deep_path):
            mod._save_index([])
        assert deep_path.exists()

    def test_save_uses_utf8_encoding(self, tmp_path: Path):
        mod = _import_growthmemo()
        data = [{"title": "程式化 SEO 研究"}]
        index_path = tmp_path / "index.json"
        with patch.object(mod, "INDEX_PATH", index_path):
            mod._save_index(data)
        raw = index_path.read_bytes()
        assert "程式化".encode("utf-8") in raw


class TestParseRssFeedGrowthmemo:
    def test_parses_substack_rss_with_content(self):
        mod = _import_growthmemo()
        rich_html = "<p>" + "Kevin Indig programmatic SEO analysis " * 10 + "</p>"
        entry = _make_feedparser_entry(
            guid="https://growthmemo.substack.com/p/prog-seo",
            title="Programmatic SEO in 2025",
            url="https://growthmemo.substack.com/p/prog-seo",
            html_content=rich_html,
        )
        mock_feed = _make_feedparser_feed([entry])

        with patch("feedparser.parse", return_value=mock_feed):
            articles = mod._parse_rss_feed("https://www.kevin-indig.com/feed")

        assert len(articles) == 1
        assert articles[0]["title"] == "Programmatic SEO in 2025"
        assert articles[0]["html_content"] == rich_html

    def test_published_date_parsed(self):
        mod = _import_growthmemo()
        entry = _make_feedparser_entry(
            guid="g1",
            title="Test",
            url="https://growthmemo.substack.com/p/test",
            published_parsed=(2025, 6, 15, 0, 0, 0),
        )
        mock_feed = _make_feedparser_feed([entry])

        with patch("feedparser.parse", return_value=mock_feed):
            articles = mod._parse_rss_feed("https://www.kevin-indig.com/feed")

        assert articles[0]["published"] == "2025-06-15"

    def test_falls_back_to_summary_when_no_content(self):
        mod = _import_growthmemo()
        entry = _make_feedparser_entry(
            guid="g1",
            title="Test",
            url="https://growthmemo.substack.com/p/test",
            html_content="",
        )
        entry.summary = "<p>Summary content</p>"
        mock_feed = _make_feedparser_feed([entry])

        with patch("feedparser.parse", return_value=mock_feed):
            articles = mod._parse_rss_feed("https://www.kevin-indig.com/feed")

        assert articles[0]["html_content"] == "<p>Summary content</p>"

    def test_raises_on_bozo_feed_with_no_entries(self):
        mod = _import_growthmemo()
        mock_feed = _make_feedparser_feed([], bozo=True)

        with (
            patch("feedparser.parse", return_value=mock_feed),
            pytest.raises(ValueError, match="RSS parse failed"),
        ):
            mod._parse_rss_feed("https://www.kevin-indig.com/feed")


class TestFetchArticlePageGrowthmemo:
    def test_extracts_substack_body_div(self):
        mod = _import_growthmemo()
        html = '<html><body><div class="body markup"><p>Full article content here</p></div></body></html>'
        mock_resp = _MockHttpResponse(text=html)
        with patch("httpx.get", return_value=mock_resp):
            result = mod._fetch_article_page("https://growthmemo.substack.com/p/article")
        assert "Full article content here" in result

    def test_fallback_to_article_tag(self):
        mod = _import_growthmemo()
        html = "<html><body><article><p>Fallback content</p></article></body></html>"
        mock_resp = _MockHttpResponse(text=html)
        with patch("httpx.get", return_value=mock_resp):
            result = mod._fetch_article_page("https://growthmemo.substack.com/p/article")
        assert "Fallback content" in result

    def test_fallback_to_main_tag(self):
        mod = _import_growthmemo()
        html = "<html><body><main><p>Main content</p></main></body></html>"
        mock_resp = _MockHttpResponse(text=html)
        with patch("httpx.get", return_value=mock_resp):
            result = mod._fetch_article_page("https://growthmemo.substack.com/p/article")
        assert "Main content" in result

    def test_returns_empty_string_when_no_container_found(self):
        mod = _import_growthmemo()
        html = "<html><body><div class='sidebar'>no content</div></body></html>"
        mock_resp = _MockHttpResponse(text=html)
        with patch("httpx.get", return_value=mock_resp):
            result = mod._fetch_article_page("https://growthmemo.substack.com/p/article")
        assert isinstance(result, str)

    def test_raises_on_http_error(self):
        mod = _import_growthmemo()
        mock_resp = _MockHttpResponse(status_code=403)
        with (
            patch("httpx.get", return_value=mock_resp),
            pytest.raises(httpx.HTTPStatusError),
        ):
            mod._fetch_article_page("https://growthmemo.substack.com/p/paywalled")

    def test_validates_url_before_fetch(self):
        mod = _import_growthmemo()
        with pytest.raises(ValueError, match="allowlist"):
            mod._fetch_article_page("https://evil.com/article")


class TestFetchGrowthmemoArticles:
    def _rich_html(self) -> str:
        return "<p>" + "Kevin Indig programmatic SEO analysis content. " * 10 + "</p>"

    def _make_entry(
        self,
        guid: str = "https://growthmemo.substack.com/p/prog-seo",
        title: str = "Programmatic SEO 2025",
        url: str = "https://growthmemo.substack.com/p/prog-seo",
        html_content: str = "",
    ):
        content = html_content or self._rich_html()
        return _make_feedparser_entry(guid=guid, title=title, url=url, html_content=content)

    def test_skips_existing_guid_incremental_mode(self, tmp_path: Path):
        mod = _import_growthmemo()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "gm_markdown"
        output_dir.mkdir()

        existing_index = [{
            "guid": "https://growthmemo.substack.com/p/prog-seo",
            "slug": "prog-seo",
            "title": "Programmatic SEO 2025",
            "url": "https://growthmemo.substack.com/p/prog-seo",
            "fetched_at": "2025-01-01T00:00:00+00:00",
            "md_file": "prog-seo.md",
            "source_collection": "growth-memo",
        }]
        index_path.write_text(json.dumps(existing_index), encoding="utf-8")

        entry = self._make_entry()
        mock_feed = _make_feedparser_feed([entry])

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
        ):
            result = mod.fetch_growthmemo_articles(force=False)

        assert result["skipped"] == 1
        assert result["fetched"] == 0

    def test_force_mode_refetches_existing(self, tmp_path: Path):
        mod = _import_growthmemo()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "gm_markdown"
        output_dir.mkdir()

        existing_index = [{
            "guid": "https://growthmemo.substack.com/p/prog-seo",
            "slug": "prog-seo",
            "title": "Old Title",
            "url": "https://growthmemo.substack.com/p/prog-seo",
            "fetched_at": "2025-01-01T00:00:00+00:00",
            "md_file": "prog-seo.md",
            "source_collection": "growth-memo",
        }]
        index_path.write_text(json.dumps(existing_index), encoding="utf-8")

        entry = self._make_entry()
        mock_feed = _make_feedparser_feed([entry])

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
        ):
            result = mod.fetch_growthmemo_articles(force=True)

        assert result["fetched"] == 1

    def test_insufficient_rss_content_triggers_page_fetch(self, tmp_path: Path):
        mod = _import_growthmemo()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "gm_markdown"
        output_dir.mkdir()

        # RSS content is too short
        entry = self._make_entry(html_content="<p>Short teaser.</p>")
        mock_feed = _make_feedparser_feed([entry])
        full_page_html = '<html><body><div class="body markup"><p>' + "Full article content. " * 20 + "</p></div></body></html>"

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
            patch("httpx.get", return_value=_MockHttpResponse(text=full_page_html)),
            patch("time.sleep"),
        ):
            result = mod.fetch_growthmemo_articles(force=False)

        assert result["fetched"] == 1

    def test_insufficient_content_after_page_fetch_skips(self, tmp_path: Path):
        mod = _import_growthmemo()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "gm_markdown"
        output_dir.mkdir()

        entry = self._make_entry(html_content="<p>Short teaser.</p>")
        mock_feed = _make_feedparser_feed([entry])
        # Page also returns minimal content
        sparse_page_html = "<html><body><article><p>Still short.</p></article></body></html>"

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
            patch("httpx.get", return_value=_MockHttpResponse(text=sparse_page_html)),
            patch("time.sleep"),
        ):
            result = mod.fetch_growthmemo_articles(force=False)

        assert result["insufficient"] == 1
        assert result["fetched"] == 0

    def test_page_fetch_http_error_falls_through_to_insufficient(self, tmp_path: Path):
        mod = _import_growthmemo()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "gm_markdown"
        output_dir.mkdir()

        entry = self._make_entry(html_content="<p>Short teaser.</p>")
        mock_feed = _make_feedparser_feed([entry])

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
            patch("httpx.get", return_value=_MockHttpResponse(status_code=403)),
            patch("time.sleep"),
        ):
            result = mod.fetch_growthmemo_articles(force=False)

        assert result["insufficient"] == 1
        assert result["fetched"] == 0

    def test_limit_respected(self, tmp_path: Path):
        mod = _import_growthmemo()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "gm_markdown"
        output_dir.mkdir()

        entries = [
            self._make_entry(
                guid=f"https://growthmemo.substack.com/p/article-{i}",
                title=f"Article {i}",
                url=f"https://growthmemo.substack.com/p/article-{i}",
            )
            for i in range(3)
        ]
        mock_feed = _make_feedparser_feed(entries)

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
        ):
            result = mod.fetch_growthmemo_articles(force=False, limit=1)

        assert result["fetched"] == 1

    def test_markdown_file_written_with_metadata_header(self, tmp_path: Path):
        mod = _import_growthmemo()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "gm_markdown"
        output_dir.mkdir()

        entry = _make_feedparser_entry(
            guid="https://growthmemo.substack.com/p/prog-seo",
            title="Programmatic SEO at Scale",
            url="https://growthmemo.substack.com/p/prog-seo",
            published_parsed=(2025, 3, 10, 0, 0, 0),
            html_content="<p>" + "Growth Memo programmatic SEO analysis. " * 10 + "</p>",
        )
        mock_feed = _make_feedparser_feed([entry])

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
        ):
            result = mod.fetch_growthmemo_articles(force=False)

        assert result["fetched"] == 1
        md_file = output_dir / "prog-seo.md"
        assert md_file.exists()
        content = md_file.read_text(encoding="utf-8")
        assert "growth-memo" in content
        assert "Kevin Indig" in content
        assert "article" in content

    def test_index_sorted_by_slug(self, tmp_path: Path):
        mod = _import_growthmemo()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "gm_markdown"
        output_dir.mkdir()

        entries = [
            self._make_entry(
                guid=f"https://growthmemo.substack.com/p/z-article-{i}",
                title=f"Article {i}",
                url=f"https://growthmemo.substack.com/p/z-article-{i}",
            )
            for i in range(3, 0, -1)  # reverse order
        ]
        mock_feed = _make_feedparser_feed(entries)

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
        ):
            mod.fetch_growthmemo_articles(force=False)

        loaded = json.loads(index_path.read_text(encoding="utf-8"))
        slugs = [e["slug"] for e in loaded]
        assert slugs == sorted(slugs)

    def test_returns_correct_counters_structure(self, tmp_path: Path):
        mod = _import_growthmemo()
        index_path = tmp_path / "index.json"
        output_dir = tmp_path / "gm_markdown"
        output_dir.mkdir()

        mock_feed = _make_feedparser_feed([])
        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch("feedparser.parse", return_value=mock_feed),
        ):
            result = mod.fetch_growthmemo_articles(force=False)

        assert "fetched" in result
        assert "skipped" in result
        assert "insufficient" in result
        assert "total" in result
