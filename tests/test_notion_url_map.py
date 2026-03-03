"""tests/test_notion_url_map.py — notion_url_map 模組測試"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from utils.notion_url_map import (
    _build_from_index,
    _build_from_markdown,
    _validate_notion_url,
    build_source_to_notion_url,
)


# ── _validate_notion_url ─────────────────────────────────

class TestValidateNotionUrl:
    def test_valid_url(self):
        assert _validate_notion_url("https://www.notion.so/SEO-abc123") is True

    def test_prefix_only_is_invalid(self):
        assert _validate_notion_url("https://www.notion.so/") is False

    def test_wrong_domain(self):
        assert _validate_notion_url("https://example.com/page") is False

    def test_empty_string(self):
        assert _validate_notion_url("") is False


# ── _build_from_index ────────────────────────────────────

class TestBuildFromIndex:
    def test_basic_mapping(self, tmp_path: Path):
        index = [
            {
                "title": "SEO 0628",
                "url": "https://www.notion.so/SEO-0628-abc123",
                "md_file": "markdown/SEO_0628.md",
            },
            {
                "title": "SEO 0705",
                "url": "https://www.notion.so/SEO-0705-def456",
                "md_file": "markdown/SEO_0705.md",
            },
        ]
        idx_file = tmp_path / "meetings_index.json"
        idx_file.write_text(json.dumps(index), encoding="utf-8")

        result = _build_from_index(idx_file)

        assert result == {
            "SEO_0628.md": "https://www.notion.so/SEO-0628-abc123",
            "SEO_0705.md": "https://www.notion.so/SEO-0705-def456",
        }

    def test_skips_empty_url(self, tmp_path: Path):
        index = [
            {"title": "T", "url": "", "md_file": "markdown/T.md"},
        ]
        idx_file = tmp_path / "meetings_index.json"
        idx_file.write_text(json.dumps(index), encoding="utf-8")

        result = _build_from_index(idx_file)
        assert result == {}

    def test_skips_invalid_url(self, tmp_path: Path):
        index = [
            {"title": "T", "url": "https://example.com/bad", "md_file": "markdown/T.md"},
        ]
        idx_file = tmp_path / "meetings_index.json"
        idx_file.write_text(json.dumps(index), encoding="utf-8")

        result = _build_from_index(idx_file)
        assert result == {}

    def test_skips_missing_md_file(self, tmp_path: Path):
        index = [
            {"title": "T", "url": "https://www.notion.so/T-123"},
        ]
        idx_file = tmp_path / "meetings_index.json"
        idx_file.write_text(json.dumps(index), encoding="utf-8")

        result = _build_from_index(idx_file)
        assert result == {}


# ── _build_from_markdown ─────────────────────────────────

class TestBuildFromMarkdown:
    def test_extracts_url_from_metadata(self, tmp_path: Path):
        md_dir = tmp_path / "markdown"
        md_dir.mkdir()
        (md_dir / "SEO_0628.md").write_text(
            textwrap.dedent("""\
            # SEO 0628
            - **Notion URL**: https://www.notion.so/SEO-0628-abc123
            ---
            Some content
            """),
            encoding="utf-8",
        )

        result = _build_from_markdown(md_dir)
        assert result == {"SEO_0628.md": "https://www.notion.so/SEO-0628-abc123"}

    def test_nonexistent_dir_returns_empty(self, tmp_path: Path):
        result = _build_from_markdown(tmp_path / "no_such_dir")
        assert result == {}

    def test_no_url_in_header(self, tmp_path: Path):
        md_dir = tmp_path / "markdown"
        md_dir.mkdir()
        (md_dir / "plain.md").write_text("# No URL here\nJust text.", encoding="utf-8")

        result = _build_from_markdown(md_dir)
        assert result == {}


# ── build_source_to_notion_url ───────────────────────────

class TestBuildSourceToNotionUrl:
    def test_prefers_index_over_markdown(self, tmp_path: Path):
        # 同時建立 index 和 markdown
        index = [
            {
                "title": "SEO A",
                "url": "https://www.notion.so/SEO-A-from-index",
                "md_file": "markdown/A.md",
            },
        ]
        idx_file = tmp_path / "meetings_index.json"
        idx_file.write_text(json.dumps(index), encoding="utf-8")

        md_dir = tmp_path / "markdown"
        md_dir.mkdir()
        (md_dir / "A.md").write_text(
            "- **Notion URL**: https://www.notion.so/SEO-A-from-markdown",
            encoding="utf-8",
        )

        result = build_source_to_notion_url(idx_file, md_dir)
        # index 優先
        assert result["A.md"] == "https://www.notion.so/SEO-A-from-index"

    def test_fallback_to_markdown(self, tmp_path: Path):
        # index 不存在
        idx_file = tmp_path / "nonexistent_index.json"

        md_dir = tmp_path / "markdown"
        md_dir.mkdir()
        (md_dir / "B.md").write_text(
            "- **Notion URL**: https://www.notion.so/SEO-B-from-md",
            encoding="utf-8",
        )

        result = build_source_to_notion_url(idx_file, md_dir)
        assert result["B.md"] == "https://www.notion.so/SEO-B-from-md"

    def test_real_index_coverage(self):
        """整合測試：驗證真實 meetings_index.json 載入正確。"""
        real_index = Path(__file__).resolve().parent.parent / "raw_data" / "meetings_index.json"
        if not real_index.exists():
            pytest.skip("raw_data/meetings_index.json 不存在")

        result = build_source_to_notion_url(real_index)
        assert len(result) >= 80, f"預期至少 80 筆映射，實際 {len(result)}"
        # 全部 URL 都是 Notion
        for url in result.values():
            assert url.startswith("https://www.notion.so/"), f"非 Notion URL: {url}"
