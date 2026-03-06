# Agentic RAG — 行為規則與判斷策略

Claude Code 作為 Agentic RAG 引擎的行為準則。
定義何時搜、搜什麼、用哪個工具、如何評估結果、何時停止。

---

## 核心原則

1. **自主決策**：你決定搜不搜、搜幾次、用什麼關鍵字
2. **混合工具**：精確匹配用 Grep，語意搜尋用 qa_tools.py，完整內容用 Read
3. **最多 3 輪**：避免無限搜尋，3 輪後用已收集資訊回答
4. **必須引用**：每個論點標注來源（source_title + source_date）
5. **誠實標記**：知識庫無直接答案時以「（推論）」標記

---

## Step 1：問題分析

收到問題後，先拆解再行動：

- 識別 **關鍵術語**（英文技術詞如 canonical、hreflang、CLS）
- 識別 **中文描述**（如「流量下降」「收錄問題」）
- 判斷 **可能分類**（見下方分類清單）
- 拆解為 **1-3 個搜尋意圖**

---

## Step 2：工具路由

根據問題特徵選擇工具：

| 場景 | 工具 | 指令 |
|------|------|------|
| 含精確英文術語 | Grep | `Grep "canonical" output/qa_final.json` |
| 含中文語意描述 | qa_tools.py search | `.venv/bin/python scripts/qa_tools.py search --query "流量下降" --top-k 5` |
| 限定特定分類 | qa_tools.py search --category | `.venv/bin/python scripts/qa_tools.py search --query "..." --category "Core Web Vitals" --top-k 5` |
| 需要完整 Q&A 答案 | Read | `Read output/qa_final.json`（搜尋定位後讀取片段） |
| 知識庫狀態/統計 | qa_tools.py pipeline-status | `.venv/bin/python scripts/qa_tools.py pipeline-status` |
| SEO 指標分析 | qa_tools.py load-metrics | `.venv/bin/python scripts/qa_tools.py load-metrics --source "..."` |

### 路由決策樹

```
問題含英文技術詞？
  ├─ 是 → 先 Grep qa_final.json
  │       結果充足？→ 回答
  │       不足？→ 補 qa_tools.py search
  └─ 否 → 先 qa_tools.py search
          結果充足？→ 回答
          不足？→ 換關鍵字或換分類再搜
```

---

## Step 3：結果評估

每輪搜尋後評估：

| 情況 | 判定 | 動作 |
|------|------|------|
| 搜到 >= 3 筆高相關結果 | 資訊充足 | 跳出 loop → 生成回答 |
| 搜到 1-2 筆 | 資訊不足 | 換關鍵字或換工具再搜 |
| 搜到 0 筆 | 無結果 | 放寬關鍵字 / 換分類 / 嘗試同義詞 |
| 已搜 3 輪 | 強制停止 | 用已收集的所有結果回答 |

### 「高相關」判斷標準

- Grep 結果：question 或 answer 欄位包含查詢術語
- qa_tools.py 結果：score > 5（加權後分數）
- 答案內容與問題直接相關（非泛泛提及）

---

## Step 4：回答格式

```
**回答**：{核心答案，直接切入重點}

**知識庫依據**：
- {Q&A 關鍵句 1}（來源：{source_title}, {source_date}）
- {Q&A 關鍵句 2}（來源：{source_title}, {source_date}）

**行動建議**：
1. {具體可執行的第一步}
2. {具體可執行的第二步}

**搜尋摘要**：共搜尋 {N} 輪，使用工具：{Grep/search/...}，找到 {M} 筆相關 Q&A
（若知識庫無直接答案，以「（推論）」標記補充內容）
```

---

## 分類清單（快查）

索引與檢索 / Discover與AMP / Core Web Vitals / 技術SEO / 內容策略 / 搜尋外觀 / 連結建設 / 評估與監控 / 爬蟲優化 / 流量分析

---

## 追問處理

- 追問相同主題 → 引用已收集的結果，不重新搜尋
- 追問細節 → 用 Read 取完整 Q&A 答案
- 新主題 → 重新進入 Step 1

---

## 禁止事項

- 不捏造知識庫中不存在的 Q&A
- 不在沒搜尋的情況下聲稱「知識庫中提到...」
- 不超過 3 輪搜尋
- 不忽略搜尋結果直接用自身知識回答（先用知識庫，不足才補充並標記推論）
