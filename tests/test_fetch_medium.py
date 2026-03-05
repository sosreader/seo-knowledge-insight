"""Tests for scripts/01b_fetch_medium.py"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.fetch_medium_helpers import _safe_filename


def _import_fetch_medium():
    """Import the module with a non-standard name."""
    return importlib.import_module("scripts.01b_fetch_medium")


class TestSafeFilename:
    def test_basic(self):
        assert _safe_filename("Hello World") == "Hello_World"

    def test_special_chars(self):
        result = _safe_filename("AI & SEO: What's Next?")
        assert "/" not in result
        assert "?" not in result
        assert ":" not in result

    def test_cjk_preserved(self):
        result = _safe_filename("AI 時代的 SEO 策略")
        assert "AI" in result
        assert "SEO" in result

    def test_truncation(self):
        long_title = "A" * 200
        result = _safe_filename(long_title)
        assert len(result) <= 80

    def test_empty_returns_untitled(self):
        assert _safe_filename("???") == "untitled"


class TestStripMediumUiElements:
    """Tests for _strip_medium_ui_elements() UI cleaning logic."""

    def _strip(self, html: str) -> str:
        """Helper: parse → strip → return str."""
        from bs4 import BeautifulSoup
        mod = _import_fetch_medium()
        soup = BeautifulSoup(html, "html.parser")
        mod._strip_medium_ui_elements(soup, base_url="https://genehong.medium.com/test")
        return str(soup)

    # --- Press enter accessibility text ---
    def test_removes_press_enter_text(self):
        html = '<div><span>Press enter or click to view image in full size</span></div>'
        result = self._strip(html)
        assert "Press enter" not in result

    def test_press_enter_preserves_surrounding_content(self):
        html = (
            '<article>'
            '<p>Real SEO content</p>'
            '<span>Press enter or click to view image in full size</span>'
            '<p>More content</p>'
            '</article>'
        )
        result = self._strip(html)
        assert "Press enter" not in result
        assert "Real SEO content" in result
        assert "More content" in result

    # --- Subscription CTA ---
    def test_removes_join_medium_cta_div(self):
        html = '<div><p>Join Medium for free to get updates from this writer.</p></div>'
        result = self._strip(html)
        assert "Join Medium" not in result

    def test_removes_stories_in_your_inbox_heading(self):
        """h2 heading CTA (simple text) must be removed."""
        html = (
            '<article>'
            '<p>Article content here</p>'
            "<h2>Get Gene Hong's stories in your inbox</h2>"
            '<p>More article content</p>'
            '</article>'
        )
        result = self._strip(html)
        assert "stories in your inbox" not in result
        assert "Article content here" in result
        assert "More article content" in result

    def test_removes_stories_in_your_inbox_heading_with_mixed_markup(self):
        """h2 with nested <a> tag (real Medium structure) must be removed.

        Regression: find_all(string=...) only matches leaf NavigableString nodes,
        so mixed-markup headings like <h2>Get <a>Author</a>'s stories</h2>
        were not caught by the previous string-matching approach.
        """
        html = (
            '<article>'
            '<p>Article content here</p>'
            '<h2>Get <a href="/@genehong?source=post_page">Gene Hong, 還是黑貘</a>\'s stories in your inbox</h2>'
            '<p>Content after heading must survive</p>'
            '</article>'
        )
        result = self._strip(html)
        assert "stories in your inbox" not in result
        assert "Article content here" in result
        assert "Content after heading must survive" in result

    def test_removes_stories_heading_with_nbsp(self):
        """h2 containing \\xa0 (non-breaking space) from Medium HTML must be removed.

        Regression: Medium renders 'stories in\\xa0your\\xa0inbox' with \\xa0 instead
        of regular spaces. Without whitespace normalization, the regex doesn't match.
        """
        html = (
            '<article>'
            '<p>Article content here</p>'
            '<h2>Get Gene Hong\u2019s stories in\xa0your\xa0inbox</h2>'
            '<p>Content after heading must survive</p>'
            '</article>'
        )
        result = self._strip(html)
        assert "stories" not in result or "your\xa0inbox" not in result
        assert "Article content here" in result
        assert "Content after heading must survive" in result

    def test_byline_in_heading_does_not_remove_following_content(self):
        """Byline <a> inside <h2> must only remove the heading, not its parent div.

        Regression: while loop didn't stop at h2, walked up to parent div,
        and decomposed it — removing all subsequent article content.
        """
        html = (
            '<div>'
            '<h2><a href="/?source=post_page---byline--abc">Author</a></h2>'
            '<p>This article paragraph must survive</p>'
            '</div>'
        )
        result = self._strip(html)
        assert "This article paragraph must survive" in result

    def test_removes_follow_to_never_miss_cta(self):
        html = '<div>Follow to never miss any stories from this author.</div>'
        result = self._strip(html)
        assert "Follow to never miss" not in result

    # --- Byline author blocks ---
    def test_removes_byline_link(self):
        html = (
            '<div>'
            '<a href="/?source=post_page---byline--c5e33a2f565c">Gene Hong</a>'
            '</div>'
        )
        result = self._strip(html)
        assert "byline" not in result

    def test_preserves_延伸閱讀_article_links(self):
        """Author-curated related article links must NOT be removed (regression guard)."""
        html = (
            '<article>'
            '<p>延伸閱讀：</p>'
            '<a href="https://genehong.medium.com/some-article-abc123?source=post_page-----c5e33a2f565c">網路選戰輿情系統</a>'
            '</article>'
        )
        result = self._strip(html)
        assert "網路選戰輿情系統" in result

    # --- Relative URL fix ---
    def test_fixes_relative_href(self):
        html = '<a href="/some-path">Link</a>'
        result = self._strip(html)
        assert 'href="https://medium.com/some-path"' in result

    def test_fixes_query_relative_href(self):
        html = '<a href="/?source=something">Link</a>'
        result = self._strip(html)
        assert "https://medium.com" in result


class TestIsPaywalled:
    def _check(self, html: str) -> bool:
        mod = _import_fetch_medium()
        return mod._is_paywalled(html)

    def test_short_content_is_paywalled(self):
        assert self._check("<p>Short.</p>") is True

    def test_long_content_is_not_paywalled(self):
        content = "<p>" + "這是文章內容。" * 100 + "</p>"
        assert self._check(content) is False

    def test_empty_is_paywalled(self):
        assert self._check("") is True

    def test_exactly_500_chars_not_paywalled(self):
        content = "<p>" + "A" * 500 + "</p>"
        assert self._check(content) is False

    def test_499_chars_is_paywalled(self):
        content = "<p>" + "A" * 499 + "</p>"
        assert self._check(content) is True


class TestMediumIndexOperations:
    def test_load_nonexistent_index(self, tmp_path: Path):
        mod = _import_fetch_medium()
        index_path = tmp_path / "nonexistent.json"
        with patch.object(mod, "INDEX_PATH", index_path):
            assert mod._load_index() == []

    def test_save_and_load_index(self, tmp_path: Path):
        mod = _import_fetch_medium()
        index_path = tmp_path / "index.json"
        test_data = [{"guid": "test-1", "title": "Test Article"}]

        with patch.object(mod, "INDEX_PATH", index_path):
            mod._save_index(test_data)
            loaded = mod._load_index()
            assert loaded == test_data
