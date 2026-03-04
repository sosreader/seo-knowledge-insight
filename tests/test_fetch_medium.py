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
