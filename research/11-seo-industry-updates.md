# SEO 業界動態追蹤

> 由 `/meeting-prep` 自動累積，每次執行 append 一個日期 section。
> 保留最近 12 次記錄（約 6 個月），超過自動移除最舊 section。

---

<!-- 以下為自動累積區域，請勿手動編輯格式 -->

## 2026-07-24（快照日期：2026-07-27，source: meeting_prep_20260724）

### Google 官方
- [2026-07-18~19] **未確認演算法震盪** — 14 個獨立 SERP 追蹤工具偵測到顯著位移（週六起、週日加重）；**Google Search Status Dashboard 全清、截至 7/21 未確認任何事項**。Search Engine Land 引述：四分之一前十名頁面跌出百名外、80% 前三名易主；中間商與薄聯盟型內容失血最重（[Digital Applied](https://www.digitalapplied.com/blog/google-weekend-algorithm-update-july-2026-volatility-triage)、[Joseph Charnin](https://www.josephcharnin.com/seo/unconfirmed-july-2026-google-ranking-volatility/)）
- [2026-07-11] 另有「7-Eleven update」未確認震盪（[SER](https://www.seroundtable.com/google-search-ranking-volatility-july-11th-41676.html)）
- [2026-06-24~26] June 2026 Spam Update — 仍為 Status Dashboard 45 天窗內**唯一**確認 incident
- **框架修正（重要）**：連續三週使用的「Dashboard 查無 incident 即非演算法驅動」判讀**本週被推翻**——官方無記錄 ≠ 無事件發生。未來週度診斷須把第三方 SERP 波動追蹤納入固定輸入

### Google Search Central 公告
- [2026-07] See how content from social and video platforms performs on Google Search（新報表）
- [2026-07] Search Central Deep Dive Europe 2026: Barcelona
- [2026-06] Introducing Search Generative AI performance reports in Search Console（連續第 5 週可用、本站連續第 5 週未導入）

### 結構化資料 / Rich Results
- **Review snippet 資格收緊**：self-serving 評論（被評論實體 A 把評論放在 A 自己網站，含嵌入第三方 widget）不再具備資格，`LocalBusiness` / `Organization` 及子型別不再顯示評論 rich result；未揭露或有償評論同樣不具資格（[Google 官方文件](https://developers.google.com/search/docs/appearance/structured-data/review-snippet)、[SEOteric](https://www.seoteric.com/google-cracks-down-on-fake-and-undisclosed-incentivized-reviews-in-review-snippet-markup/)）
- **FAQ rich results 全面退場**：2026/5/7 正式淘汰，Search Console 報表與 Rich Results Test 支援 6 月終止、API 8 月終止；`FAQPage` schema 型別本身仍有效（[inblog](https://inblog.ai/blog/google-faq-schema-rich-result-deprecation)）

### GSC 資料口徑（桌機曝光偏斜，對應本站桌機 −20.94%）
- **`num=100` 移除的長尾效應**：2025/9 Google 停止支援 `num=100`，此前排名工具一次拉 100 筆、第 99 名也計一次曝光；參數關閉後 bot 曝光自報表消失。LOCOMOTIVE 分析 319 個 property：**87.7% 網站損失曝光、77.6% 損失獨立排名詞**，短尾中尾受創最深（[Search Engine Land](https://searchengineland.com/google-num100-impact-data-462231)、[LOCOMOTIVE](https://locomotive.agency/blog/google-removes-num100-parameter-what-this-means-for-your-website/)）
- **GSC 記錄錯誤修正**：Google 確認自 2025/5/13 起的記錄錯誤造成曝光灌水，修正 2026/4/27 上線（僅對新資料、不回溯）；**「曝光下修主要影響桌機，行動受創小得多」**（[Vizup](https://www.tryvizup.com/blog/google-search-console-impressions-drop-2026-what-the-gsc-bug)）
- **時間點缺陷須標註**：兩者皆早於 2026/7，可解釋「桌機曝光長期承壓」的背景，**無法解釋單週跳變**

### Discover / AIO
- **Discover 跨投資組合成長 30%**，已成突發新聞分發主要成長引擎；資料集中**首次出現 Discover 與網頁搜尋導流量大致相當**（[Memeburn](https://memeburn.com/google-search-traffic-shifts-again-as-ai-overviews-expand-across-results/)）——本站 +34.60% 僅略高於市場，屬 beta 非 alpha
- AIO 覆蓋約 **48–50%** 美國查詢（2025/1 僅 6.49%，15 個月近 8 倍擴張），使搜尋點擊減少 42%（[Search Engine Land](https://searchengineland.com/google-ai-overviews-cut-search-clicks-report-471497)、[Omnibound](https://www.omnibound.ai/blog/google-ai-overviews-statistics)）

### Google Trends / SERP Feature
- **B5 本週失敗**：WebSearch 未取得台灣區 2026/7 娛樂關鍵字量化搜尋量，僅回傳 Trends 工具教學頁。改以「同品類內部對照法」降級推導（劇 −32.38% vs 評價 −3.12% → 偏本站問題），證據等級低於前幾週

### Off-Page Authority（B7 carry forward 2026-07-06，距今 21 天 ≤30）
- 沿用 DR **77** / AS **64**；Majestic TF/CF **連續第 4 次未取得**，連結品質錨點續缺

### SER 重點
- WebFetch 對 seroundtable.com 主站續 403（bot detection），B2 降級改由 WebSearch 取得同源報導

## 2026-07-10（快照日期：2026-07-10）

### Google 官方
- [本週] **Status Dashboard 查無新 incident** — 最近 30 天僅 June 2026 Spam Update（6/24–26 完成），本週（7/4–7/10）無新 ranking/indexing 事件。**本週異常皆「非演算法驅動」**：索引 refresh=data lag 解除、爬蟲量崩=基礎設施、Organic 月線深化=AIO 產業趨勢（[Status Dashboard](https://status.search.google.com/incidents.json)）
- [2026-01] **2026 crawl 政策揭露** — HTML 檢索上限 15MB→2MB；Gary Illyes「基礎設施速度比站台規模更決定 crawl rate；站台變慢/回錯誤→crawl rate 降；內容看似低值→crawl demand 自動降」（[Google Developers](https://developers.google.com/crawling/docs/crawl-budget)、[Stan Ventures](https://www.stanventures.com/news/decrease-in-google-crawl-rate-why-it-happens-how-to-fix-it-4067/)）——直擊本站回應時間 374ms + 爬蟲量 −11.22%
- [2026-07] **GSC 社群/影片平台成效報告上線** + 生成式 AI 效能報告（連第 4 週可用）（[Search Central Blog](https://developers.google.com/search/blog)）——量化影片外觀 vs 帶量背離、AI 引用率的官方工具，本站連 4 週未導入

### 業界報導
- **Digital Content Next：會員出版商 5→6 月整體搜尋流量再降 10%**、AIO 觸發查詢 CTR 崩 61%、AIO 出現在約 30% 查詢（[Search Engine Land](https://searchengineland.com/organic-search-is-fundamentally-disrupted-heres-what-to-do-about-it-470816)）；本站 Organic 月線深化 −14.53% 屬同一趨勢
- **Google 對出版商導流年減 22%**、AIO「引用更少更權威的一組來源」（[Medium/Alan Ronis](https://medium.com/@alanronis/google-is-sending-22-less-traffic-to-publishers-than-a-year-ago-what-should-you-do-a1a12de297f9)）——本站 DR 77 本應是被引用候選卻 AI 崩，坐實「有連結權威缺品牌提及」脫鉤
- **搜尋進入「有序衰退」而非崩盤**，對策是分散來源而非追曝光（[Press Gazette](https://pressgazette.co.uk/publishers/search-isnt-dead-its-fragmenting-how-to-manage-google-traffic-decline/)）——呼應本站工作階段月線首次翻負、須經營站外多元入口
- **AIO 出現時 top 有機點擊再降約 58%**、只有 1.16% 首頁結果無 SERP feature（[Digital Applied](https://www.digitalapplied.com/blog/google-ai-overviews-surge-58-percent-queries-seo-impact)、[Ahrefs CTR 2026](https://ahrefs.com/blog/what-is-a-good-ctr/)）——電影/影評類資訊查詢是重災區，KW 影評 −44.98% 部分來自 SERP 排擠

### 關鍵字市場趨勢（B5/B6）
- **KW 影評 −44.98%/電影月線 −80.75%**：院線空窗 + AIO/影音排擠雙重因素，市場面為主但本站權重不可歸零（KW 劇月線 +30.62% 證娛樂需求未整體熄火），需人工複查 Google Trends TW
- **KW 股 +81.55% 三度翻臉**（+90→−56→+81）：辛普森脈衝雜訊坐實、不追加資源

### 對本站意涵
- 索引清理紅利（檢索未索引 −39.53%）vs 爬蟲量崩跌（−11.22%）正面對撞——清理靠爬蟲回填、爬蟲量崩威脅紅利，官方 crawl 政策從外部佐證因果
- 本週非演算法月份，更該把診斷聚焦本站可控（回應時間、內連、結構化）而非等外部演算法
- 拿到索引清理大勝卻因執行債（告警未落地、內連惡化）升不動技術體質——Process 天花板新形式

---

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

---

## 2026-06-19（快照日期：2026-06-22，source: meeting_prep_20260619）

### Google 官方
- [May 2026 Core Update] 已 6/2 完成（5/21→6/2，12 天），但後續波動延續——[seroundtable.com](https://www.seroundtable.com/google-search-ranking-volatility-41523.html) 6/15–17 連三天排名波動、6/19 又有不明更新（主打黑帽側，[seroundtable.com](https://www.seroundtable.com/google-search-ranking-hits-black-hats-41541.html)）。本週資料窗（6/13–6/19）坐落核心更新後「重新評估期」
- [GSC 生成式 AI 效能報告上線] Search Console 新增追蹤內容被 AI Overview 引用的曝光/點擊（developers.google.com/search/blog）
- [GEO 官方指南] [SEJ: Google's New AI Search Guide Calls AEO And GEO 'Still SEO'](https://www.searchenginejournal.com/googles-new-ai-search-guide-calls-aeo-and-geo-still-seo/575026/)——AEO/GEO 不是獨立學科、是傳統 SEO 延伸，強化 E-E-A-T 即可同時得益
- [6/15 llms.txt 澄清] Google 不需 llms.txt 來索引（加它屬選配非 SEO 必要）

### 業界報導
- **[關鍵] [SEL: What new AI search data reveals about visibility and trust](https://searchengineland.com/new-ai-search-data-visibility-trust-480089)**——75,000 品牌跨 ChatGPT/AI Mode/AI Overviews 分析：**AI 引用與品牌曝光度（YouTube、網路提及）相關性最高 r=0.50–0.74、與反鏈數量最低 <0.30**。直接解釋本站 DR 76 強卻 AI 弱的脫鉤
- [SEL: AI search adoption rises as consumer trust declines](https://searchengineland.com/ai-search-adoption-rises-consumer-trust-declines-study-480338)——AI 搜尋信任度 2025 年 82% → 2026 年 54%（-28pp），用戶平均跨 2.4 平台驗證、referral 碎片化
- [SEJ: Gemini Sends More Traffic Than Perplexity](https://www.searchenginejournal.com/google-gemini-sends-more-traffic-to-sites-than-perplexity-report/570714/)——Gemini Nov–Jan +115% 超越 Perplexity；整體 AI referral 仍 <1% 總流量。**Perplexity 下滑是業界普遍現象（非單站個案）、ChatGPT 仍佔 AI referral ~80%**
- [SEJ: Google Updates Product Structured Data Documentation](https://www.searchenginejournal.com/google-updates-product-structured-data-documentation/484813/)——Google 拆 Product 文件為 product snippet（非購買頁/評論聚合）vs merchant listing（可購買頁）；屬性重判會在 GSC 兩報告間移轉計數

### SER 重點
- [2026-06] SERoundTable June Webmaster Report：May Core Update 完成 + Google I/O AI 搜尋功能 + HTML vs Markdown（Google 明示 HTML 是 Search 標準格式）
- WebFetch 對 SER/SEL 主站仍易 403——改用 WebSearch + 多源交叉驗證（延續 4/29 起策略）

---

## 2026-06-26（快照日期：2026-06-29，source: meeting_prep_20260626）

### Google 官方
- [June 2026 Spam Update] **6/24 16:00 UTC → 6/26 17:00 UTC 完成**（約 48 小時、提前收尾），全語言/全地區、SpamBrain AI 主導。**明確不針對連結垃圾與 Site Reputation Abuse、針對其他內容操縱手法**（[Google Search Status Dashboard](https://status.search.google.com/products/rGHU1u87FJnkP6W2GwMi/history)、[seroundtable.com](https://www.seroundtable.com/google-june-2026-spam-update-out-41568.html)）。三波更新疊加：May Core Update（6/2）→ 不明更新（6/19）→ June Spam Update（6/24–26）
- [GSC 生成式 AI 效能報告正式開放] [developers.google.com/search/blog/2026/06/gen-ai-performance-reports](https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports)——可追蹤內容在 Gemini/AI Overview 的曝光與點擊，建 AI 引用率 baseline
- [GEO 官方優化指南] [developers.google.com/search/blog/2026/05/a-new-resource-for-optimizing](https://developers.google.com/search/blog/2026/05/a-new-resource-for-optimizing)——結構化內容 + E-E-A-T + 清晰 facts 標記為被 AIO 引用的基礎

### 業界報導
- **AIO 桌機 CTR 壓縮已結構化**：2026 年 AIO 出現於 48% 查詢（YoY +58%），首位有機 CTR −58%（Ahrefs 300K KW）、AIO 查詢 CTR 系統性落後非 AIO 約 37%；被 AIO 引用頁多獲 +120% 點擊曝光比（[ALM Corp](https://almcorp.com/blog/google-ai-overviews-organic-ctr-2026/)、[Infinite Labs](https://infinitelabsdigital.com/google-ai-overviews-are-eating-your-organic-traffic-heres-how-to-fight-back/)）
- **桌機 vs 行動分裂屬全球趨勢**：全球出版商搜尋流量年降 1/3（美國 −38%），桌機持續失血、行動因短影音/卡片維持（[Digital Strategy Force](https://digitalstrategyforce.com/journal/why-did-organic-traffic-drop-in-q1-2026/)）
- **Perplexity 業界普遍下滑但 vocus 惡化更深**：Perplexity AI 引流市佔 7.3%、perplexity.ai 流量月降 10.82%（Similarweb May）；vocus −87.81% 遠超市場（[Goodie](https://higoodie.com/blog/ai-search-traffic-report-2026/)）。Perplexity Publisher Program 80/20 分潤、2,400+ 出版商加入後 referral +34%（[Digital Strategy Force](https://digitalstrategyforce.com/journal/perplexitys-2026-publisher-program-what-it-means-for-content-creators/)）
- **內部連結 2026 最佳實踐**：Pillar-Cluster 雙向架構、每頁 12–25 contextual links（vocus 11.86 近下限）；Cluster 比孤立文章多 30% 有機流量、排名穩定 2.5 倍；**2026 AI 引擎（Perplexity/Gemini/SGE）同樣依賴內連理解站點結構**（[Digital Applied](https://www.digitalapplied.com/blog/internal-linking-strategy-2026-large-site-architecture-guide)、[Topical Map AI](https://topicalmap.ai/blog/auto/internal-linking-strategy-guide-2026)）

### Google Trends / 院線檔期
- 影評/電影 WoW 下滑屬院線空窗期：6/17 玩具總動員 5 首映衝頂 → 6/20–26 空窗 → 6/30 小小兵；月線仍 +58~68% 確認需求健康；7 月諾蘭《奧德賽》+ 蜘蛛人下波高峰將至（[2026 暑假片單](https://blog.enjoymovie.net/summer-2026-blockbuster-movies-preview/)）

### SER 重點
- WebFetch 對 SER 主站仍 403（bot detection），本週 B1–B6 全程改用 WebSearch + Google Status Dashboard JSON 多源交叉驗證

---

## 2026-07-03（快照日期：2026-07-06，source: meeting_prep_20260703）

### Google 官方
- [GSC Page Indexing Report 官方延遲 2–3 週] John Mueller 證實 Page Indexing report 延遲近三週且無 ETA（[seroundtable.com](https://www.seroundtable.com/google-search-console-page-indexing-report-delayed-41571.html)）——**把本站索引面 weekly 全 0.00% 的 data lag 從「本站推論」升級為「Google 官方確認的全平台報表延遲」**；索引三鏈續延用讀數、WoW 判讀留白
- [June 2026 Spam Update 已收尾（6/26）] status.search.google.com/incidents.json 確認 6/6 之後查無其他 incident——本資料窗（6/27–7/3）完整落在 Spam Update 完成後的「紅利/回吐確認窗」；本站未見排名崩跌（ALERT_DOWN 多屬流量分發層），Spam Update 對 vocus UGC 衝擊初步確認有限
- [SER July Webmaster Report] 月度彙整重點：spam update 兩天內完成、Google 談 chunking / site signals / paywalls / AI clicks（[seroundtable.com](https://www.seroundtable.com/july-2026-google-webmaster-report-41591.html)）

### 業界報導
- **AIO 使有機 CTR 崩 61%（1.76%→0.61%）**（[Search Engine Land](https://searchengineland.com/google-ai-overviews-drive-drop-organic-paid-ctr-464212)）——本站本週 CTR 逆勢 +9.88% 與業界普遍崩跌方向相反，反證本站 CTR 上升屬曝光收縮的分母萎縮統計濃縮、非優化見效
- **Organic search 產業級結構性收縮**：AIO 致資訊類站點有機流量 −15~64%、News 出版商月減 33–38%（[Search Engine Land](https://searchengineland.com/organic-search-is-fundamentally-disrupted-heres-what-to-do-about-it-470816)）；Google 對出版商整體導流年減 22%（[Medium/Alan Ronis](https://medium.com/@alanronis/google-is-sending-22-less-traffic-to-publishers-than-a-year-ago-what-should-you-do-a1a12de297f9)）——本站 Organic Search 月線首次翻負 −9.77% 屬同一趨勢
- **Discover 數據 5/21 起平台異常**：出版商回報 Discover 數據記錄斷崖、可信度存疑（[PPC Land](https://ppc.land/googles-discover-data-went-dark-on-may-21-what-publishers-need-to-know/)）——本站 Discover −29.36% 崩跌須先排除平台數據面因素，但探索比例 −19.06% + Google 導流 −12.44% 同步走弱顯示部分為真實回落
- **回應時間 crawl budget 外部標準**：GSC 平均回應時間應 ~100ms、上限 1,000ms，超過壓縮 crawl budget（[Matthew Edgar: Crawl Stats](https://www.matthewedgar.net/blog/crawl-stats-average-response-time/)）——支撐本站 285→366ms 反彈 + 爬蟲量 −4.01% 的因果

### Google Trends / SERP Feature
- KW 股 −56.34% 對應台股 6 月下旬–7 月初量縮（7/3 五日均量降至 1.15 兆、交投清淡）——偏外部因素、坐實上週辛普森脈衝判讀
- 電影類 AIO rollout 已涵蓋（2026/04 起 Gemini 3 為預設模型、YouTube 為最大被引用網域 10.74%）（[SE Ranking](https://seranking.com/blog/ai-overviews/)）

### Off-Page Authority（B7 refresh 2026-07-06，距上次 34 天）
- Ahrefs DR **77**（76→77 +1）、參考網域 11,000（月增 718）；Semrush AS **64**（65→64 −1）——長期域權威持平於行業領先
- Semrush 月流量 **5.89M**（5 月資料、4→5 月 MoM **−22%**）——外部第三方獨立驗證流量收縮，與本站曝光 −15.05%、Organic Search 月線 −9.77% 方向一致；Moz DA 仍停免費查詢、Majestic TF/CF 未取得

### SER 重點
- WebFetch 對 SER/SEL 主站仍 403（bot detection），本週 B1–B7 全程改用 WebSearch + Google Status Dashboard JSON 多源交叉驗證
