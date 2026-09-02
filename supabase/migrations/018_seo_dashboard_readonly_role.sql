-- 018_seo_dashboard_readonly_role.sql
-- 為 Grafana 儀表板開一個唯讀角色 seo_dashboard_ro，讓倉儲資料看得到
--
-- 【編號】新增前已現場 `ls supabase/migrations/` 確認：現況最大為 017，本檔為 018。
-- （013 註解記過一次同編號相撞 `duplicate key ... Key (version)=(012)` 的事故，
--   「往上加 1」不是可靠做法，必須先列目錄。）
--
-- ══════════════════════════════════════════════════════════════════════
-- 【這個檔在做什麼 —— 它明確地縮小 013/015/016 的 default deny】
-- ══════════════════════════════════════════════════════════════════════
--
-- 013 / 015 / 016 對倉儲物件建立了一致且刻意的安全模型，三層：
--
--   (1) ENABLE ROW LEVEL SECURITY 且**不建立任何 policy** → default deny
--   (2) REVOKE ALL ... FROM anon, authenticated                → 縱深防禦第一層
--   (3) REVOKE ALL ... FROM PUBLIC                             → 縱深防禦第二層
--
-- 013 第 651 行與 015 第 651 行都寫了同一句話：
--
--     「之後若要開放前端直讀，必須另開 migration 明確加 policy，不能靠預設。」
--
-- 本檔就是那個 migration。它**不推翻**上面的模型，而是在它旁邊開一道
-- 只通往「唯讀 + 指定物件 + 指定角色」的窄門。anon 與 authenticated
-- 的權限本檔一個字都不動，(2) 與 (3) 兩層原封不動保留。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【為什麼不直接開放 anon —— 這是本檔存在的唯一理由，實測過才這樣決定】
-- ══════════════════════════════════════════════════════════════════════
--
-- 最省事的做法是 `GRANT SELECT ... TO anon` + 對 anon 加 policy，
-- 然後把 anon key 貼進 Grafana 的 datasource 設定。**不可以這樣做。**
--
-- 2026-09-02 用 anon key 實測本專案其他資料表，它讀得到：
--
--   qa_items        32,439 列   ← 整個知識庫語料
--   meeting_prep        36 列   ← 兩年 SEO 顧問會議紀錄
--   sessions            21 列
--   learnings            3 列
--
-- 而 004 / 005 / 006 另外給了 anon 對 sessions / learnings / synonym_custom
-- 的 INSERT / UPDATE / DELETE。也就是說——
--
--     **本專案的 anon key 不是唯讀金鑰，它是一把有寫入權的中權限金鑰。**
--
-- Grafana 是跨團隊共用的基礎設施。把 anon key 放進去，等於讓每一個看得到
-- 那個 datasource 設定的人都拿到上述全部讀取權與部分寫入權。倉儲資料本身
-- （彙總後的 SEO 指標，無 PII）給團隊看是合理的；連帶送出會議紀錄與寫入權
-- 不是。兩者用同一把金鑰就無法分開，所以必須另開角色。
--
-- 判準留給之後的人：**要把某把金鑰放進一個更多人看得到的地方之前，
-- 先實測那把金鑰在「這次要開放的資源」之外還碰得到什麼。**
-- 金鑰的名字（anon / public / readonly）描述的是它被設計時的意圖，
-- 不是它在這個 schema 累積了三年之後的實際權限。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【怎麼用 —— PostgREST 的角色切換機制】
-- ══════════════════════════════════════════════════════════════════════
--
-- PostgREST 以 `authenticator` 連線，再依 JWT 的 `role` claim 執行
-- `SET LOCAL ROLE <role>`。所以要讓這個角色能被用到，需要兩件事：
--
--   1. 這個角色存在，且 authenticator 被 GRANT 了它（本檔負責）
--   2. 一枚 `{"role":"seo_dashboard_ro", "iss":"supabase", ...}` 的 JWT，
--      用專案的 JWT secret 以 HS256 簽出（本檔不負責，也不該負責——
--      migration 不碰密鑰）
--
-- 專案現況為 legacy 對稱簽章（2026-09-02 實測 anon key：alg=HS256、
-- iss=supabase、role=anon），所以自簽 custom role JWT 這條路可用。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【刻意不開放的東西】
-- ══════════════════════════════════════════════════════════════════════
--
--   seo_change_log  —— 資料性質與其他倉儲表同級（無 PII），但儀表板現在
--                      不需要它。Phase 5 要把變更點畫成 Grafana annotation
--                      時再另開 migration 加一行 GRANT + 一條 policy。
--                      窄門開太寬就不是窄門。
--
--   任何 INSERT / UPDATE / DELETE —— 本角色只有 SELECT。儀表板不寫資料。
--
--   GRANT ... ON ALL TABLES IN SCHEMA public —— 刻意逐物件列名。
--                      用 ALL TABLES 的話，**之後任何人新建的表都會自動
--                      落進這個角色的讀取範圍**，而那個人不會知道有這件事。
--                      逐物件列名讓「新增曝光」永遠是一個要動這個檔的動作。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【冪等性】
-- ══════════════════════════════════════════════════════════════════════
--
-- CREATE ROLE 沒有 IF NOT EXISTS → 包在 DO block 裡查 pg_roles。
-- CREATE POLICY 沒有 IF NOT EXISTS → 用 DROP POLICY IF EXISTS 前置。
--   （注意：013 註解警告的是 **ALTER** POLICY 沒有 IF EXISTS；
--     DROP POLICY IF EXISTS 是有的，所以 drop-then-create 這個組合安全。）
-- GRANT 本身冪等，重複授予不報錯。
-- 本檔可重跑任意次。

-- === 1. 角色本體 ===
--
-- NOLOGIN：這個角色永遠不會被直接連線，只會被 PostgREST 以 SET ROLE 切進去。
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'seo_dashboard_ro') THEN
    CREATE ROLE seo_dashboard_ro NOLOGIN;
  END IF;
END
$$;

-- authenticator 要能 SET ROLE 進去，必須先被 GRANT 這個角色。
-- 本機純 postgres 環境沒有 authenticator，跳過（與 013/015 的 role 判斷同款）。
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticator') THEN
    EXECUTE 'GRANT seo_dashboard_ro TO authenticator';
  END IF;
END
$$;

-- === 2. schema 與物件層權限（逐物件列名，不用 ALL TABLES）===

GRANT USAGE ON SCHEMA public TO seo_dashboard_ro;

-- 事實表
GRANT SELECT ON TABLE
  cwv_hourly,
  crawl_daily,
  gsc_daily_metrics,
  gsc_url_inspection
TO seo_dashboard_ro;

-- ingestion_run：資料新鮮度面板的查詢對象。
-- 這張表就是 S3.5「新鮮度告警」的權威來源，儀表板要能顯示「最後一次成功寫入
-- 是什麼時候」，所以它與事實表一樣必須可讀——**看不到它，就看不出管線停了。**
GRANT SELECT ON TABLE ingestion_run TO seo_dashboard_ro;

-- 016 的兩個組合視圖。
-- 它們是 WITH (security_invoker = true)，即以**查詢者**的身分套用底表 RLS，
-- 所以除了這裡的 view 權限，底表 gsc_daily_metrics 的 SELECT 與 policy
-- 兩者缺一不可（上面已給 SELECT，下面第 3 節給 policy）。
GRANT SELECT ON TABLE
  gsc_page_daily,
  gsc_query_daily
TO seo_dashboard_ro;

-- === 3. RLS policy —— 只給 SELECT，只給這個角色 ===
--
-- 底表都是 ENABLE RLS + 零 policy 的 default deny，光有 GRANT 讀不到任何一列
-- （會回 HTTP 200 + 空陣列，不會報錯——這正是最難察覺的失敗形狀）。
-- 所以每張底表都要有一條對應的 policy。
--
-- USING (true)：本角色看得到該表的全部列。這些表沒有租戶維度，
-- 沒有需要逐列裁切的東西；把範圍寫在 GRANT 的物件清單上（哪些表）
-- 而不是 policy 的述詞上（哪些列），是這裡正確的切法。

DROP POLICY IF EXISTS seo_dashboard_ro_select ON cwv_hourly;
CREATE POLICY seo_dashboard_ro_select ON cwv_hourly
  FOR SELECT TO seo_dashboard_ro USING (true);

DROP POLICY IF EXISTS seo_dashboard_ro_select ON crawl_daily;
CREATE POLICY seo_dashboard_ro_select ON crawl_daily
  FOR SELECT TO seo_dashboard_ro USING (true);

DROP POLICY IF EXISTS seo_dashboard_ro_select ON gsc_daily_metrics;
CREATE POLICY seo_dashboard_ro_select ON gsc_daily_metrics
  FOR SELECT TO seo_dashboard_ro USING (true);

DROP POLICY IF EXISTS seo_dashboard_ro_select ON gsc_url_inspection;
CREATE POLICY seo_dashboard_ro_select ON gsc_url_inspection
  FOR SELECT TO seo_dashboard_ro USING (true);

DROP POLICY IF EXISTS seo_dashboard_ro_select ON ingestion_run;
CREATE POLICY seo_dashboard_ro_select ON ingestion_run
  FOR SELECT TO seo_dashboard_ro USING (true);

-- === 4. 明確不動的東西（寫下來，避免之後有人以為是漏的）===
--
-- 不對 anon / authenticated 做任何 GRANT 或 REVOKE。
-- 不對 seo_change_log 開放。
-- 不建立任何 INSERT / UPDATE / DELETE policy。
-- 013 / 015 / 016 的三層 default deny 對 anon / authenticated / PUBLIC 完全保留。
--
-- 驗收方式（套用後應得到的結果）：
--   以 seo_dashboard_ro 的 JWT 打 /rest/v1/cwv_hourly?select=*&limit=1  → 200 有列
--   以 seo_dashboard_ro 的 JWT 打 /rest/v1/qa_items?select=*&limit=1    → 401/42501
--   以 anon              的 JWT 打 /rest/v1/cwv_hourly?select=*&limit=1 → 401/42501（不變）
--
-- 第二與第三條和第一條同樣重要：只驗「想開的開了」而不驗「沒想開的仍然關著」，
-- 就無法區分「開了一道窄門」與「把門全拆了」。
