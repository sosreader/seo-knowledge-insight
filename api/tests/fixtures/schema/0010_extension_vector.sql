-- run-as: master
-- 0010_extension_vector.sql
-- 啟用 pgvector extension（ski-rag-into-vocus-warehouse 子計畫 S1.3；RAG 向量表的前置）。
--
-- 為什麼獨立一號：CREATE EXTENSION 需要 rds_superuser 權限，warehouse_admin 沒有（見 docs/runbook-migrate.md
--   「何時用 run-as: master」）。把 extension 與之後的向量表拆開，向量表的 migration 就能用預設的
--   warehouse_admin 身分，物件 owner 自然是 admin；extension 本身由 master 擁有，和 0005 的 pg_cron 同。
--
-- 版本需求：RAG 要用 halfvec 型別與 halfvec 的 hnsw／ivfflat opclass，pgvector 需 >= 0.7.0。
--   目標版本 0.8.2（RDS PostgreSQL 17 提供的版本以 pg_available_extensions 為準，S1.3 前置探針
--   已查過）。本檔套用後若 extversion < 0.7.0 就整檔中止，避免後續向量表 migration 才發現型別不存在。
--
-- 執行身分：`-- run-as: master`（runner 不切 role）。以 RDS master `warehouse_master`
--   （rds_superuser 成員，非 superuser）執行，`schema_migrations.applied_by` 為 warehouse_master。
--
-- 物件：extension vector（裝在 public schema；vector／halfvec 型別、運算子與 opclass 隨之出現）。
--   不建任何表、不 GRANT：extension 的型別與函式預設對 PUBLIC 可用，warehouse_admin 之後建 halfvec 欄位
--   與 hnsw index 不需要額外授權。各角色對向量表的權限由向量表自己的 migration 負責。
--
-- 冪等：`CREATE EXTENSION IF NOT EXISTS`。重跑不改版本；要升級 extension 版本請另開 migration
--   （`ALTER EXTENSION vector UPDATE`），不要改這個已套用的檔。
--
-- 測試容器逃生口：沒有 pgvector 的環境（一般 postgres:17 測試容器）上，只有資料庫層級設定
--   `vw.allow_missing_vector = on` 時才略過 extension 與版本檢查。正式環境沒有設定，
--   pgvector 不可用就整檔中止，不會靜默略過。

DO $do$
BEGIN
  IF current_user <> session_user THEN
    RAISE EXCEPTION '0010 必須以 master 本人執行（run-as: master），目前 current_user % 與 session_user % 不同',
      current_user, session_user;
  END IF;
END
$do$;


-- ======================================================================
-- 1. extension
-- ======================================================================

DO $do$
DECLARE
  v_version text;
BEGIN
  IF EXISTS (SELECT FROM pg_catalog.pg_available_extensions WHERE name = 'vector') THEN
    CREATE EXTENSION IF NOT EXISTS vector;
    SELECT extversion INTO v_version FROM pg_catalog.pg_extension WHERE extname = 'vector';
    IF string_to_array(v_version, '.')::int[] < ARRAY[0, 7, 0] THEN
      RAISE EXCEPTION 'pgvector 版本 % 低於 0.7.0，沒有 halfvec；先 ALTER EXTENSION vector UPDATE（另開 migration）', v_version;
    END IF;
  ELSIF coalesce(current_setting('vw.allow_missing_vector', true), '') = 'on' THEN
    RAISE NOTICE 'pgvector 不可用且 vw.allow_missing_vector = on：略過 extension（僅限測試容器）';
  ELSE
    RAISE EXCEPTION 'pgvector 不可用：RDS 需先確認 pg_available_extensions 含 vector（PostgreSQL 17 引擎版本是否提供）';
  END IF;
END
$do$;
