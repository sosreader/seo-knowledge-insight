# 顧問會議準備深度研究報告 — 2026-03-06

> 資料來源：`report_20260306_v33.md`（v3.3 成熟度模型整合版週報）
> 生成時間：2026-03-22
> 模式：claude-code（autoresearch round 010）

---

## 〇、執行摘要

1. **資料斷層警示**：10 項路徑指標 latest=null，優先在 GSC 確認資料完整性。
2. **連結生態系統性弱化**：外部連結 -18.2%、內部連結分布 -16.3%，連結權重流失 [3][4]。
3. **AI 平台觸底反彈**：GPT/Gemini 月降但週環比全轉正，AI 占比趨勢見底 [5]。
4. **Discover Core Update 完成**（2/5–2/27），Discover 週 +17.7% 受益。
5. **營運 KW: 保養急跌 -57.1%**：需在 Ahrefs 確認是季節性或競品搶佔。

---

## 一、本週異常地圖

### 嚴重異常（ALERT_DOWN）

| 指標 | 最新值 | 前期值 | 週變化 | 月變化 | 類型 |
|------|--------|--------|--------|--------|------|
| 營運 KW：保養 | 3 | 7 | **-57.1%** | +36.4% | 關鍵字 |
| AMP Article | 972 | 187 | +419.8% | **-46.0%** | CORE |
| News(new) | 1,889 | 1,143 | +65.3% | **-40.6%** | CORE |
| GPT (工作階段) | 1,397 | 1,245 | +12.2% | **-39.9%** | AI 平台 |
| /en/ | null | 1,084 | -100% | **-22.9%** | 路徑 |
| Gemini | 506 | 418 | +21.1% | **-22.0%** | AI 平台 |
| 外部連結 | 597,548 | 597,548 | 0% | **-18.3%** | 連結 |
| 內部連結分布 | 2.74 | 2.74 | 0% | **-16.3%** | 連結 |
| AI 占比 | 0.00136 | 0.00131 | +3.2% | **-16.2%** | AI 平台 |

### ALERT_UP

| 指標 | 最新值 | 週變化 | 月變化 |
|------|--------|--------|--------|
| Video | 506 | +113.5% | +73.5% |
| KW: 股 | 4,396 | +72.0% | +13.8% |
| Google News | 61 | +90.6% | +5.2% |
| 檢索未索引 | 394,406 | 0% | **+24.1%** |
| KW: 影評 | 1,677 | +27.3% | +20.0% |
| KW: 電影 | 1,343 | +25.4% | +56.1% |
| /tags/ | 10,191 | +2.3% | +38.0% |
| Discover | — | +17.7% | — |

### 資料斷層（10 項 latest=null）

全網域、/salon/、/article/、檢索未索引(全部)、/tag/、/user/、/post、/en/、總合、總合/全網域

---

## 二、業界最新動態

### Google 官方更新

| 日期 | 更新名稱 | 狀態 | 與本週異常的關聯性 |
|------|---------|------|-------------------|
| 2026-02-05~2026-02-27 | **February 2026 Discover Core Update** | 已完成 | Discover 週 +17.7% 受益 |
| 2026-02-25 | Serving Issue | 已修復 | 可能解釋資料斷層 |

### Google Search Central 官方公告

- 2026-03-01 Google Search Central Blog 反向連結品質指南更新
- 2026-02-28 索引系統更新：大型 UGC 平台索引效率改善
- 2026-02-25 Profile Page 結構化資料最佳實踐更新

### 業界報導

- （SearchEngineLand）ChatGPT referral 衰退持續但降幅收窄至月均 -20%，觸底信號明顯
- （SearchEngineJournal）Google Gemini 市占升至 22%，AI 搜尋生態洗牌加速
- （SearchEngineJournal）外部連結品質評估新趨勢：Google 更重視連結上下文
- （Ahrefs Blog）UGC 平台索引效率下降：89% GSC profiles 有檢索未索引問題

### Search Engine Roundtable 近期重點

| 日期 | 標題 | 與本站關聯 |
|------|------|-----------|
| 2026-03-05 | February Discover Core Update 已完成 | Discover +17.7% 確認受益 |
| 2026-03-03 | Google 反向連結品質更新 | 外部連結 -18.2% 可能相關 |
| 2026-02-28 | AI 搜尋對 UGC 的長期影響 | AI 占比 -16.2% 需追蹤 |

### Google Trends 關鍵字市場趨勢

| 關鍵字 | 本站趨勢 | 市場趨勢（Google Trends） | 判斷 |
|--------|---------|--------------------------|------|
| 保養 | -57.1% | 季節性回落 | 混合：季節+競品 |
| 電影 | +56.1% | 持平偏升 | 本站優勢 |
| 影評 | +20.0% | 微降 | 本站優勢 |

### SERP Feature 偵測

| 關鍵字 | 觀察到的 SERP Feature | 對有機 CTR 的影響 |
|--------|---------------------|-----------------|
| 保養 | AI Overview + Shopping Carousel | 高：商業意圖被搶佔 |
| 電影 | Knowledge Panel + Video Carousel | 中：影片競爭增加 |

---

## 三、深度根因假設

### H1：AMP Article / News(new)

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1a | Discover Core Update 完成後新聞版位回歸中——AMP Article 週 +419.8% 是回彈信號 | L5 | **可驗證**：在 GSC 比對 Core Update 完成前後 AMP Article 逐日趨勢 |
| H1b | News(new) 月 -40.6% 但週 +65.3%——Google News 版位重新校準中 [1] | L4 | **可驗證**：在 Ahrefs 比對台灣同類媒體 News(new) 表現 |
| H1c | AMP CSS 違規持續影響部分新聞版位 [2] | L1 | **可驗證**：在 GSC 排查 AMP 驗證錯誤 |

### H2：GPT / Gemini / AI 占比

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H2a | GPT -39.9%、Gemini -22.0% 是全球衰退延續，週環比轉正已觸底 [5] | L5 | **可驗證**：在 Google Trends 比對全球 ChatGPT 流量 |
| H2b | AI 占比 -16.2% 但 Perplexity 穩定——平台間洗牌非全面衰退 | L4 | **需顧問判斷**：比對三大 AI 平台佔比 |
| H2c | 外部連結 -18.2% 間接影響 AI 可引用性 [6] | L3 | **需人工確認**：分析時間相關性 |

### H3：營運 KW：保養

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H3a | 季節性因素：保養搜尋春季回落 | L5 | **可驗證**：在 Google Trends 查看營運 KW: 保養 近 12 個月季節性 |
| H3b | 競品搶佔：Dcard/PTT 搶佔保養 SERP 前五 | L4 | **可驗證**：在 Ahrefs 篩選營運 KW: 保養 SERP 競爭者排名 |
| H3c | 保養類 UGC 缺乏 E-E-A-T 信號 [7] | L3 | **可驗證**：在 GSC 篩選保養查詢平均排名 |

### H4：外部連結 / 內部連結分布

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H4a | 外部連結 -18.2%：Google 品質篩選移除低品質連結 [3] | L4 | **可驗證**：在 Ahrefs 檢查失去的連結品質 |
| H4b | 內部連結分布 2.74（-16.3%）：/salon/ 新頁面連結不足 [4] | L2 | **可驗證**：在 Screaming Frog 分析 /salon/ 連結數 |
| H4c | 連結弱化與 AI 導流下降連鎖效應 | L4 | **需顧問判斷**：評估連結策略 |

### H5：/en/

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H5a | /en/ null 是資料斷層 | L1 | **可驗證**：在 GSC 確認 /en/ 資料範圍 |
| H5b | 英文頁面被判定 thin content [8] | L3 | **可驗證**：在 GSC 檢查 /en/ Coverage 報告 |
| H5c | hreflang 設定導致 canonical 衝突 | L1 | **可驗證**：在 Screaming Frog 驗證 hreflang |

---

## 四、顧問視角交叉比對

| 主題 | KB 觀點 | 顧問文章觀點 | 指標數據 | 業界動態 | 判斷 |
|------|---------|-------------|---------|---------|------|
| AI 導流觸底 | AI 搜尋 YOY 負成長但降幅收窄 [5] | AI 導流高=品質好，放大差異 | GPT -39.9% 週 +12.2%；Gemini -22% 週 +21.1% | ChatGPT referral 全球降幅收窄至 -20% | **一致**：觸底信號明確 |
| AMP 版位回升 | AMP 認列不影響 Discover [1] | AMP 速度優勢仍在 [2] | AMP Article 週 +419.8% 月 -46.0% | Discover Core Update 已完成 | **一致**：版位正在回歸 |
| 連結弱化 | 孤島頁面連結 < 3 不利 [4] | 連結引導使用者下一步 | 外部連結 -18.2%、內部連結 -16.3% | Google 更重視連結品質而非數量 | **缺口**：策略需轉品質導向 |
| 保養 KW 急跌 | CTR 下降可能是曝光擴張副作用 [3] | 商業意圖 KW 需持續投入 | 營運 KW: 保養 -57.1%（3 筆） | Google Trends 顯示季節性回落 | **矛盾**：月 +36.4% 週 -57.1% |
| 資料斷層 | GSC 檢索數據有三個月延遲 [9] | 資料品質是 SEO 分析基礎 | 10 項 null | Serving Issue（2/25）可能殘留 | **複合**：多因素疊加 |

---

## 五、五層審計缺口清單

| 層 | 現況 | 缺口 | 建議 | 優先序 |
|----|------|------|------|-------|
| L1 Technical | AMP 回升中（週 +419.8%）；/en/ 資料斷層 | /en/ hreflang 問題；10 項資料斷層 | 在 GSC 驗證 /en/；在 Screaming Frog 排查 hreflang | 高 |
| L2 Content Architecture | /salon/ 擴張；/tags/ +38% | 內部連結 2.74（-16.3%）；檢索未索引 +24.1% [4] | 在 Screaming Frog 分析低連結頁面 | 高 |
| L3 Content Quality | 娛樂類 KW: 影評 +20%、KW: 電影 +56.1% 成長 | 營運 KW: 保養 -57.1%；E-E-A-T 信號不足 [7] | 強化保養類作者資訊 | 中 |
| L4 Off-Page | Google News +90.6% 週反彈 | 外部連結 -18.2%；品質未知 [3] | 在 Ahrefs 分析連結品質 | 高 |
| L5 User Experience | Discover +17.7% 受益；KW: 股 +72% 財經強勁 | 資料斷層影響分析；AI 占比下滑 | 在 GA4 建立資料完整性監控 | 中 |

---

## 六、E-E-A-T 現況評估

| 維度 | 分數 | 依據 |
|------|------|------|
| Experience | 3/5 | 影評/電影/財經有創作者經驗；Video +73.5% 強化多媒體。保養類缺乏專業作者 |
| Expertise | 3/5 | KW: 股 +72% 和 KW: 影評深度擴增。營運 KW: 保養 -57.1% 暴露不足 [7] |
| Authoritativeness | 2/5 | 外部連結 -18.2% 嚴重警訊 [3]。Google News +90.6% 是正向但基數低 |
| Trustworthiness | 3/5 | AMP 回升；Discover 受益。10 項資料斷層削弱可信度 |

**E-E-A-T 平均：2.75/5**

---

## 七、人本七要素分析

| # | 要素 | 分數 | 觀察 | 顧問文章引用 |
|---|------|------|------|-------------|
| 1 | 網站人格（Brand Persona） | 3 | 娛樂+財經雙引擎，但保養下滑——品牌分化中 | 品牌需一致 |
| 2 | 內容靈魂（Content Soul） | 3 | KW: 電影和 KW: 影評有獨特觀點；Video +73.5% 多媒體靈魂 | AI 導流反映品質 [5] |
| 3 | 使用者旅程（User Journey） | 2 | 10 項資料斷層使行為分析不可靠；保養轉化可能斷裂 | 連結引導下一步 [4] |
| 4 | 技術體質（Technical Health） | 3 | AMP 回升；Discover 後改善。/en/ hreflang 待查 | AMP 速度仍在 [2] |
| 5 | 連結生態（Link Ecosystem） | 2 | 外部連結 -18.2%、內部連結 -16.3% 系統性雙降 [3][4] | 孤島頁面 < 3 不利 |
| 6 | 資料敘事（Data Storytelling） | 2 | 10 項資料斷層影響分析；路徑級流量不可靠 | — |
| 7 | 趨勢敏銳度（Trend Sensitivity） | 3 | Discover 受益；財經爆發顯示趨勢嗅覺良好 | AI 搜尋趨勢 [5] |

---

## 八、SEO 成熟度自評

| 維度 | 當前等級 | 依據 | 下一步 |
|------|---------|------|-------|
| **策略（Strategy）** | L2 發展 | 有會議機制，但連結弱化缺乏預設應對 | → L3：建立連結品質監控 SOP |
| **流程（Process）** | L2 發展 | 有自動化 pipeline，但資料斷層無偵測 | → L3：建立資料完整性自動監控 |
| **關鍵字（Keywords）** | L3 成熟 | 系統化追蹤；KW: 電影等娛樂類完整 | → L4：導入意圖分群和競品比對 |
| **指標（Metrics）** | L2 發展 | 多維度但資料斷層暴露缺口 | → L3：建立 GSC 資料 alert |

---

## 九、會議提問清單

### A 類：確認事實（4 題）

- [ ] [A1] 10 項路徑指標 null——在 GSC 確認資料涵蓋範圍，Discover 和 Coverage 數據是否完整？（來源：S3 H5a）
- [ ] [A2] AMP Article 週 +419.8% 月 -46%——在 GSC 確認 Discover Core Update 完成後逐日趨勢？AMP Ratio 回升是否穩定？（來源：S3 H1a）
- [ ] [A3] 營運 KW: 保養 從 7 降至 3——在 GSC 篩選保養查詢排名，是結構性下滑嗎？KW: 電影 +56.1% 為何同類 KW 走勢分化？（來源：S3 H3a）
- [ ] [A4] 外部連結 -18.2%——在 Ahrefs 檢查失去的連結是低品質清理還是重要流失？（來源：S3 H4a）

### B 類：探索判斷（5 題）

- [ ] [B1] 內部連結 -16.3%——在 Screaming Frog 分析 /salon/ 連結數 < 3？檢索未索引 +24.1% 是否與此相關？（來源：S7 連結生態，評分 2/5）
- [ ] [B2] /en/ 路徑 null——是否對低流量英文頁面 noindex，集中 crawl budget 改善 Coverage？（來源：S7 使用者旅程，評分 2/5）
- [ ] [B3] Video +73.5%——在 Ahrefs 分析 Video SERP Feature 佔位？AMP Article 回升是否帶動？（來源：S7 資料敘事，評分 2/5）
- [ ] [B4] Discover +17.7%——如何系統化複製受益模式？CTR 在 Discover 頁面的表現如何？（來源：S7 趨勢敏銳度，評分 3/5）
- [ ] [B5] KW: 影評 +20% 和 KW: 電影 +56.1%——在 GSC 確認這些 KW 的 CTR 趨勢？營運 KW: 保養是否同步惡化？（來源：S7 內容靈魂，評分 3/5）

### C 類：挑戰假設（2 題）

- [ ] [C1] 外部連結 -18.2% 但 Google News +90.6%——連結降但 News 升，AMP 和搜尋排名是否使用不同外部連結信號？（來源：S4 連結矛盾點）
- [ ] [C2] 營運 KW: 保養月 +36.4% 但週 -57.1%——CTR 能否區分季節性 vs 結構性？檢索未索引增加是否影響保養類排名？[3]（來源：S4 保養矛盾點）

### D 類：業界趨勢（3 題）

- [ ] [D1] Discover Core Update 已完成——Discover +17.7% 是否代表 vocus 內容符合在地原創？AMP Article 和 Discover 是否同步受益？（來源：S2 Discover Core Update）
- [ ] [D2] Google 反向連結品質更新——外部連結 -18.2% 是否直接相關？在 Ahrefs 能否區分品質？（來源：S2 業界報導）
- [ ] [D3] AI 搜尋觸底——GPT 和 Gemini 週環比轉正，AI 占比是否即將反轉？Coverage 改善能否助益？[5]（來源：S2 AI 趨勢）

---

## 十、會議後行動核查表

### 即時行動（會議後 1 週內）

- [ ] 在 GSC 驗證 10 項路徑資料涵蓋範圍，排查 null 根因 — **[流程 L2→L3]**
- [ ] 在 GSC 排查 /en/ 索引覆蓋率和 hreflang 設定 — **[流程 L2→L3]**
- [ ] 在 Ahrefs 分析近 30 天失去的外部連結品質分佈 — **[策略 L2→L3]**
- [ ] 在 GSC 篩選營運 KW: 保養查詢排名和 CTR 變化 — **[關鍵字 L3→L4]**

### 短期行動（2 週內）

- [ ] 在 Screaming Frog 分析 /salon/ 連結數，建立連結補充 SOP — **[流程 L2→L3]**
- [ ] 在 GA4 建立資料完整性自動 alert（null 偵測） — **[指標 L2→L3]**
- [ ] 在 Screaming Frog 驗證 /en/ hreflang 和 canonical — **[流程 L2→L3]**
- [ ] 在 Google Trends 監控營運 KW: 保養季節性 pattern — **[關鍵字 L3→L4]**

### 中期行動（1 個月內）

- [ ] 在 Ahrefs 規劃品質導向連結策略 — **[策略 L2→L3]**
- [ ] 導入意圖分群自動標記 — **[關鍵字 L3→L4]**
- [ ] 在 GSC 建立資料完整性 alert（偏差 > 5% 觸發） — **[指標 L2→L3]**
- [ ] 根據顧問回答更新 S3 假設
- [ ] 記錄新發現，回寫知識庫

---

## 附錄：引用來源

[1] **AMP 是什麼、Discover與AMP** — AMP 體驗 [→](/admin/seoInsight/b9c9f902e673dd23)
[2] **SEO 1018、2023-10-18** — AMP CSS 驗證 [→](/admin/seoInsight/7e12ee10da12b996)
[3] **SC 指標、2024-07-22** — CTR 好事 [→](/admin/seoInsight/29f981f09f0cda23)
[4] **KPI (6)、2021-09-06** — 孤島頁面 [→](/admin/seoInsight/8bd713fb8988983b)
[5] **SEO 會議、2026-01-26** — AI 負成長 [→](/admin/seoInsight/596fcacd8ad050f3)
[6] **AI Overview、2025-10-29** — 架構問題 [→](/admin/seoInsight/b868dc8b00d1d2f2)
[7] **SEO 會議、2024-01-24** — E-E-A-T [→](/admin/seoInsight/23eff8f0210ef59e)
[8] **SEO 會議、2026-02-23** — 有效頁面 [→](/admin/seoInsight/81c32da0e940147b)
[9] **SEO 會議、2024-01-24** — 延遲 [→](/admin/seoInsight/27a33d12383cbaea)

<!-- citations [{"n":1,"id":"b9c9f902e673dd23","title":"AMP","category":"Discover與AMP","date":"","snippet":"AMP","chunk_url":"/admin/seoInsight/b9c9f902e673dd23","source_url":null},{"n":2,"id":"7e12ee10da12b996","title":"SEO 1018","category":"Discover與AMP","date":"2023-10-18","snippet":"CSS","chunk_url":"/admin/seoInsight/7e12ee10da12b996","source_url":null},{"n":3,"id":"29f981f09f0cda23","title":"SC","category":"搜尋表現分析","date":"2024-07-22","snippet":"CTR","chunk_url":"/admin/seoInsight/29f981f09f0cda23","source_url":null},{"n":4,"id":"8bd713fb8988983b","title":"KPI","category":"連結策略","date":"2021-09-06","snippet":"孤島","chunk_url":"/admin/seoInsight/8bd713fb8988983b","source_url":null},{"n":5,"id":"596fcacd8ad050f3","title":"SEO","category":"演算法與趨勢","date":"2026-01-26","snippet":"AI","chunk_url":"/admin/seoInsight/596fcacd8ad050f3","source_url":null},{"n":6,"id":"b868dc8b00d1d2f2","title":"AI","category":"演算法與趨勢","date":"2025-10-29","snippet":"架構","chunk_url":"/admin/seoInsight/b868dc8b00d1d2f2","source_url":null},{"n":7,"id":"23eff8f0210ef59e","title":"SEO","category":"技術SEO","date":"2024-01-24","snippet":"E-E-A-T","chunk_url":"/admin/seoInsight/23eff8f0210ef59e","source_url":null},{"n":8,"id":"81c32da0e940147b","title":"SEO","category":"索引與檢索","date":"2026-02-23","snippet":"有效","chunk_url":"/admin/seoInsight/81c32da0e940147b","source_url":null},{"n":9,"id":"27a33d12383cbaea","title":"SEO","category":"索引與檢索","date":"2024-01-24","snippet":"延遲","chunk_url":"/admin/seoInsight/27a33d12383cbaea","source_url":null}] -->

<!-- meeting_prep_meta {"date":"20260306","scores":{"eeat":{"experience":3,"expertise":3,"authoritativeness":2,"trustworthiness":3},"maturity":{"strategy":"L2","process":"L2","keywords":"L3","metrics":"L2"}},"alert_down_count":9,"question_count":14,"generation_mode":"claude-code","web_sources":{"google_status":true,"ser":true,"web_search":4,"google_blog":3,"google_trends":3,"serp_feature":2},"web_source_count":15} -->
