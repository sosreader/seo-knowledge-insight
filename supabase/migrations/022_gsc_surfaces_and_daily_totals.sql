-- 022_gsc_surfaces_and_daily_totals.sql
-- 讓無排名 surface（googleNews / discover）進得了 gsc_daily_metrics，並另開 gsc_daily_totals 存全站總數
--
-- 【編號】新增前已現場 `ls supabase/migrations/` 確認：現況最大為 021，本檔為 022。
-- （013 註解記過一次同編號相撞 `duplicate key ... Key (version)=(012)` 的事故，
--   「往上加 1」不是可靠做法，必須先列目錄。）
--
-- ══════════════════════════════════════════════════════════════════════
-- 【這個檔在解什麼問題】
-- ══════════════════════════════════════════════════════════════════════
--
-- 兩件事，在 015 當時是刻意不做、現在有了需求才做：
--
--   (A) googleNews 與 discover 這兩個 surface 目前**結構上進不了**
--       gsc_daily_metrics。Search Analytics API 對它們回 position = 0
--       （不是「排第 0 名」，是「這個 surface 沒有排名這個概念」），
--       撞 position_ck；discover 另外還不在 search_type_ck 的值域裡。
--
--   (B) 倉儲只有 API 的 top-N 抽樣，沒有「與 GSC UI 上那個數字一致」的
--       全站總數可以當分母。8/25 實測抽樣只涵蓋 41.7% 點擊、8.0% 曝光——
--       沒有分母，任何「覆蓋率」「這篇文章佔全站多少」都答不出來。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【(A) 為什麼是條件式 CHECK，而不是把 position 改成 nullable】
-- ══════════════════════════════════════════════════════════════════════
--
-- 015 第 324-325 行寫下 position_ck 的用意：
--
--     「position 是 1-based。< 1 代表 ingest 端把 BQ 的 0-based sum_position
--       直接塞進來卻忘了 +1，這是遷移時最容易犯的錯，讓 DB 擋住。」
--
-- 那道防線要保留。可選的兩條路：
--
--   1. 欄位改 nullable、寫入時把 0 轉成 NULL。
--      代價是 DROP NOT NULL——等於對**所有** surface 拆掉「這一欄一定有值」
--      的保證，然後得再補一條 `(position IS NULL) = (search_type IN (...))`
--      的 CHECK 才能把防護補回來。多一步，不多一分安全。
--      而且 ingest 端的原則是「不靜默改寫 API 回的值」
--      （scripts/ingest_gsc_search_analytics.py L334 註解），存 0 是忠實紀錄。
--
--   2. CHECK 改成綁 search_type 的條件式（本檔採用）。
--      NOT NULL 保留、web/image/video/news 的 `>= 1` 防線一個字不動，
--      只對「已知沒有排名概念」的兩個 surface 開一個值為 0 的例外。
--      **例外的形狀被 CHECK 本身寫死**：googleNews / discover 也只能是 0
--      或 >= 1，不能是 0.5——0.5 仍然是 0-based 誤植的形狀，仍該被擋。
--
-- 選 2。判準：讓「危險狀態無法被表示」優先於「靠寫入端自律」，這是 013/015
-- 一路下來的紀律；把 NOT NULL 拆掉是往反方向走。
--
-- 【既有資料相容性】既有 web/news 列全部 position >= 1，新 CHECK 對它們恆真，
-- 所以 ADD CONSTRAINT 的全表驗證掃描不會失敗。
--
-- 【視圖層才是給人看的地方】底表存 0（忠實），視圖把 0 顯示成 NULL（可讀）。
-- 見下方第 3 節，那裡也寫明了 NULL **修不掉**哪一種聚合——別以為轉了 NULL 就安全。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【(B) 為什麼另開一張表，而不是在 gsc_daily_metrics 加哨兵列】
-- ══════════════════════════════════════════════════════════════════════
--
-- 這不是本檔的新判斷，是 015 第 243-246 行作者自己就寫下的結論：
--
--     「唯一真正不可重組的切面是「該日**未抽樣**的全站總計」（GSC UI 上那個
--       數字），它確實推不回來。但那也不該用哨兵列存：它跟本表的列**母體不同**
--       （全量 vs top-N 抽樣），混在同一張表、同一個 key 空間就是 014 的坑
--       再犯一次。要存的話請另開 gsc_daily_totals 表，讓它連被誤加總的
--       機會都沒有。」
--
-- 本檔就是那張表。補充兩個當時沒展開的技術理由：
--   - `page = ''` 這種哨兵會撞 gsc_daily_metrics_page_ck（要求 `^https?://`）。
--   - 若改用 `dimension_kind` 欄，它必須進 dim_uniq 才不會撞既有的七欄唯一鍵，
--     等於動到 upsert 的衝突鍵與 016 兩個視圖的判別式——牽連遠大於一張 8 欄新表。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【冪等性】
-- ══════════════════════════════════════════════════════════════════════
--
-- PostgreSQL 的 ADD CONSTRAINT 沒有 IF NOT EXISTS（021 註解已記過這個坑），
-- 一律 DROP CONSTRAINT IF EXISTS 前置，drop-then-add 可重跑任意次。
-- CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS / CREATE OR REPLACE
-- VIEW / COMMENT ON / GRANT 天生冪等。
-- CREATE POLICY 沒有 IF NOT EXISTS → DROP POLICY IF EXISTS 前置（照 018/020）。
-- ALTER TABLE ... ENABLE ROW LEVEL SECURITY 重跑不報錯。
-- 本檔可重跑任意次（本機 postgres:17 實測套用兩次，第二次零 ERROR）。
--
-- 【lock 影響】ALTER TABLE ... ADD CONSTRAINT 取 ACCESS EXCLUSIVE lock 並對
-- gsc_daily_metrics 全表驗證一次（30 萬列量級實測秒級）。每日排程在 07:20 UTC
-- 寫入，push 本檔請避開 07:00-08:00 UTC。


-- ══════════════════════════════════════════════════════════════════════
-- 1. gsc_daily_metrics —— 放寬兩道 CHECK
-- ══════════════════════════════════════════════════════════════════════

-- 1a. search_type_ck：值域加入 'discover'
--
-- 015 當時刻意扣掉 discover，理由是「值域收了它、另一道 CHECK 卻保證它裝不進去，
-- 照著值域實作的人會撞上一個看起來與 search_type 無關的 position_ck 錯誤」。
-- 那個理由在本檔之後不再成立：1b 已經讓 discover 的 position=0 通得過。
-- 兩道 CHECK 必須同一支 migration 一起改，否則就是 015 警告的那個半開狀態。
--
-- 'googleNews' 與 'discover' 都保留 API 原生的 camelCase / 小寫拼法，
-- 理由同 015：這些值要能直接當 Search Analytics API 的 `type` 參數送出。
ALTER TABLE gsc_daily_metrics
  DROP CONSTRAINT IF EXISTS gsc_daily_metrics_search_type_ck;

ALTER TABLE gsc_daily_metrics
  ADD CONSTRAINT gsc_daily_metrics_search_type_ck
  CHECK (search_type IN ('web', 'image', 'video', 'news', 'googleNews', 'discover'));

-- 1b. position_ck：改為綁 search_type 的條件式
--
-- 讀法：有排名的 surface 一律 >= 1（015 的原防線，一個字沒改）；
--       googleNews / discover 額外允許「恰好等於 0」這一個值。
-- 0 以外的 <1 值（例如 0.5）對任何 surface 都仍然被擋——那是 0-based 誤植的形狀。
ALTER TABLE gsc_daily_metrics
  DROP CONSTRAINT IF EXISTS gsc_daily_metrics_position_ck;

ALTER TABLE gsc_daily_metrics
  ADD CONSTRAINT gsc_daily_metrics_position_ck
  CHECK (
    position >= 1
    OR (position = 0 AND search_type IN ('googleNews', 'discover'))
  );

-- 1c. 更新 catalog 註解
--
-- 015 原註解把 BQ 對照公式 `sum_position = (position-1)*impressions` 寫成無條件成立。
-- 本檔之後不再無條件成立：position=0 代入會得到負值。這件事必須寫進 pg_description，
-- 因為它的受害者是「照著註解寫對照查詢的下一個人」，而錯誤形式是靜默的負數，不會報錯。
COMMENT ON COLUMN gsc_daily_metrics.position IS
  '1-based 加權平均排名。聚合時不可 AVG()，必須 SUM(position*impressions)/SUM(impressions)。'
  '對應 BigQuery searchdata_url_impression.sum_position（0-based 總和）：sum_position = (position-1)*impressions。'
  '⚠ 【例外】search_type 為 googleNews 或 discover 時本欄恆為 0，那是 API 對「這個 surface 沒有排名概念」'
  '的表示法，不是「排第 0 名」，**不可套用上述 BQ 對照公式**（代入會得到負的 sum_position）。'
  '⚠ 【加權平均要連分母一起過濾】視圖 gsc_page_daily / gsc_query_daily 已把這個 0 轉成 NULL，'
  '那讓 AVG(position) 自動略過它們（實測 0 → 1.440、NULL → 2.400），'
  '但**修不掉** SUM(position*impressions)/SUM(impressions)：NULL 只讓分子略過，'
  '分母 SUM(impressions) 照樣把無排名的列算進去，加權平均仍被稀釋（實測兩者同為 2.467，正確值 2.846）。'
  '正確寫法是分子分母都加 FILTER (WHERE position IS NOT NULL)。';


-- ══════════════════════════════════════════════════════════════════════
-- 2. gsc_daily_totals —— 全站總數（與 GSC UI 一致），母體與 gsc_daily_metrics 不同
-- ══════════════════════════════════════════════════════════════════════
--
-- 【資料從哪來 —— 不需要多打任何一次 API】
-- ingest 腳本的 probe_available_dates() 本來就會發一次 `dimensions=["date"]` 的查詢
-- 來探測「哪幾天已經有資料」，而 Search Analytics API 的每一列固定帶
-- clicks / impressions / ctr / position 四個 metric。那個回應**本身就是全站總數**，
-- 現行程式只取了 keys[0]（日期）就把 metric 丟掉。本表要存的就是被丟掉的那部分。
--
-- 【為什麼沒有 reap】
-- 每個 (property, search_type, date) 恰好一列，upsert 天生冪等，
-- 不存在 gsc_daily_metrics 那種「昨天抽樣抽到、今天沒抽到」的殘留列問題。
--
-- 【欄位設計刻意與 gsc_daily_metrics 對齊】
-- 同名同型同語意，讓「總數 vs 抽樣」的對照查詢不需要任何欄位對照表。
-- 但**沒有** page / query / device / country——本表沒有維度，只有日期切面。
-- 少掉那四欄正是「這張表裝的是另一種東西」最直觀的訊號。
CREATE TABLE IF NOT EXISTS gsc_daily_totals (
  date         DATE             NOT NULL,

  -- 值域鎖單值，理由同 015：讓跨 property 重複計算成為無法表示的狀態。
  property     gsc_property     NOT NULL,

  search_type  TEXT             NOT NULL,

  clicks       INTEGER          NOT NULL,
  impressions  INTEGER          NOT NULL,
  ctr          DOUBLE PRECISION NOT NULL,
  position     DOUBLE PRECISION NOT NULL,

  ingested_at  TIMESTAMPTZ      NOT NULL DEFAULT now(),

  -- 冪等 upsert 的衝突鍵。三欄就是本表的全部維度，
  -- 不像 gsc_daily_metrics 的 dim_uniq 需要七欄——這也是母體不同的結構證據。
  CONSTRAINT gsc_daily_totals_uniq UNIQUE (property, search_type, date),

  -- 值域與 gsc_daily_metrics_search_type_ck（本檔 1a 之後的版本）一致。
  -- 兩張表的 surface 值域必須同進退，否則會出現「總數有這個 surface、
  -- 抽樣表裝不下它」的半開狀態——正是 015 對 discover 提出的那個警告。
  CONSTRAINT gsc_daily_totals_search_type_ck
    CHECK (search_type IN ('web', 'image', 'video', 'news', 'googleNews', 'discover')),

  -- 上下界與釘死 UTC 的理由完全同 gsc_daily_metrics_date_ck：
  -- CURRENT_DATE 隨 session TimeZone 擺盪 ±1 天，改用 (now() AT TIME ZONE 'UTC')::DATE。
  CONSTRAINT gsc_daily_totals_date_ck
    CHECK (date BETWEEN DATE '2020-01-01' AND ((now() AT TIME ZONE 'UTC')::DATE + 1)),

  CONSTRAINT gsc_daily_totals_clicks_ck      CHECK (clicks      >= 0),

  -- 與 015 同樣取 `> 0` 而非 `>= 0`：本表的列只會來自探測查詢的回應，
  -- 而 API 只會回「那天有資料」的日期。曝光為 0 的日期根本不會出現在回應裡，
  -- 真的出現就代表 ingest 端造了一列不存在的資料——讓 DB 擋住。
  CONSTRAINT gsc_daily_totals_impressions_ck CHECK (impressions >  0),

  CONSTRAINT gsc_daily_totals_ctr_ck         CHECK (ctr         BETWEEN 0 AND 1),

  -- position 條件式，與本檔 1b 的 gsc_daily_metrics_position_ck 同一套規則。
  CONSTRAINT gsc_daily_totals_position_ck
    CHECK (
      position >= 1
      OR (position = 0 AND search_type IN ('googleNews', 'discover'))
    ),

  CONSTRAINT gsc_daily_totals_clicks_le_impressions_ck
    CHECK (clicks <= impressions),

  -- 對帳約束，抓「clicks 與 impressions 寫反」這種靜默錯誤。
  -- NULLIF 不可省、容差取 1e-4 的完整理由見 015 同名約束的註解
  -- （CHECK 求值順序按 constraint 名稱排序，ctr_consistency 排在 impressions 前面，
  --   沒有 NULLIF 會先噴 division by zero 而蓋掉正確的 constraint 名稱）。
  CONSTRAINT gsc_daily_totals_ctr_consistency_ck
    CHECK (abs(ctr - clicks::DOUBLE PRECISION / NULLIF(impressions, 0)) < 1e-4)
);

-- 唯一的查詢型態就是日期範圍掃描（趨勢圖、覆蓋率分母、新鮮度檢查）。
-- unique constraint 附帶的索引以 (property, search_type) 開頭，
-- 而這兩欄一個恆為單值、一個基數極低，提供不了選擇性——理由同 015 對
-- dim_uniq 的實測結論，那個索引的用途只有 upsert 的衝突偵測。
CREATE INDEX IF NOT EXISTS gsc_daily_totals_date_idx
  ON gsc_daily_totals (date DESC);

-- === RLS：與 013/015/016 完全一致的 default deny ===
--
-- 只 ENABLE，刻意不建立任何面向 anon / authenticated 的 policy。
-- 唯一的 policy 在第 4 節，只給 seo_dashboard_ro、只給 SELECT。
ALTER TABLE gsc_daily_totals ENABLE ROW LEVEL SECURITY;

-- 縱深防禦第一層：撤掉 Supabase 對 public schema 的預設 GRANT。
-- 角色不存在（本機純 postgres）時跳過，與 013/015/016 的 role 判斷同款。
DO $$
DECLARE
  r TEXT;
BEGIN
  FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('REVOKE ALL ON TABLE gsc_daily_totals FROM %I', r);
    END IF;
  END LOOP;
END
$$;

-- 縱深防禦第二層：REVOKE ... FROM <role> 不會撤銷授予 PUBLIC 的權限
-- （那是獨立的 grantee），理由同 015。
REVOKE ALL ON TABLE gsc_daily_totals FROM PUBLIC;

-- === Catalog comments ===
--
-- 「這張表與 gsc_daily_metrics 母體不同、不可相加」是本表最容易被誤讀、
-- 且誤讀後果最嚴重的一件事，所以寫進 pg_description（\d+、Supabase Studio、
-- PostgREST OpenAPI 都看得到），不是只寫在這個檔案的註解裡等人翻。
COMMENT ON TABLE gsc_daily_totals IS
  'Search Analytics API 以 dimensions=[date] 查回的**全站每日總數**，與 GSC UI 上那個數字一致。'
  '⚠ 【母體與 gsc_daily_metrics 不同，兩張表的數字絕對不可相加、不可 UNION】'
  '本表是**全量**（該 property 該 surface 該日的全部點擊與曝光），'
  'gsc_daily_metrics 是**top-N 抽樣**（API 只回 top rows、每天每 surface 上限 50,000 列）。'
  '8/25 實測：抽樣只涵蓋全站 41.7% 的點擊、8.0% 的曝光。'
  '正確用法是把本表當**分母**（覆蓋率 = 抽樣加總 / 本表總數），'
  '任何把兩張表的 clicks 或 impressions 相加的查詢得到的都是假數字，而且不會有錯誤訊號。'
  '每個 (property, search_type, date) 恰一列，upsert 冪等，不需要 reap。'
  '資料來源是 ingest 腳本探測「哪幾天有資料」那一次查詢的回應，不額外消耗 API 配額。';

COMMENT ON COLUMN gsc_daily_totals.position IS
  '該日全站的 1-based 加權平均排名（API 直接給，已對全站加權，不需要也不可以再自行加權）。'
  '⚠ search_type 為 googleNews 或 discover 時恆為 0，代表「這個 surface 沒有排名概念」，'
  '不是「排第 0 名」，不可套用 BigQuery 的 sum_position = (position-1)*impressions 對照公式。';

COMMENT ON COLUMN gsc_daily_totals.search_type IS
  'Search Analytics API `type` 參數的原值。值域與 gsc_daily_metrics_search_type_ck 一致，'
  '兩張表必須同進退：只有一邊收了某個 surface，就會出現「總數有它、抽樣表裝不下它」的半開狀態。';


-- ══════════════════════════════════════════════════════════════════════
-- 3. 兩個組合視圖 —— position 的 0 在視圖層變成 NULL
-- ══════════════════════════════════════════════════════════════════════
--
-- 【只換一個運算式，欄位名與順序逐字照抄 016】
-- CREATE OR REPLACE VIEW 要求新定義的欄位名稱、順序、型別與舊定義完全一致，
-- 任何一項不同都會直接 ERROR（而不是替換）。所以下面兩個 SELECT 清單是從
-- 016 原文複製的，唯一的改動是 position 那一欄外面包了 NULLIF。
-- NULLIF(position, 0::DOUBLE PRECISION) 的型別仍是 double precision，
-- `AS position` 保住欄位名——018 對這兩個 view 的 GRANT 與第 4 節的 policy 都不受影響。
--
-- 【為什麼要轉 NULL —— 以及它修不掉什麼，這半段更重要】
-- 沒有排名的東西不應該有平均排名。0 進得了聚合的分子，NULL 進不了。
-- 本機 postgres:17 實測（測資：web 3.2@100 曝光、news 1.0@20、web 3.0@10、
-- googleNews 0@10、discover 0@10）：
--
--   AVG(position)   底表原值 0 → 1.440（假的「排名很好」）
--                   視圖 NULL  → 2.400（只算有排名的三列，正確）
--     ✅ NULL 修好了這一種。
--
--   SUM(position*impressions)/SUM(impressions)
--                   底表原值 0 → 2.467
--                   視圖 NULL  → 2.467（**一模一樣，NULL 沒有修好**）
--     ❌ 因為 NULL 只讓分子略過那些列，**分母 SUM(impressions) 照樣把它們算進去**，
--        加權平均仍被稀釋。正確寫法必須把分母一起過濾：
--
--          SUM(position * impressions) FILTER (WHERE position IS NOT NULL)
--          / SUM(impressions)          FILTER (WHERE position IS NOT NULL)
--
--        同一組測資這樣寫得到 2.846，才是「只看有排名那些列」的加權平均。
--
-- 寫在這裡是因為 015 的 catalog 註解要求「聚合必須用 impressions 加權」，
-- 照著那句話寫的人會直接踩進上面那個 ❌——而它不會報錯，只會給一個偏低的數字。
-- 轉 NULL 的真正價值是：**讓踩進去的人至少在原始欄位上看得見 NULL**，
-- 而不是看見一個長得很像排名的 0。它是訊號，不是保護。
--
-- 【對既有 surface 是 no-op】web / image / video / news 的 position 全部 >= 1
-- （position_ck 保證），NULLIF 對它們永遠不會命中，一列都不會變。
--
-- 【security_invoker = true 不可省】理由見 016 完整論證：預設的 view 是
-- security definer 語意，會繞過底表的 RLS default deny。這裡照抄不改。

CREATE OR REPLACE VIEW gsc_page_daily
  WITH (security_invoker = true) AS
SELECT
  date, property, search_type, page, device,
  clicks, impressions, ctr, NULLIF(position, 0::DOUBLE PRECISION) AS position, ingested_at
FROM gsc_daily_metrics
WHERE page <> gsc_page_not_requested();

COMMENT ON VIEW gsc_page_daily IS
  'GSC Search Analytics 以 (date, page, device) 為維度的逐日抽樣資料。'
  '【務必先讀】底表 gsc_daily_metrics 同時裝著另一組以 (date, query, device) 為維度的列，'
  '兩組是同一批點擊的兩個邊際聚合；直接對底表 SUM(clicks) 會得到約兩倍的假數字，'
  '且不會有任何錯誤訊號。本 view 已寫死判別式，照這裡查不會重複計算。'
  '【資料是抽樣不是全量】API 只回 top rows 且每天每 property 每 search type 上限 50,000 列，'
  '所以 SUM(clicks) 必然小於 GSC UI 上的總點擊，差額大小不可知'
  '（全站總數請查 gsc_daily_totals，⚠ 兩者母體不同、不可相加）。'
  '本 view 每日約 28,000 列（未貼上限），截斷程度低於 gsc_query_daily。'
  '【position 可能是 NULL】googleNews / discover 沒有排名概念，底表存 API 原值 0，本 view 轉成 NULL。'
  '⚠ 這讓 AVG(position) 正確，但**修不掉**加權平均：SUM(position*impressions)/SUM(impressions) 的'
  '分母仍會把無排名的列算進去，得到偏低的假排名。分子分母都要加 FILTER (WHERE position IS NOT NULL)。';

CREATE OR REPLACE VIEW gsc_query_daily
  WITH (security_invoker = true) AS
SELECT
  date, property, search_type, query, device,
  clicks, impressions, ctr, NULLIF(position, 0::DOUBLE PRECISION) AS position, ingested_at
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
  '而 index bloat / thin content 這類需要看長尾的分析，缺的正是被截掉的那部分。'
  '【position 可能是 NULL】googleNews / discover 沒有排名概念，底表存 API 原值 0，本 view 轉成 NULL；'
  '不過這兩個 surface 不支援 query 維度（API 回 400），實務上不會出現在本 view。';


-- ══════════════════════════════════════════════════════════════════════
-- 4. seo_dashboard_ro 對 gsc_daily_totals 的讀取權
-- ══════════════════════════════════════════════════════════════════════
--
-- 【為什麼在這一支，不是另開一支】
-- 019 定下的原則：「授予讀取權的動作應該和產生資料的那一步在同一個變更裡」，
-- 否則就是超前授權，變成「沒人記得為什麼存在的授權」。
-- 本表的 ingestion（S2.2 的 write_totals）與本檔是同一次交付，
-- Grafana 的覆蓋率面板（S3.1 的 panel 12）直接查它——授權在這裡有完整上下文。
--
-- 【兩件事缺一不可】本表是 ENABLE RLS + 零 policy 的 default deny，
-- 只 GRANT 不加 policy 的話這個角色一列都讀不到，而且會回 HTTP 200 + 空陣列、
-- 不會報錯——018 說的「最難察覺的失敗形狀」。所以 GRANT 與 policy 兩件都要做。
--
-- 【逐物件列名，不用 ALL TABLES】理由見 018：ALL TABLES 會讓之後任何人新建的表
-- 自動落進這個角色的讀取範圍，而那個人不會知道。逐物件列名讓「新增曝光」
-- 永遠是一個要動 migration 的動作。
--
-- 【USING (true)】本表沒有租戶維度，範圍寫在 GRANT 的物件清單上（只有這一張表），
-- 不需要在 policy 述詞上再裁切——與 018/020 對其餘表的處理一致。

GRANT SELECT ON TABLE gsc_daily_totals TO seo_dashboard_ro;

DROP POLICY IF EXISTS seo_dashboard_ro_select ON gsc_daily_totals;
CREATE POLICY seo_dashboard_ro_select ON gsc_daily_totals
  FOR SELECT TO seo_dashboard_ro USING (true);


-- ══════════════════════════════════════════════════════════════════════
-- === 套用後應成立的狀態 ===
-- ══════════════════════════════════════════════════════════════════════
--
-- CHECK 定義（pg_get_constraintdef 讀回）：
--   gsc_daily_metrics_search_type_ck
--     → CHECK (search_type = ANY (ARRAY['web','image','video','news','googleNews','discover']))
--   gsc_daily_metrics_position_ck
--     → CHECK ("position" >= 1::double precision
--              OR ("position" = 0::double precision
--                  AND search_type = ANY (ARRAY['googleNews','discover'])))
--
-- 寫入行為（四組測資）：
--   INSERT search_type='web',        position=0   → 被 gsc_daily_metrics_position_ck 擋下
--   INSERT search_type='googleNews', position=0   → 成功
--   INSERT search_type='discover',   position=0   → 成功（同時證明 search_type_ck 已放寬）
--   INSERT search_type='web',        position=3   → 成功（既有路徑無回歸）
--   INSERT search_type='googleNews', position=0.5 → 仍被擋下（0-based 誤植的形狀）
--
-- 視圖：
--   gsc_page_daily / gsc_query_daily 的欄位名與順序與 016 完全相同
--   （date, property, search_type, page|query, device, clicks, impressions, ctr, position, ingested_at）
--   對 googleNews / discover 的列 position 回 NULL；對 web 的列回原值。
--   reloptions 仍含 security_invoker=true。
--
-- 新表：
--   gsc_daily_totals 存在，relrowsecurity = true，pg_policies 對它恰一條
--     （seo_dashboard_ro_select，cmd=SELECT，roles={seo_dashboard_ro}）。
--   同一組 (property, search_type, date) 連續 upsert 兩次 → 表內仍只有一列，
--     且第二次的值覆蓋第一次（ON CONFLICT ... DO UPDATE）。
--
-- 權限（開了一道窄門，不是把門拆了——018/019/020 沿用的驗收方式）：
--   has_table_privilege('seo_dashboard_ro','gsc_daily_totals','SELECT') → true
--   has_table_privilege('seo_dashboard_ro','seo_change_log','SELECT')   → false（不變）
--   has_table_privilege('seo_dashboard_ro','meeting_prep','SELECT')     → false（不變）
--   has_table_privilege('seo_dashboard_ro','qa_items','SELECT')         → false（不變）
--   information_schema.role_table_grants where grantee='seo_dashboard_ro'
--     → 020 收尾時的 7 列 + 本檔新增的 gsc_daily_totals，共 8 列，全部是 SELECT。
--
-- 既有資料：
--   gsc_daily_metrics 的列數在套用前後完全相同（本檔不寫入、不刪除任何一列）。
