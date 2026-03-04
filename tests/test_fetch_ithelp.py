"""Tests for scripts/01c_fetch_ithelp.py"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest


def _import_fetch_ithelp():
    """Import the module with a non-standard name."""
    return importlib.import_module("scripts.01c_fetch_ithelp")


class TestArticleUrlPattern:
    def test_matches_ithelp_article_url(self):
        mod = _import_fetch_ithelp()
        html = '<a href="https://ithelp.ithome.com.tw/articles/10259247">Article</a>'
        matches = mod.ARTICLE_URL_PATTERN.findall(html)
        assert len(matches) == 1
        assert matches[0][1] == "10259247"

    def test_extracts_multiple_urls(self):
        mod = _import_fetch_ithelp()
        html = """
        <a href="https://ithelp.ithome.com.tw/articles/10259247">A</a>
        <a href="https://ithelp.ithome.com.tw/articles/10259300">B</a>
        """
        matches = mod.ARTICLE_URL_PATTERN.findall(html)
        assert len(matches) == 2

    def test_no_match_for_other_urls(self):
        mod = _import_fetch_ithelp()
        html = '<a href="https://example.com/articles/123">Other</a>'
        matches = mod.ARTICLE_URL_PATTERN.findall(html)
        assert len(matches) == 0


class TestIthelpIndex:
    def test_load_nonexistent_index(self, tmp_path: Path):
        mod = _import_fetch_ithelp()
        index_path = tmp_path / "nonexistent.json"
        with patch.object(mod, "INDEX_PATH", index_path):
            assert mod._load_index() == []

    def test_save_and_load_index(self, tmp_path: Path):
        mod = _import_fetch_ithelp()
        index_path = tmp_path / "index.json"
        test_data = [{"article_id": "10259247", "day": 1, "title": "Day 1"}]

        with patch.object(mod, "INDEX_PATH", index_path):
            mod._save_index(test_data)
            loaded = mod._load_index()
            assert loaded == test_data
