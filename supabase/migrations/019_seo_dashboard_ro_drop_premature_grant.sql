-- 019_seo_dashboard_ro_drop_premature_grant.sql
-- 收回 018 對 gsc_url_inspection 的超前授權 + 把角色改為 NOINHERIT
--
-- 【編號】新增前已現場 `ls supabase/migrations/` 確認：現況最大為 018，本檔為 019。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【為什麼要收回 gsc_url_inspection —— 我在 018 違反了自己寫的原則】
-- ══════════════════════════════════════════════════════════════════════
--
-- 018 對 5 張表 + 2 個 view 授予 SELECT，其中 gsc_url_inspection 是
-- **超前授權**：那張表由 S3.4（URL Inspection API 抽樣管線）產生資料，
-- 而 S3.4 還沒做，表是空的，儀表板現在沒有任何 panel 會查它。
--
-- 018 自己的註解裡寫了這段話：
--
--     「刻意不用 GRANT ... ON ALL TABLES IN SCHEMA public——用了的話，
--       之後任何人新建的表都會自動落進這個角色的讀取範圍，而那個人
--       不會知道有這件事。逐物件列名讓『新增曝光』永遠是一個要動這個
--       檔的動作。」
--
-- 那條原則的內核是「**權限跟著需求走，不跟著預期走**」。而我在同一個檔案裡
-- 對一張還沒有需求的表授了權——用逐物件列名的形式犯了 ALL TABLES 的錯誤：
-- 少了一個「這張表現在被誰用？」的檢查點。
--
-- 差別看起來很小（一張空表），但**正確的落點不是這裡**：授予讀取權的動作
-- 應該和產生資料的那一步在同一個變更裡。S3.4 建立 ingestion 管線時，
-- 一併在它自己的 migration 加這一行，那時「為什麼需要這個授權」有上下文；
-- 放在 018 就只是一個沒人記得為什麼存在的授權。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【為什麼加 NOINHERIT】
-- ══════════════════════════════════════════════════════════════════════
--
-- 2026-09-02 稽核結果：這個角色目前不是任何角色的成員（pg_auth_members 查無），
-- 所以 INHERIT 與否當下沒有差別。加 NOINHERIT 是針對未來：
--
--   若之後有人執行 `GRANT some_other_role TO seo_dashboard_ro`，
--   INHERIT 會讓它**立即自動獲得**該角色的全部權限，不需要任何額外動作；
--   NOINHERIT 則要求顯式 SET ROLE 才拿得到。
--
-- 這與上面那條原則同源：讓擴權變成需要顯式決定的事，而不是自動發生的事。
-- PostgREST 是以 authenticator `SET ROLE` 切進本角色，本角色自己不需要
-- 從別處繼承任何東西，所以 NOINHERIT 不影響現有用途。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【冪等性】REVOKE / DROP POLICY IF EXISTS / ALTER ROLE 皆可重跑。

-- === 1. 收回超前授權 ===

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'seo_dashboard_ro') THEN
    EXECUTE 'REVOKE ALL ON TABLE gsc_url_inspection FROM seo_dashboard_ro';
  END IF;
END
$$;

-- policy 一併移除。留著一條指向沒有 SELECT 權限的角色的 policy，
-- 會讓之後讀 pg_policies 的人以為那張表是開放的——policy 存在但 GRANT 不存在
-- 的組合讀起來像「開放了但壞掉」，而實際上是「刻意沒開放」。
-- 兩層要一致，否則下一個人得同時查兩個地方才知道真相。
DROP POLICY IF EXISTS seo_dashboard_ro_select ON gsc_url_inspection;

-- === 2. NOINHERIT ===

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'seo_dashboard_ro') THEN
    EXECUTE 'ALTER ROLE seo_dashboard_ro NOINHERIT';
  END IF;
END
$$;

-- === 3. 套用後應成立的狀態 ===
--
--   information_schema.role_table_grants where grantee='seo_dashboard_ro'
--     → 恰好 6 列，全部是 SELECT：
--       cwv_hourly / crawl_daily / gsc_daily_metrics / ingestion_run
--       / gsc_page_daily / gsc_query_daily
--   has_table_privilege('seo_dashboard_ro','gsc_url_inspection','SELECT') → false
--   pg_roles.rolinherit for seo_dashboard_ro → false
--
-- S3.4 實作 URL Inspection 管線時，在該 step 自己的 migration 裡重新加上
-- gsc_url_inspection 的 GRANT SELECT + policy——連同它的資料一起交付。
