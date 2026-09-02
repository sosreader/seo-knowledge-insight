-- 020_gsc_url_inspection_dashboard_grant.sql
-- 補回 gsc_url_inspection 對 seo_dashboard_ro 的讀取權（S3.4 交付：URL Inspection 抽樣管線）
--
-- 【編號】新增前已現場 `ls supabase/migrations/` 確認：現況最大為 019，本檔為 020。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【為什麼是這裡，不是 018】
-- ══════════════════════════════════════════════════════════════════════
--
-- 019 收回了 018 對 gsc_url_inspection 的超前授權，理由是「S3.4 還沒做，表是空的，
-- 儀表板現在沒有任何 panel 會查它」，並在檔尾明講：
--
--     「S3.4 實作 URL Inspection 管線時，在該 step 自己的 migration 裡重新加上
--       gsc_url_inspection 的 GRANT SELECT + policy——連同它的資料一起交付。」
--
-- 本檔就是那個交付。S3.4（scripts/ingest_gsc_url_inspection.py）現在會把資料寫進
-- gsc_url_inspection，「為什麼需要這個授權」在這個 commit 裡有完整上下文——
-- 這正是 019 想避免的「沒人記得為什麼存在的授權」該有的落點。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【做什麼 —— 兩件事，缺一不可】
-- ══════════════════════════════════════════════════════════════════════
--
-- gsc_url_inspection 與 013/015/016 同一套安全模型：ENABLE RLS + 零 policy（default
-- deny）+ REVOKE ALL FROM anon/authenticated/PUBLIC。只 GRANT SELECT 而不加 policy，
-- 這個角色一列都讀不到——會回 HTTP 200 + 空陣列，不會報錯，是最難察覺的失敗形狀
-- （018 的原話）。所以兩件事都要做：
--
--   1. GRANT SELECT ON TABLE gsc_url_inspection TO seo_dashboard_ro
--   2. 一條 FOR SELECT TO seo_dashboard_ro USING (true) 的 RLS policy
--
-- USING (true)：這張表沒有租戶維度，範圍已經寫在 GRANT 的物件清單上（只有這一張表），
-- 不需要在 policy 述詞上再裁切——與 018 對其餘表的處理一致。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【冪等性】
-- ══════════════════════════════════════════════════════════════════════
--
-- GRANT 本身冪等，重複授予不報錯。
-- CREATE POLICY 沒有 IF NOT EXISTS → 用 DROP POLICY IF EXISTS 前置。
--   （019 的註解已提醒過：PostgreSQL 的 ALTER POLICY 沒有 IF EXISTS，
--     但 DROP POLICY IF EXISTS 有，drop-then-create 組合安全，可重跑任意次。）

GRANT SELECT ON TABLE gsc_url_inspection TO seo_dashboard_ro;

DROP POLICY IF EXISTS seo_dashboard_ro_select ON gsc_url_inspection;
CREATE POLICY seo_dashboard_ro_select ON gsc_url_inspection
  FOR SELECT TO seo_dashboard_ro USING (true);

-- === 套用後應成立的狀態 ===
--
--   has_table_privilege('seo_dashboard_ro', 'gsc_url_inspection', 'SELECT') → true
--   has_table_privilege('seo_dashboard_ro', 'qa_items', 'SELECT')           → false（不變）
--   information_schema.role_table_grants where grantee='seo_dashboard_ro'
--     → 019 收尾時的 6 列 + 本檔新增的 gsc_url_inspection，共 7 列，全部是 SELECT。
--
-- 第二條與第一條同樣重要：只驗「想開的開了」無法區分「開了一道窄門」與「把門全拆了」
-- ——這條規則抄自 018/019，本檔沿用同一份驗收方式。
