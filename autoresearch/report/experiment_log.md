# Experiment Log — autoresearch/report

Baseline composite_v3: **0.6383** (2026-03-22)

## Experiment Details

### Baseline — golden fixture eval
- **File:** (none — baseline measurement)
- **Fixture:** `eval/fixtures/reports/report_20260321_c202663e.md`
- **Composite:** 0.6383
- **Key scores:**
  - action_specificity: 0.3125 (5/16 specific action items)
  - quadrant_judgment: 0.0000 (no exact quadrant keyword match)
  - section_depth: 0.3787 (section 一 and 六 much longer than others)
  - causal_chain: 0.6000 (3/5 structured blocks)
  - maturity_labeled: 0.6667 (4/6 total labels)
  - cross_metric: 0.7333 (11/15 qualifying lines)
  - data_evidence: 0.7571 (53/70 paragraphs with data)
  - priority_balance: 0.7778 (🔴4/🟡1/🟢3)
  - citation_integration: 0.8571 (6/7 sections with citations)
  - temporal_dual: 0.9333 (14/15 dual-frame lines)

---

### #1 — exact quadrant keywords + explanation signals | KEPT

- **File:** `.claude/commands/generate-report.md`
- **Change:** Section 二 — 將象限格式從 `高曝光 / 低 CTR` 改為 `高曝光低點擊`（四字格式），並在每個選項後加入解釋信號詞（表示/代表/意味/建議）
- **Diff:**
  ```diff
  - - 高曝光 / 低 CTR → Title 吸引力問題或 SERP Feature 搶走點擊
  + - **高曝光低點擊** → 表示 Title 吸引力問題或 SERP Feature 搶走點擊，建議優先檢查 Title/Description
  ```
- **Snapshot:** 20260305-172646
- **Alert names:** AMP Article,/,KW: 電影,KW: 股,營運 KW：保養,Video,News(new),Google News,AMP Article Ratio,新聞比例,首頁占比,工作階段總數（七天）,Organic Search (工作階段),Organic Social (工作階段),Referral (工作階段),GPT (工作階段),Gemini,Perplexity,AI 占比,檢索未索引失敗數目,/en/
- **Report:** `reports/001_20260305-172646_keep_8815c31.md`
- **Composite:** 0.6841 | **Delta:** +0.0458 (+7.2%)
- **Commit:** 8815c31
- **Status:** keep — quadrant_judgment 從 0.0 → 1.0（+0.07 weighted），足以抵銷其他衰退
- **Impact:**
  - quadrant_judgment: 0.0 → 1.0 (+1.0)
  - citation_integration: 0.857 → 1.0 (+0.143)
  - cross_metric: 0.733 → 0.933 (+0.200)
  - alert_coverage: 1.0 → 1.0 (=)
  - maturity_labeled: 0.667 → 1.0 (+0.333)
  - data_evidence: 0.757 → 0.286 (-0.471)
  - temporal_dual: 0.933 → 0.467 (-0.466)
  - causal_chain: 0.600 → 0.000 (-0.600)
  - section_depth: 0.379 → 0.551 (+0.172)

---

### #2 — structured causal blocks + dual temporal frame | KEPT

- **File:** `.claude/commands/generate-report.md`
- **Change:** Section 一的異常指標解讀改為要求 ≥5 個 `**現象**→**原因**→**行動**` 結構化區塊，並要求每行同時包含月趨勢和週環比百分比
- **Diff:**
  ```diff
  - - 你對該指標下滑的推理（結合 qaMap 的 KB 知識）
  + - 每個主要異常指標用以下格式分析（至少 5 個區塊）：
  +   **現象** {指標名稱}月趨勢 {X}%、週環比 {Y}%（latest {數值}）
  +   **原因** {你的推理 + KB 知識佐證}
  +   **行動** {具體建議 + KB 引用}
  + **格式要求**：每個指標描述行必須同時包含月趨勢和週環比百分比
  ```
- **Snapshot:** 20260306-184745
- **Alert names:** AMP Article,/article/,/post,/salon/,營運 KW：保養,News(new),外部連結,週平均回應時間,AMP Article Ratio,內部連結分布,GPT (工作階段),Gemini,AI 占比,全網域,檢索未索引 (全部),/en/,/tag/,/user/,總合,總合/全網域
- **Report:** `reports/002_20260306-184745_keep_3126673.md`
- **Composite:** 0.7428 | **Delta:** +0.0587 (+8.6% from #1)
- **Commit:** 3126673
- **Status:** keep — causal_chain 從 0.0 → 1.0，temporal_dual 從 0.467 → 0.733
- **Impact:**
  - causal_chain: 0.000 → 1.000 (+1.000)
  - temporal_dual: 0.467 → 0.733 (+0.266)
  - cross_metric: 0.933 → 1.000 (+0.067)
  - citation_integration: 1.000 → 0.857 (-0.143)
  - priority_balance: 0.778 → 0.444 (-0.334)
  - data_evidence: 0.286 → 0.271 (-0.015)

---

### #3 — emoji per action item for priority_balance | KEPT

- **File:** `.claude/commands/generate-report.md`
- **Change:** Section 六 — 要求每個行動項目前加 emoji（🔴/🟡/🟢），明確範例 🔴≥4/🟡≥3/🟢≥2
- **Diff:**
  ```diff
  - 🔴 高優先（需立即處理）：針對 ALERT_DOWN，各一條具體行動
  + 🔴 高優先：
  + - 🔴 {行動 1} + KB 佐證連結
  + - 🔴 {行動 2} ...
  ```
- **Snapshot:** 20260305-081902
- **Alert names:** (same 21 as Round 1)
- **Report:** `reports/003_20260305-081902_keep_361080c.md`
- **Composite:** 0.7431 | **Delta:** +0.0003 (+0.04% from #2)
- **Commit:** 361080c
- **Status:** keep — priority_balance 0.444→1.0, temporal_dual 0.733→0.933；微幅提升但多個指標改善
- **Impact:**
  - priority_balance: 0.444 → 1.000 (+0.556)
  - temporal_dual: 0.733 → 0.933 (+0.200)
  - cross_metric: 1.000 → 0.733 (-0.267)
  - action_specificity: 0.409 → 0.333 (-0.076)
  - section_depth: 0.549 → 0.456 (-0.093)

---

### #4 — specific action verbs + reduce analysis list items | KEPT

- **File:** `.claude/commands/generate-report.md`
- **Change:** 加入全局行動項目用詞規範（具體動詞+工具名），Section 一改為段落描述取代 list items
- **Diff:**
  ```diff
  + **行動項目用詞規範**：所有 - 開頭的行動建議都應使用具體動詞（檢查、驗證、排查、修復、設定...）
  + 搭配具體工具名（GSC、Search Console、PageSpeed、GA4、Screaming Frog）。
  + 分析性段落盡量用段落文字而非 - 列表。
  ```
- **Snapshot:** 20260305-172646
- **Report:** `reports/004_20260305-172646_keep_f1a1454.md`
- **Composite:** 0.8149 | **Delta:** +0.0718 (+9.7% from #3)
- **Commit:** f1a1454
- **Status:** keep — action_specificity 0.333→1.0 是最大提升，分析改用段落減少了非行動 list items
- **Impact:**
  - action_specificity: 0.333 → 1.000 (+0.667)
  - temporal_dual: 0.933 → 0.867 (-0.066)
  - cross_metric: 0.733 → 0.600 (-0.133)
  - data_evidence: 0.357 → 0.300 (-0.057)
  - section_depth: 0.456 → 0.472 (+0.016)

---

### #5 — causal connectors for cross_metric | KEPT

- **File:** `.claude/commands/generate-report.md`
- **Change:** 加入「跨指標因果分析規範」，要求大量使用因果連接詞（導致/因此/進而/由於/反映/源自）
- **Diff:**
  ```diff
  + **跨指標因果分析規範**：分析段落中必須大量使用因果連接詞
  + 每個 section 至少 2 句含因果連接詞的跨指標推理
  ```
- **Snapshot:** 20260306-184745
- **Report:** `reports/005_20260306-184745_keep_9d35573.md`
- **Composite:** 0.8529 | **Delta:** +0.0380 (+4.7% from #4)
- **Commit:** 9d35573
- **Status:** keep — cross_metric 0.600→1.0
- **Impact:**
  - cross_metric: 0.600 → 1.000 (+0.400)
  - section_depth: 0.472 → 0.532 (+0.060)
  - temporal_dual: 0.867 → 0.667 (-0.200)
  - data_evidence: 0.300 → 0.271 (-0.029)

---

## 累計分析（Round 1-5）

- Best composite: 0.8529（+33.6% from baseline 0.6383）
- 最有效的假設類型：action_specificity 用詞規範（#4, +9.7%）、causal_chain 結構化區塊（#2, +8.6%）
- 反復失敗的面向：data_evidence 嘗試 0 次但持續衰退（0.757→0.271）
- 已飽和指標（=1.0）：quadrant_judgment, causal_chain, priority_balance, action_specificity, cross_metric, citation_integration(~0.86), top_recommendation, L1 全部
- 仍有提升空間：data_evidence(0.271), section_depth(0.532), temporal_dual(0.667), citation_integration(0.857)

### 失敗模式索引
| 模式 | 出現次數 | 實驗編號 |
|------|---------|---------|
| data_evidence 持續衰退 | 5 | #1-#5 全部 |
| temporal_dual 不穩定 | 3 | #1(0.47), #4(0.87), #5(0.67) |

### #6 — balanced section depth (400-600 chars) | discarded

- **File:** `.claude/commands/generate-report.md`
- **Change:** 加入 section 字數均衡規範（每 section 400-600 字）
- **Snapshot:** 20260305-081902
- **Report:** `reports/006_20260305-081902_discard_d4d633d.md`
- **Composite:** 0.8305 | **Delta:** -0.0224 (-2.6% from #5)
- **Status:** discard — section_depth 0.532→0.660 (+0.128) 但 causal_chain 1.0→0.6 (-0.4)
- **失敗分類:** causal_chain 衰退最多（-0.4），壓縮 Section 一 導致因果區塊不足 5 個

### #7 — expand short sections without compressing long ones | KEPT

- **File:** `.claude/commands/generate-report.md`
- **Change:** 加入 Section 深度均衡規範，只擴展短 section（三/四/五），不壓縮長 section（一/六）
- **Diff:**
  ```diff
  + **Section 深度均衡規範**：Section 三、四、五 需增加推理深度：
  + 每個至少 3 段分析段落。Section 一和六不需壓縮。
  ```
- **Snapshot:** 20260305-172646
- **Report:** `reports/007_20260305-172646_keep_c678abf.md`
- **Composite:** 0.8715 | **Delta:** +0.0186 (+2.2% from #5)
- **Commit:** c678abf
- **Status:** keep — section_depth 0.532→0.710，causal_chain 保持 1.0
- **Impact:**
  - section_depth: 0.532 → 0.710 (+0.178)
  - temporal_dual: 0.667 → 0.800 (+0.133)
  - cross_metric: 1.000 → 0.867 (-0.133)

### #8 — short paragraphs with data in each | KEPT

- **File:** `.claude/commands/generate-report.md`
- **Change:** 加入段落密度規範（每段 1-2 句、80-120 字、每段含數據點、不合併多指標）
- **Diff:**
  ```diff
  + **段落密度規範**：每段限 1-2 句（約 80-120 字），段落之間用空行分隔。
  + 每段至少包含一個數據點。不要將多個指標合併在同一段落中。
  ```
- **Snapshot:** 20260306-184745
- **Report:** `reports/008_20260306-184745_keep_3b95e62.md`
- **Composite:** 0.9036 | **Delta:** +0.0321 (+3.7% from #7)
- **Commit:** 3b95e62
- **Status:** keep — data_evidence 0.271→0.671（段落從 41 增加到 101，含數據段從 19 增到 47）
- **Impact:**
  - data_evidence: 0.271 → 0.671 (+0.400)
  - section_depth: 0.710 → 0.765 (+0.055)
  - temporal_dual: 0.800 → 0.667 (-0.133)

### #9 — dual temporal frame per line | KEPT

- **File:** `.claude/commands/generate-report.md`
- **Change:** 加入雙時間框架規範（每段同時寫月趨勢和週環比，目標 ≥15 段）
- **Snapshot:** 20260305-081902
- **Report:** `reports/009_20260305-081902_keep_e3c4270.md`
- **Composite:** 0.9267 | **Delta:** +0.0231 (+2.6% from #8)
- **Commit:** e3c4270
- **Status:** keep — temporal_dual 0.667→1.0, alert_coverage 略降 1.0→0.905
- **Impact:**
  - temporal_dual: 0.667 → 1.000 (+0.333)
  - l1_overall: 1.000 → 0.981 (-0.019)
  - alert_coverage: 1.000 → 0.905 (-0.095)
  - section_depth: 0.765 → 0.599 (-0.166)
  - data_evidence: 0.671 → 0.657 (-0.014)

### #10 — cap Section 一 + expand 三四五 | discarded

- **File:** `.claude/commands/generate-report.md`
- **Change:** Section 一 限 5-6 因果區塊，三/四/五 擴充至 ≥5 段
- **Snapshot:** 20260305-172646
- **Report:** `reports/010_20260305-172646_discard_3c4ceb3.md`
- **Composite:** 0.9061 | **Delta:** -0.0206 (-2.2% from #9)
- **Status:** discard — section_depth 0.599→0.757 (+0.158) 但 cross_metric 1.0→0.733 (-0.267)
- **失敗分類:** cross_metric 衰退最多（-0.267），限制 Section 一 長度後因果連接詞密度下降

## 累計分析（Round 1-10）

- Best composite: 0.9267（+45.2% from baseline 0.6383）
- 最有效假設：data_evidence 短段落（#8, +3.7%）、action_specificity 具體動詞（#4, +9.7%）、causal_chain 結構化區塊（#2, +8.6%）
- 反復失敗面向：section_depth 嘗試 3 次（#6 discard、#7 keep、#10 discard），壓縮 Section 一 都會犧牲其他指標
- 飽和指標（11/17 = 1.0）：L1 overall, section_coverage, kb_citation, has_research, has_links, alert_coverage, maturity_labeled, action_specificity, quadrant_judgment, causal_chain, priority_balance, top_recommendation, temporal_dual
- 仍有空間：data_evidence(0.657), section_depth(0.599), cross_metric(未穩定 0.87-1.0)

### 失敗模式索引
| 模式 | 出現次數 | 實驗編號 |
|------|---------|---------|
| section_depth vs cross_metric/causal_chain trade-off | 3 | #6, #7(partial), #10 |
| data_evidence 持續低於 baseline(0.757) | 10 | #1-#10 全部 |

## 累計分析（每 10 輪更新）

_(Agent 每 10 輪實驗後在此更新小結)_
