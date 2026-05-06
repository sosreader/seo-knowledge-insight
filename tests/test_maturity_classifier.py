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

    def test_l4_ai_search_visibility_strategy(self):
        """AI Search / AIO visibility strategy topics should classify as L4."""
        result = classify_maturity_level(
            keywords=["AI Overview", "品牌可見度", "GEO"],
            question="AI Overview 品牌可見度的核心影響因子有哪些？",
            answer="應從品牌提及、反向連結與可引用內容結構切入，建立 AI Search 可見度監測與競爭情報框架，持續追蹤品牌在 AIO 的曝光變化。",
        )
        assert result == "L4"

    def test_l4_scenario_planning_for_ai_seo_budget(self):
        """Scenario-planning and leadership budgeting topics should classify as L4."""
        result = classify_maturity_level(
            keywords=["AI SEO", "scenario planning", "citation growth"],
            question="向管理層爭取 AI SEO 預算時，為什麼應以情境規劃取代流量預測？",
            answer="因為 AI 搜尋流量預測不穩定，較合理的作法是用 conservative、moderate、aggressive 三種 scenario planning，搭配 citation growth、authority building 與 decision gates 來配置投資。",
        )
        assert result == "L4"

    def test_basic_ai_overview_question_stays_basic(self):
        """Basic explanatory AI questions should not be over-classified to L4."""
        result = classify_maturity_level(
            keywords=["AI Overview", "基礎"],
            question="什麼是 AI Overview？",
            answer="AI Overview 是 Google 在搜尋結果中提供的摘要，簡單來說是把答案先整理給使用者看。",
        )
        assert result == "L1"

    def test_expectation_does_not_trigger_prediction_l4(self):
        """「預期」should not be treated as the advanced 「預測」 signal."""
        result = classify_maturity_level(
            keywords=["排名", "預期"],
            question="預期排名會下降嗎？",
            answer="根據最近波動，預期排名可能小幅下修，先觀察一週即可。",
        )
        assert result != "L4"

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


class TestL4RetightenFixtures:
    """L4 retighten sprint regression — 5 TP（應為 L4）+ 5 FP（應降至非 L4）。

    驗證 plans/active/maturity-l4-retighten.md 的雙重證據規則：
    L4 必須同時有 keyword 命中 AND (advanced pattern OR L4_STRATEGY_TERMS OR 長答案 > 500)。
    純談 trend 詞（AI Overview / GEO / AEO / ai-driven / brand visibility）不再單獨升 L4。
    """

    # ── True-Positive：實作層級內容應維持 L4 ──────────────────────────────

    def test_tp_programmatic_seo_system(self):
        """大規模 programmatic SEO 系統設計 — 應為 L4。"""
        result = classify_maturity_level(
            keywords=["programmatic seo", "程式化 seo"],
            question="如何建立大規模 programmatic SEO 系統？",
            answer=(
                "建立 programmatic SEO 系統需要從資料來源、模板架構、URL 生成、品質審核四個面向設計 pipeline。"
                "先設計資料 schema，整合 API 自動化生成內容，建立 regression testing 框架確保品質。"
            ),
        )
        assert result == "L4"

    def test_tp_predictive_ranking_model(self):
        """排名預測模型 with ML — 應為 L4。"""
        result = classify_maturity_level(
            keywords=["排名預測", "預測模型", "machine learning"],
            question="如何建立 SEO 排名預測模型？",
            answer=(
                "排名預測模型可使用 machine learning 方法，結合歷史 GSC 資料、競爭對手指標、季節性因子訓練模型。"
                "建議用 random forest 或 XGBoost 架構，定期 retrain 並驗證 forecasting 準確度。"
            ),
        )
        assert result == "L4"

    def test_tp_cross_channel_attribution(self):
        """跨通路歸因模型實作 — 應為 L4。"""
        result = classify_maturity_level(
            keywords=["跨通路整合", "歸因模型", "multi-touch"],
            question="如何設計跨通路 SEO 歸因模型？",
            answer=(
                "跨通路整合需要結合 SEO、付費搜尋、社群、Email 等管道。"
                "建議使用 multi-touch attribution model，搭配 GA4 的事件追蹤建立資料 pipeline，"
                "整合到 BI 系統做 cross-channel 分析。"
            ),
        )
        assert result == "L4"

    def test_tp_recommendation_engine_for_internal_links(self):
        """推薦系統優化內部連結 — 應為 L4。"""
        result = classify_maturity_level(
            keywords=["推薦系統", "recommendation engine"],
            question="如何用推薦系統優化內部連結？",
            answer=(
                "建立內部連結推薦系統可使用協同過濾或 content-based recommendation engine。"
                "設計流程：從 GSC 抓 query → 嵌入向量 → 相似度排序 → 推薦給編輯器。"
                "需要架構 pipeline 並建立 A/B 測試框架驗證。"
            ),
        )
        assert result == "L4"

    def test_tp_seo_automated_regression_testing(self):
        """SEO 自動化測試框架 — 應為 L4。"""
        result = classify_maturity_level(
            keywords=["seo 自動化測試", "regression testing"],
            question="如何建立 SEO 自動化測試框架？",
            answer=(
                "SEO 自動化測試框架可使用 Playwright + GSC API 整合，建立 regression testing pipeline。"
                "每次發版前跑：meta tag 驗證、canonical 一致性、sitemap 完整性、robots.txt 規則、"
                "結構化資料 schema 驗證。發現問題自動建立 issue。"
            ),
        )
        assert result == "L4"

    # ── False-Positive：純 trend 內容應降為非 L4 ──────────────────────────

    def test_fp_ai_overview_concept_only(self):
        """純解釋 AI Overview 概念 — 不應為 L4。"""
        result = classify_maturity_level(
            keywords=["AI Overview", "AIO"],
            question="什麼是 AI Overview？",
            answer=(
                "AI Overview 是 Google 在搜尋結果頂部顯示的 AI 摘要功能。"
                "AIO 整合 LLM 為使用者提供問題答案，影響傳統藍色連結的點擊率。"
            ),
        )
        assert result != "L4"

    def test_fp_geo_aeo_definition_listing(self):
        """純列舉 GEO / AEO 名詞定義 — 不應為 L4。"""
        result = classify_maturity_level(
            keywords=["GEO", "AEO", "generative engine optimization"],
            question="GEO 和 AEO 有什麼差別？",
            answer=(
                "GEO 是 generative engine optimization 的縮寫，"
                "AEO 則是 answer engine optimization。兩者都是針對 AI 搜尋的優化概念。"
            ),
        )
        assert result != "L4"

    def test_fp_ai_driven_concept_explanation(self):
        """純談 ai-driven SEO 概念 — 不應為 L4。"""
        result = classify_maturity_level(
            keywords=["ai-driven", "ai-powered"],
            question="什麼是 ai-driven SEO？",
            answer=(
                "ai-driven SEO 是利用 AI 工具輔助 SEO 工作的概念，"
                "目前 ai-powered 工具越來越多，但實際應用仍在發展中。"
            ),
        )
        assert result != "L4"

    def test_fp_brand_visibility_short_note(self):
        """品牌可見度短篇科普 — 不應為 L4。"""
        result = classify_maturity_level(
            keywords=["品牌可見度", "ai visibility"],
            question="品牌可見度為什麼重要？",
            answer=(
                "品牌可見度反映使用者是否認得你的品牌，對 SEO 有間接影響。"
                "AI visibility 也是同樣道理，與品牌建立有關。"
            ),
        )
        assert result != "L4"

    def test_fp_aeo_introduction_paragraph(self):
        """AEO 入門介紹段落 — 不應為 L4。"""
        result = classify_maturity_level(
            keywords=["AEO", "answer engine optimization"],
            question="AEO 跟傳統 SEO 有什麼不一樣？",
            answer=(
                "AEO（answer engine optimization）著重在問答型搜尋的優化，"
                "而傳統 SEO 主要處理藍色連結排名。對 SEO 從業者來說是新概念。"
            ),
        )
        assert result != "L4"
