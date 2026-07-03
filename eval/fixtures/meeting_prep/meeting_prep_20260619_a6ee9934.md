# SEO 顧問會議準備 — 2026/06/19（週期 6/13–6/19）

> 輸入來源：`output/report_20260619_dc74c632.md`（本週週報）
> 對比基準：前次 meeting-prep `meeting_prep_20260605_0910d58b.md`（6/5）
> 框架：5-Layer Audit + E-E-A-T + 人本七要素 + SEO 成熟度
> **報告銜接**：上一份 meeting-prep 截至 6/5，本份跳過 6/6–6/12 週的獨立成稿、直接以其為「上週」基準。
> **本週最大內部變數：上週列為唯一 P0 的「週平均回應時間」連三週飆破 600ms（694ms）本週崩回 340ms（週線 −20.56%、自高點 −51%）——P0 解除，且上週預測的「壓回 → 爬蟲量回升」因果鏈正向兌現。**
> **本週最大外部變數：May 2026 Core Update 已 6/2 完成，但 6/15–17 排名波動持續、6/19 又有不明更新（主打黑帽側）——本週資料窗（6/13–6/19）正坐落於核心更新後的「重新評估期」。**

---

## Section 0：執行摘要

- **上週 P0（回應時間）解除、因果鏈正向兌現**：週平均回應時間 694→428→**340ms**（週線 −20.56%），週平均檢索數隨即回升 +12.17%、Coverage +6.83%、檢索未索引清到波段新低 708k——6/5 報告「壓回回應時間 → 爬蟲量回升 → 回填引擎重新點火」的預測本週逐項命中，是「把基礎設施債當第一要務」決策正確性的直接驗證。Health Score 48→53（+5，連五週新高）。
- **核心軸守成 + 轉換回補**：曝光守在 5,100 萬量級（週線 −0.09%、月線 +16.53%），但點擊 +2.76%、CTR +2.85% 雙漲跑在曝光之前——上週「曝光擴張、CTR 稀釋」的漏點本週收斂。惟此守成期正逢 May Core Update 後的重新評估窗（6/15–17 業界排名波動），月線水位能否補回 6/5 高點需 6/26 再確認紅利是否回吐。
- **本週最該警惕的反向訊號是「內部連結基礎」**：內部連結月線 **−26.12%**（每頁內連 14→11.86），同期策展頁需求卻在加速（/tags/ 月線 +57.75%、搜尋標籤占比 +50.45%、影評月線 +101.61%）——「需求升、供給縮」的供需背離。業界佐證：內鏈一致性是 AI/Google 推斷主題權威的核心訊號，遷移期舊連結失效會暫時削弱主題權威。此為本週 💡 最值得投入項。
- **引用型 AI 加速失血、但業界證實非本站個案**：Perplexity 月線 −216%、Gemini −135% 續崩，GPT +22.45% 單引擎撐盤。業界 75,000 品牌研究顯示「AI 引用與品牌網路提及相關性最高（r=0.50–0.74）、與反鏈數量最低（<0.30）」——這精準解釋本站 DR 76（連結權威強）卻 AI 能見度弱的分離：**有連結權威、缺品牌提及/AI 引用**。GEO 仍列 Q2 P0。
- **結構化資料「產品摘要」−19.71% 可能是 Google 重分類而非標記故障**：業界證實 Google 已把 Product 文件拆為 product snippet（非購買頁）vs merchant listing（可購買頁）——本站若被重新判定屬性，會在 GSC 兩張報告間重分類造成計數下滑，須交叉比對而非直接判定 schema 失效。B7 off-page authority 沿用 2026-06-02 取得值（DR 76 / AS 65 / 月流量 8.03M，≤30 天 carry forward）。

---

## Section 1：本週異常地圖

### ALERT_DOWN（按嚴重度排序）

| 指標 | 週線 | 月線 | latest | 判讀 |
|------|-----:|-----:|-------:|------|
| AMP Article | **−48.65%** | −142.64% | 133 | AMP 版位續萎縮（CWV 時代自然退場）🟡 |
| Perplexity（工作階段） | −33.09% | −216.01% | 184 | 引用型 AI 月線斷崖 🔴 |
| Gemini（工作階段） | −23.98% | −135.21% | 149 | 引用型 AI 月線崩 🔴 |
| News(new) | −23.36% | −78.58% | 909 | 院線檔期退潮（暴起暴落）🟡 |
| Organic Social（工作階段） | −23.21% | −3.35% | 78,459 | 社群轉介走弱 🟡 |
| GSC 探索/GA Direct | −22.64% | +26.52% | 0.4 | 比值異常、疑 Discover 錯歸 Direct 🔴 |
| /user（作者頁） | −20.25% | +2.52% | 2,993 | 作者頁流量回吐 🟡 |
| 產品摘要 | −19.71% | −34.35% | 220 | 結構化外觀流失（疑重分類）🟡 |
| Image（圖片版位） | −16.16% | −3.46% | 21,272 | 圖片版位回吐 🟡 |
| 討論區 | −15.90% | +20.25% | 13,373 | 社群版位 WoW 回吐（月線仍正）🟢 |
| Video | −13.30% | −1.55% | 1,356 | 影片版位回吐 🟡 |
| Discover | −9.09% | +20.90% | 415,832 | 檔期回吐（月線仍 +20.90%）🟢 |
| Referral（工作階段） | −8.94% | −26.56% | 59,740 | 外部轉介續弱 🟡 |
| 內部連結（月線結構） | 0.00% | **−26.12%** | 16,960,024 | 每頁內連 14→11.86、策展入口弱化 🔴 |

### ALERT_UP（正向訊號 / 需釐清）

| 指標 | 週線 | 月線 | latest | 判讀 |
|------|-----:|-----:|-------:|------|
| 週平均回應時間 | **−20.56%** | −7.21% | 340ms（←694） | **P0 解除、自高點腰斬** 🟢 |
| Video Appearance | +83.48% | +224.47% | 2,877 | 影視結構化版位走強 🟢 |
| AMP 索引(警告) | −59.53% | −162.95% | 312 | 警告債清償（降為佳）🟢 |
| 檢索未索引 | −14.64% | −13.83% | 708,188 | 清到波段新低（降為佳）🟢 |
| 週平均檢索數 | **+12.17%** | −26.30% | 843,476 | 爬蟲量回溫、反轉量縮 🟢 |
| GPT（工作階段） | +22.45% | +5.22% | 1,860 | AI 對話型領頭回穩 🟢 |
| 營運 KW：必買 | +18.20% | +6.61% | 526 | 節慶購物檔期 🟢 |
| 工作階段總數（七天） | +8.80% | +3.70% | 2,771,520 | 大盤回升 🟢 |
| 有效（Coverage） | +6.83% | −2.68% | 1,429,688 | 回填重新點火（月線未回高點）🟢 |
| Direct（工作階段） | +17.52% | −12.77% | 1,051,223 | 暴衝（需歸因檢核）🟢⚠️ |
| /tags/ | +9.60% | +57.75% | 17,456 | 策展頁需求加速 🟢 |
| 點擊 | +2.76% | +7.56% | 1,226,192 | 創波段新高 🟢 |
| CTR | +2.85% | −9.78% | 2.40% | WoW 止跌回升 🟢 |
| 手機 好 | −4.09% | +79.68% | 831,931 | CWV「好」桶守住（坐實非雜訊）🟢 |
| 曝光 | −0.09% | +16.53% | 51,052,986 | 守 5,100 萬量級 🟢 |

### 跨週對比（6/5 vs 6/19）

| 軸 | 6/5（上次 MP） | 6/19（本次） | 變化 |
|----|----------------|--------------|------|
| 週平均回應時間 | 694ms（+27.57%、連三週、新 P0） | **340ms（−20.56%）** | **P0 解除、腰斬 −51%** |
| 週平均檢索數 | 788,366（−7.29% W、月 −26.30%） | 843,476（+12.17% W） | **爬蟲量回溫** |
| 有效 Coverage | 1,542,469（+0.58% W、月 +29.97%） | 1,429,688（+6.83% W、月 −2.68%） | **WoW 回填、月線水位待補** |
| 檢索未索引 | 735,583（−6.60%） | 708,188（−14.64%） | **清到波段新低** |
| 曝光 | 51,891,586（+7.64%、月 +11.46%） | 51,052,986（−0.09%、月 +16.53%） | **守高檔、月線續強** |
| 點擊 / CTR | 1,210,692（+1.95%）/ 稀釋 | 1,226,192（+2.76%）/ +2.85% | **轉換回補、CTR 翻紅** |
| Perplexity / Gemini | 325 / 208（月 −174% / −111%） | 184 / 149（月 −216% / −135%） | **續崩、月線加劇** |
| 內部連結（每頁） | 14 | 11.86（月 −26.12%） | **入口基礎弱化** |
| May Core Update | 完成（6/2） | 後續波動（6/15–17 + 6/19 不明更新） | **重新評估期** |
| B7 Authority | DR 76 / AS 65（CF 6/2） | DR 76 / AS 65（CF 6/2，≤30 天） | **沿用** |

---

## Section 2：業界最新動態

### Google 官方更新

**[ONGOING-W3→重新評估期] May 2026 Core Update 後續波動（6/15–17 + 6/19 不明更新）**

- [Search Engine Roundtable: Google Search Ranking Volatility Continues Into June 15th–17th](https://www.seroundtable.com/google-search-ranking-volatility-41523.html) — 6/15–17 連三天排名波動持續，與本站 Discover 檔期退潮（−9.09%）時點重疊。
- [Search Engine Roundtable: Google Search Ranking Unconfirmed Update Hits Friday June 19th](https://www.seroundtable.com/google-search-ranking-hits-black-hats-41541.html) — 6/19 觀察到不明更新、主打黑帽側，正常站衝擊低；本站若有小幅波動可歸因此處。
- **對本站意涵**：本週資料窗（6/13–6/19）正坐落於 May Core Update（6/2 完成）後的「重新評估期」。本站 Coverage 回升、爬蟲量回溫發生在核心更新後，需區分「核心更新重評後恢復信任（系統因素）」vs「回應時間修復帶動回填（網站因素）」兩種歸因 [4]。

<details>
<summary>[NEW] GSC 生成式 AI 效能報告 + GEO 官方指南（點擊展開）</summary>

- [Google Search Central: Introducing Search Generative AI performance reports in Search Console](https://developers.google.com/search/blog) — Search Console 新增「AI 生成結果成效報告」，可追蹤內容被 AI Overview 引用的曝光與點擊。**本站應優先開啟，量化 AI Mode 曝光是否彌補傳統 Click 流失**。
- [Search Engine Journal: Google's New AI Search Guide Calls AEO And GEO 'Still SEO'](https://www.searchenginejournal.com/googles-new-ai-search-guide-calls-aeo-and-geo-still-seo/575026/) — Google 官方確認 AEO/GEO 不是獨立學科、是傳統 SEO 延伸，強化現有 E-E-A-T 即可同時得益 [9]。
- [Google Search Central（6/15）: llms.txt 澄清](https://developers.google.com/search/updates) — Google 不需要 llms.txt 來索引，確認本站加 llms.txt 屬選配而非 SEO 必要項。

</details>

### 業界報導

**[NEW] AI 引用的核心訊號是品牌曝光度、不是反鏈數量（75,000 品牌研究）**

- [Search Engine Land: What new AI search data reveals about visibility and trust](https://searchengineland.com/new-ai-search-data-visibility-trust-480089) — 跨 ChatGPT / AI Mode / Google AI Overviews 的 75,000 品牌分析：**AI 引用與品牌曝光度（YouTube 曝光、網路提及）相關性最高（r=0.50–0.74）、與反鏈數量相關性最低（<0.30）**。
- [Search Engine Land: AI search adoption rises as consumer trust declines](https://searchengineland.com/ai-search-adoption-rises-consumer-trust-declines-study-480338) — 消費者對 AI 搜尋信任度 2025 年 82% → 2026 年 54%（−28pp），用戶平均跨 2.4 個平台驗證，AI referral 碎片化。
- **對本站意涵**：本站 DR 76（反鏈權威行業領先）vs AI 占比月線 −58.61%——研究精準解釋此分離：本站「有連結權威、缺品牌提及」，這是 AI 引用權威與連結權威脫鉤的領先訊號 [7][8]。

<details>
<summary>[ONGOING-W5] AI 引擎導流版圖：ChatGPT 主導、Perplexity 業界普遍下滑（點擊展開）</summary>

- [Search Engine Journal: Google Gemini Sends More Traffic Than Perplexity](https://www.searchenginejournal.com/google-gemini-sends-more-traffic-to-sites-than-perplexity-report/570714/) — SE Ranking 101,000+ 站：Gemini Nov–Jan 成長 115% 超越 Perplexity，但整體 AI referral 仍 <1% 總流量。
- **本週新發展**：本站 Perplexity 月線 −216% 與業界 Perplexity 普遍下滑同向（非本站個案），ChatGPT 仍佔 AI referral 約 80%——本站 GPT +22.45% 是真實正向訊號，說明 GPT 使用者正引用 vocus 內容 [6]。

</details>

### 關鍵字市場趨勢（Google Trends 驗證）

| 關鍵字 | 本站趨勢 | 市場趨勢 | 判斷 | 來源 |
|--------|---------|---------|------|------|
| KW: 股 | W −32.48% / M −23.91% | 台股 6 月初熱潮（COMPUTEX / 台積電股東會）已於月中回落 | **6/5 預測兌現：事件性高峰、月中回吐、非結構成長** | [台股 6 月利多](https://money.udn.com/money/story/5607/9537229) |
| KW: 影評/電影 | 影評 W +4.56% / M +101.61%；電影 M +93.10% | 6 月暑期新片檔期（玩具總動員 5、柯南）持續 | **檔期驅動、月線坐實、市場同步** | [2026 上映電影表](https://www.atmovies.com.tw/movie/next/) |
| KW: 必買 | W +18.20% / M +6.61% | 年中購物節（618）檔期 | **節慶購物驅動、事件性** | [SERoundTable June Recap](https://www.seroundtable.com/recap-06-19-2026-41534.html) |

### SERP Feature 偵測

| 關鍵字 | 觀察到的 SERP Feature | 對有機 CTR 的影響 | 來源 |
|--------|---------------------|-----------------|------|
| 影評/電影 | AI Overview + Video Carousel（暑期影視查詢影音版位強） | 影音版位分流文字 CTR，但本站 Video Appearance +83.48% 可承接 | [SERP Features 2026](https://searchengineland.com/geo-metrics-to-track-476642) |
| 產品/評測 | Product Snippet vs Merchant Listing 重分類 | 非購買頁改派 snippet，計數在兩報告間移轉 | [SEJ: Product Structured Data Docs](https://www.searchenginejournal.com/google-updates-product-structured-data-documentation/484813/) |

**判讀**：本週 SERP 端的關鍵不在關鍵字流失（娛樂 KW 月線全強），而在**結構化版位的重分類**——產品摘要 −19.71% 最可能是 Google 把 Product 文件拆為 product snippet（非購買頁）vs merchant listing（可購買頁），本站若被重判屬性會在 GSC 兩張報告間移轉計數，須交叉比對而非直接判 schema 故障 [15]。

### Off-Page Authority 指標（B7）

**[CF] 沿用 2026-06-02 取得值（≤30 天 carry forward，今日 6/22 距 6/2 為 20 天，未重新查詢）：**

| 指標 | 工具 | 取得值 | 備註 |
|------|------|--------|------|
| DR (Domain Rating) | Ahrefs | **76** | 沿用 6/2；8.1K 參考網域 ⭐ |
| AS (Authority Score) | Semrush | **65** | 沿用 6/2；17.87K 參考網域 ⭐ |
| Monthly Traffic | Semrush | **8.03M** | 沿用 6/2；台灣占 82.69% |
| DA (Domain Authority) | Moz | 無法取得 | Moz 已停免費公開查詢 |
| TF / CF | Majestic | 待補 | 距 6/2 滿 30 天（≈7/2）重查時補連結品質錨點 |

**核心判讀（carry forward）**：DR 76（行業領先）+ AS 65 vs AI 占比月線 **−58.61%**——「長期域權威強 vs 短期 AI 分發弱」分離持續。本週新增佐證：75,000 品牌研究證實「AI 引用 ∝ 品牌提及（r=0.50–0.74），∝ 反鏈（<0.30）」，從業界數據面坐實本站「有連結權威、無 AI 引用權威」的脫鉤 [7][8]。

---

## Section 3：深度根因假設

> 本週 ALERT_DOWN 14 項 + ALERT_UP 15 項，依根因分群為 6 群（H1–H6）。生命週期標注對齊前週（6/5）。

### H1：週平均回應時間自高點崩回 340ms、爬蟲量回升 [Validated → P0 解除]

**對應指標**（呼應 S1）：週平均回應時間 W −20.56%（**340ms**，←694←428）、週平均檢索數 W +12.17%（843,476）、檢索數/有效 W +5.00%、HTML 檢索/有效 W +5.02%

**假設 1（修復見效面）**：回應時間自 694ms（6/5）連兩段崩回 340ms，週平均檢索數隨即回升 +12.17%——6/5 報告「壓回回應時間 → 爬蟲預算釋放 → 爬蟲量回升」的因果鏈正向兌現，證實這是「把基礎設施債當第一要務」的決策正確 [1][3]。**【需顧問判斷】**——是否以近兩週上線紀錄 **比對** 回應時間 694→340ms 的回落起點、確認改善來源（CDN / 後端哪一項生效）並文件化，避免下次部署再推高 TTFB [2]？

**假設 2（月線滯後面）**：WoW 雖回溫，但週平均檢索數月線仍 −20.81%、Coverage 月線 −2.68%——回應時間修復的紅利需連續數週才傳導到月線水位，本週只是觸底回升第一週 [1][4]。**【可驗證】**——以 GSC 檢索統計 **檢查** 回應時間回落後爬蟲量月線是否在 2–3 週內轉正。

**假設 3（歸因混淆面）**：本週 Coverage 回升 +6.83% 同時受兩個變數驅動——回應時間修復（網站因素）+ May Core Update 後重新評估恢復信任（系統因素，6/15–17 仍波動）[B-SER][4]。**【需顧問判斷】**——是否同意「回應時間修復是主因、核心更新重評是助燃」，並在 6/26 確認核心更新紅利不回吐後才把回填定性為結構性？

### H2：引用型 AI（Perplexity/Gemini）月線加速崩、GPT 單引擎撐盤 [Updated → 加劇]

**對應指標**（呼應 S1）：Perplexity W −33.09% / M −216.01%（184）、Gemini W −23.98% / M −135.21%（149）、GPT W +22.45% / M +5.22%（1,860）、AI 占比 M −58.61%

**假設 1（業界普遍面）**：Perplexity 下滑是業界普遍現象（SE Ranking 101,000+ 站證實 Perplexity 整體下滑、ChatGPT 佔 AI referral ~80%）——本站 Perplexity 崩非個案，GPT +22.45% 才是本站真實正向訊號 [6]。**【可驗證】**——導入 GSC 生成式 AI 效能報告 **檢查** 本站在 AI Overview 的引用率與引用頁類型 [B-GSCAI]。

**假設 2（品牌訊號弱面）**：75,000 品牌研究證實「AI 引用 ∝ 品牌提及（r=0.50–0.74），∝ 反鏈（<0.30）」——本站 DR 76 卻 AI 占比月線 −58.61%，正是「有連結權威、缺品牌提及」的典型，這是內容品質/品牌曝光弱訊號的領先指標 [7][8]。顧問 Gene Hong「AI 導流低的網站，才是搜尋與 AI 都同時忽略的那群；AI 放大內容品質差異」[TS-AI1]。**【需顧問判斷】**——是否同意 GEO 的正解是「經營品牌網路提及（PR + 原創數據新聞 + YouTube 曝光）」而非站內內容量？

**假設 3（GEO 工具到位面）**：GSC AI 效能報告 + GEO 官方指南（AEO/GEO「仍是 SEO」）本月到位——AI 引用條件與 SEO 排名邏輯高度一致（結構清楚、回答完整、資訊可信）[9]。**【需顧問判斷】**——是否啟動 GEO 為 Q2 P0（連續第 5 週列待辦），用官方新報告建引用率 baseline、優先 Gemini（成長引擎）？

### H3：內部連結月線崩 26.12% vs 策展頁需求加速 [New Hypothesis]

**對應指標**（呼應 S1）：內部連結 M −26.12%（16,960,024，每頁 14→11.86）、/tags/ W +9.60% / M +57.75%、搜尋標籤占比 M +50.45%、文章占比 M −5.13%、KW 影評 M +101.61%

**假設 1（供需背離面）**：策展頁需求月線級放大（/tags/ +57.75%、搜尋標籤占比 +50.45%）、但內連供給月線級縮減（每頁內連 14→11.86）——策展頁高度依賴內連把爬蟲與權重導入，供給弱化會削弱收錄率與權重傳遞，形成「需求進來、頁面接不住」的漏接 [10][11]。**【可驗證】**——用 Screaming Frog **抓取** /tags/ 與 /salon/ 策展頁、**檢查** 孤島頁內連缺口、**驗證** 每頁內連推回 13 以上。

**假設 2（遷移期失效面）**：業界指出策展頁/標籤頁遷移期間若舊連結失效（4xx 或 redirect chain）會暫時削弱主題權威訊號——內部連結月線 −26.12% 可能含遷移期的連結斷裂 [B-IntLink][11]。**【可驗證】**——用 Screaming Frog **篩選** /tags/ 遷移路徑的 4xx 與 redirect chain，**修復** 為 301 並更新內鏈錨點。

**假設 3（策展價值面）**：顧問與 KB 均指策展型頁面（標籤頁 / 懶人包）是突破流量瓶頸的高 SEO 價值入口（財報狗以標籤頁突破全站 25% 流量）——本站策展需求正旺，正是補內連把策展價值兌現的窗口 [10][12]。**【需顧問判斷】**——是否把內連資源優先灌注娛樂類策展頁（影評月線 +101.61%）而非平均分配？

### H4：Discover/News 檔期退潮、核心更新後波動 [Updated → 退潮]

**對應指標**（呼應 S1）：Discover W −9.09% / M +20.90%（415,832）、News(new) W −23.36% / M −78.58%（909）、探索比例 W −8.61% / M +9.99%

**假設 1（檔期回吐面）**：News(new) 自 6/5 的 3,391 退到 909、Discover 自 6/12 高點回吐——院線/時事檔期視窗關閉，再現「News 暴起暴落」規律，屬脈衝紅利非常態 [13][14]。**【需人工確認】**——6/26 確認 Discover 月線（+20.90%）是否守正、或續探。

**假設 2（核心更新波動面）**：Discover 回吐時點與 6/15–17 核心更新後排名波動重疊——Discover 歷來對核心更新更敏感，本週退潮可能含核心更新重評的成分而非純檔期 [B-SER][14]。**【需顧問判斷】**——是否同意「Discover 退潮先當檔期 + 核心更新波動的混合、月線守正即不需介入」？

**假設 3（分發回站面）**：Discover/News 退潮但 Organic Search 守首位（月線 +9.90%）、工作階段 +8.80%——分發紅利退場後流量重心回到搜尋端，本站搜尋基本盤穩固 [13]。**【可驗證】**——用 GSC **篩選** Discover 高點到達頁，**檢查** 行動圖片規格，趁月線仍正鞏固到達頁體驗。

### H5：結構化資料「產品摘要」流失、疑 Google 重分類 [New Hypothesis]

**對應指標**（呼應 S1）：產品摘要 W −19.71% / M −34.35%（220）、評論摘錄 W −1.09% / M −4.25%（28,204，月線跌幅較 6/5 −33.87% 大幅收斂）、Video Appearance W +83.48%（2,877）

**假設 1（重分類面）**：業界證實 Google 已把 Product 文件拆為 product snippet（非購買頁 / 評論聚合）vs merchant listing（可購買頁）——本站若被重判屬性，會在 GSC 兩張報告間移轉計數造成「產品摘要」下滑，非必然是 schema 故障 [15][B-Product]。**【可驗證】**——在 GSC **比對** 「產品摘要」vs「商家資訊」兩張報告的交叉變化，**確認** 是重分類還是真失效。

**假設 2（Review 止血面）**：評論摘錄月線跌幅從 6/5 的 −33.87% 收斂到 −4.25%——上週的 Review schema 系統性失效本週止穩，結構化漏點本週移轉到 Product/Offer 類型 [15]。**【可驗證】**——在 GSC「結構化資料 → Product」**檢查** price/availability 欄位完整性。

**假設 3（影視結構化走強面）**：Video Appearance +83.48%（月線 +224.47%）與產品摘要下滑背離——影視結構化版位走強、商品結構化走弱，反映本站內容重心（娛樂 vs 商品）的結構化收錄差異 [15]。**【需顧問判斷】**——是否把結構化資源優先投向走強的影視版位（承接娛樂檔期）而非衰退的商品版位？

### H6：核心軸守成 + 轉換回補、曝光月線續強 [Validated → 守成]

**對應指標**（呼應 S1）：曝光 W −0.09% / M +16.53%（51,052,986）、點擊 W +2.76% / M +7.56%（1,226,192）、CTR W +2.85% / M −9.78%、有效 Coverage W +6.83%

**假設 1（守成面）**：曝光守在 5,100 萬量級（月線 +16.53%）——回答 6/5「曝光能否守住」之問，守住了；點擊與 CTR 跑在曝光之前，上週「CTR 稀釋」漏點收斂 [16][17]。**【可驗證】**——用 GSC **篩選** 月線曝光增但點擊未跟漲查詢，**重寫** title / **優化 description** 趁 CTR 翻紅再撈一段。

**假設 2（辛普森校準面）**：曝光月線 +16.53% 但 CTR 月線仍 −9.78%——須以「總曝光 + 有效關鍵字數」並看，避免被單一比值誤導（辛普森悖論）[20]。**【需人工確認】**——CTR 月線負是否為「索引更多長尾、平均稀釋」而非真實惡化？

**假設 3（歸因健康面）**：Direct 暴衝 +17.52% 但「GSC 搜尋/GA 搜尋」比值 0.89 穩定、「GSC 探索/GA Direct」比值異常 −22.64%——搜尋端歸因健康，但 Discover 點擊疑被剝離 referrer 錯歸 Direct [18]。**【可驗證】**——在 GA4 **檢查** Direct 到達頁與裝置構成，**驗證** 是否為分發流量錯歸。

---

## Section 4：顧問視角交叉比對

| 狀態 | 主題 | KB 觀點 | 顧問文章觀點 | 指標數據 | 業界動態 | 判斷 |
|------|------|---------|-------------|---------|---------|------|
| [CF] | 回應時間修復、爬蟲回溫 | KB [1][3] 回應時間與流量強烈負相關、釋放爬蟲預算 | Gene Hong「Crawler Stats 回應資料表看 Cache/CDN 健康度」[TSC1] | 回應時間 W −20.56%（340ms）、檢索數 +12.17% | 核心更新後重評期、6/15–17 波動 [B-SER] | P0 解除、因果鏈兌現；月線水位待補、6/26 確認 |
| [NEW] | 內部連結崩 vs 策展需求升 | KB [10][12] 標籤頁突破流量瓶頸的策展工具 | Gene Hong 懶人包/策展頁高 SEO 價值、需內連導權重 [TS-TAG] | 內連 M −26.12%（每頁 14→11.86）vs /tags/ M +57.75% | 內鏈一致性是 AI/Google 推主題權威核心訊號 [B-IntLink] | 供需背離、本週 💡；遷移期補 301 + 內連 |
| [Updated] | 引用型 AI 崩、GEO 品牌曝光 | KB [7][8] AI 偏好大站 + branded mentions → AI visibility | Gene Hong「AI 放大內容品質差異、AI 導流低＝被雙重忽略」[TS-AI1] | Perplexity/Gemini 月線崩 vs GPT +22.45% | 75K 研究：AI 引用 ∝ 品牌提及 r=0.50–0.74、∝ 反鏈 <0.30 [B-AIvis] | GEO 升 Q2 P0；經營品牌提及非站內量、優先 Gemini |
| [NEW] | 產品摘要流失疑重分類 | KB [15] 結構化資料格式與收錄判讀 | — | 產品摘要 W −19.71% / M −34.35% | Google 拆 Product 為 snippet vs merchant listing [B-Product] | 先查 GSC 兩報告交叉、非直接判 schema 故障 |
| [CF] | 核心軸守成、CTR 翻紅 | KB [16][17] CTR 下降是好事、TDK 變動影響點擊 | Gene Hong「SEO KPI 不是排名」[TS-KPI] | 曝光守 5,100 萬、點擊 +2.76%、CTR +2.85% | May Core Update 後重評期 | 守成期、轉換回補；趁 CTR 翻紅撈高曝光低點擊頁 |
| [Updated] | Discover/News 檔期退潮 | KB [13][14] Discover 助燃、死灰復燃需新社群訊號 | Gene Hong「涵蓋範圍分系統因素 vs 網站因素」[TS-CV] | Discover W −9.09%（M +20.90%）、News −23.36% | Discover 對核心更新更敏感、6/15–17 波動 | 檔期 + 核心更新混合、月線守正即不介入 |
| [CF] | B7 長期權威 vs 短期分發分離 | KB [7][8] organic/品牌 → AI mentions | Gene Hong「AI 導流低＝被雙重忽略」[TS-AI1] | DR 76 / AS 65 vs AI 占比 M −58.61% | AI 引用 ∝ 品牌提及非反鏈 [B-AIvis] | 有連結權威無 AI 引用權威、脫鉤；carry forward 6/2 |

---

## Section 5：五層審計缺口清單

| 層級 | 類型 | 描述 | 缺口現況 | 優先度 | SITREP |
|------|------|------|---------|--------|--------|
| **L1 技術層** | 回應時間崩回 340ms、爬蟲回溫 | W −20.56%、340ms、檢索數 +12.17% [1][3] | **P0 解除**、待文件化改善來源 | 🟢 正向（鎖定） | [Validated, P0 解除] |
| **L1 技術層** | 索引三鏈回填、月線水位待補 | Coverage W +6.83%（M −2.68%）、未索引波段新低 708k [4] | 月線未回 6/5 高點、待傳導 | 🟢 正向（觀察） | [Validated, WoW 回填] |
| **L1 技術層** | 駭客風險排除（採樣未索引 URLs） | 未索引降至 708,188 但絕對量仍逾 70 萬、未排除被駭注入 [4] | **P0+、連續第 8 週未執行** | 🔴 紅線級 | [CARRY-W8, 連續未執行] |
| **L1 技術層** | 手機 CWV「好」桶守住 | 手機好 831,931（M +79.68%）守住、坐實非雜訊 [5] | 殘留「中」17,708 待收乾 | 🟢 正向 | [Validated, 守住] |
| **L2 內容層** | 內部連結月線崩 vs 策展需求升 | 內連 M −26.12%（每頁 14→11.86）vs /tags/ M +57.75% [10][11] | **供需背離、入口基礎弱化** | 🔴 高 | [NEW, 本週 💡] |
| **L2 內容層** | 引用型 AI 崩、GEO 未啟動 | Perplexity/Gemini 月線崩、GSC AI 報告到位 [7][8] | GEO 策略未啟動（工具已到位） | 🔴 高 | [CF-W5, 工具到位] |
| **L2 內容層** | Discover/News 檔期退潮 | Discover −9.09%（M +20.90%）、News −23.36% [13][14] | 檔期 + 核心更新波動混合 | 🟡 中 | [Updated, 退潮] |
| **L3 內容品質層** | CTR 翻紅但月線仍負 | CTR W +2.85% / M −9.78%、曝光月線 +16.53% [16][17] | 高曝光低點擊頁 title 重寫未啟動 | 🟡 中 | [CF, 翻紅] |
| **L4 結構化資料層** | 產品摘要流失疑重分類 | 產品摘要 M −34.35%、Google 拆 Product 文件 [15] | GSC 兩報告交叉比對未做 | 🟡 中 | [NEW, 疑重分類] |
| **L4 結構化資料層** | 影視結構化走強 vs AMP Article 萎縮 | Video Appearance +83.48% vs AMP Article −48.65% | 混合（影視承接娛樂檔期） | 🟡 中 | [Updated, 分化] |
| **L4 連結層** | 連結生態錨點（carry forward） | DR 76 / 8.1K 參考網域，TF/CF 待補 | 錨點沿用、品質未驗 | 🟢 正向 | [CF, 沿用 6/2] |
| **L5 分發層** | Direct 暴衝、歸因檢核 | Direct +17.52%、GSC 探索/GA Direct 比值 −22.64% [18] | 疑 Discover 錯歸 Direct、未驗證 | 🟡 中 | [Updated, 需檢核] |
| **L5 分發層** | GEO / AI 可見度經營 | AI 占比 M −58.61%、GSC AI 報告 + GEO 指南 [7][9] | Brand Radar + GSC AI 報告 baseline 未啟動 | 🔴 高 | [CARRY-W8, 工具到位待啟動] |

---

## Section 6：E-E-A-T 現況評估

**Changed this week:**

| 維度 | 分數 | 變化 | 原因 |
|------|------|------|------|
| Trustworthiness | **3/5 ↑** | +0.5 | 6/5 設「升 3 條件：回應時間壓回 < 500ms + 駭客排除完成」——本週回應時間崩回 340ms（< 500ms 達標），解除「基礎設施債封印信任紅利」的狀態；惟駭客採樣連續第 8 週未做，故升 3 而非更高，駭客排除是升 3.5 的唯一剩餘閘門 [1][4] |

<details>
<summary>No Change（3 維度，點擊展開上週評估）</summary>

| 維度 | 分數 | 上週依據（carry forward）+ 本週註記 |
|------|------|------------------------|
| Experience | 3/5 | UGC 多元觀點持續、Information Gain 結構性不足未改變。本週娛樂 KW 月線強屬市場需求驅動非第一手經驗；強化方向仍為作者頁 Profile Page 結構化（且 /user 本週 −20.25%，作者頁體質待強化）[19] |
| Expertise | 3/5 | 技術 SEO 知識庫豐富、個別作者深度不一。本週無新結構性變化，維持 |
| Authoritativeness | 4/5 | **沿用 6/2 B7 錨點**（DR 76 ≥70 / AS 65，≤30 天未重查）。長期權威強 vs AI 分發弱（AI 占比 M −58.61%）分離持續。升 5 條件：AI 引用率回升 + 品牌提及成長 [7][8] |

</details>

**Authoritativeness 評分客觀錨點（B7 carry forward）**：

- DR 76（≥70→錨點 5）+ AS 65（50–70→錨點 4）→ 加權約 4.5，因短期 AI 分發弱維持 **4**（沿用 6/2，未重查）
- **矛盾標記**：DR/AS（長期反向連結權威）強 vs AI 占比 M −58.61%（短期分發認可）弱——「短期擾動 vs 長期權威分離」持續；本週業界 75K 研究（AI 引用 ∝ 品牌提及非反鏈）從外部佐證此分離成因 [8]
- 下次 B7 重查（距 6/2 滿 30 天，≈7/2）補 TF/CF（Majestic）確認連結品質

**E-E-A-T 平均**：上週 3.13 → 本週 **3.25**（+0.12，Trustworthiness 2.5→3）

**核心判讀**：本週 T 維度終於從 2.5 升 3，是「回應時間 P0 解除」的直接成果——6/5 報告診斷「基礎設施債正在封印內容/索引面的信任紅利」，本週回應時間崩回 340ms 把這個封印解除，索引面的改善（Coverage 回填）終於能反映到信任維度。但 E-E-A-T 仍受限於 Experience/Expertise 的結構性瓶頸（作者深度、第一手經驗），這兩維是下一階段的天花板。

---

## Section 7：人本七要素分析

**Changed this week:**

| 要素 | 上週分數 | 本週分數 | 變化 | 依據 |
|------|---------|---------|------|------|
| 技術體質 | 3/5 | **4/5 ↑** | +1.0 | 6/5 明設「若回應時間壓回可升 4」——本週回應時間崩回 340ms（W −20.56%）、爬蟲量回升 +12.17%、手機 CWV「好」桶守住，使用者端與爬蟲端體驗首次同向健康，技術體質的正負相抵狀態解除、升 4。升 5 條件：月線爬蟲量轉正 + 駭客採樣完成 [1][5] |

<details>
<summary>No Change（6 要素，點擊展開上週評估）</summary>

| 要素 | 分數 | 上週依據（carry forward）+ 本週註記 |
|------|------|------------------------|
| 網站人格 | 3/5 | UGC 平台定位清晰；本週娛樂（影評）需求強化內容人格但未改結構，維持 |
| 內容靈魂 | 2/5 | 引用型 AI 續崩（Perplexity 月線 −216%）仍是內容品質弱訊號；75K 研究證實 AI 引用靠品牌提及非反鏈，本站缺「被提及的靈魂」，維持 2/5 列觀察 [7][TS-AI1] |
| 使用者旅程 | 3/5 | Organic 守首位、工作階段 +8.80%（管道穩），但 Direct 暴衝疑分發錯歸（比值 −22.64%）；混合維持 3/5 [18] |
| 連結生態 | 4/5 | **沿用 6/2 B7**：DR 76 + 8.1K 參考網域（健康）。但本週內連月線 −26.12%（每頁 14→11.86）是站內連結的反向訊號，外部健康 vs 內部弱化並存，維持 4 但標警示 [11] |
| 資料敘事 | 4.5/5 | 6/5 的「預測對帳」能力延續——本週把「回應時間壓回 → 爬蟲回升」的預測兌現拿來驗證，是可證偽敘事的閉環；維持 4.5 |
| 趨勢敏銳度 | 4.5/5 | 本週正確辨識核心更新後重評期、引用型 AI 業界普遍下滑（非個案）、產品摘要疑重分類；維持 4.5 |

</details>

**連結生態（Link Ecosystem）評分客觀錨點（B7 carry forward）**：DR 76（≥60→錨點 5）+ 參考網域 8.1K–17.87K（充足），維持 **4**（沿用 6/2）；下調至 4 因 TF/CF 未取得無法確認 trust 品質，且本週內連月線 −26.12% 為站內結構反向訊號。**S6 vs S7 差異**：S6 Authoritativeness 評「外部如何看本站」（DR/AS 強→4），S7 連結生態評「連結結構是否健康」（外部反鏈健康但站內內連弱化→維持 4 標警示），同一份數據從不同角度解讀、不重複扣分。

**人本七要素平均**：上週 3.43 → 本週 **3.57**（+0.14，技術體質 3→4）

**核心判讀**：本週 +0.14 全來自「技術體質」——與 S6 的 Trustworthiness 升級同源（回應時間 P0 解除）。值得注意的是「連結生態」維持 4 卻內含分裂：外部反鏈健康（DR 76）vs 站內內連月線崩 26.12%——這個「外健內弱」的張力是本週新浮現、需在下階段獨立追蹤的結構訊號。

---

## Section 8：SEO 成熟度自評

**本週四維度均 No Change**——說明如下（必填）：本週的進展（回應時間 P0 解除、因果鏈驗證、產品摘要重分類辨識）屬「執行品質 + 預測對帳」的延續，尚未轉化為「制度化能力」——自動 alerting、Crawl Budget API / GSC AI 報告實際導入、Brand Radar 週級追蹤均未落地，故四維度維持。**P0 解除是成果、不是制度**：把「回應時間壓回」變成「回應時間 > 500ms 自動告警」才是 L3→L4 的制度化。

<details>
<summary>No Change（4 維度，點擊展開上週評估）</summary>

| 維度 | 等級 | 上週依據（carry forward）+ 本週註記 |
|------|------|------------------------|
| Strategy（策略）| L2.5（L2→L3 邊緣）| Plan B（影視 α / GEO γ）仍未實際啟動；本週內連 vs 策展供需背離 + 引用型 AI 崩提供 Plan B 新素材，但尚未決策。升 L3：Plan B 至少一方向實際啟動 + 量化 KPI |
| Process（流程）| L3 | 危機應對仍依賴每週手動審核；回應時間 P0 本週靠人工排查解除（非自動 alerting）。升 L4：回應時間 > 500ms 自動告警 + GSC AI 報告導入流程 |
| Keywords（關鍵字）| L3 | 本週 KW 分析（股回吐驗證、娛樂月線坐實、必買檔期）具 L4 雛形但仍手動。升 L4：SERP feature 細分追蹤 + Brand Radar 引用率 [20] |
| Metrics（指標）| L3.5 | 本週能做預測對帳（回應時間→爬蟲量因果驗證）+ 產品摘要重分類辨識，歸因能力強，維持 L3.5。升 L4：GSC API + Crawl Budget API 自動抓取 + 閾值 alerting |

</details>

**成熟度概覽**：Strategy L2.5 / Process L3 / Keywords L3 / Metrics L3.5——與上週持平。本週「P0 靠人工解除」恰恰凸顯 Process 的 L3 天花板：能在危機後正確排查（執行品質高），但缺「危機前自動預警」（制度化缺）。**把本週手動排查的回應時間流程沉澱為自動 alerting = Process L3→L4 的最具體路徑。**

---

## Section 9：會議提問清單（核心輸出）

### A 類：確認事實（4 題）

**A1 [Validated]（前週 A1 carry，本週解除）**：上週列為唯一 P0、連三週飆破 600ms 的**週平均回應時間**本週崩回 **340ms（週線 −20.56%）**、週平均檢索數隨即回升 +12.17%——是否已確認改善來源（CDN / 後端哪一項生效）並文件化，避免下次部署重蹈覆轍 [1][3]？

**A2 [CARRY-W8]（前週 A3 carry，連續第 8 週）**：採樣 50–100 個**檢索未索引** URLs 確認合法 vocus 路徑而非被駭注入——**連續第 8 週未取得答案**。本週未索引降至 708,188 但絕對量仍逾 70 萬。是否本週指派獨立 owner 在 GSC **採樣** 完成（這也是 T 維度升 3.5 的唯一剩餘閘門）[4]？

**A3 [NEW]**：本週**內部連結**月線 **−26.12%**（每頁內連 14→11.86），同期 /tags/ 月線 +57.75% 需求加速——是否已用 Screaming Frog **檢查** 策展頁遷移期是否有舊連結失效（4xx / redirect chain）拉低內連密度 [10][11]？

**A4 [Updated]（前週 A4 演進）**：本週 **Direct 暴衝 +17.52%**、但「GSC 探索/GA Direct」比值異常 −22.64%——是否確認此暴衝含 Discover 點擊被剝離 referrer 錯歸 Direct 的成分（而非真實直接流量成長）[18]？

### B 類：探索判斷（5 題）

**B1 [NEW]**：本週 **內部連結基礎崩 26.12% vs 策展頁需求升 57.75%** 是最大供需背離——是否同意把本週資源優先灌注「補回娛樂類策展頁（影評月線 +101.61%）的內連密度到 13 以上」，而非平均分配 [10][12]？

**B2 [CARRY-W5]（前週 B2 carry）**：**引用型 AI 月線崩**（Perplexity −216% / Gemini −135%）vs GPT +22.45%。業界 75K 研究證實「AI 引用 ∝ 品牌提及（r=0.50–0.74）∝ 反鏈（<0.30）」——是否啟動 GEO 為 Q2 P0，且路徑改為「經營品牌網路提及（PR + 原創數據新聞 + YouTube 曝光）」而非站內內容量，並用 GSC AI 效能報告建 baseline [7][8]？

**B3 [NEW]**：**產品摘要 −19.71%（月線 −34.35%）**——業界證實 Google 已拆 Product 文件為 snippet（非購買頁）vs merchant listing（可購買頁）。是否同意「先在 GSC 比對兩張報告的交叉變化、確認是 Google 重分類而非 schema 故障」再決定是否投工程修復 [15]？

**B4 [CARRY-W7]（前週 B4 carry）**：**Plan B 主軸選擇**連續第 7 週——本週素材：影視（影評月線 +101.61%、Video Appearance +83.48%）、GEO（官方工具到位 + 品牌提案）、內連修復（策展供需背離）三選項。是否本週正式拍板主軸並分配資源 [TS-AIM]？

**B5 [Updated]（前週 B5 演進）**：**Coverage 回升 +6.83%** 同時受「回應時間修復（網站因素）+ May Core Update 後重評（系統因素，6/15–17 仍波動）」驅動——是否同意「6/26 確認核心更新紅利不回吐後才把回填定性為結構性」（涵蓋範圍系統因素 vs 網站因素）[TS-CV][4]？

### C 類：挑戰假設（3 題）

**C1 [NEW]**：本週把 P0 從「回應時間」（已解除）改列為「內部連結基礎」——但內連月線 −26.12% 屬**月線**訊號（WoW 其實 0.00% 持平），不是急性惡化。**既然 WoW 已止穩，把 P0 給內連是否反應過度？是否應把唯一 P0 留給連續第 8 週未做的駭客採樣**（風險性質：資安 > 流量結構）？

**C2 [CARRY-W2]（前週 C2 演進）**：上週質疑「顧問會議價值正從『改善網站』轉為『改善分析』」——本週 E-E-A-T +0.12、人本 +0.14 **全來自回應時間 P0 解除這一個事件**，網站本體 E-E-A-T（Experience/Expertise）仍卡關。**這是否意味本站的成長已高度依賴「修復既有惡化」、而非「創造新能力」**？若是，下一階段該如何從「止血」轉向「創高」？

**C3 [NEW]**：本週「連結生態」維持 4 分，但內含「外部反鏈健康（DR 76）vs 站內內連崩（每頁 14→11.86）」的分裂——**我們用一個分數掩蓋了內外背離**。是否該把「連結生態」拆為「外部連結權威」與「站內連結結構」兩個獨立子維度，避免外部強掩蓋內部弱 [11]？

### D 類：業界趨勢（2 題）

**D1 [NEW]**：業界 75,000 品牌研究證實「**AI 引用與品牌網路提及相關性最高（r=0.50–0.74）、與反鏈數量最低（<0.30）**」、消費者 AI 信任度 2026 年降至 54%——本站 DR 76 卻 AI 占比月線 −58.61%。是否同意「本站的 AI 能見度瓶頸不在連結、在品牌被提及的場景太少」，並把 GEO 重心放在製造「被提及」（原創數據 + 媒體 co-citation）[7][8]？

**D2 [CARRY-W3]（前週 D2 carry）**：Google 官方確認「**AEO/GEO 仍是 SEO**」、AI 引用條件與 SEO 排名邏輯高度一致（結構清楚 + 回答完整 + 可信）[9]——顧問「AI x SEO 重點在用人不用 AI、Human in the Loop、累積而非佔位」[TS-AIM]。是否同意 GEO 不需另起爐灶、強化現有 E-E-A-T + 結構化 Q&A 即可同時得益，避免投入重複工具 [9]？

---

## Section 10：會議後行動核查表

| 優先度 | 行動（含工具名 + 動作動詞 + 成熟度標籤） |
|--------|----------------------------------------|
| 🔴 P0 | 在 **Screaming Frog** **抓取** /tags/ 與 /salon/ 娛樂類策展頁、**檢查** 內連從 14 掉到 11.86 的缺口頁與遷移期 4xx/redirect chain，對缺口頁 **加入** 標籤導讀內連 5–10 條 + **修復** 失效連結為 301，**驗證** 每頁內連推回 13 以上 — **[L2 內容 L3→L3]** |
| 🔴 P0+ | 在 **GSC「已檢索但未編入索引」** **採樣** 50–100 個 URLs **確認** 全為合法 vocus 路徑而非被駭注入（連續第 8 週 carry、指派獨立 owner）— **[L1 技術 L2→L3]** |
| 🔴 P1 | 導入 **GSC 生成式 AI 效能報告** **建立** vocus.cc 在 AI Overview 的引用率 baseline，**對比** GPT/Gemini/Perplexity 引用頁類型，**驗證** 引用型雙引擎崩是否全引擎被擠出 — **[L4 指標 L3→L4]** |
| 🔴 P1 | 在 **內部監控系統** **建立** 回應時間 > 500ms 自動告警（把本週手動解除的 P0 制度化），**設定** 週環比 ±15% 觸發 Slack，**驗證** 下次部署 TTFB 不回吐 — **[Process L3→L4]** |
| 🟡 P2 | 在 **GSC** **比對** 「產品摘要」vs「商家資訊」兩張結構化報告的交叉變化，**確認** −19.71% 是 Google 重分類（product snippet vs merchant listing）還是 schema 故障，**修復** 對應欄位 — **[L4 結構化 L3→L3]** |
| 🟡 P2 | 在 **GSC「成效 → 查詢」** **篩選** 月線曝光增但點擊未跟漲的查詢 Top-30（趁 CTR 翻紅 +2.85%），**重寫** title 並 **優化 description** 補時事關鍵字 + 數字 — **[L2 內容 L2→L3]** |
| 🟡 P2 | 在 **GA4** **檢查** Direct 暴衝 +17.52% 的到達頁與裝置構成（GSC 探索/GA Direct 比值 −22.64%），**驗證** 是否 Discover 流量錯歸 Direct — **[L5 分發 L3→L3]** |
| 🟡 P3 | 在 **Ahrefs Brand Radar** **檢查** 「vocus + 核心 KW」在 Perplexity/Gemini 的被引用率與品牌提及缺口，對缺口主題 **補上** 原創數據與事實摘要段（業界證實 AI 引用 ∝ 品牌提及）— **[L2 內容 L3→L4]** |
| 🟡 P3 | 在 **Majestic** **查詢** vocus.cc 的 TF/CF 補全 B7 連結品質錨點（距 6/2 滿 30 天≈7/2 時），**補錄** `data/off-page-authority.jsonl`，**驗證** TF/CF > 0.8 — **[L4 指標 L3→L4]** |
| 🟢 P4 | 在 **GSC「成效 → Discover」** **篩選** 自高點回吐 −9.09% 的到達頁，**檢查** 行動圖片規格，趁月線仍 +20.90% **加入** 高解析圖片鞏固分發端 — **[L5 分發 L3→L3]** |

> ℹ️ **回應時間 P0 解除（本週最大成果）**
> 上週列為唯一 P0、連三週飆破 600ms（694ms）的回應時間，本週崩回 340ms（−20.56%）、爬蟲量隨即回升 +12.17%。6/5「壓回 → 回填重新點火」的因果鏈正向兌現。**後續重點轉為「鎖死改善 + 制度化告警」**（見 P1），避免下次部署再推高 TTFB。前端歸屬不變：手機「好」桶守住證實前端資源載入已最佳化，回應時間由 TTFB（後端/CDN）主導，勿誤派前端。

**成熟度參考**：本期四維度持平（Strategy L2.5 / Process L3 / Keywords L3 / Metrics L3.5）。本週 P0 靠人工解除，凸顯 Process L3 天花板；若 P1（回應時間自動告警 + GSC AI 報告導入）落地 + 駭客採樣完成，可同步推進 Process L3→L4 與 Metrics L3.5→L4——**把本週的手動排查沉澱為自動制度是本季 L3→L4 的最具體槓桿。**

---

## Appendix：顧問文章引用

**Gene Hong「AI 導流越高，搜尋流量越上升？一個被誤解的流量悖論」（2025-12-10）**[TS-AI1]
- 「AI 導流低的網站，才是搜尋與 AI 都同時忽略的那群」「AI 並沒奪走誰的流量，它只是放大內容品質的差異」「越是焦慮 AI 的網站，往往越是 SEO 基本功沒做好的網站」
- 對應本週 H2：本站 AI 占比月線 −58.61% + DR 76 域權威分離——業界 75K 研究（AI 引用 ∝ 品牌提及非反鏈）從外部坐實「有連結權威、無 AI 引用權威」
- 來源：[genehong.medium.com](https://genehong.medium.com/ai-導流越高-搜尋流量越上升-一個被誤解的流量悖論-db8048a798a8)

**Gene Hong「AI x SEO 的幾個重要迷思與方法論」（2025-08-31）**[TS-AIM]
- 「AI x SEO 的重點不在如何使用 AI，而是如何使用人」「Human in the Loop 最重要」「選擇累積而非佔位」
- 對應本週 H2/B4：GEO 正解不是量產內容，而是人本要素 + HITL + 與權威媒體 co-citation
- 來源：[genehong.medium.com](https://genehong.medium.com/ai-x-seo-的幾個重要迷思與方法論-c99944849826)

**Gene Hong「Google Search Console 對涵蓋範圍等改版的重點提示」（2022-08-18）**[TS-CV]
- 「涵蓋範圍把原因分成網站因素與爬蟲因素；Google 系統造成的未索引才是該注意的」
- 對應本週 H1/H4/B5：Coverage 回升 + Discover 退潮需區分「核心更新重評（系統因素）vs 回應時間修復（網站因素）」
- 來源：[genehong.medium.com](https://genehong.medium.com/google-search-console-對涵蓋範圍等改版的重點提示-930928786ac9)

**Gene Hong「新媒體經營的全面手冊」+「標籤頁策展」KB 觀點**[TS-TAG]
- 「懶人包/策展頁匯聚多元關鍵字與連結、容易成為搜尋主要入口，具高 SEO 價值；但需持續更新 + 內連導權重」；財報狗以標籤頁突破全站 25% 流量
- 對應本週 H3：策展頁需求月線 +57.75% 旺盛，但內連月線 −26.12% 削弱權重傳遞，須補內連兌現策展價值
- 來源：raw_data/medium_markdown（genehong-medium）+ KB [10][12]

**Gene Hong「SEO KPI 的幾個調校角度（若 SEO 公司說 KPI 是排名請轉頭就走）」**[TS-KPI]
- 「SEO KPI 不該是排名」——應看曝光/點擊/CTR/索引等綜合健康度
- 對應本週 H6：曝光守 5,100 萬 + 點擊 +2.76% + CTR +2.85% 的綜合守成，勝過單看排名
- 來源：raw_data/medium_markdown（genehong-medium）

---

<!-- meeting_prep_meta {"date": "2026-06-19", "generated_at": "2026-06-22T00:00:00.000Z", "input_source": "output/report_20260619_dc74c632.md", "prev_report": "meeting_prep_20260605_0910d58b.md", "alert_down": 14, "industry_items": 17, "kb_citations": 20, "consultant_articles": 5, "eeat_avg": 3.25, "humanistic_avg": 3.57, "maturity": {"strategy": "L2.5", "process": "L3", "keywords": "L3", "metrics": "L3.5"}, "off_page_authority": {"dr": 76, "as": 65, "monthly_traffic": 8030000, "source": "carry-forward 2026-06-02"}, "core_update": "May 2026 Core Update completed 2026-06-02; post-update volatility 6/15-17 + unconfirmed 6/19", "key_event": "P0(回應時間)解除694->340ms因果鏈兌現 + 內連月線-26.12%新P0供需背離 + 引用型AI崩業界證實非個案 + 產品摘要疑重分類 + T維2.5->3技術體質3->4"} -->

<!-- citations [{"n": 1, "id": "dc73787fc2e911a3", "category": "索引與檢索", "title": "Search Console 的 42 個數字 - 回應時間與流量最相關", "date": "", "snippet": "檢索回應時間與流量呈現強烈負相關，是整個 KPI 表中最重要的數值之一；回應時間越久流量越低", "chunk_url": "/admin/seoInsight/dc73787fc2e911a3", "source_url": null}, {"n": 2, "id": "5778f6e414607e0a", "category": "技術SEO", "title": "SEO 會議_2024/06/24 - 回應時間異常根因", "date": "2024-06-24", "snippet": "回應時間上升可能影響 Core Web Vitals 分數及 Googlebot 爬取效率；以時間軸對比部署紀錄與回應時間上升起點找關聯", "chunk_url": "/admin/seoInsight/5778f6e414607e0a", "source_url": null}, {"n": 3, "id": "2e07b54b344c219e", "category": "搜尋表現分析", "title": "SC 27 KPI (27.5) - 回應時間 SEO KPI 價值", "date": "", "snippet": "回應時間與 SEO 流量呈現強烈負相關；過長回應時間限制爬蟲在有限資源內爬取的頁面數", "chunk_url": "/admin/seoInsight/2e07b54b344c219e", "source_url": null}, {"n": 4, "id": "81c32da0e940147b", "category": "索引與檢索", "title": "SEO 會議_20260223 - 有效頁需搭流量頁觀察", "date": "2026-02-23", "snippet": "有效頁面數下降本身不代表索引惡化，需搭配流量頁面數同步觀察；排除式上升屬正向", "chunk_url": "/admin/seoInsight/81c32da0e940147b", "source_url": null}, {"n": 5, "id": "6bd1e3242c2f381f", "category": "技術SEO", "title": "SEO 會議_2024/08/12 - SC CLS 群組判斷 CWV 改善", "date": "2024-08-12", "snippet": "觀察 Search Console 中 CLS 群組的記錄數量而非分數高低，群組數字降低表示問題範圍縮小", "chunk_url": "/admin/seoInsight/6bd1e3242c2f381f", "source_url": null}, {"n": 6, "id": "f0df121f7ebe928f", "category": "演算法與趨勢", "title": "SEO 會議_20251027 - GA4 追蹤 AI 來源流量", "date": "2025-10-27", "snippet": "在 GA4 探索報告加入工作階段來源/媒介維度，手動搜尋 GPT/Gemini/Perplexity 記錄佔總流量比例", "chunk_url": "/admin/seoInsight/f0df121f7ebe928f", "source_url": null}, {"n": 7, "id": "f3871925c18fccb3", "category": "演算法與趨勢", "title": "Google Seems More Biased Towards Big Brands - AI 偏好大站", "date": "", "snippet": "Google 在品牌呈現上長期更偏向大品牌，其他 AI 助手可能沒有相同內建偏好", "chunk_url": "/admin/seoInsight/f3871925c18fccb3", "source_url": null}, {"n": 8, "id": "2533db03cde52dc0", "category": "演算法與趨勢", "title": "Google Seems More Biased Towards Big Brands - branded mentions 與 AI visibility", "date": "", "snippet": "在 Google AI Overviews 中 branded web mentions 與 AI visibility 呈現明顯較強正相關", "chunk_url": "/admin/seoInsight/2533db03cde52dc0", "source_url": null}, {"n": 9, "id": "f3f313aa83d67851", "category": "搜尋表現分析", "title": "AI Search 引用條件與 SEO 排名邏輯一致", "date": "", "snippet": "AI Search 選擇引用的條件與 Google SEO 排名邏輯高度一致：結構清楚、回答完整、資訊可信", "chunk_url": "/admin/seoInsight/f3f313aa83d67851", "source_url": null}, {"n": 10, "id": "828316fc34745017", "category": "連結策略", "title": "SC 內部指標討論 - 標籤頁策展工具突破流量瓶頸", "date": "2023-12-06", "snippet": "標籤頁可作為突破流量瓶頸的策展工具；財報狗嘗試以標籤頁突破全站流量 25%，垂直領域流量集中效果可觀", "chunk_url": "/admin/seoInsight/828316fc34745017", "source_url": null}, {"n": 11, "id": "afe8651b569e32ea", "category": "連結策略", "title": "AI Agents for SEO - 內部連結優化", "date": "2026-05-15", "snippet": "內部連結 Agent 可爬取全站建立主題關係圖、生成連入連出機會清單與建議錨點、標記錨點過度優化或 equity 分布不均", "chunk_url": "/admin/seoInsight/afe8651b569e32ea", "source_url": null}, {"n": 12, "id": "780ba8d5305a2efd", "category": "內容策略", "title": "新媒體經營的全面手冊 - 懶人包策展 SEO 價值", "date": "", "snippet": "懶人包匯聚特定主題多元關鍵字和連結、易成搜尋主要入口具高 SEO 價值；持續更新的懶人包比靜態列表更強", "chunk_url": "/admin/seoInsight/780ba8d5305a2efd", "source_url": null}, {"n": 13, "id": "c0d98f761d07611d", "category": "演算法與趨勢", "title": "SEO 1018 - Discover 助燃", "date": "2023-10-18", "snippet": "有潛力進入 Google Discover 的文章需透過外部流量信號助燃，提升 Google 關注度與分發意願", "chunk_url": "/admin/seoInsight/c0d98f761d07611d", "source_url": null}, {"n": 14, "id": "5cea18faf6a16938", "category": "Discover與AMP", "title": "SEO 會議_2023/10/04 - Discover 死灰復燃", "date": "2023-10-04", "snippet": "已停止被探索推播的文章有機會在獲得新社群訊號或流量再次上升時重新被推播", "chunk_url": "/admin/seoInsight/5cea18faf6a16938", "source_url": null}, {"n": 15, "id": "2b1f713f1b03ce14", "category": "技術SEO", "title": "SC 27 KPI (16) - 結構化資料格式與收錄", "date": "2021-09-16", "snippet": "結構化資料格式如 RDFa/Microformat 將資料與網頁綁定，複雜度影響工程實作；格式選擇影響收錄判讀", "chunk_url": "/admin/seoInsight/2b1f713f1b03ce14", "source_url": null}, {"n": 16, "id": "f50c900d2aecc0cd", "category": "搜尋表現分析", "title": "SEO 會議_20251013 - TDK 變動影響點擊", "date": "2025-10-13", "snippet": "TDK 變動可能導致使用者看到不熟悉的標題與描述而減少點擊，即使平均排名沒變整體點擊仍可能下降", "chunk_url": "/admin/seoInsight/f50c900d2aecc0cd", "source_url": null}, {"n": 17, "id": "29f981f09f0cda23", "category": "搜尋表現分析", "title": "SC 內部指標討論、2024-07-22 - CTR 下降是好事", "date": "2024-07-22", "snippet": "CTR 下降通常意味曝光數成長幅度遠大於點擊，是好事", "chunk_url": "/admin/seoInsight/29f981f09f0cda23", "source_url": null}, {"n": 18, "id": "5267399c05566bbf", "category": "GA與數據追蹤", "title": "SEO 會議_20260112 - GA Referral 交叉驗證", "date": "2026-01-12", "snippet": "在 GA 查看 Referral → Search 來源核對 GSC 搜尋流量是否一致、找出損失量來源", "chunk_url": "/admin/seoInsight/5267399c05566bbf", "source_url": null}, {"n": 19, "id": "23eff8f0210ef59e", "category": "技術SEO", "title": "SEO 會議_2024/01/24 - 作者 Profile Page E-E-A-T", "date": "2024-01-24", "snippet": "作者頁面可透過實作 Profile Page 結構化資料向 Google 明確傳遞作者身份與專業性信號", "chunk_url": "/admin/seoInsight/23eff8f0210ef59e", "source_url": null}, {"n": 20, "id": "5b93ebdc0a348370", "category": "搜尋表現分析", "title": "SEO 會議_20251013 - 辛普森悖論與平均排名", "date": "2025-10-13", "snippet": "辛普森悖論：索引更多長尾關鍵字時整體平均排名數字反而下降，但實際流量與整體表現進步", "chunk_url": "/admin/seoInsight/5b93ebdc0a348370", "source_url": null}] -->
