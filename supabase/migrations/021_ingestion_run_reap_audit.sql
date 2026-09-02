-- 021_ingestion_run_reap_audit.sql
-- 為 ingestion_run 補上「reap（回收殘留 running 列）」的稽核欄位（S3.5 資料品質 gate 統一）
--
-- 【編號】新增前已現場 `ls supabase/migrations/` 確認：現況最大為 020，本檔為 021。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【為什麼需要這個】
-- ══════════════════════════════════════════════════════════════════════
--
-- S3.5 實測發現 3 筆殘留的 status='running' 紀錄（作業死掉沒收尾），最舊的
-- started_at 超過 30 小時未收尾。這種列讓「有沒有作業卡住」變成不可偵測，
-- 也污染以 ingestion_run 為基礎的統計（例如 013 建的新鮮度查詢索引，見該檔
-- 「典型查詢」註解——running 列的 finished_at 恆為 NULL，混進 MAX(finished_at)
-- 會被正確排除，但混進「這條管線最近一次 run 是什麼狀態」這類查詢時不會）。
--
-- 統一資料品質 gate（scripts/data_quality_gate.py）需要一個「把死掉的 running
-- 列標記成 failed」的動作，但這是全計畫唯一會寫 production 資料的檢查路徑
-- （其餘一律唯讀），所以這個寫入動作本身必須可稽核：誰改的、什麼時候改的、
-- 為什麼改。目前的 schema 沒有任何欄位能承載這件事——PATCH status 只會覆寫
-- 掉「這列曾經是 running」的痕跡，事後無法區分「作業自己回報 failed」與
-- 「gate 判定它死了才代填 failed」。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【做什麼】
-- ══════════════════════════════════════════════════════════════════════
--
-- 新增三個欄位，全部 nullable（一般 ingest 腳本的 start_run/finish_run 完全不
-- 帶這三欄，維持原本的寫入路徑不變）：
--
--   reaped_at    — gate 執行 reap 動作的時間戳
--   reaped_by    — 執行者標識（例如 'data_quality_gate.py --reap-stale-running'，
--                  不是人名——這是自動化動作，「誰改的」指的是哪個工具/哪次呼叫）
--   reap_reason  — 人類可讀的原因，含判定當下的 age_hours 與門檻，供事後回查
--
-- 三欄綁一條 CHECK：要嘛全 NULL（一般 run，從未被 reap 過），要嘛全非 NULL
-- （被 reap 過，且三個稽核欄位缺一不可）——不允許「reaped_at 有值但沒寫原因」
-- 這種半稽核狀態。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【冪等性】
-- ══════════════════════════════════════════════════════════════════════
--
-- ADD COLUMN IF NOT EXISTS 本身冪等。
-- PostgreSQL 的 ADD CONSTRAINT 不支援 IF NOT EXISTS（019/020 已提醒過這件事，
-- 那兩檔踩的是 ALTER POLICY 沒有 IF EXISTS；本檔是同一個坑的 CHECK 版本）——
-- 用 DROP CONSTRAINT IF EXISTS 前置，drop-then-add 組合可安全重跑任意次。

ALTER TABLE ingestion_run
  ADD COLUMN IF NOT EXISTS reaped_at   TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS reaped_by   TEXT,
  ADD COLUMN IF NOT EXISTS reap_reason TEXT;

ALTER TABLE ingestion_run
  DROP CONSTRAINT IF EXISTS ingestion_run_reap_audit_ck;

ALTER TABLE ingestion_run
  ADD CONSTRAINT ingestion_run_reap_audit_ck
  CHECK (
    (reaped_at IS NULL AND reaped_by IS NULL AND reap_reason IS NULL)
    OR (reaped_at IS NOT NULL AND reaped_by IS NOT NULL AND reap_reason IS NOT NULL)
  );

-- === 套用後應成立的狀態 ===
--
--   information_schema.columns 對 ingestion_run 多出 reaped_at / reaped_by /
--     reap_reason 三欄，皆 nullable。
--   既有列（reap 前寫入的所有列）三欄皆為 NULL，不違反新 CHECK。
--   對 status='running' 且已死掉的列執行
--     PATCH .../ingestion_run?id=eq.<id>
--     { status: 'failed', finished_at: <now>, reaped_at: <now>,
--       reaped_by: 'data_quality_gate.py', reap_reason: '<原因含 age_hours>' }
--   → 成功；若只給 reaped_at 不給另外兩欄 → CHECK 擋下，回 400。
