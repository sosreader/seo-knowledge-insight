# 顧問會議準備深度研究報告 — 2026-03-06

> 資料來源：`report_20260306_v33.md`（v3.3 成熟度模型整合版週報）
> 生成時間：2026-03-14
> 模式：claude-code

---

## 〇、執行摘要

1. **資料斷層警示**：10 項路徑指標 latest=null（weekly=-100%），非真正流量歸零，極可能是 GSC 資料收集延遲或快照範圍不完整，**優先確認資料完整性**。
2. **連結生態系統性弱化**：外部連結月降 18.2%、內部連結分布月降 16.3%，兩者同步下滑代表連結權重正在流失，需系統性介入 [7][8]。
3. **AI 平台導流已觸底反彈**：GPT/Gemini/Perplexity 月趨勢全面下滑，但週環比均轉正。顧問觀點「AI 導流高=網站健康」[6] 未被否定，本站 AI 占比仍在市場水準之上。
4. **February 2026 Discover Core Update 完成**（2/5–2/27），首次 Discover-only 更新，強調在地化、深度原創內容，Discover 週 +17.7% 顯示 vocus 正受益。
5. **娛樂+財經關鍵字全面爆發**：影評/電影/股/評價全線上升，但營運型關鍵字（保養/必買/攻略）同步下滑，平台內容定位正在分化。

---

## 一、本週異常地圖

### 嚴重異常（ALERT_DOWN，非資料斷層）

| 指標 | 最新值 | 前期值 | 週變化 | 月變化 | 類型 |
|------|--------|--------|--------|--------|------|
| 營運 KW：保養 | 3 | 7 | **-57.1%** | +36.4% | 關鍵字 |
| AMP Article | 972 | 187 | +419.8% | **-46.0%** | CORE |
| News(new) | 1,889 | 1,143 | +65.3% | **-40.6%** | CORE |
| GPT (工作階段) | 1,397 | 1,245 | +12.2% | **-39.9%** | AI 平台 |
| /en/ | null | 1,084 | -100% | **-22.9%** | 路徑+斷層 |
| Gemini | 506 | 418 | +21.1% | **-22.0%** | AI 平台 |
| 外部連結 | 597,548 | 597,548 | 0% | **-18.3%** | 連結 |
| 內部連結分布 | 2.74 | 2.74 | 0% | **-16.3%** | 連結 |
| AI 占比 | 0.00136 | 0.00131 | +3.2% | **-16.2%** | AI 平台 |

### ALERT_UP（正向或需關注）

| 指標 | 最新值 | 週變化 | 月變化 |
|------|--------|--------|--------|
| Video | 506 | +113.5% | +73.5% |
| KW: 股 | 4,396 | +72.0% | +13.8% |
| Google News | 61 | +90.6% | +5.2% |
| 檢索未索引 | 394,406 | 0% | **+24.1%** |
| KW: 影評 | 1,677 | +27.3% | +20.0% |
| KW: 電影 | 1,343 | +25.4% | +56.1% |
| /tags/ | 10,191 | +2.3% | +38.0% |

### 資料斷層（10 項 latest=null）

全網域、/salon/、/article/、檢索未索引(全部)、/tag/、/user/、/post、/en/、總合、總合/全網域

---

## 二、業界最新動態

### Google 官方更新

| 日期 | 更新名稱 | 狀態 | 與本週異常的關聯性 |
|------|---------|------|-------------------|
| 2/5–2/27 | **February 2026 Discover Core Update** | 已完成 | 🔴 高度相關：首次 Discover-only 更新，強調深度原創+在地內容。Discover 週 +17.7% 顯示 vocus 正受益，但 unique domains 減少（美國 172→158）代表篩選更嚴格 |
| 2/25 | Serving Issue | 已修復 | 🟡 可能相關：服務異常可能部分解釋資料斷層 |

### 業界報導

- **ChatGPT 導流量暴跌 52%**（SearchEngineLand）— ChatGPT referral traffic 月降 52%，Reddit 引用 +87%。本站 GPT 月降 39.9% 與全球趨勢一致，非本站獨有問題。
- **出版業預測搜尋流量 3 年內降 43%**（SearchEngineLand）— 73% B2B 網站 2024-2025 年流量顯著下降。本站曝光仍月 +6.6%，逆勢成長。
- **Gemini 市占上升至 21.5%**（SearchEngineJournal）— ChatGPT 降至 64.5%。本站 Gemini 月降但週轉正，可能受平台市占洗牌影響。

### Search Engine Roundtable 近期重點

| 日期 | 標題 | 與本站關聯 |
|------|------|-----------|
| 3/13 | Google 打擊自我推廣型 Listicle | 🟡 監控：vocus 部分文章可能觸及此標準 |
| 3/12 | AI Mode 新增「Ask About」功能 | 🟢 資訊：AI 搜尋互動性提升，長期利好內容平台 |
| 3/12 | AI Mode 探索個人化功能 | 🟢 資訊：個人化推薦可能利好 UGC 平台 |
| 3/11 | GSC Branded Queries Filter | 🟡 行動：新功能上線，可用於區分品牌 vs 非品牌查詢 |

---

## 三、深度根因假設

### H1：營運 KW「保養」週降 57.1%（3→7）

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1a | 季節性因素——3 月非保養品旺季，搜尋量自然回落 | L5 | **可驗證**：比對 Google Trends 同期 |
| H1b | 競品（Dcard/PTT）搶佔 SERP，vocus 排名下滑 | L4 | **可驗證**：GSC 查詢排名變化 |
| H1c | 站上保養類內容質量下降或產出減少 | L3 | **需人工確認**：檢查近期保養類文章數和品質 |

### H2：外部連結月降 18.2%

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H2a | GSC 報表更新延遲（外部連結通常有 2-4 週延遲） | L1 | **可驗證**：比對 Ahrefs 即時數據 [7] |
| H2b | 高品質引用來源停止更新/刪除含 vocus 連結的頁面 | L4 | **需人工確認**：Ahrefs 流失連結報告 |
| H2c | 競品平台（Medium/方格子）搶佔相同主題的引用來源 | L4 | **需顧問判斷**：業界連結生態趨勢 |

### H3：AI 平台導流月趨勢全面下滑

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H3a | 全球性趨勢（ChatGPT referral -52%），非 vocus 獨有 | L5 | **已驗證**：SER 報導一致 |
| H3b | AI 平台改變引用策略（Reddit/Wikipedia 引用上升，擠壓 UGC 平台） | L4 | **需顧問判斷**：引用模式變化 |
| H3c | 本站結構化資料不足，AI 爬蟲難以擷取 | L1 | **可驗證**：檢查 robots.txt 和 AI 爬蟲存取 [6] |

### H4：/salon/ 檢索未索引暴增 153%

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H4a | UGC 低品質頁面大量增加，Google 爬取但拒絕索引 | L3 | **可驗證**：抽樣檢查低互動 salon 頁面 [4] |
| H4b | 內部連結不足——salon 頁面連結數 < 3，成為孤島頁面 | L2 | **可驗證**：分析 salon 頁面平均內部連結數 [8] |
| H4c | /salon/ URL 結構對爬蟲不友善（深層路徑、參數過多） | L1 | **可驗證**：GSC 檢索報告 |

---

## 四、顧問視角交叉比對

| 主題 | KB 觀點 | 顧問文章觀點 | 指標數據 | 業界動態 | 判斷 |
|------|---------|-------------|---------|---------|------|
| AI 搶走流量？ | AI 搜尋 YOY 負成長趨勢 [5] | 「AI 導流高=品質好」，AI 沒有奪走流量，只是照亮品質差異 [6] | AI 占比月 -16.2%，但週 +3.2% 轉正 | ChatGPT referral 全球 -52% | **一致**：月降與全球趨勢一致，非品質問題 |
| AMP 是否過時？ | AMP article 認列不影響 Discover [2] | 「AMP 沒死，反而更重要」— CWV 取代 AMP 加分但 AMP 仍有速度優勢 | AMP Article 月 -46% 但週 +420% | Discover Core Update 完成 | **矛盾**：顧問認為 AMP 重要，但指標顯示月衰退嚴重——需釐清是 Discover Update 導致的重新分配還是結構性衰退 |
| 檢索未索引問題 | 根因在內部連結不足和內容稀薄 [4][8] | 連結應服務使用者而非 SEO，孤島頁面連結數應 ≥ 3 | 未索引/有效 27.67%（月 +28%） | 無直接相關 | **一致**：KB 和指標都指向相同問題，但缺乏系統性修復計畫 |
| Discover 內容策略 | CTR < 5% 停止推播 [3]；社群助燃可死灰復燃 [12] | 深度原創+在地內容 | Discover 週 +17.7% | Discover Update 強調在地化 | **一致**：平台正受益於 Discover Update |
| 外部連結下降 | SC 可見度 ~80%，需搭配 Ahrefs [7] | 可用劃重點+外部平台建立雙向連結 | 月 -18.2%，週持平 | 無直接相關 | **缺口**：KB 有策略但缺執行紀錄，需確認是否有主動連結建設 |

---

## 五、五層審計缺口清單

| 層 | 現況 | 缺口 | 建議 | 優先序 |
|----|------|------|------|-------|
| L1 Technical | 回應時間改善至 508ms，AMP 索引有效 468K | AMP 索引（警告）+24.7%；10 項路徑資料斷層 | 排查 AMP CSS !important 違規 [13]；確認 GSC 資料收集設定 | 高 |
| L2 Content Architecture | /tags/ 成長 +38%，URL 結構合理 | 內部連結分布月降 16.3%；/salon/ 大量孤島頁面 | 為低連結 salon 頁面補充內部連結（目標 ≥ 3 條/頁）[8][15] | 高 |
| L3 Content Quality | 娛樂類內容強勁（影評/電影/股） | 營運 KW（保養/必買/攻略）全面下滑；UGC 品質不穩 | 強化營運類內容的深度與差異化 [11] | 中 |
| L4 Off-Page | AI 導流逆市場趨勢微幅回升 | 外部連結月降 18.2%；缺乏主動連結建設紀錄 | 啟動外部連結修復計畫 [7][12] | 高 |
| L5 User Experience | Discover 受益於 Core Update；CTR 穩定 | 搜尋流量占比月降 2.3%；保養/必買意圖流失 | 分析流失意圖的 SERP 競爭格局 | 中 |

---

## 六、E-E-A-T 現況評估

| 維度 | 分數 | 依據 |
|------|------|------|
| Experience | 3/5 | 平台有大量創作者（多元第一手經驗），但作者頁面缺乏結構化資料（Profile Page schema）[9]，Google 無法有效辨識個別作者的專業經歷 |
| Expertise | 3/5 | 娛樂（影評/電影）和財經（股）領域正在累積 topical authority，但營運類（保養/必買）深度不足，缺乏專家級技術文章 |
| Authoritativeness | 2/5 | 外部連結月降 18.2% 是嚴重警訊——外部認可度在弱化。Google News 訂閱 1,735（+0.6%）尚穩定，但缺乏行業媒體引用 |
| Trustworthiness | 3/5 | UGC 平台天然信任度較低；/salon/ 檢索未索引暴增 153% 暗示 Google 對部分內容品質存疑。但核心文章路徑（/article/）品質穩定 |

**E-E-A-T 平均：2.75/5**

---

## 七、人本七要素分析

| # | 要素 | 分數 | 觀察 | 顧問文章引用 |
|---|------|------|------|-------------|
| 1 | 網站人格（Brand Persona） | 3 | Google 正將 vocus 定位為「娛樂評論+財經觀點」入口，但營運 KW 下滑顯示商業導購定位弱化 | 「AI x SEO」文章強調品牌人格需清晰 |
| 2 | 內容靈魂（Content Soul） | 3 | 影評/電影類有獨特觀點（KW 全線上升），但 UGC /salon/ 品質不穩定，靈魂分裂 | 「AI 導流悖論」指出內容品質差異會被放大 [6] |
| 3 | 使用者旅程（User Journey） | 2 | 搜尋→閱讀路徑順暢，但站內延伸閱讀不足（內部連結分布 -16.3%），跨內容發現路徑斷裂 | 顧問強調連結應「引導使用者達成意圖」 |
| 4 | 技術體質（Technical Health） | 4 | 回應時間 508ms 優秀，檢索效率上升 +4.5%。但 AMP 索引警告 +24.7% 和 10 項資料斷層需關注 | 「AMP 過期了嗎」指出 AMP 仍有速度優勢 |
| 5 | 連結生態（Link Ecosystem） | 2 | 外部連結 -18.2%、內部連結分布 -16.3%，系統性弱化。孤島頁面問題嚴重 [8] | 顧問多次強調連結是 SEO 核心基礎建設 |
| 6 | 資料敘事（Data Storytelling） | 3 | 指標追蹤完整（130+ 指標），但 10 項資料斷層暴露資料品質問題 | — |
| 7 | 趨勢敏銳度（Trend Sensitivity） | 3 | Discover Core Update 反應良好（+17.7%），Video SEO 策略見效（+113.5%），但 AI 平台導流缺乏主動應對策略 | 「AI x SEO 迷思」提供了前瞻框架 |

---

## 八、SEO 成熟度自評

| 維度 | 當前等級 | 依據 | 下一步 |
|------|---------|------|-------|
| 策略（Strategy） | L2 | 有基本 SEO 計畫（週報+定期顧問會議），但缺乏主動的競爭分析和預測性規劃。連結建設無明確策略文件 | → L3：建立數據驅動的季度策略文件，含競爭分析 + 預測性指標（而非只看落後指標） |
| 流程（Process） | L2 | 有 SOP（pipeline 自動化、eval 體系），但執行不一致——10 項資料斷層暴露監控流程缺口 | → L3：自動化資料品質監控（GSC 資料完整性檢查 + alerting）|
| 關鍵字（Keywords） | L3 | 系統化追蹤（130+ 指標，extraction_model 分群），但缺乏意圖分群——無法區分 Awareness/Consideration/Conversion 層 | → L4：導入意圖分群 + 競爭分析，為每個關鍵字標注搜尋意圖類型 |
| 指標（Metrics） | L2 | 看多維度指標（Health Score、5-Layer Audit），但缺乏預警機制——資料斷層未被即時發現 | → L3：建立預警閾值 + 即時儀表板，資料品質自動 alerting |

---

## 九、會議提問清單

### A 類：確認事實（4 題）

- [ ] [A1] 10 項路徑資料斷層（全網域、/salon/、/article/ 等 latest=null）是否已在最新資料中恢復？斷層原因是 GSC 回報延遲還是快照範圍設定問題？（來源：S3 假設）
- [ ] [A2] 營運關鍵字「保養」從 7 降至 3——是季節性因素，還是競品（Dcard/PTT）搶佔了 SERP？GSC 中該查詢的排名位置是否有變化？（來源：S3 H1）
- [ ] [A3] 外部連結月降 18.2%——Ahrefs 即時數據是否與 GSC 一致？是否有已知的高品質引用來源停止連結？（來源：S3 H2）
- [ ] [A4] AMP 索引（警告）數量上升 24.7%（231→288）——是否已排查 CSS `!important` 違規或其他 AMP 驗證問題？（來源：S5 L1）

### B 類：探索判斷（5 題）

- [ ] [B1] 站內延伸閱讀/推薦機制近期是否有調整？內部連結分布月降 16.3%，使用者旅程評分僅 2/5。（來源：S7 使用者旅程，評分 2/5）
- [ ] [B2] /salon/ 檢索未索引暴增 153%——是否考慮對低互動量（例如月瀏覽 < 10）的 salon 頁面實施 noindex？或者有更好的品質控管策略？（來源：S7 連結生態，評分 2/5）
- [ ] [B3] 娛樂類 KW 全面爆發（影評+27%、電影+25%、股+72%），但營運 KW 全面下滑——這是平台有意識的內容策略轉向，還是自然演變？（來源：S7 網站人格，評分 3/5）
- [ ] [B4] Video 搜尋外觀 +113.5%、影片已編入索引 +5,836%——目前影片結構化資料的覆蓋率如何？是否有擴展計畫？（來源：S5 L1）
- [ ] [B5] 作者頁面目前是否有 Profile Page 結構化資料？E-E-A-T 中 Authoritativeness 評分僅 2/5，作者辨識度是弱點 [9]。（來源：S6 Authoritativeness 2/5）

### C 類：挑戰假設（3 題）

- [ ] [C1] 顧問文章認為「AMP 沒死，反而更重要」，但 AMP Article 月降 46%——這是 Discover Core Update 導致的暫時重新分配，還是 AMP 在新聞版位的結構性式微？我們是否應該重新評估 AMP 投資？（來源：S4，矛盾點：AMP 重要性 vs. 月衰退）
- [ ] [C2] 顧問文章指出「AI 導流高=網站健康」，本站 AI 占比月降 16.2%，但同期全球 ChatGPT referral 暴跌 52%。在全球性衰退的背景下，AI 導流比例是否仍然是網站健康度的有效指標？（來源：S4，需要校準指標解讀）
- [ ] [C3] KB 知識庫建議「孤島頁面連結數應 ≥ 3」[8]，但 /salon/ 新頁面每日大量產生——以目前的內容生產速度，手動補連結是否可行？是否需要自動化的內部連結推薦系統？（來源：S4，缺口：有策略無執行）

### D 類：業界趨勢（3 題）

- [ ] [D1] February 2026 Discover Core Update 已完成，強調「在地化+深度原創」——vocus 目前的在地化內容策略是什麼？是否有針對 Discover 的專屬內容規劃？（來源：S2 Discover Core Update）
- [ ] [D2] Google 正測試 AI Mode「個人化推薦」功能——如果 AI 搜尋結果開始個人化，UGC 平台是受益者還是受害者？vocus 的內容多樣性是否能轉化為個人化推薦的優勢？（來源：S2 AI Mode 個人化）
- [ ] [D3] GSC 新增 Branded Queries Filter——我們是否應該開始區分品牌查詢 vs. 非品牌查詢的表現，以更精確地衡量 SEO 效果？（來源：S2 GSC 新功能）

---

## 十、會議後行動核查表

### 即時行動（會議後 1 週內）

- [ ] 確認 10 項資料斷層是否恢復，記錄根因 — **[指標 L2→L3]**
- [ ] 用 Ahrefs 比對外部連結數據，識別流失來源 — **[策略 L2→L3]**
- [ ] 排查 AMP 索引（警告）+24.7% 的具體錯誤類型
- [ ] 建立資料品質自動 alerting（GSC 資料完整性檢查）— **[指標 L2→L3]**

### 短期行動（2 週內）

- [ ] 為 /salon/ 低互動頁面制定索引策略（noindex 或補連結）— **[流程 L2→L3]**
- [ ] 在作者頁面實作 Profile Page 結構化資料 — **[策略 L2→L3]**
- [ ] 分析營運 KW（保養/必買/攻略）的 SERP 競爭格局
- [ ] 導入搜尋意圖分群標註 — **[關鍵字 L3→L4]**

### 中期行動（1 個月內）

- [ ] 啟動外部連結修復計畫（目標：逆轉月 -18.2% 趨勢）— **[策略 L2→L3]**
- [ ] 建立預警閾值 + 即時儀表板 — **[指標 L2→L3]**
- [ ] 擴展影片結構化資料覆蓋率 — **[流程 L2→L3]**
- [ ] 根據顧問回答更新 S3 假設
- [ ] 記錄新發現，回寫知識庫

---

## 附錄：引用來源

[1] **SC 內部指標討論、2024-07-22** — CTR 下降可能是好事：曝光成長幅度遠超點擊 [→](/admin/seoInsight/29f981f09f0cda23)
[2] **SEO 會議_2024/04/17、2024-04-17** — AMP article 認列不影響 Discover 探索流量 [→](/admin/seoInsight/d84e5e5af4caa4a7)
[3] **SEO 會議_2023/10/04、2023-10-04** — Discover CTR 門檻 5-10% [→](/admin/seoInsight/5b35a5970a291a0b)
[4] **SC 內部指標討論、2023-09-20** — 檢索未索引根因：內部連結不足 [→](/admin/seoInsight/b82545d945ee0f56)
[5] **SEO 會議_20260126、2026-01-26** — AI 搜尋 YOY 負成長趨勢 [→](/admin/seoInsight/596fcacd8ad050f3)
[6] **AI 導流越高搜尋流量越上升、2025-12-10** — AI 導流高=品質好，放大內容品質差異 [→](/admin/seoInsight/f5066fc30f82717a)
[7] **IT 技術面 SC 27 組 KPI (25)、2021-09-25** — SC 反向連結可見度 ~80% [→](/admin/seoInsight/7fe843228fbc627a)
[8] **IT 技術面 SC 27 組 KPI (6)、2021-09-06** — 孤島頁面連結數 < 3 對 SEO 不利 [→](/admin/seoInsight/8bd713fb8988983b)
[9] **SEO 會議_2024/01/24、2024-01-24** — 作者頁面 Profile Page 結構化資料 [→](/admin/seoInsight/23eff8f0210ef59e)
[10] **SC 內部指標討論、2024-01-17** — Discover 專業度不足導致流量低迷 [→](/admin/seoInsight/99a77bf6f9e89d94)
[11] **SC 內部指標討論、2023-09-20** — Discover 流量下滑診斷步驟 [→](/admin/seoInsight/60f00b85f7789c3b)
[12] **SEO 1018、2023-10-18** — 社群助燃可讓 Discover 文章死灰復燃 [→](/admin/seoInsight/c0d98f761d07611d)
[13] **SEO 1018、2023-10-18** — AMP !important CSS 驗證問題 [→](/admin/seoInsight/7e12ee10da12b996)
[14] **SEO 0614、2023-06-14** — Google News APP 導向 AMP 頁面 [→](/admin/seoInsight/efc9c4ce4951ea7d)
[15] **SEO 會議_2024/11/25、2024-11-25** — 標籤頁連結過廣稀釋 PageRank [→](/admin/seoInsight/350fb28ebeb18f81)

<!-- citations [{"n": 1, "id": "29f981f09f0cda23", "title": "SC 內部指標討論、2024-07-22", "category": "搜尋表現分析", "date": "2024-07-22", "snippet": "CTR 下降可能是好事：曝光成長幅度遠超點擊代表觸及範圍擴大", "chunk_url": "/admin/seoInsight/29f981f09f0cda23", "source_url": null}, {"n": 2, "id": "d84e5e5af4caa4a7", "title": "SEO 會議_2024/04/17、2024-04-17", "category": "Discover與AMP", "date": "2024-04-17", "snippet": "AMP article 認列不直接影響 Discover 探索流量", "chunk_url": "/admin/seoInsight/d84e5e5af4caa4a7", "source_url": null}, {"n": 3, "id": "5b35a5970a291a0b", "title": "SEO 會議_2023/10/04、2023-10-04", "category": "搜尋表現分析", "date": "2023-10-04", "snippet": "Discover CTR 門檻 5-10%，低於 5% 停止推播", "chunk_url": "/admin/seoInsight/5b35a5970a291a0b", "source_url": null}, {"n": 4, "id": "b82545d945ee0f56", "title": "SC 內部指標討論、2023-09-20", "category": "索引與檢索", "date": "2023-09-20", "snippet": "檢索未索引根因在於內部連結不足和內容稀薄", "chunk_url": "/admin/seoInsight/b82545d945ee0f56", "source_url": null}, {"n": 5, "id": "596fcacd8ad050f3", "title": "SEO 會議_20260126、2026-01-26", "category": "搜尋表現分析", "date": "2026-01-26", "snippet": "AI 搜尋崛起對內容網站 YOY 搜尋流量呈現負成長趨勢", "chunk_url": "/admin/seoInsight/596fcacd8ad050f3", "source_url": null}, {"n": 6, "id": "f5066fc30f82717a", "title": "AI 導流越高搜尋流量越上升、2025-12-10", "category": "演算法與趨勢", "date": "2025-12-10", "snippet": "AI 導流高的網站搜尋流量同時在上升，品質放大效應", "chunk_url": "/admin/seoInsight/f5066fc30f82717a", "source_url": null}, {"n": 7, "id": "7fe843228fbc627a", "title": "IT 技術面 SC 27 組 KPI (25)、2021-09-25", "category": "連結策略", "date": "2021-09-25", "snippet": "SC 對反向連結可見度約 80%，需搭配 Ahrefs", "chunk_url": "/admin/seoInsight/7fe843228fbc627a", "source_url": null}, {"n": 8, "id": "8bd713fb8988983b", "title": "IT 技術面 SC 27 組 KPI (6)、2021-09-06", "category": "索引與檢索", "date": "2021-09-06", "snippet": "孤島頁面連結數不到 3 個對 SEO 不利", "chunk_url": "/admin/seoInsight/8bd713fb8988983b", "source_url": null}, {"n": 9, "id": "23eff8f0210ef59e", "title": "SEO 會議_2024/01/24、2024-01-24", "category": "技術SEO", "date": "2024-01-24", "snippet": "作者頁面 Profile Page 結構化資料強化 E-E-A-T", "chunk_url": "/admin/seoInsight/23eff8f0210ef59e", "source_url": null}, {"n": 10, "id": "99a77bf6f9e89d94", "title": "SC 內部指標討論、2024-01-17", "category": "Discover與AMP", "date": "2024-01-17", "snippet": "Discover 專業度不足導致流量低迷", "chunk_url": "/admin/seoInsight/99a77bf6f9e89d94", "source_url": null}, {"n": 11, "id": "60f00b85f7789c3b", "title": "SC 內部指標討論、2023-09-20", "category": "索引與檢索", "date": "2023-09-20", "snippet": "Discover 流量下滑診斷：確認 Core Update 時程+檢查索引數", "chunk_url": "/admin/seoInsight/60f00b85f7789c3b", "source_url": null}, {"n": 12, "id": "c0d98f761d07611d", "title": "SEO 1018、2023-10-18", "category": "演算法與趨勢", "date": "2023-10-18", "snippet": "社群助燃可讓 Discover 文章死灰復燃", "chunk_url": "/admin/seoInsight/c0d98f761d07611d", "source_url": null}, {"n": 13, "id": "7e12ee10da12b996", "title": "SEO 1018、2023-10-18", "category": "內容策略", "date": "2023-10-18", "snippet": "AMP !important CSS 驗證失敗影響索引", "chunk_url": "/admin/seoInsight/7e12ee10da12b996", "source_url": null}, {"n": 14, "id": "efc9c4ce4951ea7d", "title": "SEO 0614、2023-06-14", "category": "Discover與AMP", "date": "2023-06-14", "snippet": "Google News APP 導向 AMP 頁面", "chunk_url": "/admin/seoInsight/efc9c4ce4951ea7d", "source_url": null}, {"n": 15, "id": "350fb28ebeb18f81", "title": "SEO 會議_2024/11/25、2024-11-25", "category": "連結策略", "date": "2024-11-25", "snippet": "標籤頁連結過廣稀釋 PageRank", "chunk_url": "/admin/seoInsight/350fb28ebeb18f81", "source_url": null}] -->

<!-- meeting_prep_meta {"date":"20260306","scores":{"eeat":{"experience":3,"expertise":3,"authoritativeness":2,"trustworthiness":3},"maturity":{"strategy":"L2","process":"L2","keywords":"L3","metrics":"L2"}},"alert_down_count":9,"question_count":15,"generation_mode":"claude-code"} -->
