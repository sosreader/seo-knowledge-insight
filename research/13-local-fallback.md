# Local Fallback 設計紀錄

> 補充 [06-project-architecture.md](./06-project-architecture.md) 中「L4 External Sources 與本地 fallback 實作快照」的細節。這份文件只聚焦在一件事：當 `OPENAI_API_KEY` 不存在、LLM 呼叫逾時，或 production schema 尚未追上最新 retrieval metadata 欄位時，系統如何維持可用。

---

## 1. 為什麼 local fallback 已經不是暫時 workaround

2026-03-14 之後，pipeline 需要同時支援兩種執行環境：

1. 完整雲端路徑：有 `OPENAI_API_KEY`，可用 remote embedding、merge、classification。
2. 本地 AI tool 路徑：沒有 `OPENAI_API_KEY`，但仍要能完成 Step 2/3、重建 artifact、檢查 pipeline 狀態。

因此 fallback 不再只是 error handling，而是正式支援的第二條執行路徑。

---

## 2. Step 3 的 local fallback：`utils/openai_helper.py`

`utils/openai_helper.py` 現在同時扮演兩個角色：

1. 有 key 時，包裝 OpenAI API 呼叫。
2. 沒 key 時，提供 deterministic / heuristic 的本地替代行為。

核心入口與對應替代行為：

- `_has_openai_key()`：統一判斷是否走 remote LLM。
- `_local_embed_text()`：以 token hashing 建立 256 維本地向量，並用 `expand_query_tokens()` 注入同義詞訊號。
- `_merge_answers_locally()`：用最長 answer 當 base，僅追加非重複補充段，避免 merge 後內容膨脹。
- `_classify_qa_locally()`：用 `_CATEGORY_RULES`、`_ADVANCED_MARKERS`、`_TIME_SENSITIVE_MARKERS` 做 rule-based category / difficulty / evergreen 推斷。

### 為什麼本地 embedding 是 256 維

`_LOCAL_EMBED_DIM = 256` 的目標不是逼近 OpenAI embedding 品質，而是把 local fallback 壓在可接受的計算成本內。

- 它是獨立的 hash-based 向量空間，不與 `text-embedding-3-small` 的 1536 維向量混用。
- 它的用途是讓「無 key 環境」仍能做 grouping、cache rebuild 與最低限度的相似度作業。
- 因為維度與生成方式不同，本地向量只能視為 availability path，不能拿來宣稱與 remote embedding 等價。

這條路徑的設計目標不是複製 remote LLM 品質，而是保證以下性質：

- 可以在沒有 `OPENAI_API_KEY` 的環境跑完整的 dedupe/classify。
- 產出的欄位結構與 remote 路徑相容，不讓下游 artifact 格式分叉。
- 本地 embedding 仍能支援 cache hit、重建 `.npy`、相似度分群等作業。

---

## 3. Step 3 orchestration 如何切換 fallback：`scripts/03_dedupe_classify.py`

切換點非常直接：

- `deduplicate_qas()` 與 `classify_all_qas()` 都以 `bool(os.getenv("OPENAI_API_KEY", "").strip())` 判斷是否使用 remote LLM。
- `preflight_check()` 只有在 key 存在時才把 `OPENAI_API_KEY` 納入必要 env；沒有 key 時不阻擋 Step 3 執行。
- `--rebuild-embeddings` 模式完全不要求 OpenAI，只利用既有 cache 或本地補齊 embedding。

這代表 Step 3 現在有三種可接受模式：

1. Full remote：去重、合併、分類、embedding 都可呼叫遠端模型。
2. Hybrid rebuild：artifact 已存在，只重建 embedding。
3. Full local fallback：無 key 但仍可完成 dedupe/classify 與 artifact 重建。

---

## 4. Ahrefs 長文 extraction 的 timeout fallback：`scripts/extract_ahrefs_slice_local.py`

外部文章中，Ahrefs 長文最容易觸發 extraction timeout，因此另外補了一層「逾時時退回 heuristic 結果」機制。

關鍵行為：

- CLI flag：`--heuristic-fallback-on-timeout`
- `_process_file()` 內若遇到 exception 且訊息包含「逾時」，則改呼叫 `_build_heuristic_result()`
- heuristic 結果仍寫回正常的 `*_qa.json`，避免 pipeline 因單篇 timeout 整批中斷

這個 fallback 的定位不是「保證高品質 extraction」，而是：

- 保住 batch progress
- 保留最小可檢視輸出
- 讓人工或後續流程能辨識哪些檔案是 heuristic 產物、哪些是正常模型輸出

若不是 timeout，而是其他例外，仍會寫入失敗格式：

- `qa_pairs: []`
- `meeting_summary: "處理失敗: ..."`

這樣 pipeline state 與人工檢查都能看出差異。

實際上可用這個形狀快速判斷輸出類型：

```json
{
	"qa_pairs": [],
	"meeting_summary": "處理失敗: TimeoutError(...)"
}
```

而 timeout heuristic fallback 仍會寫出正常結構的 `qa_pairs` 與一般摘要，因此 `scripts/list_pipeline_state.py` 可以用 `qa_pairs` 是否為 list，且 `meeting_summary` 是否包含 `處理失敗` 來區分可用輸出與明確失敗輸出。

---

## 5. API / production 的 fallback 不是同一類問題

本 repo 目前有兩種 fallback，不能混為一談：

1. Pipeline local fallback：處理「沒 OpenAI key 但仍要產出 artifact」
2. Production schema fallback：處理「Supabase `qa_items` 尚未套用最新 retrieval metadata 欄位」

前者主要在 Python scripts 與 `utils/openai_helper.py`；後者主要在 TypeScript API 的 `SupabaseQAStore`。

兩者共同點只有一個：都優先保可用性，而不是要求所有環境即時追上最新能力。

---

## 6. 目前邊界與限制

這套 fallback 設計刻意承認品質邊界：

- 本地 embedding 是 hash-based 近似，不等同 `text-embedding-3-small`
- 本地分類規則偏保守，目標是可預測與可重建，不是語意上最強
- heuristic extraction 只適合 timeout 緩衝，不適合當長期主要 extraction 路徑
- production 若仍停在 base schema，retrieval metadata 相關 boost 不會生效，只能維持基本搜尋能力

因此正確理解是：fallback 保證「系統不中斷」，不是保證「所有 advanced feature 等價可用」。

---

## 7. 實務判讀

當你看到以下現象時，可直接對應到 fallback 狀態：

- Step 3 在無 key 環境仍可跑完：代表 local merge/classify/embedding 正常
- Ahrefs 單篇輸出存在但內容較粗：通常是 timeout 後 heuristic fallback
- API 啟動時出現 `falling back to base schema`：代表 Supabase 尚未有 extended retrieval columns
- chat/search 可用但 ranking 不像預期精細：常見原因是 production 還在 base schema fallback

---

## 8. 結論

從 2026-03-14 起，local fallback 已成為這個專案的正式架構層，而不是測試環境特例。它的核心價值是把系統拆成：

1. 能力最佳化路徑：有 remote model、有完整 schema 時啟用 advanced feature。
2. 可用性保底路徑：缺 key、逾時、schema 落後時，仍保留最小可運作能力。

這個分層，讓 pipeline 與 API 可以在不同成熟度環境下維持一致的 artifact 介面與行為預期。