# /dedupe-classify — 去重 + 分類（不需要 OpenAI API Key）

**你（Claude Code）就是 LLM 引擎**，對 `output/qa_all_raw.json` 執行語意去重、合併、分類，
輸出格式與 `scripts/03_dedupe_classify.py` 完全相容。

## 前置確認

先確認 `output/qa_all_raw.json` 存在：

```bash
.venv/bin/python scripts/qa_tools.py pipeline-status
```

若不存在，告知使用者先執行 `/extract-qa`。

---

## 執行步驟

### Step A：載入所有原始 Q&A

讀取 `output/qa_all_raw.json`，取出 `qa_pairs` 陣列。
告知使用者：「共 N 個 Q&A，開始去重分析」。

### Step B：語意去重（Semantic Deduplication）

不使用 embedding 向量，改用**你的語意理解能力**找出重複：

1. 讀取所有 Q&A 的 `question` 欄位
2. 逐組比較，找出語意相同或高度重疊的 Q&A（question 意思相同，即使措辭不同）
3. 將相似的 Q&A 歸為同一群組

**相似判斷標準（必須同時符合）**：

- 問題的核心 SEO 議題相同（例如同樣在問 canonical 設定）
- 答案的建議大方向一致
- 若討論的場景差異很大（如「新網站的 canonical」vs「電商的 canonical」），視為不同 Q&A

### Step C：合併重複群組

對每個找到的重複群組，合併成一個最完整的 Q&A：

**合併規則**：

1. 問題（Q）用最清晰的方式重新表述，必須自包含
2. 回答（A）整合所有版本的資訊，保留最新、最完整的建議
3. 如果不同版本有矛盾，以較新 `source_date` 為準，並標註「此建議可能隨時間演變」
4. 保留具體的數據、工具名稱、案例
5. keywords 限 3–7 個 SEO 術語

合併後的 Q&A 新增欄位：

```json
{
  "is_merged": true,
  "merge_count": 3,
  "merged_from": [{ "source_title": "...", "source_date": "2024-01-15" }]
}
```

未合併的 Q&A 加上：

```json
{
  "is_merged": false
}
```

### Step D：分類標籤

對去重後的每個 Q&A 加上以下分類標籤：

**category**（從以下 10 個選一個）：

- `索引與檢索`：Coverage、索引狀態、robots.txt、sitemap、canonical、未索引
- `連結策略`：內部連結、外部連結、Disavow、連結架構
- `搜尋表現分析`：曝光、點擊、CTR、排名變化、SERP 外觀
- `內容策略`：關鍵字佈局、主題聚合、延伸閱讀、內容經營
- `Discover與AMP`：Google Discover、AMP Article、推薦流量
- `技術SEO`：速度、Core Web Vitals、結構化資料、URL 結構、重複頁面
- `GA與數據追蹤`：GA4、事件追蹤、歸因分析、PWA 追蹤
- `平台策略`：Vocus 產品面 SEO，如自訂網域、方案頁、SEO 功能設定
- `演算法與趨勢`：Google 演算法更新、SERP 變化、AI 搜尋趨勢
- `其他`：以上皆不適用時才選

**difficulty**（選一個）：

- `基礎`：SEO 入門概念、基本操作
- `進階`：需要較深技術理解或策略規劃

**evergreen**（boolean）：

- `true`：常青知識，不太會過時（如 canonical 基本原則）
- `false`：可能隨演算法/平台更新而過時（如某特定演算法行為）

### Step E：儲存結果

輸出以下格式到 `output/qa_final.json`：

```json
{
  "version": "1.0",
  "total_count": 725,
  "original_count": 850,
  "meetings_processed": 87,
  "qa_database": [
    {
      "id": 1,
      "question": "...",
      "answer": "...",
      "keywords": ["term1", "term2"],
      "confidence": 0.9,
      "source_file": "meeting.md",
      "source_title": "SEO 會議 2024-01",
      "source_date": "2024-01-15",
      "is_merged": false,
      "category": "索引與檢索",
      "difficulty": "基礎",
      "evergreen": true
    }
  ]
}
```

`id` 從 1 開始，依序編號。

### Step F：輸出統計

完成後輸出：

- 原始 Q&A 數量
- 找到幾組重複
- 去重後 Q&A 數量
- 各 category 的數量分布

---

## 注意事項

- 去重時**寧可保留**，不確定是否重複時當作不同 Q&A 處理
- 合併時不要發明原始資料中沒有的內容
- 分類時優先選擇最具體的 category，「其他」是最後選項
