# SEO 業界動態追蹤

> 由 `/meeting-prep` 自動累積，每次執行 append 一個日期 section。
> 保留最近 12 次記錄（約 6 個月），超過自動移除最舊 section。

---

<!-- 以下為自動累積區域，請勿手動編輯格式 -->

## 2026-06-05（快照日期：2026-06-05）

### Google 官方
- [2026-06-02] **May 2026 Core Update 完成 rollout**（5/21→6/2，12 天，波動大於 3 月更新）（[Search Engine Land](https://searchengineland.com/google-may-2026-core-update-rollout-is-now-complete-479119)、[Search Engine Journal](https://www.searchenginejournal.com/googles-may-core-update-complete-after-volatile-rollout/577704/)）——本站核心軸月線翻正時點與完成重疊，需區分「重分配紅利 vs 真修復」
- [2026-05] **Crawl Budget API 推出** — 站長可看爬蟲預算缺口與優先順序評分；官方「變慢則預算降」、動態頁爬取頻率比靜態低 22%（[Google Developers](https://developers.google.com/crawling/docs/crawl-budget)）——直擊本站回應時間 694ms → 爬蟲量 −7.29% 痛點
- [2026-06-03] **GSC 生成式 AI 效能報告上線** + 內容阻擋 AI 回應控制（[Search Engine Land](https://searchengineland.com/google-search-console-ai-performance-reports-and-controls-to-block-your-content-in-ai-responses-479298)）——GEO 首次有官方引用率追蹤工具
- [官方 benchmark] 伺服器回應時間 ≤200ms、TTFB ≤800ms，超過則 Googlebot 自動降速（[Google PageSpeed](https://developers.google.com/speed/docs/insights/Server)）——本站 694ms 遠超 benchmark

### 業界報導
- **「為何大量 SEO 工作不再帶來成長」**（[Search Engine Land 6/4](https://searchengineland.com/why-so-much-seo-work-no-longer-drives-growth-479424)）——流量焦點轉向 AI 分發與品牌；**agentic web schema**（[6/1](https://searchengineland.com/schema-markup-optimize-agentic-web-479080)）
- **ChatGPT 佔 AI 引薦 87.4%**、8 月→1 月成長 206%（[Search Engine Land 13 個月 LLM 數據](https://searchengineland.com/what-13-months-of-data-reveals-about-llm-traffic-growth-and-conversions-470115)）；本站 GPT +14% 遠遜產業——Gemini 全球引薦超越 Perplexity（[Search Engine Journal](https://www.searchenginejournal.com/google-gemini-sends-more-traffic-to-sites-than-perplexity-report/570714/)）
- **Perplexity 金融垂直市佔 24%**、整體查詢量 7.8 億——呼應本站 KW 股 +168.98% 財經熱潮（[Search Engine Land](https://searchengineland.com/perplexity-780-million-monthly-queries-month-456725)）

### 關鍵字市場趨勢（B5/B6）
- **KW 股 +168.98% 經查為真實台股熱潮**（COMPUTEX AI + 台積電股東會 + AI 半導體題材，[台股三大利多](https://money.udn.com/money/story/5607/9537229)）——非 off-topic 雜訊，但事件性、且「股」SERP 被 AIO 48% + News + Finance 小工具三層夾擊（CTR 8% vs 15%）
- **KW 影評 +112%/電影 +28% 為新片檔期驅動**（玩具總動員 5 6/17 等，[2026 上映表](https://www.atmovies.com.tw/movie/next/)）；**KW 評價 −15% 為本站問題**（市場升、評測站 mybest/愛評網競爭）

### 對本站意涵
- 核心軸月線首翻正（曝光 +11.46%、Coverage +29.97%）但與 May Core Update 完成重疊，6/12 確認紅利是否回吐
- 上週「破 600 → Coverage 崩」預測失準：回應時間破 600（694ms）但 Coverage 反升——模型過度權重單一因果鏈
- 手機 CWV 大規模重分類（好 +117%、+44.5 萬頁）但與回應時間惡化背離——欄位資料延遲生效待驗證
- AMP 四指標 WoW 全反轉（Article +351%、警告 −7.54%）——上週退場確認需重估，佐證「單週數倍跳動先當口徑波動」

---

## 2026-05-29（快照日期：2026-05-29）

### Google 官方
- [2026-05-21 起，rollout 中] **May 2026 Core Update** — **5/30–5/31 週末「重擊」**大幅排名波動（[Search Engine Roundtable](https://www.seroundtable.com/)），預期數天內完成。本站 5/23–5/29 資料窗為 rollout 中期，完整衝擊（重擊在窗末端後）下週 6/5 才反映
- [2026 官方爬取文件] **Google explains how crawling works in 2026** — 「伺服器回應時間超過 ~300ms benchmark，檢索速率按比例自動下降」（[Search Engine Land](https://searchengineland.com/google-explains-how-crawling-works-in-2026-473110)）——直接解釋本站回應時間 544ms → 週平均檢索數 −16.25%
- [SER 6/1] 推出 **Volatility Aggregator**（多源波動分數整合）；測試 **AI Overviews link card sliding carousel**（引用版位強化）、AI Mode 醫療廣告限量測試

### 業界報導
- **AMP 非 Top Stories 必要條件再確認**：2021 起 Top Stories 改 Page Experience（LCP/CLS/INP）；publisher 關閉 AMP 後流量穩定（[Search Engine Land](https://searchengineland.com/amp-wont-be-required-for-googles-top-stories-section-335276)、[turn off AMP case](https://searchengineland.com/what-happened-when-we-turned-off-amp-378591)）——強化本站「AMP 退場」定性
- **AI 引用 82–89% 來自 earned media**（Forbes/TechCrunch/WSJ/Reuters）（[Goodie 2026 AI Search Report](https://higoodie.com/blog/ai-search-traffic-report-2026/)）；ChatGPT 62.6% / Claude 18.5% / Gemini 10.6% / Perplexity 7.3%——中型 UGC 平台難進引用池
- **AIO 娛樂垂直滲透 35–40%**（[Semrush AIO Study 2026](https://almcorp.com/blog/semrush-ai-overviews-study-2026-complete-analysis/)、[GrowByData](https://growbydata.com/google-serp-features/)）——壓 organic #1–3 到摺疊下、非引用內容 CTR −15~30%

### Off-Page Authority（B7 首次取得）
- **vocus.cc：Ahrefs DR=76、Semrush AS=65、月流量 8.03M、參考網域 8.1K–17.87K**（[Ahrefs](https://ahrefs.com/websites/vocus.cc)、[Semrush](https://www.semrush.com/website/vocus.cc/overview/)）；Moz DA 已停免費公開查詢
- 判讀：**長期域權威強（DR 76 行業領先）vs 短期 AI/Discover 分發弱（AI 占比 M −61.5%）分離**——S6 Authoritativeness、S7 連結生態 1→4 為錨點修正

### 對本站意涵
- 上週兩風險 [RESOLVED]：Direct 暴衝（歸因雜訊證實，−42.72% 回吐）+ 內連腰斬（口徑波動證實，回 21.2M）
- 新 P0：回應時間反撲 544ms（+67.9%）觸發 Google 自動降速、威脅 Coverage 回填；AMP 崩盤（Article −70.72%）強化退場驗證；AI 雙引擎崩盤加劇（Perplexity −78.0%）

---

## 2026-05-24（快照日期：2026-05-22）

### Google 官方
- [2026-05-21 起] **May 2026 Core Update** — 進行中（rollout 約 2 週，~6/4 完成）。2026 年第二個 core update，業界定調為 **Discover-targeted**，對 news/lifestyle publisher 影響最大。來源：[Google Search Status Dashboard](https://status.search.google.com/incidents/)、[Search Engine Land](https://searchengineland.com/google-may-2026-core-update-rolling-out-now-478430)
- [March 2026 Core Update] 已於 4/8 完成；[March 2026 Spam Update] 3/24–25 完成
- Google Search Central Blog 近 45 天無新 indexing/crawling 公告（僅 5 月 generative AI 優化資源 + 4 月 back-button-hijacking spam policy）

### 業界報導
- 「**Google's index is getting pickier, not broken**」（[Webiano](https://webiano.digital/googles-index-is-getting-pickier-not-broken/)）— core update 期間高價值頁回填、低價值/重複頁被剔除；對應本站 Coverage +15.79% / 檢索未索引 −11.93% 的同步反轉
- **AI referral 版圖重分配**：Gemini（8.65%）超車 Perplexity（7.07%）成 AI referral 第二（[MediaPost](https://www.mediapost.com/publications/article/414030/google-ai-overtakes-perplexity-becomes-no-2-refe.html)）；AI chatbots <1% 出版商 referral、AI answers 60% zero-click（[PPC Land](https://ppc.land/small-publishers-lost-60-of-search-traffic-as-ai-reshapes-the-web/)）
- 2025 出版商傳統搜尋 referral 51.10%→27.42%、Discover 占比近乎翻倍（[SEO Sherpa](https://seosherpa.com/google-web-search-traffic-to-news-publishers-has-collapsed-in-2025/)）

### 對本站意涵
- 本週指標反轉（Coverage 回填 +188k、未索引 −117k、Discover 微反彈 +5.37%）資料窗末端正逢 5/21 core update 啟動——**屬 core update 副產品而非本站修復，rollout 完成前不宣告勝利**
- 本站 Perplexity 跌符合產業，**但 Gemini 背離產業（產業升、本站 W −15.42%）= 本站獨立警訊**

---

## 2026-05-15

### Google 官方
- [2026-05] **Google Search Central Blog**：「A new resource for optimizing for generative AI in Google Search」——官方收編 GEO 策略，民間 GEO 紅利期接近尾聲 ([developers.google.com](https://developers.google.com/search/blog/2026/05/generative-ai-optimization))
- [2026-04-08] March 2026 Core Update 完成，後續 4/23 + 5/8 + 5/13-14 共 3 波 ranking volatility（[Google Search Status Dashboard](https://status.search.google.com/incidents/) — 最新 incident 截至 5/15 為止無新項）

### 業界報導
- [SE Roundtable 5/13-14] **Search Ranking Volatility 第二波確認**：「Google Search Ranking Volatility Heating Up May 13th & 14th」、「a large spike in signs of Google search ranking movement and volatility」([seroundtable.com](https://www.seroundtable.com/google-search-ranking-volatility-heated-41324.html))
- [ALM Corp 5/8] **5/8 spike deserves attention beyond usual chatter**——本期報告 5/15 落點正中第二波視窗（[almcorp.com](https://almcorp.com/blog/google-search-ranking-volatility-may-8/)）
- [Press Gazette 2025-2026 Publisher Trends] **Publisher Discover 流量 -15-21% YoY**——「Global publisher Google traffic dropped by a third in 2025」、「Referrals to 2,500+ publisher websites from Google Discover down 21% YoY」([pressgazette.co.uk](https://pressgazette.co.uk/media-audience-and-business-data/google-traffic-down-2025-trends-report-2026/))
- [PPC Land] **News publishers 兩年內流量減半**：Google Search referral 從 51.10% → 27.42%（[ppc.land](https://ppc.land/news-publishers-lose-half-their-google-search-traffic-in-two-years/)）
- [AI SEO Journal] **Publisher 流量按規模分群**：smaller publishers -60%、medium -47%、large -22%（[aiseojournal.net](https://aiseojournal.net/publishers-report/)）
- [Search Engine Journal] **AIO CTR -61% / cited brands +35%**：「Organic CTR plummeted from 1.76% to 0.61%」（[searchenginejournal.com](https://www.searchenginejournal.com/ai-overview-ctr-fell-61-but-clicks-didnt-collapse/572993/)）
- [Seer Interactive Recovery Report] **AIO CTR leveling-off**：「rebounded from 1.3% (Dec 2025) to 2.4% (Feb 2026)」但警告為 leveling-off 非 recovery（[searcheseverywhere.com](https://www.searcheseverywhere.com/blog/google-ai-overviews-ctr-increase-2026-seo-impact)）
- [Host-Stage TTFB Study] **TTFB > 400ms 每 +100ms → Googlebot 日抓取 -12.4%**（[host-stage.net](https://www.host-stage.net/case-study/ttfb-seo/)）
- [Captain DNS 2026 Crawl Budget] **TTFB 100ms = 10 pages/sec / 500ms = ~2 pages/sec**（[captaindns.com](https://www.captaindns.com/en/blog/crawl-budget-optimization)）

### SER 重點
- [2026-05-15] SE Roundtable 主站 WebFetch 持續 403，但 SE Roundtable 文章透過 WebSearch 仍可取得標題與 URL；建議將 SE Roundtable 完全切換到 WebSearch 取得

---

## 2026-05-01

### Google 官方
- [2026-04-23 ONGOING] **April 23 起新一輪 Search Ranking Volatility 確認 + 5/8 預期續波**：「Just weeks after the March 2026 Core Update officially wrapped up on April 8, tracking tools began flagging elevated ranking movement simultaneously around April 23」（[almcorp.com](https://almcorp.com/blog/google-search-ranking-volatility-april-2026/)）；24% top-10 pages dropped out of top 100、55%+ 監控網站週內排名顯著變動；5/8 volatility spike 預期（[aeoengine.ai](https://aeoengine.ai/blog/search-volatility-guide-stabilize-rankings)）。
- [2026-02 ONGOING-W4] **Feb 2026 Discover Core Update niche reclassification 顯化**：「Niche authorities operating with depth rather than breadth have overtaken brand generalists」、「broad coverage UGC 平台」普遍下跌 30-60%（[coremountainmedia.com](https://www.coremountainmedia.com/insights/google-discover-core-update-2026)、[xeryo.com](https://xeryo.com/en/computing-cloud/google-executes-a-brutal-algorithm-shift-destroying-massive-publisher-traffic-during-the-google-discover-february-2026-core-update/)）。本站 Discover -40% 週崩盤完全吻合此 profile，前週 V 型修正期假設證偽。
- [2026-04] Google Search Central Blog：「Introducing a new spam policy for 'back button hijacking'」、Search Central Live Shanghai 2026 公告。

### 業界研究
- [2026-04-23 NEW] **2026 SEO indexing 框架**：「In 2026, quality gaps are the #1 cause of crawled-currently-not-indexed」、「Google has become far more selective. You must prove that your page adds unique value」（[speedindex.pro](https://speedindex.pro/blog/crawled-currently-not-indexed-the-complete-fix-guide)、[eliteworkhubltd.com](https://eliteworkhubltd.com/google-indexing-issues-in-2026/)）。Information gain + 內部連結強化 + JS 渲染為三大根因 [searchengineland.com](https://searchengineland.com/understanding-resolving-discovered-currently-not-indexed-392659)。
- [2026-05-01 NEW] **Coverage 下降在 volatility 期間的解讀**：「volatility 期間 don't make massive site-wide changes immediately after an update」（[openclaws.blog](https://openclaws.blog/google-search-console-impressions-2026-reality-check/)）。本站 Coverage -14.8% 週需配合「流量頁面」交叉驗證。
- [2026-04 ONGOING-W3] **AI Overviews CTR 持續反轉**：AIO CTR 1.3% Dec 2025 → 2.4% Feb 2026；Cited brands +35% / Non-cited -65%（持續，未新增來源）。

### 本期 Web Research 失敗紀錄
- 2026-04-29 起 Search Engine Roundtable 主站對 WebFetch 返回 403（可能 GPTBot blocking 或我方 IP rate limit）；改用 WebSearch + 多源驗證取代

---

## 2026-04-27

### Google 官方
- [2026-03-27~04-08] **March 2026 Core Update** — 已完成（4/8），但 4 月下旬波動再起，Search volatility 達 9.5/10 為 2026 全年最高（[searchengineland.com](https://searchengineland.com/march-2026-google-core-update-what-changed-474397)）。
- [2026-04 ONGOING] **April 2026 Search Ranking Volatility 反彈**：近 80% top 3 排名變動（vs 12 月 Core Update 後 67%），部分網站單日 30-40% 流量波動，週後部分回補。
- [2026-02-05~] **Feb 2026 Discover Core Update** 後遺效應持續，本站 Discover 月趨勢 -59.2% → -18.9% 大幅改善但週環比 -4.9% 首次轉負（V 型修正期）。

### Google Search Central 公告
- 無新內容（4/27 fetch 顯示與 4/13 相同）：Inside Googlebot / IP Range Files / Search Central Live Shanghai

### 業界報導
- [SearchEngineLand] March 2026 core update more volatile than December — 80% top-3 排名變動（vs Dec 2025 67%）
- [SERoundtable] Google Search Ranking Volatility Heating Up April 23rd — Quasa.io 報導 SEO 報告 30-40% 單日波動
- [ALM Corp] AI Overviews CTR 自 1.3% Dec 2025 反轉至 2.4% Feb 2026（被引用品牌 +35% / 未被引用 -65%）
- [ALM Corp] Google AI Overviews 滲透至 14% shopping queries
- [Optimum7] March 2026 Core Update 對 affiliate domains 影響：71% 域名負面、平均 -54%、「best X under $Y」類為最嚴重 casualties
- [Ahrefs] Update: AI Overviews Reduce Clicks by 58%（最新數據）
- [LinkedIn / Olga Zarr] 「crawled currently not indexed」突發大幅上升常為網站被駭警訊（commerce / 醫療廣告 URLs）

### SERP Feature
- AI Overviews 共現：Related searches 95.32% / People Also Ask 90.03% / Video Carousels 高頻
- Google Ads 出現於底部比例 < 1% (early 2025) → 25% (March 2026)
- Popular Products 元素 +36% YoY（2024 → 2026）
- AIO 在 14% shopping queries 滲透；資訊型 40% 不變

### Google Trends 驗證
- KW 必買 / 攻略 下跌與業界 affiliate / commerce SERP 重整高度吻合（71% domains 負面）
- KW 評價 下跌與 AIO 對 review queries 滲透方向一致

### 服務狀態
- status.search.google.com 正常取得（2 incidents 已 RESOLVED）
- developers.google.com/search/blog 可取得但無 4/27 新內容
- seroundtable.com 403（連續第二次）
- WebSearch 全部成功（5/5 不同 query）

---

## 2026-04-13

### Google 官方
- [2026-03-27~04-08] **March 2026 Core Update** — **已完成**（4/8）。AI 生成內容流量降 71%，原創數據內容升 22%。Information Gain 為核心排名信號。
- [2026-03-24~25] **March 2026 Spam Update** — 已完成，無後續異常。
- [2026-02-05~27] **February 2026 Discover Core Update** — 已完成，殘留效應逐漸消退（Discover 連續兩週正向週環比）。

### Google Search Central 公告
- [2026-04] Search Central Live is Coming to Shanghai
- [2026-03] Inside Googlebot: demystifying crawling, fetching, and the bytes we process
- [2026-03] New Location for the Google Crawlers' IP Range Files
- 無 AMP/CWV/Discover 具體技術變更公告

### 業界報導
- [SearchEngineJournal] Google Confirms March 2026 Core Update Is Complete（4/8）
- [SearchEngineLand] March 2026 Core Update rollout complete
- [linkdoctor.io] March 2026 Core Update: Early Data, Volatility & SEO Impact
- [ALM Corp] Semrush AI Overviews Study 2026: AIO 出現在 30%+ 搜尋，有機點擊降 42%
- [ALM Corp] Schema Markup 2026: Organization schema 提升 Knowledge Panel 3.7x

### SERP Feature
- AI Overviews 覆蓋 30%+ 搜尋（資訊型 40%、商業 25%）
- 98.8% 第一頁含 SERP Feature
- Organization schema 提升 Knowledge Panel 機率 3.7x

### SER 重點
- SER 首頁 403（2026-04-13 存取失敗），連續四次無法取得

---

## 2026-04-05

### Google 官方
- [2026-03-27~進行中] **March 2026 Core Update** — 第 2 週滾動中（預計 ~4/10 完成）。早期數據：AI 生成內容流量降 71%，原創數據內容升 22%。Information Gain 確認為核心排名信號。55%+ 監控網站出現排名波動。
- [2026-03-24~25] **March 2026 Spam Update** — 已完成，無後續異常。
- [2026-02-05~27] **February 2026 Discover Core Update** — 已完成，影響消退。

### Google Search Central 公告
- [2026-03] Inside Googlebot: demystifying crawling, fetching, and the bytes we process
- [2026-03] New Location for the Google Crawlers' IP Range Files
- [2026-04] Search Central Live is Coming to Shanghai

### 業界報導
- [SearchEngineLand] Google AI Overviews cut search clicks 42%
- [SearchEngineLand] News publishers expect search traffic to drop 43% by 2029
- [SearchEngineLand] Small publisher search traffic fell 60% over two years
- [SearchEngineLand] Breaking news traffic grew 103% since Nov 2024
- [TempEmailNow] Google Knowledge Panel 2026: AI-powered verification layer + Ask button

### SERP Feature
- AI Overviews 覆蓋 ~40% 資訊型查詢、~25% 商業查詢
- Knowledge Panel 整合 LLM（Gemini），新增 Ask 按鈕
- CTR 在 AIO 出現時降 42%（全球）；新聞查詢 AIO 覆蓋僅 ~15%

### SER 重點
- SER 首頁 403（2026-04-05 存取失敗），連續兩次無法取得

---

## 2026-03-29

### Google 官方
- [2026-03-27] **March 2026 Core Update** — 部署中（預計 2 週完成）。首次包含 Discover 專屬組件的廣泛核心更新。早期數據顯示部分網站 organic traffic 下降 20-35%。
- [2026-03-24~25] **March 2026 Spam Update** — 已完成。影響 Ranking，可能強化 UGC 品質篩選。

### Google Search Central 公告
- [2026-03] Search Central Live is coming to Canada
- [2026-03] Search Central Live Asia Pacific 2026（Sydney）

### 業界報導
- [9to5Google] Google Search referrals to the web have plummeted, AI links are 'less than 1%' of traffic（2026-03-18）
- [Press Gazette] Global publisher Google traffic dropped by a third in 2025 — Search -34%, Discover -15% YoY
- [Axios] Small publishers hit hardest by search traffic declines（2026-03-17）
- [ALM Corp] Semrush AI Overviews Study: AI Overviews 出現在 ~58% 搜尋中，Featured Snippets 34%→18%
- [ALM Corp] Google Search Ranking Volatility March 2026 — 部分網站 organic traffic -20~35%

### SER 重點
- SER 首頁 403（2026-03-29 存取失敗），無法取得最新報導

---

## 2026-03-22

### Google 官方
- [2026-02-25] Serving 服務故障 — 已修復（15 分鐘）
- [2026-03] **February 2026 Discover Core Update** — 已完成部署。首次 Discover 專屬核心更新，收緊域名池（美國 172→158）。目標：減少 clickbait、優先原創深度報導、增加本地內容。目前僅英語市場，計畫擴展至其他語言。
- [2026-03] **March 2026 Core Update** — 滾動中。與 Feb Discover Update 同步進行。

### Google Search Central 公告
- [2026-03] Search Central Live Asia Pacific 2026（Sydney 等亞太城市）
- [2026-03] Google's February 2026 Discover Core Update 官方說明

### 業界報導
- AI Overviews 觸發 48% 搜尋查詢（2026 數據），有機 CTR 降 61%，Position 1 CTR 年降 32%
- AI Overview 引用 Top-10 頁面佔比從 76% 降至 38%，被引用品牌反獲 +35% 有機點擊
- AI Overviews 在突發新聞中排在 Top Stories 上方（SER 2026-03-20）

### SER 重點
- Google News Showcase Label 在 Discover Feed 測試中
- AI Overviews 在 Breaking News 出現頻率上升且排在 Top Stories 之上

---

## 2026-03-21（快照日期：2026-03-21）

### Google 官方
- [2026-02-05~27] **February 2026 Discover Core Update** — 已完成。67% 網站受影響，clickbait 過濾 + expertise 信號強化 + 在地內容優先。恢復期 2-4 週。
- [2026-03 起] **March 2026 Core Update** — 滾動中。SEMrush Sensor 9.5（歷史高位），排名持續波動。
- [2026-02-25] Serving 服務故障 — 已修復。

### 業界報導
- [almcorp.com] Google Search Ranking Volatility March 2026 — 社群論壇大量報告排名每日變動
- [Brafton] Google Search Updates: Jan-Feb 2026 Recap — 雙核心更新影響整理
- [業界共識] Backlinks 仍是 2026 top-3 ranking factor，但品質遠比數量重要

### SER 重點
- [2026-03-20] Google News Showcase Label In Discover Feed — 測試 Discover 新聞 Showcase 標籤
- [2026-03-20] AI Overviews Showing For Breaking News More Often And Above Top Stories
- [2026-03-19] Universal Commerce Protocol Get New Additions Including Cart & Catalog
- [2026-03-18] Google "Developing" Opt-Out of Generative AI Features in Search — 回應英國 CMA

---

## 2026-05-08（快照日期：2026-05-08）

### Google 官方
- [2026-04 公告] **Back Button Hijacking 反詐騙政策** — 對欺騙性返回鈕劫持行為加強執法（[developers.google.com/search/blog/2026/04/back-button-hijacking](https://developers.google.com/search/blog/2026/04/back-button-hijacking)）
- [2026-03 公告] **Inside Googlebot deep dive** — 詳述 Googlebot 處理檢索/擷取/索引的位元組過程（[developers.google.com/search/blog/2026/03/crawler-blog-post](https://developers.google.com/search/blog/2026/03/crawler-blog-post)）
- [2026-03 公告] **Google Crawlers IP Range Files 新位置** — 更新 IP range 取得管道
- [2026-04-08] March 2026 Core Update Complete（已完成、滾動中波動仍持續至 4/23 起）

### 業界報導
- [almcorp.com] Google Search Ranking Volatility April 2026 — 4/23 起新一輪波動，多個 SERP 工具同步紅色
- [aeoengine.ai] Search Volatility Guide — **5/8 預期續波**，建議 stabilize rankings
- [unrealwebmarketing.com] 2026 Volatility Extended Report — Semrush Sensor / Mozcast 自 1 月持續紅色
- [greatape.digital] 2026 Volatility Crisis — 「significant and ongoing ranking instability」業界共識
- [bigorangeplanet.com] Understanding Volatility 4/25 — 強調「don't make massive site-wide changes immediately after an update」
- [aivisibility.systeme.io] 2026 Survival Guide — 「quality gaps are the #1 cause」of crawled-not-indexed 2026
- [speedindex.pro] 2026 Complete Fix Guide — 「Publishing content alone is no longer enough」

### SER 重點
- [2026-04-29 起] WebFetch 對 SER 主站持續 403——可能為 SER 端封鎖 GPTBot 或 fetch 工具 IP，改用 WebSearch + 多源驗證
