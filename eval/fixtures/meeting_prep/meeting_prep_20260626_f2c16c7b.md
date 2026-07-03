# SEO 顧問會議準備 — 2026/06/26（週期 6/20–6/26）

> 輸入來源：`output/report_20260626_a283e3fd.md`（本週週報）
> 對比基準：前次 meeting-prep `meeting_prep_20260619_a6ee9934.md`（6/19）
> 框架：5-Layer Audit + E-E-A-T + 人本七要素 + SEO 成熟度
> **報告銜接**：上一份 meeting-prep 截至 6/19，本份直接以其為「上週」基準，沿用其 6 大訊號軌跡。
> **本週最大內部變數：上週點名的兩個結構債——「內部連結基礎」與「CTR」——本週雙雙惡化（內連月線 −26.12%→−27.30%、CTR 從上週 +2.85% 翻紅回吐到 −7.62%），是 Health Score 連六週回升告終、回落 2 分的直接主因。**
> **本週最大外部變數：June 2026 Spam Update（6/24–6/26 完成）收尾三波更新疊加（May Core Update 6/2 → 不明更新 6/19 → June Spam Update 6/24–26）——本份資料窗（6/20–6/26）完整坐落於三波更新交疊期。**

---

## Section 0：執行摘要

- **連六週回升告終、本週為消化整理週（非趨勢反轉）**：Health Score 53→**51**（週線 −2）。但月線結構完全未破（工作階段 +18.03%、曝光 +9.31%、手機好桶 +47.18%、Discover +28.10% 全守正）——WoW 回吐是上週暴衝後的均值回歸 + 索引面因 GSC data lag 不計分的機械扣分，而非新風險爆發 [1][22]。
- **上週點名兩結構債雙雙惡化、是本週回落的直接主因**：內部連結月線 −26.12%→**−27.30%**（每頁內連卡 11.86），CTR 從上週 +2.85% 翻紅回吐到 **−7.62%**（曝光校正缺口 9.9 萬點擊）——兩個「能主動創高」的槓桿上週點名卻未動工，需求端（討論區 +18.07%、/tags/ 月線 +51.71%、曝光淨增 355 萬）走強時不補，等於需求進來卻被入口稀薄與標題失效漏接 [2][3][7]。
- **June Spam Update（6/24–26）收尾三波更新疊加、不針對連結但針對內容操縱**：6/2 May Core Update → 6/19 不明更新 → 6/24–26 June Spam Update 三連擊，時序與 vocus 6 月下旬異常高度重疊。Spam Update 由 SpamBrain 主導、48 小時提前完成、**明確不針對連結垃圾與 Site Reputation Abuse**，目標是其他操縱排名手法——vocus 作為 UGC 平台須優先確認內容品質端是否觸及審視 [14]。
- **桌機 CTR −9.23% vs 行動 +2.85% 分裂＝AIO 桌機壓縮的全球結構性問題、非個案**：2026 年 AIO 出現在 48% 查詢、首位有機 CTR 被壓 58%，桌機螢幕更完整顯示 AIO + Video Carousel 故損失更多點擊；影評/電影屬「問答+比較型」查詢（AIO 觸發率 85–95%）正是重災區。對策是爭取被 AIO 引用（GSC 新上線的 GenAI 效能報告可追蹤引用率）[10][14]。
- **平台集中度浮現為新跨週風險維度**：Direct 占比 40.6% + Organic Search 50.2% ＝ 逾 90% 集中於「Google 生態 + 自有品牌直接訪問」，而站外三入口（Organic Social 月線 −21.19% / Referral 月線 −29.90% / AI 引用 Perplexity 月線 −87.81%）同步月線級失血＝品牌站外訊號收縮。關鍵結構限制：vocus.cc 因 `.cc` TLD 無法提交 sitemap 至 GSC，爬取發現高度依賴內部連結——這讓內連月線崩 27% 的傷害被放大 [4][16]。

---

## Section 1：本週異常地圖

### ALERT_DOWN（按嚴重度排序）

| 指標 | 週線 | 月線 | latest | 判讀 |
|------|-----:|-----:|-------:|------|
| AMP Article | **−75.19%** | −195.79% | 33 | AMP 版位續萎縮（CWV 時代自然退場）🟡 |
| 產品摘要 | +1.82% | **−48.11%** | 224 | Product/Offer 結構化月線腰斬（疑重分類）🟡 |
| 內部連結（月線結構） | 0.00%[data lag] | **−27.30%** | 16,960,024 | 每頁內連 11.86、策展入口基礎續弱 🔴 |
| KW 電影 | −28.65% | +58.32% | 1,066 | 院線空窗期 WoW 回吐（月線仍強）🟢 |
| News(new) | −26.95% | −107.88% | 664 | 院線/時事檔期退潮（暴起暴落）🟡 |
| Perplexity（工作階段） | −19.02% | **−87.81%** | 149 | 引用型 AI 月線續崩 🔴 |
| KW 影評 | −18.66% | +67.83% | 1,007 | 院線空窗期 WoW 回吐（月線仍強）🟢 |
| Video（流量來源） | −12.91% | −15.46% | 1,181 | 影片外觀暴增 vs 帶量走弱背離 🟡 |
| 桌機點擊（推算） | **−9.23%** | — | 372,946 | 桌機 SERP 行為端弱化（行動 +2.85% 健康）🔴 |
| Referral（工作階段） | −8.28% | −29.90% | 54,795 | 站外引薦入口月線級失血 🟡 |
| CTR | **−7.62%** | −7.16% | 2.22% | 稀釋漏點重開、上週翻紅回吐 🔴 |
| Organic Search（工作階段） | −4.82% | +2.33% | 1,340,319 | 大盤週縮（月線仍正）🟡 |
| Organic Social（工作階段） | −4.66% | −21.19% | 74,805 | 社群轉介月線級失血 🟡 |
| 工作階段總數（七天） | −3.58% | +18.03% | 2,672,417 | 六週首見大盤週縮（月線守正）🟡 |
| 點擊 | −1.20% | +2.10% | 1,211,505 | 上週創高動能回吐 🟡 |
| Gemini（工作階段） | +2.01% | −63.96% | 152 | 引用型 AI 月線深跌（WoW 微升）🟡 |

### ALERT_UP（正向訊號 / 需釐清）

| 指標 | 週線 | 月線 | latest | 判讀 |
|------|-----:|-----:|-------:|------|
| 週平均回應時間 | **−16.18%** | −76.12% | 285ms（←694←340） | **P0 持續解除、累計 −59%、深入健康區** 🟢 |
| Video Appearance | +37.23% | +191.17% | 3,948 | 影片外觀版位創波段新高 🟢 |
| 討論區 | +18.07% | +21.29% | 15,790 | 策展型版位週月雙強 🟢 |
| 曝光 | +6.96% | +9.31% | 54,604,058 | 重啟攀升、逼近波段 max 83.5% 🟢 |
| Discover | +6.40% | +28.10% | 442,430 | 分發端重啟攀升（月線連兩月 +28%）🟢 |
| 站內搜尋框（PageRefer searchbox） | +7.38% | +34.02% | 343,827 | 站內探索意圖入口走強 🟢 |
| 行動裝置點擊 | +2.85% | +6.27% | 838,559 | 行動端 CTR 實質改善 🟢 |
| GPT（工作階段） | +2.20% | +11.27% | 1,901 | 對話型 AI 連三週領頭回穩 🟢 |
| /tags/（月線） | +1.82% | +51.71% | 17,774 | 策展頁需求月線續飆 🟢 |
| 週平均檢索數 | +1.20% | +3.01% | 853,579 | 爬蟲量連兩週增、月線翻正 🟢 |
| 評論摘錄 | +5.30% | −6.08% | 29,699 | Review schema WoW 回補、月線收斂 🟢 |
| 手機 好（CWV） | −1.98% | +47.18% | 815,479 | CWV「好」桶月線守住（坐實非雜訊）🟢 |
| Direct（工作階段） | +3.22% | +38.86% | 1,085,099 | 占比升至 40.6%（平台集中度風險）🟢⚠️ |

### 跨週對比（6/19 vs 6/26）

| 軸 | 6/19（上次 MP） | 6/26（本次） | 變化 |
|----|----------------|--------------|------|
| Health Score | 53（連五週新高） | **51（連六週回升告終）** | **−2，消化整理週** |
| 週平均回應時間 | 340ms（−20.56%） | **285ms（−16.18%）** | **續降、累計 −59%、P0 持續解除** |
| CTR | 2.40%（W +2.85% 翻紅） | **2.22%（W −7.62% 回吐）** | **翻紅僅維持一週、稀釋漏點重開** |
| 點擊 | 1,226,192（+2.76%） | 1,211,505（−1.20%） | **創高動能回吐** |
| 內部連結（每頁/月線） | 11.86 / M −26.12% | 11.86 / M **−27.30%** | **供需背離加深** |
| Perplexity / Gemini | 184 / 149（M −216% / −135%） | 149 / 152（M −87.81% / −63.96%） | **WoW 跌幅收斂、月線仍深崩** |
| Organic Social / Referral（月線） | −3.35% / −26.56% | **−21.19% / −29.90%** | **站外入口月線級失血加劇** |
| AMP Article / 產品摘要（月線） | −142.64% / −34.35% | −195.79% / **−48.11%** | **版位 + 結構化雙雙惡化** |
| GSC 索引面 | 可讀（Coverage +6.83%） | **data lag、讀不到（latest 卡 6/16）** | **本週索引三鏈留白、延用上週讀數** |
| Google 更新 | Core 完成 + 6/15–19 波動 | **June Spam Update（6/24–26）完成** | **三波更新疊加期** |
| B7 Authority | DR 76 / AS 65（CF 6/2，20 天） | DR 76 / AS 65（CF 6/2，27 天） | **沿用（≤30 天）** |

---

## Section 2：業界最新動態

### Google 官方更新

**[NEW] June 2026 Spam Update（6/24–6/26 完成）**

- [Google Search Status Dashboard: June 2026 Spam Update](https://status.search.google.com/products/rGHU1u87FJnkP6W2GwMi/history) — 官方確認 6/24 16:00 UTC 啟動、6/26 17:00 UTC 完成，僅約 48 小時（原估數天），全語言/全地區，SpamBrain AI 系統主導偵測。
- [Search Engine Roundtable: Google June 2026 Spam Update Is Rolling Out](https://www.seroundtable.com/google-june-2026-spam-update-out-41568.html) — **明確說明此次不針對連結垃圾與 Site Reputation Abuse 政策**，目標是其他操縱排名手法。
- **對本站意涵**：vocus 作為 UGC 平台，Spam Update 既不針對連結（vocus DR 76 連結權威健康）也不針對 SRA，但「其他內容操縱」的審視須確認站上是否有低品質 UGC 觸及。本週 ALERT_DOWN 多屬流量/分發層（CTR、站外、檔期），未見排名崩跌，初步研判 Spam Update 對 vocus 衝擊有限，但須在 6/30 後確認紅利不回吐 [14]。

<details>
<summary>[RESOLVED] May 2026 Core Update（6/2 完成）後續波動已收斂——一句帶過</summary>

- May Core Update（6/2 完成）後的 6/15–17 + 6/19 不明更新波動，本週已被 June Spam Update 取代為主要外部變數；上週的「重新評估期」判讀本週不再是主軸。
</details>

**[NEW] GSC 生成式 AI 效能報告正式開放 + GEO 官方優化指南**

- [Google Search Central: Introducing Search Generative AI performance reports in Search Console](https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports) — GSC 新增 AI 生成式搜尋成效報告，可追蹤內容在 Gemini / AI Overview 中的曝光與點擊。**本站應立即開啟、建立 AI 引用率 baseline，量化 AIO 引用是否彌補桌機 CTR 流失**。
- [Google Search Central: A new resource for optimizing for generative AI](https://developers.google.com/search/blog/2026/05/a-new-resource-for-optimizing) — 官方 AI 搜尋優化指南上線，建議結構化內容、E-E-A-T 強化、清晰 facts 標記作為被 AIO 引用的基礎工程。

### 業界報導

**[NEW] AIO 造成的有機 CTR 壓縮已是結構性問題、桌機重於行動**

- [ALM Corp: Google AI Overviews and Organic CTR in 2026](https://almcorp.com/blog/google-ai-overviews-organic-ctr-2026/) — Seer Interactive 追蹤顯示 AIO 出現查詢的 CTR 系統性落後非 AIO 查詢約 37%；Ahrefs 300K 關鍵字分析：AIO 存在時首位有機 CTR 下滑 **58%**。
- [Infinite Labs: AI Overviews Are Eating Your Organic Traffic](https://infinitelabsdigital.com/google-ai-overviews-are-eating-your-organic-traffic-heres-how-to-fight-back/) — 2026 年 48% 查詢顯示 AIO（YoY +58%）、SERP feature 占 60–80% 可視面積；**被 AIO 引用的頁面比未引用者多獲 120% 點擊/曝光比**。
- [Digital Strategy Force: Why Did Organic Traffic Drop in Q1 2026?](https://digitalstrategyforce.com/journal/why-did-organic-traffic-drop-in-q1-2026/) — 全球出版商搜尋流量一年下滑三分之一（美國達 −38%），桌機持續失血、行動端因短影音/卡片格式維持表現——直接呼應 vocus 桌機 −9.23% vs 行動 +2.85% 的分裂屬全球趨勢、非個案。

**[ONGOING-W2] 引用型 AI 導流崩、Perplexity 業界普遍下滑但 vocus 惡化更深**

<details>
<summary>[ONGOING-W2] 引用型 AI 業界數據（點擊展開本週新發展）</summary>

- [Goodie: 2026 AI Search Traffic Report](https://higoodie.com/blog/ai-search-traffic-report-2026/) — Perplexity AI 引流市佔 7.3%（2026 Q1），Similarweb May 2026 顯示 perplexity.ai 流量 **月降 10.82%**；AI chatbot 整體 referral 比傳統搜尋少 95–96%。
- **本週新發展**：vocus Perplexity 月線 **−87.81%** 遠超全市場 −10.82%——非單純跟隨業界，須調查是否有特定頁面被 Perplexity 停止引用（疑與內容新鮮度或結構化標記缺失有關）。
- [Digital Strategy Force: Perplexity's 2026 Publisher Program](https://digitalstrategyforce.com/journal/perplexitys-2026-publisher-program-what-it-means-for-content-creators/) — Perplexity 出版商計畫（80/20 分潤），2,400+ 出版商加入後 referral 平均 +34%；vocus 值得評估入選資格 [12][13]。
</details>

**[NEW] 內部連結 2026 最佳實踐：Pillar-Cluster 雙向架構 + AI 引擎同樣依賴內連**

- [Digital Applied: Internal Linking Strategy 2026](https://www.digitalapplied.com/blog/internal-linking-strategy-2026-large-site-architecture-guide) — 大型站點建議每頁 12–25 個 contextual links、重要頁面 3 次點擊內可達；vocus 每頁 11.86 已接近下限。
- [Topical Map AI: Internal Linking Strategy Guide 2026](https://topicalmap.ai/blog/auto/internal-linking-strategy-guide-2026) — Cluster 架構比孤立文章多 30% 有機流量、排名穩定性 2.5 倍；**2026 年 AI 搜尋引擎（Perplexity/Gemini/SGE）同樣依賴內部連結理解站點主題結構**——內連流失會間接加速 AI 引用下滑的惡性循環 [2]。

### 關鍵字市場趨勢（Google Trends 驗證）

| 關鍵字 | 本站趨勢 | 市場趨勢 | 判斷 | 來源 |
|--------|---------|---------|------|------|
| KW 電影 | W −28.65% / M +58.32% | 6/17 玩具總動員 5 首映衝頂 → 6/20–26 空窗 → 6/30 小小兵 | **院線空窗期週期回落、非市場崩潰；月線坐實需求健康** | [2026 暑假大片片單](https://blog.enjoymovie.net/summer-2026-blockbuster-movies-preview/) |
| KW 影評 | W −18.66% / M +67.83% | 同上，spike-and-dip 固有週期 | **檔期空窗、非演算法；7 月諾蘭《奧德賽》+ 蜘蛛人下波高峰將至** | [開眼近期上映](https://www.atmovies.com.tw/movie/next/) |

### SERP Feature 偵測

| 關鍵字 | 觀察到的 SERP Feature | 對有機 CTR 的影響 | 來源 |
|--------|---------------------|-----------------|------|
| 影評/電影 | AIO（觸發率 85–95%）+ Video Carousel（桌機更明顯） | 首位有機 CTR −58%；桌機 Video Carousel 直接壓縮藍色連結點擊 | [Hiilite: AI Overview 2026 CTR Impact](https://hiilite.com/ai-overview-aio-in-2026-what-it-is-how-it-impacts-click-through-rate-and-how-to-rank/) |
| 電影 評論（時效） | Top Stories / News Carousel | AMP 績效下滑→Top Stories 曝光降低，時效性影評查詢受影響最大 | [Growbydata: SERP Features 2026](https://growbydata.com/google-serp-features/) |

**判讀**：本週影評/電影的 CTR/流量下滑，市場面（Google Trends）已證實是院線空窗期的週期回落（月線仍強），故 S3 須把本站問題的權重從「市場需求萎縮」移轉到「SERP feature 壓縮」——桌機 Video Carousel + AIO 對「問答+比較型」查詢的壓縮，是桌機點擊 −9.23% 最可能的結構成因 [10][14]。

### Off-Page Authority 指標（B7）

**[CF] 沿用 2026-06-02 取得值（≤30 天 carry forward，今日 6/29 距 6/2 為 27 天，未重新查詢）：**

| 指標 | 工具 | 取得值 | 備註 |
|------|------|--------|------|
| DR (Domain Rating) | Ahrefs | **76** | 沿用 6/2；8.1K 參考網域 ⭐ |
| AS (Authority Score) | Semrush | **65** | 沿用 6/2；17.87K 參考網域 ⭐ |
| Monthly Traffic | Semrush | **8.03M** | 沿用 6/2；台灣占 82.69% |
| DA (Domain Authority) | Moz | 無法取得 | Moz 已停免費公開查詢 |
| TF / CF | Majestic | 待補 | 距 6/2 滿 30 天（≈7/2）重查時補連結品質錨點 |

**核心判讀（carry forward）**：DR 76（行業領先）+ AS 65 vs AI 占比月線深崩、站外三入口月線級失血——「長期域權威強 vs 短期 AI/站外分發弱」的分離本週進一步擴大。業界 75K 品牌研究 + AI Chatbot Traffic 研究（品牌提及與 AI 引用 Spearman 0.664 強相關、與反鏈相關性 <0.30）持續坐實本站「有連結權威、缺品牌提及/AI 引用」的脫鉤 [11][12][13]。

---

## Section 3：深度根因假設

> 本週 ALERT_DOWN 16 項 + ALERT_UP 13 項，依根因分群為 6 群（H1–H6）。生命週期標注對齊前週（6/19）。

### H1：內部連結月線崩、策展頁需求加速

**對應指標**（呼應 S1）：內部連結 M −27.30%（16,960,024，每頁 11.86）、/tags/ M +51.71%、討論區 W +18.07% / M +21.29%、站內搜尋框 M +34.02% [Updated → 加深]

**假設 1（供需背離面）**：策展頁需求月線級放大（/tags/ +51.71%、討論區 +21.29%、站內搜尋 +34.02%）、但內連供給月線級縮減（每頁 11.86、月線 −27.30%，較上週 −26.12% 再惡化）——背離較上週擴大，策展頁高度依賴內連把爬蟲與權重導入，供給弱化會削弱收錄率與權重傳遞 [2][3]。**【可驗證】**——用 Screaming Frog **抓取** /tags/ 與討論區策展頁、**檢查** 孤島頁內連缺口、**驗證** 每頁內連推回 13 以上。

**假設 2（爬取發現面，本週新增關鍵約束）**：vocus.cc 因 `.cc` 頂級網域**無法提交 sitemap 至 GSC**（Google 端限制），Googlebot 對新頁與策展頁的發現高度依賴內部連結自然爬取——這讓內連月線崩 27% 的傷害被放大：不只削弱權重傳遞，更直接削弱頁面「可被發現性」[4]。**【可驗證】**——用 Screaming Frog **比對** 內連月線 −27.30% 是真實連結移除（CMS 模板異動 / related-articles 模組取消）還是爬蟲快照口徑變化、**驗證** 每頁 11.86 的計算基數是否穩定。

**假設 3（AI 引擎連帶面）**：業界證實 2026 年 AI 搜尋引擎（Perplexity/Gemini/SGE）同樣依賴內部連結理解站點主題結構——內連流失不僅壓低 PageRank，更弱化 AI 引擎對 vocus 內容結構的理解，可能與 Perplexity 月線 −87.81% 形成惡性循環 [2][13]。**【需顧問判斷】**——是否同意「補內連」同時是 SEO 與 GEO 的共同基礎工程，應優先灌注娛樂類策展頁（影評月線 +67.83%）而非平均分配？

### H2：CTR 回吐、桌機點擊弱化

**對應指標**（呼應 S1）：CTR W −7.62% / M −7.16%（2.22%）、點擊 W −1.20%、桌機點擊 W −9.23%（372,946）、行動裝置點擊 W +2.85%、曝光 W +6.96% [New Hypothesis]

**假設 1（SERP feature 壓縮面）**：桌機點擊 −9.23% vs 行動 +2.85% 的分裂，與業界「AIO + Video Carousel 在桌機更積極插入、壓縮藍色連結」高度吻合——影評/電影屬「問答+比較型」查詢（AIO 觸發率 85–95%），首位有機 CTR 被壓 58%，桌機螢幕更完整顯示 AIO 故損失更多 [10][14]。**【可驗證】**——用 GSC **篩選** 桌機高曝光低點擊查詢、**比對** 是否集中於 AIO/Video Carousel 觸發的影視類查詢。

**假設 2（曝光稀釋面）**：曝光重啟攀升 +6.96% 但點擊與 CTR 跟不上——以曝光校正法回推（用上週 CTR 2.40% 套本週曝光），預期點擊 1,310,497、實際 1,211,505、缺口 98,992，證實是真實 CTR 下降而非曝光放大的均值假象；新增露出多落在低意圖長尾故拉低均值 [7][8]。**【可驗證】**——用 GSC **篩選** 曝光淨增 355 萬但點擊未跟漲的查詢 Top-30、**重寫** title / **優化 description** 撈回缺口 9.9 萬。

**假設 3（市場 vs 本站面）**：Google Trends 證實影評/電影 WoW 下滑屬院線空窗期週期（月線仍 +58~68%）——故 CTR 下降的本站責任權重應從「市場需求」移轉到「SERP 壓縮 + title/description 失效」[9][22]。**【需人工確認】**——CTR 月線 −7.16% 是否為「索引更多長尾、平均稀釋」（辛普森悖論）而非真實惡化，須以總曝光 + 有效關鍵字數並看 [22]。

### H3：Perplexity 續崩、站外品牌訊號收縮

**對應指標**（呼應 S1）：Perplexity W −19.02% / M −87.81%（149）、Gemini M −63.96%（152）、GPT W +2.20% / M +11.27%（1,901）、Referral M −29.90%、Organic Social M −21.19% [Updated → 加劇]

**假設 1（站外品牌訊號面）**：引用型 AI（Perplexity/Gemini）月線崩 + Referral/Organic Social 月線雙位數失血，三條站外入口同步收縮、方向一致——共同根源是「品牌在站外被提及/引用的密度下降」；75K 研究 + AI Chatbot Traffic 研究證實「AI 引用 ∝ 品牌提及（Spearman 0.664），∝ 反鏈（<0.30）」，本站 DR 76 卻 AI 崩，正是「有連結權威、缺品牌提及」的典型 [12][13]。**【需顧問判斷】**——是否同意 GEO 正解是「經營品牌網路提及（PR + 原創數據新聞 + YouTube 曝光）」而非站內內容量？

**假設 2（vocus 個案惡化面）**：vocus Perplexity 月線 −87.81% 遠超全市場 −10.82%——非單純跟隨業界下滑，須調查是否有特定高流量頁被 Perplexity 停止引用（疑與內容新鮮度或結構化標記缺失有關）[12]。**【可驗證】**——導入 GSC 生成式 AI 效能報告 **建立** 引用率 baseline、**比對** GPT（撐盤）/Gemini/Perplexity 的引用頁類型差異。

**假設 3（對話型撐盤面）**：GPT 連三週領頭 +2.20%（月線 +11.27%）、合計帶量靠 GPT 撐 86%——對話型（黏性高）回穩 vs 引用型（對品牌訊號最敏感）崩盤的分化延續；ChatGPT 仍佔 AI referral 約 80% [11][14]。**【需顧問判斷】**——是否評估加入 Perplexity Publisher Program（2,400+ 出版商加入後 referral +34%）作為引用型止血的戰術選項？

### H4：News 退潮、AMP Article 萎縮

**對應指標**（呼應 S1）：News(new) W −26.95% / M −107.88%（664）、Google News W −50.00%、AMP Article W −75.19% / M −195.79%（33）、AMP non-Rich M +21.80% [Updated → 版位演進]

**假設 1（檔期退潮面）**：News(new) 自高點退到 664、Google News −50%——院線/時事檔期視窗關閉，再現「News 暴起暴落」規律，屬脈衝紅利非常態 [18]。**【需人工確認】**——News 應視為脈衝紅利、不追加資源，僅在時事檔期以策展型內容提升 AMP 焦點新聞頻率。

**假設 2（AMP 版位演進面）**：AMP Article W −75.19%（自 6/5 的 133 腰斬到 33）但 AMP non-Rich M +21.80% 反向回補——CWV 時代 AMP 已非 Top Stories 必要條件，Article 版位自然退場、流量遷移到標準 AMP，屬版位演進而非故障 [19]。**【可驗證】**——在 GSC「體驗 → AMP」**比對** 警告錯誤類型是否真有對應減少、**確認** Article 從 133→33 是退場還是快照口徑不連續。

**假設 3（SERP 連動面）**：AMP 績效下滑→Top Stories / News Carousel 曝光機率同步降低，影評類「剛上映電影評論」這類時效查詢受影響最大——AMP 萎縮與 News 退潮可能互為因果 [19][14]。**【需顧問判斷】**——是否同意「AMP Article 退場順其自然、資源轉投標準頁的 AIO 友善格式」？

### H5：產品摘要月線失效

**對應指標**（呼應 S1）：產品摘要 W +1.82% / M −48.11%（224，較上週 M −34.35% 再惡化）、評論摘錄 W +5.30% / M −6.08%、結構化 Ratio W +9.53% [Updated → 惡化]

**假設 1（重分類面）**：業界曾證實 Google 把 Product 文件拆為 product snippet（非購買頁）vs merchant listing（可購買頁）——本站若被重判屬性，會在 GSC 兩張報告間移轉計數造成下滑，非必然 schema 故障；惟本月 Google 官方無新的結構化變更公告，須回 GSC 交叉比對 [20]。**【可驗證】**——在 GSC **比對**「產品摘要」vs「商家資訊」兩張報告的交叉變化、**確認** 是重分類還是真失效。

**假設 2（Review 止血面）**：評論摘錄 WoW 回補 +5.30%、月線跌幅收斂到 −6.08%——上週 Review schema 失效本週止穩，結構化漏點集中到 Product/Offer 類型 [20]。**【可驗證】**——在 GSC「結構化資料 → Product」**檢查** price/availability/review 欄位完整性、**修復** 缺漏欄位。

**假設 3（影視結構化走強面）**：Video Appearance +37.23%（月線 +191%）與產品摘要下滑背離——影視結構化版位走強、商品結構化走弱，反映本站內容重心（娛樂 vs 商品）的結構化收錄差異 [20]。**【需顧問判斷】**——是否把結構化資源優先投向走強的影視版位（承接娛樂檔期）而非衰退的商品版位？

### H6：工作階段週縮、平台集中度上升

**對應指標**（呼應 S1）：工作階段 W −3.58% / M +18.03%、Direct W +3.22% / M +38.86%（占比 40.6%）、Organic Search 占比 50.2%、站外三入口月線 −21~−88% [New Hypothesis]

**假設 1（消化整理面）**：工作階段 WoW −3.58% 是連五週回升後第一個大盤週縮，但月線仍 +18.03%、Organic Search 月線 +2.33%——月度水位完全未破，WoW 回吐更像上週 +8.80% 暴衝後的均值回歸而非趨勢反轉 [14][15]。**【可驗證】**——用 GA4「路徑探索」**檢查** 週縮集中在哪些到達頁與裝置、**驗證** 是均值回歸還是真實流失，避免過度反應。

**假設 2（平台集中度面）**：Direct 40.6% + Organic 50.2% ＝ 逾 90% 集中於 Google 生態 + 自有品牌，站外多元入口（社群 + 引薦 + AI）合計不足 5% 且月線同步崩——集中度高利於大盤穩定（本週僅微回 −3.58%），但放大單一平台演算法曝險（Core/Spam Update 三波疊加期更須警惕）[16]。**【需顧問判斷】**——是否把「流量來源多元度」列為新策略課題，補強站外品牌訊號（社群分享、外部引用、AI 被引用）？

**假設 3（歸因健康面）**：Direct +3.22%（月線 +38.86%）暴衝，但「GSC 探索/GA Direct」比值 0.41（+3.07%）回升、異常消除——當 Discover（+6.40%）與 Direct 同步上升、比值穩定，Direct 增量較不像 Discover referrer 錯歸；惟月線 +38.86% 仍遠快於工作階段 +18.03%，UTM 缺失造成的 Unassigned 膨脹須週期檢核 [15]。**【可驗證】**——在 GA4 **檢查** Direct 到達頁與 UTM 完整性、**驗證** 占比兩個月升逾 5pp 是真實成長還是歸因雜訊。

---

## Section 4：顧問視角交叉比對

| 狀態 | 主題 | KB 觀點 | 顧問文章觀點 | 指標數據 | 業界動態 | 判斷 |
|------|------|---------|-------------|---------|---------|------|
| [NEW] | June Spam Update 衝擊評估 | KB [14] 多數流量下降主因是網站架構非 AI/演算法 | Gene Hong「涵蓋範圍分系統因素 vs 網站因素」[TS-CV] | 本週無排名崩跌、ALERT_DOWN 多屬流量分發層 | June Spam Update 6/24–26 完成、不針對連結/SRA | 衝擊初判有限、6/30 後確認；UGC 品質端須自查 |
| [NEW] | 桌機 CTR 弱化 vs AIO 壓縮 | KB [10] 搜尋外觀變動手機桌機差異 | Gene Hong「搜尋外觀結構化資料互相競爭、手機端受衝擊大」[TS-SA] | 桌機點擊 −9.23% vs 行動 +2.85% | AIO 48% 查詢、首位 CTR −58%、桌機 Video Carousel | 結構性壓縮非個案、爭取 AIO citations |
| [Updated] | 內連崩 vs 策展需求升 | KB [2][3] 內連下降影響 PageRank、標籤頁突破流量瓶頸 | Gene Hong 公視案例：改善內連→網頁數 +53% / 連結數 +110% / 流量 +59% [TS-LINK] | 內連 M −27.30%（每頁 11.86）vs /tags/ M +51.71% | Pillar-Cluster 雙向、AI 引擎也依賴內連 [B-IntLink] | 背離加深、本週 💡；.cc 無 sitemap 使內連更關鍵 |
| [Updated] | 引用型 AI 崩、站外品牌訊號 | KB [12][13] 品牌提及 ∝ AI 引用（0.664）非反鏈 | Gene Hong「AI 導流低＝被搜尋與 AI 雙重忽略」[TS-AI1] | Perplexity M −87.81% vs 全市場 −10.82% | Perplexity Publisher Program +34% referral [B-AIvis] | vocus 個案惡化更深、GEO 升 P0、評估 Publisher Program |
| [NEW] | 平台集中度風險 | KB [16] 流量來源三大→四大演變、推薦流量多來自社群 | Gene Hong「推薦連結已死、轉向 Discover/社群/APP」[TS-CH] | Direct 40.6% + Organic 50.2% = 90%+ | 站外三入口月線 −21~−88% 同步崩 | 過度集中 Google 生態、補站外多元入口 |
| [CF] | 回應時間鎖死、爬蟲回溫 | KB [1] 回應時間與流量強烈負相關、釋放爬蟲預算 | Gene Hong「Crawler Stats 看 Cache/CDN 健康度」[TS-CV] | 回應時間 285ms（W −16.18%、累計 −59%）、爬蟲 +1.20% | 邊際紅利遞減（爬蟲量 +12.17%→+1.20%） | P0 持續解除、轉監控防回吐 |
| [CF] | B7 長期權威 vs 短期分發分離 | KB [11][13] Brand Radar 跨系統、品牌提及→AI visibility | Gene Hong「AI 放大內容品質差異」[TS-AI1] | DR 76 / AS 65 vs AI/站外月線崩 | AI 引用 ∝ 品牌提及非反鏈 [B-AIvis] | 分離擴大、carry forward 6/2、≈7/2 補 TF/CF |

---

## Section 5：五層審計缺口清單

| 層級 | 類型 | 描述 | 缺口現況 | 優先度 | SITREP |
|------|------|------|---------|--------|--------|
| **L1 技術層** | 回應時間續降 285ms、爬蟲回溫 | W −16.18%、285ms、爬蟲量月線 +3.01% 轉正 [1] | P0 持續解除、邊際紅利遞減、待轉自動告警 | 🟢 正向（鎖定） | [Validated, 累計 −59%] |
| **L1 技術層** | 駭客風險排除（採樣未索引 URLs） | 檢索未索引絕對量逾 70 萬、未排除被駭注入 | **P0+、連續第 9 週未執行** | 🔴 紅線級 | [CARRY-W9, 連續未執行] |
| **L1 技術層** | GSC 索引面 data lag、讀不到 | Coverage/未索引/排除/內連 WoW 全 0.00%、latest 卡 6/16 | 索引三鏈本週留白、延用上週讀數 | 🟡 中（待補資料） | [NEW, data lag] |
| **L2 內容層** | 內部連結月線崩 vs 策展需求升 | 內連 M −27.30%（每頁 11.86）vs /tags/ M +51.71%；.cc 無 sitemap [2][4] | **供需背離加深、入口基礎續弱** | 🔴 高 | [Updated, 本週 💡] |
| **L2 內容層** | 引用型 AI 崩、GEO 未啟動 | Perplexity M −87.81%（遠超市場）、GSC GenAI 報告到位 [12][13] | GEO 策略未啟動（工具已到位） | 🔴 高 | [CARRY-W6, 工具到位] |
| **L2 內容層** | CTR 回吐、桌機點擊弱化 | CTR W −7.62%、桌機點擊 −9.23%、曝光校正缺口 9.9 萬 [7][10] | 高曝光低點擊頁 title 重寫未啟動 | 🔴 高 | [NEW, 翻紅回吐] |
| **L3 內容品質層** | June Spam Update 內容品質審視 | UGC 平台、Spam Update 不針對連結但針對內容操縱 [14] | UGC 品質自查未做 | 🟡 中 | [NEW, 須自查] |
| **L4 結構化資料層** | 產品摘要月線失效疑重分類 | 產品摘要 M −48.11%（較上週 −34.35% 惡化）[20] | GSC 兩報告交叉比對未做 | 🟡 中 | [Updated, 惡化] |
| **L4 結構化資料層** | 影視結構化走強 vs AMP Article 萎縮 | Video Appearance +37.23% vs AMP Article −75.19% [19] | 混合（影視承接娛樂檔期） | 🟡 中 | [Updated, 分化] |
| **L4 連結層** | 連結生態錨點（carry forward） | DR 76 / 8.1K 參考網域，TF/CF 待補（≈7/2） | 錨點沿用、品質未驗 | 🟢 正向 | [CF, 沿用 6/2] |
| **L5 分發層** | 平台集中度風險浮現 | Direct 40.6% + Organic 50.2% = 90%+、站外三入口月線崩 [16] | 流量來源多元度未列策略課題 | 🔴 高 | [NEW, 新風險維度] |
| **L5 分發層** | GEO / AI 可見度經營 | AI 占比月線深崩、GSC GenAI 報告 + GEO 指南到位 [11][13] | Brand Radar + GSC AI 報告 baseline 未啟動 | 🔴 高 | [CARRY-W9, 工具到位待啟動] |

---

## Section 6：E-E-A-T 現況評估

**本週四維度均 No Change**——說明如下（必填）：本週的異常集中在**流量/分發層**（CTR 回吐、桌機弱化、站外入口失血）與**外部事件層**（June Spam Update、AIO 壓縮），尚未轉化為網站本體 E-E-A-T 的結構性位移。Trustworthiness 上週已因回應時間 P0 解除升到 3、本週回應時間續降鞏固但駭客採樣連續第 9 週未做（升 3.5 的唯一閘門仍卡）；Authoritativeness 沿用 6/2 B7 錨點（DR/AS 未重查），長期權威強 vs 短期分發弱的分離雖擴大但客觀錨點不變；Experience/Expertise 無新結構性變化。故四維持平、E-E-A-T 平均維持 **3.25**。

<details>
<summary>No Change（4 維度，點擊展開上週評估）</summary>

| 維度 | 分數 | 上週依據（carry forward）+ 本週註記 |
|------|------|------------------------|
| Experience | 3/5 | UGC 多元觀點持續、Information Gain 結構性不足未改變。本週娛樂 KW 月線強屬市場需求驅動非第一手經驗；強化方向仍為作者頁 Profile Page 結構化 [21] |
| Expertise | 3/5 | 技術 SEO 知識庫豐富、個別作者深度不一。本週無新結構性變化，維持 |
| Authoritativeness | 4/5 | **沿用 6/2 B7 錨點**（DR 76 ≥70 / AS 65，≤30 天未重查）。長期權威強 vs AI/站外分發弱（Perplexity M −87.81%、Referral M −29.90%）分離擴大。升 5 條件：AI 引用率回升 + 品牌提及成長 [11][13] |
| Trustworthiness | 3/5 | 回應時間續降 285ms 鞏固信任紅利，但駭客採樣連續第 9 週未做——升 3.5 的唯一閘門仍卡。June Spam Update 為新增監控項（不針對連結，UGC 品質須自查）[1][14] |

</details>

**Authoritativeness 評分客觀錨點（B7 carry forward）**：

- DR 76（≥70→錨點 5）+ AS 65（50–70→錨點 4）→ 加權約 4.5，因短期 AI/站外分發弱維持 **4**（沿用 6/2，未重查）
- **矛盾標記**：DR/AS（長期反向連結權威）強 vs AI 占比月線深崩 + Referral/Organic Social 月線雙位數失血（短期分發認可）弱——「短期擾動 vs 長期權威分離」本週擴大；75K 研究 + AI Chatbot Traffic 研究（品牌提及 ∝ AI 引用 0.664、∝ 反鏈 <0.30）從外部佐證此分離成因 [12][13]
- 下次 B7 重查（距 6/2 滿 30 天，≈7/2）補 TF/CF（Majestic）確認連結品質

**E-E-A-T 平均**：上週 3.25 → 本週 **3.25**（No Change）

**核心判讀**：本週 E-E-A-T 持平是誠實的判斷——這週的故事是流量、分發與外部演算法（CTR/桌機/站外/Spam Update/AIO），而非網站本體品質的結構性升降。E-E-A-T 仍受限於 Experience/Expertise 的結構性瓶頸（作者深度、第一手經驗）與 Trustworthiness 的駭客採樣閘門，這三點是下一階段唯一能推動 E-E-A-T 上行的槓桿，且都需要實際動工而非被動等待。

---

## Section 7：人本七要素分析

**Changed this week:**

| 要素 | 上週分數 | 本週分數 | 變化 | 依據 |
|------|---------|---------|------|------|
| 連結生態 | 4/5 | **3.5/5 ↓** | −0.5 | 上週已標「外健內弱」張力（外部 DR 76 健康 vs 站內內連月線 −26.12%），本週站內續惡化到 −27.30%、且業界證實內連流失同時弱化 AI 引擎對站點結構的理解（影響 Perplexity/Gemini 引用）——站內結構問題從「警示」升級為「實質拖累」。外部反鏈仍健康（DR 76）故未跌破 3.5；TF/CF 未取得無法確認 trust 品質 [2][4] |

<details>
<summary>No Change（6 要素，點擊展開上週評估）</summary>

| 要素 | 分數 | 上週依據（carry forward）+ 本週註記 |
|------|------|------------------------|
| 網站人格 | 3/5 | UGC 平台定位清晰；本週娛樂（影評）需求強化內容人格但未改結構，維持 |
| 內容靈魂 | 2/5 | 引用型 AI 續崩（Perplexity 月線 −87.81%）+ 站外品牌訊號加劇失血仍是內容品質弱訊號；本站缺「被提及的靈魂」，維持 2/5 列觀察 [12][13] |
| 使用者旅程 | 3/5 | 站內三入口走強（討論區 +18.07%、站內搜尋 +34.02%、/tags/ +51.71%），但站外獲客入口失血；問題在「把使用者第一次帶進站」而非站內承接，混合維持 3/5 |
| 技術體質 | 4/5 | 回應時間續降 285ms、爬蟲量月線 +3.01% 轉正（升 4.5 條件之一達標）、手機 CWV 好桶守住；惟駭客採樣連續第 9 週未做（升 4.5 另一閘門仍卡），維持 4/5 [1] |
| 資料敘事 | 4.5/5 | 「預測對帳」能力延續——本週把上週「內連/CTR 沒做會惡化」的預測兌現拿來驗證、且誠實處理 GSC data lag（不誤判為穩定）；維持 4.5 |
| 趨勢敏銳度 | 4.5/5 | 本週正確辨識 June Spam Update 三波疊加、AIO 桌機 CTR 壓縮（非個案）、影評院線空窗期、平台集中度新風險；維持 4.5 |

</details>

**連結生態（Link Ecosystem）評分客觀錨點（B7 carry forward）**：DR 76（≥60→錨點 5）+ 參考網域 8.1K–17.87K（充足），但本週**下調至 3.5**——因 (1) TF/CF 未取得無法確認 trust 品質、(2) 站內內連月線 −27.30% 持續惡化、(3) 內連流失連帶弱化 AI 引擎理解。**S6 vs S7 差異**：S6 Authoritativeness 評「外部如何看本站」（DR/AS 強→維持 4），S7 連結生態評「連結結構是否健康」（外部健康但站內持續崩 + 連帶 AI→下調 3.5），同一份數據從不同角度解讀、不重複扣分——本週首次因站內結構惡化讓兩者分數分歧。

**人本七要素平均**：上週 3.57 → 本週 **3.50**（−0.07，連結生態 4→3.5）

**核心判讀**：本週 −0.07 全來自「連結生態」下調——這是上週標記的「外健內弱」張力本週兌現為實質拖累。值得注意的是技術體質維持 4（爬蟲量月線轉正本可推 4.5，但駭客採樣閘門卡住），與 S8 Process 的 L3 天花板同源：**進展是成果、不是制度；閘門是執行、不是分析**。

---

## Section 8：SEO 成熟度自評

**本週四維度均 No Change**——說明如下（必填）：本週的進展（回應時間續降鞏固、預測對帳兌現、data lag 誠實處理、平台集中度新風險辨識）屬「執行品質 + 歸因分析」的延續，尚未轉化為「制度化能力」——自動 alerting、GSC GenAI 報告實際導入、Brand Radar 週級追蹤、Plan B 主軸拍板均未落地，故四維度維持。**最關鍵的成熟度訊號是反向的：上週點名的內連與 CTR 兩件結構性工作本週仍未動工、導致惡化**——這證明 Process 仍停在「能診斷、難執行」的 L3 天花板。

<details>
<summary>No Change（4 維度，點擊展開上週評估）</summary>

| 維度 | 等級 | 上週依據（carry forward）+ 本週註記 |
|------|------|------------------------|
| Strategy（策略）| L2.5（L2→L3 邊緣）| Plan B（影視 / GEO / 內連修復）仍未拍板；本週平台集中度 + 引用型 AI vocus 個案惡化提供 Plan B 新素材，但尚未決策。升 L3：Plan B 至少一方向實際啟動 + 量化 KPI |
| Process（流程）| L3 | 危機應對仍依賴每週手動審核；上週點名的內連/CTR 本週未執行而惡化，凸顯「診斷強、執行弱」。升 L4：回應時間自動告警 + GSC GenAI 報告導入流程 |
| Keywords（關鍵字）| L3 | 本週 KW 分析（影評/電影院線空窗驗證、KW 股脈衝辨識）具 L4 雛形但仍手動。升 L4：SERP feature 細分追蹤 + Brand Radar 引用率 [22] |
| Metrics（指標）| L3.5 | 本週能做預測對帳（內連/CTR 預測兌現）+ 誠實處理 data lag + 平台集中度新維度，歸因能力強，維持 L3.5。升 L4：GSC API + GenAI 報告自動抓取 + 閾值 alerting |

</details>

**成熟度概覽**：Strategy L2.5 / Process L3 / Keywords L3 / Metrics L3.5——與上週持平。本週「上週點名卻沒做→本週惡化」的劇本，恰恰凸顯 Process 的 L3 天花板：能正確診斷（執行品質高），但缺「把診斷轉成必執行的制度」。**把本週手動排查的回應時間流程沉澱為自動 alerting、把 GSC GenAI 報告導入週流程 = Process L3→L4 與 Metrics L3.5→L4 的最具體路徑。**

---

## Section 9：會議提問清單（核心輸出）

### A 類：確認事實（4 題）

**A1 [NEW]**：**June 2026 Spam Update**（6/24–26 完成、SpamBrain 主導、48 小時提前收尾）明確不針對連結垃圾與 Site Reputation Abuse、而針對其他內容操縱——本週 vocus 未見排名崩跌（ALERT_DOWN 多屬流量分發層）。是否已在 GSC 分裝置/分 query type **比對** Spam Update 前後（6/24 vs 6/26）的排名與曝光變化，確認 UGC 內容品質端未觸及審視 [14]？

**A2 [CARRY-W9]（前週 A2 carry，連續第 9 週）**：採樣 50–100 個**檢索未索引** URLs 確認合法 vocus 路徑而非被駭注入——**連續第 9 週未取得答案**。本週 GSC 索引面 data lag 讀不到、但絕對量仍逾 70 萬。是否本週指派獨立 owner 在 GSC **採樣** 完成（這也是 Trustworthiness 升 3.5 的唯一剩餘閘門）？

**A3 [Updated]（前週 A3 演進）**：本週**內部連結**月線從 −26.12% 惡化到 **−27.30%**（每頁 11.86），且 vocus.cc 因 `.cc` TLD 無法提交 sitemap、爬取發現高度依賴內連——是否已用 Screaming Frog **比對** 內連月線崩是真實連結移除（CMS 模板/related-articles 模組異動）還是快照口徑變化，並 **檢查** 策展頁遷移期 4xx/redirect chain [2][4]？

**A4 [NEW]**：本週**桌機點擊** −9.23% vs **行動裝置點擊** +2.85% 的分裂——業界證實 AIO（48% 查詢、首位 CTR −58%）+ 桌機 Video Carousel 對「問答+比較型」查詢的壓縮是全球結構性問題。是否確認此分裂屬 AIO/SERP feature 壓縮（全球趨勢）而非本站桌機內容/版面故障 [10][14]？

### B 類：探索判斷（5 題）

**B1 [Updated]（前週 B1 演進）**：**內部連結**基礎崩 27.30% vs 策展頁需求升（/tags/ 月線 +51.71%、討論區 +18.07%）是本週最大供需背離，且上週點名卻未動工、本週惡化。顧問公視案例顯示改善內連可帶來「網頁數 +53% / Google 認同連結數 +110% / 搜尋流量 +59%」——是否本週**真正動工**把娛樂類策展頁（影評月線 +67.83%）內連密度補回 13 以上，而非再次列而不做 [2][3]？

**B2 [CARRY-W6]（前週 B2 carry）**：**引用型 AI** 續崩（Perplexity 月線 −87.81% **遠超**全市場 −10.82%、Gemini −63.96%）vs GPT +2.20% 撐盤——vocus 屬個案惡化更深。是否啟動 GEO 為 P0：用 GSC 新上線的 GenAI 效能報告建引用率 baseline、調查特定頁是否被 Perplexity 停止引用、並評估加入 Perplexity Publisher Program（+34% referral）[12][13]？

**B3 [NEW]**：本週**平台集中度**浮現為新風險——Direct 占比 40.6% + Organic Search 50.2% ＝ 逾 90% 集中於 Google 生態，而站外三入口（Organic Social 月線 −21.19% / Referral 月線 −29.90% / Perplexity 月線 −87.81%）同步月線級失血。在 Core/Spam 三波更新疊加期，是否同意把「流量來源多元度」列為策略課題、補強站外品牌訊號 [16]？

**B4 [CARRY-W8]（前週 B4 carry，連續第 8 週）**：**Plan B 主軸選擇**連續第 8 週——本週素材：影視（影評月線 +67.83%、Video Appearance +37.23%）、GEO（GSC GenAI 報告到位 + Perplexity Publisher Program）、內連修復（背離加深 + .cc 無 sitemap）三選項。是否本週正式拍板主軸並分配資源 [TS-AIM]？

**B5 [NEW]**：本週 **CTR** 從上週 +2.85% 翻紅回吐到 −7.62%（曝光校正缺口 9.9 萬點擊），同期曝光重啟攀升 +6.96%（淨增 355 萬）——是否同意趁曝光擴張窗口、用 GSC 篩選曝光增但點擊未跟漲查詢 Top-30 重寫 title/description，把缺口 9.9 萬撈回、CTR 推回 2.4%（這是本週見效最快的單一槓桿）[7][9]？

### C 類：挑戰假設（3 題）

**C1 [NEW]**：本週 **Health Score** 51（連六週回升告終），前五週的 +11 分多來自「修復先前失血」（回應時間、Coverage、CWV），真正「創高」的指標始終是少數。**當止血紅利出盡（回應時間逼近 285ms 物理下限），而能接棒創高的內連與 CTR 兩槓桿都沒動，健康分就失速回落——這是否意味本波回升已到天花板、本站成長高度依賴「修復」而非「創造」**？

**C2 [CARRY-W3]（前週 C2 演進）**：連續三週質疑「顧問會議價值正從『改善網站』轉為『改善分析』」——本週 E-E-A-T 持平、人本僅 −0.07（且全來自連結生態下調），網站本體（Experience/Expertise）仍卡關。**本週又把 WoW 回吐判讀為「消化整理」、把索引讀不到歸因「data lag」、把影評下滑歸因「院線空窗」——這三個「合理化」是否正在掩蓋真實的執行停滯**？

**C3 [NEW]**：本週同時遭遇三波 Google 更新疊加（Core/不明/Spam）+ GSC data lag——**我們把幾乎所有 WoW 異常都歸因為「均值回歸 / 檔期 / 資料延遲 / 業界結構性」這些外部或暫時因素，是否存在「歸因外部化」的確認偏誤、低估了 June Spam Update 對 UGC 內容真實衝擊的可能性**？

### D 類：業界趨勢（2 題）

**D1 [CARRY-W2]（前週 D1 演進）**：業界證實 **AIO** 桌機 CTR 壓縮是結構性問題（48% 查詢、首位 −58%、被引用頁多獲 120% 點擊曝光比）——本站桌機點擊 −9.23%。是否同意「桌機 CTR 弱化的對策不是改 title 而是爭取被 AIO 引用」，並用 GSC 新 GenAI 效能報告追蹤本站在 AIO 的引用率，把資源投向 AIO 友善的結構化事實段落 [10][14]？

**D2 [NEW]**：**June Spam Update** 不針對連結/SRA 而針對內容操縱、且 Google 官方確認「AEO/GEO 仍是 SEO」——是否同意 vocus 的最佳防守 + 進攻是同一件事：強化 E-E-A-T + 結構化、可擷取的事實段落，既防 Spam Update 審視、又同時提升 AIO/引用型 AI 的被引用機率，避免重複投入兩套工具 [14][21]？

---

## Section 10：會議後行動核查表

| 優先度 | 行動（含工具名 + 動作動詞 + 成熟度標籤） |
|--------|----------------------------------------|
| 🔴 P0 | 在 **Screaming Frog** **抓取** /tags/ 與討論區娛樂類策展頁、**檢查** 內連卡 11.86 與月線 −27.30% 的缺口頁與遷移期 4xx/redirect chain，對缺口頁 **加入** 標籤導讀內連 5–10 條 + **修復** 失效連結為 301，**驗證** 每頁內連推回 13 以上（.cc 無 sitemap 故內連是主要爬取發現路徑）— **[L2 內容 L3→L3]** |
| 🔴 P0+ | 在 **GSC「已檢索但未編入索引」** **採樣** 50–100 個 URLs **確認** 全為合法 vocus 路徑而非被駭注入（連續第 9 週 carry、指派獨立 owner，T 維升 3.5 唯一閘門）— **[L1 技術 L2→L3]** |
| 🔴 P1 | 在 **GSC 生成式 AI 效能報告** **建立** vocus.cc 在 AI Overview / Gemini 的引用率 baseline、**調查** Perplexity 月線 −87.81% 是否有特定頁被停止引用、**對比** GPT/Gemini/Perplexity 引用頁類型 — **[L4 指標 L3→L4]** |
| 🔴 P1 | 在 **GSC「成效 → 查詢」** **篩選** 曝光淨增 355 萬但點擊未跟漲的查詢 Top-30（趁曝光擴張窗口），**重寫** title 並 **優化 description** 把曝光校正缺口 9.9 萬撈回、CTR 推回 2.4% — **[L2 內容 L2→L3]** |
| 🔴 P1 | 在 **內部監控系統** **建立** 回應時間 > 450ms 自動告警（把連兩週手動鎖死的 P0 制度化）、**設定** 週環比 ±15% 觸發 Slack、**驗證** 下次部署 TTFB 不回吐 — **[Process L3→L4]** |
| 🟡 P2 | 在 **GA4「流量開發 → 工作階段管道」** **檢查** Organic Social（月線 −21.19%）與 Referral（月線 −29.90%）的失流量來源頁與裝置構成、**驗證** 是平台演算法還是站內分享減少、**加入** 社群分享與內部導讀模組 — **[L5 分發 L3→L3]** |
| 🟡 P2 | 在 **GA4** **檢查** 桌機點擊 −9.23%（vs 行動 +2.85%）集中的落地頁與查詢、**驗證** 是否與 AIO/Video Carousel 桌機壓縮相關（而非內容故障）— **[L5 分發 L3→L3]** |
| 🟡 P2 | 在 **GSC** **比對**「產品摘要」（月線 −48.11%）vs「商家資訊」兩張結構化報告的交叉變化、**確認** 是 Google 重分類還是 schema 故障、**修復** price/availability 欄位 — **[L4 結構化 L3→L3]** |
| 🟡 P3 | 評估加入 **Perplexity Publisher Program** 入選資格（2,400+ 出版商加入後 referral +34%）+ 在 **Ahrefs Brand Radar** **檢查**「vocus + 核心 KW」在 Perplexity/Gemini 的被引用率與品牌提及缺口、**補上** 原創數據與事實摘要段 — **[L2 內容 L3→L4]** |
| 🟡 P3 | 在 **Majestic** **查詢** vocus.cc 的 TF/CF 補全 B7 連結品質錨點（距 6/2 滿 30 天≈7/2 時）、**補錄** `data/off-page-authority.jsonl`、**驗證** TF/CF > 0.8 — **[L4 指標 L3→L4]** |
| 🟢 P4 | 在 **GSC「成效 → Discover」** **篩選** 本週淨增 26,598 的到達頁、**檢查** 行動圖片規格與 LCP、趁月線 +28.10% **加入** 高解析封面圖維持 5% 點閱率門檻 — **[L5 分發 L3→L3]** |

> ℹ️ **回應時間 P0 連兩週持續解除（基礎設施紅利進入穩態）**
> 回應時間 694→340→285ms（累計 −59%），爬蟲量月線 +3.01% 轉正。但邊際紅利遞減（爬蟲量增幅 +12.17%→+1.20%）、已逼近物理下限。**後續重點轉為「監控防回吐 + 制度化告警」**（見 P1），把被動受惠轉為主動鎖死，並把資源騰出投向能「創高」的內連與 CTR 兩槓桿。

**成熟度參考**：本期四維度持平（Strategy L2.5 / Process L3 / Keywords L3 / Metrics L3.5）。本週「上週點名卻沒做→惡化」凸顯 Process L3 天花板；若 P1（回應時間自動告警 + GSC GenAI 報告導入）落地 + 駭客採樣完成，可同步推進 Process L3→L4 與 Metrics L3.5→L4——**把手動排查沉澱為自動制度、把診斷轉成必執行的閘門，是本季 L3→L4 的最具體槓桿。**

---

## Appendix：顧問文章引用

**Gene Hong「AI 導流越高，搜尋流量越上升？一個被誤解的流量悖論」（2025-12-10）**[TS-AI1]
- 「AI 導流低的網站，才是搜尋與 AI 都同時忽略的那群」「AI 並沒奪走誰的流量，它只是放大內容品質的差異」「SEO 做得好的網站，自然也同時具備 GEO 的基礎」
- 對應本週 H3：vocus Perplexity 月線 −87.81% 遠超全市場 −10.82% + DR 76 域權威分離——業界研究（AI 引用 ∝ 品牌提及非反鏈）從外部坐實「有連結權威、無 AI 引用權威」
- 來源：[genehong.medium.com](https://genehong.medium.com/ai-導流越高-搜尋流量越上升-一個被誤解的流量悖論-db8048a798a8)

**Gene Hong「公視新聞網的延伸閱讀製作流程與經驗」（2020-10-03）**[TS-LINK]
- 「SEO 的精義是『找到對的網頁，用對的說明文字，讓對的使用者點擊』」「改善延伸閱讀後：網頁數提升 53%、Google 認同的連結數提升 110%、搜尋流量提升 59%」
- 對應本週 H1/B1：內連月線 −27.30% vs 策展需求升的供需背離——顧問案例量化內連策展的直接 ROI，證明編輯用心的內連能帶來搜尋流量與連結權重雙重提升
- 來源：raw_data/medium_markdown（genehong-medium）

**Gene Hong「2023 年四月的 Google Search Console 搜尋外觀數字大變動」（2023-04-29）**[TS-SA]
- 「搜尋外觀報表中的結構化資料會有互相競爭的狀況」「手機端受影響明顯，桌機端相對穩定」（反之，桌機受 AIO/Video Carousel 壓縮時更明顯）
- 對應本週 H2/A4：桌機點擊 −9.23% vs 行動 +2.85%——搜尋外觀（AIO/Video Carousel）的版位競爭在桌機端壓縮藍色連結 CTR
- 來源：raw_data/medium_markdown（genehong-medium）

**Gene Hong「在後社群時代的導流新通道：探索」（2023-05-01）**[TS-CH]
- 「推薦連結（Referer）導流幾乎消失，流量來源變成：付費、社群、搜尋、APP」「經營 Discover 的關鍵：新鮮內容、視覺內容、分眾市場、行動裝置有效」
- 對應本週 H6/B3：站外三入口月線級失血（社群 −21.19% / 引薦 −29.90% / AI −88%）+ 平台集中度 90%——傳統 Referer 已死，須轉向 Discover/社群/AI 被引用等新入口
- 來源：raw_data/medium_markdown（genehong-medium）+ KB [16]

**Gene Hong「Google Search Console 對涵蓋範圍等改版的重點提示」（2022-08-18）**[TS-CV]
- 「涵蓋範圍把原因分成網站因素與爬蟲因素；Google 系統造成的未索引才是該注意的」
- 對應本週 A1/H6：June Spam Update + GSC data lag 須區分「系統因素（演算法/資料延遲）vs 網站因素（內容/技術）」，避免歸因外部化
- 來源：[genehong.medium.com](https://genehong.medium.com/google-search-console-對涵蓋範圍等改版的重點提示-930928786ac9)

**Gene Hong「AI x SEO 的幾個重要迷思與方法論」（2025-08-31）**[TS-AIM]
- 「AI x SEO 的重點不在如何使用 AI，而是如何使用人」「Human in the Loop 最重要」「選擇累積而非佔位」
- 對應本週 B4：Plan B 主軸（影視 / GEO / 內連）的 GEO 正解不是量產內容，而是人本要素 + HITL + 與權威媒體 co-citation
- 來源：raw_data/medium_markdown（genehong-medium）

---

<!-- meeting_prep_meta {"date": "2026-06-26", "generated_at": "2026-06-29T00:00:00.000Z", "input_source": "output/report_20260626_a283e3fd.md", "prev_report": "meeting_prep_20260619_a6ee9934.md", "alert_down": 16, "industry_items": 20, "kb_citations": 22, "consultant_articles": 6, "eeat_avg": 3.25, "humanistic_avg": 3.50, "maturity": {"strategy": "L2.5", "process": "L3", "keywords": "L3", "metrics": "L3.5"}, "off_page_authority": {"dr": 76, "as": 65, "monthly_traffic": 8030000, "source": "carry-forward 2026-06-02"}, "core_update": "June 2026 Spam Update completed 2026-06-24~26 (SpamBrain, not link/SRA); three-wave stack with May Core Update (6/2) + unconfirmed (6/19)", "key_event": "連六週回升告終Health53->51消化整理 + 上週點名內連(-27.30%)與CTR(-7.62%)雙惡化為回落主因 + June Spam Update收尾三波疊加 + 桌機CTR-9.23%=AIO桌機壓縮全球結構性 + 平台集中度90%新風險 + .cc無sitemap使內連更關鍵 + Perplexity-87.81%遠超市場-10.82%個案惡化 + 連結生態4->3.5"} -->

<!-- citations [{"n":1,"id":"dc73787fc2e911a3","category":"索引與檢索","title":"Search Console 的 42 個數字 - 回應時間與流量最相關","date":"","snippet":"檢索回應時間與流量呈現強烈負相關，是整個 KPI 表中最重要的數值之一；回應時間越久流量越低","chunk_url":"/admin/seoInsight/dc73787fc2e911a3","source_url":null},{"n":2,"id":"012e1f794ef22a80","category":"連結策略","title":"比較嚴重的指標下跌 — 內部連結指標下降改善方式 (2023-09-06)","date":"2023-09-06","snippet":"內部連結指標下降代表 Google 能追蹤的站內連結數量或品質降低，影響 PageRank 在站內的流動與頁面可發現性；策展文章缺乏互相連結會降低整體連結密度","chunk_url":"/admin/seoInsight/012e1f794ef22a80","source_url":null},{"n":3,"id":"828316fc34745017","category":"連結策略","title":"SC 內部指標討論 - 標籤頁 SEO 潛力 (2023-12-06)","date":"2023-12-06","snippet":"標籤頁可作為突破流量瓶頸的策展工具；財報狗嘗試以標籤頁突破全站流量 25%，垂直領域流量集中效果可觀","chunk_url":"/admin/seoInsight/828316fc34745017","source_url":null},{"n":4,"id":"5ccabf45b7700301","category":"索引與檢索","title":"SEO 會議_20260209 - .cc 網域 sitemap 限制 (2026-02-09)","date":"2026-02-09","snippet":"Google 不接受 .cc 頂級網域的 sitemap 提交，屬 Google 端限制；短期維持現狀，繼續透過強化內部連結結構讓 Googlebot 透過自然爬取發現頁面","chunk_url":"/admin/seoInsight/5ccabf45b7700301","source_url":null},{"n":5,"id":"780ba8d5305a2efd","category":"內容策略","title":"新媒體經營的全面手冊 - 懶人包策展 SEO 價值","date":"","snippet":"懶人包匯聚特定主題多元關鍵字和連結、易成搜尋主要入口具高 SEO 價值；持續更新的懶人包比靜態列表更強","chunk_url":"/admin/seoInsight/780ba8d5305a2efd","source_url":null},{"n":6,"id":"746c060abe9be623","category":"搜尋表現分析","title":"新媒體的未來實作 (V) 中間列表頁篇 - 懶人包 SEO 優勢","date":"","snippet":"懶人包是資訊入口型列表頁，搜尋競爭力極高；時間早累積、可不斷更新、關鍵字聚焦、CTR 高、停留時間長、被連結機會高","chunk_url":"/admin/seoInsight/746c060abe9be623","source_url":null},{"n":7,"id":"d7977e1eb5aebf5e","category":"搜尋表現分析","title":"大型網站的關鍵字流量探索 - CTR 預估落差（曝光校正）判讀升降","date":"","snippet":"用前期 CTR 套當期曝光回推預期點擊，與實際點擊的落差可判讀真實升降、排除曝光放大造成的均值假象","chunk_url":"/admin/seoInsight/d7977e1eb5aebf5e","source_url":null},{"n":8,"id":"29f981f09f0cda23","category":"搜尋表現分析","title":"SC 內部指標討論、2024-07-22 - CTR 下降是好事","date":"2024-07-22","snippet":"CTR 下降通常意味曝光數成長幅度遠大於點擊，是好事","chunk_url":"/admin/seoInsight/29f981f09f0cda23","source_url":null},{"n":9,"id":"f50c900d2aecc0cd","category":"搜尋表現分析","title":"SEO 會議_20251013 - TDK 變動影響點擊","date":"2025-10-13","snippet":"TDK 變動可能導致使用者看到不熟悉的標題與描述而減少點擊，即使平均排名沒變整體點擊仍可能下降","chunk_url":"/admin/seoInsight/f50c900d2aecc0cd","source_url":null},{"n":10,"id":"005536dc3bc9604b","category":"其他","title":"2023/04 搜尋外觀變動 - 手機桌機影響差異","date":"","snippet":"2023 年四月搜尋外觀變動對行動裝置與桌機影響有明顯差異，FAQ 影響主要集中手機端；分析時應分別檢視行動與桌機，避免籠統判斷","chunk_url":"/admin/seoInsight/005536dc3bc9604b","source_url":null},{"n":11,"id":"c166e9623752e053","category":"演算法與趨勢","title":"Google Seems More Biased Towards Big Brands - Ahrefs Brand Radar 跨系統品牌可見度","date":"","snippet":"建議使用 Ahrefs Brand Radar 進行跨系統（Google AI Overviews、ChatGPT、Perplexity）品牌可見度監測，並對比競品與被提及狀況","chunk_url":"/admin/seoInsight/c166e9623752e053","source_url":null},{"n":12,"id":"a631ace759edfb7a","category":"索引與檢索","title":"AI Chatbot Traffic: What It Is, and How to Get More (2026-05-15)","date":"2026-05-15","snippet":"品牌的網路提及數量是決定 AI 是否將品牌納入回答的最關鍵因素，Spearman 相關係數 0.664 為強相關；即使提及品牌引用率僅 10-51%","chunk_url":"/admin/seoInsight/a631ace759edfb7a","source_url":null},{"n":13,"id":"2533db03cde52dc0","category":"演算法與趨勢","title":"Google Seems More Biased Towards Big Brands - branded mentions 與 AI visibility","date":"","snippet":"在 Google AI Overviews 中 branded web mentions 與 AI visibility 呈現明顯較強正相關","chunk_url":"/admin/seoInsight/2533db03cde52dc0","source_url":null},{"n":14,"id":"b868dc8b00d1d2f2","category":"演算法與趨勢","title":"Google Search Console 近日變動的五點注意事項 (2025-10-29)","date":"2025-10-29","snippet":"大部分網站流量下降的主因是網站架構問題，而非 AI Overview 或 AI 搜尋；觀察樣本中超過半數網站流量實際上升","chunk_url":"/admin/seoInsight/b868dc8b00d1d2f2","source_url":null},{"n":15,"id":"5267399c05566bbf","category":"GA與數據追蹤","title":"SEO 會議_20260112 - GA Referral 交叉驗證","date":"2026-01-12","snippet":"在 GA 查看 Referral → Search 來源核對 GSC 搜尋流量是否一致、找出損失量來源","chunk_url":"/admin/seoInsight/5267399c05566bbf","source_url":null},{"n":16,"id":"34cecc0a258b4f4d","category":"其他","title":"在後社群時代的導流新通道：探索 - 流量來源三大到四大演變","date":"","snippet":"傳統網站流量三大來源為直接、推薦、搜尋，現代演變為付費廣告、社群、搜尋、APP 四大來源；推薦流量多來自社群網站","chunk_url":"/admin/seoInsight/34cecc0a258b4f4d","source_url":null},{"n":17,"id":"5cea18faf6a16938","category":"Discover與AMP","title":"SEO 會議_2023/10/04 - Discover 死灰復燃","date":"2023-10-04","snippet":"已停止被探索推播的文章，有機會在獲得新社群訊號或流量再次上升時重新被推播（死灰復燃）","chunk_url":"/admin/seoInsight/5cea18faf6a16938","source_url":null},{"n":18,"id":"7aa03f2fd1ac07c6","category":"內容策略","title":"SC 內部指標討論、2024-07-22 - Google News 流量下滑","date":"2024-07-22","snippet":"News 與檔期高度相關、流量暴起暴落，難成穩定流量來源，需靠時事策展內容維持焦點新聞出現頻率","chunk_url":"/admin/seoInsight/7aa03f2fd1ac07c6","source_url":null},{"n":19,"id":"0ed2930e2e2d7c04","category":"Discover與AMP","title":"What Are Core Web Vitals - CWV 後 AMP 非 Top Stories 要求","date":"","snippet":"Core Web Vitals 上線後 AMP 已非 Top Stories 的必要條件，AMP 版位自然退場屬版位演進而非故障","chunk_url":"/admin/seoInsight/0ed2930e2e2d7c04","source_url":null},{"n":20,"id":"2b1f713f1b03ce14","category":"技術SEO","title":"SC 27 KPI (16) - 結構化資料格式與收錄","date":"2021-09-16","snippet":"結構化資料格式如 RDFa/Microformat 將資料與網頁綁定，複雜度影響工程實作；格式選擇影響收錄判讀","chunk_url":"/admin/seoInsight/2b1f713f1b03ce14","source_url":null},{"n":21,"id":"23eff8f0210ef59e","category":"技術SEO","title":"SEO 會議_2024/01/24 - 作者 Profile Page E-E-A-T","date":"2024-01-24","snippet":"作者頁面可透過實作 Profile Page 結構化資料，向 Google 明確傳遞作者身份與專業性信號，強化 E-E-A-T","chunk_url":"/admin/seoInsight/23eff8f0210ef59e","source_url":null},{"n":22,"id":"5b93ebdc0a348370","category":"搜尋表現分析","title":"SEO 會議_20251013 - 辛普森悖論與平均排名","date":"2025-10-13","snippet":"辛普森悖論：索引更多長尾關鍵字時整體平均排名數字反而下降，但實際流量與整體表現進步","chunk_url":"/admin/seoInsight/5b93ebdc0a348370","source_url":null}] -->
