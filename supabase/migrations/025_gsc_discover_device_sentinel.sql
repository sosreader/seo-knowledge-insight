-- 025_gsc_discover_device_sentinel.sql
-- 讓 Discover 的 (date, page) 列進得了 gsc_daily_metrics：device 哨兵值 'n/a' + 「哨兵 ⇔ surface」等價 CHECK
--
-- 【編號】新增前已現場 `ls supabase/migrations/` 確認：磁碟現況最大為 024_ai_sov.sql，
-- 且 `supabase migration list --linked` 顯示 024_ai_sov 已在 remote，本檔為 025。
-- （013 註解記過一次同編號相撞 `duplicate key ... Key (version)=(012)` 的事故，
--   「往上加 1」不是可靠做法，必須先列目錄。）
--
-- 【與鄰居分支的關係 —— 本檔不依賴 023／024】
--   023_crawl_daily_from_origin.sql 只存在於 peer 的本機分支 feat/crawl-daily-from-origin-023，
--   remote 沒有、也沒有 open PR；024_ai_sov.sql 已在 main 與 remote。
--   本檔只碰 gsc_daily_metrics 的兩道 CHECK 與三段 catalog 註解，
--   與 023（crawl_daily）、024（ai_sov 相關物件）零交集。
--   本機驗證鏈**刻意跳過 023 與 024**（013→014→015→016→017→018→019→020→021→022→025），
--   套用成功即是「本檔獨立於那兩支」的證明，而不是靠讀 diff 推論。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【這個檔在解什麼問題】
-- ══════════════════════════════════════════════════════════════════════
--
-- 022 讓 discover 通過 search_type_ck 與 position_ck 之後，Discover 仍然只有
-- gsc_daily_totals（date-only 全站總數），**沒有 page 層明細**。剩下的那道牆是 device：
--
--   Search Analytics API 對 type=discover 帶 device 維度直接回 400
--   （run 33766178810 live 實測），所以 Discover 的列拿不到 device 值；
--   而 device 是 gsc_daily_metrics_dim_uniq 的成員、NOT NULL、且 015 的
--   device_ck 把值域鎖死在 mobile / tablet / desktop 三值。
--   結果是「(date, page) 的 Discover 列在結構上放不進這張表」。
--
-- 本檔給 device 一個「此 surface 不提供裝置維度」的哨兵值 'n/a'，
-- 並用第二道 CHECK 把它**綁死在 discover 上**。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【為什麼是 'n/a' 而不是 'all' —— 這不是 014 的哨兵，語意相反】
-- ══════════════════════════════════════════════════════════════════════
--
-- 015 第 231-246 行明確拒絕在本表放 'all' 之類的彙總哨兵，理由是
-- 「clicks / impressions / ctr / position 全部可重組，存彙總列拿不到任何多出來的
--   資訊，只會白白引進 014 那個『忘了過濾就四倍』的重複計算風險」。
-- 那個論證在本檔之後**一個字都不用改**，因為兩者是不同的東西：
--
--   014 的 cwv_hourly.device = 'all'  →「我們把三個裝置桶彙總了」
--                                       彙總列與成分列**同時存在**，
--                                       忘了過濾就把同一批流量算兩次。
--   本檔的 device = 'n/a'             →「API 根本不提供這個維度，拆不出來」
--                                       哨兵列**沒有成分列可以共存**（見下一段的 CHECK），
--                                       同一個 surface 內不存在第二個切面可以被重複加總。
--
-- 沿用 'all' 這個字會讓讀 015 的下一個人以為 025 推翻了那段論證，實際上沒有。
-- 名字不同正是為了讓「不可拆」與「已彙總」兩種語意在讀表的人眼前分開。
--
-- 【為什麼 'n/a' 這個值是安全的】哨兵值的判準是「結構上不可能是真值」：
-- ingest 端的 DEVICE_MAP 只映射 MOBILE / TABLET / DESKTOP 三個 API 枚舉，
-- 未知值一律 reject，API 的 device 枚舉本身也是固定的三值。
-- 任何非三值都滿足這個判準；選 'n/a' 是為了語意（「不提供」而非「已彙總」），
-- 並與腳本既有的 *_NOT_REQUESTED 哨兵命名族一致。
-- 它的「格式 CHECK」就是下方 device_ck 的 IN 清單本身——值域只多這一個字，
-- 打錯成 'na' / 'N/A' / 'none' 的寫入端一律被擋。
--
-- 【可見性】Grafana 對 discover 做 GROUP BY device 會看到一個獨立的 'n/a' 桶，
-- 而不是被靜默併進 mobile——哨兵要看得見才叫哨兵。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【為什麼第二道 CHECK 擋得住「忘記過濾造成重複計算」】
-- ══════════════════════════════════════════════════════════════════════
--
-- PostgreSQL 的 CHECK 只能引用同一列的欄位，所以它表達不了「跨列」的命題
-- （014 那種「彙總列與成分列不可共存」正是跨列命題，CHECK 擋不住，只能靠查詢端自律）。
--
-- 本檔的判別欄不是 device 而是 **search_type**，於是同一件事變成單列命題：
--
--     CHECK ((device = 'n/a') = (search_type IN ('discover')))
--
-- 讀法是一個等價式，兩個方向都被綁死：
--   → discover 的列，device **只能**是 'n/a'（不可能同時存在分裝置的 discover 列）
--   ← 非 discover 的列，device **不可以**是 'n/a'（哨兵不會外溢到 web / image / …）
--
-- 因此「同一個 surface 同時有分裝置列與不分裝置列」成為**無法表示的狀態**，
-- 而不是一個需要查詢端記得過濾的紀律問題。這是 015／022 一路下來的同一個判準：
-- 讓危險狀態表達不出來，優先於靠寫入端自律。
--
-- 【講清楚它擋不住什麼】跨 surface 的 SUM 不帶 search_type 本來就是雙算
-- （web + image + video + news + googleNews + discover 六個 surface 相加），
-- 那是 015 建表當天就存在的性質，本檔既沒有引進也沒有修好它。
-- 同理，底表同時裝著 (date, page, device) 與 (date, query, device) 兩組邊際聚合，
-- 直接對底表 SUM(clicks) 約兩倍——那要走 gsc_page_daily / gsc_query_daily 兩個視圖。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【被排除的方案】
-- ══════════════════════════════════════════════════════════════════════
--
--   1. device 改 nullable（DROP NOT NULL，NULL 代表不提供）：
--      UNIQUE 對 NULL 視為彼此不同，同一 (date, page) 會累積重複列，
--      upsert 的冪等性直接失效。要修就得改用 PG 15 的 NULLS NOT DISTINCT，
--      那需要重建 1.6M 列的 dim_uniq（ACCESS EXCLUSIVE，時間遠長於加一條 CHECK），
--      而且 PostgREST 的 on_conflict 對 NULL 鍵的行為還要另外驗。
--      多一步不多一分安全——與 022 拒絕 DROP NOT NULL 的理由同一套。
--
--   2. 改 unique key（把 device 拿掉，或換成 dimension_kind 欄）：
--      牽動 upsert 衝突鍵、016／022 的兩個視圖、reap 判別式與所有既有列，
--      牽連遠大於一條 CHECK。
--
--   3. 另開 gsc_discover_page_daily 表：
--      Discover 的 page 列與 googleNews 的 page 列是**同一種母體**
--      （API top-N 抽樣的 page×date），022 已把 googleNews 放進本表。
--      表的分界應該落在母體不同（全量 vs 抽樣，那是 gsc_daily_totals 的理由），
--      不是落在「這個 surface 少一個維度」。分表只會讓 Grafana 的 top-page
--      查詢變成 UNION。
--
--   4. 假填 'mobile'：違反 ingest 端「不靜默改寫 API 回的值」的原則
--      （scripts/gsc_surfaces.py:80 註解，「不假填 'mobile'」那段）。
--      更糟的是如果 API 日後開放 Discover 的 device 拆分，舊的假 mobile 列
--      與新的真 mobile 列會落在同一個 key 空間變成真雙算，
--      而且沒有任何 CHECK 分辨得出來。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【既有資料相容性】
-- ══════════════════════════════════════════════════════════════════════
--
-- 套用前底表約 1.62M 列，device 全部 ∈ {mobile, tablet, desktop}
-- 且 search_type 全部 ≠ 'discover'（Discover 至今只寫進 gsc_daily_totals）。
-- 對這些列：device_ck 放寬後恆真；device_surface_ck 兩邊皆 false，等價式成立，恆真。
-- 所以兩次 ADD CONSTRAINT 的全表驗證掃描不會失敗。
--
-- 【對視圖與 grant 是 no-op】本檔不動 gsc_page_daily / gsc_query_daily
-- （022 L316-343 的定義原封不動）、不動任何 GRANT / POLICY。
-- Discover 的 page 列判別式是 page（page <> gsc_page_not_requested()），
-- 與 device 無關，所以新列會自然落進 gsc_page_daily；
-- 它們的 position 恆為 0，視圖的 NULLIF 已經把它轉成 NULL（022 已處理）。
-- ⚠ 但 NULL **修不掉**加權平均：SUM(position*impressions)/SUM(impressions) 的分母
-- 仍會把無排名的列算進去。分子分母都要加 FILTER (WHERE position IS NOT NULL)。
-- 這條陷阱對 Discover 與 googleNews 同樣適用，已寫進下方 device 欄的 catalog 註解旁路。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【冪等性】
-- ══════════════════════════════════════════════════════════════════════
--
-- PostgreSQL 的 ADD CONSTRAINT 沒有 IF NOT EXISTS（021 註解已記過這個坑），
-- 一律 DROP CONSTRAINT IF EXISTS 前置，drop-then-add 可重跑任意次。
-- COMMENT ON 天生冪等（覆寫既有註解）。
-- 本檔可重跑任意次（本機 postgres:17 實測套用兩次，第二次零 ERROR）。
--
-- 【lock 影響】本檔對 gsc_daily_metrics 發四道 ALTER TABLE，**四道都取 ACCESS EXCLUSIVE lock**：
--   兩道 DROP CONSTRAINT IF EXISTS —— 取鎖，但只改 catalog，不掃表，瞬間完成；
--   兩道 ADD CONSTRAINT         —— 取鎖，且各做一次全表驗證掃描
--                                  （022 在約 1M 列時實測秒級；現況 1.62M 列 × 兩次，
--                                   估 5-15 秒，provisional）。
-- 因為整支在單一 transaction 內，第一道 DROP 取得的鎖就會一路持有到 COMMIT，
-- 四道不是「取四次放四次」而是「取一次持有到底」——
-- 所以持鎖總時間由那兩次驗證掃描決定，把 DROP 算進來不會讓它變長。
-- 敘述要完整的理由是：真正的起點是第一道 DROP，估算「從哪一刻開始擋寫入」要從它算起。
-- lock 期間排程寫入會等待——
-- push 本檔請避開 07:00-08:00 UTC（每日 GSC 排程）與 09:30 UTC 前後。
--
-- 【為什麼下方要 SET LOCAL lock_timeout】supabase db push 把每支 migration 包在
-- 單一 transaction 內（provisional），而 ACCESS EXCLUSIVE lock 一旦取得就會
-- **一路持有到 COMMIT**，不是「驗證完就放」。真正的風險不是驗證掃描那 5-15 秒，
-- 是「拿不到鎖」的情況：若此時有長交易或排程寫入占著表，本檔會無限期排隊，
-- 而排在它後面的所有新查詢又會被本檔的 lock 請求擋住（PG 的 lock 佇列是 FIFO，
-- 一個等待中的 ACCESS EXCLUSIVE 請求足以讓後續 SELECT 一起卡住），
-- 於是一支 DDL 的等待會放大成整條 API 停擺。
-- lock_timeout = '5s' 讓這個情境變成「5 秒後放棄、整支 migration rollback」——
-- 失敗是可重試的、看得見的；停擺不是。逾時就換個時段重跑即可。
-- SET LOCAL 的作用域是當前 transaction，COMMIT / ROLLBACK 後自動還原，
-- 不會外溢到連線的其他工作。
-- ⚠ 若在 transaction block 外執行（例如 psql -f 的 autocommit 模式），
-- PG 只會發一則 WARNING: SET LOCAL can only be used in transaction blocks，
-- 不是 ERROR，本檔仍會正常套用——本機驗證鏈實測即是這個情形。
--
-- 【本檔刻意不做的事】不加任何索引。既有 dim_uniq 的前綴就是
-- (property, search_type, date)，2026-09-04 在 1.62M 列上實測：per-surface 查詢
-- 只要帶 property = 'https://vocus.cc/'，同形的 freshness 查詢就從 33,266 ms
-- 掉到個位數毫秒（googleNews 那條走 Index Only Scan Backward using dim_uniq，5.0 ms）；
-- 不帶 property 則前導欄位缺等值條件，任何複合索引前綴都用不上。
-- 實測檔在 .verification/2026-09-04/gate-probe-shape/（explain-5 vs explain-after-*）。
-- 這是查詢寫法的問題，不是缺索引的問題，加索引解不掉也不需要。
-- 詳見下方 COMMENT ON TABLE 的最後一句。


-- ══════════════════════════════════════════════════════════════════════
-- 1. device_ck —— 值域加入哨兵 'n/a'
-- ══════════════════════════════════════════════════════════════════════
--
-- 015 原本鎖死三值。加第四個字之後，值域本身就是哨兵的格式檢查：
-- 寫入端打成 'na' / 'N/A' / 'unknown' 一律被擋，不會靜默生出第二種哨兵拼法。
-- 這一段單獨看是「放寬」，必須與第 2 段一起讀才是完整的防線——
-- 兩道 CHECK 必須在同一支 migration 一起改，否則就是 015 對 discover 警告過的半開狀態。

-- 拿不到鎖就在 5 秒後放棄整支 migration（rollback），理由見檔頭【為什麼下方要 SET LOCAL lock_timeout】。
-- 放在第一個 ALTER 之前，涵蓋本檔的兩次 ADD CONSTRAINT。
SET LOCAL lock_timeout = '5s';

ALTER TABLE gsc_daily_metrics
  DROP CONSTRAINT IF EXISTS gsc_daily_metrics_device_ck;

ALTER TABLE gsc_daily_metrics
  ADD CONSTRAINT gsc_daily_metrics_device_ck
  CHECK (device IN ('mobile', 'tablet', 'desktop', 'n/a'));


-- ══════════════════════════════════════════════════════════════════════
-- 2. device_surface_ck —— 哨兵 ⇔ surface 的等價式（本檔的主防線）
-- ══════════════════════════════════════════════════════════════════════
--
-- 【要加第二個沒有 device 維度的 surface 時，改這裡】
-- 把新的 search_type 加進下方 IN 清單，並**同步**改
-- scripts/gsc_surfaces.py 的 NO_DEVICE_SURFACES = frozenset({'discover'})。
-- 兩邊是一一對應的關係：is_device_valid() 就是這道 CHECK 的 Python 複本
-- （做法同 022 之後的 is_position_valid 對 position_ck）。
-- 只改一邊的後果不對稱：只改 Python → 寫入被 DB 擋下（吵、看得見）；
-- 只改 CHECK → DB 放行了 Python 還在 reject，會變成靜默漏資料。
-- 所以順序是先改 CHECK（migration）再改 Python，兩者同一次交付。
ALTER TABLE gsc_daily_metrics
  DROP CONSTRAINT IF EXISTS gsc_daily_metrics_device_surface_ck;

ALTER TABLE gsc_daily_metrics
  ADD CONSTRAINT gsc_daily_metrics_device_surface_ck
  CHECK ((device = 'n/a') = (search_type IN ('discover')));


-- ══════════════════════════════════════════════════════════════════════
-- 3. catalog 註解
-- ══════════════════════════════════════════════════════════════════════
--
-- 015 第 690-700 行的理由在這裡同樣適用：這幾句話的受害者是
-- 「照著欄位值寫聚合查詢的下一個人」，而錯誤形式是靜默的
-- （多一個沒人預期的 device 桶、或把 'n/a' 當成一種真裝置），不會報錯。
-- 所以它必須進 pg_description，而不是只留在這個檔案的 SQL 註解裡。

COMMENT ON COLUMN gsc_daily_metrics.device IS
  '對應 BigQuery device，值域轉小寫。'
  '⚠ 【''n/a'' 是哨兵，不是一種裝置】search_type = ''discover'' 時本欄恆為 ''n/a''，'
  '意思是「Search Analytics API 對這個 surface 不提供 device 維度」（帶 device 查詢直接回 400），'
  '**不是**「彙總了三個裝置」。與 cwv_hourly.device = ''all'' 語意相反：'
  '那個是彙總列、與成分列共存、忘了過濾會四倍；本欄的 ''n/a'' 沒有成分列可以共存，'
  '因為 gsc_daily_metrics_device_surface_ck 規定 discover 的列只能是 ''n/a''、'
  '非 discover 的列不可以是 ''n/a''。'
  '因此對單一 surface 做 GROUP BY device 不會重複計算；'
  '跨 surface 相加本來就是雙算，那與本欄無關（要帶 search_type 過濾）。'
  '⚠ 對 discover 做 GROUP BY device 會看到一個獨立的 ''n/a'' 桶，這是預期行為；'
  '若要與 web 的裝置分佈並排呈現，''n/a'' 應標示為「不適用」而非併進任一裝置。'
  '⚠ discover 的列 position 恆為 0（無排名概念），視圖 gsc_page_daily 已轉成 NULL，'
  '但加權平均的分母仍需 FILTER (WHERE position IS NOT NULL)，見 position 欄註解。';

COMMENT ON CONSTRAINT gsc_daily_metrics_device_surface_ck ON gsc_daily_metrics IS
  '哨兵 ⇔ surface 的等價式：(device = ''n/a'') = (search_type IN (''discover''))。'
  '兩個方向都被綁死——discover 的列只能是 ''n/a''，非 discover 的列不可以是 ''n/a''。'
  '目的是讓「同一個 surface 同時有分裝置列與不分裝置列」成為無法表示的狀態，'
  '而不是需要查詢端記得過濾的紀律問題（CHECK 只能管同一列，所以判別欄選 search_type 而非 device）。'
  '要新增第二個沒有 device 維度的 surface：改本 CHECK 的 IN 清單，'
  '並同步 scripts/gsc_surfaces.py 的 NO_DEVICE_SURFACES。';

-- COMMENT ON TABLE 是覆寫不是追加，所以照抄 015 第 701-702 行的原文，
-- 只在句末補上 2026-09-04 實測得到的查詢寫法要求（REQ-3 的橫切規則）。
COMMENT ON TABLE gsc_daily_metrics IS
  'Search Analytics API 逐日抽樣事實表。⚠ 這是 top-N 抽樣不是全量：API 每天每 property 每 search type 最多回 50,000 列，'
  '且官方明講只回 top rows、不保證涵蓋全部資料列。因此 SUM(clicks) 必然小於 GSC UI 上的當日總點擊，落差大小不可知。'
  'property 值域鎖成單一值以杜絕跨 property 重複計算。資料保留 16 個月、延遲 2-3 天。'
  '⚠ 【帶 search_type 的查詢一定要同時帶 property】dim_uniq 的前綴是 (property, search_type, date)，'
  '前導欄位缺等值條件時整個複合索引前綴用不上。2026-09-04 在 162 萬列上實測 freshness 查詢：'
  '只帶 search_type=''video'' 不帶 property 是 33,266 ms（走 date_idx，Rows Removed by Filter 145,064）；'
  '補上 property = ''https://vocus.cc/'' 後同形查詢落在 2.4-63 ms，'
  '其中 googleNews 那條走 Index Only Scan Backward using dim_uniq（5.0 ms）。'
  '⚠ 帶了 property 不保證一定走 dim_uniq：image 那條仍走 date_idx（63 ms），'
  '因為該 surface 的切片夠大、planner 判斷掃 date_idx 更划算——重點是最壞情況從 33 秒收斂到毫秒級。'
  '原始 EXPLAIN ANALYZE 輸出在 repo 的 .verification/2026-09-04/gate-probe-shape/'
  '（explain-5-freshness-video-search-type 對照 explain-after-1..3）。'
  'property 是單值 DOMAIN，帶上它不改變任何結果，只改索引路徑。';


-- ══════════════════════════════════════════════════════════════════════
-- === 套用後應成立的狀態 ===
-- ══════════════════════════════════════════════════════════════════════
--
-- CHECK 定義（pg_get_constraintdef 讀回）：
--   gsc_daily_metrics_device_ck
--     → CHECK (device = ANY (ARRAY['mobile','tablet','desktop','n/a']))
--   gsc_daily_metrics_device_surface_ck
--     → CHECK (((device = 'n/a'::text) = (search_type = 'discover'::text)))
--     （PG 會把單元素的 IN (...) 正規化成 =，本機 postgres:17 讀回實測如上；
--       語意與原始碼的 IN ('discover') 相同，加第二個 surface 後才會顯示成 ANY (ARRAY[...])。）
--   （其餘 CHECK 一個字都沒動：search_type_ck、position_ck、country_ck、page_ck、
--     query_ck、date_ck、ctr_ck 等仍是 022 之後的定義。）
--
-- 寫入行為（本機 postgres:17 實測四組測資）：
--   INSERT search_type='discover', device='n/a',    position=0 → 成功
--   INSERT search_type='discover', device='mobile', position=0 → 被 device_surface_ck 擋下
--   INSERT search_type='web',      device='n/a',    position=3 → 被 device_surface_ck 擋下
--   INSERT 任一 surface,           device='tv'                 → 被 device_ck 擋下
--   （既有路徑無回歸：web + mobile + position>=1 仍然成功。）
--
-- 冪等：
--   同一組 dim_uniq 鍵連續 upsert 兩次 → 表內仍只有一列（ON CONFLICT DO UPDATE）。
--
-- 視圖：
--   gsc_page_daily 查得到 discover 的列（判別式是 page，與 device 無關），
--   該列的 position 回 NULL（NULLIF，022 已有），device 回 'n/a'。
--   gsc_page_daily / gsc_query_daily 的定義與欄位順序完全未改。
--
-- 權限與 RLS：
--   本檔沒有任何 GRANT / REVOKE / POLICY 敘述，
--   has_table_privilege('seo_dashboard_ro', ...) 的結果與 022 收尾時完全相同。
--
-- 既有資料：
--   gsc_daily_metrics 的列數在套用前後完全相同（本檔不寫入、不刪除任何一列）。
