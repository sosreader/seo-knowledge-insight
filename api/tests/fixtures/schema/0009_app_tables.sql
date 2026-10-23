-- 0009_app_tables.sql
-- SKI（seo-knowledge-insight）應用表：app_report、app_meeting_prep、app_session，與寫入角色 warehouse_app 的表級 GRANT
-- （KB plan ski-supabase-decoupling-sync-db-to-warehouse.md S1.1）。
--
-- 背景：
--   SKI 的 `/sync-db` 目前把 reports、meeting_prep、sessions 三張表寫進 Supabase。plan 裁決改由 warehouse-api 的
--   寫入 endpoint（S1.3）推進本倉儲，本檔先開出三張承接表。表名加 app_ 前綴，和倉儲的 SEO 事實表區隔。
--
-- 欄位來源（SKI origin/main 367d222，每欄的檔案:行寫在 COMMENT ON COLUMN）：
--   app_report       ← Supabase `reports`。Supabase 端沒有任何 CREATE TABLE reports（不在 supabase/migrations/），
--                      欄位只能從寫入／讀取程式碼反推：api/src/store/supabase-report-store.ts 的 save()（實際寫入欄位）、
--                      ReportRow 介面（讀回欄位）、0121_soft_delete.sql（deleted_at）。
--   app_meeting_prep ← Supabase `meeting_prep`（012_meeting_prep_table.sql 有 CREATE），對照 supabase-meeting-prep-store.ts save()。
--   app_session      ← Supabase `sessions`（004_sessions_table.sql、009 加 metadata、0121 加 deleted_at），
--                      對照 api/src/sync/session-sync.ts 與 supabase-session-store.ts。
--   刻意不搬的欄位：reports.id（ReportRow 的 number 代理鍵，SKI 從不寫入、也不以它查詢或 upsert；冪等鍵是 date_key）。
--
-- 鍵（依 SKI 程式碼實際的 upsert onConflict 欄位命名，不另取 report_id 之類的新名）：
--   app_report.date_key        PRIMARY KEY（supabase-report-store.ts save() onConflict: "date_key"）
--   app_meeting_prep.date_key  PRIMARY KEY（012 PRIMARY KEY；save() onConflict: "date_key"）
--   app_session.id             PRIMARY KEY uuid DEFAULT gen_random_uuid()（session-sync.ts onConflict: "id"；
--                              createSession() 不帶 id，靠 DB 預設產生）
--   date_key 不加格式 CHECK：SKI 的 reports 檔名鍵（YYYYMMDD 或 YYYYMMDD_hash8）只在 meeting-prep store 驗格式，
--   歷史匯入（S2.3）與 S1.6 冒煙列（smoke-<date>）都不保證符合，只要求非空。
--
-- 倉儲新增欄位（三表都有，SKI 沒有對應欄位）：
--   content_hash      NOT NULL，寫入端（S1.3 endpoint）計算並據此判斷「同 hash 跳過」。
--   approved_version  發布閘門登記的核可版本（SKI data/content-publication-review.json，plan 硬約束 5）；未經閘門為 NULL。
--   synced_at         最後一次經同步寫入本列的時刻，寫入端每次 upsert 更新。
--   created_at／updated_at：SKI 已有者保留語意；Supabase 的 updated_at trigger（001 update_updated_at）不搬，
--                     本倉儲不建 trigger 函式，updated_at 由寫入端設定（session store 本來就自己寫 updated_at）。
--
-- 刪除語意：warehouse_app 沒有 DELETE／TRUNCATE（plan 硬約束 2）。reports、sessions 在 SKI 是軟刪除（PATCH deleted_at），
--   照搬 deleted_at 欄位；meeting_prep 在 SKI 是硬刪除（supabase-meeting-prep-store.ts delete()），本表沒有 deleted_at，
--   該路徑屬 SKI api 的 Lambda（plan Phase 3 退役），不在同步 endpoint 範圍。
--
-- 權限（逐表 GRANT，矩陣見 db/roles-matrix.md）：
--   warehouse_app：三表 SELECT／INSERT／UPDATE（upsert 的 ON CONFLICT DO UPDATE 與 hash 比對需要 SELECT）；無 DELETE／TRUNCATE。
--   warehouse_reader：三表 SELECT（S1.5 MCP／CLI 唯讀工具）。warehouse_etl、warehouse_rollup 不碰三表。
--   三表沒有 serial／identity 欄位，不需要 sequence 權限；gen_random_uuid() 在 pg_catalog，PUBLIC 可執行。
--
-- 前置：warehouse_app 由 db/roles.sql 建立（bootstrap-roles Job），本檔不建角色；角色不存在時守衛中止並提示先跑 bootstrap。
-- 本檔必須以 warehouse_admin 執行（S1.3 runner 預設 SET LOCAL ROLE），檔首守衛中止其他身分，所有新物件自然屬 warehouse_admin。
-- 冪等：表用 IF NOT EXISTS（PK／CHECK 寫在 CREATE TABLE 內，表已存在就整句略過），COMMENT 與 GRANT 本身冪等。

BEGIN;

DO $do$
BEGIN
  IF current_user <> 'warehouse_admin' THEN
    RAISE EXCEPTION '0009 必須以 warehouse_admin 套用，目前 current_user 為 %', current_user;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'warehouse_app') THEN
    RAISE EXCEPTION '0009 需要角色 warehouse_app：先以新版 db/roles.sql 跑 bootstrap-roles，再套用本檔';
  END IF;
END
$do$;


-- ======================================================================
-- 1. app_report（← Supabase reports）
-- ======================================================================

CREATE TABLE IF NOT EXISTS "public"."app_report" (
    "date_key" "text" NOT NULL,
    "filename" "text" NOT NULL,
    "content" "text" NOT NULL,
    "size_bytes" integer NOT NULL,
    "meta" "jsonb",
    "deleted_at" timestamp with time zone,
    "content_hash" "text" NOT NULL,
    "approved_version" "text",
    "synced_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "app_report_pkey" PRIMARY KEY ("date_key"),
    CONSTRAINT "app_report_date_key_ck" CHECK (("char_length"("date_key") > 0)),
    CONSTRAINT "app_report_size_bytes_ck" CHECK (("size_bytes" >= 0)),
    CONSTRAINT "app_report_content_hash_ck" CHECK (("char_length"("content_hash") > 0))
);

COMMENT ON TABLE "public"."app_report" IS 'SKI 週報（KB plan S1.1）：承接 Supabase reports，一個 date_key 一列，經 warehouse-api 同步 endpoint 由 warehouse_app upsert。Supabase 端沒有 reports 的 CREATE，欄位由 SKI 程式碼反推（seo-knowledge-insight@367d222 api/src/store/supabase-report-store.ts）。軟刪除：deleted_at 非 NULL 即視為已刪，讀取端自行過濾。';

COMMENT ON COLUMN "public"."app_report"."date_key" IS '主鍵，報告識別字串（檔名 report_<date_key>.md 的中段）。來源 SKI api/src/store/supabase-report-store.ts:70（save 寫入）、:77（upsert onConflict date_key）、ReportRow :13。';

COMMENT ON COLUMN "public"."app_report"."filename" IS '原始檔名 report_<date_key>.md。來源 SKI api/src/store/supabase-report-store.ts:66、:71。';

COMMENT ON COLUMN "public"."app_report"."content" IS '報告 markdown 全文。來源 SKI api/src/store/supabase-report-store.ts:72；sync 端讀 output/report_<date_key>.md（api/src/sync/report-sync.ts:67-70）。';

COMMENT ON COLUMN "public"."app_report"."size_bytes" IS 'content 的 UTF-8 位元組數（Buffer.byteLength）。來源 SKI api/src/store/supabase-report-store.ts:73。Supabase 端型別未知（無 CREATE），比照 meeting_prep 用 integer。';

COMMENT ON COLUMN "public"."app_report"."meta" IS '報告 metadata（ReportMeta：weeks、generated_at、generation_mode、generation_label、model、experiment_tag），由 content 內 <!-- report_meta {...} --> 解析；解析不到為 NULL。來源 SKI api/src/store/supabase-report-store.ts:74、api/src/schemas/report.ts:26、api/src/utils/report-file.ts:23。';

COMMENT ON COLUMN "public"."app_report"."deleted_at" IS '軟刪除時刻；NULL 為有效列。save 一律寫回 NULL（重新上傳即復原）。來源 SKI api/src/store/supabase-report-store.ts:75、:88，supabase/migrations/0121_soft_delete.sql:8。';

COMMENT ON COLUMN "public"."app_report"."content_hash" IS '倉儲新增（SKI 無對應欄位）：content 的雜湊，由同步寫入端計算；同 hash 重送即跳過（KB plan S1.3）。';

COMMENT ON COLUMN "public"."app_report"."approved_version" IS '倉儲新增（SKI 無對應欄位）：發布閘門登記的核可版本（SKI data/content-publication-review.json，KB plan 硬約束 5）；未經閘門為 NULL。';

COMMENT ON COLUMN "public"."app_report"."synced_at" IS '倉儲新增（SKI 無對應欄位）：最後一次經同步寫入本列的時刻，寫入端每次 upsert 更新。';

COMMENT ON COLUMN "public"."app_report"."created_at" IS '列建立時刻。來源 SKI api/src/store/supabase-report-store.ts:18（ReportRow 讀回欄位，Supabase 端預設值，save 不寫）。歷史匯入時保留 Supabase 原值。';

COMMENT ON COLUMN "public"."app_report"."updated_at" IS '倉儲新增（SKI reports 讀寫皆未出現此欄）：最後更新時刻，由寫入端設定，本倉儲不建 trigger。';


-- ======================================================================
-- 2. app_meeting_prep（← Supabase meeting_prep）
-- ======================================================================

CREATE TABLE IF NOT EXISTS "public"."app_meeting_prep" (
    "date_key" "text" NOT NULL,
    "filename" "text" NOT NULL,
    "content" "text" NOT NULL,
    "size_bytes" integer NOT NULL,
    "meta" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "content_hash" "text" NOT NULL,
    "approved_version" "text",
    "synced_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "app_meeting_prep_pkey" PRIMARY KEY ("date_key"),
    CONSTRAINT "app_meeting_prep_date_key_ck" CHECK (("char_length"("date_key") > 0)),
    CONSTRAINT "app_meeting_prep_size_bytes_ck" CHECK (("size_bytes" >= 0)),
    CONSTRAINT "app_meeting_prep_content_hash_ck" CHECK (("char_length"("content_hash") > 0))
);

COMMENT ON TABLE "public"."app_meeting_prep" IS 'SKI 會議準備報告（KB plan S1.1）：承接 Supabase meeting_prep（seo-knowledge-insight@367d222 supabase/migrations/012_meeting_prep_table.sql），一個 date_key 一列，經 warehouse-api 同步 endpoint 由 warehouse_app upsert。SKI 端為硬刪除，本表沒有 deleted_at、warehouse_app 也沒有 DELETE。';

COMMENT ON COLUMN "public"."app_meeting_prep"."date_key" IS '主鍵，YYYYMMDD 或 YYYYMMDD_hash8（SKI 只在 store 層驗格式，本表只要求非空）。來源 SKI supabase/migrations/012_meeting_prep_table.sql:6、api/src/store/supabase-meeting-prep-store.ts:16、:101、:107（upsert onConflict date_key）。';

COMMENT ON COLUMN "public"."app_meeting_prep"."filename" IS '原始檔名（meeting_prep_*.md）。來源 SKI supabase/migrations/012_meeting_prep_table.sql:7、api/src/store/supabase-meeting-prep-store.ts:102、api/src/sync/meeting-prep-sync.ts:92。';

COMMENT ON COLUMN "public"."app_meeting_prep"."content" IS '會議準備 markdown 全文。來源 SKI supabase/migrations/012_meeting_prep_table.sql:8、api/src/store/supabase-meeting-prep-store.ts:103。';

COMMENT ON COLUMN "public"."app_meeting_prep"."size_bytes" IS 'content 的 UTF-8 位元組數（Buffer.byteLength）。來源 SKI supabase/migrations/012_meeting_prep_table.sql:9、api/src/store/supabase-meeting-prep-store.ts:104。';

COMMENT ON COLUMN "public"."app_meeting_prep"."meta" IS 'MeetingPrepMeta（含 scores.maturity、scores.eeat、alert_down_count 等），未提供時為 {}。來源 SKI supabase/migrations/012_meeting_prep_table.sql:10、api/src/store/supabase-meeting-prep-store.ts:105、:126-139（成熟度趨勢讀取）。';

COMMENT ON COLUMN "public"."app_meeting_prep"."content_hash" IS '倉儲新增（SKI 無對應欄位）：content 的雜湊，由同步寫入端計算；同 hash 重送即跳過（KB plan S1.3）。';

COMMENT ON COLUMN "public"."app_meeting_prep"."approved_version" IS '倉儲新增（SKI 無對應欄位）：發布閘門登記的核可版本（SKI data/content-publication-review.json，KB plan 硬約束 5）；未經閘門為 NULL。';

COMMENT ON COLUMN "public"."app_meeting_prep"."synced_at" IS '倉儲新增（SKI 無對應欄位）：最後一次經同步寫入本列的時刻，寫入端每次 upsert 更新。';

COMMENT ON COLUMN "public"."app_meeting_prep"."created_at" IS '列建立時刻。來源 SKI supabase/migrations/012_meeting_prep_table.sql:11。歷史匯入時保留 Supabase 原值。';

COMMENT ON COLUMN "public"."app_meeting_prep"."updated_at" IS '最後更新時刻。來源 SKI supabase/migrations/012_meeting_prep_table.sql:12（Supabase 以 trigger :38-40 維護）；本倉儲不建 trigger，由寫入端設定。';


-- ======================================================================
-- 3. app_session（← Supabase sessions）
-- ======================================================================

CREATE TABLE IF NOT EXISTS "public"."app_session" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "title" "text" DEFAULT 'New Chat'::"text" NOT NULL,
    "messages" "jsonb" DEFAULT '[]'::"jsonb" NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    "deleted_at" timestamp with time zone,
    "content_hash" "text" NOT NULL,
    "approved_version" "text",
    "synced_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "app_session_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "app_session_messages_ck" CHECK (("jsonb_typeof"("messages") = 'array'::"text")),
    CONSTRAINT "app_session_metadata_ck" CHECK (("jsonb_typeof"("metadata") = 'object'::"text")),
    CONSTRAINT "app_session_content_hash_ck" CHECK (("char_length"("content_hash") > 0))
);

COMMENT ON TABLE "public"."app_session" IS 'SKI 對話 session（KB plan S1.1）：承接 Supabase sessions（seo-knowledge-insight@367d222 supabase/migrations/004_sessions_table.sql、009、0121），一個 id 一列，經 warehouse-api 同步 endpoint 由 warehouse_app upsert。軟刪除：deleted_at 非 NULL 即視為已刪，讀取端自行過濾。';

COMMENT ON COLUMN "public"."app_session"."id" IS '主鍵 uuid（SKI sync 端只收 UUID v4 檔名）；未提供時 DB 產生。來源 SKI supabase/migrations/004_sessions_table.sql:6、api/src/sync/session-sync.ts:15、:91、:104（upsert onConflict id）。';

COMMENT ON COLUMN "public"."app_session"."title" IS 'session 標題（escapeHtml 後最多 50 字），預設 New Chat。來源 SKI supabase/migrations/004_sessions_table.sql:7、api/src/sync/session-sync.ts:92、api/src/store/supabase-session-store.ts:15-17、:79、:128。';

COMMENT ON COLUMN "public"."app_session"."messages" IS 'SessionMessage 陣列（role、content、sources、created_at、metadata），SKI 上限 100 則。來源 SKI supabase/migrations/004_sessions_table.sql:8、api/src/sync/session-sync.ts:93、api/src/store/supabase-session-store.ts:13、:129、api/src/store/session-store.ts:35-41。';

COMMENT ON COLUMN "public"."app_session"."metadata" IS 'SessionMetadata（maturity_level 等），預設 {}。來源 SKI supabase/migrations/009_maturity_relevance.sql:16-17、api/src/store/supabase-session-store.ts:81、:151-159、api/src/store/session-store.ts:43-46。注意 sync 端 upsert 不帶本欄（session-sync.ts:90-96）。';

COMMENT ON COLUMN "public"."app_session"."deleted_at" IS '軟刪除時刻；NULL 為有效列。來源 SKI supabase/migrations/0121_soft_delete.sql:9、api/src/store/supabase-session-store.ts:178-182。';

COMMENT ON COLUMN "public"."app_session"."content_hash" IS '倉儲新增（SKI 無對應欄位）：本列同步內容的雜湊，由同步寫入端計算；同 hash 重送即跳過（KB plan S1.3）。';

COMMENT ON COLUMN "public"."app_session"."approved_version" IS '倉儲新增（SKI 無對應欄位）：發布閘門登記的核可版本（KB plan 硬約束 5）；session 不經發布閘門時為 NULL。';

COMMENT ON COLUMN "public"."app_session"."synced_at" IS '倉儲新增（SKI 無對應欄位）：最後一次經同步寫入本列的時刻，寫入端每次 upsert 更新。';

COMMENT ON COLUMN "public"."app_session"."created_at" IS 'session 建立時刻（SKI 寫入端提供）。來源 SKI supabase/migrations/004_sessions_table.sql:9、api/src/sync/session-sync.ts:94、api/src/store/supabase-session-store.ts:82。';

COMMENT ON COLUMN "public"."app_session"."updated_at" IS '最後一次新增訊息或改 metadata 的時刻（SKI 寫入端提供）。來源 SKI supabase/migrations/004_sessions_table.sql:10、api/src/sync/session-sync.ts:95、api/src/store/supabase-session-store.ts:83、:130、:160。';


-- ======================================================================
-- 4. GRANT（逐表；角色 × 物件 × 權限的真源是 db/roles-matrix.md）
-- ======================================================================

GRANT SELECT, INSERT, UPDATE ON TABLE "public"."app_report" TO warehouse_app;

GRANT SELECT, INSERT, UPDATE ON TABLE "public"."app_meeting_prep" TO warehouse_app;

GRANT SELECT, INSERT, UPDATE ON TABLE "public"."app_session" TO warehouse_app;

GRANT SELECT ON TABLE "public"."app_report" TO warehouse_reader;

GRANT SELECT ON TABLE "public"."app_meeting_prep" TO warehouse_reader;

GRANT SELECT ON TABLE "public"."app_session" TO warehouse_reader;

COMMIT;
