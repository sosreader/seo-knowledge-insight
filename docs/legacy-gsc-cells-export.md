# 舊爬蟲 20 格等價匯出

> `scripts/export_legacy_gsc_cells.py`——用 GSC Search Analytics API 直接產出與
> 舊爬蟲 `seo-automation` 讀 GSC 網頁介面卡片**完全相同**的 20 個「總點擊次數」
> （G20~G34 共 15 格、G38~G42 共 5 格）。只讀 API，**不寫 Supabase**，與
> `ingest_gsc_search_analytics.py` 的抽樣寫入管線是平行的兩條路，互不影響。

---

## 用途

外部顧問拿到的是舊爬蟲那份「20 格」報表口徑，不是本 repo 倉儲的抽樣表口徑
（見下方「與倉儲抽樣表的差異」）。這支腳本讓我們不必真的重跑舊爬蟲、也不必
手動開瀏覽器讀 20 次 GSC 介面卡片，就能拿到同一份數字，也用來驗證 API 抽樣值
與網頁介面卡片值是否等價。

---

## 這 20 格是什麼

事實來源是 `seo-automation/config.mjs` 的 `SEARCH_PERFORMANCE`，本腳本每次執行
都重新解析該檔案（不寫死一份副本），格式改了會直接拋錯，不會悄悄用舊值跑。

| 分組 | 格號 | 筆數 | 內容 |
|---|---|---|---|
| queryPage | G20~G26 | 7 | 依 URL pattern 過濾（`type: "page"`），例如首頁、`/article/` |
| queryPage | G27~G34 | 8 | 依關鍵字 pattern 過濾（`type: "query"`），例如「影評」「保養」 |
| multiType | G38~G42 | 5 | 圖片／影片／新聞／探索／Google News 五個 surface 的整體總點擊（無 pattern） |

對應到 Search Analytics API：

- queryPage：`type: "web"` + `dimensionFilterGroups=[{filters:[{dimension:
  "page"|"query", operator:"includingRegex", expression:<pattern>}]}]`，不帶
  `dimensions`（不分組 = 該規則運算式命中範圍內的聚合值，等同介面卡片）。
- multiType：`type` 分別是 `image`/`video`/`news`/`discover`/`googleNews`，不帶
  filter、不帶 `dimensions`——是該 surface 在整個 property 上的總點擊。
  `discover`／`googleNews` 是 Search Analytics API 為探索／Google News 這兩個
  介面頁面保留的 `type` 值，不是走不同的 endpoint。

---

## 用法

```bash
source .venv/bin/activate

# dry-run（預設）：不需要 GSC_READONLY_KEY，只印出 20 個計畫中的請求，
# 用來確認 config.mjs 解析對不對、視窗算得對不對
python scripts/export_legacy_gsc_cells.py --start 2026-08-26 --end 2026-09-01

# 實際打 API 並寫出 JSON/CSV（需要 .env 或環境變數有 GSC_READONLY_KEY）
python scripts/export_legacy_gsc_cells.py --start 2026-08-26 --end 2026-09-01 --execute

# 用 --days/--end-offset 推算視窗，而不是明給 --start/--end
python scripts/export_legacy_gsc_cells.py --execute

# 額外對「保養」多打一次 operator=equals 當對照組（判讀關鍵字口徑用，見下方）
python scripts/export_legacy_gsc_cells.py --start 2026-08-26 --end 2026-09-01 \
  --execute --equals-control 保養

# config.mjs 不在預設的手足目錄位置時
python scripts/export_legacy_gsc_cells.py --config /path/to/seo-automation/config.mjs --execute
```

輸出（`--execute` 才會寫檔）：

- stdout：20 行 `G20 首頁 8592` 形式。
- `output/legacy-cells/<end>.json`：含 `start`／`end`／`cells`（20 筆）／`controls`
  （`--equals-control` 才有內容）。
- `output/legacy-cells/<end>.csv`：只有 20 筆主體，欄位為 cell/label/kind/
  search_type/dimension/pattern/operator/start/end/clicks。`controls` 不進 CSV，
  只在 JSON 裡（它不是 20 格的一部分，是額外的口徑對照）。

---

## 視窗規則

舊爬蟲的視窗是「跑批當下往前 7 天」，沒有寫死的資料延遲天數（`num_of_days=7`
是 GSC 介面參數，介面自己處理延遲）。本腳本用 `--days`（預設 7）與
`--end-offset`（預設 3，「視窗終點 = 執行日 - N 天」）推算，或用 `--start`/
`--end`（兩者需同時給）整組覆寫。

預設值反推自一個已知例：舊爬蟲 09-04 18:20（台北時間）跑的批次，經五個
surface 三角反推視窗是 **2026-08-26~2026-09-01**（7 天、end-offset=3）。這只是
「目前唯一已驗證過的一組參數」，不是舊爬蟲程式碼裡有一個叫 end-offset=3 的常數
——換一批次時間點反推出來的 offset 可能不同，需要時用 `--start`/`--end` 明給，
不要照抄這組預設值套到別的跑批日期上。

---

## 與倉儲抽樣表的差異

`ingest_gsc_search_analytics.py` 寫進 `gsc_daily_metrics` 的資料，是**逐日、
分組（page/query × device）** 的 top-N 抽樣（API 對同一 property 同一 search
type 每天最多回 50,000 列），`SUM(clicks)` 得到的是「這些 page/query 的相對
趨勢」，不是總量，該檔模組 docstring 有完整說明。

本腳本每個 cell 是一次**不分組**查詢，回傳的就是該過濾條件（或該 surface）在
整個視窗內的**聚合總點擊**，與 GSC 介面卡片的口徑一致，不受 top-N 抽樣截斷
影響——這也是它能拿來跟「舊爬蟲讀介面卡片」的數字逐格比對的原因。兩者母體與
用途都不同，不可互相驗算或相加。

---

## 關鍵字口徑判讀（G27~G34）

`includingRegex` 在 GSC 介面（`~` 前綴＝自訂規則運算式）與 API 之間，實測前應
先假設兩者一致；若比對出現系統性落差，用 `--equals-control` 對同一個關鍵字多打
一次 `operator: equals`（精確比對）當對照組：

- API `includingRegex` 值 ≈ 舊值 → 介面與 API 對這個 pattern 的語意一致，倉儲的
  「包含加總」口徑（分組後對多個 query 加總）是另一回事，不是這裡的問題。
- API 值 ≫ 舊值（例如某關鍵字 API 回一百多、舊值卻是個位數）→ 舊爬蟲透過 URL
  查詢參數送出去的規則運算式，在介面實際被當成別的語意解讀（可能是被當成子字串
  精確比對、或被 URL 編碼／跳脫規則以不同方式處理），需要留原始請求與回應人工
  核對，不要直接假設 API 錯或舊值錯。

兩種情況都只記錄事實與推論，依 live 證據標 `[live]`／依配置與程式碼推論標
`[provisional]`，**不要改舊爬蟲**——那是另一個 repo，改動需要另外的授權與流程。
