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


def test_enrich_qa_adds_technical_and_video_metadata_for_videoobject() -> None:
    qa = {
        "id": 1,
        "question": "影片 SEO VideoObject 結構化資料應如何實作？",
        "answer": "應在影片頁加入 VideoObject 與 JSON-LD，並持續監控 Video Appearance 與索引覆蓋。",
        "keywords": ["影片 SEO", "VideoObject", "結構化資料"],
        "category": "索引與檢索",
        "source_type": "article",
        "source_file": "video.md",
        "source_date": "2026-03-01",
    }

    enriched = _enrich_qa(qa, notion_url_map={}, hit_counts={})

    assert "技術SEO" in enriched["categories"]
    assert "video-seo" in enriched["scenario_tags"]


def test_enrich_qa_adds_ai_tracking_categories_for_ai_traffic_ratio() -> None:
    qa = {
        "id": 1,
        "question": "如何追蹤 ChatGPT、Perplexity 與 Gemini 的 AI 流量佔比？",
        "answer": "可在 GA4 與 referral source 中建立 AI 流量佔比監控，並把 ChatGPT、Perplexity、Gemini 視為 AI Search 趨勢觀測來源。",
        "keywords": ["ChatGPT", "Perplexity", "Gemini", "AI 流量"],
        "category": "搜尋表現分析",
        "source_type": "article",
        "source_file": "ai-traffic.md",
        "source_date": "2026-03-01",
    }

    enriched = _enrich_qa(qa, notion_url_map={}, hit_counts={})

    assert "GA與數據追蹤" in enriched["categories"]
    assert "演算法與趨勢" in enriched["categories"]
    assert "ai-referral-traffic" in enriched["scenario_tags"]


def test_enrich_qa_adds_discover_and_trend_dual_categories() -> None:
    qa = {
        "id": 1,
        "question": "Google Discover 流量下降是否反映演算法趨勢改變？",
        "answer": "若 Discover 與 Google News 同步走弱，通常要同時檢查內容供給與演算法趨勢訊號。",
        "keywords": ["Discover", "Google News", "演算法"],
        "category": "內容策略",
        "source_type": "meeting",
        "source_file": "discover.md",
        "source_date": "2026-03-01",
    }

    enriched = _enrich_qa(qa, notion_url_map={}, hit_counts={})

    assert "Discover與AMP" in enriched["categories"]
    assert "演算法與趨勢" in enriched["categories"]


def test_enrich_qa_adds_dual_categories_for_waf_indexing_issues() -> None:
    qa = {
        "id": 1,
        "question": "WAF 封鎖 Googlebot 時，為何會造成檢索未索引增加？",
        "answer": "WAF 若誤擋 Googlebot，會讓 sitemap、coverage 與 canonical 訊號一起失真，造成檢索與技術問題並存。",
        "keywords": ["WAF", "Googlebot", "Coverage"],
        "category": "技術SEO",
        "source_type": "meeting",
        "source_file": "waf.md",
        "source_date": "2026-03-01",
    }

    enriched = _enrich_qa(qa, notion_url_map={}, hit_counts={})

    assert "技術SEO" in enriched["categories"]
    assert "索引與檢索" in enriched["categories"]


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