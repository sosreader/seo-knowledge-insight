# 顧問會議準備深度研究報告 — 2026-02-20

> 資料來源：`output/report_20260220.md`（週報萃取模式）
> 生成時間：2026-03-14
> 模式：claude-code

---

## 〇、執行摘要

1. **新聞/時事曝光渠道斷線**：AMP Article、News(new)、Google News 同步明顯下滑，非單純排名波動，而是「時事曝光管道」系統性衰退，需優先排查 AMP 追蹤碼與版本一致性。
2. **Discover 週期性波動**：週降幅明顯但月趨勢相對穩定，更像推薦量週期而非全站 SEO 失效，需拆解是單篇退潮還是整體推薦減少。
3. **檢索未索引持續堆高**：Google 有抓取但不索引的 URL 顯著增加，長期將稀釋 crawl budget、壓縮可競爭頁面數量 [4][5]。
4. **桌機 CWV 差的頁面上升**：CLS 問題在 post/沙龍/首頁模板蔓延，即使曝光回復也會因體驗問題壓低 CTR 與互動。
5. **February 2026 Discover Core Update 進行中**（2/5 起）：首次 Discover-only 更新，強調深度、原創、在地內容，可能影響 vocus 探索流量中期趨勢。

---

## 一、本週異常地圖

### 渠道型異常（時事曝光鏈斷裂）

| 指標 | 趨勢 | 嚴重度 | 說明 |
|------|------|--------|------|
| AMP Article | 週顯著下滑 | 高 | 與焦點頭條連動，時事供給不足或 AMP 驗證問題 [2] |
| News(new) | 週顯著下滑 | 高 | 與 AMP Article 同步走弱 |
| Google News | 週下滑 | 高 | 入口渠道斷線，非內容自然衰退 |
| Discover | 週下滑、月持平 | 中 | 推薦量週期波動，待拆解 [8][11] |

### 技術型異常

| 指標 | 趨勢 | 嚴重度 | 說明 |
|------|------|--------|------|
| 檢索未索引 | 顯著攀升 | 高 | 被看見但未轉成可排名資產 [4] |
| 桌機 CWV（差） | 緩慢上升 | 中 | CLS 問題擴散中 |

---

## 二、業界最新動態

### Google 官方更新

| 日期 | 事件 | 狀態 | 與本週異常的關聯性 |
|------|------|------|-------------------|
| 2026-02-05 起 | **February 2026 Discover Core Update** | 進行中 | **高度相關**：首次 Discover-only 核心更新，強調深度、原創、在地內容。可能直接影響 Discover 推薦量與流量分配 [8][10][11] |
| 2026-02-25 | Serving 服務故障 | 已修復 | 可能造成當週 GSC 數據短暫異常 |

### 業界報導

| 來源 | 標題 | 摘要 | 與本站異常的可能關聯 |
|------|------|------|---------------------|
| Search Engine Land | Google February 2026 Discover core update | 首次公告的 Discover-only 更新，偏好在地、原創、深度內容 | Discover 週下滑的潛在原因 |
| Search Engine Land | Fix Crawled – Currently not indexed | 89% GSC profiles 有此問題，品質是主因 | 檢索未索引攀升的參考 |
| SearchEngineLand | AI search referral traffic trends 2026 | ChatGPT referral 量持續下滑，AI 搜尋 YOY 影響趨勢 [7] | AI 流量評估背景 |
| Google E-E-A-T guidance | Author authority & profile markup | Google 強調 E-E-A-T 作者結構化資料 [6] | Authoritativeness 評分偏低的外部驗證 |

### Search Engine Roundtable 近期重點

| 日期 | 標題 | 摘要 |
|------|------|------|
| 2026-02-20 | Google Discover Core Update ongoing | Discover 更新持續，強調在地化、深度原創 [10][11] |
| 2026-02-18 | AI Mode referral decline continues | ChatGPT 導流繼續下滑，Gemini 逐步填補空白 [7] |
| 2026-02-15 | E-E-A-T author signals | 作者頁面結構化資料影響 Discover 分發 [6] |

---

## 三、深度根因假設

### 3.1 AMP Article + News + Google News 同步下滑

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1 | **AMP 追蹤碼/版本不一致**：AMP 頁面的 GA 追蹤碼或轉換事件不完整，實際流量存在但未被記錄 | L1 Technical | 可驗證——檢查 AMP 頁面 GA tag |
| H2 | **時事內容供給不足**：近期缺少可被推薦至 Top Stories 的時事題材，導致 AMP 曝光自然萎縮 | L3 Content Quality | 可驗證——對比近期發文與時事熱度 |
| H3 | **AMP CSS !important 違規**：CSS 驗證問題導致 AMP 頁面被拒絕索引 [2] | L1 Technical | 可驗證——AMP 驗證工具掃描 |
| H4 | **Discover Core Update 影響**：Feb 2026 更新偏好「深度原創」，可能降低聚合型時事內容的推薦權重 | L3 Content Quality | 需觀察——更新仍在進行中 |

### 3.2 Discover 週下滑但月持平

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1 | **單篇爆量文退潮**：少數高推薦文章退熱，導致週跌幅集中但月趨勢穩定 [11] | — | 可驗證——拉出 Discover 前 N 名文章比對 |
| H2 | **Discover CTR 低於門檻**：CTR 低於 5% 停止推播，導致推薦量週期性下降 [8] | — | 可驗證——GSC Discover 報表 CTR 確認 |
| H3 | **Discover Core Update 調整推薦權重**：更新期間推薦分配暫時異常 [10] | L3 Content Quality | 需觀察——更新完成後評估 |

### 3.3 檢索未索引顯著攀升

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1 | **低價值/重複 URL 增生**：tag、搜尋結果頁、參數頁被大量爬取但不值得索引 [4] | L2 Content Architecture | 可驗證——GSC 檢索涵蓋報表分析 |
| H2 | **內部連結不足導致品質信號弱**：新增頁面缺少足夠的內部連結，孤島頁面無法獲得足夠 PageRank [5] | L2 Content Architecture | 可驗證——檢查近期新文章的內部連結數 |
| H3 | **AMP 雙版本一致性問題**：AMP 與 canonical 頁面內容/結構化資料不一致 [2] | L1 Technical | 可驗證——抽查 AMP vs canonical 內容 |

### 3.4 桌機 CWV 差上升

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1 | **CLS 模板層級問題**：post/沙龍/首頁模板中圖片/廣告/嵌入元件未預留尺寸 | L1 Technical | 可驗證——PSI/Lighthouse 掃描 |
| H2 | **版位調整或改版殘留**：近期版面調整導致更多 URL 被歸類為「差」 | L1 Technical | 可驗證——比對改版時間與 CWV 變化 |
| H3 | **字型載入閃爍（FOUT）**：桌機特定斷點出現版面位移 | L1 Technical | 可驗證——Chrome DevTools 檢查 |

---

## 四、顧問視角交叉比對

| 主題 | KB 知識庫觀點 | 顧問文章觀點 | 指標數據 | 業界動態 | 判斷 |
|------|-------------|-------------|---------|---------|------|
| **AMP 與時事流量** | AMP Article 反映時事趨勢；AMP CSS !important 違規影響索引 [2]；SC 反向連結可見度需搭配 Ahrefs [3] | 顧問文章指出 AMP 仍有速度優勢，CWV 良好比例高的多是已導入 AMP 的網站 | AMP/News/Google News 三者同步下滑 | AMP 不再是 Top Stories 必要條件（2021 起），但仍影響體驗分數 | **一致**：KB 與顧問都認為 AMP 問題會連帶影響時事曝光，但需區分「AMP 追蹤斷線」vs「時事供給不足」 |
| **Discover 流量** | CTR < 5% 停止推播 [8]；社群助燃可死灰復燃 [11]；Discover 專業度不足導致流量低迷 [10] | 顧問強調 Discover 需持續產出新鮮、視覺化、分眾內容 | 週下滑但月持平 | Feb 2026 Discover Core Update 進行中，偏好深度原創在地內容 | **缺口**：Discover Update 進行中但尚未評估對 vocus 的影響，且缺少 vocus Discover 專屬數據 |
| **檢索未索引** | 根因在內部連結不足和孤島頁面 [4][5] | 顧問文章強調連結應服務使用者體驗 | 檢索未索引顯著攀升 | 89% GSC profiles 有此問題，品質是主因 | **缺口**：攀升趨勢明確但缺乏具體 URL 分群分析——是 tag/參數頁還是正式內容頁被拒索引？ |
| **AI 流量趨勢** | AI 導流越高搜尋流量越上升 [1]；AI 搜尋 YOY 影響 [7] | 顧問認為 AI 導流高=網站健康，非競爭關係 | 本週 AI 來源未大幅異常 | ChatGPT referral 全球下滑，AI 搜尋景況持續演變 [7] | **需監控**：Feb 2026 AI 導流趨勢與 Discover 更新交叉影響尚未明朗 |
| **E-E-A-T 作者信號** | 作者頁面 Profile Page 結構化資料強化 E-E-A-T [6] | 顧問重視內容創作者的第一手經驗與作者辨識度 | 外部連結無重大異常但 Authoritativeness 弱 | Google 持續強調 E-E-A-T，Discover 分發與作者信號高度相關 | **一致**：KB 和顧問都指向作者結構化資料是改善 Authoritativeness 的關鍵動作 |

---

## 五、五層審計缺口清單

| 層 | 現況 | 缺口 | 建議 | 優先序 |
|----|------|------|------|-------|
| L1 Technical Foundation | 桌機 CWV 差上升；AMP 追蹤碼完整性未確認 | **AMP 追蹤碼與版本一致性**：AMP 頁面的 GA 事件可能不完整，造成流量低估；AMP CSS !important 可能觸發驗證錯誤 [2] | 1. 建立 AMP vs canonical 分流監控 2. 稽核 AMP GA tag 完整性 3. 掃描 AMP CSS 違規 | 高 |
| L2 Content Architecture | 檢索未索引顯著攀升 | **低價值 URL 與孤島頁面**：tag/參數頁被爬取但不索引；新內容內部連結不足 [4][5] | 1. 盤點未索引 URL 分群 2. 建立新文章發布時的內部連結 SOP | 高 |
| L3 Content Quality | 時事文章供給不足，AMP 曝光下滑 | **時事題材覆蓋不足**：缺少可被 Top Stories 收錄的時事內容 | 1. 建立時事選題節奏 2. 盤點可更新再推的舊文章 | 高 |
| L4 Off-Page & Authority | 外部連結無重大異常，但作者頁面缺乏結構化資料 | **作者 E-E-A-T 信號缺失**：缺少 Profile Page schema，Google 難以辨識作者的專業背景 [6]；SC 反向連結可見度僅 ~80% [3] | 1. 為主要作者頁面實作 Profile Page 結構化資料 2. 用 Ahrefs 補充反向連結監控 | 中 |
| L5 User Experience | 桌機 CLS 擴散中 | **CLS 模板問題持續蔓延**：Discover CTR 若低於門檻 5% 將停止推播 [8] | 1. 鎖定 post/沙龍/首頁模板修正 CLS 2. PSI/Lighthouse 驗證 | 中 |

---

## 六、E-E-A-T 現況評估

| 維度 | 分數 | 依據 |
|------|------|------|
| **Experience（經驗）** | 3/5 | vocus 平台有大量創作者第一手經驗分享，但缺乏統一的作者署名規範。Profile Page 結構化資料可強化此信號 [6]，但尚未系統性實施。 |
| **Expertise（專業性）** | 3/5 | 部分專業領域有深度內容，但 UGC 品質參差。Discover 回落原因之一是「Google 認定專業度不足」[10]，時事文章供給不足也削弱即時專業形象。 |
| **Authoritativeness（權威性）** | 2/5 | SC 反向連結可見度僅 ~80%，且缺乏主動的外部連結建設記錄 [3]。AMP/News 下滑意味著在時事渠道的權威曝光減少，長期將影響 Google 對平台的新聞權威性評估。作者頁面缺少 Profile Page schema 也使外部認可度難以被 Google 機器讀取。 |
| **Trustworthiness（可信度）** | 3/5 | 平台有基本內容管理機制。桌機 CWV 變差可能間接影響可信度感知——使用者看到版面跳動的頁面會降低信任感。AI 導流趨勢 [1] 顯示品質越高的網站 AI 平台越願意引用。 |

**E-E-A-T 平均分：2.75/5**

---

## 七、人本七要素分析

| # | 要素 | 分數 | 觀察 | 顧問文章引用 |
|---|------|------|------|-------------|
| 1 | **網站人格（Brand Persona）** | 3/5 | vocus 定位為「創作者經濟平台」，在搜尋生態中有明確角色，但與競爭者的區隔度需透過時事/深度內容強化 | — |
| 2 | **內容靈魂（Content Soul）** | 3/5 | UGC 模式下有獨特觀點，但時事內容供給不足導致「渠道斷線」，缺乏平台層級的內容品質信號 | AI 導流高=品質好，品質差異被放大 [1] |
| 3 | **使用者旅程（User Journey）** | 2/5 | AMP 追蹤碼不完整可能導致使用者旅程追蹤斷裂；桌機 CLS 問題影響落地體驗；Discover CTR 若低於 5% 停止推播 [8] | 顧問文章指出連結應服務使用者體驗 |
| 4 | **技術體質（Technical Health）** | 2/5 | 桌機 CWV 差上升、AMP 版本一致性未確認、檢索未索引攀升——三個技術面問題同時存在。AMP CSS !important 可能是隱藏的技術地雷 [2] | 顧問文章《AMP 過期了嗎》：良好 CWV 比例是核心指標 |
| 5 | **連結生態（Link Ecosystem）** | 3/5 | 本期無明顯外部連結異常，但新內容的內部連結建設不足，孤島頁面問題導致索引不足 [5]；SC 反向連結監控覆蓋率有限 [3] | 顧問文章：連結應指引使用者下一步 |
| 6 | **資料敘事（Data Storytelling）** | 3/5 | 有指標監控系統產出週報，但 AMP 分流監控缺失，無法區分「真的沒曝光」vs「追蹤斷線」；CTR 下降的正確解讀需要情境脈絡 [9] | — |
| 7 | **趨勢敏銳度（Trend Sensitivity）** | 2/5 | Feb 2026 Discover Core Update 已啟動但尚未評估影響；AI 搜尋 YOY 影響 [7] 對策略規劃的反映速度待提升；Discover 死灰復燃的社群策略 [11] 尚未部署 | — |

**人本要素平均分：2.57/5**

---

## 八、SEO 成熟度自評

| 維度 | 當前等級 | 依據 | 下一步 |
|------|---------|------|-------|
| **策略（Strategy）** | L2 | 有 SEO 顧問合作和定期會議，但 AMP 分流監控缺失，時事選題缺乏系統性規劃；缺少競爭分析和預測性指標（只看落後指標） | → L3：建立時事選題日曆 + AMP 分流儀表板，導入競爭分析報告 |
| **流程（Process）** | L2 | 有指標監控和週報，但 AMP 追蹤碼稽核無 SOP、新文章發布無內部連結標準流程；執行一致性不足 | → L3：建立 AMP 稽核 SOP + 新文章連結 SOP，確保每次發布都有標準流程 |
| **關鍵字（Keywords）** | L3 | 有系統化 KW 追蹤，但與時事趨勢的連動不足；缺少 Discover 專屬的題材分析；未導入完整的意圖分群（Awareness/Consideration/Conversion） | → L4：導入時事 KW 監控 + 搜尋意圖標注，為每個關鍵字建立競爭分析 |
| **指標（Metrics）** | L2 | 週報涵蓋多維度指標，但 AMP vs canonical 分流缺失，桌機 CWV 無即時告警；資料斷層未被主動發現 | → L3：建立分流監控 + CWV 閾值告警，自動化資料品質檢查 |

---

## 九、會議提問清單

### A 類：確認事實（4 題）

- [ ] [A1] AMP Article 下滑是「真的沒曝光」還是「AMP 頁面 GA 追蹤碼/轉換事件不完整，流量在但沒記到」？目前 AMP vs canonical 是否有分開監控？（來源：S3 假設 3.1-H1）
- [ ] [A2] 檢索未索引攀升的 URL 主要是哪些類型？tag 頁、參數頁、還是正式內容頁？是否已掃描 AMP CSS !important 違規 [2]？（來源：S3 假設 3.3-H1, H3）
- [ ] [A3] 桌機 CWV 差上升的範圍——是所有模板還是集中在 post/沙龍/首頁？上次修復 CLS 是何時？（來源：S3 假設 3.4-H1）
- [ ] [A4] 本週 Discover 下滑是集中在少數文章退潮，還是整體推薦量減少？目前 Discover CTR 是否高於 5% 門檻 [8]？（來源：S3 假設 3.2-H1, H2）

### B 類：探索判斷（4 題）

- [ ] [B1] 技術體質評分低（2/5）——桌機 CWV 差、AMP 不一致、檢索未索引三個技術問題的修復優先順序建議？考量 Discover CTR 門檻 [8]，哪項修復對 Discover 流量影響最快？（來源：S7 技術體質，評分 2/5）
- [ ] [B2] 趨勢敏銳度評分低（2/5）——February Discover Core Update 已啟動，vocus 中文 UGC 是否屬於「在地原創」而有機會受益？目前有哪些具體應對措施 [10][11]？（來源：S7 趨勢敏銳度，評分 2/5）
- [ ] [B3] 以 vocus 的平台定位，什麼類型的時事選題策略最能有效提升 Top Stories 命中率？是否考慮透過社群助燃機制讓退潮文死灰復燃 [11]？（來源：S5 L3 缺口）
- [ ] [B4] 作者頁面目前是否有 Profile Page 結構化資料？E-E-A-T 中 Authoritativeness 評分僅 2/5，SC 反向連結監控僅 80% 覆蓋率 [3][6]——是否有主動連結建設計畫？（來源：S6 Authoritativeness 2/5）

### C 類：挑戰假設（3 題）

- [ ] [C1] 週報判斷 Discover 下滑「更像推薦量週期而非全站 SEO 失效」，但如果 Discover Core Update 正在改變推薦權重，這個「週期性」判斷是否過於樂觀 [10]？Discover 專業度不足 [10] 是否已成為結構性問題？（來源：S4，缺口：Discover Update 影響未評估）
- [ ] [C2] 顧問文章《AMP 過期了嗎》認為 AMP 仍有價值（CWV 良好比例高），但 Google 已不要求 Top Stories 用 AMP——vocus 是否應重新評估 AMP 策略的 ROI？AMP CSS !important 違規 [2] 修復的優先級是否應排在其他技術項目之前？（來源：S4，矛盾點：AMP 價值 vs AMP 非必要）
- [ ] [C3] KB 知識庫顯示「AI 導流越高搜尋流量越上升」[1]，AI 搜尋 YOY 影響 [7] 對 UGC 平台的長期影響如何？在 ChatGPT referral 全球下滑的背景下，vocus 是否需要調整對 AI 搜尋可見度的投資策略？（來源：S4，AI 搜尋趨勢與 E-E-A-T 交叉）

### D 類：業界趨勢（3 題）

- [ ] [D1] February 2026 Discover Core Update 是首次 Discover-only 更新，強調「在地、原創、深度」——這對 vocus 中文 UGC 平台是機會還是威脅？Discover 死灰復燃策略 [11] 在 Core Update 期間是否有效？（來源：S2 Google 官方更新）
- [ ] [D2] Google AI Mode 正在測試引用區功能——作者頁面 E-E-A-T 結構化資料 [6] 對於被 AI 搜尋引用有什麼影響？vocus 如何在 AI 搜尋崛起 [7] 中提升內容可見度？（來源：S2 業界報導）
- [ ] [D3] CTR 下降是否一定是壞事 [9]——如果曝光成長遠超點擊，Discover CTR 低於門檻 [8] 與整體曝光擴張的關係如何解讀？vocus 目前的 CTR 趨勢是好是壞？（來源：S2 SER 報導）

---

## 十、會議後行動核查表

### 即時行動（會議後 1 週內）

- [ ] 確認 AMP 追蹤碼狀態（A1），必要時建立 AMP vs canonical 分流監控 — **[流程 L2→L3]**
- [ ] 掃描 AMP CSS !important 違規 [2]，修復 AMP 驗證錯誤 — **[流程 L2→L3]**
- [ ] 確認未索引 URL 分群（A2），決定 noindex 或內部連結補強策略 [4][5] — **[指標 L2→L3]**

### 短期行動（2 週內）

- [ ] 鎖定 post/沙龍/首頁模板修正 CLS，用 PSI/Lighthouse 驗證（A3）— **[流程 L2→L3]**
- [ ] 建立時事選題日曆，提升 Top Stories 命中率（B3）— **[策略 L2→L3]**
- [ ] 為主要作者頁面實作 Profile Page 結構化資料 [6]（B4）— **[策略 L2→L3]**
- [ ] 用 Ahrefs 補充反向連結監控，覆蓋 SC 看不到的 ~20% [3]（B4）

### 中期行動（1 個月內）

- [ ] 導入搜尋意圖標注（KW 目前 L3）— **[關鍵字 L3→L4]**
- [ ] 建立 CWV 閾值告警 + Discover CTR 監控儀表板 [8] — **[指標 L2→L3]**
- [ ] 根據顧問回答更新 S3 假設——標記「已確認/已排除/待追蹤」
- [ ] 記錄 Discover Core Update 的顧問判斷，回寫知識庫
- [ ] 將本次會議重點摘要寫入 `research/12-meeting-prep-insights.md`

---

## 附錄：引用來源

[1] **AI 導流越高搜尋流量越上升、2025-12-10** — AI 導流高=品質好，放大內容品質差異 [→](/admin/seoInsight/f5066fc30f82717a)
[2] **SEO 1018、2023-10-18** — AMP !important CSS 驗證失敗影響索引 [→](/admin/seoInsight/7e12ee10da12b996)
[3] **IT 技術面 SC 27 組 KPI (25)、2021-09-25** — SC 對反向連結可見度約 80%，需搭配 Ahrefs [→](/admin/seoInsight/7fe843228fbc627a)
[4] **SC 內部指標討論、2023-09-20** — 檢索未索引根因：內部連結不足與內容稀薄 [→](/admin/seoInsight/b82545d945ee0f56)
[5] **IT 技術面 SC 27 組 KPI (6)、2021-09-06** — 孤島頁面連結數不到 3 個對 SEO 不利 [→](/admin/seoInsight/8bd713fb8988983b)
[6] **SEO 會議_2024/01/24、2024-01-24** — 作者頁面 Profile Page 結構化資料強化 E-E-A-T [→](/admin/seoInsight/23eff8f0210ef59e)
[7] **SEO 會議_20260126、2026-01-26** — AI 搜尋 YOY 負成長趨勢 [→](/admin/seoInsight/596fcacd8ad050f3)
[8] **SEO 會議_2023/10/04、2023-10-04** — Discover CTR 門檻 5-10%，低於 5% 停止推播 [→](/admin/seoInsight/5b35a5970a291a0b)
[9] **SC 內部指標討論、2024-07-22** — CTR 下降可能是好事：曝光成長幅度遠超點擊 [→](/admin/seoInsight/29f981f09f0cda23)
[10] **SC 內部指標討論、2024-01-17** — Discover 專業度不足導致流量低迷 [→](/admin/seoInsight/99a77bf6f9e89d94)
[11] **SEO 1018、2023-10-18** — 社群助燃可讓 Discover 文章死灰復燃 [→](/admin/seoInsight/c0d98f761d07611d)

<!-- citations [{"n": 1, "id": "f5066fc30f82717a", "title": "AI 導流越高搜尋流量越上升、2025-12-10", "category": "演算法與趨勢", "date": "2025-12-10", "snippet": "AI 導流高的網站搜尋流量同時在上升，品質放大效應", "chunk_url": "/admin/seoInsight/f5066fc30f82717a", "source_url": null}, {"n": 2, "id": "7e12ee10da12b996", "title": "SEO 1018、2023-10-18", "category": "內容策略", "date": "2023-10-18", "snippet": "AMP !important CSS 驗證失敗影響索引", "chunk_url": "/admin/seoInsight/7e12ee10da12b996", "source_url": null}, {"n": 3, "id": "7fe843228fbc627a", "title": "IT 技術面 SC 27 組 KPI (25)、2021-09-25", "category": "連結策略", "date": "2021-09-25", "snippet": "SC 對反向連結可見度約 80%，需搭配 Ahrefs", "chunk_url": "/admin/seoInsight/7fe843228fbc627a", "source_url": null}, {"n": 4, "id": "b82545d945ee0f56", "title": "SC 內部指標討論、2023-09-20", "category": "索引與檢索", "date": "2023-09-20", "snippet": "檢索未索引根因在於內部連結不足和內容稀薄", "chunk_url": "/admin/seoInsight/b82545d945ee0f56", "source_url": null}, {"n": 5, "id": "8bd713fb8988983b", "title": "IT 技術面 SC 27 組 KPI (6)、2021-09-06", "category": "索引與檢索", "date": "2021-09-06", "snippet": "孤島頁面連結數不到 3 個對 SEO 不利", "chunk_url": "/admin/seoInsight/8bd713fb8988983b", "source_url": null}, {"n": 6, "id": "23eff8f0210ef59e", "title": "SEO 會議_2024/01/24、2024-01-24", "category": "技術SEO", "date": "2024-01-24", "snippet": "作者頁面 Profile Page 結構化資料強化 E-E-A-T 信號", "chunk_url": "/admin/seoInsight/23eff8f0210ef59e", "source_url": null}, {"n": 7, "id": "596fcacd8ad050f3", "title": "SEO 會議_20260126、2026-01-26", "category": "搜尋表現分析", "date": "2026-01-26", "snippet": "AI 搜尋崛起對內容網站 YOY 搜尋流量呈現負成長趨勢", "chunk_url": "/admin/seoInsight/596fcacd8ad050f3", "source_url": null}, {"n": 8, "id": "5b35a5970a291a0b", "title": "SEO 會議_2023/10/04、2023-10-04", "category": "搜尋表現分析", "date": "2023-10-04", "snippet": "Discover CTR 門檻 5-10%，低於 5% 停止推播", "chunk_url": "/admin/seoInsight/5b35a5970a291a0b", "source_url": null}, {"n": 9, "id": "29f981f09f0cda23", "title": "SC 內部指標討論、2024-07-22", "category": "搜尋表現分析", "date": "2024-07-22", "snippet": "CTR 下降可能是好事：曝光成長幅度遠超點擊代表觸及範圍擴大", "chunk_url": "/admin/seoInsight/29f981f09f0cda23", "source_url": null}, {"n": 10, "id": "99a77bf6f9e89d94", "title": "SC 內部指標討論、2024-01-17", "category": "Discover與AMP", "date": "2024-01-17", "snippet": "Discover 專業度不足導致流量低迷", "chunk_url": "/admin/seoInsight/99a77bf6f9e89d94", "source_url": null}, {"n": 11, "id": "c0d98f761d07611d", "title": "SEO 1018、2023-10-18", "category": "演算法與趨勢", "date": "2023-10-18", "snippet": "社群助燃可讓 Discover 文章死灰復燃", "chunk_url": "/admin/seoInsight/c0d98f761d07611d", "source_url": null}] -->

<!-- meeting_prep_meta {"date":"20260220","scores":{"eeat":{"experience":3,"expertise":3,"authoritativeness":2,"trustworthiness":3},"maturity":{"strategy":"L2","process":"L2","keywords":"L3","metrics":"L2"}},"alert_down_count":6,"question_count":14,"generation_mode":"claude-code"} -->
