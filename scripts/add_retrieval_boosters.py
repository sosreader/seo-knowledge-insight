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


def compute_stable_id(source_file: str, question: str) -> str:
    content = f'{source_file}::{question[:120]}'
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def build_booster_qas() -> list[dict[str, Any]]:
    internal_links_question = '當重要頁面的內部連結過少或分配不均時，應如何用 Site Audit 找出並優先補強連結架構？'
    structured_data_question = '當結構化資料覆蓋率下降時，應優先補哪些 Schema 類型，並用哪些工具持續檢查 rich result 與 AMP 問題？'
    ga4_question = '當 GA4 出現大量 unassigned 或 direct 流量、看不清來源歸因時，應如何補強追蹤、事件與 channel group 設定？'
    image_search_question = '當圖片搜尋或 Discover 圖片曝光下降時，應優先檢查哪些圖片設定，才能提高圖片 CTR 與 metadata 呈現？'
    content_supply_question = '當週文章數明顯下滑、整體曝光跟著走弱時，應如何判讀內容供給對曝光池的影響，並恢復穩定產出？'
    google_news_question = '當 Google News 或新聞型內容流量下降時，應先檢查哪些時效、AMP 與結構化資料訊號？'
    multilingual_video_question = '若要提升多語言影片在 Google 搜尋中的曝光，應如何結合 VideoObject、Key Moments 與語言版本策略？'
    brand_nonbrand_question = '要評估品牌關鍵字與非品牌流量是否同步成長，應優先看哪些指標與結構化資料訊號？'
    search_console_kpi_question = '建立 Search Console KPI 指標體系時，應優先追蹤哪些流量、曝光與點擊訊號，才能判斷 SEO 改善是否有效？'
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
            'difficulty': '中階',
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
            'difficulty': '中階',
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
            'difficulty': '中階',
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
            'difficulty': '中階',
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
            'difficulty': '中階',
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