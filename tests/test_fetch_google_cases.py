"""Tests for scripts/01d_fetch_google_cases.py"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest


def _import_fetch_google_cases():
    """Import the module with a non-standard name."""
    return importlib.import_module("scripts.01d_fetch_google_cases")


class TestCaseStudyLinkPattern:
    def test_matches_case_study_url(self):
        mod = _import_fetch_google_cases()
        html = '<a href="/search/case-studies/saramin-case-study?hl=zh-tw">Saramin</a>'
        matches = mod.CASE_STUDY_LINK_PATTERN.findall(html)
        assert len(matches) == 1
        assert matches[0][1] == "saramin-case-study"

    def test_extracts_multiple_urls(self):
        mod = _import_fetch_google_cases()
        html = """
        <a href="/search/case-studies/saramin-case-study?hl=zh-tw">Saramin</a>
        <a href="/search/case-studies/vidio-case-study?hl=zh-tw">Vidio</a>
        """
        matches = mod.CASE_STUDY_LINK_PATTERN.findall(html)
        assert len(matches) == 2

    def test_no_match_for_other_urls(self):
        mod = _import_fetch_google_cases()
        html = '<a href="/search/docs/some-page">Other</a>'
        matches = mod.CASE_STUDY_LINK_PATTERN.findall(html)
        assert len(matches) == 0

    def test_deduplicates_slugs(self):
        mod = _import_fetch_google_cases()
        html = """
        <a href="/search/case-studies/saramin-case-study">Link1</a>
        <a href="/search/case-studies/saramin-case-study?hl=zh-tw">Link2</a>
        """
        matches = mod.CASE_STUDY_LINK_PATTERN.findall(html)
        # Pattern finds both, but _fetch_case_study_urls deduplicates
        assert len(matches) == 2


class TestGoogleCasesIndex:
    def test_load_nonexistent_index(self, tmp_path: Path):
        mod = _import_fetch_google_cases()
        index_path = tmp_path / "nonexistent.json"
        with patch.object(mod, "INDEX_PATH", index_path):
            assert mod._load_index() == []

    def test_save_and_load_index(self, tmp_path: Path):
        mod = _import_fetch_google_cases()
        index_path = tmp_path / "index.json"
        test_data = [{"slug": "saramin-case-study", "title": "Saramin"}]

        with patch.object(mod, "INDEX_PATH", index_path):
            mod._save_index(test_data)
            loaded = mod._load_index()
            assert loaded == test_data


class TestExtractArticleBody:
    def test_extracts_devsite_article_body(self):
        mod = _import_fetch_google_cases()
        html = """
        <div class="devsite-article-body clearfix">
        <h2>Challenge</h2>
        <p>Some content here.</p>
        <devsite-feedback>feedback</devsite-feedback>
        </div>
        """
        result = mod._extract_article_body(html)
        assert "Challenge" in result
        assert "Some content here" in result
        assert "devsite-feedback" not in result

    def test_returns_empty_for_missing_body(self):
        mod = _import_fetch_google_cases()
        html = "<div>No article body here</div>"
        result = mod._extract_article_body(html)
        assert result == ""


class TestFetchGoogleCases:
    def test_skips_existing_slugs(self, tmp_path: Path):
        mod = _import_fetch_google_cases()
        import config as cfg

        output_dir = tmp_path / "google_cases_markdown"
        output_dir.mkdir()
        index_path = tmp_path / "google_cases_index.json"

        # Pre-populate index with one existing case study
        existing_index = [{
            "slug": "saramin-case-study",
            "title": "Saramin",
            "url": "https://developers.google.com/search/case-studies/saramin-case-study",
            "fetched_at": "2026-03-05T00:00:00+00:00",
            "md_file": "saramin-case-study.md",
            "source_collection": "google-case-studies",
        }]
        index_path.write_text(json.dumps(existing_index), encoding="utf-8")

        mock_listing_html = """
        <a href="/search/case-studies/saramin-case-study?hl=zh-tw">Saramin</a>
        """

        class MockResponse:
            text = mock_listing_html
            def raise_for_status(self):
                pass

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(cfg, "RAW_GOOGLE_CASES_MD_DIR", output_dir),
            patch("httpx.get", return_value=MockResponse()),
        ):
            result = mod.fetch_google_cases(force=False)

        assert result["skipped"] == 1
        assert result["fetched"] == 0

    def test_metadata_header_added(self, tmp_path: Path):
        mod = _import_fetch_google_cases()
        import config as cfg

        output_dir = tmp_path / "google_cases_markdown"
        output_dir.mkdir()
        index_path = tmp_path / "google_cases_index.json"

        listing_html = '<a href="/search/case-studies/test-case-study?hl=zh-tw">Test</a>'
        article_html = """
        <html>
        <h1>Test Case Study Title</h1>
        <div class="devsite-article-body">
        <h2>Challenge</h2>
        <p>Content here.</p>
        <devsite-feedback>x</devsite-feedback>
        </div>
        </html>
        """

        call_count = 0

        class MockListResponse:
            text = listing_html
            def raise_for_status(self):
                pass

        class MockArticleResponse:
            text = article_html
            def raise_for_status(self):
                pass

        def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MockListResponse()
            return MockArticleResponse()

        with (
            patch.object(mod, "INDEX_PATH", index_path),
            patch.object(cfg, "RAW_GOOGLE_CASES_MD_DIR", output_dir),
            patch("httpx.get", side_effect=mock_get),
            patch("time.sleep"),
        ):
            result = mod.fetch_google_cases(force=False)

        assert result["fetched"] == 1
        md_file = output_dir / "test-case-study.md"
        assert md_file.exists()
        content = md_file.read_text(encoding="utf-8")
        assert "Google Search Central" in content
        assert "google-case-studies" in content
        assert "article" in content
