# Pipeline 操作手冊

> 從 [README.md](../README.md) 搬移的深度操作指南。快速入口請見 README。

---

## 本機執行完整 ETL

> 2026-09-15 起，排程 workflow `etl-and-deploy.yml`（ETL Pipeline + Quality Gate）已移除：全歷史 32 次 run 為 31 failure／1 cancelled，一次都沒成功過。ETL 改在本機依本節執行。`qa_items` 的時效分數仍由 CI 的 Update Freshness Scores（`update-freshness.yml`，週一 02:00 UTC）維護。
>
> 本節逐步對應原 workflow 的每個 step。每步的主指令逐字取自原 workflow 的 `run:`，env 取自原 step 的 `env:`。Makefile target 只在確認與原指令等價時列為替代寫法，不等價的會註明差異。`tests/test_eval_cli_contract.py` 會掃描本節每一個 `scripts/*.py` 呼叫與它帶的長參數，確認腳本的 argparse 真的認得，所以本節要用到的 flag 一律寫成完整指令、放在程式碼區塊裡。改指令時，測試會一起把關。

**前置**

- Python 環境：先執行 `source .venv/bin/activate`，下列指令的 `python` 都是指 venv 裡的直譯器，等同 Makefile 的 `PYTHON := .venv/bin/python`。各腳本會自動讀取 repo 根目錄的 `.env`；下列 env 只列名稱，值放在 `.env`，不要貼到終端機或文件裡。
- 先跑 `make check`：只檢查依賴，不呼叫任何 API。
- 本機會保留 `output/`（含 LLM content-addressed cache）與 `raw_data/`，所以萃取與分類是真正的增量。原 workflow 每次都從空的 `output/` 開始，等於每週全量重萃，08-31 那次光 ETL job 就跑了 4 小時 54 分。
- 步驟 6～8 會寫入 prod Supabase（`qa_items`、`eval_runs`）。

### 1. Notion 擷取（原 step：Fetch from Notion (incremental)）

- 指令（逐字取自原 workflow）：

  ```bash
  python scripts/01_fetch_notion.py
  ```

  `make fetch-notion` 帶 `--filter SEO`（`Makefile:49`），只抓標題含 "SEO" 的頁面，範圍較小，不等同原 workflow。
- env：`NOTION_TOKEN`、`NOTION_PARENT_PAGE_ID`
- 預期輸出：`增量模式：只抓新增或有更新的頁面`、`預設增量 cutoff: last_edited_time >= <日期>`，最後是 `步驟 1 完成！`；新頁面寫進 `raw_data/markdown/`。
- 失敗時：出現「環境變數未設定」時，先比對 env 名稱（見下方〈2026-07-03 Notion Multi-Source API 400 判別與 CI Secret 排查方法論〉），不要先懷疑 token 過期；Notion API 400 對照同一節的錯誤表。

### 2. 外部文章（原 step：Fetch external articles，best-effort）

- 指令（逐字取自原 workflow，抓 iThome + Google Cases）：

  ```bash
  python scripts/run_pipeline.py --step fetch-articles
  ```

  `make fetch-articles` 會抓全部 10 個來源（其中 Medium 需要 Playwright），範圍較大，不等同原 workflow。
- env：無
- 預期輸出：各來源腳本自己的擷取紀錄，沒有統一的摘要行。
- 失敗時：原 workflow 設 `continue-on-error: true`。來源網站擋爬蟲屬預期，失敗不阻斷後續步驟，核心資料迴路是 Notion。

### 3. Q&A 萃取（原 step：Extract Q&A (OpenAI)）

- 指令（逐字取自原 workflow；增量，會跳過已完成的檔案）：

  ```bash
  python scripts/02_extract_qa.py
  ```

  `make extract-qa` 與上面等價：它經 `run_pipeline.py --step extract-qa`，用同一個直譯器呼叫同一支腳本，不另加參數。想先試跑、只處理前 3 份時，用下面這行（等同 `make extract-qa-test`）：

  ```bash
  python scripts/02_extract_qa.py --limit 3
  ```
- env：
  - `OPENAI_API_KEY`：未設定時會改走本機 heuristic（`extraction_model` = `claude-code-heuristic`），品質不同，正式跑請設定。
  - `LMNR_PROJECT_API_KEY`：選填，未設定只是不送 trace。
- 預期輸出：`共 N 份待處理`（或 `所有檔案已處理完畢，無需重跑。`），最後是 `步驟 2 完成`、`本次處理: N 份`、`總計 Q&A: N 個`。
- 失敗時：
  - 出現 `錯誤: Error code: 429 ... insufficient_quota` 代表 OpenAI 額度用盡。**PR 70 合併前**，這種情況 step 仍然 exit 0 並產出 0 筆（2026-09-07、09-14 兩次都是這樣），所以要拿 `總計 Q&A` 跟上次比，不能只看 exit code。PR 70 合併後，遇到第一個 `insufficient_quota` 就會 exit 1；本次檔案全部失敗也會 exit 1。
  - 個別檔案有 `錯誤:`、其他檔案成功：失敗的那份會寫成「處理失敗」artifact，下次增量時自動重跑。

### 4. 去重＋分類（原 step：Deduplicate + Classify）

- 指令（逐字取自原 workflow）：

  ```bash
  python scripts/03_dedupe_classify.py
  ```

  `make dedupe-classify` 與上面等價：它經 `run_pipeline.py --step dedupe-classify`，不另加參數。
- env：`OPENAI_API_KEY`（embeddings 與分類）、`LMNR_PROJECT_API_KEY`（選填）
- 預期輸出：`去重後 Q&A 總數: N`、`分類統計：`；產出 `output/qa_final.json`、`output/qa_embeddings.npy`、`output/qa_embeddings_index.json`、`output/qa_embeddings_manifest.json`。
- 失敗時：
  - `ValueError: Embedding manifest requires nonempty candidates` 代表上游是 0 筆，要回頭查步驟 3，問題不在這一步。
  - `qa_embeddings.npy` 與 `qa_final.json` 對不上時，用 `make rebuild-embeddings` 修。

### 5. 上傳前檢查（原 step：Validate candidate artifacts before upload）

- 指令（逐字取自原 workflow，等同 `make migrate-supabase-dry`）：

  ```bash
  python scripts/migrate_to_supabase.py --dry-run
  ```
- env：無（dry-run 不連 Supabase）
- 預期輸出：`Prepared N rows for upsert`、`[DRY RUN] Would upsert N rows in batches of 100`。
- 失敗時：結構或向量沒對齊（例如 manifest 不符）會在這一步 raise。**N 是 0 或明顯少於上次就停下**，不要進入步驟 6。2026-09-07 那次就是 0 筆一路綠到 migrate。

### 6. 寫入 Supabase（原 job：Migrate to Supabase）

- 指令（逐字取自原 workflow，等同 `make migrate-supabase`）：

  ```bash
  python scripts/migrate_to_supabase.py
  ```

  寫入完成後，程式本身就會印 `Verification: M rows in qa_items`。要另外核對筆數，用下面這行（等同 `make migrate-supabase-verify`，原 workflow 沒有這一步）：

  ```bash
  python scripts/migrate_to_supabase.py --verify
  ```
- env：`SUPABASE_URL`、`SUPABASE_SERVICE_KEY`（**這一步會寫 prod 的 `qa_items`**）
- 預期輸出：`Migration complete: N succeeded, 0 failed (total N)`、`Verification: M rows in qa_items`；`--verify` 會印 `qa_items count in Supabase: M`。
- 失敗時：
  - `57014 statement timeout`：程式會先把該批二分後重送（最多 3 層）。仍然失敗會印 `Migration stopped: ... remaining batches were not attempted` 並 exit 1，這時改用小批次重跑。upsert 用 `resolution=merge-duplicates`，重跑不會重複插入：

    ```bash
    python scripts/migrate_to_supabase.py --batch-size 50
    ```
  - `Missing SUPABASE_URL or SUPABASE_SERVICE_KEY` 代表 env 沒設。

### 7. 資料品質 eval（原 step：Run data quality eval）

- 指令（逐字取自原 workflow）：

  ```bash
  python scripts/_eval_data_quality.py --source supabase
  ```

  只想看數字、不推 Laminar 時改用下面這行。注意它**仍然會寫 `eval_runs`**：

  ```bash
  python scripts/_eval_data_quality.py --source supabase --dry-run
  ```
- env：
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`：讀 `qa_items`
  - `SUPABASE_SERVICE_KEY`：寫 `eval_runs`
  - `LMNR_PROJECT_API_KEY`：推 Laminar（用 `--dry-run` 時不需要）
- 預期輸出：`=== Data Quality 指標（N 筆 QA）===` 與四項指標，接著是 `Saved eval_run to Supabase`。
- 失敗時：
  - `eval_runs 寫入失敗，HTTP 401` 代表用錯 key，寫入必須用 service key。
  - 只設了 `SUPABASE_URL`、沒設 service key，會判定「環境設定不完整」並 exit 1。

### 8. 檢索 eval（原 step：Run retrieval eval）

- 指令（逐字取自原 workflow）：

  ```bash
  python scripts/_eval_laminar.py --source supabase --group keyword-retrieval
  ```

  `make eval-laminar` 讀的是本機 JSON，跟這一步不一樣。
- env：`SUPABASE_URL`、`SUPABASE_ANON_KEY`、`LMNR_PROJECT_API_KEY`。PR 70 合併後另外需要 `SUPABASE_SERVICE_KEY`，用來把 hit_rate／mrr 寫進 `eval_runs`。
- 預期輸出：`Eval run 完成，請至 Laminar Dashboard 查看結果（group='keyword-retrieval'）`。PR 70 合併後，還會多出 `keyword-retrieval 指標（40 cases，top-k=5）：{...}` 與 `Saved eval_run to Supabase`。
- 失敗時：
  - `lmnr 未安裝`：重裝依賴（`make install`）。
  - `golden_retrieval.json 不存在`：確認 `eval/golden_retrieval.json` 在版控裡。

### 9. Quality Gate（原 step：Quality Gate）

- 指令（逐字取自原 workflow 的一般分支）：

  ```bash
  python scripts/quality_gate.py --source supabase
  ```

  只想看結果、不讓它 exit 1 時，用下面這行。它就是原 workflow 在 `skip_quality_gate` 為 true 時跑的指令：

  ```bash
  python scripts/quality_gate.py --source supabase --dry-run
  ```

  `make quality-gate` 預設讀本機 `output/evals/`，跟這一步不一樣。
- env：`SUPABASE_URL`、`SUPABASE_ANON_KEY`
- 預期輸出：`Quality gate PASSED — all thresholds met`
- 失敗時：**PR 70 合併前這一步一定 FAIL**，因為沒有任何程式把 `hit_rate`／`mrr` 寫進 `eval_runs`。PR 70 合併後，每一行 `QUALITY GATE FAILED:` 都會寫明是哪個指標、是缺值還是低於門檻，以及該由哪一步寫入。

### PR 70 合併後在本機跑 quality gate

只驗 gate、不重跑 ETL 時，依序執行步驟 7、8、9：

```bash
python scripts/_eval_data_quality.py --source supabase
python scripts/_eval_laminar.py --source supabase --group keyword-retrieval
python scripts/quality_gate.py --source supabase
```

- 前兩行各寫一筆 `eval_runs`（group 分別是 `data-quality`、`keyword-retrieval`），第三行只讀。
- gate 對每個 group 只取最新一筆，而且預設必須是 6 小時內寫入的。PR 70 另外提供 `--max-age-hours`（例如 48），用來回頭檢查較舊的某一次。**這個 flag 在 PR 70 合併前不存在**，所以暫時只寫在說明文字裡：放進程式碼區塊的話，本 PR 單獨合併時 contract 測試會紅。PR 70 合併後，請在上面的區塊補一行帶 `--max-age-hours 48` 的 gate 指令，讓測試納管。
- 2026-09-15 以 live 資料唯讀試算：hit_rate 1.0、mrr 0.8967、avg_confidence 0.7941、qa_count 32439，四項都過門檻；其中 avg_confidence 離門檻 0.75 只差 0.044。

---

## 步驟 4：每週 SEO 週報

### 操作流程

**一行指令搞定（最簡方式）：**

```bash
python scripts/run_pipeline.py --step generate-report
```

腳本自動從 [Google Sheets](https://docs.google.com/spreadsheets/d/1fzttLHJfl2Tnecxg0PDKsTmj0-PT5eSsYOivTI6wRdo) 下載最新資料（無需手動複製），報告儲存至 `output/report_YYYYMMDD.md`。

**資料來源優先順序：**

| 優先度 | 方式                                | 說明                              |
| ------ | ----------------------------------- | --------------------------------- |
| 1      | `--input <URL 或檔案>`              | 明確指定 URL 或本機 `.tsv` 檔     |
| 2      | `.env` 裡的 `SHEETS_URL`            | 適合換了試算表 URL 時設定         |
| 3      | `config.py` 的 `DEFAULT_SHEETS_URL` | 內建預設（目前指向 vocus 試算表） |

> **前提**：Google Sheets 須設為「任何知道連結者可檢視」（Anyone with the link - Viewer）。
> **安全性**：腳本驗證 URL 格式與主機名稱，防止注入攻擊（僅允許 `docs.google.com`），回應大小上限 10MB。

### 報告內容

| 區段                  | 說明                                                                  |
| --------------------- | --------------------------------------------------------------------- |
| **本週 SEO 狀況概覽** | 2-3 句總結本週最重要變化                                              |
| **重點指標分析**      | 核心指標（曝光/點擊/CTR/Coverage/Organic Search 等）數值與趨勢        |
| **異常值與潛在原因**  | 月趨勢超過 ±15% 或週趨勢超過 ±20% 的指標，結合 Q&A 知識庫解釋可能原因 |
| **本週行動建議**      | 2-3 條具體 Todo（附 Notion 連結指向原始會議紀錄）                     |
| **相關 SEO 知識補充** | 從 Q&A 知識庫節錄最相關的 1-2 個問答（含原始會議紀錄連結）            |

### Claude Code 模式報告生成（v3.7+）

**流程說明**：無需 OpenAI API，Claude Code 直接作為 LLM 引擎，呼叫 Python 工具函數取得指標與知識庫資料，生成 7 維度分析型週報。

**技術堆疊**：
- `fetch_from_sheets()` — Google Sheets CSV 下載（無手動複製）
- `parse_metrics_tsv()` — TSV 指標解析（月/週環比計算、異常值偵測）
- `detect_anomalies()` — 臨界值篩選（月 ±15%、週 ±20%）
- `compute_keyword_boost()` — 關鍵字加權搜尋（取代嵌入式搜尋，速度快）
- 知識庫版本：3,341+ Q&A，7 個來源集合

**報告結構**（7 維度）：

| 區段 | 內容 | 特點 |
|------|------|------|
| 一 | 本週情勢快照 | Health Score（0-100）+ 5 大現象 + 異常指標結構化分析 |
| 二 | 流量信號解讀 | 象限判定 + Discover 單獨分析 + 工作階段趨勢 |
| 三 | 技術 SEO 健康度 | Coverage 有效率 + AMP 生態 + 結構化資料 |
| 四 | 意圖與搜尋行為 | 關鍵字主題羣聚 + KW 類別趨勢 + 使用者信號 |
| 五 | 跨週對比與模式 | 連續週環比 + 月度基數 + 季度變化 |
| 六 | 行動清單 | 🔴 高優先 / 🟡 中優先 / 🟢 低優先（Notion 連結） |
| 七 | 來源 | 知識庫引用 `[N]` 標記 + `<!-- citations JSON -->` |

**驗證機制**：section 六（行動清單）的 ALERT_DOWN 覆蓋率必須與 section 一（異常指標）相符，否則報告驗證失敗。

**2026-04-10 範例**：AMP 生態系崩塌（索引警告 +364.8%、有效 -42.0%、流量 -46.3%）連鎖觸發 Google News、Mobile CWV 下滑；但 Organic Search +16.3%、Discover 週環比首度轉正 +23.2%，反映基本盤逆勢強化。

### 知識庫來源

- 優先使用 `output/qa_enriched.json`（含 Notion 連結；需執行 `make enrich`）
- 降級使用 `output/qa_final.json`（若 ≥50 筆，即步驟 3 完整跑過；無連結）
- 自動降級使用 `output/qa_all_raw.json`（670 筆，步驟 2 產出；無連結）

---

## 步驟 5：品質評估（Evaluation）

### 概述

用 LLM-as-Judge 對 Q&A 萃取品質做五維度自動評估，產出診斷報告。

### 操作方式

```bash
# 基本評估（抽樣 30 筆）
python scripts/run_pipeline.py --step evaluate-qa

# 加大抽樣
python scripts/run_pipeline.py --step evaluate-qa --sample 50

# 帶原始 Markdown 驗證 Faithfulness（更嚴格）
python scripts/run_pipeline.py --step evaluate-qa --with-source

# 含 Retrieval 品質評估
python scripts/run_pipeline.py --step evaluate-qa --eval-retrieval

# 完整評估（品質 + 分類 + Retrieval）
python scripts/run_pipeline.py --step evaluate-qa --sample 50 --with-source --eval-retrieval
```

### 評估維度（1–5 分）

| 維度             | 說明                                           |
| ---------------- | ---------------------------------------------- |
| **Relevance**    | Q&A 是否涵蓋真正有價值的 SEO 知識              |
| **Accuracy**     | A 的內容是否合理且無明顯虛構                   |
| **Completeness** | A 是否包含足夠上下文讓讀者理解                 |
| **Granularity**  | Q 的範圍是否恰當（不太粗也不太細）             |
| **Faithfulness** | （with-source 模式）A 是否忠實反映原始會議文本 |

### Retrieval 品質評估（--eval-retrieval）

| 指標                    | 說明                                           |
| ----------------------- | ---------------------------------------------- |
| **Keyword Hit Rate**    | 檢索結果的 keywords 是否覆蓋預期關鍵字         |
| **Category Hit Rate**   | 檢索結果的分類是否命中預期類別                 |
| **MRR**                 | Mean Reciprocal Rank，第一個相關結果的排名品質 |
| **LLM Top-1 Precision** | LLM 判斷排名第一的結果是否真的相關             |

### 附加檢查

- **Confidence 校準**：模型自評的 confidence 分數是否與實際品質一致
- **Self-contained**：Q 是否不需要看過原文就能理解
- **Actionable**：A 是否提供可執行的建議
- **分類準確度**：category、difficulty、evergreen 標籤是否合理

### 產出

- `output/eval_report.json` — 完整評估結果（每筆 Q&A 的詳細分數）
- `output/eval_report.md` — 人類可讀的摘要報告

---

## 成本估算

> 定價來源：OpenAI Developers Pricing（https://developers.openai.com/api/docs/pricing）

### 使用到的模型與單價（Standard tier；每 1M tokens）

- `gpt-5.2`：$1.75
- `gpt-5-mini`：$0.10（本專案用於「分類標籤」與「分類評估」，見 `utils/openai_helper.py`）
- `text-embedding-3-small`：$0.02（Embeddings；Batch 會更便宜）

> 註：Pricing 頁面的「Text tokens」是以 tokens 計價；模型的 reasoning tokens 會算在 output tokens 內並計費。

### 用你目前已匯出的資料做估算（raw backup 規模）

你目前在 `raw_data/markdown/` 有 87 份 Markdown，總字元數約 163,664。

由於 token 與語言/符號密度有關，這裡用「字元 → tokens」做區間估算：

- 粗估範圍：約 40,916 ~ 81,832 tokens（以 4 chars/token 與 2 chars/token 夾出區間）

你可以用下面指令重算（不會呼叫 API，不花錢）：

```bash
python - <<'PY'
from pathlib import Path

md_dir = Path('raw_data/markdown')
paths = sorted(md_dir.glob('*.md'))

total_chars = 0
for p in paths:
    total_chars += len(p.read_text(encoding='utf-8', errors='replace'))

min_tokens = total_chars // 4
max_tokens = total_chars // 2

print('files=', len(paths))
print('chars=', total_chars)
print('tokens_est_range=', f'{min_tokens}..{max_tokens}')
PY
```

### 依 pipeline 各步驟估算（以你目前 87 份資料）

以下是「可重算」的估算方式（讓你之後換資料量/換模型時能快速更新）。

1. **步驟 2：萃取 Q&A（`gpt-5.2`）**

- 會議內容 tokens：$T_{raw}$（上面那個 40,916~81,832）
- 每份會議的 prompt/格式化開銷：假設 $T_{overhead}=800$ tokens/份（system prompt + JSON 格式要求等）
- 輸出 tokens：高度依「每場產出幾個 Q&A」而變，保守用 $0.6\times T_{raw}$ ~ $1.5\times T_{raw}$

則：

$$
T_{step2} \approx (T_{raw} + 87\times 800) + (0.6T_{raw} \sim 1.5T_{raw})
$$

套入你目前資料量，約：

- input：約 110,516 ~ 151,432 tokens
- output：約 24,549 ~ 122,748 tokens
- 合計：約 135,065 ~ 274,180 tokens
- 成本（`gpt-5.2` $1.75/1M）：約 **$0.24 ~ $0.48**

2. **步驟 3：Embedding 去重（`text-embedding-3-small`）**

- Embedding 的 tokens 大致跟「所有 Q&A 的文字量」同級（通常接近步驟 2 的輸出規模）。
- 若粗略用 output tokens 當 proxy：成本約 **$0.0005 ~ $0.0025**（非常低）

3. **步驟 3：合併重複（`gpt-5.2`）**

- 只有在判定重複的群組才會呼叫模型，且每群組通常 1 次。
- 成本主要看「重複群組數」與「每群組帶入的 Q&A 長度」，通常會遠小於步驟 2。

4. **步驟 3：分類標籤（`gpt-5-mini`）**

- 每個 Q&A 會呼叫 1 次分類。
- 以 **600 個 Q&A、每次約 350 tokens** 估算：成本約 **$0.02**（`gpt-5-mini` $0.10/1M）

> 總結：以你目前已匯出的 87 份 Markdown，整體通常會落在 **小於 $1** 的量級；真正差異會主要來自「每場會議產出的 Q&A 數量」與「去重合併需要呼叫模型的群組數」。

---

## 運維須知

### 重要提醒

- **Raw data 永遠保留**：`raw_data/` 是你的 source of truth。就算 Q&A 萃取不理想，隨時可以重跑步驟 2、3。
- **圖片有效期**：Notion 內建圖片的 URL 是暫時的（1 小時過期），腳本會自動下載到本地 `raw_data/images/`。
- **重跑安全**：每個步驟都可以單獨重跑，不會影響其他步驟的資料。
- **SEO 時效性**：部分 Q&A 的建議可能隨演算法更新而過時，建議定期 review `evergreen: false` 的項目。

### 2026-07-03 Retry 層涵蓋原則 — Transport 層必納入（PR #50）

長跑 pipeline（Notion fetch、external API）的 retry 邏輯必須涵蓋 **transport 層錯誤**（`httpx.TransportError` 含 ReadTimeout / ConnectError / PoolTimeout），而非只有 HTTP status 層錯誤（`httpx.HTTPStatusError`）。

**背景**：CI run 28660141787 在 Notion fetch 跑 20 分鐘後被單次 `httpx.ReadTimeout` 中止，導致整個 job skipped，下游三個 verification jobs 也連鎖失敗。root cause 是 retry 邏輯只捕 `HTTPStatusError`，transport 超時漏網。

**修復方案**（已實作於 `utils/notion_client.py`；以下為簡化示意，非原始碼 — 實際實作拆 `_api_get`/`_api_post` 兩支並另有 429 rate-limit 分支）：
```python
for attempt in range(max_retries):
    try:
        return session.post(url, ...)  # or .get()
    except httpx.HTTPStatusError as e:
        # 400/403/5xx 等 HTTP status 錯誤
        if should_retry(e.status_code):
            backoff = base_backoff ** attempt
            time.sleep(backoff)
            continue
        else:
            raise
    except httpx.TransportError as e:
        # ReadTimeout, ConnectError, PoolTimeout 等 transport 層瞬時故障
        backoff = base_backoff ** attempt
        time.sleep(backoff)
        continue
```

**適用範圍**：
- ✅ 冪等操作（GET、query POST）可安全重試 transport 錯誤
- ❌ 非冪等操作（POST create、DELETE）需謹慎，應評估 idempotency key 機制
- 建議：所有外部 API 呼叫都納入 transport 層 retry 涵蓋，backoff 策略統一（1.5^attempt 或指數退避）

### 2026-04-08 對齊守則

- **區分 Notion-core 與 full-data refresh**：`make pipeline` 與 `/pipeline-local` 僅代表 Notion-core Steps 1–3；若要把 9 個外部來源一起納入，應明確執行 `make fetch-all` 後再跑 `extract-qa` / `dedupe-classify`。
- **保留歷史模型 lineage**：合併或回填 QA metadata 時，不要把既有 `extraction_model` 粗暴改寫成當前預設模型；應優先保留原值，並用 `extraction_provenance` / `legacy-unknown` 表達來源與不確定性。
- **slash command 要對齊真實 runtime contract**：`/generate-report` 現在是 `scripts/04_generate_report.py` 的操作入口；2026-05-06 PR #38 之後支援雙模式 — `OPENAI_API_KEY` 設定時走 OpenAI（rerank + LLM 摘要），未設定時 fallback 到 `claude-code-heuristic`（rerank no-op + 本地 metrics summary builder）。`/pipeline-local` 仍只涵蓋本地 Steps 1–3。當 Step 4、backfill 或 fetch contract 變動時，應一起檢查 `Makefile`、`README.md`、`CLAUDE.md`、`api/README.md` 與 `.claude/commands/`。

### 2026-05-06 dedupe-classify 規模規則 + PR #38 fallback 範圍實測

- **PR #38 fallback 涵蓋範圍比 CLAUDE.md 描述更廣**：CLAUDE.md 標註 PR #38 fallback 適用 `make extract-qa` 與 `make generate-report`，實測 `make dedupe-classify` 也走 fallback。`utils/openai_helper.py` 三個關鍵函數都有 `_has_openai_key()` 判斷 + heuristic 路徑：
  - `get_embeddings` (L521) → `get_local_embeddings()`（hash-based）
  - `merge_similar_qas` (L618) → 取最長 question + concat answers + merge keywords
  - `classify_qa` (L860) → `_classify_qa_locally()`（規則 + 關鍵字匹配）
  - 結論：整段 pipeline（fetch → extract → dedupe → classify）在無 OpenAI key 下都能跑完，fallback model 標記為 `claude-code-heuristic`。CLAUDE.md「無 OPENAI_API_KEY 時的 fallback」段應補上 dedupe-classify。

- **`/dedupe-classify` skill 不適合 4,000+ QA 規模**：當 `qa_all_raw.json` 規模超過約 2,000 筆，Claude Code sub-agent 無法在單次 context 內處理完整去重比對。實測 4,455 筆規模下，正確路徑是直接跑 `make dedupe-classify`（21 秒完成；heuristic 模式或 OpenAI 模式都可）。skill 適合的場景是首次跑或小規模驗證批（<500 筆）。

- **高合併率（>80%）是 KB 成熟度指標，非品質問題**：本次新加 95 筆 zh-TW Q&A，dedupe 後 78 筆併入既有群組（合併率 82%），僅 17 筆獨立。這代表新來源主題（GSC 教學、結構化資料、mobile-first indexing）與既有資料庫高度重疊，是 KB 已成熟的訊號。判斷準則：
  - 合併率 <30% → 來源帶來大量新主題（值得投資擴大批次）
  - 合併率 30%–70% → 部分擴增、部分覆蓋（合理）
  - 合併率 >80% → 主題已飽和，新批次主要在補強既有群組（KB 進入精煉期）

- **Heuristic difficulty 偏態（已知限制）**：`_classify_qa_locally` 的 difficulty 規則嚴重偏向「進階」（實測 98% 進階 / 2% 基礎）。若需正確分布，需有 OpenAI key 重跑 classify，或調整 heuristic 規則。Lineage 角度建議：difficulty 欄位若由 heuristic 產生應標 `extraction_model="claude-code-heuristic"`，下游搜尋若依賴 difficulty 過濾應併考慮 model 來源。

### 2026-05-07 L4 Maturity Retighten — `--reclassify-l4-only` flag（PR #42）

`scripts/03_dedupe_classify.py` 新增 `--reclassify-l4-only --execute` 子命令，**對既有 `output/qa_final.json` 中所有 L4 項目套用新雙重證據規則 + LLM gate 重跑分類**，不重做 dedupe / embedding。

**用法**：

```bash
# Dry-run（不寫檔，看 transition 分布）
python scripts/03_dedupe_classify.py --reclassify-l4-only

# 實際寫入
python scripts/03_dedupe_classify.py --reclassify-l4-only --execute

# 推 Supabase（PATCH 變動的 maturity_relevance 欄位）
python scripts/push_qa_metadata_to_supabase.py --verify   # 先看 diff
python scripts/push_qa_metadata_to_supabase.py --execute
```

**內部行為**：

1. 讀 `qa_final.json`，篩出 `maturity_relevance == "L4"` 的項目
2. 強制清掉 `maturity_relevance` 欄位讓 `_infer_maturity_relevance()` 走規則路徑
3. 規則層回 None 時 → **conservative fallback to L3**（避免 push 腳本跳過 None 留 stale L4，line 120 `if lv and lv != rv`）
4. `--execute` 時寫回原檔
5. 印 transition 分布：`{"L4->L4": N, "L4->L3": N, ...}`

**典型轉換結果**（2026-05-07 retighten 實測）：

```
L4→L4: 256（56% 維持，真正的實作型 L4）
L4→L3: 163（其中 26 來自規則 demote，137 來自 None→L3 fallback）
L4→L2: 31
L4→L1: 7
```

**搭配 LLM gate**：若 `OPENAI_API_KEY` 已設定，每筆規則層判 L4 的項目會多打一次 `gpt-5.4-nano` 做 reality check（走 `pipeline_cache` namespace `l4_judge`，重複呼叫不會重打 API）。無 key 時走純規則路徑（保留 PR #38 OpenAI-less 流程）。

**何時用此 flag**：

- 規則層調整後（拆 keyword、改 threshold、加新 strategy term）想重新評估既有 L4
- 新增 LLM gate 後想對歷史 L4 補做 reality check
- 從 git checkout 取得新版 `maturity_classifier.py` 後，不想全 pipeline 重跑只想刷新分類

**何時不該用**：

- 想動 L1/L2/L3（本 flag 只處理 L4 candidates）
- 想加分類給目前未分類（None）的 QA → 跑 `make dedupe-classify` 全流程

### 2026-07-03 Notion Multi-Source API 400 判別與 CI Secret 排查方法論

- **Multi-Source Database 觸發 400（API 版本過舊）**：Notion 的 Meeting Minutes database 現有 2 個 data sources（"Meeting Minutes" + "New data source"），成為 multi-source database；舊版 `NOTION_API_VERSION="2022-06-28"` 的 `GET /v1/databases/{id}` 對 multi-source 回 `400 validation_error: "Databases with multiple data sources are not supported in this API version."`，導致 `scripts/01_fetch_notion.py` 連 3 次重試後 traceback 崩潰（CI run 28654423476 與本地皆重現）。修法：升版至 `"2025-09-03"`；`utils/notion_client.py` 的 `list_child_pages` 改讀 db 回應的 `data_sources` 陣列，查詢由單一 `POST /v1/databases/{id}/query` 改為逐一 `POST /v1/data_sources/{data_source_id}/query`，多 source 結果以 page id 去重合併；`_list_database_pages` 更名 `_list_data_source_pages`、多 source 合併去重抽成 `_query_data_sources`；db-check 只對 400/404（物件類型不符）fallback 頁面模式，401/403/5xx 原樣拋出（code review 後收斂，避免認證錯誤被吞、誤入頁面模式二次重試模糊根因；順帶修掉原本 parent 為頁面時會直接 crash 的潛在 bug）；filter（`last_edited_time on_or_after`）與分頁 cursor 邏輯不變。新增 `tests/test_notion_multi_source.py`（9 個測試：多 source 合併去重、缺 data_sources 明確報錯、400/404 退頁面模式、401/403/500 必 re-raise、filter 形狀、分頁 cursor）。

- **驗證批掀出的第二個 bug — callout icon 可為 null**：升版後本地實跑 fetch，新會議紀錄含無 icon 的 callout block，`utils/block_to_markdown.py` 的 `content.get("icon", {})` 對「key 存在但值為 None」仍回傳 None → `AttributeError` 崩潰。修法：`content.get("icon") or {}`；新增 `tests/test_block_to_markdown_callout.py`（2 測試）。教訓：`.get(key, default)` 的 default 只擋 key 缺失、擋不了 explicit null；解析外部 API 回應的巢狀欄位用 `or {}`。

- **400 錯誤形態判別（修法不同，勿混用）**：

  | 錯誤訊息片段 | 根因 | 修法 |
  | --- | --- | --- |
  | `Databases with multiple data sources...` | API 版本過舊 | 升 `NOTION_API_VERSION` + 改走 `data_sources` 查詢 |
  | `path failed validation` | ID 格式錯 | 檢查傳入的 database/page ID 格式 |
  | `is a database, not a page` | endpoint 用錯 | 換成對應 database vs page endpoint |

- **CI「環境變數未設定」排查法：先三方比對，非先懷疑 token 過期**（PR #48）：排程 ETL（`etl-and-deploy.yml`，每週一）自 2026-03-09 起 17 次全數失敗、從未成功。根因兩層：(1) workflow 引用 `secrets.NOTION_TOKEN` 但 repo 只有 `NOTION_API_KEY`（env 為空、`pipeline_deps` 檢查 exit 1）；(2) workflow 傳 `NOTION_DATABASE_ID` 但 `scripts/01_fetch_notion.py` 讀的是 `config.NOTION_PARENT_PAGE_ID`（`config.py` 無 `DATABASE_ID` key）。排查順序：先比對 ①workflow 的 `${{ secrets.NAME }}` 引用名、②`gh secret list` 實際存在的 secret 名、③script/config 實際讀取的 env key，三者對不上即是根因；「token 過期」是最後才考慮的假設。另需注意：資料最後更新日（本地跑的日期）不等於 CI 最後成功日；判斷 CI 健康要看 `gh run list -L 30` 完整歷史，不能只看資料新鮮度。
  - 後續（2026-09-15）：`etl-and-deploy.yml` 已移除（全歷史 31 failure／1 cancelled、0 success），ETL 改在本機執行，見本文件開頭〈本機執行完整 ETL〉。

- **Secret 設定不落檔法**：以 `gh secret set` 補齊 `NOTION_TOKEN`、`NOTION_PARENT_PAGE_ID` 時，值取自本地 `.env`、先經 Notion API `/v1/users/me` 200 驗證有效，再用「python 讀值 → stdout pipe → `gh secret set` stdin」全程不 echo、不落檔的方式設定；workflow L40 改為 `NOTION_PARENT_PAGE_ID: ${{ secrets.NOTION_PARENT_PAGE_ID }}`（PR #48 squash merged）。

### 已知限制

1. **分類呼叫 API 次數 = Q&A 數量** — 沒有批次化，每筆各呼叫一次 `gpt-5-mini`。
2. **圖片只在步驟 1 下載** — 如果 Notion 上的圖片被替換，需要手動清除 `raw_data/images/` 後重跑步驟 1。
