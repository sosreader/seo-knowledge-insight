-- 016_gsc_daily_metrics_combo_views.sql
-- gsc_daily_metrics 的兩個組合 view：gsc_page_daily / gsc_query_daily
--
-- 沿用 013/015 的紀律：
--   - 「能讓 DB 擋住的事就不要靠文件約定」（013 對 environment 欄位的論證）
--   - DDL 重跑冪等（CREATE OR REPLACE VIEW 天生冪等）
--   - 危險寫進 COMMENT ON（PostgREST 會吐進 OpenAPI，Supabase Studio 直接顯示），
--     不是只寫在 migration 註解裡等人翻
--
-- 【編號】新增前已 `ls supabase/migrations/` 確認：現況最大為 015，故本檔為 016。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【為什麼需要這兩個 view —— 不是為了方便，是為了擋掉一個沒有訊號的錯誤】
-- ══════════════════════════════════════════════════════════════════════
--
-- gsc_daily_metrics 裡同時裝著**同一批底層資料的兩個邊際聚合**：
--
--   page 組  = Search Analytics 以 (date, page, device) 為維度查回來的結果
--   query 組 = 同一天、同一批點擊，改以 (date, query, device) 為維度查回來的結果
--
-- 兩組加起來不是「更完整的資料」，是**同一批點擊被數了兩遍**。
-- 而 dim_uniq 是 (property, search_type, date, page, query, device, country) 七欄，
-- 兩組共用同一個 key 空間，於是：
--
--     SELECT SUM(clicks) FROM gsc_daily_metrics;   -- ← 約等於真實值的兩倍
--
-- 這個查詢**不會報錯、不會有警告、圖照樣畫得出來**。它就是 KB learned skill
-- `rollup-sentinel-in-shared-key-space-has-no-check-guard-against-double-count`
-- 講的那個坑，而且 CHECK constraint 擋不住 —— CHECK 只能約束單一列的欄位值，
-- 表達不了「這兩類列不可同時進入同一次 SUM」這種跨列語意。
--
-- 015 對 property 欄位用的解法（把值域縮到單值，讓危險狀態無法被表示，見
-- `shrink-domain-to-one-value-makes-cross-row-double-count-unrepresentable`）
-- 在這裡**用不上**：兩套組合都要存，值域不能縮。
--
-- 所以這一層只能是「讓正確路徑成為最省事的路徑」：
--   - 兩個 view 各自把判別式寫死在定義裡，下游不可能忘記帶
--   - 兩個 view 都**不暴露對方的哨兵欄位**（page 組看不到 query/country，
--     query 組看不到 page/country）—— 拿不到哨兵值，就不會誤用它
--
-- 【這一層擋得住什麼、擋不住什麼 —— 別高估它】
-- 擋得住：照著 view 查的人不會重複計算，而且不需要知道哨兵值存在。
-- **擋不住**：直接查底表 gsc_daily_metrics 的人。底表的權限刻意**維持現狀**
--   （team-lead 2026-09-01 裁決）—— 撤權會擋掉維運查詢，而我們沒有真正的
--   多租戶邊界。這一層靠慣例，不是強制。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【security_invoker = true 不可省】
-- ══════════════════════════════════════════════════════════════════════
-- PostgreSQL 的 view 預設以**建立者的權限**執行（security definer 語意），
-- 於是 view 會**繞過底表的 RLS**。015 對 gsc_daily_metrics 設的是
-- 「RLS ENABLE + 零 policy」= default deny，若這裡建一個預設語意的 view，
-- 等於在那道 default deny 上開一個洞：view 的擁有者是 postgres，
-- 任何拿得到 view 權限的角色都會讀到全表。
--
-- `security_invoker = true`（PG 15+，目標環境 17.6.1）讓 RLS 以**查詢者**的
-- 身分求值，view 因此繼承底表的 default deny。
-- 下方另外對 anon/authenticated/PUBLIC REVOKE 一次，是縱深防禦：
-- Supabase 對 public schema 有預設 GRANT，新建物件會自動被涵蓋。

-- ══════════════════════════════════════════════════════════════════════
-- 0. 哨兵值的單一事實來源
-- ══════════════════════════════════════════════════════════════════════
-- 哨兵字面值原本會出現在 3 個地方（兩個 view 的 WHERE + ingest 腳本的常數）。
-- 收斂成一個 IMMUTABLE 函式，改哨兵時 DB 這側是單一 CREATE OR REPLACE，
-- 兩個 view 自動同步；漏改一個就讓兩個 view 的判別式靜默分岔，
-- 正是本檔一直在對抗的那種「沒有訊號的錯誤」。
--
-- IMMUTABLE + 回傳常數 ⇒ planner 會 inline 成常數，不影響索引使用
-- （本機 postgres:17 實測 EXPLAIN 確認，見 verification 檔）。
--
-- 注意：ingest 端（scripts/ingest_gsc_search_analytics.py 的 PAGE_NOT_REQUESTED）
-- 是**第 4 個** consumer，它跨越了 process 邊界、沒辦法 import 這個函式，
-- 只能靠兩邊字串相同。改哨兵時兩邊必須同一個 PR 一起改。
CREATE OR REPLACE FUNCTION gsc_page_not_requested() RETURNS TEXT
  LANGUAGE sql IMMUTABLE PARALLEL SAFE
  AS $$ SELECT 'https://__dimension_not_requested__/'::TEXT $$;

COMMENT ON FUNCTION gsc_page_not_requested() IS
  'gsc_daily_metrics 中「這一列不是以 page 為維度查回來的」的哨兵值。'
  'query 組的列 page 欄存這個值；page 組存真實 URL。'
  '判別式一律以 page 為準（不以 query 為準）：兩者互斥且窮盡，沒有第三種狀態。'
  'ingest 端 scripts/ingest_gsc_search_analytics.py 的 PAGE_NOT_REQUESTED 必須與此一致。';

-- ══════════════════════════════════════════════════════════════════════
-- 1. gsc_page_daily —— 以 (date, page, device) 為維度的那一半
-- ══════════════════════════════════════════════════════════════════════
-- 刻意不選 query 與 country：這兩欄在 page 組的列裡是哨兵值
-- （query='' 與 country='zzz'），暴露出去只會讓下游誤以為
-- 「這些點擊來自空查詢 / 來自未知地區」。它們不是觀測值。
CREATE OR REPLACE VIEW gsc_page_daily
  WITH (security_invoker = true) AS
SELECT
  date, property, search_type, page, device,
  clicks, impressions, ctr, position, ingested_at
FROM gsc_daily_metrics
WHERE page <> gsc_page_not_requested();

COMMENT ON VIEW gsc_page_daily IS
  'GSC Search Analytics 以 (date, page, device) 為維度的逐日抽樣資料。'
  '【務必先讀】底表 gsc_daily_metrics 同時裝著另一組以 (date, query, device) 為維度的列，'
  '兩組是同一批點擊的兩個邊際聚合；直接對底表 SUM(clicks) 會得到約兩倍的假數字，'
  '且不會有任何錯誤訊號。本 view 已寫死判別式，照這裡查不會重複計算。'
  '【資料是抽樣不是全量】API 只回 top rows 且每天每 property 每 search type 上限 50,000 列，'
  '所以 SUM(clicks) 必然小於 GSC UI 上的總點擊，差額大小不可知。'
  '本 view 每日約 28,000 列（未貼上限），截斷程度低於 gsc_query_daily。';

-- ══════════════════════════════════════════════════════════════════════
-- 2. gsc_query_daily —— 以 (date, query, device) 為維度的那一半
-- ══════════════════════════════════════════════════════════════════════
-- 同理不選 page 與 country：page 在這組列裡就是哨兵本身。
CREATE OR REPLACE VIEW gsc_query_daily
  WITH (security_invoker = true) AS
SELECT
  date, property, search_type, query, device,
  clicks, impressions, ctr, position, ingested_at
FROM gsc_daily_metrics
WHERE page = gsc_page_not_requested();

COMMENT ON VIEW gsc_query_daily IS
  'GSC Search Analytics 以 (date, query, device) 為維度的逐日抽樣資料。'
  '【務必先讀】底表 gsc_daily_metrics 同時裝著另一組以 (date, page, device) 為維度的列，'
  '兩組是同一批點擊的兩個邊際聚合；直接對底表 SUM(clicks) 會得到約兩倍的假數字，'
  '且不會有任何錯誤訊號。本 view 已寫死判別式，照這裡查不會重複計算。'
  '【本 view 的資料被截斷，缺的正好是長尾】實測 2026-08-23..08-29 七天，'
  '每日列數 47,832 / 47,956 / 47,923 / 48,004 / 48,048 / 48,009 / 47,861 —— '
  '波動不到 0.5%，貼著 50,000 列/天的 API 天花板。真實搜尋流量不會連續七天穩在 ±0.2% 內，'
  '那是天花板的形狀不是流量的形狀。因此：任何「query 總點擊」的加總只是**下界**，'
  '而 index bloat / thin content 這類需要看長尾的分析，缺的正是被截掉的那部分。';

-- ══════════════════════════════════════════════════════════════════════
-- 3. 權限
-- ══════════════════════════════════════════════════════════════════════
-- security_invoker=true 已讓 view 繼承底表的 RLS default deny；
-- 這裡再撤一次 Supabase 對 public schema 的預設 GRANT，理由同 015 第 660 行起的論證。
-- 底表 gsc_daily_metrics 的權限**不動**（team-lead 2026-09-01 裁決：
-- 撤權會擋掉維運查詢，且無真正的多租戶邊界）。
DO $$
DECLARE r TEXT;
BEGIN
  FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('REVOKE ALL ON TABLE gsc_page_daily, gsc_query_daily FROM %I', r);
    END IF;
  END LOOP;
END
$$;

-- REVOKE ... FROM <role> 不會撤銷授予 PUBLIC 的權限（那是獨立的 grantee），
-- 所以另外撤一次，理由同 015。
REVOKE ALL ON TABLE gsc_page_daily, gsc_query_daily FROM PUBLIC;
