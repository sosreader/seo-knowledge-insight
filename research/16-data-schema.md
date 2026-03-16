# 資料結構（Data Schema）

> 從 [README.md](../README.md) 搬移的資料格式參考。

---

## meetings_index.json

步驟 1 產生的索引檔，記錄所有已擷取的會議紀錄。

```jsonc
[
  {
    "title": "SEO 會議_2024/05/02", // Notion 頁面標題
    "id": "052d1af9-3b5b-4de6-...", // Notion Page ID
    "created_time": "2024-05-15T01:55:00.000Z",
    "last_edited_time": "2024-09-18T01:01:00.000Z",
    "url": "https://www.notion.so/...",
    "json_file": "notion_json/SEO_會議_2024_05_02.json", // 對應的原始 JSON
    "md_file": "markdown/SEO_會議_2024_05_02.md", // 對應的 Markdown
  },
]
```

---

## qa_per_meeting/{filename}_qa.json

步驟 2 中間產物，每份會議的萃取結果。

```jsonc
{
  "qa_pairs": [
    {
      "question": "Google 如何處理 JavaScript 渲染的頁面？",
      "answer": "Google 會用 headless Chromium 做二次渲染，但...",
      "keywords": ["JavaScript SEO", "渲染", "Googlebot"],
      "confidence": 0.9, // 0-1，萃取品質信心
      "source_file": "SEO_會議_2024_05_02.md",
      "source_title": "SEO 會議_2024/05/02",
      "source_date": "2024-05-02",
    },
  ],
  "meeting_summary": "本次會議討論了 JS 渲染問題與內部連結優化策略",
}
```

---

## qa_all_raw.json

步驟 2 最終合併，所有來源的原始 Q&A。

```jsonc
{
  "total_qa_count": 342,
  "meetings_processed": 87,
  "qa_pairs": [
    /* 所有會議的 qa_pairs 合併 */
  ],
  "processing_summary": [
    {
      "file": "SEO_會議_2024_05_02.md",
      "qa_count": 5,
      "summary": "討論了 JS 渲染問題...",
    },
  ],
}
```

---

## qa_final.json

步驟 3 最終資料庫，去重後的知識庫。

```jsonc
{
  "version": "1.0",
  "total_count": 280, // 去重後的數量
  "original_count": 342, // 去重前的數量
  "meetings_processed": 87,
  "qa_database": [
    {
      "id": 1, // 唯一序號
      "question": "...",
      "answer": "...",
      "keywords": ["..."],
      "category": "技術SEO", // 主分類（見下方分類列表）
      "difficulty": "進階", // 基礎 / 進階
      "evergreen": true, // true=常青知識, false=可能過時
      "source_file": "...",
      "source_title": "...",
      "source_date": "...",
      "is_merged": false, // 是否由多筆合併而來
      "merge_count": 3, // (選填) 合併了幾筆
      "merged_from": [
        // (選填) 合併來源
        { "source_title": "...", "source_date": "..." },
      ],
    },
  ],
}
```

---

## qa_enriched.json

Enrichment 階段豐富化資料，包含同義詞與時效性。

```jsonc
{
  "qa_database": [
    {
      // 包含 qa_final.json 的所有欄位 +
      "_enrichment": {
        "synonyms": ["JavaScript rendering", "JS SEO", "..."],
        "freshness_score": 0.9076, // half_life=540d, min=0.5
        "search_hit_count": 3, // 來自 access_logs 統計
        "notion_url": "https://www.notion.so/SEO-_2024-05-02-052d1af93b5b4de688e0ac006848ed45",
      },
    },
  ],
}
```

---

## 分類標籤列表（category）

| 分類            | 說明                                              |
| --------------- | ------------------------------------------------- |
| 技術SEO         | Crawling、Indexing、Rendering、Structured Data 等 |
| 內容策略        | 內容規劃、改寫、E-E-A-T、內容行銷                 |
| 連結建設        | 外鏈、內鏈、Anchor Text 策略                      |
| 關鍵字研究      | 關鍵字挖掘、搜尋意圖、長尾策略                    |
| 網站架構        | URL 結構、導覽、分類架構、Breadcrumb              |
| Core Web Vitals | LCP、FID/INP、CLS、效能優化                       |
| 本地SEO         | Google 商家、NAP、在地搜尋                        |
| 電商SEO         | 商品頁、分類頁、結構化資料（Product）             |
| GA/GSC 數據分析 | Google Analytics、Search Console 數據解讀         |
| SEO 工具        | Ahrefs、Screaming Frog 等工具使用                 |
| 演算法更新      | Google 演算法更新、應對策略                       |
| 其他            | 無法歸類的項目                                    |
