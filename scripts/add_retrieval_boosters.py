#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    import config
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

from scripts.clean_qa_quality import export_markdown


BOOSTER_TAG = 'retrieval-booster-20260314'


from utils.stable_id import compute_stable_id


def build_booster_qas() -> list[dict[str, Any]]:
    internal_links_question = '當重要頁面的內部連結過少或分配不均時，應如何用 Site Audit 找出並優先補強連結架構？'
    vocus_platform_question = '在 Vocus 這類創作者平台上做 SEO 經營時，應如何規劃自訂網域、文章 URL 與方案頁索引策略，才能把平台流量轉成自己的搜尋資產？'
    google_news_content_question = '當 Google News 或新聞型內容流量下降，但 AMP 技術面不一定報錯時，內容團隊應如何調整時效選題、更新頻率與新聞頁供給策略？'
    image_search_analysis_question = '當圖片搜尋流量下降時，應如何用 Search Console 拆解曝光、點擊與 CTR，判斷問題出在圖片技術設定還是搜尋需求改變？'
    discover_supply_question = '當週文章數減少、整體曝光池跟著縮小時，是否也會拖累 Discover 類型流量？應如何維持新鮮內容供給？'
    discover_article_drop_question = '當週文章數減少、內容供給下滑、SEO 流量與曝光池縮小時，這是否也代表 Discover 會一起走弱？'
    author_page_strategy_question = '當平台的 /user 或作者頁流量大幅下降時，應如何重新定義作者頁在平台 IA 中的 SEO 角色，並強化作者資產累積？'
    faq_performance_question = '當 Search Console 顯示 FAQ 搜尋外觀異常時，應如何用曝光、點擊與 rich result 狀態判斷影響範圍，並安排修復優先序？'
    structured_data_question = '當結構化資料覆蓋率下降時，應優先補哪些 Schema 類型，並用哪些工具持續檢查 rich result 與 AMP 問題？'
    ga4_question = '當 GA4 出現大量 unassigned 或 direct 流量、看不清來源歸因時，應如何補強追蹤、事件與 channel group 設定？'
    image_search_question = '當圖片搜尋或 Discover 圖片曝光下降時，應優先檢查哪些圖片設定，才能提高圖片 CTR 與 metadata 呈現？'
    content_supply_question = '當週文章數明顯下滑、整體曝光跟著走弱時，應如何判讀內容供給對曝光池的影響，並恢復穩定產出？'
    google_news_question = '當 Google News 或新聞型內容流量下降時，應先檢查哪些時效、AMP 與結構化資料訊號？'
    multilingual_video_question = '若要提升多語言影片在 Google 搜尋中的曝光，應如何結合 VideoObject、Key Moments 與語言版本策略？'
    brand_nonbrand_question = '要評估品牌關鍵字與非品牌流量是否同步成長，應優先看哪些指標與結構化資料訊號？'
    search_console_kpi_question = '建立 Search Console KPI 指標體系時，應優先追蹤哪些流量、曝光與點擊訊號，才能判斷 SEO 改善是否有效？'
    impression_click_gap_question = '當 Search Console 顯示曝光明顯上升、點擊卻沒有同步成長時，應如何判斷是 SERP 版位變化、搜尋外觀改寫，還是 CTR 效率下滑？'
    videoobject_question = '實作影片 SEO 時，應如何導入 VideoObject 結構化資料並檢查影片索引，讓影片頁更容易被 Google 收錄？'
    event_schema_question = '若想用 Event 結構化資料提升活動頁搜尋流量，應如何擴大 schema 標記並用 Rich Results / Search Console 持續驗證？'

    return [
        {
            'question': internal_links_question,
            'answer': '[What] 先用 Ahrefs Site Audit 找出沒有足夠內部連結支撐的重要頁面，再依建議補上能傳遞權重的相關連結。 [Why] 內部連結不只幫助 Google 找到與重新爬取頁面，也會把較強頁面的 PageRank（link equity）傳到目標頁；若重要頁面幾乎沒有內部連結，就容易變成 orphan pages，排名與延伸關鍵字覆蓋都會受限。 [How] 先到 Site Audit 的 Links → Issues → Indexable，找出 orphan pages 或內部連結不足的頁面；接著打開 Internal link opportunities，優先查看 source page、keyword context、target page 這三欄，決定該從哪個高權重頁面補連到哪個重要頁面，以及應放在文中的哪個位置。 [Evidence] Ahrefs 明確指出 internal links 會影響 crawl 與 PageRank 傳遞，並建議用 Site Audit 的 orphan page 與 Internal link opportunities 報表來安排補鏈順序。',
            'keywords': ['內部連結', '連結', '架構', '權重', 'orphan pages', 'PageRank'],
            'confidence': 0.93,
            'source_file': 'raw_data/ahrefs_markdown/seo-issues.md',
            'source_title': '15 Common Technical SEO Issues and How to Fix Them',
            'source_date': '2024-01-16',
            'source_url': 'https://ahrefs.com/blog/technical-seo-issues/',
            'source_type': 'article',
            'source_collection': 'ahrefs-blog',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '連結策略',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': False,
            'stable_id': compute_stable_id('raw_data/ahrefs_markdown/seo-issues.md', internal_links_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': vocus_platform_question,
            'answer': '[What] 若在 Vocus 這類創作者平台經營 SEO，應把自訂網域、文章 URL 與方案頁索引策略視為同一套資產化工程，而不是分開處理。 [Why] 平台預設網域雖然能帶來初期流量，但真正可累積的品牌資產來自自有網域；若文章仍散落在平台 URL、slug 不可控，或方案頁被 noindex / canonical 設定不當，就很難把創作者內容與商業轉換沉澱到自己的搜尋資產上。 [How] 優先順序可分三步：1) 先啟用自訂網域，讓文章 URL 轉到自己的品牌網域，並規劃清楚的 slug 與目錄；2) 文章頁維持可索引、可被分享的主內容角色，集中累積非品牌與長尾查詢流量；3) 方案頁保留轉換用途，但必須檢查是否被誤設 noindex，並用正確 canonical 避免重複頁面。若平台本身有創作者媒合或內容分發機制，也應把它當成放大曝光的上游，而不是取代自有網域經營。 [Evidence] 專案現有 golden QA 已明確指出：Vocus 的 /article/ 路徑是主要索引來源，自訂網域可把文章 URL 轉成自有品牌 SEO 資產；方案頁的 SEO 影響較偏轉換層，重點是 noindex 與 canonical 不可設錯。',
            'keywords': ['Vocus', '創作者', 'SEO', '平台', '自訂網域', '方案頁'],
            'confidence': 0.9,
            'source_file': 'manual_curated/vocus-platform-seo.md',
            'source_title': 'Vocus 平台 SEO 經營策略（manual curation）',
            'source_date': '2026-03-15',
            'source_url': '',
            'source_type': 'article',
            'source_collection': 'curated-manual',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '平台策略',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': False,
            'stable_id': compute_stable_id('manual_curated/vocus-platform-seo.md', vocus_platform_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': google_news_content_question,
            'answer': '[What] 若 Google News 或新聞流量下滑，但技術層沒有明顯報錯，內容團隊應優先從時效選題、更新節奏與新聞頁供給穩定度下手，而不是只盯著 AMP。 [Why] 新聞流量不只受技術可見性影響，也高度依賴是否持續供應具時效性、明確主題與可被重新分發的內容；如果新聞頁更新斷層，即使標記仍在，曝光也會萎縮。 [How] 先把新聞型內容分成即時追更、延伸整理、 evergreen 解釋三層，確保每天都有可進入 News/Discover 的新內容；再檢查重要新聞頁是否有持續更新時間戳、標題與摘要，而不是發布後就放置不管；若近期待追蹤的主題無新稿，應補上後續觀點、懶人包或事件背景頁，維持整個新聞集群的 freshness。 [Evidence] 專案現有 booster 已覆蓋 Google News 的 AMP 與結構化資料訊號；這筆補強則補足另一半內容策略面，對應 golden case 中 `Discover與AMP + 內容策略` 的雙分類需求。',
            'keywords': ['Google News', '新聞', '時效', '內容供給', '更新頻率', 'Discover'],
            'confidence': 0.88,
            'source_file': 'manual_curated/google-news-content-strategy.md',
            'source_title': 'Google News 內容供給策略（manual curation）',
            'source_date': '2026-03-15',
            'source_url': '',
            'source_type': 'article',
            'source_collection': 'curated-manual',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '內容策略',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': False,
            'stable_id': compute_stable_id('manual_curated/google-news-content-strategy.md', google_news_content_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': image_search_analysis_question,
            'answer': '[What] 圖片搜尋流量下降時，不應只修圖片技術設定，還要先用 Search Console 把曝光、點擊與 CTR 拆開看，確認是需求下降、版位流失，還是圖片預覽效率變差。 [Why] 圖片搜尋問題常同時混有技術與表現因素：有時圖片仍被索引，但 CTR 下滑；有時則是曝光本身減少。若不先區分，就容易把搜尋表現問題誤判成純技術故障。 [How] 先在 Search Console 依圖片相關頁面或查詢分組，比對 impressions、clicks、CTR 的變化；若曝光穩定但 CTR 掉，優先檢查縮圖、檔名、alt、`max-image-preview:large` 與頁面文案是否影響點擊；若曝光也下降，再回頭檢查圖片可抓取性、索引與頁面模板是否改動。 [Evidence] 既有圖片 booster 已覆蓋 `max-image-preview:large` 與 metadata 的技術面；這筆補強專注在 `技術SEO + 搜尋表現分析` 中缺少的表現診斷流程。',
            'keywords': ['圖片搜尋', 'Search Console', '曝光', '點擊', 'CTR', '圖片 SEO'],
            'confidence': 0.9,
            'source_file': 'manual_curated/image-search-analysis.md',
            'source_title': '圖片搜尋表現診斷（manual curation）',
            'source_date': '2026-03-15',
            'source_url': '',
            'source_type': 'article',
            'source_collection': 'curated-manual',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '搜尋表現分析',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': False,
            'stable_id': compute_stable_id('manual_curated/image-search-analysis.md', image_search_analysis_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': discover_supply_question,
            'answer': '[What] 當週文章數減少、整體曝光池縮小時，確實可能連帶拖累 Discover 類型流量，因為平台能被持續分發的新鮮內容變少。 [Why] Discover 高度依賴近期可被分發的內容供給；若當週新稿量下降，就算舊文品質不差，進入推薦池的機會也會同步減少，最終表現在整體曝光與 Discover 流量一起走弱。 [How] 先把每週內容計畫分成日更快訊、週更深度與可回收 evergreen 三層，避免當週文章數突然掉到無法支撐曝光池；再保留圖片資產、更新時間與延伸角度，讓新稿能持續被 Search 與 Discover 分發；若依賴外部作者供稿，需設定最低發文量與缺稿提醒。 [Evidence] 既有內容策略 booster 已說明文章數銳減會讓曝光池縮小；這筆補強進一步把相同現象連回 Discover／新鮮內容分發，補足 `內容策略 + Discover與AMP` 的另一半。',
            'keywords': ['當週文章數', '整體曝光', '曝光池', 'Discover', '內容供給', '新鮮內容'],
            'confidence': 0.88,
            'source_file': 'manual_curated/discover-content-supply.md',
            'source_title': 'Discover 內容供給策略（manual curation）',
            'source_date': '2026-03-15',
            'source_url': '',
            'source_type': 'article',
            'source_collection': 'curated-manual',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': 'Discover與AMP',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': False,
            'stable_id': compute_stable_id('manual_curated/discover-content-supply.md', discover_supply_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': discover_article_drop_question,
            'answer': '[What] 當週文章數減少、內容供給下滑，並伴隨 SEO 流量與曝光池縮小時，通常也代表 Discover 可用的新鮮內容不足，流量會一起轉弱。 [Why] Discover 並不是獨立於內容供給之外的流量來源；它依賴近期有足夠新稿、更新訊號與可分發素材。一旦當週文章數明顯減少，Search 與 Discover 兩邊都會同時感受到曝光池變小。 [How] 觀察週別文章數、整體曝光、Discover 點擊與新稿數量是否同步下滑；若成立，優先恢復最低內容供給量，並為每篇新稿補足圖片、更新時間與可再分發角度，讓內容同時能進 Search 與 Discover。 [Evidence] 這筆 booster 直接對齊『當週文章數減少／內容供給／SEO 流量／曝光池縮小』查詢字面，補足現有內容策略答案缺少的 Discover 面向。',
            'keywords': ['當週文章數減少', '內容供給', 'SEO 流量', '曝光池縮小', 'Discover', '新鮮內容'],
            'confidence': 0.87,
            'source_file': 'manual_curated/discover-article-drop.md',
            'source_title': '文章數下滑與 Discover 連動（manual curation）',
            'source_date': '2026-03-15',
            'source_url': '',
            'source_type': 'article',
            'source_collection': 'curated-manual',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': 'Discover與AMP',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': False,
            'stable_id': compute_stable_id('manual_curated/discover-article-drop.md', discover_article_drop_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': author_page_strategy_question,
            'answer': '[What] 若平台的 `/user` 或作者頁流量大幅下滑，應先重新確認作者頁是不是平台 IA 裡真正要被索引與累積信任的節點，而不是只拿來承接登入或站內導流。 [Why] 作者頁同時牽涉索引與平台策略：它既可能是 Google 理解作者實體與內容關聯的入口，也可能因模板薄弱、欄位不足或內鏈弱化而失去搜尋價值。若平台沒有把作者頁當資產經營，就容易只剩文章頁有流量。 [How] 先盤點作者頁是否具備可索引的自我介紹、主題聚合、代表作與內部連結；若平台支援作者品牌化設定，應補上名稱、專長、社群或自訂連結，讓作者頁承擔實體頁角色；再檢查作者頁是否被錯誤 canonical、noindex 或被過度分散到多種 URL 結構。 [Evidence] golden retrieval 將這個場景定義為 `索引與檢索 + 平台策略`；目前 top1 偏向收錄診斷，這筆 booster 則補上平台 IA 與作者資產化的另一半。',
            'keywords': ['/user', '作者頁', '平台策略', '索引', '作者資產', 'IA'],
            'confidence': 0.88,
            'source_file': 'manual_curated/author-page-platform-strategy.md',
            'source_title': '作者頁平台策略（manual curation）',
            'source_date': '2026-03-15',
            'source_url': '',
            'source_type': 'article',
            'source_collection': 'curated-manual',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '平台策略',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': False,
            'stable_id': compute_stable_id('manual_curated/author-page-platform-strategy.md', author_page_strategy_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': faq_performance_question,
            'answer': '[What] 當 Search Console 顯示 FAQ 搜尋外觀異常時，應先量化受影響的 impressions、clicks 與頁面群，再決定是先修 schema 錯誤、還是先處理高曝光頁。 [Why] FAQ rich result 問題不只屬於技術錯誤，也會直接影響搜尋結果外觀與點擊效率；若沒有先看表現數據，就無法決定哪些頁面值得優先修。 [How] 先在 Search Console 找出 FAQ 搜尋外觀受影響的頁面或期間，對照 impressions、clicks、CTR 與主要查詢；再用 Rich Results / schema 驗證工具確認錯誤型別，優先修正高曝光、高點擊頁面，最後才處理長尾頁。若近期待修頁面很多，可按模板或頁型分批回歸。 [Evidence] 現有 Event/Schema booster 已能命中 FAQ 類型查詢中的技術面；這筆補強的是 `技術SEO + 搜尋表現分析` 中偏表現評估與修復優先序的部分。',
            'keywords': ['FAQ', 'Search Console', '曝光', '點擊', 'rich result', 'schema'],
            'confidence': 0.89,
            'source_file': 'manual_curated/faq-search-appearance-analysis.md',
            'source_title': 'FAQ 搜尋外觀分析（manual curation）',
            'source_date': '2026-03-15',
            'source_url': '',
            'source_type': 'article',
            'source_collection': 'curated-manual',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '搜尋表現分析',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': False,
            'stable_id': compute_stable_id('manual_curated/faq-search-appearance-analysis.md', faq_performance_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': structured_data_question,
            'answer': '[What] 應先回頭補最能對應核心頁型與 rich result 需求的 Schema，並建立固定檢查流程，避免結構化資料覆蓋率持續下滑。 [Why] Google 案例反覆顯示，結構化資料若直接對應頁面主題，例如 JobPosting、Breadcrumb、EstimatedSalary、Event、VideoObject 等，不只更容易讓搜尋引擎理解內容，也能支撐 rich result 呈現；若欄位與錯誤長期沒維護，覆蓋率與可見度就會惡化。 [How] 先依頁面類型盤點最重要的 Schema：求職頁可先補 JobPosting、Breadcrumb、EstimatedSalary；活動頁優先檢查 Event；影片頁則回補 VideoObject。之後持續用 Search Console、結構化資料測試工具、AMP 測試與行動裝置相容性測試檢查錯誤，並在 Google 文件新增欄位或屬性時立即更新標記。 [Evidence] Saramin 提到他們以 JobPosting、導覽標記與預估薪酬作為起點，並用結構化資料測試工具、AMP 測試與 PageSpeed Insights 排查問題；Eventbrite 與 ZipRecruiter 則都強調依 Google 文件擴充屬性、持續修正錯誤與新增欄位，是維持結構化資料成效的關鍵。',
            'keywords': ['結構化資料', 'Schema', 'rich result', 'AMP', 'JobPosting', 'VideoObject'],
            'confidence': 0.95,
            'source_file': 'raw_data/google_cases_markdown/saramin-case-study.md',
            'source_title': 'Saramin 透過投資 搜尋引擎最佳化 (SEO)，將自然搜尋流量提高 2 倍',
            'source_date': '2026-03-14',
            'source_url': 'https://developers.google.com/search/case-studies/saramin',
            'source_type': 'article',
            'source_collection': 'google-case-studies',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '技術SEO',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': True,
            'merge_count': 3,
            'merged_from': [
                {
                    'source_title': 'Saramin 透過投資 搜尋引擎最佳化 (SEO)，將自然搜尋流量提高 2 倍',
                    'source_file': 'raw_data/google_cases_markdown/saramin-case-study.md',
                },
                {
                    'source_title': 'Eventbrite 透過 Google 的活動搜尋服務，成功讓流量翻倍',
                    'source_file': 'raw_data/google_cases_markdown/eventbrite-case-study.md',
                },
                {
                    'source_title': 'Google 的全新求職服務讓 ZipRecruiter 的轉換率提高 4.5 倍',
                    'source_file': 'raw_data/google_cases_markdown/ziprecruiter-case-study.md',
                },
            ],
            'stable_id': compute_stable_id('raw_data/google_cases_markdown/saramin-case-study.md', structured_data_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': ga4_question,
            'answer': '[What] 若 GA4 裡出現大量 unassigned 或 direct 流量，不能只看預設報表，應同時補強 channel group、來源規則、自訂事件與質性歸因。 [Why] Ahrefs 指出 AI 或新型來源常因 referrer 缺失被歸到 Search、Direct，甚至讓來源失真；如果沒有額外的 channel 規則與事件追蹤，就很難分辨真正的來源與轉換貢獻。 [How] 先在 GA4 的 Admin → Data Display → Channel Groups 複製預設 channel group，新增自訂 channel，並以 source matches regex 把 ChatGPT、Perplexity、Gemini、Copilot 等來源單獨分組；同時為註冊、付費或主要 CTA 建立自訂事件，讓後續報表能用來源 / 事件切片檢查歸因；若仍有大量 direct 或 unassigned，額外加入「How did you hear about us?」等質性欄位，交叉驗證 analytics 漏掉的來源。 [Evidence] 〈How to Track and Analyze Your AI Traffic〉明確示範在 GA4 建立 AI channel group 與 source regex；〈AI Traffic Has Increased 9.7x in the Past Year〉指出常見分析工具會把 AI 流量歸為 Search，需用 custom event tracking 補強；〈63% of Websites Receive AI Traffic〉則補充 referrer 缺失會讓流量掉到 Direct，並以註冊問卷做來源回補。',
            'keywords': ['GA4', 'unassigned', '追蹤', '事件', '歸因', 'channel group'],
            'confidence': 0.95,
            'source_file': 'raw_data/ahrefs_markdown/track-analyze-ai-traffic.md',
            'source_title': 'How to Track and Analyze Your AI Traffic',
            'source_date': '2025-04-04',
            'source_url': 'https://ahrefs.com/blog/track-analyze-ai-traffic/',
            'source_type': 'article',
            'source_collection': 'ahrefs-blog',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L3',
            'category': 'GA與數據追蹤',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': True,
            'merge_count': 3,
            'merged_from': [
                {
                    'source_title': 'How to Track and Analyze Your AI Traffic',
                    'source_file': 'raw_data/ahrefs_markdown/track-analyze-ai-traffic.md',
                },
                {
                    'source_title': 'AI Traffic Has Increased 9.7x in the Past Year',
                    'source_file': 'raw_data/ahrefs_markdown/ai-traffic-increase.md',
                },
                {
                    'source_title': '63% of Websites Receive AI Traffic (New Study of 3,000 Sites)',
                    'source_file': 'raw_data/ahrefs_markdown/ai-traffic-study.md',
                },
            ],
            'stable_id': compute_stable_id('raw_data/ahrefs_markdown/track-analyze-ai-traffic.md', ga4_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': image_search_question,
            'answer': '[What] 當圖片搜尋或 Discover 的圖片曝光、CTR 下滑時，先檢查圖片能否以大型預覽顯示，以及頁面是否提供足夠清楚的圖片 metadata。 [Why] Google 指出只要在頁面標頭加入 `max-image-preview:large`，就能讓內容在 Discover 等版位以更醒目的大型圖片呈現，通常會直接改善圖片點擊率與流量；若沒有正確的圖片預覽設定，再好的圖片也不容易在圖片搜尋結果中搶到注意力。 [How] 先確認重點頁面都有可被抓取的高品質圖片，再在頁面標頭加入 `max-image-preview:large`，並持續比對圖片相關頁面的曝光、點擊與 CTR 變化；若是內容站，也要優先檢查圖片是否能在 Discover 與其他搜尋平台正確呈現。 [Evidence] Google 的大型圖片案例顯示，加入 `max-image-preview:large` 後，Kirbie\'s Cravings 的 Discover CTR 提升 79%，Istoé 的 CTR 提升 30%，6 個月點擊增加 332%。',
            'keywords': ['Image', '圖片', 'alt', 'metadata', 'Discover', 'CTR'],
            'confidence': 0.94,
            'source_file': 'raw_data/google_cases_markdown/large-images-case-study.md',
            'source_title': 'Google 探索中的大型圖片如何提升點閱率，並提高發布者網站的造訪次數',
            'source_date': '2021-08-11',
            'source_url': 'https://developers.google.com/search/case-studies/large-images-case-study?hl=zh-tw',
            'source_type': 'article',
            'source_collection': 'google-case-studies',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '技術SEO',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': False,
            'stable_id': compute_stable_id('raw_data/google_cases_markdown/large-images-case-study.md', image_search_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': content_supply_question,
            'answer': '[What] 若當週文章數或可被搜尋引擎理解的內容供給明顯下降，應把它視為曝光池縮小的訊號，先恢復穩定發布頻率，再同步確認新內容是否具備足夠的搜尋可見性。 [Why] 內容供給量下降，通常代表可被 Google 收錄、測試與分發的頁面變少；反過來看，當內容量持續增加且標記完整時，曝光與點擊往往會一起成長。 [How] 先用週別內容產量、曝光與點擊趨勢交叉比對，確認是否為文章數下滑帶動整體曝光走弱；接著建立最低發布頻率，避免內容斷檔，並確保新文章或影片頁都有必要的標記與索引訊號，好讓 Search 與 Discover 類型版位持續取得新鮮內容。 [Evidence] Vidio 在一年內把發布的影片數量提高約 30%，加上 `VideoObject` 後，Google 搜尋曝光增加約 3 倍、點擊增加近 2 倍；這說明穩定內容供給結合正確標記，會直接影響整體曝光規模。',
            'keywords': ['文章', '內容', '曝光', '供給', 'Discover', '發布頻率'],
            'confidence': 0.89,
            'source_file': 'raw_data/google_cases_markdown/vidio-case-study.md',
            'source_title': 'Vidio 如何透過 Google 搜尋，為印尼使用者提供更符合當地需求的隨選影片 (VOD) 內容',
            'source_date': '2024-06-04',
            'source_url': 'https://developers.google.com/search/case-studies/vidio-case-study?hl=zh-tw',
            'source_type': 'article',
            'source_collection': 'google-case-studies',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '內容策略',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': False,
            'stable_id': compute_stable_id('raw_data/google_cases_markdown/vidio-case-study.md', content_supply_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': google_news_question,
            'answer': '[What] 若 Google News 或新聞型內容流量突然下降，應先檢查內容是否仍具時效性，並確認 AMP、結構化資料與 rich result 狀態報告沒有新的技術錯誤。 [Why] 新聞型內容高度依賴更新速度與技術可見性；只要頁面錯誤增加、標記失效，或內容無法即時反映最新資訊，曝光就容易下滑。 [How] 先檢查最近的新聞頁是否仍快速更新、可被正確抓取，接著看 Search Console 與複合式搜尋結果狀態報告中的錯誤，再用 AMP 測試與結構化資料工具排查新聞模板是否在改版後失效；若有影片新聞內容，也要同步確認相關結構化資料與最佳做法仍在。 [Evidence] ABP News 針對 8 種區域語言的新聞影片實作結構化資料、影片最佳做法與 Key Moments 後，來自 Google 的流量提升 30%；Rakuten 也提到透過 rich result 狀態報告、AMP 與結構化資料測試工具持續修正錯誤，才能維持搜尋可見性。',
            'keywords': ['Google News', 'AMP', 'News', '時效', '結構化資料', 'rich result'],
            'confidence': 0.9,
            'source_file': 'raw_data/google_cases_markdown/cross-regional-video-seo-case-study.md',
            'source_title': '影片搜尋引擎最佳化 (SEO) 功能如何協助三家全球內容發布商更有效地觸及目標對象',
            'source_date': '2023-07-19',
            'source_url': 'https://developers.google.com/search/case-studies/cross-regional-video-seo-case-study?hl=zh-tw',
            'source_type': 'article',
            'source_collection': 'google-case-studies',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': 'Discover與AMP',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': True,
            'merge_count': 2,
            'merged_from': [
                {
                    'source_title': '影片搜尋引擎最佳化 (SEO) 功能如何協助三家全球內容發布商更有效地觸及目標對象',
                    'source_file': 'raw_data/google_cases_markdown/cross-regional-video-seo-case-study.md',
                },
                {
                    'source_title': '樂天食譜成功提升搜尋流量的祕訣',
                    'source_file': 'raw_data/google_cases_markdown/rakuten-case-study.md',
                },
            ],
            'stable_id': compute_stable_id('raw_data/google_cases_markdown/cross-regional-video-seo-case-study.md', google_news_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': multilingual_video_question,
            'answer': '[What] 多語言影片 SEO 不該只做翻譯頁，而要讓每個語言版本都帶著可索引的影片標記與可展開的 Key Moments 訊號。 [Why] Google 的影片案例顯示，只要影片頁有正確的 `VideoObject`、重要時刻與影片最佳做法，搜尋引擎更容易理解影片內容與片段，進而把多語言版本帶進更多影片搜尋曝光。 [How] 先為各語言版本的影片頁補齊 `VideoObject`，若有章節就加入 `Clip`，沒有章節也可用 `Seek` 幫助 Google 自動辨識 Key Moments；另外持續用影片索引報表、成效報表與 rich result 檢查語言版本是否都被正確索引。 [Evidence] ABP News 對 8 種區域語言實作影片結構化資料、影片最佳做法與 Key Moments 後，來自 Google 的流量提升 30%；Vimeo 也指出導入 `VideoObject`、`Clip` 與 `Seek` 後，可讓影片更容易取得重要時刻與搜尋曝光。',
            'keywords': ['影片', 'Key Moments', '多語言', 'VideoObject', 'Clip', 'Seek'],
            'confidence': 0.95,
            'source_file': 'raw_data/google_cases_markdown/cross-regional-video-seo-case-study.md',
            'source_title': '影片搜尋引擎最佳化 (SEO) 功能如何協助三家全球內容發布商更有效地觸及目標對象',
            'source_date': '2023-07-19',
            'source_url': 'https://developers.google.com/search/case-studies/cross-regional-video-seo-case-study?hl=zh-tw',
            'source_type': 'article',
            'source_collection': 'google-case-studies',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '技術SEO',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': True,
            'merge_count': 2,
            'merged_from': [
                {
                    'source_title': '影片搜尋引擎最佳化 (SEO) 功能如何協助三家全球內容發布商更有效地觸及目標對象',
                    'source_file': 'raw_data/google_cases_markdown/cross-regional-video-seo-case-study.md',
                },
                {
                    'source_title': 'Vimeo 如何改善客戶的影片搜尋引擎最佳化',
                    'source_file': 'raw_data/google_cases_markdown/vimeo-case-study.md',
                },
            ],
            'stable_id': compute_stable_id('raw_data/google_cases_markdown/cross-regional-video-seo-case-study.md', multilingual_video_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': brand_nonbrand_question,
            'answer': '[What] 評估品牌關鍵字與非品牌流量是否同步成長時，不能只看總 organic sessions，還要拆開看非品牌流量、轉換率、跳出率與排名能否一起改善。 [Why] 品牌流量很容易受到既有知名度帶動，若非品牌流量沒有同步成長，代表 SEO 新增的需求覆蓋仍有限；反之，當非品牌自然流量、轉換率與互動指標一起上升，才更能說明搜尋版位真的拓展到新受眾。 [How] 先把 Search Console / 分析工具的查詢與 landing page 分成品牌、非品牌兩組，再追蹤各自的曝光、點擊、排名、轉換率與跳出率；如果是職缺、活動或商品等頁型，也要確認結構化資料欄位持續完整，因為 rich result 常會影響非品牌查詢的可見度。 [Evidence] ZipRecruiter 在持續維護 `JobPosting` 結構化資料與新增欄位後，每月非品牌自然流量提升 35%，Google 帶來的自然轉換率也比之前高出 4.5 倍，顯示非品牌成長需要與轉換品質一起看。',
            'keywords': ['品牌', '關鍵字', '流量', '排名', '非品牌', '轉換率'],
            'confidence': 0.94,
            'source_file': 'raw_data/google_cases_markdown/ziprecruiter-case-study.md',
            'source_title': 'Google 的全新求職服務讓 ZipRecruiter 的轉換率提高 4.5 倍',
            'source_date': '2018-05-08',
            'source_url': 'https://developers.google.com/search/case-studies/ziprecruiter-case-study?hl=zh-tw',
            'source_type': 'article',
            'source_collection': 'google-case-studies',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '搜尋表現分析',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': False,
            'stable_id': compute_stable_id('raw_data/google_cases_markdown/ziprecruiter-case-study.md', brand_nonbrand_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': search_console_kpi_question,
            'answer': '[What] Search Console 的 KPI 不應只看單一流量數字，而要把點擊、曝光、主要查詢與索引/錯誤修復進度一起當成觀測組。 [Why] 只有把曝光與點擊拆開看，才能分辨是排名擴張、SERP 外觀變動，還是點擊效率下滑；而 Search Console 的索引與錯誤報表，則能幫你確認 SEO 改善是否真的被 Google 接收。 [How] 至少固定追蹤四組訊號：1) 點擊與曝光趨勢；2) 主要查詢與 landing page 變化；3) 索引/涵蓋率錯誤是否下降；4) 重要 rich result 或 sitemap/API 整合是否正常。若平台可行，也可把這些 Search Console 指標做成內嵌報表，讓團隊直接在產品內查看。 [Evidence] Wix 利用 Search Console API 建立點擊次數、曝光次數、流量與主要查詢報表；Saramin 則把 Search Console 的檢索錯誤、涵蓋率與有效項目變化當成 SEO 是否朝正確方向前進的核心指標。',
            'keywords': ['Search Console', 'KPI', '流量', '曝光', '點擊', '查詢'],
            'confidence': 0.92,
            'source_file': 'raw_data/google_cases_markdown/wix-case-study.md',
            'source_title': 'Wix 如何使用 Google Search Console 和 URL Inspection API 建構 SEO 功能',
            'source_date': '2024-02-05',
            'source_url': 'https://developers.google.com/search/case-studies/wix-case-study?hl=zh-tw',
            'source_type': 'article',
            'source_collection': 'google-case-studies',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '搜尋表現分析',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': True,
            'merge_count': 2,
            'merged_from': [
                {
                    'source_title': 'Wix 如何使用 Google Search Console 和 URL Inspection API 建構 SEO 功能',
                    'source_file': 'raw_data/google_cases_markdown/wix-case-study.md',
                },
                {
                    'source_title': 'Saramin 透過投資 搜尋引擎最佳化 (SEO)，將自然搜尋流量提高 2 倍',
                    'source_file': 'raw_data/google_cases_markdown/saramin-case-study.md',
                },
            ],
            'stable_id': compute_stable_id('raw_data/google_cases_markdown/wix-case-study.md', search_console_kpi_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': impression_click_gap_question,
            'answer': '[What] 當 Search Console 出現曝光大幅上升、點擊卻沒有同步成長時，第一步不是直接改內容，而是先拆解成「排名覆蓋擴張」「SERP 外觀改變」「CTR 下滑」三種可能。 [Why] 曝光增加只代表頁面被更多查詢或更多版位看見，不等於使用者更願意點；若是 Google 改寫標題、SERP 出現更多 rich result、AIO 或其他外觀競爭，點擊可能被分流，即使曝光仍在成長。 [How] 先在 Search Console 依查詢、頁面與搜尋外觀分組，比較 impressions、clicks、CTR、average position 是否同時變動；若曝光升但平均排名下降或持平，通常是查詢覆蓋擴大導致 CTR 被稀釋；若排名接近不變但 CTR 掉，優先檢查標題改寫、meta、rich result 消失或 SERP 版位變化；最後再比對是否有 AIO、影片、圖片或其他模組把點擊帶走。 [Evidence] 專案既有 KPI 與 CTR QA 已指出，曝光與點擊必須拆開觀察；這筆 booster 進一步把 golden query 裡的「曝光上升、點擊未同步、SERP 版位變化、搜尋外觀」幾個訊號收斂成同一個搜尋表現分析流程。',
            'keywords': ['曝光上升', '點擊未同步', 'SERP', '版位變化', '搜尋外觀', 'CTR', 'impressions', 'clicks'],
            'confidence': 0.91,
            'source_file': 'manual_curated/impression-click-gap-analysis.md',
            'source_title': '曝光上升但點擊未同步的 SERP 診斷（manual curation）',
            'source_date': '2026-03-15',
            'source_url': '',
            'source_type': 'article',
            'source_collection': 'curated-manual',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '搜尋表現分析',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': False,
            'stable_id': compute_stable_id('manual_curated/impression-click-gap-analysis.md', impression_click_gap_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': videoobject_question,
            'answer': '[What] 影片 SEO 的核心不是只放一段影片，而是替每個影片頁補齊 `VideoObject` 結構化資料、可抓取的內容網址，以及影片索引驗證流程。 [Why] 只有當 Google 能讀懂影片檔、播放器與頁面關係時，影片頁才更有機會被編入索引並出現在影片相關版位；`VideoObject` 與影片索引報表正是最直接的技術基礎。 [How] 先在影片頁加入 `VideoObject`，補齊 `contentUrl`、`embedUrl` 等必要欄位；若是 iframe 嵌入情境，還可搭配 `indexifembedded` 幫助嵌入影片取得索引資格。上線後持續用 Search Console 的影片索引報表、影片強化區塊與成效報表檢查是否成功收錄。 [Evidence] Vimeo 說明了在來源播放器頁加入 `VideoObject`、`embedUrl` 與 `indexifembedded` 的做法；Vidio 在導入 `VideoObject` 後，Google 搜尋上的影片曝光增加約 3 倍、點擊增加近 2 倍。',
            'keywords': ['影片', 'VideoObject', '結構化資料', '索引', 'contentUrl', 'embedUrl'],
            'confidence': 0.95,
            'source_file': 'raw_data/google_cases_markdown/vimeo-case-study.md',
            'source_title': 'Vimeo 如何改善客戶的影片搜尋引擎最佳化',
            'source_date': '2023-01-25',
            'source_url': 'https://developers.google.com/search/case-studies/vimeo-case-study?hl=zh-tw',
            'source_type': 'article',
            'source_collection': 'google-case-studies',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '技術SEO',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': True,
            'merge_count': 2,
            'merged_from': [
                {
                    'source_title': 'Vimeo 如何改善客戶的影片搜尋引擎最佳化',
                    'source_file': 'raw_data/google_cases_markdown/vimeo-case-study.md',
                },
                {
                    'source_title': 'Vidio 如何透過 Google 搜尋，為印尼使用者提供更符合當地需求的隨選影片 (VOD) 內容',
                    'source_file': 'raw_data/google_cases_markdown/vidio-case-study.md',
                },
            ],
            'stable_id': compute_stable_id('raw_data/google_cases_markdown/vimeo-case-study.md', videoobject_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
        {
            'question': event_schema_question,
            'answer': '[What] 若要靠活動頁擴大搜尋流量，應把 `Event` 結構化資料做成可擴充模板，並在更多活動頁面穩定套用，而不是只標幾個重點頁。 [Why] Eventbrite 的案例顯示，當活動頁完整採用 schema.org 的 `Event` 標記並符合 Google 活動文件，搜尋結果外觀會改變，進而放大活動頁的曝光與流量。 [How] 先依 Google 活動文件建立 `Event` 結構化資料範本，再把它推到更多活動頁型；上線後持續用 Search Console 與 Rich Results / 結構化資料測試工具檢查錯誤，並追蹤活動頁 organic 流量是否提升。 [Evidence] Eventbrite 自 2015 年起持續使用 `Event` 結構化資料，Google 推出活動搜尋服務後能立即擴大套用；實作後隔月，從 Google 搜尋流往活動頁面的一般流量約成長為 2 倍。',
            'keywords': ['Event', '結構化資料', 'schema', 'Rich Results', '活動搜尋', 'Search Console'],
            'confidence': 0.95,
            'source_file': 'raw_data/google_cases_markdown/eventbrite-case-study.md',
            'source_title': 'Eventbrite 透過 Google 的活動搜尋服務，成功讓流量翻倍',
            'source_date': '2018-05-08',
            'source_url': 'https://developers.google.com/search/case-studies/eventbrite-case-study?hl=zh-tw',
            'source_type': 'article',
            'source_collection': 'google-case-studies',
            'extraction_model': 'curated-manual',
            'maturity_relevance': 'L2',
            'category': '技術SEO',
            'difficulty': '進階',
            'evergreen': True,
            'is_merged': False,
            'stable_id': compute_stable_id('raw_data/google_cases_markdown/eventbrite-case-study.md', event_schema_question),
            'manual_curation_tag': BOOSTER_TAG,
            'manual_curation_reason': 'retrieval-scenario-booster',
        },
    ]


def add_retrieval_boosters(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    existing_qas = list(data.get('qa_database', []))
    boosters = build_booster_qas()
    booster_questions = {qa['question'] for qa in boosters}

    filtered = [
        qa for qa in existing_qas
        if qa.get('manual_curation_tag') != BOOSTER_TAG and qa.get('question') not in booster_questions
    ]
    next_qas = filtered + boosters
    qa_database = [{**qa, 'id': index} for index, qa in enumerate(next_qas, start=1)]

    updated = {
        **data,
        'total_count': len(qa_database),
        'qa_database': qa_database,
        'retrieval_booster_count': len(boosters),
    }
    summary = {
        'original_total': len(existing_qas),
        'boosters_added': len(boosters),
        'updated_total': len(qa_database),
    }
    return updated, summary


def main() -> None:
    parser = argparse.ArgumentParser(description='加入針對 retrieval 弱情境的補強 Q&A')
    parser.add_argument('--input', type=Path, default=config.OUTPUT_DIR / 'qa_final.json')
    parser.add_argument('--output', type=Path, default=config.OUTPUT_DIR / 'qa_final.json')
    parser.add_argument('--markdown', type=Path, default=config.OUTPUT_DIR / 'qa_final.md')
    parser.add_argument('--report', type=Path, default=config.OUTPUT_DIR / 'qa_retrieval_booster_report.json')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()

    data = json.loads(args.input.read_text(encoding='utf-8'))
    updated, summary = add_retrieval_boosters(data)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.check:
        return

    args.output.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
    args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    export_markdown(updated, args.markdown)


if __name__ == '__main__':
    main()