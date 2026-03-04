"""Tests for utils/html_to_markdown.py"""
from __future__ import annotations

import pytest

from utils.html_to_markdown import html_to_markdown, add_metadata_header, _cleanup


class TestHtmlToMarkdown:
    def test_basic_html_conversion(self):
        html = "<h1>Title</h1><p>Hello world</p>"
        md = html_to_markdown(html)
        assert "# Title" in md
        assert "Hello world" in md

    def test_strips_script_tags(self):
        html = "<p>Content</p><script>alert('xss')</script>"
        md = html_to_markdown(html)
        assert "alert" not in md
        assert "Content" in md

    def test_strips_style_tags(self):
        html = "<style>.foo { color: red; }</style><p>Text</p>"
        md = html_to_markdown(html)
        assert "color" not in md
        assert "Text" in md

    def test_preserves_links(self):
        html = '<p>Visit <a href="https://example.com">here</a></p>'
        md = html_to_markdown(html)
        assert "https://example.com" in md
        assert "here" in md

    def test_handles_empty_html(self):
        md = html_to_markdown("")
        assert md.strip() == ""

    def test_handles_nested_tags(self):
        html = "<div><h2>Sub</h2><ul><li>Item 1</li><li>Item 2</li></ul></div>"
        md = html_to_markdown(html)
        assert "## Sub" in md
        assert "Item 1" in md
        assert "Item 2" in md


class TestCleanup:
    def test_collapses_blank_lines(self):
        text = "Line 1\n\n\n\n\nLine 2"
        result = _cleanup(text)
        assert result == "Line 1\n\nLine 2\n"

    def test_strips_trailing_whitespace(self):
        text = "Hello   \nWorld  "
        result = _cleanup(text)
        assert result == "Hello\nWorld\n"

    def test_single_trailing_newline(self):
        text = "Content"
        result = _cleanup(text)
        assert result.endswith("\n")
        assert not result.endswith("\n\n")


class TestAddMetadataHeader:
    def test_basic_header(self):
        result = add_metadata_header(
            "Body content\n",
            title="Test Article",
            published="2025-12-01",
            author="Author",
            source_url="https://example.com/article",
        )
        assert result.startswith("# Test Article\n")
        assert "**發佈日期**: 2025-12-01" in result
        assert "**作者**: Author" in result
        assert "**來源 URL**: https://example.com/article" in result
        assert "**來源類型**: article" in result
        assert "Body content" in result

    def test_with_collection(self):
        result = add_metadata_header(
            "Body\n",
            title="T",
            published="2025-01-01",
            author="A",
            source_url="https://example.com",
            source_collection="my-collection",
        )
        assert "**來源集合**: my-collection" in result

    def test_separator_present(self):
        result = add_metadata_header(
            "Body\n",
            title="T",
            published="2025-01-01",
            author="A",
            source_url="https://example.com",
        )
        assert "---" in result
