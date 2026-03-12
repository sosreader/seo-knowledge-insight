# 顧問會議準備深度研究報告 — 2026-03-06

> 資料來源：`metrics_snapshots/20260306-184745.json`（2 週數據，130+ 指標）
> 生成時間：2026-03-12
> 模式：claude-code

---

## 〇、執行摘要

1. **資料斷層警示**：10 項路徑指標 latest=null（weekly=-100%），非真正流量歸零，極可能是 GSC 資料收集延遲或快照範圍不完整，**優先確認資料完整性**。
2. **營運關鍵字顯著衰退**：「保養」週降 57%（7→3）、「必買」週降 13%（1,000→866），需判斷是搜尋意圖轉移還是排名滑落。
3. **AI 可見度月趨勢全面下滑**：AI 占比 -16%、GPT 工作階段 -40%、Gemini -22%，與顧問「AI 導流高=網站健康」的觀點 [14] 形成警訊。
4. **February 2026 Discover Core Update 已完成**（2/5–2/27），首次 Discover-only 更新，強調深度、原創、在地內容——需評估對 vocus 探索流量的中期影響。
5. **外部連結月降 18.2%**，結合內部連結分布月降 16.3%，連結生態出現系統性弱化跡象。

---

## 一、本週異常地圖

### 嚴重異常（weekly < -10% 且 latest 有值）

| 指標 | 最新值 | 前期值 | 週變化 | 月變化 | 嚴重度 |
|------|--------|--------|--------|--------|--------|
| 營運 KW：保養 | 3 | 7 | **-57.1%** | +36.4% | 🔴 極高 |
| 週平均回應時間 | 508ms | 948ms | -46.4% | -59.7% | ✅ 正向（更快） |
| KW: 攻略 | 1,110 | 1,308 | **-15.1%** | +19.8% | 🟡 中 |
| 產品摘要 | 263 | 304 | **-13.5%** | +14.5% | 🟡 中 |
| 營運 KW：必買 | 866 | 1,000 | **-13.4%** | -5.2% | 🟡 中 |
| /user | 3,428 | 3,925 | **-12.7%** | -7.1% | 🟡 中 |

### 資料斷層（latest=null，weekly=-100%）

| 指標 | 前期值 | 月變化 | 判斷 |
|------|--------|--------|------|
| 全網域 | 788,814 | +17.0% | 資料缺失，非真正下降 |
| /salon/ | 88,088 | +153.4% | 資料缺失，月趨勢反而大幅上升 |
| /article/ | 70,766 | +37.4% | 資料缺失 |
| 檢索未索引 (全部) | 394,406 | +30.1% | 資料缺失 |
| /tag/ | 24,866 | -9.8% | 資料缺失，月也微降 |
| /user/ (路徑) | 3,075 | -4.1% | 資料缺失 |
| /post | 1,275 | +8.5% | 資料缺失 |
| /en/ | 1,084 | -22.9% | 資料缺失，月也顯著下降 |
| 總合 | 189,154 | +62.0% | 資料缺失 |
| 總合/全網域 | 0.2398 | +44.7% | 資料缺失 |

### 月趨勢下滑（weekly 穩定/正向，但 monthly < -15%）

| 指標 | 最新值 | 週變化 | 月變化 | 說明 |
|------|--------|--------|--------|------|
| 週平均回應時間 | 508ms | -46.4% | **-59.7%** | 正向——回應更快 |
| AMP Article | 972 | +419.8% | **-46.0%** | 週暴漲但月大降，高波動 |
| AMP Article Ratio | 0.0012 | +449.6% | **-47.0%** | 同上 |
| News(new) | 1,889 | +65.3% | **-40.6%** | 週回升但月仍低 |
| GPT (工作階段) | 1,397 | +12.2% | **-39.9%** | AI 流量月衰退 |
| /en/ | — | -100% | **-22.9%** | 英文版持續萎縮 |
| Gemini | 506 | +21.1% | **-22.0%** | AI 流量月衰退 |
| 外部連結 | 597,548 | 0% | **-18.2%** | 連結流失中 |
| 內部連結分布 | 2.74 | 0% | **-16.3%** | 結構弱化 |
| AI 占比 | 0.136% | +3.2% | **-16.1%** | AI 可見度月降 |

---

## 二、業界最新動態

### Google 官方更新

| 日期 | 事件 | 狀態 | 與本週異常的關聯性 |
|------|------|------|-------------------|
| 2026-02-05 ~ 02-27 | **February 2026 Discover Core Update** | 已完成 | **高度相關**：首次 Discover-only 核心更新。強調深度、原創、在地內容；目前僅影響美國英語用戶，但即將擴展至所有語言。可能影響 vocus 的探索流量中期趨勢 |
| 2026-02-25 | Serving 服務故障 | 已修復 | 可能造成當週數據異常（與 latest=null 資料斷層時間吻合） |

### 業界報導

| 來源 | 標題 | 摘要 | 與本站異常的可能關聯 |
|------|------|------|---------------------|
| Search Engine Land | [Google February 2026 Discover core update is now complete](https://searchengineland.com/google-february-2026-discover-core-update-is-now-complete-469450) | Discover 更新歷時 21 天完成，是 Google 首次公告的 Discover-only 更新 | Discover 流量波動的潛在原因 |
| Search Engine Land | [Organic search is fundamentally disrupted](https://searchengineland.com/organic-search-is-fundamentally-disrupted-heres-what-to-do-about-it-470816) | 73% B2B 網站 2024-2025 年流量顯著下滑，AI Overviews 造成 15-64% 有機流量降幅 | 營運關鍵字下降的宏觀背景 |
| Search Engine Land | [The dark SEO funnel](https://searchengineland.com/the-dark-seo-funnel-why-traffic-no-longer-proves-seo-success-470334) | 流量不再是 SEO 成功的證明，需追蹤轉換路徑 | KPI 重新定義的參考 |
| Google Developers | [Debug Google Search Traffic Drops](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops) | 官方流量下降除錯指南 | 排查 latest=null 的參考流程 |

### Search Engine Roundtable 近期重點

| 日期 | 標題 | 摘要 |
|------|------|------|
| 2026-03-11 | Branded Queries Filter Rolling Out in Search Console | 品牌查詢篩選器正式推出，可獨立分析品牌 vs 非品牌流量 |
| 2026-03-11 | Google explains undocumented way to disavow entire TLDs | John Mueller 揭露可拒絕整個 TLD 的未記錄方法 |
| 2026-03-11 | Google Launches Merchant Center For Agencies | 新的代理商 Merchant Center 體驗 |
| 2026-03-11 | Google Search Your Related Activity Adds Chart | 搜尋歷史新增活動視覺化圖表 |
| 2026-03-10 | Survey: PPC is Harder Than 2 Years Ago | 付費搜尋管理難度增加 |

---

## 三、深度根因假設

### 3.1 營運 KW：保養（週降 57.1%，7→3）

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1 | **排名位移**：Google Discover Core Update（2/27 完成）改變了「保養」相關查詢的排名分布，vocus 文章被更具 E-E-A-T 的競爭者取代 | L3 Content Quality | 需人工確認——GSC 查詢「保養」排名變化 |
| H2 | **搜尋意圖轉移**：AI Overviews 直接回答「保養」類資訊查詢，減少點擊到內容平台的需求 | L5 User Experience | 需人工確認——搜尋「保養」是否出現 AIO |
| H3 | **季節性波動**：3 月初非保養品旺季，加上絕對值極低（3 vs 7），統計雜訊可能性高 | — | 可驗證——比對歷史同期數據 |

### 3.2 KW: 攻略 / 營運 KW：必買（週降 13-15%）

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1 | **SERP 版面改變**：Rich Results（圖片、影片、PAA）佔比增加，壓縮有機結果點擊空間 [5] | L5 User Experience | 可驗證——抽查 SERP 截圖 |
| H2 | **內容新鮮度不足**：攻略/推薦類內容若未定期更新，在 Discover Update 後可能被降權 | L3 Content Quality | 需人工確認——檢查相關文章最後更新日期 |
| H3 | **競爭者內容品質提升**：業界整體 SEO 水準提高，相對排名下降 | L4 Off-Page | 需顧問判斷——競爭分析 |

### 3.3 AI 可見度全面月降（AI 占比 -16%、GPT -40%、Gemini -22%）

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1 | **AI 引用品質門檻提高**：AI 搜尋引擎對引用來源的品質要求提高，vocus UGC 內容不夠結構化 [14] | L3 Content Quality | 需顧問判斷——與「AI 導流越高=網站健康」理論比對 |
| H2 | **技術可解析性不足**：缺乏 FAQ Schema、Answer Card、清晰 H2 結構，AI 無法有效擷取摘要 | L1 Technical | 可驗證——抽查 vocus 熱門文章的 Schema 標記 |
| H3 | **AI 流量計算方式變更**：GA4 或分析工具的 AI 流量辨識邏輯更新，非真正流量下降 | — | 可驗證——比對 referrer 原始資料 |

### 3.4 外部連結月降 18.2% + 內部連結分布月降 16.3%

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1 | **外站連結自然衰退**：引用 vocus 的外部文章過期或刪除 | L4 Off-Page | 可驗證——GSC 外部連結報告 |
| H2 | **內部連結策略缺失**：新增內容未妥善建立延伸閱讀連結，連結密度被稀釋 [18] | L2 Content Architecture | 可驗證——抽查近期文章的內部連結數 |
| H3 | **GSC 連結報告更新週期**：Google 不定期更新連結數據，單次下降可能是報告刷新 | — | 需觀察——下期是否回升 |

### 3.5 資料斷層（10 項 latest=null）

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1 | **快照擷取不完整**：指標快照工具在 3/6 擷取時，GSC 當週數據尚未完全就緒 | — | 可驗證——重新擷取快照 |
| H2 | **Google Serving 故障殘留**：2/25 serving bug 導致部分數據延遲回補 | L1 Technical | 可驗證——GSC 介面直接查看 |
| H3 | **路徑指標統計邏輯變更**：Search Console 對 URL 分群邏輯有更新 | — | 需觀察——是否持續為 null |

---

## 四、顧問視角交叉比對

| 主題 | KB 知識庫觀點 | 顧問文章觀點 | 指標數據 | 業界動態 | 判斷 |
|------|-------------|-------------|---------|---------|------|
| **CTR 下降** | CTR 下降可能是正面訊號——曝光成長超過點擊 [4] | 顧問多次指出 CTR 下降是 SEO 做得好的表現（觸及更多長尾關鍵字）[5] | 本週整體 CTR 數據缺失（latest=null），無法直接判斷 | AI Overviews 計入 GSC 曝光但零點擊，拉低全局 CTR | **一致**：KB 與顧問觀點一致，但需排除 AIO 造成的 CTR 稀釋效應 |
| **AI 流量下降** | AI 搜尋對 YoY 流量呈負成長趨勢 [13] | 「AI 導流高的網站，搜尋流量同時在上升」——AI 是照妖鏡，不是小偷 | AI 占比月降 16%、GPT 工作階段月降 40% | 73% B2B 網站流量顯著下滑，AI Overviews 造成 15-64% 有機流量降幅 | **矛盾**：顧問認為 AI 導流高=健康，但 vocus AI 可見度在下降。需釐清是「內容品質導致 AI 不引用」還是「AI 流量計算方式變更」 |
| **Discover 流量** | Discover 受演算法評分影響，受攻擊或低品質內容會降低分發 [10]；Google News 訂閱可帶動 Discover [12] | 探索是後社群時代的新導流通道，需持續產出新鮮、視覺化、分眾內容 | 資料斷層，無法直接觀察 | Feb 2026 Discover Core Update：強調深度、原創、在地內容 | **缺口**：Discover Update 已完成但尚未評估對 vocus 的影響，且缺少 vocus Discover 專屬數據 |
| **外部連結衰退** | 連結應服務使用者體驗，非僅為排名因素 [18] | 「SEO 核心是找到對的網頁、用對的說明文字、讓對的使用者點擊」 | 外部連結月降 18.2%、內部連結分布月降 16.3% | SER: Google 新增 TLD 整體拒絕功能 | **缺口**：連結衰退趨勢明確但缺少連結品質分析（是否流失的是高價值外鏈） |
| **關鍵字排名觀測** | 關鍵字排名不適合當核心 KPI [15]，應以爬取指標為先驗指標 | SEO KPI 不應以排名為核心，而應看搜尋引擎對網站的爬取數字 | 營運 KW 確實在下降（保養 -57%、必買 -13%） | GSC Branded Queries Filter 正式推出 | **一致**：雖然排名非核心 KPI，但營運關鍵字作為商業指標仍需關注。新的 Branded Queries Filter 可協助分離品牌 vs 非品牌表現 |

---

## 五、五層審計缺口清單

| 層 | 現況 | 缺口 | 建議 | 優先序 |
|----|------|------|------|-------|
| L1 Technical Foundation | 週平均回應時間改善（508ms，月降 60%）；但多項路徑指標 latest=null | **資料收集完整性**：快照機制可能有盲區，無法掌握完整技術健康度 | 1. 驗證快照擷取時機與 GSC API 資料就緒度 2. 建立 null 值自動警示 | 高 |
| L2 Content Architecture | 內部連結分布 2.74（月降 16.3%） | **內部連結密度不足**：新內容未建立足夠的延伸閱讀連結 [18][19] | 1. 建立新文章發布時的內部連結 SOP 2. 定期掃描「孤島頁面」 | 高 |
| L3 Content Quality | 營運 KW 下降，AMP Article 高波動 | **內容新鮮度與深度**：營運相關內容可能未定期更新，Discover Update 偏好「深度、原創、即時」內容 | 1. 盤點營運 KW 對應的 top 文章更新日期 2. 增加專家觀點/第一手經驗 [7] | 高 |
| L4 Off-Page & Authority | 外部連結月降 18.2% | **外鏈自然流失**：缺乏主動的 Digital PR 或內容行銷策略 | 1. 分析流失外鏈來源 2. 評估是否需要內容合作計畫 | 中 |
| L5 User Experience | AI 可見度月降 16% | **AI 時代的內容可解析性**：缺乏 FAQ Schema、Answer Card、結構化摘要 [14] | 1. 熱門文章加入 FAQ Schema 2. 首段加入可被 AI 引用的結論句 | 中 |

---

## 六、E-E-A-T 現況評估

| 維度 | 分數 | 依據 |
|------|------|------|
| **Experience（經驗）** | 3/5 | vocus 平台有大量創作者第一手經驗分享，但缺乏統一的作者署名規範和 Profile Page 結構化資料 [7]。平台屬性（UGC）使得經驗信號分散在個別創作者，非平台整體。 |
| **Expertise（專業性）** | 3/5 | 部分專業領域（如保養、攻略）有深度內容，但整體 UGC 品質參差。KB 搜尋顯示顧問指出 Discover 流量回落原因之一是「Google 認定專業度不足」[8]。營運 KW 下降可能反映特定領域專業內容不足。 |
| **Authoritativeness（權威性）** | 2/5 | 外部連結月降 18.2%，顯示外部認可度下滑。缺乏業界引用或媒體報導的系統性追蹤。AI 可見度月降也暗示 AI 搜尋引擎對 vocus 作為權威來源的引用意願降低 [14]。 |
| **Trustworthiness（可信度）** | 3/5 | 平台本身有基本的內容管理機制，但 UGC 性質使得品質控管較困難。缺乏「最後更新時間」標記和引用來源的系統性要求。 |

**E-E-A-T 平均分：2.75/5**

---

## 七、人本七要素分析

| # | 要素 | 分數 | 觀察 | 顧問文章引用 |
|---|------|------|------|-------------|
| 1 | **網站人格（Brand Persona）** | 3/5 | vocus 定位為「創作者經濟平台」，在搜尋生態中角色明確但與競爭者（Medium、方格子）區隔度待加強 | — |
| 2 | **內容靈魂（Content Soul）** | 3/5 | UGC 模式下有獨特觀點的內容與聚合型內容並存，缺乏平台層級的內容品質信號 | 顧問文章《AI 導流越高搜尋流量越上升》：「AI 淘汰的是靠堆字存活的內容，而不是有真正知識密度的網站」 |
| 3 | **使用者旅程（User Journey）** | 2/5 | 內部連結分布月降 16.3%，延伸閱讀機制弱化。從搜尋到轉換的路徑需要更清晰的 CTA 設計 | 顧問文章《如何知道 AIO 是怎影響搜尋以及因應》：「首屏要有 Answer Card + 目錄 + 關鍵 CTA」 |
| 4 | **技術體質（Technical Health）** | 4/5 | 回應時間改善（508ms），技術基礎面穩健。但 AMP Article 波動大（月降 46%），可能需要重新評估 AMP 策略 | — |
| 5 | **連結生態（Link Ecosystem）** | 2/5 | 外部連結月降 18.2%、內部連結分布月降 16.3%，雙重衰退。連結建設缺乏主動策略 | 顧問文章《從 Search Console 看連結建立的檢驗》：「連結應服務使用者體驗，指引使用者下一步」[18] |
| 6 | **資料敘事（Data Storytelling）** | 3/5 | 有指標監控系統，但異常分析仍依賴人工。營運 KW 下降未自動觸發內容調整流程 | — |
| 7 | **趨勢敏銳度（Trend Sensitivity）** | 2/5 | February Discover Core Update 已完成近兩週但尚未評估影響。AI 可見度下降未及時回應。GSC Branded Queries Filter 推出可作為新的分析工具但尚未採用 | 顧問文章《在後社群時代的導流新通道探索》：「探索是後社群時代最大導流通道，需持續產出新鮮、分眾內容」 |

**人本要素平均分：2.71/5**

---

## 八、SEO 成熟度自評

| 維度 | 當前等級 | 依據 | 下一步 |
|------|---------|------|-------|
| **策略（Strategy）** | L2 發展 | 有 SEO 顧問合作和定期會議，但缺乏數據驅動的自動決策機制。營運 KW 下降仍依賴人工發現 | → L3：建立異常自動警示 + 內容調整 SOP |
| **流程（Process）** | L2 發展 | 有指標監控和週報流程，但快照擷取有盲區（latest=null）、內部連結建設無標準流程 | → L3：快照完整性驗證自動化 + 新文章連結 SOP |
| **關鍵字（Keywords）** | L3 成熟 | 有系統化的關鍵字追蹤（130+ 指標），營運 KW 分群明確。但缺乏意圖分群和競爭分析 | → L4：加入搜尋意圖分類 + 競爭者排名比對 |
| **指標（Metrics）** | L2 發展 | 多維度追蹤已建立，但 AI 可見度監控不夠即時，缺乏預警機制。KW 排名觀察與 KB 建議 [15] 的「爬取指標優先」尚有落差 | → L3：建立預警閾值 + 爬取指標前置 |

---

## 九、會議提問清單

### A 類：確認事實（4 題）

- [ ] [A1] 3/6 快照中 10 項路徑指標 latest=null，是否為 GSC 資料延遲？能否在 GSC 介面直接確認這些路徑的當週數據？（來源：S3 假設 3.5-H1）
- [ ] [A2] 營運 KW「保養」從 7 降到 3，絕對值很低——這是單一文章排名滑落還是整體品類被取代？（來源：S3 假設 3.1-H1）
- [ ] [A3] 外部連結從 ~730K 降到 ~598K（月降 18.2%），是自然衰退還是有特定的高價值外鏈流失？（來源：S3 假設 3.4-H1）
- [ ] [A4] 週平均回應時間從 948ms 改善到 508ms，這是技術優化成果還是流量結構變化造成的統計效果？（來源：S1 正向指標）

### B 類：探索判斷（5 題）

- [ ] [B1] 使用者旅程評分低（2/5）——vocus 目前從搜尋進站到付費訂閱的轉換路徑，哪個環節流失最嚴重？有無改善的優先建議？（來源：S7 使用者旅程，評分 2/5）
- [ ] [B2] 連結生態評分低（2/5）——以 vocus 的平台定位，什麼類型的外部連結策略最有效？UGC 平台能否透過創作者合作建立外鏈？（來源：S7 連結生態，評分 2/5）
- [ ] [B3] 趨勢敏銳度評分低（2/5）——February Discover Core Update 強調「深度、原創、在地」，這對 vocus 中文 UGC 內容是機會還是威脅？（來源：S7 趨勢敏銳度，評分 2/5）
- [ ] [B4] E-E-A-T 權威性僅 2/5——作為 UGC 平台，vocus 在 E-E-A-T 框架下天生劣勢，有什麼結構性的解法？（來源：S6 Authoritativeness，評分 2/5）
- [ ] [B5] AMP Article 數據極度波動（週 +420%、月 -46%），AMP 對 vocus 的實際價值如何？是否應該重新評估 AMP 策略？（來源：S1 月趨勢表）

### C 類：挑戰假設（3 題）

- [ ] [C1] 您在《AI 導流越高搜尋流量越上升》中提出「AI 導流高的網站搜尋流量也在上升」，但 vocus 的 AI 占比月降 16%、GPT 工作階段月降 40%——這是否意味著 vocus 屬於「AI 與搜尋都忽略」的那群？該如何扭轉？（來源：S4，矛盾點：AI 可見度下降 vs 顧問「AI 是照妖鏡」理論）
- [ ] [C2] KB 知識庫記錄顧問曾判斷「CTR 下降是好事」[4]，但如果 AI Overviews 計入 GSC 曝光導致 CTR 被稀釋，這個判斷框架是否需要修正？（來源：S4，矛盾點：傳統 CTR 下降=好事 vs AIO 時代 CTR 稀釋）
- [ ] [C3] 您在《如何知道 AIO 是怎影響搜尋以及因應》中建議「首屏要有 Answer Card + TOC + CTA」，但 vocus 作為 UGC 平台，如何在不干預創作者自由的前提下推動這些結構化要求？（來源：S4，缺口：平台層級 vs 創作者層級的 SEO 控制）

### D 類：業界趨勢（3 題）

- [ ] [D1] February 2026 Discover Core Update 是首次 Discover-only 更新，目前僅影響美國英語用戶但即將擴展——vocus 是否應提前準備中文市場的 Discover 優化策略？（來源：S2 Google 官方更新）
- [ ] [D2] Search Console 剛推出 Branded Queries Filter——這個工具能幫助 vocus 區分品牌 vs 非品牌流量嗎？建議的分析角度是什麼？（來源：S2 SER 報導）
- [ ] [D3] 業界報導指出 73% B2B 網站流量顯著下滑、AI Overviews 造成 15-64% 有機流量降幅——vocus 作為 B2C 內容平台，受影響程度與 B2B 有何不同？（來源：S2 Search Engine Land 報導）

---

## 十、會議後行動核查表

- [ ] 根據顧問回答確認 A1（資料斷層原因），必要時重新擷取快照
- [ ] 根據顧問回答更新 S3 假設——標記「已確認/已排除/待追蹤」
- [ ] 確認 S5 五層審計缺口的優先序（與顧問共識）
- [ ] 記錄會議中的新發現，回寫知識庫（特別是 Discover Update 影響判斷）
- [ ] 評估是否需要啟動 Branded Queries Filter 分析（D2 回答後）
- [ ] 安排下週行動項目：
  - [ ] 快照擷取機制修正（如 A1 確認為資料問題）
  - [ ] 營運 KW 對應文章更新計畫（如 A2 確認為內容問題）
  - [ ] 外鏈流失分析報告（如 A3 確認有特定流失）
  - [ ] AI 可見度改善方案（如 C1 確認為內容品質問題）
- [ ] 將本次會議重點摘要寫入 `research/12-meeting-prep-insights.md`

<!-- citations [{"n":1,"id":"63c7b5042b8a8827","title":"Search Console Coverage 數字異常上升判斷","category":"索引與檢索","date":"2025-08-11","snippet":"有效 Coverage 數字上升由 #! 重複頁面導致","chunk_url":"","source_url":null},{"n":2,"id":"81c32da0e940147b","title":"有效頁面數下降不代表索引惡化","category":"索引與檢索","date":"2026-02-23","snippet":"有效頁面數下降需搭配流量頁面數同步觀察","chunk_url":"","source_url":null},{"n":3,"id":"115ec2e2a314561e","title":"tags 頁攻擊不影響整體 index","category":"索引與檢索","date":"2025-06-23","snippet":"Crawl Budget 消耗需達一定程度才影響正常頁面索引","chunk_url":"","source_url":null},{"n":4,"id":"29f981f09f0cda23","title":"CTR 下降可能是好事","category":"搜尋表現分析","date":"2024-07-22","snippet":"CTR 下降意味曝光成長超過點擊，觸及範圍擴大","chunk_url":"","source_url":null},{"n":5,"id":"7661b36e8d666547","title":"CTR 提高時平均排名下降","category":"搜尋表現分析","date":"2025-04-14","snippet":"CTR 提升代表低排名頁面也開始吸引點擊","chunk_url":"","source_url":null},{"n":6,"id":"58625a6dd40c445d","title":"點擊數與 CTR 平穩屬正常","category":"搜尋表現分析","date":"2025-05-26","snippet":"Google 演算法調整期間 CTR 平穩暫不需緊急干預","chunk_url":"","source_url":null},{"n":7,"id":"23eff8f0210ef59e","title":"作者頁面 E-E-A-T 結構化資料","category":"技術SEO","date":"2024-01-24","snippet":"Profile Page 結構化資料強化 E-E-A-T 信號","chunk_url":"","source_url":null},{"n":8,"id":"99a77bf6f9e89d94","title":"Discover 流量回落專業度不足","category":"Discover與AMP","date":"2024-01-17","snippet":"Google E-E-A-T 框架評估不佳時 Discover 分發下降","chunk_url":"","source_url":null},{"n":9,"id":"6bc8d7fd5cb79523","title":"E-A-T 2020 年實作要求","category":"內容策略","date":"","snippet":"圍繞 E-A-T 原則建立更精確的實作項目","chunk_url":"","source_url":null},{"n":10,"id":"8528645fe35f1fd3","title":"發現方式降指 Discover 流量下滑","category":"Discover與AMP","date":"2024-10-28","snippet":"Discover 流量受演算法評分影響","chunk_url":"","source_url":null},{"n":11,"id":"c0d98f761d07611d","title":"如何點燃 Discover 文章","category":"Discover與AMP","date":"2023-10-18","snippet":"透過外部流量信號助燃提升 Discover 分發","chunk_url":"","source_url":null},{"n":12,"id":"6f27566ce677e69b","title":"Discover 與 Google News 關聯","category":"Discover與AMP","date":"2023-09-06","snippet":"Google News 訂閱可帶動 Discover 流量","chunk_url":"","source_url":null},{"n":13,"id":"596fcacd8ad050f3","title":"AI 搜尋對 YoY 流量影響","category":"演算法與趨勢","date":"2026-01-26","snippet":"AI 搜尋直接回答問題減少點擊進入內容網站","chunk_url":"","source_url":null},{"n":14,"id":"f5066fc30f82717a","title":"AI 導流高不代表被搶流量","category":"演算法與趨勢","date":"2025-12-10","snippet":"AI 導流高的網站搜尋流量同時在上升","chunk_url":"","source_url":null},{"n":15,"id":"cebcea9f136a3cd4","title":"關鍵字排名不適合當核心 KPI","category":"搜尋表現分析","date":"2021-09-01","snippet":"應以搜尋引擎爬取數字為先驗指標","chunk_url":"","source_url":null},{"n":16,"id":"988e72a7b5e02da9","title":"Google 爬取 JS 頁面效率","category":"索引與檢索","date":"2023-09-20","snippet":"JS 爬蟲效率低於 HTML 爬蟲","chunk_url":"","source_url":null},{"n":17,"id":"98b9d6331381796c","title":"JS 渲染 SEO 挑戰","category":"技術SEO","date":"","snippet":"CSR 對 Core Web Vitals 是挑戰","chunk_url":"","source_url":null},{"n":18,"id":"2b3452a516dcf225","title":"連結的真正目的是引導使用者","category":"連結策略","date":"","snippet":"連結應服務使用者體驗，指引下一步","chunk_url":"","source_url":null},{"n":19,"id":"be4efa2d957eeaa6","title":"文章目錄對 SEO 和閱讀體驗幫助","category":"內容策略","date":"","snippet":"清晰章節目錄有助 SEO 排名和閱讀體驗","chunk_url":"","source_url":null}] -->
<!-- meeting_prep_meta {"date":"20260306","scores":{"eeat":{"experience":3,"expertise":3,"authoritativeness":2,"trustworthiness":3},"maturity":{"strategy":"L2","process":"L2","keywords":"L3","metrics":"L2"}},"alert_down_count":24,"question_count":15,"generation_mode":"claude-code"} -->
