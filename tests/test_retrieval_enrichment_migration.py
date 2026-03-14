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