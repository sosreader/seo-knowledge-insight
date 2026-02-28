# 計畫：資料庫遷移策略（File-first → PostgreSQL + pgvector）

> 日期：2026-02-28
> 狀態：v2 — 改寫為非後端背景讀者版
> 前置計畫：[modular-pipeline-with-dep-checks.md](./modular-pipeline-with-dep-checks.md)、[claude-code-llm-engine.md](./claude-code-llm-engine.md)

---

## 一、先理解這份文件在解決什麼問題

你問的問題是：

> 「`output/*` 這些檔案，是不是未來資料庫要存放的東西？現在的設計會不會讓未來改資料庫很麻煩？」

**簡短回答：**

1. `output/*` 確實就是未來資料庫的前身，大部分可以直接遷移過去
2. **只有一個地方現在沒改、未來改就很痛**：Q&A 的 ID 設計
3. 其他都不需要提前動，等真的需要加資料庫時再說

---

## 一的延伸：`output/*` 對應到未來哪張資料表

### 什麼是「資料表」？

資料庫就是一堆「表格」的集合，每個表格放一種資料。
就好比 Excel 裡面有很多個 sheet，每個 sheet 是一張表。

### 對應關係

| 現在的檔案                     | 未來的資料表                   |       現在需要改嗎？        |
| ------------------------------ | ------------------------------ | :-------------------------: |
| `output/qa_final.json`         | `qa_items` 表                  | ⚠️ 需加一個欄位（見第三節） |
| `output/qa_embeddings.npy`     | `qa_items` 表裡的向量欄位      | ✅ 不用動，遷移時一起帶過去 |
| `raw_data/meetings_index.json` | `meetings` 表                  |        ✅ 完全不用動        |
| `output/eval_history.jsonl`    | `eval_runs` 表                 |          ✅ 不用動          |
| `output/eval_reports/*.json`   | `eval_reports` 表              |          ✅ 不用動          |
| `output/fetch_logs/*.jsonl`    | `fetch_events` 表（操作紀錄）  |          ✅ 不用動          |
| `output/access_logs/*.jsonl`   | `access_events` 表（查詢紀錄） |          ✅ 不用動          |
| `output/qa_per_meeting/*.json` | **不需要存入資料庫**           |             N/A             |

> **`qa_per_meeting/` 為什麼不遷移？**
> 這些是 pipeline 的「中間產物」，就像做菜的備料。
> 最終的成品是 `qa_final.json`，備料本身不需要存進資料庫。

---

## 二、唯一真正的問題：Q&A 的「身份證號碼」設計

### 2.1 背景：什麼是 ID？

每筆資料都需要一個獨一無二的識別碼（ID），才能被精準引用。
就像每個人有身份證字號，每個 Q&A 也要有自己的 ID。

### 2.2 目前的做法有什麼問題？

目前每筆 Q&A 的 `id` 欄位是流水號（`1, 2, 3, 4...`）：

```jsonc
// qa_final.json 目前長這樣
{ "id": 1, "question": "Google如何..."}
{ "id": 2, "question": "AMP頁面..."}
{ "id": 3, "question": "Core Web Vitals..."}
```

**問題：每次重跑 Step 3（去重 + 分類），這些號碼會重新分配。**

舉個具體例子：

```
第一次執行 Step 3 後：
  id=42  →  「如何設定 canonical 標籤？」
  id=43  →  「Discover 流量掉了怎麼辦？」

新增一場會議後，重跑 Step 3（去重排序改變了）：
  id=42  →  「Discover 流量掉了怎麼辦？」  ← id 42 換人了！
  id=43  →  「Core Web Vitals 怎麼優化？」
  id=44  →  「如何設定 canonical 標籤？」  ← 原本的 42 變成 44
```

**這會造成什麼後果？**

| 場景                                    | 影響                                   |
| --------------------------------------- | -------------------------------------- |
| vocus-web-ui 存了 `/qa/42` 的書籤或連結 | 重跑後指向不同資料，使用者看到錯誤內容 |
| eval 的 golden set 引用了 `id=42`       | 評估結果對應到錯誤的 Q&A，數字失去意義 |
| 對外分享的 Q&A 連結                     | 重跑後全部失效                         |

這就叫做 **破壞性 API 變更**（Breaking Change）：API 的網址格式沒變，但同一個網址返回不同內容，使用者被誤導卻無從察覺。

### 2.3 正確的做法：`stable_id`（內容哈希值）

**核心原則：ID 應該根據「內容」決定，而不是根據「順序」決定。**

相同的來源檔案 + 相同的問題文字 → 永遠產生相同的 ID，不管重跑幾次、資料庫換幾次。

```
stable_id 的計算方式：
  輸入：來源檔案名 + 問題文字的前 120 個字
  算法：SHA-256（一種數學函數，確保相同輸入絕對得到相同輸出）
  結果：取前 16 個字元作為 ID

舉例：
  "2024-05-02_SEO會議.md" + "如何設定canonical標籤？"
  → sha256(...) → "a3f7c891b2d04e56"
```

**效果對比：**

```
重跑 Step 3 前後的 ID 比較：

  文章 ID（流水號，目前）：
    重跑前  id=42  → 「如何設定 canonical？」
    重跑後  id=44  → 「如何設定 canonical？」  ← 變了！書籤壞了

  stable_id（改後）：
    重跑前  stable_id="a3f7c891"  → 「如何設定 canonical？」
    重跑後  stable_id="a3f7c891"  → 「如何設定 canonical？」  ← 永遠不變！
```

### 2.4 這件事為什麼要現在做，不能等之後？

```
現在改的代價：
  Step 3 加 4 行程式 (~2h)
  API route 加判斷 (~30min)
  store.py 加欄位 (~30min)
  ─────────────────────────
  合計 ~3 小時

上線後才改的代價：
  必須發一個 Breaking Change API 版本（/api/v2/qa/{stable_id}）
  前端 vocus-web-ui 全部改連結
  通知所有使用舊連結的人重新存書籤
  eval golden set 全部重建
  ─────────────────────────
  合計 > 1 天 + 使用者困擾
```

一旦 vocus-web-ui 上線並有外部連結引用 `/qa/{id}`，這個 API 就不能改了（改了就是破壞性變更）。

---

## 三、具體修改方式（三件事，合計 ~3 小時）

### 事項一：Step 3 計算並寫入 `stable_id`

**在哪裡改：** `scripts/03_dedupe_classify.py`

**改什麼：**

```python
import hashlib

def compute_stable_id(source_file: str, question: str) -> str:
    """根據內容算出永久不變的 ID"""
    content = f"{source_file}::{question[:120]}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]

# 寫入 qa_final.json 時，多加這一行
qa_item["stable_id"] = compute_stable_id(qa["source_file"], qa["question"])
```

**`qa_final.json` 改後長這樣：**

```jsonc
{
  "id": 1,                           // ← 保留，舊程式不影響
  "stable_id": "a3f7c891b2d04e56",   // ← 新增，這是未來的主鍵
  "question": "...",
  ...
}
```

**同時要建立的對應表：** `output/qa_embeddings_index.json`

```jsonc
// 記錄每個 stable_id 對應到 .npy 檔案的哪一行
{
  "a3f7c891b2d04e56": 0,
  "b4e8d902c3e15f67": 1,
  ...
}
```

這個對應表的用途：向量（embedding）存在 `.npy` 的第幾行，沒有名字，只有位置。
加了這個 index，才能用 `stable_id` 找到對應的向量，而不是靠「我是第幾筆」（位置會跑掉）。

**效果：** 重跑 Step 3 之後，`stable_id` 保持不變，向量對應不會跑掉。

---

### 事項二：API 支援 `stable_id` 查詢路徑

**在哪裡改：** `app/routers/qa.py`

**改什麼：** 同一個 endpoint 自動判斷傳入的是數字還是 stable_id：

```python
@router.get("/qa/{qa_id}")
async def get_qa(qa_id: str):
    if qa_id.isdigit():
        # 舊連結 /qa/42 → 還是能用（向下相容）
        item = store.get_by_display_id(int(qa_id))
    else:
        # 新連結 /qa/a3f7c891 → 永久有效
        item = store.get_by_stable_id(qa_id)
    ...
```

**使用效果：**

```
GET /api/v1/qa/42            → 舊連結，繼續有效（不讓已存在的書籤壞掉）
GET /api/v1/qa/a3f7c891      → 新連結，永久有效（推薦前端改用這個）
```

**效果：** 不破壞任何現有呼叫，同時給前端一個可以安心長期儲存的 ID。

---

### 事項三：所有 API 回傳都包含 `stable_id`

**在哪裡改：** `app/core/store.py` 的 Pydantic model

**改什麼：** 每筆 Q&A 的回傳格式加一個 `stable_id` 欄位：

```python
class QAItem(BaseModel):
    id: int             # 舊欄位，保留
    stable_id: str      # 新增
    question: str
    answer: str
    ...
```

**效果：** 前端搜尋時拿到的每筆 Q&A 都帶有 `stable_id`，可以用來做書籤、分享連結、存入收藏。

---

## 四、其他技術決策：為什麼現在不需要動

### 4.1 「source 欄位重複存」— 為什麼不整理成只存一份？

> 常見問題：
>
> - 正規化有沒有做的差別是什麼？
> - 為什麼感覺變複雜卻沒好處？

下面這一節就是為了回答這兩個問題。

**什麼叫重複存？**

目前每筆 Q&A 都各自存了來源會議的資訊：

```jsonc
// 同一場會議的 8 筆 Q&A，source_title 存了 8 次
{"source_title": "SEO 會議 2024/05/02", "question": "...第 1 題..."}
{"source_title": "SEO 會議 2024/05/02", "question": "...第 2 題..."}
// ...
{"source_title": "SEO 會議 2024/05/02", "question": "...第 8 題..."}
```

**「不重複存」的做法（資料庫術語叫正規化）：**

```
meetings 表：id=5, title="SEO 會議 2024/05/02"

qa_items 表：
  meeting_id=5, question="...第 1 題..."  ← 只存數字 5，不存標題
  meeting_id=5, question="...第 2 題..."
```

**為什麼不需要現在做正規化？**

想把 Q&A 顯示出來，需要同時知道問題和來源會議名稱。

| 方法           | 讀取 Q&A 時的動作                            | 速度       |
| -------------- | -------------------------------------------- | ---------- |
| 重複存（現況） | 直接讀，一次取完                             | ⚡ 最快    |
| 正規化         | 先讀 Q&A，再去 meetings 表查標題，組合在一起 | 多一個步驟 |

703 筆 Q&A，87 場會議，「重複存」帶來的浪費幾乎是零（不到 50KB）。
API 讀這份資料的頻率遠高於修改，重複存反而是更好的選擇。

**何時才需要正規化：** 你需要「改一場會議的標題，所有 8 筆 Q&A 自動跟著改」時。
目前會議標題不會改，所以正規化只是增加複雜度，沒有實際好處。

**正規化 vs. 不正規化：直接比較**

| 角色                | 正規化（只存一份）                    | 不正規化（現在這樣）    |
| ------------------- | ------------------------------------- | ----------------------- |
| 想改一場會議的標題  | 改一個地方，8 筆 Q&A 自動更新         | 要改 8 個地方，很容易漏 |
| 查詢一筆 Q&A 的來源 | 要先查 qa_items，再去 meetings 查標題 | 直接拿到，一步完成      |
| 程式複雜度          | 高（需要 JOIN、維護關聯）             | 低（直接讀 JSON）       |
| 儲存空間            | 省一點點                              | 多存幾個文字，幾乎無感  |

**為什麼你的狀況不值得做**

正規化解決的問題是：**同一份資料被存在很多地方，改一個地方另一個沒跟著改，導致不一致。**

但這個問題在你的案例**不存在**：

- **會議標題不會改** — Notion 上的會議紀錄標題是固定的，通常只會新增不會修改。
- **read-only 資料** — pipeline 只會寫入，API 只會讀取，沒有「修改會議標題」的功能。
- **703 筆的重複量極小** — 重複存 87 個標題帶來的儲存浪費不到 50 KB。

正規化在這裡只帶來「要寫 JOIN」的複雜度，卻沒有解決任何實際存在的問題。

**何時才需要正規化（再次強調）：**
當你真的開始有「修改會議標題 → 希望自動反映所有相關 Q&A」的需求時，再做也不晚。

---

### 4.2 `qa_embeddings.npy`（向量檔）— 為什麼不換成 pgvector？

**背景：** 語意搜尋（「找跟這個問題意思最接近的 Q&A」）需要用向量做計算。
目前向量存在 `qa_embeddings.npy`，是一個純數字矩陣（703 行 × 1536 列）。

**pgvector 是什麼：** PostgreSQL 資料庫的外掛，讓資料庫也能存向量並做搜尋。
把向量從 `.npy` 的「獨立檔案」搬進資料庫的「欄位」。

**需要換嗎？對照表：**

| 知識庫規模     | `.npy` 搜尋延遲 | 實際感受           | 建議        |
| -------------- | --------------- | ------------------ | ----------- |
| 703 筆（現況） | < 2ms           | 使用者完全感覺不到 | ✅ 不需要換 |
| 5,000 筆       | ~15ms           | 稍微有感           | 考慮換      |
| 100,000 筆     | ~300ms          | 明顯慢             | 必須換      |

**不換的原因：**

- pgvector 需要架設 PostgreSQL、管理資料庫連線、寫向量同步邏輯——這些都是額外的工程工作
- 703 筆的搜尋速度已經是「幾乎瞬間」，花幾天架 pgvector 完全不划算
- 等真的需要時，`stable_id` index 建好了，遷移只是一個 INSERT 指令

---

### 4.3 JSONL 日誌檔案— 為什麼不立刻存進資料庫？

**JSONL 長什麼樣子：** 每行是一個完整的 JSON 事件，就是文字版的資料庫 row。

```jsonc
// output/access_logs/access_2026-02-28.jsonl
{"query": "canonical 設定", "returned_ids": ["a3f7c891", "b4e8d902"], "at": "2026-02-28T10:30:00Z"}
{"query": "Core Web Vitals", "returned_ids": ["c5f1e003"], "at": "2026-02-28T10:31:00Z"}
```

目前用 `python scripts/audit_trail.py access` 可以直接查這些日誌，完全夠用。

**什麼時候才需要搬進資料庫：** 你需要跨天、跨週的聚合問題，例如：

```sql
-- 「上個月最常被搜尋的關鍵字是哪十個？」
SELECT query, COUNT(*) FROM access_events
WHERE occurred_at >= '2026-01-01'
GROUP BY query ORDER BY count DESC LIMIT 10;
```

目前需求還沒到這裡，搬進去只是增加維護負擔。

**不會造成未來重工的原因：** JSONL 每行的欄位幾乎就是資料庫 row 的結構，
遷移時只需要四行指令，不存在「設計不對，需要大幅改寫」的問題。

---

### 4.4 `merged_from` 欄位— 為什麼不建獨立的關聯表？

**背景：** Step 3 會把多場會議重複討論的問題合併成一筆 Q&A，
並記錄「這筆是從哪幾筆合併來的」：

```jsonc
{
  "question": "canonical 標籤的最佳實踐...",
  "is_merged": true,
  "merged_from": [
    { "source_title": "SEO 2023-05-03" },
    { "source_title": "SEO 2023-10-04" },
  ],
}
```

**「建獨立表格」是更規範的做法（正規化）：**

```
qa_merged_sources 表：
  qa_stable_id="a3f7c891" | source_title="SEO 2023-05-03"
  qa_stable_id="a3f7c891" | source_title="SEO 2023-10-04"
```

**為什麼不需要現在做：** 目前整個 703 筆資料庫只有 **1 筆** `is_merged=true`。
專門建一張表管理 1 row 的資料，是過度工程。等 merged Q&A 超過 100 筆再說。

遷移時，`merged_from` 這個 JSON 陣列直接存成資料庫的 `JSONB` 欄位，
PostgreSQL 支援直接查詢 JSONB 的內容，不需要建關聯表也能找到「哪些 Q&A 合併自某場會議」。

---

## 五、不需要提前做的完整清單（避免過度工程）

> **原則：** 不要為了「也許有一天會用到」而增加現在的複雜度。
> 等到有具體的問題或瓶頸，再加也不遲。

| 提案                          | 什麼時候才需要                       | 現在的狀況             |
| ----------------------------- | ------------------------------------ | ---------------------- |
| 架設 PostgreSQL + pgvector    | QA 筆數 > 5,000，或每日查詢 > 500 次 | 703 筆，每日查詢個位數 |
| `source` 欄位正規化           | 需要同步改會議標題到所有 Q&A         | 目前標題固定不改       |
| `merged_from` 獨立成關聯表    | merged Q&A > 100 筆                  | 目前 1 筆              |
| Redis 快取                    | 每日請求 > 1,000，或搜尋明顯變慢     | 目前流量極低           |
| Alembic（資料庫版本管理工具） | 有 PostgreSQL 才需要                 | 還沒有 DB              |
| JSONL 日誌遷移進 DB 表        | 需要跨週/月聚合查詢                  | 目前用腳本查詢夠用     |

---

## 六、未來資料庫的完整 Schema（備查）

等真的要上資料庫時，設計應該長這樣：

### 主要表：`qa_items`（來自 `qa_final.json`）

| 欄位名稱       | 資料型別       | 說明                                 | 現在的對應欄位           |
| -------------- | -------------- | ------------------------------------ | ------------------------ |
| `stable_id`    | `CHAR(16)`     | 主鍵，永久不變                       | **新增**（事項一）       |
| `display_id`   | `INTEGER`      | 顯示用流水號，向下相容               | 現有 `id`                |
| `question`     | `TEXT`         | 問題                                 | 現有                     |
| `answer`       | `TEXT`         | 答案                                 | 現有                     |
| `keywords`     | `TEXT[]`       | 關鍵字陣列                           | 現有                     |
| `confidence`   | `REAL`         | 萃取信心值 0–1                       | 現有                     |
| `category`     | `TEXT`         | 分類（技術SEO 等）                   | 現有                     |
| `difficulty`   | `TEXT`         | 基礎 / 進階                          | 現有                     |
| `evergreen`    | `BOOLEAN`      | 是否為長青知識                       | 現有                     |
| `is_merged`    | `BOOLEAN`      | 是否由多筆合併                       | 現有                     |
| `merged_from`  | `JSONB`        | 合併來源（JSON 格式）                | 現有                     |
| `source_file`  | `TEXT`         | 來源 Markdown 檔名                   | 現有                     |
| `source_title` | `TEXT`         | 來源會議標題（非正規化，故意重複存） | 現有                     |
| `source_date`  | `DATE`         | 會議日期                             | 現有                     |
| `embedding`    | `vector(1536)` | 語意向量，用 pgvector 存             | 來自 `qa_embeddings.npy` |
| `created_at`   | `TIMESTAMPTZ`  | 建立時間                             | 遷移時產生               |

> 95% 的欄位是現有 JSON 欄位的直接對應。
> `stable_id` 是現在就要加的，`embedding` 是遷移時從 `.npy` 帶入的。

### 參考表：`meetings`（來自 `meetings_index.json`）

| 欄位名稱           | 說明                                           |
| ------------------ | ---------------------------------------------- |
| `id`               | Notion Page UUID（已是 UUID 格式，直接當主鍵） |
| `title`            | 會議標題                                       |
| `last_edited_time` | 增量更新用                                     |
| `notion_url`       | Notion 頁面連結                                |
| `md_file`          | 本機 Markdown 路徑                             |

> Notion 的 page id 已經是 UUID（`052d1af9-3b5b-4de6-88e0-ac006848ed45`），
> 直接作為資料庫主鍵，不需要另外設計。

---

## 七、遷移時的工作量估算

等到真的需要上資料庫時，工作量不大——因為現在做的 `stable_id` 把最難的部分解決了：

```
Step 1  建立 PostgreSQL + 執行 CREATE TABLE                  (~1 小時)
Step 2  匯入 qa_final.json → qa_items 表                     (~2 小時)
          （用 stable_id 當主鍵，不需要任何轉換）
Step 3  從 qa_embeddings.npy + index.json 補入 embedding 欄位 (~1 小時)
Step 4  修改 app/core/store.py：從讀 JSON 改成查資料庫        (~4 小時)
Step 5  測試 + 驗證                                           (~2 小時)
────────────────────────────────────────────────────────────
合計    ~10 小時
```

**為什麼這麼快？**

`store.py` 已經做了 Repository 抽象：外面的 API 只呼叫 `store.search()`、`store.get_by_id()`，
不管儲存層是 JSON 還是 PostgreSQL，API 程式碼完全不用動，只需要改 `store.py` 的內部實作。

這就是 [Repository Pattern](https://www.martinfowler.com/eaaCatalog/repository.html) 的設計效益。

---

## 八、計畫的優先順序

```
modular-pipeline-with-dep-checks.md（先做）
  └─ config.py lazy loading
       └─ 解除 import config 副作用，讓 Step 3 加入 stable_id 不影響 Step 1

claude-code-llm-engine.md Step 0（緊接著）
  └─ [Step 0.2] stable_id 寫入 qa_final.json       ← ★ 本計畫事項一
  └─ [Step 0.1] merged_from 補 source_file
  └─ [Step 0.3] qa_embeddings_index.json 建立

本計畫事項二 + 三（stable_id 完成後立刻）
  └─ API GET /qa/{stable_id} endpoint               ← ★ 本計畫事項二
  └─ store.py + response model 加入 stable_id 欄位  ← ★ 本計畫事項三

vocus-web-ui 前端開始用 stable_id 引用 Q&A

... 未來某天，知識庫夠大或有並發需求 ...

PLAN_SEO_INSIGHT.md Phase 1 後段
  → PostgreSQL + pgvector 遷移（~10 小時，上面規劃的那些）
```

---

## 九、研究佐證

| 技術決策                                   | 參考來源                                                                                                                                                                          | 本計畫應用                                        |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| 用內容哈希而非流水號作為 API ID            | [Stripe ID 設計原則](https://docs.stripe.com/ids)、[GitHub 全局 Node ID](https://github.blog/2020-05-06-using-global-node-ids/)                                                   | `stable_id = sha256(source_file + question)[:16]` |
| 讀多寫少適合非正規化（重複存）             | [PostgreSQL 效能建議](https://www.postgresql.org/docs/current/performance-tips.html)、[NoSQL Distilled — Fowler](https://martinfowler.com/books/nosql.html)                       | `source_title` 重複存避免 JOIN，703 筆不浪費      |
| 小規模向量搜尋 numpy 足夠                  | [pgvector Benchmark](https://github.com/pgvector/pgvector#performance)、[Anyscale 向量 DB 選型](https://www.anyscale.com/blog/the-engineers-guide-to-production-vector-databases) | 703 筆 < 2ms，< 5,000 筆前不換                    |
| YAGNI：不做現在不需要的事                  | [Martin Fowler — Yagni](https://www.martinfowler.com/bliki/Yagni.html)                                                                                                            | 不提前架 PostgreSQL、Redis、Alembic               |
| Append-only JSONL 即 event log，可直接遷移 | [Designing Data-Intensive Applications — Kleppmann Ch.11](https://www.oreilly.com/library/view/designing-data-intensive-applications/9781491903063/)                              | JSONL 欄位結構幾乎就是 DB row                     |
| Repository Pattern 讓儲存層可替換          | [Repository Pattern — Fowler](https://www.martinfowler.com/eaaCatalog/repository.html)                                                                                            | `store.py` 換 DB 只改內部實作，API 不動           |
