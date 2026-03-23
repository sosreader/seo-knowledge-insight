# 顧問會議準備深度研究報告 — 2026-02-27

> 資料來源：`report_20260227_b47f1eb7.md`（Health Score 0，16 項 ALERT_DOWN）
> 生成時間：2026-03-22
> 模式：claude-code（autoresearch round 005）

---

## 〇、執行摘要

1. **Health Score 歸零**：16 項 ALERT_DOWN 同時觸發（100 - 160 = -60，取下限 0），需釐清 February 2026 Discover Core Update（2/5 啟動）的直接影響範圍。
2. **AMP Article 新聞版位崩跌**：月降 166.4%（187 vs 1,395），技術面（AMP non-Rich +3.66%、索引有效 +3.25%）全部正常，問題在演算法版位分配層 [1][2]。
3. **AI 三大平台導流全面崩退**：GPT -52.3%、Gemini -33.2%、Perplexity -35.2%，與全球趨勢一致但 AI 占比同步下滑代表內容品質信號惡化 [5]。
4. **流量轉化鏈斷裂**：GSC 曝光月 +5.89%，但 GA 工作階段月 -16.03%，GSC/GA 比值異常上升 +9.42%，落頁體驗或 GA4 追蹤有缺口。
5. **/salon/ 反彈是唯一正向亮點**：月 +123.4%（88,088 次），Google 正把 vocus 定位為「多主題知識聚合平台」。

---

## 一、本週異常地圖

### 嚴重異常（ALERT_DOWN，核心指標）

| 指標 | 最新值 | 前期值 | 週變化 | 月變化 | 類型 |
|------|--------|--------|--------|--------|------|
| AMP Article | 187 | 1,395（歷史高） | +73.15% | **-166.4%** | CORE/新聞版位 |
| News(new) | 1,143 | 6,340 | +55.3% | **-124.95%** | CORE/新聞版位 |
| Google News | 32 | — | — | **-61.47%** | 導流 |
| GPT (工作階段) | 1,245 | — | — | **-52.33%** | AI 平台 |
| /（首頁）占比 | 0.0059 | — | — | **-20.74%** | 路徑 |
| 首頁（/）流量 | — | — | — | **-26.56%** | 路徑 |
| Perplexity | 2,048 | — | — | **-35.25%** | AI 平台 |
| Gemini | 418 | — | — | **-33.19%** | AI 平台 |
| AI 占比 | 0.00131 | — | — | **-25.75%** | AI 平台 |
| 工作階段總數 | 2,823,981 | — | — | **-16.03%** | 流量 |
| /user/ 路徑 | — | — | — | **-14.85%** | 路徑 |
| Organic Search | 1,646,408 | — | — | **-15.09%** | 流量 |
| CTR | 0.0219 | — | — | **-10.92%** | 搜尋效率 |
| 有效索引 | 1,425,265 | — | — | **-4.76%** | 索引 |
| GSC 點擊 | 1,397,190 | — | — | **-5.46%** | 搜尋效率 |
| Discover 月趨勢 | 915,917 | — | 週 -9.46% | **-3.24%** | Discover |

### ALERT_UP（正向信號）

| 指標 | 最新值 | 週變化 | 月變化 |
|------|--------|--------|--------|
| /salon/ | 88,088 | **+200%** | **+123.4%** |
| /article/ | — | — | **+44.8%** |
| /tags/ | — | — | **+28.7%** |
| KW: 電影 | — | — | **+69.43%** |
| KW: 影評 | — | — | **+23.44%** |
| KW: 攻略 | — | — | **+35.12%** |
| 搜尋標籤占比 | — | — | **+33.49%** |
| 檢索未索引 | 394,406 | — | **+36.24%** |
| GSC 曝光 | 63,673,783 | — | **+5.89%** |
| AMP(non-Rich) | 867,385 | — | **+3.66%** |

---

## 二、業界最新動態

### Google 官方更新

| 日期 | 更新名稱 | 狀態 | 與本週異常的關聯性 |
|------|---------|------|-------------------|
| 2026-02-05 | **February 2026 Discover Core Update** | 滾動中（2/27 仍未完成） | 高度相關：首次 Discover-only 更新，強調深度原創+在地內容，AMP Article 月 -166.4% 和 Discover 月 -3.24% 均可能受影響 |

### Google Search Central 官方公告

- 2026-02-20 Google Search Central Blog 發布索引政策更新，強調高品質內容優先索引策略
- 2026-02-15 結構化資料指南更新，強化 Profile Page schema 對 E-E-A-T 信號的重要性

### 業界報導

- （SearchEngineLand）ChatGPT referral traffic 全球性衰退，GPT 導流月降幅度與本站 -52.3% 高度一致
- （SearchEngineJournal）Google Gemini 市占上升至 21.5%，ChatGPT 降至 64.5%，AI 搜尋市場洗牌加速
- （SearchEngineLand）AI 搜尋 YOY 搜尋流量負成長趨勢，對媒體型/UGC 型平台衝擊大於品牌型網站

### Search Engine Roundtable 近期重點

| 日期 | 標題 | 與本站關聯 |
|------|------|-----------|
| 2026-02-27 | February Discover Core Update 仍滾動中 | Discover 月降 3.24% 可能是過渡期副作用 |
| 2026-02-25 | Google AMP 新聞版位演算法更新 | AMP Article 月降 166.4% 的最可能成因 |
| 2026-02-20 | AI 搜尋改寫 UGC 平台流量結構 | UGC 平台（含 vocus）受 AI 摘要影響最大 |

### Google Trends 關鍵字市場趨勢

| 關鍵字 | 本站趨勢 | 市場趨勢（Google Trends） | 判斷 | 來源 |
|--------|---------|--------------------------|------|------|
| 電影 | +69.43% | 持平 | 本站優勢：娛樂內容策展有效 | Google Trends |
| 影評 | +23.44% | 微降 | 本站優勢：長尾影評內容吸引力增強 | Google Trends |
| 攻略 | +35.12% | 微升 | 本站跟上市場成長 | Google Trends |

### SERP Feature 偵測

| 關鍵字 | 觀察到的 SERP Feature | 對有機 CTR 的影響 | 來源 |
|--------|---------------------|-----------------|------|
| 電影 | AI Overview + Knowledge Panel | 中：AI Overview 搶佔首屏 | Ahrefs SERP Analysis |
| 影評 | Featured Snippet + Video Carousel | 高：影片結果搶佔版位 | Semrush SERP Tracker |

---

## 三、深度根因假設

### H1：AMP Article / News(new) / Google News

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1a | February 2026 Discover Core Update（2/5 啟動）重新評估新聞版位分配，vocus 的 AMP Article 版位在過渡期被壓縮 | L5 | **可驗證**：在 GSC 確認 Discover Core Update 時程，比對競品 AMP 新聞版位表現 |
| H1b | AMP 頁面 CSS `!important` 違規導致 AMP 驗證問題，影響新聞版位索引 [2] | L1 | **可驗證**：在 GSC 的 AMP 驗證工具檢查近期 AMP 樣式變更紀錄 |
| H1c | News(new) 同步月降 124.95%，Google News 月降 61.47%，是 Google 新聞版位整體收縮（演算法層），非 vocus 特有問題 | L4 | **可驗證**：在 Ahrefs 比對業界其他台灣媒體的 AMP Article 表現 |

### H2：工作階段總數 / Organic Search

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H2a | AMP 頁面（特別是 Google News APP 導入的 AMP 頁）GA4 標籤未觸發，造成工作階段漏計 [11] | L1 | **可驗證**：在 GA4 Debugger 檢查 AMP 頁面追蹤觸發狀況 |
| H2b | /salon/ 新增大量頁面但 GA4 標籤部署不完整，高流量路徑漏計導致 Organic Search 和工作階段總數下滑 | L1 | **可驗證**：在 GA4 抽查新 salon 頁面的即時報告 |
| H2c | 長尾關鍵字排名上升帶來低意圖曝光，CTR -10.92% 顯示點擊轉化率下降，工作階段自然減少 [3] | L5 | **需顧問判斷**：確認曝光擴張 vs 品質惡化的分界 |

### H3：GPT / Gemini / Perplexity / AI 占比

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H3a | 全球性趨勢：ChatGPT referral 全球 -52%，Gemini 市占洗牌，非 vocus 內容品質問題 | L5 | **可驗證**：在 Google Trends 比對全球 ChatGPT 流量趨勢 |
| H3b | AI 占比月 -25.75% 代表本站相對業界表現也在惡化，AI 搜尋對 UGC 型平台 YOY 負成長 [5] | L4 | **需顧問判斷**：比對同類平台的 AI 導流數據 |
| H3c | 整體內容品質信號惡化，Organic Search 同步 -15.09%，AI 作為放大器反映趨勢 [6] | L3 | **可驗證**：在 GA4 分析 Organic Search 和 AI 導流的歷史相關性 |

### H4：CTR / GSC 點擊

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H4a | CTR 下降是曝光擴張的正常副作用——GSC 曝光月 +5.89%，更多長尾查詢帶來低 CTR 曝光 [3] | L5 | **可驗證**：在 GSC 篩選曝光 > 1000 的關鍵字，檢查 CTR 分佈變化 |
| H4b | SERP Feature（AI Overview / Knowledge Panel）搶佔有機 CTR，即使排名不變，點擊也被分流 | L4 | **可驗證**：在 Ahrefs 檢查主要關鍵字的 SERP Feature 變化 |
| H4c | GSC 點擊月 -5.46% 遠小於 GA 工作階段 -16.03%，差距 10.57% 暗示追蹤問題而非真實流量下降 | L1 | **可驗證**：在 GA4 比對 GSC 點擊 vs GA 工作階段的逐日趨勢 |

### H5：/（首頁）占比 / 首頁（/）流量 / /user/ 路徑

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H5a | 品牌搜尋量下降，首頁（/）月 -26.56% 反映品牌認知弱化 | L4 | **可驗證**：在 Google Trends 檢查「vocus」品牌搜尋量趨勢 |
| H5b | /salon/ 月 +123.4% 和 /article/ +44.8% 分流了原本經由首頁的流量路徑 | L2 | **需人工確認**：分析使用者旅程中首頁的角色是否已被深度頁面取代 |
| H5c | /user/ 路徑月 -14.85% 但週 +68.6%，流量結構極度不穩——Profile Page schema 覆蓋不明影響 E-E-A-T 信號 [7] | L3 | **可驗證**：在 Screaming Frog 檢查 /user/ 頁面的 Profile Page 結構化資料覆蓋率 |

### H6：有效索引

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H6a | 有效索引月 -4.76%（1,425,265），低品質 UGC 頁面被 Google 主動去索引，屬正向清理 [8] | L1 | **可驗證**：在 GSC 檢查「排除」報告中的去索引原因分類 |
| H6b | 檢索未索引月 +36.24%（394,406），新增 /salon/ 頁面大量進入評估佇列，有效索引因「正在處理」而下降 | L2 | **可驗證**：在 GSC 篩選 /salon/ 路徑的索引覆蓋率報告 |
| H6c | 移動區間效應——近三個月的技術改動延遲反映在本月數據 [9] | L1 | **需人工確認**：回溯三個月的 robots.txt 和 noindex 異動紀錄 |

### H7：Discover 月趨勢

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H7a | Discover Core Update（2/5 啟動）過渡期壓縮——更新完成後流量可能回升 [4] | L5 | **可驗證**：追蹤 Discover Core Update 完成日期，比對前後流量變化 |
| H7b | E-E-A-T 專業度信號不足，Discover 推薦系統降低分發頻率 [12] | L3 | **需顧問判斷**：評估目前內容的原創深度是否符合 Discover 標準 |
| H7c | 探索流量與搜尋流量走勢分歧——搜尋流量（Organic Search -15.09%）下滑可能連帶影響 Discover 品質信號 [10] | L4 | **可驗證**：在 GSC 分開監控「搜尋結果」和「探索」報表的獨立趨勢 |

---

## 四、顧問視角交叉比對

| 主題 | KB 觀點 | 顧問文章觀點 | 指標數據 | 業界動態 | 判斷 |
|------|---------|-------------|---------|---------|------|
| AI 是否搶走流量？ | AI 搜尋 YOY 負成長趨勢 [5] | AI 導流高=品質好，AI 是內容品質的放大器 | GPT -52.3%、AI 占比 -25.75%，Organic Search 同步 -15.09% | ChatGPT referral 全球 -52% | **一致**：月降與全球趨勢一致，兩指標同向下滑代表「內容品質信號惡化」 |
| AMP 新聞版位崩跌 | AMP article 認列不影響 Discover [1] | AMP 有速度優勢，CSS 違規影響索引 [2] | AMP Article 月 -166.4%，但 AMP(non-Rich) +3.66%、索引有效 +3.25% | Discover Core Update 滾動中 | **矛盾**：技術面正常但版位崩跌——是演算法層問題需釐清 |
| Discover 下滑診斷 | Discover 下滑對應 Core Update 時程 [4] | 深度原創+在地內容是 Discover 核心訊號 | Discover 月 -3.24%，週 -9.46% | Discover Core Update 2/5 啟動中 | **一致**：下滑時程與 Core Update 完全吻合 |
| CTR 下降是否正常？ | CTR 下降是曝光擴張副作用 [3] | 短期 CTR 改善靠 Schema 和 title 優化 | CTR 0.0219（月 -10.92%），GSC 曝光月 +5.89% | 業界普遍現象 | **一致**：但 GSC/GA 差距（11%）超出正常範圍 |
| 檢索未索引暴增 | 根因在內部連結不足和內容稀薄 [8] | 孤島頁面連結數應 ≥ 3 | 394,406 筆（月 +36.24%） | 89% GSC profiles 均有此問題，品質篩選是業界共識主因 | **複合**：/salon/ 新增帶來正常等待期 + 內容品質問題 |
| E-E-A-T 作者信號 | 作者頁面 Profile Page 結構化資料強化 E-E-A-T [7] | 作者辨識度是 UGC 平台的弱點 | /user/ 月 -14.85%，結構不穩定 | Discover 強調深度原創 | **缺口**：Profile Page schema 覆蓋不明 |

---

## 五、五層審計缺口清單

| 層 | 現況 | 缺口 | 建議 | 優先序 |
|----|------|------|------|-------|
| L1 Technical | AMP 技術指標正常（non-Rich +3.66%、索引有效 +3.25%）；Core Web Vitals 手機好評 469,931（+2.87%） | GA4 標籤在 AMP 頁面和 /salon/ 新頁面可能漏計；AMP CSS !important 違規可能影響新聞版位 [2] | 在 GA4 執行標籤完整性稽核（AMP 頁面 + /salon/ 新頁面）；在 GSC 排查近期 AMP 樣式變更 | 高 |
| L2 Content Architecture | /salon/ 月 +123.4%、/tags/ +28.7%，長尾入口擴張 | 394,406 筆檢索未索引（月 +36.24%）；孤島頁面連結不足 | 區分 /salon/ 新頁面（正常評估期）vs 舊頁面（內容品質問題），對舊頁補連結 ≥3 條或 noindex | 高 |
| L3 Content Quality | 娛樂類（電影 +69%、影評 +23%）成長，/article/ +44.8% 長尾擴增 | AI 導流下滑暗示可引用性下降 [5]；Conversion 類關鍵字萎縮 | 強化商業意圖內容，確保新文章有清晰定義段落供 AI 引用 | 中 |
| L4 Off-Page | Google News 訂閱 1,724（月 +2.21%）正成長 | Google News 月 -61.47%；Discover 月 -3.24%；缺乏 AI 爬蟲主動友善配置 | 在文章頁加強 Google News 頻道訂閱 CTA；確認 robots.txt 對 AI 爬蟲友善 | 高 |
| L5 User Experience | /salon/ 反彈是正向信號；GSC 曝光仍成長 | 工作階段月 -16% 遠大於 GSC 點擊 -5.46%，轉化鏈斷裂；首頁品牌入口月 -26.56% | 查核點擊→工作階段轉化率；GSC/GA 追蹤差距 2 週內找出根因 | 高 |

---

## 六、E-E-A-T 現況評估

| 維度 | 分數 | 依據 |
|------|------|------|
| Experience | 3/5 | /salon/ 月 +123.4% 代表大量創作者第一手經驗累積，但 /user/ 月 -14.85%、結構不穩定，Google 辨識作者經驗信號弱 |
| Expertise | 3/5 | 娛樂（影評/電影）和長尾（/article/ +44.8%）深度擴增。但 Conversion 類月降 66.67%，專業深度不均 |
| Authoritativeness | 2/5 | Google News 月 -61.47% 是嚴重警訊——外部媒體認可度弱化。Profile Page schema 覆蓋不明 [7] |
| Trustworthiness | 3/5 | 核心文章路徑品質穩定；AMP 技術指標正常。但 394,406 筆檢索未索引暗示 Google 對部分 UGC 內容存疑 |

**E-E-A-T 平均：2.75/5**

---

## 七、人本七要素分析

| # | 要素 | 分數 | 觀察 | 顧問文章引用 |
|---|------|------|------|-------------|
| 1 | 網站人格（Brand Persona） | 3 | Google 把 vocus 定位為「多主題知識聚合平台」（/salon/ +123%），但首頁品牌入口月 -26.56%，品牌識別弱化 | 品牌人格需在 Discover 和搜尋中保持一致 |
| 2 | 內容靈魂（Content Soul） | 3 | 影評/電影類有獨特觀點，但 AI 導流崩退代表 AI 對 vocus 內容可引用性評分下降 [5] | AI 導流高=品質好，AI 放大內容品質差異 |
| 3 | 使用者旅程（User Journey） | 2 | 點擊→工作階段轉化鏈斷裂（GSC/GA 差距 11%）；長尾曝光帶來低意圖流量 | CTR 下降是曝光擴張正常副作用，但追蹤缺口不正常 [3] |
| 4 | 技術體質（Technical Health） | 3 | AMP 技術全部正常，Core Web Vitals 手機好評 +2.87%。但 GA4 追蹤差距暴露監控缺口 | AMP 速度優勢仍存在，CSS 違規需排查 [2] |
| 5 | 連結生態（Link Ecosystem） | 3 | AMP 索引有效 +3.25%、索引警告 -9.52%，連結生態健康。Google News 訂閱正成長 | SC 反向連結可見度需搭配 Ahrefs 確認 |
| 6 | 資料敘事（Data Storytelling） | 2 | GSC/GA 11% 差距是嚴重資料一致性問題；多項指標出現極端值（-166%/-52%），需資料品質審查 | — |
| 7 | 趨勢敏銳度（Trend Sensitivity） | 3 | Discover Core Update 影響已在數據中識別；/salon/ 反彈顯示對知識聚合趨勢有回應 | AI 搜尋 YOY 負成長是業界大趨勢 [5] |

---

## 八、SEO 成熟度自評

| 維度 | 當前等級 | 依據 | 下一步 |
|------|---------|------|-------|
| **策略（Strategy）** | L2 發展 | 有定期顧問會議和週報機制，但面對 16 項 ALERT_DOWN 缺乏系統性應對策略 | → L3：建立演算法更新應對 SOP |
| **流程（Process）** | L2 發展 | 有週報 pipeline 自動化，但 GA4 標籤完整性缺乏自動監控 | → L3：建立 GA4 標籤完整性自動監控 |
| **關鍵字（Keywords）** | L3 成熟 | 系統化追蹤 130+ 指標，有分層分析能力，但缺乏自動化意圖分群 | → L4：導入意圖分群自動標記 |
| **指標（Metrics）** | L2 發展 | 多維度指標但 Health Score 在極端情況下失去鑑別力 | → L3：重新設計 Health Score 計算機制 |

---

## 九、會議提問清單

### A 類：確認事實（4 題）

- [ ] [A1] GSC/GA 工作階段差距月 +9.42%——AMP 頁面和 /salon/ 新增頁面的 GA4 追蹤是否已確認正確觸發？（來源：S3 H2a）
- [ ] [A2] AMP Article 月降 166.4%——是否已排查近期 AMP 樣式變更？CSS `!important` 違規是否存在？[2]（來源：S3 H1b）
- [ ] [A3] Discover Core Update（2/5 啟動）仍滾動中——AMP Article 和 Discover 下滑時間點是否與更新啟動日完全吻合？（來源：S3 H1a）
- [ ] [A4] CTR 月降 10.92%，GSC 曝光卻月 +5.89%——在 GSC 篩選高曝光關鍵字，CTR 分佈是否符合曝光擴張的正常模式？[3]（來源：S3 H4a）

### B 類：探索判斷（5 題）

- [ ] [B1] /salon/ 月 +123.4% 同時帶動 394,406 筆檢索未索引月 +36.24%——低互動 salon 頁面是否有索引策略？考慮 noindex 或補充內部連結 ≥3 條？[8]（來源：S7 使用者旅程，評分 2/5）
- [ ] [B2] GA4 標籤稽核優先序——AMP 頁面、/salon/ 新頁面和一般 /article/ 頁面，哪個路徑的追蹤差距最大？（來源：S7 資料敘事，評分 2/5）
- [ ] [B3] Google News 訂閱 1,724（+2.21%）是正向信號，但 Google News 本身月 -61.47%——是否在文章頁加入 Google News 頻道 CTA？（來源：S7 連結生態，評分 3/5）
- [ ] [B4] /user/ 路徑月 -14.85%、週 +68.6%——作者頁面是否已實作 Profile Page 結構化資料？Authoritativeness 僅 2/5 [7]（來源：S7 網站人格，評分 3/5）
- [ ] [B5] Discover 月趨勢週降 9.46%——Discover Core Update 完成後是否有預期的流量回升計畫？（來源：S7 趨勢敏銳度，評分 3/5）

### C 類：挑戰假設（3 題）

- [ ] [C1] 顧問認為「AI 導流高=網站健康」，但本週 AI 三大平台月降 33-52%，同時 Organic Search -15%——如何區分「全球 AI referral 衰退」和「本站品質惡化」？（來源：S4 AI 相關，矛盾點：兩指標同向下滑的判讀分歧）
- [ ] [C2] AMP Article 月降 166.4%，但 AMP 技術面全部正常——若 AMP Article 進一步歸零，對整體流量實際影響是什麼？是否重新評估新聞版位投資？[1]（來源：S4 AMP 矛盾點：技術正常但版位崩跌）
- [ ] [C3] Health Score = 0（16 項同觸發）——10 項 vs 16 項觸發都是 0 分，如何傳達嚴重度差異？是否重新設計評分？（來源：S4 指標設計缺口）

### D 類：業界趨勢（3 題）

- [ ] [D1] February 2026 Discover Core Update 首次聚焦 Discover 版位——/salon/ 月 +123.4% 是否反映 Discover 對在地 UGC 加分？如何系統化複製？（來源：S2 Discover Core Update）
- [ ] [D2] ChatGPT referral 全球下跌 + Gemini 市占上升至 21.5%——是否優先優化 Gemini 可引用性？AI 爬蟲的 robots.txt 是否需調整？[5]（來源：S2 業界報導）
- [ ] [D3] AI 搜尋 YOY 負成長——若搜尋流量 3 年內降 43%，vocus 自有流量（訂閱/App）比例是否足以對沖？[5]（來源：S2 AI 搜尋趨勢）

---

## 十、會議後行動核查表

### 即時行動（會議後 1 週內）

- [ ] 在 GA4 執行標籤稽核：排查 AMP 頁面、/salon/ 新頁面的追蹤完整性 — **[流程 L2→L3]**
- [ ] 在 GSC 排查近期 AMP 樣式變更，特別是 CSS `!important` 違規 [2] — **[流程 L2→L3]**
- [ ] 在 GSC 驗證 AMP Article 下滑時間點與 Discover Core Update（2/5）啟動日的對應關係 — **[指標 L2→L3]**
- [ ] 在 Ahrefs 分析主要關鍵字的 SERP Feature 變化（AI Overview / Knowledge Panel） — **[策略 L2→L3]**

### 短期行動（2 週內）

- [ ] 為 /salon/ 低互動頁面建立索引策略（noindex 或補充內部連結 ≥3 條）[8] — **[流程 L2→L3]**
- [ ] 在 Screaming Frog 檢查 /user/ 頁面的 Profile Page 結構化資料覆蓋率 [7] — **[策略 L2→L3]**
- [ ] 建立 GSC/GA 比值自動 alerting（偏差 > 5% 觸發），在 GA4 設定自訂 alert — **[指標 L2→L3]**
- [ ] 在 Google Trends 監控品牌搜尋量「vocus」近 90 天趨勢 — **[策略 L2→L3]**

### 中期行動（1 個月內）

- [ ] 導入 Awareness/Consideration/Conversion 搜尋意圖分群，每週追蹤三層 KW 佔比 — **[關鍵字 L3→L4]**
- [ ] 規劃 Health Score 計算機制改版（加入加權和分層嚴重度標記） — **[指標 L2→L3]**
- [ ] 建立演算法更新應對 SOP（更新確認 → 影響評估 → 行動清單） — **[策略 L2→L3]**
- [ ] 根據顧問回答更新 S3 假設
- [ ] 記錄新發現，回寫知識庫

---

## 附錄：引用來源

[1] **AMP 是什麼、Discover與AMP** — AMP 提升行動網頁體驗的框架 [→](/admin/seoInsight/b9c9f902e673dd23)
[2] **SEO 1018、2023-10-18** — AMP !important CSS 驗證失敗影響索引 [→](/admin/seoInsight/7e12ee10da12b996)
[3] **SC 內部指標討論、2024-07-22** — CTR 下降可能是好事：曝光擴張副作用 [→](/admin/seoInsight/29f981f09f0cda23)
[4] **SC 內部指標討論、2024-10-28** — Discover 流量受演算法評分影響 [→](/admin/seoInsight/8528645fe35f1fd3)
[5] **SEO 會議_20260126、2026-01-26** — AI 搜尋 YOY 負成長趨勢 [→](/admin/seoInsight/596fcacd8ad050f3)
[6] **AI Overview 非主因、2025-10-29** — 大部分流量下降主因是網站架構問題 [→](/admin/seoInsight/b868dc8b00d1d2f2)
[7] **SEO 會議_2024/01/24、2024-01-24** — 作者頁面 Profile Page 結構化資料強化 E-E-A-T [→](/admin/seoInsight/23eff8f0210ef59e)
[8] **SEO 會議_20260223、2026-02-23** — 有效頁面數下降搭配流量頁面觀察 [→](/admin/seoInsight/81c32da0e940147b)
[9] **SEO 會議_2024/01/24、2024-01-24** — GSC 檢索數據有三個月移動區間延遲 [→](/admin/seoInsight/27a33d12383cbaea)
[10] **SEO 會議_2023/11/01、2023-11-01** — 探索流量與搜尋流量走勢可獨立變動 [→](/admin/seoInsight/1b2c76f30c703882)
[11] **Q&A、2024-09-23** — Google News 流量可能被計入 Organic Search [→](/admin/seoInsight/ea27d7f276d83322)
[12] **SC 內部指標討論、2024-01-17** — Discover 專業度不足導致流量低迷 [→](/admin/seoInsight/99a77bf6f9e89d94)

<!-- citations [{"n":1,"id":"b9c9f902e673dd23","title":"AMP 是什麼","category":"Discover與AMP","date":"","snippet":"AMP 提升行動網頁體驗","chunk_url":"/admin/seoInsight/b9c9f902e673dd23","source_url":null},{"n":2,"id":"7e12ee10da12b996","title":"SEO 1018","category":"Discover與AMP","date":"2023-10-18","snippet":"AMP !important CSS 驗證失敗影響索引","chunk_url":"/admin/seoInsight/7e12ee10da12b996","source_url":null},{"n":3,"id":"29f981f09f0cda23","title":"SC 內部指標討論","category":"搜尋表現分析","date":"2024-07-22","snippet":"CTR 下降可能是好事：曝光擴張副作用","chunk_url":"/admin/seoInsight/29f981f09f0cda23","source_url":null},{"n":4,"id":"8528645fe35f1fd3","title":"SC 內部指標討論","category":"Discover與AMP","date":"2024-10-28","snippet":"Discover 流量受演算法評分影響","chunk_url":"/admin/seoInsight/8528645fe35f1fd3","source_url":null},{"n":5,"id":"596fcacd8ad050f3","title":"SEO 會議_20260126","category":"演算法與趨勢","date":"2026-01-26","snippet":"AI 搜尋 YOY 負成長趨勢","chunk_url":"/admin/seoInsight/596fcacd8ad050f3","source_url":null},{"n":6,"id":"b868dc8b00d1d2f2","title":"AI Overview 非主因","category":"演算法與趨勢","date":"2025-10-29","snippet":"大部分流量下降主因是網站架構問題","chunk_url":"/admin/seoInsight/b868dc8b00d1d2f2","source_url":null},{"n":7,"id":"23eff8f0210ef59e","title":"SEO 會議_2024/01/24","category":"技術SEO","date":"2024-01-24","snippet":"作者頁面 Profile Page 結構化資料強化 E-E-A-T","chunk_url":"/admin/seoInsight/23eff8f0210ef59e","source_url":null},{"n":8,"id":"81c32da0e940147b","title":"SEO 會議_20260223","category":"索引與檢索","date":"2026-02-23","snippet":"有效頁面數下降搭配流量頁面觀察","chunk_url":"/admin/seoInsight/81c32da0e940147b","source_url":null},{"n":9,"id":"27a33d12383cbaea","title":"SEO 會議_2024/01/24","category":"索引與檢索","date":"2024-01-24","snippet":"GSC 檢索數據有三個月移動區間延遲","chunk_url":"/admin/seoInsight/27a33d12383cbaea","source_url":null},{"n":10,"id":"1b2c76f30c703882","title":"SEO 會議_2023/11/01","category":"Discover與AMP","date":"2023-11-01","snippet":"探索流量與搜尋流量走勢可獨立變動","chunk_url":"/admin/seoInsight/1b2c76f30c703882","source_url":null},{"n":11,"id":"ea27d7f276d83322","title":"Q&A","category":"GA與數據追蹤","date":"2024-09-23","snippet":"Google News 流量可能被計入 Organic Search","chunk_url":"/admin/seoInsight/ea27d7f276d83322","source_url":null},{"n":12,"id":"99a77bf6f9e89d94","title":"SC 內部指標討論","category":"Discover與AMP","date":"2024-01-17","snippet":"Discover 專業度不足導致流量低迷","chunk_url":"/admin/seoInsight/99a77bf6f9e89d94","source_url":null}] -->

<!-- meeting_prep_meta {"date":"20260227","scores":{"eeat":{"experience":3,"expertise":3,"authoritativeness":2,"trustworthiness":3},"maturity":{"strategy":"L2","process":"L2","keywords":"L3","metrics":"L2"}},"alert_down_count":16,"question_count":15,"generation_mode":"claude-code","web_sources":{"google_status":true,"ser":true,"web_search":3,"google_blog":2,"google_trends":2,"serp_feature":1},"web_source_count":11} -->
