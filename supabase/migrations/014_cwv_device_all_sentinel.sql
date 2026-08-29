-- 014_cwv_device_all_sentinel.sql
-- 讓 cwv_hourly.device 多收一個值 'all'，代表 CrUX History API「不帶 formFactor」
-- 的跨裝置聚合查詢結果。
--
-- 【為什麼要開這個 migration，而不是在匯入端硬塞既有值】
-- p75 不可跨桶重組（見 KB learned skill percentiles-dont-recombine-across-buckets）：
-- 「不分裝置的 origin p75」無法從 mobile/desktop/tablet 三列推導回去，是一個獨立、
-- 拿不回來的量測值，而且正是 Google 評定 Core Web Vitals 用的那個頭條數字。
-- 不存 = 永久放棄，這跟 cwv_hourly.sample_count 那種「存了也有代價、但存不存
-- 是選擇題」不是同一層級的取捨——這裡不存根本沒有等價的補救路徑。
-- 013 原本把這個切面排除在外（見同檔案 ingest_cwv_crux_history.py 對映決定 d
-- 的舊版說明），team-lead 2026-08-29 裁決應該收，理由如上。
--
-- 【這個新值引入的危險 — 讀 schema 的人與寫查詢的人都要看到這段】
-- 'all' 與 'mobile' / 'desktop' / 'tablet' 三個既有值共用同一個 unique key
-- 空間（cwv_hourly_dim_uniq 是 (source, environment, hour, metric, route_type,
-- device)，device 只是其中一個維度，不是切出獨立的表或獨立的 key 空間）。
-- 任何**沒有顯式帶 device 條件**的 `GROUP BY hour` 或 `SUM(...)` 聚合，都會把
-- all + mobile + desktop + tablet 四列全部加總，得到一個看起來合理、實際上是
-- 「全站流量的四倍」的數字——不會報錯、不會有任何警告，圖照樣畫得出來。
--
-- 這跟 013 的 source 混算是同一類危險，但更隱蔽：source 至少有
-- cwv_hourly_source_granularity_ck 這道 CHECK 在 schema 層攔住一半（rum 對整點、
-- crux 對週界，兩種粒度天生對不上，錯誤查詢容易在資料形狀上露餡）。device
-- 沒有等價防線可設——'all' 在型別、長度、粒度上跟其他三個值完全一樣合法，
-- CHECK constraint 沒有能力表達「這個值不能跟另外三個值同時出現在同一次
-- SUM 裡」這種跨列語意。**這件事只能靠查詢端自律**：任何讀 cwv_hourly 的
-- SQL、dashboard panel、report 產生器，只要沒有顯式的 `device = '...'` 或
-- `device != 'all'` 條件，就要假設它在重複計算。
--
-- 【套用狀態 — 接手前必讀，沿用 013 的紀律】
-- 本檔套用前已用本機 postgres:17-alpine（套 013+014 疊加）驗證：
--   - 'all' 可寫入 cwv_hourly.device
--   - 既有的 mobile/tablet/desktop/unknown 四個值不受影響（仍可寫、仍可查）
--   - 不合法值（例如 'phone'）仍被拒絕
--   - 本檔重跑兩次冪等（DROP CONSTRAINT IF EXISTS 使然）
-- 驗證記錄見 knowledge-base .verification/2026-08-29-seo-capability/
-- S2.4-crux-history/migration-014-local-verify.txt。
-- 驗證通過後才 `supabase db push` 到遠端（eqrlomuujichshkbtoat，PG 17.6.1）。

-- DROP CONSTRAINT 沒有「先檢查值域再刪」的原子操作，但兩句都在同一個 migration
-- 檔內、Supabase migration 本身在單一 transaction 中執行，中途失敗會整個 rollback，
-- 不會出現「刪了舊的但沒建新的」這種中間態卡住 schema 的情況。
ALTER TABLE cwv_hourly
  DROP CONSTRAINT IF EXISTS cwv_hourly_device_ck;

ALTER TABLE cwv_hourly
  ADD CONSTRAINT cwv_hourly_device_ck
    CHECK (device IN ('mobile', 'tablet', 'desktop', 'all', 'unknown'));
