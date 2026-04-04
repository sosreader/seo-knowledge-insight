# Meeting Prep 洞察追蹤

> 由 `/meeting-prep` 自動累積，追蹤 E-E-A-T + SEO 成熟度評分變化趨勢。
> 每次執行 append 一行評分 + 重要交叉比對發現。

---

## 評分追蹤表

| 日期 | E-E-A-T (E/E/A/T) | 成熟度 (策略/流程/KW/指標) | 重要發現 |
|------|-------------------|--------------------------|---------|
| 2026-03-12 | E:3 E:3 A:2 T:3 (avg 2.75) | 策略:L2 流程:L2 KW:L3 指標:L2 | AI 可見度月降 16%；外部連結月降 18%；10 項路徑指標 latest=null 資料斷層 |
| 2026-02-20 | E:3 E:3 A:3 T:3 (avg 3.00) | 策略:L2 流程:L2 KW:L2 指標:L2 | 時事曝光渠道斷裂（AMP/News/Google News）；Discover 週期波動；檢索未索引攀升；桌機 CWV 差 |
| 2026-02-27 | E:3 E:2 A:2 T:3 (avg 2.50) | 策略:L2 流程:L2 KW:L2 指標:L2 | Health Score 0；AMP Article -166%；Sessions -16%；AI 三平台崩退 50%+；/salon/ +123% |
| 2026-03-09 | E:3 E:3 A:2 T:3 (avg 2.75) | 策略:L2 流程:L2 KW:L3 指標:L2 | 連結雙重衰退（外部-18%+內部-16%）；AI 月降但週轉正；Video +340%；Discover 回穩 |
| 2026-03-21 | E:3 E:3 A:2 T:3 (avg 2.75) | 策略:L2 流程:L2 KW:L3 指標:L2 | Discover -55.4%（Feb Core Update 影響）；AI 流量全面正成長驗證顧問假說；外鏈連續三期降；/article/ 索引惡化 +45.6%；March Core Update 滾動中 |

| 2026-03-22 | E:3 E:3 A:2 T:3 (avg 2.75) | 策略:L2 流程:L2 KW:L3 指標:L2 | Feb Discover Core Update 完成、域名池-8%；AI 流量全面正成長驗證顧問假說；外鏈連續4期降→升級必做；AIO 觸發 48% 查詢、有機 CTR -61% |
| 2026-03-29 | E:3 E:3 A:2 T:3 (avg 2.75) | 策略:L2 流程:L2 KW:L3 指標:L2 | March Core Update 3/27 啟動（資料僅含 1 天）；Discover 月-26%週+57% 高波動；外鏈-28% 連續5期降；KW:影評-44% vs KW:攻略+63% 意圖分化；AI 流量全正（GPT+35%/Gemini+41%/Perplexity+24%）；AIO ~58% 搜尋觸發 |
| 2026-04-05 | E:3 E:3 A:2 T:3 (avg 2.75) | 策略:L2 流程:L2 KW:L3 指標:L2 | Discover+News+News(new) 三路 ALERT_DOWN（上週反彈未持續）；ALERT_DOWN 從 19→3 但更集中；Health Score 50/100；Core Update 第 2 週（AI 內容-71%/原創+22%/Info Gain 核心信號）；AIO 點擊降 42%；突發新聞+103% 但本站未捕捉 |

### Autoresearch Meeting-Prep 實驗結果 (2026-03-22~23)

33 rounds 自主 prompt 優化（`autoresearch/meeting-prep-mar22`），composite eval 0.831→0.903（+8.7%）。

**關鍵改進**：S10 三要素（tool+verb+maturity）、S3→S9 cross-section coverage（KW heading、大型 S1 分群策略）、citation category 指引、heading no-parenthesis rule。

**瓶頸**：cross_section_coherence 受 eval S3/S9 regex 不對稱限制（S3 broad regex 提取 GPT/Gemini/Video/salon，S9 narrow regex 無法匹配），theoretical ceiling 0.919。

<!-- 以下為自動累積區域 -->

---

## 交叉比對發現

<!-- 格式：### YYYY-MM-DD\n- 矛盾/一致/缺口描述 -->

### 2026-03-12
- **矛盾**：顧問文章「AI 導流高=網站健康」vs vocus AI 可見度月降 16%、GPT -40%、Gemini -22%。需釐清是內容品質問題還是流量計算方式變更。
- **一致**：KB 與顧問均認為 CTR 下降可能是正面訊號（觸及擴大），但需排除 AIO 造成的 CTR 稀釋效應。
- **缺口**：Feb 2026 Discover Core Update 已完成近兩週，但缺少 vocus Discover 專屬數據，無法評估影響。
- **缺口**：外部連結衰退趨勢明確但缺少連結品質分析（高價值 vs 低價值外鏈流失）。

### 2026-02-20
- **缺口**：Discover Core Update 進行中但缺少 vocus Discover 專屬數據，無法評估初期影響。
- **一致**：AMP 技術指標正常但新聞版位同步下滑，KB 與顧問均確認非技術問題。

### 2026-02-27
- **矛盾**：顧問「AI 導流高=內容品質好」vs vocus AI 三平台崩退 50%+。嚴重度升級：與 Organic -15% 同向，可能已進入「AI 與搜尋都忽略」區間。
- **一致但需修正**：KB 「CTR 下降是好事」在 AIO 時代需修正框架——GA/GSC 落差 10% 超出 CTR 稀釋可解釋範圍。
- **缺口**：/salon/ +123% 但索引效率惡化（+36%），無法區分新頁面等待期 vs 品質不足。

### 2026-03-09
- **矛盾**：AI 流量月降但週轉正——品質改善信號還是統計噪音？需要更長觀察窗口（建議 4-6 週）。
- **一致**：Discover 回穩（+17.7% 週），與 Discover Core Update 完成後的預期一致。
- **缺口**：連結雙重衰退（外部 -18% + 內部 -16%）的行動門檻不明確，缺乏連結品質分析。

### 2026-03-22
- **一致**：顧問「AI 導流高 = 網站健康」假說再次驗證——AI 四平台全面正成長（GPT +26.9%/週、Gemini +53.3%/月），搜尋流量同步雙升（曝光 +14.1%、點擊 +15.6%）。
- **矛盾**：AI + 搜尋雙升 vs Discover -55.4% 暴跌——Discover Core Update 的 expertise 評估標準可能與搜尋/AI 引擎分歧，需釐清 vocus 在 Discover 被排除的具體原因。
- **矛盾**：KB「不要單獨針對 Discover 優化」vs Feb 2026 首次 Discover 專屬更新——舊建議可能過時。
- **缺口→升級**：外鏈連續 4 期下降（本期 -30.5%），連續 4 次記錄缺口仍無品質分析行動。本次升級為必做行動。
- **新發現**：AI Overview 觸發 48% 查詢、有機 CTR -61%、但被引用品牌 +35% 點擊——「被 AI 引用」成為新護城河。

### 2026-03-21
- **一致**：顧問「AI 導流高 = 網站健康」假說得到驗證——AI 流量全面正成長（GPT +26.9%/週、Gemini +53.3%/月），搜尋流量同步雙升。2026-02-27 的「AI 三平台崩退」已完全反轉。
- **矛盾**：AI 流量升 vs Discover -55.4% 暴跌——同一網站被 AI/搜尋引擎肯定，卻被 Discover 演算法懲罰。Feb Discover Core Update 的 expertise 信號評估標準可能與搜尋/AI 引擎分歧。
- **矛盾**：檢索未索引惡化集中在核心路徑（/article/ +45.6%、/salon/ +77.5%），而低品質路徑（/tag/ -43%、/en/ -49.6%）反而改善——與「補強內部連結」的標準建議不完全吻合，可能需更根本的內容品質提升。
- **缺口**：外鏈連續三期下降（本期 -30.5%）仍缺品質分析——已連續 4 次記錄此缺口，建議升級為必做行動。
- **趨勢確認**：E-E-A-T 連續兩期停滯 2.75，Authoritativeness = 2 持續是最大短板。成熟度全維度持平。
