from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from scripts.enrich_qa import _enrich_qa
from scripts import migrate_to_supabase


def test_enrich_qa_item_uses_article_source_url_when_present() -> None:
    qa = {
        "id": 1,
        "question": "Article QA",
        "answer": "Answer",
        "keywords": ["SEO"],
        "source_type": "article",
        "source_url": " https://example.com/article ",
        "source_file": "article.md",
    }

    enriched = _enrich_qa(qa, notion_url_map={"article.md": "https://notion.invalid/page"}, hit_counts={})

    assert enriched["_enrichment"]["source_url"] == "https://example.com/article"


def test_enrich_qa_item_falls_back_to_notion_url_for_blank_article_source_url() -> None:
    qa = {
        "id": 1,
        "question": "Article QA",
        "answer": "Answer",
        "keywords": ["SEO"],
        "source_type": "article",
        "source_url": "   ",
        "source_file": "article.md",
    }

    enriched = _enrich_qa(qa, notion_url_map={"article.md": "https://notion.invalid/page"}, hit_counts={})

    assert enriched["_enrichment"]["source_url"] == "https://notion.invalid/page"


def test_enrich_qa_backfills_maturity_relevance_when_missing() -> None:
    qa = {
        "id": 1,
        "question": "AI Overview 品牌可見度的核心影響因子有哪些？",
        "answer": "研究指出品牌提及、品牌錨文本與反向連結會影響 AI Overview 的品牌可見度，應建立跨通路監測與競爭情報框架持續追蹤。",
        "keywords": ["AI Overview", "品牌可見度", "競爭情報"],
        "source_type": "article",
        "source_file": "article.md",
        "source_date": "2026-03-01",
    }

    enriched = _enrich_qa(qa, notion_url_map={}, hit_counts={})

    assert enriched["maturity_relevance"] == "L4"
    assert enriched["_enrichment"]["maturity_relevance"] == "L4"


def test_enrich_qa_preserves_existing_maturity_relevance() -> None:
    qa = {
        "id": 1,
        "question": "Canonical 設定要怎麼檢查？",
        "answer": "先在 GSC 與站內稽核工具確認 canonical 一致。",
        "keywords": ["canonical", "GSC"],
        "maturity_relevance": "L2",
        "source_type": "meeting",
        "source_file": "meeting.md",
        "source_date": "2026-03-01",
    }

    enriched = _enrich_qa(qa, notion_url_map={}, hit_counts={})

    assert enriched["maturity_relevance"] == "L2"
    assert enriched["_enrichment"]["maturity_relevance"] == "L2"


def test_map_item_prefers_trimmed_source_url() -> None:
    row = migrate_to_supabase._map_item(
        {
            "id": 1,
            "question": "Q",
            "answer": "A",
            "source_url": " https://example.com/source ",
            "_enrichment": {
                "source_url": "https://stale.invalid",
                "notion_url": "https://notion.invalid/page",
            },
        },
        embedding=None,
    )

    assert row["source_url"] == "https://example.com/source"


def test_map_item_uses_enriched_maturity_relevance_when_top_level_missing() -> None:
    row = migrate_to_supabase._map_item(
        {
            "id": 1,
            "question": "Q",
            "answer": "A",
            "_enrichment": {
                "maturity_relevance": "L3",
            },
        },
        embedding=None,
    )

    assert row["maturity_relevance"] == "L3"


def test_migrate_raises_on_embedding_count_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(migrate_to_supabase, "_load_qa_data", lambda: [{"id": 1}, {"id": 2}])
    monkeypatch.setattr(
        migrate_to_supabase,
        "_load_embeddings",
        lambda: np.zeros((1, 3), dtype=np.float32),
    )

    with pytest.raises(ValueError, match="Count mismatch"):
        migrate_to_supabase.migrate(
            "https://example.supabase.co",
            "service-key",
            dry_run=True,
        )


def test_migrate_dry_run_succeeds_with_matching_counts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        migrate_to_supabase,
        "_load_qa_data",
        lambda: [{"id": 1, "question": "Q", "answer": "A", "source_title": "T"}],
    )
    monkeypatch.setattr(
        migrate_to_supabase,
        "_load_embeddings",
        lambda: np.zeros((1, 3), dtype=np.float32),
    )

    migrate_to_supabase.migrate(
        "https://example.supabase.co",
        "service-key",
        dry_run=True,
    )