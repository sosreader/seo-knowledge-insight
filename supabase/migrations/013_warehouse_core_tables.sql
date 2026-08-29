-- 013_warehouse_core_tables.sql
-- SEO warehouse 核心三表：cwv_hourly / seo_change_log / ingestion_run
--
-- cwv_hourly     — Core Web Vitals 聚合事實表（RUM 逐小時 + CrUX 週序列）
-- seo_change_log — 變更登記表，供全計畫引用與 Phase 5 因果分析
-- ingestion_run  — 每次匯入作業的執行紀錄，資料新鮮度告警的查詢對象
--
-- 安全模型：三張表一律 ENABLE ROW LEVEL SECURITY 且「不建立任何 policy」，
-- 即 default deny。只有 service_role（bypass RLS）可讀寫，anon / authenticated
-- 拿不到任何一列。這與 001/004/012 的「anon 可讀」模式刻意不同——倉儲表是
-- 內部管線資產，沒有前端直讀需求。
--
-- 【套用狀態 — 接手前必讀】
-- 本檔已實跑驗證：本機 postgres:15-alpine 與 **postgres:17-alpine**（遠端實際版本
-- 為 PG 17.6.1）皆 apply 成功、重跑冪等、3 張表 + 11 個 constraint 齊全，
-- 且在 SET TimeZone='Asia/Taipei' 下 granularity CHECK 行為仍正確。
--
-- 本檔已於 2026-08-29 套用到遠端（PG 17.6.1），三張表皆 live。
-- 同日一併完成 migration 歷史對帳：遠端追蹤表原本是 15 筆時間戳版本
-- （20260305215414 … 20260321185022），與本地的序號命名（001–013）交集為零，
-- 於是 CLI 認為本地一個都沒套用過。對帳後為 14 筆同步、0 待套用、0 孤兒。
-- 過程與被移除的 15 個時間戳版本 ID 保存在
-- docs/migration-history-reconciliation-2026-08-29.md。
--
-- 對帳當時踩到、之後仍會再踩到的兩件事（這兩條不會過期，故留下）：
--
--   1. PostgreSQL 的 ALTER POLICY **沒有 IF EXISTS 語法**，所以帶 ALTER POLICY
--      的 migration 天生非冪等——目標 policy 不存在就報錯中斷該檔。
--      012_soft_delete 有 4 條。整批重跑前必須先確認那些 policy 在遠端存在。
--
--   2. 本地曾有兩個檔共用編號 012，CLI 只追蹤得到其中一個，push 會在
--      追蹤表的 INSERT 撞 `duplicate key ... Key (version)=(012)`。
--      已用 `git mv` 把 012_soft_delete 改名為 0121_soft_delete 解掉。
--      **新增 migration 前先 `ls`，不要只信「往上加 1」。**
--
-- 不能假設「檔案在 migrations/ 裡」等於「schema 已經生效」。

-- === 1. cwv_hourly — Core Web Vitals 聚合 ===
--
-- 維度值的權威來源：vocus-web-ui/pages/api/web-vitals.ts 的 ALLOWLISTS
-- （2026-08-29 以 Loki 實際 label 值交叉驗證一致，非文件與現況脫節）：
--   metricType : INP / LCP / CLS / FCP / TTFB / LoAF          （6）
--   rating     : good / needs-improvement / poor              （3，本表以 good_rate 表達，不另存欄位）
--   environment: localhost / staging / staging-v2 / staging-v3 /
--                staging-v4 / hotfix / production / unknown   （8）
--   deviceType : mobile / tablet / desktop                    （3）
--
-- 下面 CHECK 允許值 = 上述 allowlist ∪ {'unknown'}。'unknown' 不是自創值，
-- 而是上游 sanitizeAllowlisted() 的降級常數 UNKNOWN，見第 3 段說明。

CREATE TABLE IF NOT EXISTS cwv_hourly (
  -- 時間桶。source='rum' 時對齊整點；source='crux' 時對齊週一 00:00 UTC。
  -- 由 cwv_hourly_source_granularity_ck 在 schema 層強制。
  hour          TIMESTAMPTZ      NOT NULL,

  -- 對應上游 environment。allowlist 本身就含 'unknown'（8 個值裡的一個），
  -- 不像 metric / device 需要另外補。
  --
  -- 【為什麼一定要有這一欄 — 它是 unique constraint 的正確性零件，不是附加維度】
  -- 若不存這一欄，unique key 就只有 (metric, route_type, device, hour, source)，
  -- 於是 production 與 staging 的同維度同小時資料會撞同一個 key，變成互相覆蓋
  -- 或 upsert 打架——把兩個不同母體靜默混成一列，且不產生任何錯誤訊號。
  -- 那正是 unknown_ratio 存在要對抗的同一類錯誤。
  --
  -- 另一條路是「不存這一欄，改由匯入端保證只寫 production」，但那把正確性押在
  -- 一個口頭約定上：匯入端哪天忘了加 filter，DB 沒有任何機制會攔。
  -- **能讓 DB 擋住的事就不要靠文件約定**——與下方 granularity CHECK 同一條原則。
  environment   TEXT             NOT NULL,

  -- 對應上游 metricType。'unknown' 為降級值。
  metric        TEXT             NOT NULL,

  -- 對應上游 routePattern。該欄位無法窮舉（~50 個 Next.js route），上游
  -- 改用 charset + 長度驗證（/^[A-Za-z0-9/_.[\]-]+$/、上限 100 字元），
  -- 不合規者同樣落到 UNKNOWN。此處沿用同一組規則，不自創 enum。
  route_type    TEXT             NOT NULL,

  -- 對應上游 deviceType。'unknown' 為降級值。
  -- 注意：CrUX 的 form factor 是 phone/tablet/desktop，匯入端必須先正規化
  -- 成本欄位的值域再寫入，不可直接落 'phone'。
  device        TEXT             NOT NULL,

  -- 該桶的 p75 值。單位隨 metric 而異（CLS 無單位，其餘為毫秒）。
  p75           DOUBLE PRECISION NOT NULL,

  -- rating='good' 的比例，0..1。
  good_rate     DOUBLE PRECISION NOT NULL,

  -- 該桶的原始樣本數。
  sample_count  INTEGER          NOT NULL,

  -- 【這一欄存在的理由 — 靜默降級的可觀測化】
  -- 上游 sanitizeAllowlisted() 對不在 allowlist 的值的處理是
  -- 「換成 UNKNOWN 繼續送出」，不是拒收：
  --   1. client 送出不合法值（例如未來新增的 staging-v5、或型別錯誤的空字串）
  --   2. sanitizeAllowlisted() 判定不合法 → 換成 'unknown'
  --   3. 該筆照常組進 LokiStream、照常 push
  --   4. Loki 確實收到、/api/web-vitals 回 204（成功）
  --   5. 送出筆數、ingest 筆數、API 成功率——全部正常，沒有任何訊號會亮紅燈
  -- 這是一個「不會產生任何錯誤訊號」的靜默降級。聚合時若不顯式處理
  -- 'unknown' 桶，會稀釋真實維度（如 production）的統計代表性。
  -- unknown_ratio 就是把這個靜默降級變成一個看得到的數字：
  -- 本桶來源記錄中，任一 allowlist 維度被降級為 UNKNOWN 的比例（0..1）。
  -- 匯入端不得靜默丟棄也不得靜默混入 unknown 桶。
  --
  -- 刻意「不給 DEFAULT」：有 DEFAULT 0 的話，忘記計算這一欄的匯入路徑會靜默
  -- 寫進一筆「看起來 0% 降級」的資料——那正好是把上游那種無錯誤訊號的靜默
  -- 降級複製到 warehouse 層。沒有 DEFAULT 時漏算會直接撞 NOT NULL 而失敗。
  -- 同理，upsert 的 ON CONFLICT ... DO UPDATE 必須把 unknown_ratio 放進 SET，
  -- 否則衝突時會沿用舊值（stale），不會被重算。
  unknown_ratio DOUBLE PRECISION NOT NULL,

  -- 'rum'  = Loki 來的逐小時 real-user monitoring
  -- 'crux' = CrUX History API 來的 28 天滾動視窗週序列
  -- 兩者 granularity 不同（小時 vs 週）、母體不同（本站取樣 vs Chrome 使用者），
  -- 報表中不得混算。schema 層以 source 欄位 + granularity CHECK 讓這件事明確。
  source        TEXT             NOT NULL,

  ingested_at   TIMESTAMPTZ      NOT NULL DEFAULT now(),

  -- 防重複寫入：同一維度組合 + 同一時間桶 + 同一來源只能有一列（供 upsert）。
  -- environment 是這組 key 的必要成員，理由見上方欄位註解。
  -- 欄序刻意以 source, environment, hour 開頭，讓此索引同時服務
  -- 「某來源某環境某時間區間」掃描（實務上幾乎都會 filter environment），
  -- 不與下方 (metric, route_type, device, hour) 索引重疊。
  CONSTRAINT cwv_hourly_dim_uniq
    UNIQUE (source, environment, hour, metric, route_type, device),

  -- 值域取自上游 ALLOWLISTS.environment，8 個值一個不多一個不少。
  CONSTRAINT cwv_hourly_environment_ck
    CHECK (environment IN ('localhost', 'staging', 'staging-v2', 'staging-v3',
                           'staging-v4', 'hotfix', 'production', 'unknown')),

  CONSTRAINT cwv_hourly_metric_ck
    CHECK (metric IN ('INP', 'LCP', 'CLS', 'FCP', 'TTFB', 'LoAF', 'unknown')),

  CONSTRAINT cwv_hourly_device_ck
    CHECK (device IN ('mobile', 'tablet', 'desktop', 'unknown')),

  CONSTRAINT cwv_hourly_route_type_ck
    CHECK (
      route_type = 'unknown'
      OR (char_length(route_type) BETWEEN 1 AND 100
          AND route_type ~ '^[A-Za-z0-9/_.\[\]-]+$')
    ),

  CONSTRAINT cwv_hourly_source_ck
    CHECK (source IN ('rum', 'crux')),

  -- granularity 混算的第一道防線：rum 必須對齊整點，crux 必須對齊週界。
  --
  -- 為什麼要 AT TIME ZONE 'UTC' 包一層（不要簡化掉）：
  -- date_trunc('week', <timestamptz>) 的截斷基準是 session TimeZone GUC 對應的
  -- 當地時間，不是絕對 UTC。實測 PG15：SET TimeZone='Asia/Taipei' 之後，
  -- 直接寫 date_trunc('week', hour) 會把合法的 UTC 週一午夜判成不合法（差 8 小時），
  -- 於是同一筆資料「從哪個 session 寫入」決定了它過不過 CHECK。
  -- 先 AT TIME ZONE 'UTC' 轉成 timestamp 再 date_trunc，結果與 session 設定無關。
  -- （順帶更正一個常見誤解：CHECK 並不要求 IMMUTABLE，PG 連 STABLE/VOLATILE
  --   函式都收；這個包裝的理由純粹是 timezone，不是 volatility。）
  CONSTRAINT cwv_hourly_source_granularity_ck
    CHECK (
      (source = 'rum'
        AND (hour AT TIME ZONE 'UTC') = date_trunc('hour', hour AT TIME ZONE 'UTC'))
      OR
      (source = 'crux'
        AND (hour AT TIME ZONE 'UTC') = date_trunc('week', hour AT TIME ZONE 'UTC'))
    ),

  CONSTRAINT cwv_hourly_good_rate_ck     CHECK (good_rate     BETWEEN 0 AND 1),
  CONSTRAINT cwv_hourly_unknown_ratio_ck CHECK (unknown_ratio BETWEEN 0 AND 1),
  CONSTRAINT cwv_hourly_sample_count_ck  CHECK (sample_count  >= 0),
  CONSTRAINT cwv_hourly_p75_ck           CHECK (p75           >= 0)
);

-- 時間範圍掃描（跨維度趨勢圖、新鮮度檢查）
CREATE INDEX IF NOT EXISTS cwv_hourly_hour_idx
  ON cwv_hourly (hour DESC);

-- 維度下鑽（固定 metric/route/device 看時間序列）
CREATE INDEX IF NOT EXISTS cwv_hourly_dim_hour_idx
  ON cwv_hourly (metric, route_type, device, hour DESC);

-- 靜默降級監控：只掃有降級的列，桶數遠小於全表
CREATE INDEX IF NOT EXISTS cwv_hourly_degraded_idx
  ON cwv_hourly (hour DESC) WHERE unknown_ratio > 0;

-- === 2. seo_change_log — 變更登記 ===
--
-- 供全計畫引用：任何可能影響 SEO / CWV 的變更（PR、設定調整、內容改版、
-- 第三方腳本上線）都登記一列，Phase 5 因果分析以 changed_at 對齊
-- cwv_hourly.hour 做前後比較。

CREATE TABLE IF NOT EXISTS seo_change_log (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

  -- 變更「生效」時間，不是登記時間。因果分析的對齊點。
  changed_at      TIMESTAMPTZ NOT NULL,

  description     TEXT        NOT NULL,

  -- 受影響的 URL 範圍，glob / 前綴形式（例：'/', '/article/*'）。
  -- NULL = 全站範圍。
  url_pattern     TEXT,

  pr_url          TEXT,

  -- 預期受影響的指標名稱。刻意不加 CHECK：可能是 CWV 指標（LCP/INP/CLS…）
  -- 也可能是 GSC 指標（clicks/impressions/position），跨域值不宜硬綁 enum。
  expected_metric TEXT,

  -- 這一列從哪裡來：'manual'（人工登記）/ 'github'（PR webhook）/
  -- 'deploy'（發版管線）。與 cwv_hourly.source 語義不同，勿混用。
  source          TEXT        NOT NULL DEFAULT 'manual',

  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT seo_change_log_source_ck
    CHECK (source IN ('manual', 'github', 'deploy')),

  CONSTRAINT seo_change_log_description_ck
    CHECK (char_length(description) > 0)
);

-- 時間軸查詢（因果分析主要存取路徑）
CREATE INDEX IF NOT EXISTS seo_change_log_changed_at_idx
  ON seo_change_log (changed_at DESC);

-- 依 URL 範圍找相關變更
CREATE INDEX IF NOT EXISTS seo_change_log_url_pattern_idx
  ON seo_change_log (url_pattern) WHERE url_pattern IS NOT NULL;

-- === 3. ingestion_run — 匯入執行紀錄 ===
--
-- 資料新鮮度告警的查詢對象。典型查詢：
--   SELECT max(finished_at) FROM ingestion_run
--   WHERE table_name = 'cwv_hourly' AND status = 'success';
-- 超過門檻沒有成功列 → 告警。
--
-- 注意：status='running' 的列 finished_at 為 NULL，告警查詢必須以
-- status='success' 過濾，不可只看 max(finished_at)。

CREATE TABLE IF NOT EXISTS ingestion_run (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

  -- 這次匯入寫入的目標表名（例：'cwv_hourly'）。
  table_name   TEXT        NOT NULL,

  -- 這次匯入涵蓋的資料時間視窗（半開區間 [window_start, window_end)）。
  window_start TIMESTAMPTZ NOT NULL,
  window_end   TIMESTAMPTZ NOT NULL,

  -- 實際寫入列數。0 是合法值（該視窗真的沒資料），與 status 一起判讀。
  row_count    INTEGER     NOT NULL DEFAULT 0,

  status       TEXT        NOT NULL,

  -- status='running' 時為 NULL；終態時必填。
  finished_at  TIMESTAMPTZ,

  started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT ingestion_run_status_ck
    CHECK (status IN ('running', 'success', 'partial', 'failed')),

  CONSTRAINT ingestion_run_window_ck
    CHECK (window_end > window_start),

  CONSTRAINT ingestion_run_row_count_ck
    CHECK (row_count >= 0),

  CONSTRAINT ingestion_run_table_name_ck
    CHECK (char_length(table_name) > 0),

  -- 終態必須有 finished_at，running 必須沒有——避免「跑完但沒收尾」的列
  -- 混進新鮮度查詢，讓卡死的作業看起來像成功。
  CONSTRAINT ingestion_run_finished_at_ck
    CHECK (
      (status = 'running' AND finished_at IS NULL)
      OR (status <> 'running' AND finished_at IS NOT NULL)
    )
);

-- 新鮮度告警主要存取路徑
-- 同時服務「最近一次成功匯入」與「最近一次任意 status 的 run」兩種查詢。
-- 刻意不另建 WHERE status='success' 的 partial 索引：那會是本索引的嚴格子集，
-- 而 ingestion_run 是每次作業一列的低寫入量表，多一份索引維護不划算。
CREATE INDEX IF NOT EXISTS ingestion_run_table_finished_idx
  ON ingestion_run (table_name, finished_at DESC);

-- === 4. RLS — 三表一律 default deny ===
--
-- 只 ENABLE，刻意不建立任何 policy：沒有 policy 的 RLS 表對所有非 bypass
-- 角色是「全部拒絕」。service_role 有 BYPASSRLS，管線照常讀寫。
-- 之後若要開放前端直讀，必須另開 migration 明確加 policy，不能靠預設。

ALTER TABLE cwv_hourly     ENABLE ROW LEVEL SECURITY;
ALTER TABLE seo_change_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingestion_run  ENABLE ROW LEVEL SECURITY;

-- 縱深防禦：Supabase 對 public schema 有預設 GRANT 給 anon / authenticated。
-- RLS default deny 已經擋住，這裡再把 table 權限收回，讓誤加 permissive
-- policy 時不會立刻變成全開。角色不存在（本機純 postgres）時跳過。
DO $$
DECLARE
  r TEXT;
BEGIN
  FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format(
        'REVOKE ALL ON TABLE cwv_hourly, seo_change_log, ingestion_run FROM %I', r
      );
    END IF;
  END LOOP;
END
$$;
