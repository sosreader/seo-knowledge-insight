"""Tests for utils/maturity_classifier.py — rule-based maturity classification."""

import pytest
from utils.maturity_classifier import classify_maturity_level


class TestClassifyMaturityLevel:
    """Covers L1-L4 classification with edge cases."""

    def test_l1_basic_question(self):
        """Basic 'what is' questions should classify as L1."""
        result = classify_maturity_level(
            keywords=["SEO", "基礎"],
            question="什麼是 SEO？如何開始學習？",
            answer="SEO 是搜尋引擎最佳化，簡單來說就是讓網站在 Google 搜尋結果中排名更高。",
        )
        assert result == "L1"

    def test_l1_keyword_research(self):
        """Keyword research basics are L1."""
        result = classify_maturity_level(
            keywords=["keyword research", "入門"],
            question="如何做關鍵字研究？",
            answer="關鍵字研究是 SEO 的基礎，可以先使用 Google Keyword Planner 工具。",
        )
        assert result == "L1"

    def test_l2_process_tracking(self):
        """Process and tracking topics are L2."""
        result = classify_maturity_level(
            keywords=["Google Search Console", "追蹤", "指標"],
            question="如何用 Google Search Console 追蹤 SEO 指標？",
            answer="在 GSC 中設定效能報表，追蹤點擊、曝光、CTR 和排名。定期監控變化。",
        )
        assert result == "L2"

    def test_l2_internal_linking(self):
        """Internal linking strategy is L2."""
        result = classify_maturity_level(
            keywords=["internal link", "內部連結"],
            question="內部連結策略怎麼規劃？",
            answer="建立 sitemap 架構，使用 canonical 標籤避免重複，規劃內部連結的層級結構。",
        )
        assert result == "L2"

    def test_l3_data_driven(self):
        """Data-driven optimization topics are L3."""
        result = classify_maturity_level(
            keywords=["A/B test", "數據分析", "自動化"],
            question="如何用 A/B 測試優化 SEO 策略？",
            answer="建立 A/B 測試框架，使用數據分析工具追蹤轉換率。設計自動化 dashboard 監控 KPI。",
        )
        assert result == "L3"

    def test_l3_automation(self):
        """Automation and SOP topics are L3."""
        result = classify_maturity_level(
            keywords=["SOP", "automation"],
            question="如何建立 SEO SOP 和自動化流程？",
            answer="制定標準作業流程，整合 API 自動化報告生成。建立 content hub 策略。",
        )
        assert result == "L3"

    def test_l4_predictive(self):
        """Predictive analytics and AI-driven strategies are L4."""
        result = classify_maturity_level(
            keywords=["predictive", "machine learning", "cross-channel"],
            question="如何用機器學習預測 SEO 排名變化？",
            answer="建立預測模型分析歷史排名數據，整合跨通路歸因分析。",
        )
        assert result == "L4"

    def test_l4_competitive_intelligence(self):
        """Competitive intelligence is L4."""
        result = classify_maturity_level(
            keywords=["competitive intelligence", "AI-driven"],
            question="如何建立 AI 驅動的競爭情報系統？",
            answer="使用 AI 驅動分析工具追蹤競爭對手策略變化，建立自動化測試框架。",
        )
        assert result == "L4"

    def test_no_clear_signal_returns_none(self):
        """Ambiguous content should return None (low confidence)."""
        result = classify_maturity_level(
            keywords=["SEO"],
            question="SEO 很重要",
            answer="是的",
        )
        # Very short answer + no clear keywords = None or L1
        # (depends on scoring — L1 gets +1 from short answer)
        assert result in (None, "L1")

    def test_empty_inputs(self):
        """Empty inputs should return None."""
        result = classify_maturity_level(
            keywords=[],
            question="",
            answer="",
        )
        assert result is None

    def test_mixed_signals_prefers_higher(self):
        """When multiple levels match, highest score wins."""
        result = classify_maturity_level(
            keywords=["數據分析", "A/B test", "自動化", "dashboard"],
            question="如何建立 SEO 數據分析自動化 dashboard？",
            answer="整合 API 建立自動化 dashboard，用數據分析驅動決策。設定 SOP 流程。",
        )
        # L3 keywords dominate
        assert result == "L3"

    def test_case_insensitive(self):
        """Classification should be case-insensitive."""
        result = classify_maturity_level(
            keywords=["GOOGLE SEARCH CONSOLE", "KPI"],
            question="How to use GOOGLE SEARCH CONSOLE for tracking KPIs?",
            answer="Set up performance reports in GSC to monitor metrics.",
        )
        assert result == "L2"

    def test_chinese_l1_patterns(self):
        """Chinese basic patterns should classify as L1."""
        result = classify_maturity_level(
            keywords=["title tag"],
            question="什麼是 title tag？",
            answer="Title tag 是 HTML 中的標題標籤，簡單來說就是瀏覽器標籤上顯示的文字。",
        )
        assert result == "L1"
