# 顧問會議準備深度研究報告 — 2026-02-20

> 資料來源：`output/report_20260220.md`（週報萃取模式）
> 生成時間：2026-03-12
> 模式：claude-code

---

## 〇、執行摘要

1. **新聞/時事曝光渠道斷線**：AMP Article、News(new)、Google News 同步明顯下滑，非單純排名波動，而是「時事曝光管道」系統性衰退，需優先排查 AMP 追蹤碼與版本一致性。
2. **Discover 週期性波動**：週降幅明顯但月趨勢相對穩定，更像推薦量週期而非全站 SEO 失效，需拆解是單篇退潮還是整體推薦減少。
3. **檢索未索引持續堆高**：Google 有抓取但不索引的 URL 顯著增加，長期將稀釋 crawl budget、壓縮可競爭頁面數量。
4. **桌機 CWV 差的頁面上升**：CLS 問題在 post/沙龍/首頁模板蔓延，即使曝光回復也會因體驗問題壓低 CTR 與互動。
5. **February 2026 Discover Core Update 進行中**（2/5 起）：首次 Discover-only 更新，強調深度、原創、在地內容，可能影響 vocus 探索流量中期趨勢。

---

## 一、本週異常地圖

### 渠道型異常（時事曝光鏈斷裂）

| 指標 | 趨勢 | 嚴重度 | 說明 |
|------|------|--------|------|
| AMP Article | 週顯著下滑 | 🔴 高 | 與焦點頭條連動，時事供給不足或 AMP 驗證問題 |
| News(new) | 週顯著下滑 | 🔴 高 | 與 AMP Article 同步走弱 |
| Google News | 週下滑 | 🔴 高 | 入口渠道斷線，非內容自然衰退 |
| Discover | 週下滑、月持平 | 🟡 中 | 推薦量週期波動，待拆解 |

### 技術型異常

| 指標 | 趨勢 | 嚴重度 | 說明 |
|------|------|--------|------|
| 檢索未索引 | 顯著攀升 | 🔴 高 | 被看見但未轉成可排名資產 |
| 桌機 CWV（差） | 緩慢上升 | 🟡 中 | CLS 問題擴散中 |

---

## 二、業界最新動態

### Google 官方更新

| 日期 | 事件 | 狀態 | 與本週異常的關聯性 |
|------|------|------|-------------------|
| 2026-02-05 起 | **February 2026 Discover Core Update** | 進行中 | **高度相關**：首次 Discover-only 核心更新，強調深度、原創、在地內容。可能直接影響 Discover 推薦量與流量分配 |
| 2026-02-25 | Serving 服務故障 | 已修復 | 可能造成當週 GSC 數據短暫異常 |

### 業界報導

| 來源 | 標題 | 摘要 | 與本站異常的可能關聯 |
|------|------|------|---------------------|
| Search Engine Land | [Google February 2026 Discover core update](https://searchengineland.com/google-releases-discover-core-update-february-2026-468308) | 首次公告的 Discover-only 更新，偏好在地、原創、深度內容 | Discover 週下滑的潛在原因 |
| Search Engine Land | [How to increase Google Discover traffic with technical fixes](https://searchengineland.com/google-discover-technical-fixes-470448) | 技術修復可提升 Discover 流量 | Discover 改善的參考 |
| Google Developers | [Debug Google Search Traffic Drops](https://developers.google.com/search/docs/monitor-debug/debugging-search-traffic-drops) | 官方流量下降除錯指南 | 排查 AMP/News 下滑的參考流程 |
| Search Engine Land | [Fix Crawled – Currently not indexed](https://searchengineland.com/fix-crawled-currently-not-indexed-error-google-search-console-445344) | 89% GSC profiles 有此問題，品質是主因 | 檢索未索引攀升的參考 |

### Search Engine Roundtable 近期重點

| 日期 | 標題 | 摘要 |
|------|------|------|
| 2026-03-12 | Google Tests Instagram Knowledge Panel Design | 新知識面板設計實驗 |
| 2026-03-12 | Google Tests Ask About Feature in AI Mode Citation Overlays | AI Mode 引用區新增「Ask about」功能 |
| 2026-03-11 | Branded Queries Filter Rolling Out in Search Console | 品牌查詢篩選器正式推出 |
| 2026-03-11 | Google Launches Merchant Center For Agencies | 新代理商 Merchant Center |

---

## 三、深度根因假設

### 3.1 AMP Article + News + Google News 同步下滑

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1 | **AMP 追蹤碼/版本不一致**：AMP 頁面的 GA 追蹤碼或轉換事件不完整，實際流量存在但未被記錄 [1] | L1 Technical | 可驗證——檢查 AMP 頁面 GA tag |
| H2 | **時事內容供給不足**：近期缺少可被推薦至 Top Stories 的時事題材，導致 AMP 曝光自然萎縮 [2] | L3 Content Quality | 可驗證——對比近期發文與時事熱度 |
| H3 | **Discover Core Update 影響**：Feb 2026 更新偏好「深度原創」，可能降低聚合型時事內容的推薦權重 | L3 Content Quality | 需觀察——更新仍在進行中 |

### 3.2 Discover 週下滑但月持平

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1 | **單篇爆量文退潮**：少數高推薦文章退熱，導致週跌幅集中但月趨勢穩定 [3] | — | 可驗證——拉出 Discover 前 N 名文章比對 |
| H2 | **推薦演算法週期波動**：Discover 推薦量本身有自然週期，非結構性下滑 | — | 需觀察——下週是否回升 |
| H3 | **Discover Core Update 調整推薦權重**：更新期間推薦分配暫時異常 | L3 Content Quality | 需觀察——更新完成後評估 |

### 3.3 檢索未索引顯著攀升

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1 | **低價值/重複 URL 增生**：tag、搜尋結果頁、參數頁被大量爬取但不值得索引 [4] | L2 Content Architecture | 可驗證——GSC 檢索涵蓋報表分析 |
| H2 | **AMP 雙版本一致性問題**：AMP 與 canonical 頁面內容/結構化資料不一致，Google 選擇不索引某版本 | L1 Technical | 可驗證——抽查 AMP vs canonical 內容 |
| H3 | **內部連結不足導致品質信號弱**：新增頁面缺少足夠的內部連結，Google 判定不值得索引 [5] | L2 Content Architecture | 可驗證——檢查近期新文章的內部連結數 |

### 3.4 桌機 CWV 差上升

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1 | **CLS 模板層級問題**：post/沙龍/首頁模板中圖片/廣告/嵌入元件未預留尺寸 [6][7] | L1 Technical | 可驗證——PSI/Lighthouse 掃描 |
| H2 | **版位調整或改版殘留**：近期版面調整導致更多 URL 被歸類為「差」 | L1 Technical | 可驗證——比對改版時間與 CWV 變化 |
| H3 | **字型載入閃爍（FOUT）**：桌機特定斷點出現版面位移 [6] | L1 Technical | 可驗證——Chrome DevTools 檢查 |

---

## 四、顧問視角交叉比對

| 主題 | KB 知識庫觀點 | 顧問文章觀點 | 指標數據 | 業界動態 | 判斷 |
|------|-------------|-------------|---------|---------|------|
| **AMP 與時事流量** | AMP Article 反映時事趨勢 [2]；Google News App 導 AMP，追蹤碼需完整 [1] | 顧問文章《AMP 過期了嗎》指出 AMP 是提升行動體驗的方法論，CWV 良好比例高的多是已導入 AMP 的網站 | AMP/News/Google News 三者同步下滑 | AMP 不再是 Top Stories 必要條件（2021 起），但仍影響體驗分數 | **一致**：KB 與顧問都認為 AMP 問題會連帶影響時事曝光，但需區分「AMP 追蹤斷線」vs「時事供給不足」 |
| **Discover 流量** | Discover 高度受即時熱度影響 [3]；Google News 訂閱可帶動 Discover [8] | 顧問強調 Discover 需持續產出新鮮、視覺化、分眾內容 | 週下滑但月持平 | Feb 2026 Discover Core Update 進行中，偏好深度原創在地內容 | **缺口**：Discover Update 進行中但尚未評估對 vocus 的影響，且缺少 vocus Discover 專屬數據 |
| **檢索未索引** | 頁面連結結構與內容豐富性是索引關鍵 [5]；檢索數據有 3 個月移動區間延遲 [9] | 顧問文章強調連結應服務使用者體驗 [10] | 檢索未索引顯著攀升 | 89% GSC profiles 有此問題，品質是主因 | **缺口**：攀升趨勢明確但缺乏具體 URL 分群分析——是 tag/參數頁還是正式內容頁被拒索引？ |
| **桌機體驗** | CLS 常見於 post/沙龍/首頁模板 [6][7]；修復 CLS 後流量大幅增長 [11] | 顧問文章指出 CWV 良好比例是核心指標，60% 及格、90%+ 優秀 | 桌機差的頁面上升 | Google 持續強化 Page Experience 信號 | **一致**：KB 已定位問題模板，顧問也確認 CWV 重要性。行動項目清楚——鎖定 CLS 元素修正 |
| **內容新鮮度** | Discover 偏好新鮮、深度內容 [3]；時事文章不夠是核心問題 [2] | 顧問強調「時事推動」是 AMP/Top Stories 的關鍵推力 | AMP/Discover 同步下滑 | Discover Update 偏好「深度、原創、即時」 | **一致**：所有來源都指向內容新鮮度不足是根因之一 |

---

## 五、五層審計缺口清單

| 層 | 現況 | 缺口 | 建議 | 優先序 |
|----|------|------|------|-------|
| L1 Technical Foundation | 桌機 CWV 差上升；AMP 追蹤碼完整性未確認 | **AMP 追蹤碼與版本一致性**：AMP 頁面的 GA 事件可能不完整，造成流量低估 [1] | 1. 建立 AMP vs canonical 分流監控 2. 稽核 AMP GA tag 完整性 | 高 |
| L2 Content Architecture | 檢索未索引顯著攀升 | **低價值 URL 與內部連結不足**：tag/參數頁被爬取但不索引，新內容缺乏足夠內部連結 [5] | 1. 盤點未索引 URL 分群 2. 建立新文章發布時的內部連結 SOP | 高 |
| L3 Content Quality | 時事文章供給不足，AMP 曝光下滑 | **時事題材覆蓋不足**：缺少可被 Top Stories 收錄的時事內容 [2] | 1. 建立時事選題節奏 2. 盤點可更新再推的舊文章 | 高 |
| L4 Off-Page & Authority | 無明顯異常 | **缺乏 Discover 推薦機制的主動策略** | 1. 透過外部流量信號助燃 Discover 推薦 [12] 2. Google News 訂閱策略 [8] | 中 |
| L5 User Experience | 桌機 CLS 擴散中 | **CLS 模板問題持續蔓延** [6][7] | 1. 鎖定 post/沙龍/首頁模板修正 CLS 2. PSI/Lighthouse 驗證 | 中 |

---

## 六、E-E-A-T 現況評估

| 維度 | 分數 | 依據 |
|------|------|------|
| **Experience（經驗）** | 3/5 | vocus 平台有大量創作者第一手經驗分享，但缺乏統一的作者署名規範。Profile Page 結構化資料可強化此信號 [13]，但尚未系統性實施。 |
| **Expertise（專業性）** | 3/5 | 部分專業領域有深度內容，但 UGC 品質參差。Discover 回落原因之一是「Google 認定專業度不足」[14]，時事文章供給不足也削弱即時專業形象。 |
| **Authoritativeness（權威性）** | 3/5 | 本期數據未顯示外部連結異常。但 AMP/News 下滑意味著在時事渠道的權威曝光減少，長期可能影響 Google 對平台的新聞權威性評估。 |
| **Trustworthiness（可信度）** | 3/5 | 平台有基本內容管理機制。桌機 CWV 變差可能間接影響可信度感知——使用者看到版面跳動的頁面會降低信任感。 |

**E-E-A-T 平均分：3.00/5**

---

## 七、人本七要素分析

| # | 要素 | 分數 | 觀察 | 顧問文章引用 |
|---|------|------|------|-------------|
| 1 | **網站人格（Brand Persona）** | 3/5 | vocus 定位為「創作者經濟平台」，在搜尋生態中有明確角色，但與競爭者的區隔度需透過時事/深度內容強化 | — |
| 2 | **內容靈魂（Content Soul）** | 3/5 | UGC 模式下有獨特觀點，但時事內容供給不足導致「渠道斷線」，缺乏平台層級的內容品質信號 | — |
| 3 | **使用者旅程（User Journey）** | 2/5 | AMP 追蹤碼不完整可能導致使用者旅程追蹤斷裂 [1]；桌機 CLS 問題影響落地體驗 | 顧問文章指出連結應服務使用者體驗 [10] |
| 4 | **技術體質（Technical Health）** | 2/5 | 桌機 CWV 差上升、AMP 版本一致性未確認、檢索未索引攀升——三個技術面問題同時存在 | 顧問文章《AMP 過期了嗎》：良好 CWV 比例是核心指標 |
| 5 | **連結生態（Link Ecosystem）** | 3/5 | 本期無明顯外部連結異常，但新內容的內部連結建設可能不足，間接導致檢索未索引攀升 [5] | 顧問文章《從 Search Console 看連結建立的檢驗》：連結應指引使用者下一步 [10] |
| 6 | **資料敘事（Data Storytelling）** | 3/5 | 有指標監控系統產出週報，但 AMP 分流監控缺失，無法區分「真的沒曝光」vs「追蹤斷線」 | — |
| 7 | **趨勢敏銳度（Trend Sensitivity）** | 2/5 | Feb 2026 Discover Core Update 已啟動但尚未評估影響，時事文章供給不足反映對趨勢的反應速度待提升 | — |

**人本要素平均分：2.57/5**

---

## 八、SEO 成熟度自評

| 維度 | 當前等級 | 依據 | 下一步 |
|------|---------|------|-------|
| **策略（Strategy）** | L2 發展 | 有 SEO 顧問合作和定期會議，但 AMP 分流監控缺失，時事選題缺乏系統性規劃 | → L3：建立時事選題日曆 + AMP 分流儀表板 |
| **流程（Process）** | L2 發展 | 有指標監控和週報，但 AMP 追蹤碼稽核無 SOP、新文章發布無內部連結標準流程 | → L3：AMP 稽核 SOP + 新文章連結 SOP |
| **關鍵字（Keywords）** | L2 發展 | 有基本關鍵字追蹤，但未與時事趨勢連動，缺少 Discover 專屬的題材分析 | → L3：時事 KW 追蹤 + Discover 題材分析 |
| **指標（Metrics）** | L2 發展 | 週報涵蓋多維度指標，但 AMP vs canonical 分流缺失，桌機 CWV 無即時告警 | → L3：分流監控 + CWV 閾值告警 |

---

## 九、會議提問清單

### A 類：確認事實（4 題）

- [ ] [A1] AMP Article 下滑是「真的沒曝光」還是「AMP 頁面 GA 追蹤碼/轉換事件不完整，流量在但沒記到」？目前 AMP vs canonical 是否有分開監控？（來源：S3 假設 3.1-H1）
- [ ] [A2] 檢索未索引攀升的 URL 主要是哪些類型？tag 頁、參數頁、還是正式內容頁？是否與 AMP 雙版本一致性有關？（來源：S3 假設 3.3-H1, H2）
- [ ] [A3] 桌機 CWV 差上升的範圍——是所有模板還是集中在 post/沙龍/首頁？上次修復 CLS 是何時？（來源：S3 假設 3.4-H1）
- [ ] [A4] 本週 Discover 下滑是集中在少數文章退潮，還是整體推薦量減少？（來源：S3 假設 3.2-H1）

### B 類：探索判斷（5 題）

- [ ] [B1] 使用者旅程評分低（2/5）——AMP 追蹤碼修復的優先順序如何？修復後如何驗證轉換歸因完整性？（來源：S7 使用者旅程，評分 2/5）
- [ ] [B2] 技術體質評分低（2/5）——桌機 CWV 差、AMP 不一致、檢索未索引三個技術問題的修復順序建議？（來源：S7 技術體質，評分 2/5）
- [ ] [B3] 趨勢敏銳度評分低（2/5）——February Discover Core Update 已啟動，vocus 中文 UGC 是否屬於「在地原創」而有機會受益？（來源：S7 趨勢敏銳度，評分 2/5）
- [ ] [B4] 以 vocus 的平台定位，什麼類型的時事選題策略最能有效提升 Top Stories 命中率？（來源：S5 L3 缺口）
- [ ] [B5] 檢索未索引如果主要是 tag/參數頁，是否建議直接 noindex 處理？還是有更好的做法？（來源：S4，缺口：URL 分群分析不足）

### C 類：挑戰假設（2 題）

- [ ] [C1] 週報判斷 Discover 下滑「更像推薦量週期而非全站 SEO 失效」，但如果 Discover Core Update 正在改變推薦權重，這個「週期性」判斷是否過於樂觀？（來源：S4，缺口：Discover Update 影響未評估）
- [ ] [C2] 顧問文章《AMP 過期了嗎》認為 AMP 仍有價值（CWV 良好比例高），但 Google 已不要求 Top Stories 用 AMP——vocus 是否應重新評估 AMP 策略的 ROI？（來源：S4，矛盾點：AMP 價值 vs AMP 非必要）

### D 類：業界趨勢（3 題）

- [ ] [D1] February 2026 Discover Core Update 是首次 Discover-only 更新，強調「在地、原創、深度」——這對 vocus 中文 UGC 平台是機會還是威脅？（來源：S2 Google 官方更新）
- [ ] [D2] Google AI Mode 正在測試引用區「Ask about」功能——這對 vocus 內容被 AI 引用的可見度有什麼影響？（來源：S2 SER 報導）
- [ ] [D3] Search Console 推出 Branded Queries Filter——建議如何用這個新工具來分析 vocus 的品牌 vs 非品牌流量結構？（來源：S2 SER 報導）

---

## 十、會議後行動核查表

- [ ] 根據顧問回答確認 A1（AMP 追蹤碼狀態），必要時啟動 AMP 稽核
- [ ] 根據顧問回答確認 A2（未索引 URL 分群），決定 noindex 或內部連結策略
- [ ] 根據顧問回答更新 S3 假設——標記「已確認/已排除/待追蹤」
- [ ] 確認 S5 五層審計缺口的優先序（與顧問共識）
- [ ] 記錄 Discover Core Update 的顧問判斷，回寫知識庫
- [ ] 安排下週行動項目：
  - [ ] AMP vs canonical 分流監控建立（如 A1 確認為追蹤問題）
  - [ ] 時事選題日曆建立（如 B4 獲得具體建議）
  - [ ] 桌機 CLS 修復排程（如 A3 確認模板範圍）
  - [ ] 檢索未索引 URL 分群處理方案（如 A2 確認類型）
- [ ] 將本次會議重點摘要寫入 `research/12-meeting-prep-insights.md`

<!-- citations [{"n":1,"id":"efc9c4ce4951ea7d","title":"Google News APP 與 Pixel 導頁差異","category":"Discover與AMP","date":"2023-06-14","snippet":"Google News APP 會導 AMP，Pixel 原生 News 導一般頁面","chunk_url":"","source_url":null},{"n":2,"id":"664536e8a7b205b3","title":"AMP Article 點擊數創新高的解讀","category":"Discover與AMP","date":"2025-11-24","snippet":"AMP Article 反映時事趨勢，焦點頭條曝光依賴時事熱度","chunk_url":"","source_url":null},{"n":3,"id":"60f00b85f7789c3b","title":"Discover 探索流量大幅下滑診斷","category":"Discover與AMP","date":"2023-09-20","snippet":"Discover 對內容品質與新鮮度高度敏感，Core Update 是常見原因","chunk_url":"","source_url":null},{"n":4,"id":"b82545d945ee0f56","title":"檢索未索引指標下跌根因","category":"索引與檢索","date":"2023-09-20","snippet":"Google 爬取但不索引，需從連結結構與內容豐富性著手","chunk_url":"","source_url":null},{"n":5,"id":"d8748a7372deac4c","title":"連結在 SEO 排名中的角色","category":"連結策略","date":"","snippet":"內部連結與外部連結是排名檢查項目","chunk_url":"","source_url":null},{"n":6,"id":"98068609c4bfaef8","title":"桌機版 CWV Warning 上升原因","category":"技術SEO","date":"2023-11-01","snippet":"CLS 由圖片、廣告、字型載入造成版面位移","chunk_url":"","source_url":null},{"n":7,"id":"65240f556077b23f","title":"CLS 問題定位與優先處理","category":"技術SEO","date":"2024-01-31","snippet":"沙龍 post 頁面與首頁有 CLS 問題","chunk_url":"","source_url":null},{"n":8,"id":"6f27566ce677e69b","title":"Discover 與 Google News 關聯","category":"Discover與AMP","date":"2023-09-06","snippet":"Google News 訂閱可帶動 Discover 流量","chunk_url":"","source_url":null},{"n":9,"id":"27a33d12383cbaea","title":"GSC 檢索數據反映延遲","category":"索引與檢索","date":"2024-01-24","snippet":"GSC 檢索指標有約三個月移動區間","chunk_url":"","source_url":null},{"n":10,"id":"2b3452a516dcf225","title":"連結的真正目的是引導使用者","category":"連結策略","date":"","snippet":"連結應服務使用者體驗，指引下一步","chunk_url":"","source_url":null},{"n":11,"id":"bc9a270cabda418c","title":"修復 CLS 後流量大幅增長","category":"技術SEO","date":"2025-10-13","snippet":"CLS 修復對搜尋流量有直接正向影響","chunk_url":"","source_url":null},{"n":12,"id":"c0d98f761d07611d","title":"如何點燃 Discover 文章","category":"Discover與AMP","date":"2023-10-18","snippet":"透過外部流量信號助燃提升 Discover 分發","chunk_url":"","source_url":null},{"n":13,"id":"23eff8f0210ef59e","title":"作者頁面 E-E-A-T 結構化資料","category":"技術SEO","date":"2024-01-24","snippet":"Profile Page 結構化資料強化 E-E-A-T 信號","chunk_url":"","source_url":null},{"n":14,"id":"99a77bf6f9e89d94","title":"Discover 流量回落專業度不足","category":"Discover與AMP","date":"2024-01-17","snippet":"Google E-E-A-T 框架評估不佳時 Discover 分發下降","chunk_url":"","source_url":null}] -->
<!-- meeting_prep_meta {"date":"20260220","scores":{"eeat":{"experience":3,"expertise":3,"authoritativeness":3,"trustworthiness":3},"maturity":{"strategy":"L2","process":"L2","keywords":"L2","metrics":"L2"}},"alert_down_count":6,"question_count":14,"generation_mode":"claude-code"} -->
