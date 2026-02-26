"""
Unit tests for core logic functions.

Run with: pytest tests/ -v
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ──────────────────────────────────────────────────────
# _extract_date_from_title
# ──────────────────────────────────────────────────────

from scripts.extract_qa_helpers import _extract_date_from_title, _extract_date_from_content, _split_content


class TestExtractDateFromTitle:
    def test_iso_format(self):
        assert _extract_date_from_title("SEO 會議_2024-05-02") == "2024-05-02"

    def test_slash_format(self):
        assert _extract_date_from_title("SEO 會議_2024/05/02") == "2024/05/02"

    def test_compact_format(self):
        assert _extract_date_from_title("SEO_會議_20240502") == "20240502"

    def test_no_date(self):
        assert _extract_date_from_title("Frank_SEO顧問會議") == ""

    def test_date_in_middle(self):
        assert _extract_date_from_title("某某_2023-11-28_會議") == "2023-11-28"


class TestExtractDateFromContent:
    def test_found(self):
        content = "blah\n- **會議日期**: 2024-03-15\n- other"
        assert _extract_date_from_content(content) == "2024-03-15"

    def test_not_found(self):
        assert _extract_date_from_content("no date here") == ""


# ──────────────────────────────────────────────────────
# _split_content
# ──────────────────────────────────────────────────────

class TestSplitContent:
    def test_short_content_no_split(self):
        content = "Hello world"
        result = _split_content(content, 1000)
        assert len(result) == 1
        assert result[0] == content

    def test_splits_on_headings(self):
        content = "intro\n\n## Section A\nAAA\n\n## Section B\nBBB"
        result = _split_content(content, 30)
        assert len(result) >= 2
        # Each chunk should be non-empty
        for chunk in result:
            assert len(chunk) > 0

    def test_splits_on_paragraphs_when_no_headings(self):
        """When no ## headings, should split on paragraph boundaries (\\n\\n)"""
        paragraphs = ["段落" * 20 for _ in range(5)]
        content = "\n\n".join(paragraphs)
        max_chars = len(paragraphs[0]) + 10  # Just over one paragraph
        result = _split_content(content, max_chars)
        assert len(result) >= 2
        # Should NOT cut in the middle of a paragraph
        for chunk in result:
            # Each chunk should contain complete paragraph(s)
            assert "段落" in chunk

    def test_single_giant_paragraph_still_works(self):
        """Even a single huge paragraph without any \\n\\n should be returned"""
        content = "字" * 10000
        result = _split_content(content, 100)
        # Should still return something (single chunk since no split point)
        assert len(result) >= 1
        total = "".join(result)
        assert total == content


# ──────────────────────────────────────────────────────
# cosine similarity matrix (vectorized)
# ──────────────────────────────────────────────────────

import numpy as np
from scripts.dedupe_helpers import _cosine_similarity_matrix


class TestCosineSimilarityMatrix:
    def test_identical_vectors(self):
        embs = [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
        mat = _cosine_similarity_matrix(embs)
        assert mat.shape == (2, 2)
        assert abs(mat[0, 1] - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        embs = [[1.0, 0.0], [0.0, 1.0]]
        mat = _cosine_similarity_matrix(embs)
        assert abs(mat[0, 1]) < 1e-6

    def test_zero_vector(self):
        embs = [[0.0, 0.0], [1.0, 0.0]]
        mat = _cosine_similarity_matrix(embs)
        # Zero vector should not cause NaN
        assert not np.isnan(mat).any()

    def test_self_similarity_is_one(self):
        embs = [[0.3, 0.7, 0.1], [0.9, 0.1, 0.5]]
        mat = _cosine_similarity_matrix(embs)
        for i in range(len(embs)):
            assert abs(mat[i, i] - 1.0) < 1e-5

    def test_symmetry(self):
        embs = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        mat = _cosine_similarity_matrix(embs)
        np.testing.assert_array_almost_equal(mat, mat.T)


# ──────────────────────────────────────────────────────
# block_to_markdown — rich text conversion
# ──────────────────────────────────────────────────────

from utils.block_to_markdown import _rich_text_to_md


class TestRichTextToMd:
    def test_plain_text(self):
        rt = [{"plain_text": "hello", "annotations": {}}]
        assert _rich_text_to_md(rt) == "hello"

    def test_bold(self):
        rt = [{"plain_text": "bold", "annotations": {"bold": True}}]
        assert _rich_text_to_md(rt) == "**bold**"

    def test_italic(self):
        rt = [{"plain_text": "em", "annotations": {"italic": True}}]
        assert _rich_text_to_md(rt) == "*em*"

    def test_code(self):
        rt = [{"plain_text": "var", "annotations": {"code": True}}]
        assert _rich_text_to_md(rt) == "`var`"

    def test_link(self):
        rt = [{"plain_text": "click", "annotations": {}, "href": "https://example.com"}]
        assert _rich_text_to_md(rt) == "[click](https://example.com)"

    def test_combined(self):
        rt = [
            {"plain_text": "start ", "annotations": {}},
            {"plain_text": "bold", "annotations": {"bold": True}},
            {"plain_text": " end", "annotations": {}},
        ]
        assert _rich_text_to_md(rt) == "start **bold** end"

    def test_empty(self):
        assert _rich_text_to_md([]) == ""
