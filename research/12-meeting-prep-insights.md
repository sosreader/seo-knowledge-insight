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
| 2026-04-13 | E:3 E:3 A:2 T:3 (avg 2.75) | 策略:L2 流程:L2 KW:L3 指標:L2 | ALERT_DOWN 27→33 但主因聚焦 AMP 崩塌（警告 47K→241K）；「雙速復甦」——Organic +6.0% 翻正、Referral +89.7% 爆發 vs AMP/News 持續惡化；娛樂 KW 連續兩週反彈（影評 -81→-16.9%）；March Core Update 4/8 完成；Discover 連續兩週正向週環比；Authoritativeness 1→2（外鏈穩定+Referral 爆發）；技術體質 2→3；連結生態 1→2 |
| 2026-04-27 | E:3 E:3 A:2 T:3 (avg 2.75) | 策略:L2 流程:**L3↑** KW:L3 指標:**L3↑** | **「結構復原 vs 流量斷層」悖論週**——AMP 警告 -69.5% 週（217K→66K）、有效 +57.2% 週、Mobile 好 +57.9% 週同步爆發 vs Organic Search -19.0% 週（過去三月最大幅）、工作階段 -15.2% 週；CTR 仍 +0.8% 週支持「Google 重新驗證過渡期」假設；回應時間 283ms 創歷史新低；檢索未索引第五週上升 +15.6%；技術體質 3→4（AMP 復原+回應時間+Mobile 連動）；Process L2→L3（修復循環自動化）；Metrics L2→L3（CTR/曝光/點擊三軸悖論診斷） |

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

### 2026-04-13
- **一致**：「雙速復甦」格局確認——Organic Search +6.0% 翻正、Referral +89.7% 爆發，與 AMP/News 持續惡化形成明確脫鉤。搜尋基本盤不受 AMP 崩塌影響。
- **矛盾**：AMP 索引(警告）47K→241K（+409%），但 Google 已於 2021 年停止 AMP 為排名因子——AMP 崩塌的實際 SEO 影響可能小於指標表面值，主要影響在 Google News APP 路徑 [5] 和 Mobile CWV 統計 [13]。
- **一致**：娛樂 KW 連續兩週反彈（影評 -81→-16.9%、電影 -50.5→-40.3%），March Core Update 4/8 完成後趨穩。
- **缺口→部分解決**：外鏈穩定（weekly 0.0%）但品質分析仍未完成。Referral +89.7% 爆發可能帶入新外鏈，需 Ahrefs 確認。
- **新發現**：March Core Update 完成後，Authoritativeness 從 1 回升至 2（Referral 爆發 + 外鏈穩定），技術體質 2→3（Coverage 持續成長），連結生態 1→2。E-E-A-T 平均維持 2.75 但 Authoritativeness 止跌。

### 2026-04-27
- **悖論辨識**：本週是「**結構復原 vs 流量斷層**」悖論週——AMP 警告 -69.5% 週（史詩級反轉）+ Mobile 好 +57.9% 週同步爆發，但 Organic Search -19.0% 週、工作階段 -15.2% 週急跌。**新分析框架**：CTR/曝光/點擊三軸交叉判斷流量下跌類型——CTR 微升 +0.8% 排除「演算法降權」、AI 引擎側成長 +21.6% 排除「AIO 截流主因」、爬蟲量 +7.5% 排除「伺服器降頻被動」，**最支持「Google 重新驗證過渡期」假設**。
- **一致**：上週 H1 假設「AMP 批次失效根因」本週 [Validated]——AMP 警告 217K→66K 的 -69.5% 收斂幅度約等於前 3 週累積增量的反向歸零，CSS `!important`、`<amp-iframe>`、amphref 修復假設得到大規模驗證。
- **矛盾**：AMP 結構性復原但流量同步暴跌——技術修復成功但流量未即時回補。可能解釋：Google 對 AMP 重新驗證期間部分 URL 暫時掉出 SERP，預計 1-2 週後流量回補。
- **業界對標**：April 2026 ranking volatility 9.5/10 為全年最高，部分網站單日 30-40% 流量波動——本站 -19.0% 週環比落在業界整體波動區間內，**降低「本站獨立問題」假設權重**。商業類 KW（必買 -22.7%、攻略 -41.7%）下跌與業界 71% affiliate domains 負面、AIO 14% shopping queries 滲透高度吻合。
- **新警示**：檢索未索引連續第五週上升並加速 +15.6% 週，業界研究指出突發性大幅上升常為**網站被駭警訊**（commerce / 醫療廣告 URLs）—— P0 行動必須先採樣 50-100 個「已檢索-未索引」URLs 確認合法性。
- **缺口→升級**：上週 P2「Ahrefs 外部連結質量審計」本週仍未完成，前週 Referral +89.7% 爆發本週週 -19.5% 大幅回落，**新來源質量問題不再可延後**。
- **成熟度雙升**：Process L2→L3（AMP 修復→部署→驗證循環自動化）、Metrics L2→L3（多維度悖論診斷工具化）。技術體質 3→4（三項技術指標同時進入過去半年最佳區間）。E-E-A-T 平均維持 2.75（未到結構性訊號重評估觸發點）。
