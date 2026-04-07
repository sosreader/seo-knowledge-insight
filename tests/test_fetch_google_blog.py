"""Tests for scripts/01h_fetch_google_blog.py."""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest


pytestmark = pytest.mark.unit


def _import_fetch_google_blog():
    """Import the module with a non-standard name."""
    return importlib.import_module("scripts.01h_fetch_google_blog")


class _MockResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None


def _make_article_html(
    *,
    title: str = "Spam Update",
    body_text: str = "Google Search Central update " * 20,
    author: str = "Google Search Central",
    published: str = "2024-03-07T00:00:00Z",
    include_time: bool = True,
    include_meta_date: bool = False,
) -> str:
    time_html = f'<time datetime="{published}"></time>' if include_time else ""
    meta_html = '<meta name="date" content="2024-03-07" />' if include_meta_date else ""
    return (
        "<html><head>"
        f"{meta_html}"
        "</head><body>"
        f"<h1>{title}</h1>"
        f"{time_html}"
        f'<span class="devsite-byline-author-name">{author}</span>'
        f'<div class="devsite-article-body"><p>{body_text}</p></div>'
        "</body></html>"
    )


def _build_metadata_header(
    md_content: str,
    *,
    title: str,
    published: str,
    author: str,
    source_url: str,
    source_type: str,
    source_collection: str,
) -> str:
    return (
        f"# {title}\n"
        f"**發佈日期**: {published}\n"
        f"**作者**: {author}\n"
        f"**來源 URL**: {source_url}\n"
        f"**來源類型**: {source_type}\n"
        f"**來源集合**: {source_collection}\n\n"
        f"{md_content}\n"
    )


class TestBlogPostPattern:
    def test_matches_english_blog_urls(self):
        mod = _import_fetch_google_blog()
        html = '<a href="/search/blog/2024/03/spam-update">Update</a>'

        matches = mod._BLOG_POST_PATTERN.findall(html)

        assert len(matches) == 1
        assert matches[0][0] == "/search/blog/2024/03/spam-update"
        assert matches[0][1] == "2024"
        assert matches[0][2] == "03"
        assert matches[0][3] == "spam-update"

    def test_matches_zhtw_blog_urls_without_capturing_query(self):
        mod = _import_fetch_google_blog()
        html = '<a href="/search/blog/2024/03/spam-update?hl=zh-tw">更新</a>'

        matches = mod._BLOG_POST_PATTERN.findall(html)

        assert len(matches) == 1
        assert matches[0][0] == "/search/blog/2024/03/spam-update"
        assert matches[0][3] == "spam-update"

    def test_ignores_other_query_params_when_matching_slug(self):
        mod = _import_fetch_google_blog()
        html = '<a href="/search/blog/2024/03/spam-update?authuser=1">Update</a>'

        matches = mod._BLOG_POST_PATTERN.findall(html)

        assert len(matches) == 1
        assert matches[0][0] == "/search/blog/2024/03/spam-update"
        assert matches[0][3] == "spam-update"

    def test_no_match_for_non_blog_urls(self):
        mod = _import_fetch_google_blog()
        html = '<a href="/search/docs/2024/03/spam-update">Docs</a>'

        assert mod._BLOG_POST_PATTERN.findall(html) == []


class TestValidateUrl:
    def test_allows_google_blog_zhtw_url(self):
        mod = _import_fetch_google_blog()

        mod._validate_url("https://developers.google.com/search/blog?hl=zh-tw")

    def test_rejects_non_google_domains(self):
        mod = _import_fetch_google_blog()

        with pytest.raises(ValueError, match="allowlist"):
            mod._validate_url("https://evil.example.com/search/blog")

    def test_rejects_non_http_schemes(self):
        mod = _import_fetch_google_blog()

        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            mod._validate_url("file:///tmp/secrets.txt")


class TestSanitizeSlug:
    def test_preserves_zhtw_prefix(self):
        mod = _import_fetch_google_blog()

        assert mod._sanitize_slug("zhtw-2024-03-spam-update") == "zhtw-2024-03-spam-update"

    def test_removes_special_characters(self):
        mod = _import_fetch_google_blog()

        sanitized = mod._sanitize_slug("zhtw-2024/03:spam update?!")

        assert "/" not in sanitized
        assert ":" not in sanitized
        assert "?" not in sanitized
        assert " " not in sanitized

    def test_truncates_long_slugs(self):
        mod = _import_fetch_google_blog()

        sanitized = mod._sanitize_slug("zhtw-" + ("a" * 400))

        assert len(sanitized) == 200


class TestHasSufficientContent:
    def test_accepts_200_visible_characters(self):
        mod = _import_fetch_google_blog()
        html = f"<div><p>{'繁體中文內容' * 40}</p></div>"

        assert mod._has_sufficient_content(html) is True

    def test_rejects_199_visible_characters(self):
        mod = _import_fetch_google_blog()
        html = f"<div><p>{'A' * 199}</p></div>"

        assert mod._has_sufficient_content(html) is False

    def test_strips_tags_before_counting(self):
        mod = _import_fetch_google_blog()
        html = "<div>" + "<span>A</span>" * 200 + "</div>"

        assert mod._has_sufficient_content(html) is True


class TestLoadSaveIndex:
    def test_load_nonexistent_default_index(self, tmp_path: Path):
        mod = _import_fetch_google_blog()
        index_path = tmp_path / "google_blog_articles_index.json"

        assert mod._load_index(index_path=index_path) == []

    def test_save_and_load_english_index(self, tmp_path: Path):
        mod = _import_fetch_google_blog()
        index_path = tmp_path / "google_blog_articles_index.json"
        data = [{"slug": "2024-03-spam-update", "title": "Spam Update"}]

        mod._save_index(data, index_path=index_path)

        assert mod._load_index(index_path=index_path) == data

    def test_save_and_load_zhtw_index(self, tmp_path: Path):
        mod = _import_fetch_google_blog()
        index_path = tmp_path / "google_blog_zhtw_articles_index.json"
        data = [{"slug": "zhtw-2024-03-spam-update", "title": "垃圾內容更新"}]

        mod._save_index(data, index_path=index_path)

        loaded = json.loads(index_path.read_text(encoding="utf-8"))
        assert loaded == data
        assert mod._load_index(index_path=index_path) == data


class TestDiscoverBlogPosts:
    def test_filters_since_year_deduplicates_and_sorts_newest_first(self):
        mod = _import_fetch_google_blog()
        html = """
        <a href="/search/blog/2023/02/older-update">Older</a>
        <a href="/search/blog/2024/03/spam-update">Spam</a>
        <a href="/search/blog/2024/03/spam-update">Spam Duplicate</a>
        <a href="/search/blog/2024/01/core-update">Core</a>
        """

        with patch("httpx.get", return_value=_MockResponse(html)) as mock_get:
            posts = mod._discover_blog_posts(since_year=2024)

        mock_get.assert_called_once_with(
            mod.BLOG_INDEX_URL,
            follow_redirects=True,
            timeout=30,
            headers=mod._HTTP_HEADERS,
        )
        assert [post["slug"] for post in posts] == [
            "2024-03-spam-update",
            "2024-01-core-update",
        ]

    def test_zhtw_uses_hl_param_and_prefixes_slug(self):
        mod = _import_fetch_google_blog()
        html = '<a href="/search/blog/2024/03/spam-update?hl=zh-tw">更新</a>'

        with patch("httpx.get", return_value=_MockResponse(html)) as mock_get:
            posts = mod._discover_blog_posts(since_year=2024, lang="zh-tw")

        mock_get.assert_called_once_with(
            f"{mod.BLOG_INDEX_URL}?hl=zh-tw",
            follow_redirects=True,
            timeout=30,
            headers=mod._HTTP_HEADERS,
        )
        assert posts[0]["slug"] == "zhtw-2024-03-spam-update"
        assert posts[0]["url"].endswith("/search/blog/2024/03/spam-update?hl=zh-tw")


class TestFetchGoogleBlogEn:
    def test_extracts_article_content_title_author_and_published(self):
        mod = _import_fetch_google_blog()
        html = _make_article_html(author="Google Team")

        with patch("httpx.get", return_value=_MockResponse(html)):
            page = mod._fetch_article_content("https://developers.google.com/search/blog/2024/03/spam-update")

        assert page["title"] == "Spam Update"
        assert page["author"] == "Google Team"
        assert page["published"] == "2024-03-07"
        assert "devsite-article-body" in page["html_content"]

    def test_uses_meta_date_when_time_tag_missing(self):
        mod = _import_fetch_google_blog()
        html = _make_article_html(include_time=False, include_meta_date=True)

        with patch("httpx.get", return_value=_MockResponse(html)):
            page = mod._fetch_article_content("https://developers.google.com/search/blog/2024/03/spam-update")

        assert page["published"] == "2024-03-07"

    def test_skips_existing_articles_incrementally(self, tmp_path: Path):
        mod = _import_fetch_google_blog()
        output_dir = tmp_path / "google_blog_markdown"
        index_path = tmp_path / "google_blog_articles_index.json"
        mod._save_index(
            [{"slug": "2024-03-spam-update", "title": "Spam Update"}],
            index_path=index_path,
        )

        with (
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "_discover_blog_posts", return_value=[
                {
                    "slug": "2024-03-spam-update",
                    "url": "https://developers.google.com/search/blog/2024/03/spam-update",
                    "published_approx": "2024-03-01",
                    "year": 2024,
                    "month": 3,
                }
            ]),
            patch.object(mod, "time") as mock_time,
        ):
            result = mod.fetch_google_blog_articles()

        mock_time.sleep.assert_not_called()
        assert result == {"fetched": 0, "skipped": 1, "insufficient": 0, "total": 1}

    def test_force_refetch_replaces_existing_index_entry(self, tmp_path: Path):
        mod = _import_fetch_google_blog()
        output_dir = tmp_path / "google_blog_markdown"
        index_path = tmp_path / "google_blog_articles_index.json"
        mod._save_index(
            [{"slug": "2024-03-spam-update", "title": "Old Title"}],
            index_path=index_path,
        )

        with (
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "_discover_blog_posts", return_value=[
                {
                    "slug": "2024-03-spam-update",
                    "url": "https://developers.google.com/search/blog/2024/03/spam-update",
                    "published_approx": "2024-03-01",
                    "year": 2024,
                    "month": 3,
                }
            ]),
            patch.object(mod, "_fetch_article_content", return_value={
                "title": "Updated Title",
                "html_content": "<div>" + ("A" * 250) + "</div>",
                "author": mod.AUTHOR,
                "published": "2024-03-07",
            }),
            patch.object(mod, "html_to_markdown", return_value="converted markdown"),
            patch.object(mod, "add_metadata_header", side_effect=_build_metadata_header),
            patch.object(mod.time, "sleep"),
        ):
            result = mod.fetch_google_blog_articles(force=True)

        saved_index = mod._load_index(index_path=index_path)
        assert result["fetched"] == 1
        assert result["total"] == 1
        assert saved_index[0]["title"] == "Updated Title"
        assert saved_index[0]["source_collection"] == mod.SOURCE_COLLECTION
        assert (output_dir / "2024-03-spam-update.md").exists()

    def test_default_constants_remain_english_aliases(self):
        mod = _import_fetch_google_blog()

        assert mod.SOURCE_COLLECTION == mod.SOURCE_COLLECTION_EN
        assert mod.INDEX_PATH.name == "google_blog_articles_index.json"
        assert mod.OUTPUT_DIR.name == "google_blog_markdown"


class TestFetchGoogleBlogZhTw:
    def test_writes_zhtw_articles_to_dedicated_output_and_index(self, tmp_path: Path):
        mod = _import_fetch_google_blog()
        output_dir = tmp_path / "google_blog_zhtw_markdown"
        index_path = tmp_path / "google_blog_zhtw_articles_index.json"

        with (
            patch.object(mod, "OUTPUT_DIR_ZH", output_dir),
            patch.object(mod, "INDEX_PATH_ZH", index_path),
            patch.object(mod, "_discover_blog_posts", return_value=[
                {
                    "slug": "zhtw-2024-03-spam-update",
                    "url": "https://developers.google.com/search/blog/2024/03/spam-update?hl=zh-tw",
                    "published_approx": "2024-03-01",
                    "year": 2024,
                    "month": 3,
                }
            ]),
            patch.object(mod, "_fetch_article_content", return_value={
                "title": "垃圾內容更新",
                "html_content": "<div>" + ("繁體中文內容" * 40) + "</div>",
                "author": mod.AUTHOR,
                "published": "2024-03-07",
            }),
            patch.object(mod, "html_to_markdown", return_value="繁體中文內容"),
            patch.object(mod, "add_metadata_header", side_effect=_build_metadata_header),
            patch.object(mod.time, "sleep"),
        ):
            result = mod.fetch_google_blog_articles(lang="zh-tw")

        md_path = output_dir / "zhtw-2024-03-spam-update.md"
        md_content = md_path.read_text(encoding="utf-8")
        saved_index = mod._load_index(index_path=index_path)

        assert result["fetched"] == 1
        assert result["total"] == 1
        assert md_path.exists()
        assert "**來源集合**: google-search-central-zh" in md_content
        assert saved_index[0]["source_collection"] == "google-search-central-zh"
        assert saved_index[0]["md_file"] == "zhtw-2024-03-spam-update.md"

    def test_main_passes_lang_argument_to_fetcher(self):
        mod = _import_fetch_google_blog()

        with (
            patch("sys.argv", ["01h_fetch_google_blog.py", "--lang", "zh-tw", "--limit", "5", "--since", "2024"]),
            patch.object(mod, "fetch_google_blog_articles", return_value={
                "fetched": 5,
                "skipped": 0,
                "insufficient": 0,
                "total": 5,
            }) as mock_fetch,
        ):
            mod.main()

        mock_fetch.assert_called_once_with(
            force=False,
            limit=5,
            since_year=2024,
            lang="zh-tw",
        )


class TestPathTraversal:
    def test_skips_when_sanitized_slug_is_empty(self, tmp_path: Path):
        mod = _import_fetch_google_blog()
        output_dir = tmp_path / "google_blog_markdown"
        index_path = tmp_path / "google_blog_articles_index.json"

        with (
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "_discover_blog_posts", return_value=[
                {
                    "slug": "2024-03-spam-update",
                    "url": "https://developers.google.com/search/blog/2024/03/spam-update",
                    "published_approx": "2024-03-01",
                    "year": 2024,
                    "month": 3,
                }
            ]),
            patch.object(mod, "_fetch_article_content", return_value={
                "title": "Spam Update",
                "html_content": "<div>" + ("A" * 250) + "</div>",
                "author": mod.AUTHOR,
                "published": "2024-03-07",
            }),
            patch.object(mod, "_sanitize_slug", return_value=""),
            patch.object(mod, "html_to_markdown", return_value="converted markdown"),
            patch.object(mod, "add_metadata_header", side_effect=_build_metadata_header),
            patch.object(mod.time, "sleep"),
        ):
            result = mod.fetch_google_blog_articles()

        assert result["fetched"] == 0
        assert result["total"] == 0
        assert list(output_dir.glob("*.md")) == []

    def test_skips_when_resolved_path_escapes_output_dir(self, tmp_path: Path):
        mod = _import_fetch_google_blog()
        output_dir = tmp_path / "google_blog_markdown"
        index_path = tmp_path / "google_blog_articles_index.json"

        with (
            patch.object(mod, "OUTPUT_DIR", output_dir),
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(mod, "_discover_blog_posts", return_value=[
                {
                    "slug": "2024-03-spam-update",
                    "url": "https://developers.google.com/search/blog/2024/03/spam-update",
                    "published_approx": "2024-03-01",
                    "year": 2024,
                    "month": 3,
                }
            ]),
            patch.object(mod, "_fetch_article_content", return_value={
                "title": "Spam Update",
                "html_content": "<div>" + ("A" * 250) + "</div>",
                "author": mod.AUTHOR,
                "published": "2024-03-07",
            }),
            patch.object(mod, "_sanitize_slug", return_value="../escape"),
            patch.object(mod, "html_to_markdown", return_value="converted markdown"),
            patch.object(mod, "add_metadata_header", side_effect=_build_metadata_header),
            patch.object(mod.time, "sleep"),
        ):
            result = mod.fetch_google_blog_articles()

        assert result["fetched"] == 0
        assert result["total"] == 0
        assert list(output_dir.glob("*.md")) == []