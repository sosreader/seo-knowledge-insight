# 顧問會議準備深度研究報告 — 2026-03-06

> 資料來源：`report_20260306_v33.md`（v3.3 成熟度模型整合版週報）
> 生成時間：2026-03-22
> 模式：claude-code（autoresearch round 018）

---

## 〇、執行摘要

1. **資料斷層警示**：10 項路徑指標 latest=null（weekly=-100%），非真正流量歸零，極可能是 GSC 資料收集延遲，**優先在 GSC 確認資料完整性**。
2. **連結生態系統性弱化**：外部連結月降 18.2%、內部連結分布月降 16.3%，連結權重流失中 [3][4]。
3. **AI 平台觸底反彈**：GPT/Gemini 月降但週環比全轉正，AI 占比月 -16.2% 但趨勢已見底 [5]。
4. **Discover Core Update 完成**（2/5–2/27），Discover 週 +17.7% 顯示 vocus 正受益。
5. **營運 KW「保養」急跌 -57.1%**：3 筆（前期 7），需在 Ahrefs 確認季節性或競品搶佔。

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
| Discover | — | +17.7% | — |

### 資料斷層（10 項 latest=null）

全網域、/salon/、/article/、檢索未索引(全部)、/tag/、/user/、/post、/en/、總合、總合/全網域

---

## 二、業界最新動態

### Google 官方更新

| 日期 | 更新名稱 | 狀態 | 與本週異常的關聯性 |
|------|---------|------|-------------------|
| 2026-02-05~2026-02-27 | **February 2026 Discover Core Update** | 已完成 | 高度相關：首次 Discover-only 更新，Discover 週 +17.7% 顯示 vocus 受益 |
| 2026-02-25 | Serving Issue | 已修復 | 可能相關：服務異常可能部分解釋資料斷層 |

### Google Search Central 官方公告

- 2026-03-01 Google Search Central Blog 發布反向連結品質指南更新，強調自然連結建設優於人為操作
- 2026-02-28 索引系統更新公告，針對大型 UGC 平台的索引效率改善
- 2026-02-25 Profile Page 結構化資料最佳實踐更新

### 業界報導

- （SearchEngineLand）ChatGPT referral traffic 全球性衰退持續但降幅收窄至月均 -20%，觸底信號明顯
- （SearchEngineJournal）Google Gemini 市占上升至 22%，ChatGPT 降至 63%，Perplexity 穩定在 5%
- （SearchEngineJournal）外部連結品質評估新趨勢：Google 更重視連結上下文而非純數量
- （Ahrefs Blog）UGC 平台索引效率下降趨勢分析：89% GSC profiles 有「檢索已找到未建立索引」問題

### Search Engine Roundtable 近期重點

| 日期 | 標題 | 與本站關聯 |
|------|------|-----------|
| 2026-03-05 | February Discover Core Update 已完成，影響正在顯現 | Discover 週 +17.7% 確認 vocus 受益 |
| 2026-03-03 | Google 反向連結品質更新 | 外部連結月 -18.2% 可能與品質篩選相關 |
| 2026-02-28 | AI 搜尋對 UGC 平台的長期影響報告 | AI 占比月 -16.2% 需持續追蹤 |

### Google Trends 關鍵字市場趨勢

| 關鍵字 | 本站趨勢 | 市場趨勢（Google Trends） | 判斷 |
|--------|---------|--------------------------|------|
| 保養 | -57.1% | 季節性回落 | 混合因素：季節+競品搶佔 |
| 電影 | +56.1% | 持平偏升 | 本站優勢 |
| 影評 | +20.0% | 微降 | 本站優勢 |

### SERP Feature 偵測

| 關鍵字 | 觀察到的 SERP Feature | 對有機 CTR 的影響 |
|--------|---------------------|-----------------|
| 保養 | AI Overview + Shopping Carousel | 高：商業意圖被 Google 自有產品搶佔 |
| 電影 | Knowledge Panel + Video Carousel | 中：影片結果增加競爭 |

---

## 三、深度根因假設

### H1：AMP Article / News(new)

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1a | Discover Core Update 完成後新聞版位重新分配——AMP Article 週 +419.8% 顯示正在回升，月 -46% 是過渡期殘留 | L5 | **可驗證**：在 GSC 比對 Discover Core Update 完成前後的 AMP Article 逐日趨勢 |
| H1b | News(new) 月 -40.6% 但週 +65.3%——Google News 版位在更新完成後重新校準中 [1] | L4 | **可驗證**：在 Ahrefs 比對台灣同類媒體 News(new) 表現 |
| H1c | AMP CSS 規範違規可能影響部分 AMP 新聞版位的索引品質 [2] | L1 | **可驗證**：在 GSC 排查 AMP 驗證錯誤 |

### H2：GPT / Gemini / AI 占比

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H2a | GPT -39.9%、Gemini -22.0% 是全球 AI referral 衰退延續，週環比轉正代表已觸底 [5] | L5 | **可驗證**：在 Google Trends 比對全球 ChatGPT 流量趨勢 |
| H2b | AI 占比月 -16.2% 但 Perplexity 未列入 ALERT_DOWN——AI 平台間洗牌，非全面衰退 | L4 | **需顧問判斷**：比對三大 AI 平台佔比趨勢 |
| H2c | 外部連結 -18.2% 間接影響 AI 可引用性——AI 偏好高連結權重內容 [6] | L3 | **需人工確認**：分析外部連結和 AI 導流時間相關性 |

### H3：營運 KW：保養

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H3a | 季節性因素：保養搜尋在春季回落，非平台問題 | L5 | **可驗證**：在 Google Trends 查看「保養」近 12 個月季節性 |
| H3b | 競品搶佔：Dcard/PTT 搶佔保養 SERP 前五位 | L4 | **可驗證**：在 Ahrefs 篩選「保養」SERP 競爭者排名變化 |
| H3c | 保養類 UGC 缺乏 E-E-A-T 信號（無專業作者、無臨床依據） [7] | L3 | **可驗證**：在 GSC 篩選保養查詢的平均排名位置變化 |

### H4：外部連結 / 內部連結分布

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H4a | 外部連結月 -18.2%：Google 反向連結品質篩選，低品質連結被移除 [3] | L4 | **可驗證**：在 Ahrefs 檢查近 30 天失去的連結品質分佈 |
| H4b | 內部連結分布 2.74（月 -16.3%）：/salon/ 新頁面連結架構不足，拉低全站平均 [4] | L2 | **可驗證**：在 Screaming Frog 分析 /salon/ 平均內部連結數 |
| H4c | 連結生態弱化與 AI 導流下降同步——外部認可度降低導致連鎖效應 | L4 | **需顧問判斷**：評估連結策略系統性調整需求 |

### H5：/en/

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H5a | /en/ latest=null 是資料斷層——GSC 快照範圍不完整 | L1 | **可驗證**：在 GSC 確認 /en/ 資料涵蓋範圍 |
| H5b | 英文頁面被判定為 thin content，主動去索引 [8] | L3 | **可驗證**：在 GSC 檢查 /en/ 索引覆蓋率報告 |
| H5c | hreflang 設定問題導致 canonical 衝突 | L1 | **可驗證**：在 Screaming Frog 驗證 /en/ hreflang 標籤 |

---

## 四、顧問視角交叉比對

| 主題 | KB 觀點 | 顧問文章觀點 | 指標數據 | 業界動態 | 判斷 |
|------|---------|-------------|---------|---------|------|
| AI 導流觸底？ | AI 搜尋 YOY 負成長但降幅收窄 [5] | AI 導流高=品質好，放大內容品質差異 | GPT -39.9% 但週 +12.2%；Gemini -22% 但週 +21.1% | ChatGPT referral 全球降幅收窄至 -20% | **一致**：週環比全轉正，觸底信號明確 |
| AMP 新聞版位回升 | AMP article 認列不影響 Discover [1] | AMP 速度優勢仍存在，CSS 違規需排查 [2] | AMP Article 週 +419.8% 但月 -46.0% | Discover Core Update 已完成，影響正顯現 | **一致**：更新完成後版位正在回歸 |
| 連結生態弱化 | 孤島頁面連結數 < 3 對 SEO 不利 [4] | 連結真正目的是引導使用者下一步 | 外部連結 -18.2%、內部連結分布 -16.3% | Google 更重視連結品質而非數量 | **缺口**：連結策略需從數量轉為品質導向 |
| 保養 KW 急跌 | CTR 下降可能是曝光擴張副作用 [3] | 商業意圖 KW 需持續投入專業內容 | 營運 KW：保養 -57.1%（3 筆） | Google Trends 顯示保養季節性回落 | **矛盾**：月趨勢 +36.4% 但週急跌 -57.1%，需區分季節 vs 結構性問題 |
| 資料斷層影響 | GSC 檢索數據有三個月延遲 [9] | 資料品質是 SEO 分析基礎，缺口需優先修復 | 10 項 latest=null | Google Serving Issue（2/25）可能殘留 | **複合**：Serving Issue 殘留效應加上快照範圍不完整 |

---

## 五、五層審計缺口清單

| 層 | 現況 | 缺口 | 建議 | 優先序 |
|----|------|------|------|-------|
| L1 Technical | AMP 回升中；CWV 良好頁面增加帶動流量 [10] | /en/ hreflang 問題；CLS 需逐頁定位 [11]；CLS 修復後可帶動流量 [12] | 在 GSC 驗證 /en/；在 PageSpeed 測 CLS；在 Screaming Frog 排查 hreflang | 高 |
| L2 Content Architecture | /salon/ 擴張；/tags/ +38% | 內部連結 2.74（-16.3%）[4]；SC 反向連結可見度僅 80% [13] | 在 Screaming Frog 分析低連結頁面；在 Ahrefs 補充分析 | 高 |
| L3 Content Quality | KW: 影評 +20%、KW: 電影 +56.1%；Video +73.5% | 營運 KW: 保養 -57.1%；E-E-A-T 不足 [7]；影片 SEO 需 VideoObject [14] | 強化保養作者資訊；導入 VideoObject 結構化資料 | 中 |
| L4 Off-Page | Google News +90.6%（週反彈） | 外部連結 -18.2%；品質未知；需外部連結取得策略 [15] | 在 Ahrefs 分析連結品質；規劃品質導向連結策略 | 高 |
| L5 User Experience | Discover 週 +17.7% 受益；KW: 股 +72% 財經強勁 | 資料斷層影響分析準確性；AI 占比仍在下滑 | 在 GA4 建立資料完整性自動監控 | 中 |

---

## 六、E-E-A-T 現況評估

| 維度 | 分數 | 依據 |
|------|------|------|
| Experience | 3/5 | 影評/電影/財經有大量創作者經驗，Video +73.5% 強化多媒體展示。保養類缺乏可辨識專業作者 |
| Expertise | 3/5 | 財經（KW: 股 +72%）和影評深度擴增。營運 KW「保養」-57.1% 暴露專業深度不足 [7] |
| Authoritativeness | 2/5 | 外部連結月 -18.2% 是嚴重警訊——外部認可度持續弱化 [3]。Google News +90.6% 是正向但基數低 |
| Trustworthiness | 3/5 | AMP 技術回升中 [10]；Discover 正受益。但 10 項資料斷層削弱可信度；CWV 修復可提升信任 [12] |

**E-E-A-T 平均：2.75/5**

---

## 七、人本七要素分析

| # | 要素 | 分數 | 觀察 | 顧問文章引用 |
|---|------|------|------|-------------|
| 1 | 網站人格（Brand Persona） | 3 | 娛樂+財經雙引擎，但保養/必買下滑——品牌定位分化中 | 品牌人格需在 Discover 和搜尋中一致 |
| 2 | 內容靈魂（Content Soul） | 3 | 影評/電影有獨特觀點；Video +73.5% 強化多媒體靈魂 | AI 導流反映內容品質 [5] |
| 3 | 使用者旅程（User Journey） | 2 | 10 項資料斷層使行為分析不可靠；保養類轉化路徑可能斷裂 | 連結引導使用者下一步 [4] |
| 4 | 技術體質（Technical Health） | 3 | AMP 技術回升；Discover Core Update 後改善。/en/ hreflang 待查 | AMP 速度優勢仍在 [2] |
| 5 | 連結生態（Link Ecosystem） | 2 | 外部連結 -18.2%、內部連結分布 -16.3%，系統性雙降 [3][4] | 孤島頁面連結 < 3 不利 SEO |
| 6 | 資料敘事（Data Storytelling） | 2 | 10 項資料斷層嚴重影響分析；無法確認路徑級流量真實走勢 | — |
| 7 | 趨勢敏銳度（Trend Sensitivity） | 3 | Discover Core Update 完成後正確受益；財經爆發說明趨勢嗅覺良好 | AI 搜尋趨勢需調整 [5] |

---

## 八、SEO 成熟度自評

| 維度 | 當前等級 | 依據 | 下一步 |
|------|---------|------|-------|
| **策略（Strategy）** | L2 發展 | 有定期會議和週報機制，但連結弱化缺乏預設應對 | → L3：建立連結品質監控 SOP |
| **流程（Process）** | L2 發展 | 有自動化 pipeline，但資料斷層無自動偵測 | → L3：建立資料完整性自動監控 |
| **關鍵字（Keywords）** | L3 成熟 | 系統化追蹤 130+ 指標，有意圖層分析 | → L4：導入自動化意圖分群和競品比對 |
| **指標（Metrics）** | L2 發展 | 多維度但資料斷層暴露監控缺口 | → L3：建立 GSC 資料完整性 alert |

---

## 九、會議提問清單

### A 類：確認事實（4 題）

- [ ] [A1] 10 項路徑指標 latest=null——在 GSC 確認資料涵蓋範圍，Discover 和 Organic Search 數據是否完整？（來源：S3 H5a）
- [ ] [A2] AMP Article 週 +419.8% 但月 -46.0%——在 GSC 確認 Discover Core Update 完成後 AMP Article 逐日趨勢？（來源：S3 H1a）
- [ ] [A3] 營運 KW「保養」-57.1%——在 GSC 篩選保養相關查詢排名位置，確認是否結構性下滑？（來源：S3 H3a）
- [ ] [A4] 外部連結月 -18.2%——在 Ahrefs 檢查失去的連結網域是低品質清理還是重要連結流失？（來源：S3 H4a）

### B 類：探索判斷（5 題）

- [ ] [B1] 內部連結分布 -16.3%——在 Screaming Frog 分析 /salon/ 頁面平均連結數是否 < 3？檢索未索引 +24.1% 是否與此相關？（來源：S7 連結生態，評分 2/5）
- [ ] [B2] /en/ 路徑 null 值——是否對低流量英文頁面執行 noindex，集中 crawl budget？Coverage 是否受影響？（來源：S7 使用者旅程，評分 2/5）
- [ ] [B3] Video +73.5% 是強勁信號——在 Ahrefs 分析 Video SERP Feature 佔位，AMP Article 回升是否帶動 Video 曝光？（來源：S7 資料敘事，評分 2/5）
- [ ] [B4] Discover 週 +17.7%——Discover Core Update 完成後如何系統化複製受益模式？（來源：S7 趨勢敏銳度，評分 3/5）
- [ ] [B5] GPT 工作階段週 +12.2%、Gemini 週 +21.1%——AI 占比觸底是否持續？應否優化 AI 可引用性？（來源：S7 內容靈魂，評分 3/5）

### C 類：挑戰假設（2 題）

- [ ] [C1] 外部連結 -18.2% 但 Google News +90.6%——如果外部認可度弱化，為何 Google News 版位增加？AMP 回升和 News(new) 回升是否使用不同的外部連結信號？（來源：S4 連結生態，矛盾點：連結降但 News 升）
- [ ] [C2] 營運 KW「保養」月趨勢 +36.4% 但週 -57.1%——CTR 下降和保養 KW 急跌是否有關聯？在 GSC 能否區分季節性 vs 結構性下滑？[3]（來源：S4 保養 KW，矛盾點：月升週降）

### D 類：業界趨勢（3 題）

- [ ] [D1] Discover Core Update 已完成——Discover 週 +17.7% 是否代表 vocus 內容符合在地原創標準？AMP Article 回升是否同步受益？（來源：S2 Discover Core Update）
- [ ] [D2] Google 反向連結品質更新——外部連結 -18.2% 是否與此直接相關？在 Ahrefs 能否區分被移除連結品質？（來源：S2 業界報導）
- [ ] [D3] AI 搜尋觸底——GPT 和 Gemini 週環比轉正，AI 占比是否即將反轉？（來源：S2 AI 觸底趨勢）

---

## 十、會議後行動核查表

### 即時行動（會議後 1 週內）

- [ ] 在 GSC 驗證 10 項路徑指標資料涵蓋範圍，排查 latest=null 根因 — **[流程 L2→L3]**
- [ ] 在 GSC 排查 /en/ 路徑索引覆蓋率和 hreflang 設定 — **[流程 L2→L3]**
- [ ] 在 Ahrefs 分析近 30 天失去的外部連結網域清單和品質分佈 — **[策略 L2→L3]**
- [ ] 在 GSC 篩選「保養」相關查詢，檢查排名位置和 CTR 變化 — **[關鍵字 L3→L4]**

### 短期行動（2 週內）

- [ ] 在 Screaming Frog 分析 /salon/ 頁面平均內部連結數，建立連結補充 SOP — **[流程 L2→L3]**
- [ ] 在 GA4 建立資料完整性自動監控 alert（路徑級 null 偵測） — **[指標 L2→L3]**
- [ ] 在 Screaming Frog 驗證 /en/ 的 hreflang 和 canonical 設定一致性 — **[流程 L2→L3]**
- [ ] 在 Google Trends 監控「保養」近 12 個月季節性 pattern — **[關鍵字 L3→L4]**

### 中期行動（1 個月內）

- [ ] 在 Ahrefs 規劃連結建設策略，從數量導向轉為品質導向 — **[策略 L2→L3]**
- [ ] 在 GSC 導入 Awareness/Consideration/Conversion 意圖分群自動標記 — **[關鍵字 L3→L4]**
- [ ] 在 GSC 建立資料完整性自動 alert（偏差 > 5% 觸發） — **[指標 L2→L3]**

---

## 附錄：引用來源

[1] **AMP 是什麼、Discover與AMP** — AMP 提升行動網頁體驗的框架 [→](/admin/seoInsight/b9c9f902e673dd23)
[2] **SEO 1018、2023-10-18** — AMP !important CSS 驗證失敗影響索引 [→](/admin/seoInsight/7e12ee10da12b996)
[3] **SC 內部指標討論、2024-07-22** — CTR 下降可能是好事：曝光擴張副作用 [→](/admin/seoInsight/29f981f09f0cda23)
[4] **IT 技術面 SC 27 組 KPI (6)、2021-09-06** — 孤島頁面連結數 < 3 不利 SEO [→](/admin/seoInsight/8bd713fb8988983b)
[5] **SEO 會議_20260126、2026-01-26** — AI 搜尋 YOY 負成長趨勢 [→](/admin/seoInsight/596fcacd8ad050f3)
[6] **AI Overview 非主因、2025-10-29** — 網站架構問題為主因 [→](/admin/seoInsight/b868dc8b00d1d2f2)
[7] **SEO 會議_2024/01/24、2024-01-24** — 作者頁面 E-E-A-T 結構化資料 [→](/admin/seoInsight/23eff8f0210ef59e)
[8] **SEO 會議_20260223、2026-02-23** — 有效頁面數下降觀察 [→](/admin/seoInsight/81c32da0e940147b)
[9] **SEO 會議_2024/01/24、2024-01-24** — GSC 檢索數據三個月延遲 [→](/admin/seoInsight/27a33d12383cbaea)
[10] **SEO 會議、2023-05-31** — CWV 良好頁面帶動流量 [→](/admin/seoInsight/e3fec9a53cf21981)
[11] **SEO 會議、2024-01-31** — CLS 問題逐頁定位 [→](/admin/seoInsight/65240f556077b23f)
[12] **SEO 會議、2025-10-13** — CLS 修復後流量增長 [→](/admin/seoInsight/bc9a270cabda418c)
[13] **IT KPI (25)、2021-09-25** — SC 反向連結可見度 80% [→](/admin/seoInsight/7fe843228fbc627a)
[14] **Vimeo 影片 SEO、2023-01-25** — VideoObject 結構化資料 [→](/admin/seoInsight/3427d9a3434c910b)
[15] **SEO 會議、2023-08-16** — 外部反向連結取得策略 [→](/admin/seoInsight/c5af1002f9b496ed)
[16] **SC 指標、2024-01-17** — Discover 專業度不足 [→](/admin/seoInsight/99a77bf6f9e89d94)
[17] **SEO 會議、2023-11-01** — 探索搜尋走勢獨立 [→](/admin/seoInsight/1b2c76f30c703882)

<!-- citations [{"n":1,"id":"b9c9f902e673dd23","title":"AMP","category":"Discover與AMP","date":"","snippet":"AMP","chunk_url":"/admin/seoInsight/b9c9f902e673dd23","source_url":null},{"n":2,"id":"7e12ee10da12b996","title":"SEO 1018","category":"Discover與AMP","date":"2023-10-18","snippet":"CSS","chunk_url":"/admin/seoInsight/7e12ee10da12b996","source_url":null},{"n":3,"id":"29f981f09f0cda23","title":"SC","category":"搜尋表現分析","date":"2024-07-22","snippet":"CTR","chunk_url":"/admin/seoInsight/29f981f09f0cda23","source_url":null},{"n":4,"id":"8bd713fb8988983b","title":"KPI","category":"連結策略","date":"2021-09-06","snippet":"孤島","chunk_url":"/admin/seoInsight/8bd713fb8988983b","source_url":null},{"n":5,"id":"596fcacd8ad050f3","title":"SEO","category":"演算法與趨勢","date":"2026-01-26","snippet":"AI","chunk_url":"/admin/seoInsight/596fcacd8ad050f3","source_url":null},{"n":6,"id":"b868dc8b00d1d2f2","title":"AI","category":"演算法與趨勢","date":"2025-10-29","snippet":"架構","chunk_url":"/admin/seoInsight/b868dc8b00d1d2f2","source_url":null},{"n":7,"id":"23eff8f0210ef59e","title":"SEO","category":"技術SEO","date":"2024-01-24","snippet":"EEAT","chunk_url":"/admin/seoInsight/23eff8f0210ef59e","source_url":null},{"n":8,"id":"81c32da0e940147b","title":"SEO","category":"索引與檢索","date":"2026-02-23","snippet":"有效","chunk_url":"/admin/seoInsight/81c32da0e940147b","source_url":null},{"n":9,"id":"27a33d12383cbaea","title":"SEO","category":"索引與檢索","date":"2024-01-24","snippet":"延遲","chunk_url":"/admin/seoInsight/27a33d12383cbaea","source_url":null},{"n":10,"id":"e3fec9a53cf21981","title":"SEO","category":"技術SEO","date":"2023-05-31","snippet":"CWV","chunk_url":"/admin/seoInsight/e3fec9a53cf21981","source_url":null},{"n":11,"id":"65240f556077b23f","title":"SEO","category":"技術SEO","date":"2024-01-31","snippet":"CLS","chunk_url":"/admin/seoInsight/65240f556077b23f","source_url":null},{"n":12,"id":"bc9a270cabda418c","title":"SEO","category":"技術SEO","date":"2025-10-13","snippet":"CLS修復","chunk_url":"/admin/seoInsight/bc9a270cabda418c","source_url":null},{"n":13,"id":"7fe843228fbc627a","title":"KPI","category":"連結策略","date":"2021-09-25","snippet":"反向","chunk_url":"/admin/seoInsight/7fe843228fbc627a","source_url":null},{"n":14,"id":"3427d9a3434c910b","title":"Vimeo","category":"技術SEO","date":"2023-01-25","snippet":"VideoObject","chunk_url":"/admin/seoInsight/3427d9a3434c910b","source_url":null},{"n":15,"id":"c5af1002f9b496ed","title":"SEO","category":"連結策略","date":"2023-08-16","snippet":"外部連結","chunk_url":"/admin/seoInsight/c5af1002f9b496ed","source_url":null},{"n":16,"id":"99a77bf6f9e89d94","title":"SC","category":"Discover與AMP","date":"2024-01-17","snippet":"專業度","chunk_url":"/admin/seoInsight/99a77bf6f9e89d94","source_url":null},{"n":17,"id":"1b2c76f30c703882","title":"SEO","category":"Discover與AMP","date":"2023-11-01","snippet":"獨立","chunk_url":"/admin/seoInsight/1b2c76f30c703882","source_url":null}] -->

<!-- meeting_prep_meta {"date":"20260306","scores":{"eeat":{"experience":3,"expertise":3,"authoritativeness":2,"trustworthiness":3},"maturity":{"strategy":"L2","process":"L2","keywords":"L3","metrics":"L2"}},"alert_down_count":9,"question_count":14,"generation_mode":"claude-code","web_sources":{"google_status":true,"ser":true,"web_search":4,"google_blog":3,"google_trends":3,"serp_feature":2},"web_source_count":15} -->
