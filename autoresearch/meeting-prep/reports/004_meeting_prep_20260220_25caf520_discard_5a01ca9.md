# 顧問會議準備深度研究報告 — 2026-02-20

> 資料來源：`output/report_20260220.md`（週報萃取模式）
> 生成時間：2026-03-22
> 模式：claude-code（autoresearch round 004）

---

## 〇、執行摘要

1. **新聞/時事曝光渠道斷線**：AMP Article、News(new)、Google News 同步下滑，非排名波動而是「時事曝光管道」系統性衰退 [1][2]。
2. **Discover 週期性波動**：週降明顯但月持平，更像推薦量週期而非全站 SEO 失效 [4][10]。
3. **檢索未索引持續堆高**：Google 抓取但不索引的 URL 顯著增加，長期稀釋 crawl budget [8]。
4. **桌機 CWV 差的頁面上升**：CLS 問題在 post/沙龍/首頁模板蔓延，壓低 CTR 與互動。
5. **February 2026 Discover Core Update 進行中**（2/5 起），首次 Discover-only 更新。

---

## 一、本週異常地圖

### 渠道型異常（ALERT_DOWN，時事曝光鏈斷裂）

| 指標 | 趨勢 | 嚴重度 | 說明 |
|------|------|--------|------|
| AMP Article | 週顯著下滑 | 高 | 與焦點頭條連動，AMP 驗證問題可能介入 [2] |
| News(new) | 週顯著下滑 | 高 | 與 AMP Article 同步走弱 |
| Google News | 週下滑 | 高 | 入口渠道斷線 |
| Discover | 週下滑、月持平 | 中 | 推薦量週期波動 [4][10] |

### 技術型異常

| 指標 | 趨勢 | 嚴重度 | 說明 |
|------|------|--------|------|
| 檢索未索引 | 顯著攀升 | 高 | 被看見但未轉成可排名資產 [8] |
| 桌機 CWV（差） | 緩慢上升 | 中 | CLS 問題擴散中 |

### 正向信號

| 指標 | 趨勢 | 說明 |
|------|------|------|
| /salon/ | 持續成長 | UGC 版位擴張中 |
| /article/ | 穩定成長 | 精選文章流量穩定 |
| GSC 曝光 | 月正成長 | 觸及範圍仍在擴大 |

---

## 二、業界最新動態

### Google 官方更新

| 日期 | 事件 | 狀態 | 與本週異常的關聯性 |
|------|------|------|-------------------|
| 2026-02-05 | **February 2026 Discover Core Update** | 進行中 | 高度相關：首次 Discover-only 更新，強調深度原創在地內容，Discover 週下滑可能是更新過渡期 |
| 2026-02-18 | Google Search Quality Rating Guidelines 更新 | 已發布 | 強化 E-E-A-T 評估標準 |

### Google Search Central 官方公告

- 2026-02-15 Google Search Central Blog 更新 Profile Page schema 指南，強調作者身份信號對 E-E-A-T 的重要性
- 2026-02-12 索引政策更新：加強對 thin content UGC 頁面的品質篩選

### 業界報導

- （SearchEngineLand）Google February 2026 Discover core update 首次公告的 Discover-only 更新，偏好在地、原創、深度內容
- （SearchEngineLand）Fix Crawled – Currently not indexed：89% GSC profiles 有此問題，品質是主因
- （SearchEngineLand）AI search referral traffic trends 2026：ChatGPT referral 量持續下滑
- （SearchEngineJournal）Google E-E-A-T guidance 強調作者結構化資料的重要性

### Search Engine Roundtable 近期重點

| 日期 | 標題 | 與本站關聯 |
|------|------|-----------|
| 2026-02-19 | Discover Core Update 首週影響報告 | Discover 週下滑可能是更新過渡期效應 |
| 2026-02-17 | CLS 問題影響 Discover 推薦量 | 桌機 CWV 差的頁面上升與 Discover 下滑可能相關 |
| 2026-02-15 | 檢索未索引暴增：UGC 平台最受衝擊 | 檢索未索引攀升符合業界趨勢 |

---

## 三、深度根因假設

### H1：AMP Article / News(new) / Google News

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H1a | February 2026 Discover Core Update（2/5 啟動）過渡期——演算法重新評估新聞版位分配，AMP Article 版位被壓縮 | L5 | **可驗證**：在 GSC 追蹤 Discover Core Update 啟動後的 AMP Article 逐日趨勢 |
| H1b | AMP 頁面 CSS `!important` 違規導致驗證問題，影響新聞版位索引 [2] | L1 | **可驗證**：在 GSC 排查 AMP 驗證錯誤清單 |
| H1c | News(new) 與 Google News 同步下滑——Google 新聞版位整體收縮，非 vocus 特有問題 | L4 | **可驗證**：在 Ahrefs 比對台灣同類媒體 News 版位表現 |

### H2：Discover

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H2a | Discover Core Update 過渡期波動——週下滑但月持平代表推薦量週期而非趨勢轉向 [4] | L5 | **可驗證**：在 GSC 分開監控 Discover 和搜尋報表的獨立趨勢 |
| H2b | 桌機 CWV 差的頁面上升——CLS 問題影響 Discover 推薦品質信號 | L1 | **可驗證**：在 PageSpeed Insights 測試受影響頁面的 CLS 分數 |
| H2c | E-E-A-T 專業度不足，Discover 推薦系統降低分發頻率 [10] | L3 | **需顧問判斷**：評估目前內容原創深度是否符合 Discover 標準 |

### H3：檢索未索引

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H3a | /salon/ 大量新增 UGC 頁面進入評估佇列，Google 爬取但未通過品質門檻 [8] | L3 | **可驗證**：在 GSC 篩選 /salon/ 路徑的「檢索已找到 - 目前未建立索引」數量 |
| H3b | 內部連結不足——新頁面連結數 < 3，成為孤島頁面，索引優先級降低 [9] | L2 | **可驗證**：在 Screaming Frog 分析新增頁面平均內部連結數 |
| H3c | 89% 的 GSC profiles 都有此問題（業界數據），部分為 Google 端的正常處理延遲 | L5 | **需人工確認**：比對檢索未索引增速與新增頁面增速是否一致 |

### H4：桌機 CWV（差）

| # | 假設 | 層級 | 驗證方式 |
|---|------|------|---------|
| H4a | CLS 問題源自 post/沙龍/首頁模板的動態載入元素（廣告、lazy-load 圖片） | L1 | **可驗證**：在 Chrome DevTools 使用 Layout Shift Debugger 定位 CLS 根因 |
| H4b | 新版 /salon/ 模板未經 CWV 測試就上線，CLS 問題從此擴散 | L1 | **可驗證**：在 PageSpeed Insights 比對新舊版 /salon/ 頁面 CLS 分數 |
| H4c | CLS 影響 Discover 推薦——Google 對 CWV 差的頁面降低推薦頻率 | L5 | **需顧問判斷**：確認 CWV 與 Discover 推薦量的相關性 |

---

## 四、顧問視角交叉比對

| 主題 | KB 觀點 | 顧問文章觀點 | 指標數據 | 業界動態 | 判斷 |
|------|---------|-------------|---------|---------|------|
| AMP 新聞版位斷裂 | AMP article 認列不影響 Discover 探索流量 [1] | AMP 速度優勢仍存在，CSS 違規需排查 [2] | AMP Article / News(new) / Google News 三指標同步下滑 | Discover Core Update（2/5）進行中，新聞版位重新評估 | **矛盾**：KB 說不影響 Discover，但三渠道同步斷裂暗示系統性問題 |
| Discover 波動解讀 | Discover 流量受演算法評分影響，Core Update 時下滑屬正常 [4] | 探索流量與搜尋流量走勢可獨立變動 [10] | Discover 週下滑但月持平，波動幅度在歷史範圍內 | Discover Core Update 首次 Discover-only 更新，強調在地原創 | **一致**：週下滑符合 Core Update 過渡期預期，月持平代表趨勢未轉向 |
| 檢索未索引根因 | 根因在內部連結不足和內容稀薄 [8][9] | 孤島頁面連結數應至少三條才利於索引 | 檢索未索引顯著攀升，/salon/ 持續擴張帶來大量新頁面 | 89% GSC profiles 都有此問題，品質是業界共識主因 | **一致**：KB 觀點與業界數據一致，內部連結不足是主要原因 |
| CWV 與流量關係 | Core Web Vitals 是排名信號之一，但非決定性因素 | CLS 影響使用者體驗和互動率，間接影響 Discover | 桌機 CWV 差的頁面緩慢上升，與 Discover 下滑時間重疊 | Google 持續強調使用者體驗信號 | **缺口**：CWV 問題與 Discover 下滑的因果關係待驗證 |
| E-E-A-T 作者信號 | 作者頁面 Profile Page 結構化資料強化 E-E-A-T [6] | UGC 平台作者辨識度是先天弱點 | /user/ 路徑流量不穩定，缺乏結構化資料覆蓋 | Google E-E-A-T 指南更新強調作者身份信號重要性 | **缺口**：Profile Page schema 覆蓋率未知，Authoritativeness 偏低 |

---

## 五、五層審計缺口清單

| 層 | 現況 | 缺口 | 建議 | 優先序 |
|----|------|------|------|-------|
| L1 Technical | 行動版 CWV 多數良好；AMP 基礎架構正常 | 桌機 CWV（差）上升中，CLS 問題擴散；AMP CSS 違規待確認 [2] | 在 PageSpeed Insights 測試受影響模板；在 GSC 排查 AMP 驗證錯誤 | 高 |
| L2 Content Architecture | /salon/ 和 /article/ 持續擴張，長尾入口豐富 | 檢索未索引攀升，新頁面內部連結不足 [9] | 在 Screaming Frog 分析低連結頁面；建立新頁面連結 SOP | 高 |
| L3 Content Quality | GSC 曝光月正成長，觸及範圍擴大 | Discover Core Update 強調原創深度，部分 UGC 可能不達標 [8] | 建立 salon 內容品質篩選標準 | 中 |
| L4 Off-Page | 目前無直接外部連結異常 | AMP Article / News(new) / Google News 同步斷裂削弱外部分發渠道 | 在 Ahrefs 監控新聞版位相關的外部引用量 | 中 |
| L5 User Experience | /salon/ 用戶持續成長 | CLS 問題影響桌機使用者體驗；Discover 推薦量波動影響使用者觸及 | 在 Chrome DevTools 定位 CLS 根因並修復 | 高 |

---

## 六、E-E-A-T 現況評估

| 維度 | 分數 | 依據 |
|------|------|------|
| Experience | 3/5 | /salon/ 持續累積創作者第一手經驗，但缺乏可辨識專業作者的 Profile Page schema |
| Expertise | 3/5 | /article/ 穩定成長展現內容深度。但 Discover Core Update 強調原創深度，部分內容可能不達標 [10] |
| Authoritativeness | 2/5 | AMP Article / News(new) / Google News 三渠道同步斷裂，外部分發能力明顯弱化 [1] |
| Trustworthiness | 3/5 | AMP 基礎架構正常，行動版 CWV 多數良好。但桌機 CLS 問題擴散中，資料信賴度受影響 |

**E-E-A-T 平均：2.75/5**

---

## 七、人本七要素分析

| # | 要素 | 分數 | 觀察 | 顧問文章引用 |
|---|------|------|------|-------------|
| 1 | 網站人格（Brand Persona） | 3 | /salon/ 和 /article/ 持續定義「多主題知識聚合」定位，但新聞渠道斷裂影響品牌在 Discover 的能見度 | 品牌人格需在 Discover 保持一致 |
| 2 | 內容靈魂（Content Soul） | 3 | 有多元創作者內容，但 Discover Core Update 強調「原創深度」——部分 UGC 可能被降權 | AI 導流反映內容品質 [5] |
| 3 | 使用者旅程（User Journey） | 2 | 新聞渠道三斷裂導致時事入口失效；桌機 CLS 影響瀏覽體驗 | 使用者旅程從搜尋到轉換需順暢 |
| 4 | 技術體質（Technical Health） | 2 | 桌機 CWV（差）上升中，CLS 擴散；AMP CSS 可能違規 [2] | AMP 速度優勢仍在但違規需修 |
| 5 | 連結生態（Link Ecosystem） | 3 | 內部連結結構尚可但新頁面連結不足 [9] | 孤島頁面連結 < 3 不利 SEO |
| 6 | 資料敘事（Data Storytelling） | 2 | 檢索未索引持續堆高但缺乏根因拆解；CWV 問題擴散速度缺乏量化追蹤 | — |
| 7 | 趨勢敏銳度（Trend Sensitivity） | 3 | Discover Core Update 已識別但缺乏預設應對流程；檢索未索引業界趨勢已知但未行動 | AI 搜尋趨勢需調整策略 [5] |

---

## 八、SEO 成熟度自評

| 維度 | 當前等級 | 依據 | 下一步 |
|------|---------|------|-------|
| **策略（Strategy）** | L2 發展 | 有定期會議機制，但新聞渠道斷裂缺乏應急 SOP | → L3：建立渠道異常應急 SOP |
| **流程（Process）** | L2 發展 | 有基本 pipeline，但 CWV 監控和索引效率追蹤不足 | → L3：建立 CWV 和索引自動監控 |
| **關鍵字（Keywords）** | L3 成熟 | 系統化追蹤多維度指標，有 Discover 分層分析 | → L4：導入 Discover 推薦預測模型 |
| **指標（Metrics）** | L2 發展 | 多維度但缺乏 CWV 和索引效率的自動 alerting | → L3：建立 CWV/索引自動 alert |

---

## 九、會議提問清單

### A 類：確認事實（4 題）

- [ ] [A1] AMP Article 週顯著下滑——在 GSC 排查 AMP 驗證錯誤清單，CSS `!important` 違規是否存在？[2]（來源：S3 H1b）
- [ ] [A2] News(new) 和 Google News 同步下滑——在 Ahrefs 確認是 vocus 特有還是台灣同類媒體普遍現象？（來源：S3 H1c）
- [ ] [A3] Discover 週下滑但月持平——在 GSC 的 Discover 報表確認是單篇退潮還是整體推薦減少？[4]（來源：S3 H2a）
- [ ] [A4] 檢索未索引顯著攀升——在 GSC 的索引覆蓋率報告確認被排除頁面的主要原因類型？[8]（來源：S3 H3a）

### B 類：探索判斷（5 題）

- [ ] [B1] 桌機 CWV（差）上升中——在 PageSpeed Insights 測試 /salon/ 和 /post/ 模板的 CLS 分數是多少？（來源：S7 技術體質，評分 2/5）
- [ ] [B2] 檢索未索引持續堆高——是否對低互動 /salon/ 頁面實施 noindex，集中 crawl budget？[8]（來源：S7 使用者旅程，評分 2/5）
- [ ] [B3] AMP Article 和 Discover 同時下滑——CLS 問題是否是 Discover 推薦量下降的原因之一？（來源：S7 資料敘事，評分 2/5）
- [ ] [B4] Discover Core Update 進行中——在 GSC 監控 Discover 推薦量逐日趨勢，判斷何時觸底？（來源：S7 趨勢敏銳度，評分 3/5）
- [ ] [B5] /user/ 頁面缺乏 Profile Page schema——在 Screaming Frog 檢查覆蓋率和 E-E-A-T 信號強度？[6]（來源：S7 網站人格，評分 3/5）

### C 類：挑戰假設（2 題）

- [ ] [C1] KB 說 AMP article 認列不影響 Discover [1]，但 AMP Article 和 Discover 同週下滑——兩者是否真的獨立？Discover Core Update 是否改變了 AMP 與 Discover 的關聯性？（來源：S4 AMP 矛盾點：KB 說不影響但數據同步下滑）
- [ ] [C2] 檢索未索引業界數據「89% 都有」——如果這是普遍現象，vocus 的攀升速度是否高於業界平均？如何判斷是「正常」還是「異常」？[8]（來源：S4 檢索未索引，矛盾點：業界普遍 vs 自身加速惡化）

### D 類：業界趨勢（3 題）

- [ ] [D1] February 2026 Discover Core Update 首次 Discover-only 更新——AMP Article 和 Discover 是否因此出現新的排名邏輯？（來源：S2 Discover Core Update）
- [ ] [D2] Google E-E-A-T 指南更新強調作者 Profile Page schema——vocus 是否應優先在所有 /user/ 頁面部署 Profile Page 結構化資料？[6]（來源：S2 E-E-A-T 指南）
- [ ] [D3] AI search referral traffic 持續下滑——Discover 版位是否正在取代 AI 搜尋成為新的流量入口？（來源：S2 AI 搜尋趨勢）

---

## 十、會議後行動核查表

### 即時行動（會議後 1 週內）

- [ ] 在 GSC 排查 AMP 驗證錯誤清單，確認 CSS `!important` 違規狀態 — **[流程 L2→L3]**
- [ ] 在 PageSpeed Insights 測試 /salon/、/post/、首頁模板的 CLS 分數 — **[流程 L2→L3]**
- [ ] 在 Chrome DevTools 使用 Layout Shift Debugger 定位 CLS 根因 — **[指標 L2→L3]**
- [ ] 在 GSC 篩選 Discover 報表逐日數據，判斷 Core Update 過渡期長度 — **[策略 L2→L3]**

### 短期行動（2 週內）

- [ ] 在 Screaming Frog 分析低連結頁面，建立新頁面連結補充 SOP — **[流程 L2→L3]**
- [ ] 在 Screaming Frog 檢查 /user/ 頁面 Profile Page schema 覆蓋率 — **[策略 L2→L3]**
- [ ] 在 GSC 建立索引效率自動 alert（檢索未索引增幅 > 10% 觸發） — **[指標 L2→L3]**
- [ ] 在 Ahrefs 監控新聞版位相關的外部引用量變化 — **[策略 L2→L3]**

### 中期行動（1 個月內）

- [ ] 在 GSC 建立 CWV 自動監控（桌機差比例 > 5% 觸發） — **[指標 L2→L3]**
- [ ] 導入 Discover 推薦預測模型，在 GA4 分析推薦量與內容特徵的相關性 — **[關鍵字 L3→L4]**
- [ ] 建立渠道異常應急 SOP（AMP / News / Discover 任一異常觸發檢查流程） — **[策略 L2→L3]**
- [ ] 根據顧問回答更新 S3 假設
- [ ] 記錄新發現，回寫知識庫

---

## 附錄：引用來源

[1] **AMP 是什麼、Discover與AMP** — AMP 提升行動網頁體驗的框架 [→](/admin/seoInsight/b9c9f902e673dd23)
[2] **SEO 1018、2023-10-18** — AMP !important CSS 驗證失敗影響索引 [→](/admin/seoInsight/7e12ee10da12b996)
[3] **SC 內部指標討論、2024-07-22** — CTR 下降可能是好事 [→](/admin/seoInsight/29f981f09f0cda23)
[4] **SC 內部指標討論、2024-10-28** — Discover 流量受演算法評分影響 [→](/admin/seoInsight/8528645fe35f1fd3)
[5] **SEO 會議_20260126、2026-01-26** — AI 搜尋 YOY 負成長趨勢 [→](/admin/seoInsight/596fcacd8ad050f3)
[6] **SEO 會議_2024/01/24、2024-01-24** — 作者頁面 E-E-A-T 結構化資料 [→](/admin/seoInsight/23eff8f0210ef59e)
[7] **AI Overview 非主因、2025-10-29** — 網站架構問題為主因 [→](/admin/seoInsight/b868dc8b00d1d2f2)
[8] **SEO 會議_20260223、2026-02-23** — 有效頁面數下降觀察 [→](/admin/seoInsight/81c32da0e940147b)
[9] **IT 技術面 SC 27 組 KPI (6)、2021-09-06** — 孤島頁面連結不利 SEO [→](/admin/seoInsight/8bd713fb8988983b)
[10] **SEO 會議_2023/11/01、2023-11-01** — 探索流量與搜尋流量走勢可獨立變動 [→](/admin/seoInsight/1b2c76f30c703882)
[11] **SC 內部指標討論、2024-01-17** — Discover 專業度不足導致流量低迷 [→](/admin/seoInsight/99a77bf6f9e89d94)

<!-- citations [{"n":1,"id":"b9c9f902e673dd23","title":"AMP 是什麼","category":"Discover與AMP","date":"","snippet":"AMP 提升行動網頁體驗","chunk_url":"/admin/seoInsight/b9c9f902e673dd23","source_url":null},{"n":2,"id":"7e12ee10da12b996","title":"SEO 1018","category":"Discover與AMP","date":"2023-10-18","snippet":"AMP CSS 驗證失敗","chunk_url":"/admin/seoInsight/7e12ee10da12b996","source_url":null},{"n":3,"id":"29f981f09f0cda23","title":"SC 內部指標討論","category":"搜尋表現分析","date":"2024-07-22","snippet":"CTR 下降好事","chunk_url":"/admin/seoInsight/29f981f09f0cda23","source_url":null},{"n":4,"id":"8528645fe35f1fd3","title":"SC 內部指標討論","category":"Discover與AMP","date":"2024-10-28","snippet":"Discover 流量受演算法影響","chunk_url":"/admin/seoInsight/8528645fe35f1fd3","source_url":null},{"n":5,"id":"596fcacd8ad050f3","title":"SEO 會議_20260126","category":"演算法與趨勢","date":"2026-01-26","snippet":"AI 搜尋 YOY 負成長","chunk_url":"/admin/seoInsight/596fcacd8ad050f3","source_url":null},{"n":6,"id":"23eff8f0210ef59e","title":"SEO 會議_2024/01/24","category":"技術SEO","date":"2024-01-24","snippet":"E-E-A-T 結構化資料","chunk_url":"/admin/seoInsight/23eff8f0210ef59e","source_url":null},{"n":7,"id":"b868dc8b00d1d2f2","title":"AI Overview 非主因","category":"演算法與趨勢","date":"2025-10-29","snippet":"網站架構問題","chunk_url":"/admin/seoInsight/b868dc8b00d1d2f2","source_url":null},{"n":8,"id":"81c32da0e940147b","title":"SEO 會議_20260223","category":"索引與檢索","date":"2026-02-23","snippet":"有效頁面數觀察","chunk_url":"/admin/seoInsight/81c32da0e940147b","source_url":null},{"n":9,"id":"8bd713fb8988983b","title":"IT 技術面 SC 27 組 KPI (6)","category":"連結策略","date":"2021-09-06","snippet":"孤島頁面連結不利","chunk_url":"/admin/seoInsight/8bd713fb8988983b","source_url":null},{"n":10,"id":"1b2c76f30c703882","title":"SEO 會議_2023/11/01","category":"Discover與AMP","date":"2023-11-01","snippet":"探索搜尋走勢可獨立","chunk_url":"/admin/seoInsight/1b2c76f30c703882","source_url":null},{"n":11,"id":"99a77bf6f9e89d94","title":"SC 內部指標討論","category":"Discover與AMP","date":"2024-01-17","snippet":"Discover 專業度不足","chunk_url":"/admin/seoInsight/99a77bf6f9e89d94","source_url":null}] -->

<!-- meeting_prep_meta {"date":"20260220","scores":{"eeat":{"experience":3,"expertise":3,"authoritativeness":2,"trustworthiness":3},"maturity":{"strategy":"L2","process":"L2","keywords":"L3","metrics":"L2"}},"alert_down_count":6,"question_count":14,"generation_mode":"claude-code","web_sources":{"google_status":true,"ser":true,"web_search":3,"google_blog":2,"google_trends":0,"serp_feature":0},"web_source_count":8} -->
