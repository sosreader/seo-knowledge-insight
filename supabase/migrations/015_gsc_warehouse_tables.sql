-- 015_gsc_warehouse_tables.sql
-- GSC / crawl 倉儲三表：gsc_daily_metrics / gsc_url_inspection / crawl_daily
--
-- gsc_daily_metrics — Search Analytics API 逐日 × 四維度的**抽樣**事實表
-- gsc_url_inspection — URL Inspection API 的索引狀態**抽樣**快照（每日一筆／URL）
-- crawl_daily        — 逐小時 crawler 流量聚合。**來源不是 GSC**，見第 3 段。
--
-- 沿用 013 的安全模型與紀律：
--   - RLS ENABLE 且不建任何 policy（default deny），另外 REVOKE anon/authenticated
--   - ingestion_run 沿用 013 建的那張，本檔不另建
--   - 能讓 DB 擋住的事就不要靠文件約定
--   - DDL 全部 IF NOT EXISTS，重跑冪等。本檔**不含任何 ALTER POLICY**
--     （PostgreSQL 的 ALTER POLICY 沒有 IF EXISTS，用了就天生非冪等，見 013 註解）
--
-- 【編號】新增前已 `ls supabase/migrations/` 確認：012 曾被兩個檔共用而撞
-- `duplicate key ... (version)=(012)`，現況為 012 + 0121 + 013 + 014，故本檔為 015。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【全域前提：這裡的 GSC 資料是抽樣，不是全量】
-- ══════════════════════════════════════════════════════════════════════
-- Search Analytics API 每天每 property 每 search type 最多回 50,000 列，
-- 而且官方明講「只回 top rows，不保證涵蓋全部資料列」。
-- 因此：
--   SUM(clicks) FROM gsc_daily_metrics  ≠  GSC UI 上那天的總點擊
-- 兩者必然有落差，而且落差大小不可知。這不是 bug，是資料源的性質。
-- 這件事用 COMMENT ON TABLE 寫進 catalog（不只是 SQL 註解）：PostgREST 會把
-- table/column comment 吐進 OpenAPI，Supabase Studio 也直接顯示，
-- 下游拿到的是「看得到」的警告，不是要翻 migration 檔才知道的約定。
--
-- 其他已查證、會影響 schema 的事實：
--   - 單次 rowLimit 1..25,000（預設 1,000），startRow 0-based 分頁
--     → 一天的資料會分多批寫入，靠 unique key + upsert 保證冪等
--   - 資料保留 16 個月，超過就再也拿不回來 → 清理策略見第 1 段末尾
--   - 資料延遲通常 2-3 天 → 新鮮度告警門檻不能設成「今天要有資料」
--   - URL Inspection 2,000 QPD／property、600 QPM → 第 2 段的表天生是抽樣
--   - Crawl Stats **沒有公開 API**（v1 只有 searchAnalytics / sitemaps /
--     sites / urlInspection 四個 resource）→ 第 3 段的表不是 GSC 來的
--
-- ══════════════════════════════════════════════════════════════════════
-- 【冪等契約 —— schema 保證的到哪裡為止，其餘是 ingest 端的責任】
-- ══════════════════════════════════════════════════════════════════════
-- 三張表都以 unique key + upsert 達成冪等，但 upsert 的冪等**只涵蓋
-- 「桶集合不變」的情形**。三個 schema 擋不住、ingest 端必須自己處理的破口：
--
-- 1. **upsert 只新增與覆蓋，不刪除。** 重跑同一視窗時若新結果的桶比舊結果少
--    （GSC top-N 抽樣的邊界移動、Loki 的 UA 分類規則調整、某個路徑桶被拆出去），
--    舊列會殘留並繼續被計入 SUM，變成靜默高估。
--    收尾策略二擇一，不可只做 upsert：
--      (a) 先 DELETE 該視窗、再批次 INSERT；或
--      (b) upsert 後 DELETE 該視窗中 ingested_at < 本次 run 起始時刻的列
--          （採 (b) 的話 ingested_at 必須每次更新，見第 2 點）。
--
-- 2. **ingested_at 在 upsert 時預設不會更新。** PostgREST 的
--    `Prefer: resolution=merge-duplicates` 只會 SET payload 裡出現的欄位，
--    ingested_at 有 DEFAULT now() 但不在 payload 裡，衝突時沿用第一次寫入的值。
--    所以它的語意是「首次匯入時間」而非「最後更新時間」。
--    要當成後者用（例如上面的收尾策略 (b)），必須把 ingested_at 明確放進 payload。
--
-- 3. **同一批次內不可有重複 key。** GSC 用 startRow 分頁，兩次 request 之間
--    底層資料若有變動，相鄰頁可能回傳重疊列。把多頁合併成一個 batch 送出時，
--    PostgreSQL 會回
--      ON CONFLICT DO UPDATE command cannot affect row a second time
--    而且死的是**整批**（25,000 列）不是那一列。
--    batch 送出前必須先以 unique key 去重。
--
-- 4. **gsc_url_inspection 的 payload 不可帶 inspected_on**（生成欄位）：
--      ERROR: cannot insert a non-DEFAULT value into column "inspected_on"
--    但 `on_conflict` 參數**要**帶它（衝突偵測需要完整的 unique key）。
--    「on_conflict 列到的欄位就都放進 payload」這個直覺在這裡會踩雷。

-- ══════════════════════════════════════════════════════════════════════
-- 1. gsc_daily_metrics — Search Analytics 逐日抽樣事實表
-- ══════════════════════════════════════════════════════════════════════
--
-- 【硬性前提：欄位語意對齊 BigQuery Bulk Data Export 的 searchdata_url_impression】
--
-- 採用 Postgres 而非 BigQuery 的前提條件是「保留退路」——資料量長到必須搬去
-- BigQuery 時，語意對齊才能無痛遷移。語意一旦分岔，這個決策就沒有退路。
-- 下表是逐欄位對照（BQ 欄位定義查證自 Search Console Help「Table guidelines
-- and reference」，2026-08-29 實查）：
--
--  BQ searchdata_url_impression | 本表欄位      | 對照關係
--  ─────────────────────────────┼───────────────┼────────────────────────────
--  data_date        DATE        | date          | 語意相同（GSC 的日界是太平洋時間，
--                               |               |   兩邊都直接沿用 API 給的日期，不做時區換算）
--  site_url         STRING      | property      | 語意相同。改名理由見下方欄位註解
--  url              STRING      | page          | 語意相同（都是使用者點擊後最終落地的完整 URL）。
--                               |               |   改名是因為 Search Analytics API 的維度名就叫
--                               |               |   `page`，本表的**實際來源是 API 不是 BQ**，
--                               |               |   用來源端的名字可讓 ingest 端零心智轉換。
--                               |               |   遷移 BQ 時是純改名，語意不動。
--  query            STRING      | query         | 語意相同。匿名化時 BQ 給空字串，本表同樣存 ''
--  is_anonymized_query BOOL     | （不存）      | **不一致**：Search Analytics API 不吐這個旗標。
--                               |               |   帶 query 維度查詢時，匿名化的列會被 API 直接
--                               |               |   略去，我們拿不到「這列被匿名了」的訊號，
--                               |               |   憑空造一個 false 會是說謊。遷移 BQ 時這一欄
--                               |               |   由 BQ 自己填，不需要回填歷史。
--  is_anonymized_discover BOOL  | （不存）      | **不一致**：同上。且我們不打 discover search type。
--  country          STRING      | country       | 語意相同，同為 ISO-3166-1-Alpha-3 小寫
--  search_type      STRING      | search_type   | 語意相同（web/image/video/news/discover/googleNews）
--  device           STRING      | device        | **值域大小寫不一致**：BQ/API 用大寫
--                               |               |   DESKTOP/MOBILE/TABLET，本表存小寫。
--                               |               |   理由：本 warehouse 既有的 cwv_hourly.device
--                               |               |   是小寫，兩表要能直接 JOIN 比對「哪個裝置
--                               |               |   CWV 差且 GSC 排名掉」。跨表 casing 不一致是
--                               |               |   每天都要付的成本，遷移 BQ 只需一次 LOWER()。
--  is_[appearance]  BOOL × N    | （不存）      | **不一致**：Search Analytics API 的
--                               |               |   searchAppearance 是一個「維度」而非每列旗標，
--                               |               |   而且**不能與其他維度同時查詢**（API 限制）。
--                               |               |   要存就得另開一張表打第二次 API、再吃一份
--                               |               |   50K 配額。本階段不做，未來要做時是新表不是新欄位。
--  impressions      INTEGER     | impressions   | 語意相同
--  clicks           INTEGER     | clicks        | 語意相同
--  sum_position     INTEGER     | position      | **形狀不一致，但可逆**。BQ 存的是「0-based 位置
--                               |               |   的總和」，本表存 API 直接給的 1-based 加權
--                               |               |   平均位置。互換公式：
--                               |               |     BQ → 本表：SUM(sum_position)/SUM(impressions)+1
--                               |               |     本表 → BQ：sum_position = (position-1)*impressions
--                               |               |   兩邊資訊等價（本表另存 impressions），
--                               |               |   遷移不會掉資訊。
--                               |               |   ⚠ 聚合時 position **不能直接 AVG()**，
--                               |               |   必須 SUM(position*impressions)/SUM(impressions)。
--  （BQ 不存）                  | ctr           | **本表多存**。BQ 要 clicks/impressions 現算，
--                               |               |   API 直接給。存下來的價值是對帳：
--                               |               |   下方 ctr_consistency_ck 會用它抓「欄位對錯位」
--                               |               |   這種靜默錯誤。遷移 BQ 時直接丟掉即可。
--  （BQ 不存）                  | ingested_at   | 本表多存，管線 metadata，與 013 一致
--
-- 注意 BQ 的另一張表 searchdata_site_impression 的位置欄位叫
-- **sum_top_position**（不是 sum_position），且沒有 url／is_anonymized_discover／
-- is_[appearance] 這些欄位。本表對齊的是 **searchdata_url_impression**，
-- 抄錯表會抄到錯的欄名。

-- property 的值域用 DOMAIN 收斂，而不是在兩張表各寫一次 CHECK。
-- 理由：這個常數原本會出現在 4 個地方（兩個 CHECK + 兩個 COMMENT），
-- 未來換 property 時漏改一個，兩張表的值域就會靜默分岔——正是本檔一直在
-- 對抗的那種「沒有訊號的錯誤」。收成 DOMAIN 之後，換 property 是單一
-- ALTER DOMAIN，兩張表自動同步。PostgREST 對 domain over text 無差別對待。
--
-- CREATE DOMAIN 沒有 IF NOT EXISTS 語法，用 DO block 吞掉 duplicate_object
-- 來保持重跑冪等（同理於 ALTER POLICY 沒有 IF EXISTS 的那個坑）。
DO $$
BEGIN
  CREATE DOMAIN gsc_property AS TEXT
    CONSTRAINT gsc_property_ck CHECK (VALUE = 'https://vocus.cc/');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END
$$;

CREATE TABLE IF NOT EXISTS gsc_daily_metrics (
  -- 對應 BQ data_date。GSC 的日界是太平洋時間，直接沿用 API 回的日期字串，
  -- 不做任何時區換算——換算會製造一個「我們的日」與「GSC UI 的日」對不起來的
  -- 落差，而且不可逆。
  date         DATE             NOT NULL,

  -- 對應 BQ site_url。
  --
  -- 【為什麼值域被鎖成單一值 —— 這是本表最重要的設計決定】
  -- 實測（2026-08-29）：`sc-domain:vocus.cc` 與 `https://vocus.cc/` 兩個 property
  -- 回傳近乎相同的資料（5 列樣本只差 1 個 click）。意涵有兩層：
  --   (a) 配額是 50K 不是 100K —— 兩個 property 不是兩份獨立額度可以疊加使用
  --   (b) 兩者的數字**絕對不可相加** —— 加起來會得到接近兩倍的假數字
  --
  -- (b) 正是 KB learned skill
  -- `rollup-sentinel-in-shared-key-space-has-no-check-guard-against-double-count`
  -- 講的那個坑的同構情形：兩個 property 的列共用同一個 unique key 空間，
  -- 任何沒帶 `WHERE property = ...` 的 SUM 都會重複計算，而 CHECK 沒有能力
  -- 表達「這個值不能跟另一個值同時進入同一次 SUM」這種跨列語意。
  --
  -- 那則 skill 的結論是「只能靠查詢端自律」。本表用另一個辦法繞過它：
  -- **把值域縮到單一值，讓危險狀態根本無法被表示**。
  -- CHECK 擋不住「兩個值同時出現」，但擋得住「第二個值出現」——
  -- 只要表裡永遠只有一個 property，跨 property 重複計算就不是紀律問題，
  -- 而是物理上不存在的狀態。忘記加 WHERE 也不會錯。
  --
  -- 選 'https://vocus.cc/' 的理由是它是**目前唯一有存取權**的 property：
  -- 唯讀 SA 只被加進這個 url-prefix property（siteRestrictedUser），
  -- sc-domain:vocus.cc 沒有。schema 不假設兩個 property 都會有資料。
  --
  -- 未來要換 property 或真的要同時存兩個，必須開新 migration，
  -- 屆時被迫正面回答「怎麼防重複計算」。這是刻意的摩擦：
  -- 那是一個值得一個 migration 的決定，不該靠某次 ingest 靜默改個環境變數就發生。
  -- （若屆時確定要並存，PostgreSQL 有能表達跨列條件的工具：
  --   EXCLUDE USING gist (date WITH =, property WITH <>) 可讓「同一天出現兩個
  --   property」在寫入當下就報錯。本階段不採用，因為要 btree_gist 擴充、
  --   要在千萬列規模維護一份 GiST 索引，成本遠大於單值 CHECK。）
  --
  -- 【這道防線擋得住什麼、擋不住什麼 —— 別高估它】
  -- 擋得住：兩個 property 的列並存於同一張表（第二個值寫不進來）。
  -- **擋不住**：有人為了通過本約束，把 sc-domain:vocus.cc 的資料「正規化」成
  -- 'https://vocus.cc/' 再寫入。那樣兩份近乎相同的資料會撞同一個 unique key，
  -- 跨批次是靜默的 last-writer-wins，同批次內則是硬錯
  -- （ON CONFLICT DO UPDATE command cannot affect row a second time）。
  -- 換句話說：改值域繞過本約束等同於資料覆蓋，不是等同於合併。
  --
  -- 【為什麼 property 仍留在 unique key 裡（雖然它恆為單值、不提供選擇性）】
  -- 拿掉的話 key 會變成 (search_type, date, page, query, device, country)，
  -- 在單值前提下唯一性完全等價，還能省下每列 18 bytes（2,500 萬列約 0.9 GB）。
  -- 不拿掉是因為：未來放寬值域時，若 key 裡沒有 property，失敗模式會從
  -- 「寫不進去」惡化成「靜默覆蓋」——用 0.9 GB 換掉一個靜默錯誤是划算的。
  property     gsc_property     NOT NULL,

  -- 對應 BQ search_type。
  --
  -- 【這一欄是 unique key 的正確性零件，不是附加維度】
  -- 50K 配額是**每 search type 各自計算**的，所以 web 與 image 是兩次獨立查詢、
  -- 兩批獨立資料。不存這一欄的話，同一天同一個 page/query/device/country 的
  -- web 列與 image 列會撞同一個 key，變成互相覆蓋——把兩個不同母體靜默混成
  -- 一列，且不產生任何錯誤訊號。與 013 的 cwv_hourly.environment 同一個論證。
  search_type  TEXT             NOT NULL,

  -- 對應 BQ url。使用者點擊後最終落地的完整 URL（含 scheme）。
  --
  -- 長度上限用 octet_length 而非 char_length：這一欄在 unique 索引裡，
  -- 而 btree 的索引項上限約 2704 bytes，管的是**位元組**不是字元。
  -- 中文 URL 經 percent-encode 後一個字可以膨脹成 9 bytes，用 char_length
  -- 設限會漏過去，等到寫入時才撞
  -- 「index row size exceeds btree version 4 maximum」——那是一個
  -- 訊息難懂、且只在特定資料上才出現的失敗。用 octet_length 直接擋在 CHECK，
  -- 錯誤訊息會直接指向這一欄。
  -- 1024 + 512（query）+ 其餘維度約 60 bytes ≈ 1600，離 2704 有安全邊界。
  page         TEXT             NOT NULL,

  -- 對應 BQ query。
  -- 匿名化查詢：BQ 存空字串 + is_anonymized_query=true；Search Analytics API
  -- 則是**直接不回這些列**，我們連空字串都拿不到。此處允許 '' 是為了對齊 BQ
  -- 的形狀（未來從 BQ 回填歷史時不必改 schema），不代表 API 會給。
  query        TEXT             NOT NULL,

  -- 對應 BQ device，值域轉小寫（理由見上方對照表）。
  --
  -- 【刻意不收 'all' 之類的彙總哨兵值 —— 與 014 的取捨明確不同】
  -- 014 給 cwv_hourly.device 加 'all'，是因為 p75 不可跨桶重組：
  -- 「不分裝置的 p75」從三個分裝置的桶推不回來，不存就永久放棄。
  -- 本表沒有這個問題：clicks / impressions 可加總，ctr 可由
  -- SUM(clicks)/SUM(impressions) 重算，position 可由
  -- SUM(position*impressions)/SUM(impressions) 重算——**全部可重組**，
  -- 存彙總列拿不到任何多出來的資訊，只會白白引進 014 那個
  -- 「忘了過濾就四倍」的重複計算風險。
  -- 所以本表選「不要放」：下游自己 GROUP BY。
  --
  -- 唯一真正不可重組的切面是「該日**未抽樣**的全站總計」（GSC UI 上那個數字），
  -- 它確實推不回來。但那也不該用哨兵列存：它跟本表的列**母體不同**
  -- （全量 vs top-N 抽樣），混在同一張表、同一個 key 空間就是 014 的坑再犯一次。
  -- 要存的話請另開 gsc_daily_totals 表，讓它連被誤加總的機會都沒有。
  device       TEXT             NOT NULL,

  -- 對應 BQ country。ISO-3166-1-Alpha-3 小寫（例：'twn'、'usa'）。
  -- GSC 對無法判定的地區回 'zzz'，下方 regex 已涵蓋，不需另設哨兵。
  country      TEXT             NOT NULL,

  clicks       INTEGER          NOT NULL,
  impressions  INTEGER          NOT NULL,

  -- API 直接給的點閱率，0..1。BQ 不存這一欄。
  -- 存下來不是為了省一次除法，是為了 ctr_consistency_ck 那道對帳（見下）。
  ctr          DOUBLE PRECISION NOT NULL,

  -- API 直接給的 1-based 加權平均排名。
  -- ⚠ 聚合時不可 AVG(position)，必須用 impressions 加權，見上方對照表。
  position     DOUBLE PRECISION NOT NULL,

  ingested_at  TIMESTAMPTZ      NOT NULL DEFAULT now(),

  -- 冪等 upsert 的衝突鍵。一天的資料會分多批（rowLimit ≤ 25,000）寫入，
  -- 重跑同一區間必須得到同樣結果，全靠這組 key。
  -- 欄序以 (property, search_type, date) 開頭。
  -- 【實測修正，不要照直覺理解這個索引的用途】原本預期它能兼任
  -- 「某 search type 某段日期」的範圍掃描索引，但 300,012 列的 EXPLAIN ANALYZE
  -- 顯示 planner 對這種查詢一律改用下方較窄的 date_idx（15.8ms），
  -- 因為 property 恆為單值、search_type 基數極低，這兩個前綴欄位提供不了
  -- 任何額外選擇性，只是讓索引項變寬。
  -- 所以這個索引的實際用途只有一個：**upsert 的衝突偵測**（單列精確查找，
  -- 實測 0.04ms）。範圍掃描交給 date_idx，兩者不重疊也不互相取代。
  CONSTRAINT gsc_daily_metrics_dim_uniq
    UNIQUE (property, search_type, date, page, query, device, country),

  -- Search Analytics API `type` 參數的值域，**刻意扣掉 'discover'**。
  -- 理由（複審實測）：Discover 沒有排名概念，API 對 Discover 列回 position 0，
  -- 會被下方 position_ck 擋下；Discover 也不支援 query 維度，與 dim_uniq 的形狀
  -- 不相容。若值域收 'discover'，等於宣告「這張表裝得下 Discover」，
  -- 而另一道 CHECK 保證「裝不進去」——照著值域實作的人會撞上一個
  -- 看起來與 search_type 無關的 position_ck 錯誤。要收 Discover 得另開表。
  --
  -- 注意 'googleNews' 保留 API 原生的 camelCase，與 device 刻意轉小寫不同。
  -- 兩個決定各有理由：search_type 的值要能直接當 API 的 `type` 參數送出，
  -- 轉換只會製造對照表；device 則是要與既有的 cwv_hourly.device 對得起來。
  CONSTRAINT gsc_daily_metrics_search_type_ck
    CHECK (search_type IN ('web', 'image', 'video', 'news', 'googleNews')),

  CONSTRAINT gsc_daily_metrics_device_ck
    CHECK (device IN ('mobile', 'tablet', 'desktop')),

  CONSTRAINT gsc_daily_metrics_country_ck
    CHECK (country ~ '^[a-z]{3}$'),

  -- 上限理由見 page 欄位註解（btree 索引項的位元組上限）。
  CONSTRAINT gsc_daily_metrics_page_ck
    CHECK (page ~ '^https?://' AND octet_length(page) BETWEEN 8 AND 1024),

  CONSTRAINT gsc_daily_metrics_query_ck
    CHECK (octet_length(query) <= 512),

  -- 未來日期一律是 bug（時區換算寫錯、或把 window_end 當成資料日期）；
  -- 資料延遲 2-3 天，所以連「今天」都不該出現，留 1 天寬容度。
  -- 下界擋 1970-01-01 / 0001-01-01 這類 epoch 誤解或日期解析失敗的產物——
  -- 它們會靜默落在 date_idx 的一端，讓「最舊資料」的判讀失真。
  --
  -- 用 (now() AT TIME ZONE 'UTC')::DATE 而不是 CURRENT_DATE：
  -- CURRENT_DATE 隨 session TimeZone 擺盪 ±1 天（實測同一瞬間
  -- UTC → 2026-08-29、Pacific/Niue → 2026-08-28），於是「上界是哪一天」
  -- 會由寫入的那個 session 決定。這與 013 的 granularity CHECK 是同一個坑、
  -- 同一個解法，紀律要一致。
  -- （非 IMMUTABLE 函式在 CHECK 裡是合法的，且本約束只會隨時間放寬，
  --   pg_dump/restore 與邏輯複製方向永遠安全。）
  CONSTRAINT gsc_daily_metrics_date_ck
    CHECK (date BETWEEN DATE '2020-01-01' AND ((now() AT TIME ZONE 'UTC')::DATE + 1)),

  CONSTRAINT gsc_daily_metrics_clicks_ck      CHECK (clicks      >= 0),
  CONSTRAINT gsc_daily_metrics_impressions_ck CHECK (impressions >  0),
  CONSTRAINT gsc_daily_metrics_ctr_ck         CHECK (ctr         BETWEEN 0 AND 1),

  -- position 是 1-based。< 1 代表 ingest 端把 BQ 的 0-based sum_position
  -- 直接塞進來卻忘了 +1，這是遷移時最容易犯的錯，讓 DB 擋住。
  CONSTRAINT gsc_daily_metrics_position_ck    CHECK (position    >= 1),

  -- 曝光不可能少於點擊。
  CONSTRAINT gsc_daily_metrics_clicks_le_impressions_ck
    CHECK (clicks <= impressions),

  -- 【對帳約束 —— 抓「欄位對錯位」這種靜默錯誤】
  -- API 的 ctr 定義就是 clicks/impressions，所以這三欄之間有硬關係。
  -- 若 ingest 端把 clicks 與 impressions 寫反、或把某欄對到別的 key，
  -- 數字仍然全部合法（都是非負整數）、CHECK 全過、圖照樣畫得出來——
  -- 正是 013 unknown_ratio 要對抗的那種無錯誤訊號的靜默錯誤。
  -- 這道約束讓它在寫入當下就爆掉。
  --
  -- 【NULLIF 不可省 —— 複審實測抓到的 bug】
  -- 沒有 NULLIF 時，impressions=0 的列會在這道 CHECK 求值時噴
  -- `ERROR: division by zero`，而不是預期的 gsc_daily_metrics_impressions_ck。
  -- 原因：PostgreSQL 求值 CHECK 的順序是按 constraint 名稱排序，
  -- 而 `..._ctr_consistency_ck` 排在 `..._impressions_ck` 前面，先除先死。
  -- 後果是錯誤訊息裡沒有 constraint 名稱，PostgREST 轉給 ingest 端的 body
  -- 只剩一個 SQLSTATE 22012，排查成本高一個量級。
  -- NULLIF 讓分母 0 時整條運算式變 NULL，CHECK 對 NULL 視同通過，
  -- 於是 impressions_ck 得以接手並給出正確的 constraint 名稱。
  -- （用 NULLIF 而不是 `impressions > 0 AND ...`：PG 不保證布林運算子短路，
  --   NULLIF 是純函式呼叫，行為確定。）
  --
  -- 【容差取 1e-4 而非 1e-6】
  -- 實測 Python repr(float) → JSON → PG float8 的往返是**精確**的，
  -- 所以 1e-6 對「現況」綽綽有餘。但那等於把這道 CHECK 綁死在
  -- 「Google 永遠回全精度 double」這個未文件化的假設上：
  -- API 哪天改成回 4 位小數（誤差可達 5e-5），整批 25,000 列會一起 400，
  -- 而且要開新 migration 才能放寬。
  -- 1e-4 對本約束要抓的錯誤（clicks/impressions 對調、欄位錯位）完全無損——
  -- 那些會產生 O(0.1~1) 的差異，不是 O(1e-5)。放寬是純賺。
  CONSTRAINT gsc_daily_metrics_ctr_consistency_ck
    CHECK (abs(ctr - clicks::DOUBLE PRECISION / NULLIF(impressions, 0)) < 1e-4)
);

-- 【分區決定：不分區】
-- 判斷依據而非直覺：
--   - 量級：50K 列／天是**理論天花板**（配額上限），實際會更少。
--     以最壞情況 50K × 500 天（16 個月保留期）≈ 2,500 萬列估算。
--     實測（本機 PG 17.11，30 萬列真實形狀資料 + 本表全部 4 個索引）：
--     110 MB / 300,012 列 ≈ 0.37 KB/列，外推 2,500 萬列約 9 GB。
--     單一 PostgreSQL 表在這個量級加上適當索引仍屬舒適區間——
--     實測查詢時間見下方，2 天 10 萬列的聚合掃描 21ms、單 URL 下鑽 3.7ms。
--     這不是分區的門檻。
--   - 分區的主要誘因是「保留期到期的整批刪除」（DROP PARTITION vs DELETE）。
--     但這裡每月要刪的是約 150 萬列，一次 DELETE 幾秒鐘的事，
--     不值得換來每月要新增分區的維運負擔（且本專案沒有 pg_partman、
--     沒有排程器來建分區——忘記建的後果是寫入直接失敗）。
--   - 分區還會讓 PostgREST 的 upsert 變複雜（ON CONFLICT 在分區表上要求
--     分區鍵必須在 unique 索引裡）。
-- **重新評估的觸發條件**（寫死，免得靠感覺）：
--   - 單表超過 5,000 萬列；或
--   - gsc_daily_metrics_dim_uniq 超過 6 GB —— 實測 300,012 列時它佔 54 MB，
--     是全表 110 MB 的 49%，本表最大的單一物件（約 0.18 KB/entry，
--     外推 2,500 萬列約 4.5 GB）。它若開始 bloat 會比列數先變成問題；或
--   - 保留期 DELETE 開始造成明顯 bloat／autovacuum 追不上。
--
-- 【尚未實作】16 個月保留期目前只是註解，沒有任何機制在執行清理。
-- 需要一個排程 DELETE（或 pg_cron）。這是刻意留給後續 step 的缺口，不是漏掉。
--
-- 索引策略：三個查詢型態各一個，不重疊。
-- （unique constraint 已附帶一個以 property/search_type/date 開頭的索引，
--   服務「某 search type 某段日期」的掃描，不再重複建。）

-- 純日期範圍掃描（每日總計、抽樣覆蓋率檢查）
CREATE INDEX IF NOT EXISTS gsc_daily_metrics_date_idx
  ON gsc_daily_metrics (date DESC);

-- 單一 URL 的時間序列（「這篇文章的曝光什麼時候掉的」——最常用的下鑽）
CREATE INDEX IF NOT EXISTS gsc_daily_metrics_page_date_idx
  ON gsc_daily_metrics (page, date DESC);

-- 單一 query 的時間序列。排除 ''（匿名化列）——它們不是一個真的 query，
-- 沒有人會查 query='' 的時間序列，卻可能佔掉可觀比例的列。
CREATE INDEX IF NOT EXISTS gsc_daily_metrics_query_date_idx
  ON gsc_daily_metrics (query, date DESC) WHERE query <> '';

-- ══════════════════════════════════════════════════════════════════════
-- 2. gsc_url_inspection — URL Inspection 索引狀態快照
-- ══════════════════════════════════════════════════════════════════════
--
-- 【這張表天生是抽樣，而且比 gsc_daily_metrics 更稀疏】
-- URL Inspection API 的配額是 2,000 QPD／property、600 QPM，一次一個 URL。
-- vocus.cc 的 URL 數遠超過 2,000，所以**不可能全站覆蓋**：
-- 這張表永遠只會有被挑選過的一小撮 URL。
-- 「表裡沒有這個 URL」== 「我們沒查過它」，**不等於**「它沒被索引」。
-- 這句話用 COMMENT ON 寫進 catalog，因為它是最容易被誤讀的一件事。
--
-- 【unique key 的取捨：為什麼是 (property, url, 日期) 而不是 (property, url)】
-- 只用 (property, url)：每次查都覆蓋，只留最新狀態——「這個 URL 什麼時候從
-- 已索引變成未索引」這個問題就永遠答不出來，而那正是我們想要的訊號。
-- 加上 inspected_at（時間戳）：同一天重跑會產生第二列，**不冪等**，
-- 補跑或重試會把同一個狀態灌成好幾列，之後 count 就錯了。
-- 折衷是以「日」為粒度：同一天同一個 URL 只有一列（當天重跑覆蓋，冪等），
-- 跨天保留歷史。
--
-- inspected_on 用 GENERATED ALWAYS ... STORED 而非讓 ingest 端自己填：
-- 讓 ingest 端填等於把「這一欄必須是 inspected_at 的日期」變成口頭約定，
-- 填錯了不會有任何訊號，而且會直接破壞冪等性。由 DB 算就不可能不一致。
-- 時區固定 UTC（AT TIME ZONE 'UTC'），與 013 的 granularity CHECK 同一個理由：
-- date_trunc / ::date 的結果會隨 session TimeZone 變動，不釘死的話
-- 「從哪個 session 寫入」會決定它落在哪一天。

CREATE TABLE IF NOT EXISTS gsc_url_inspection (
  -- 與 gsc_daily_metrics.property 同一個值域、同一個理由（見該欄註解）。
  property       gsc_property NOT NULL,

  url            TEXT        NOT NULL,

  -- 我們呼叫 API 的時刻（不是 Google 檢查的時刻）。
  inspected_at   TIMESTAMPTZ NOT NULL,

  -- 冪等鍵的日粒度成員。由 DB 算，理由見上方。
  inspected_on   DATE        NOT NULL
                 GENERATED ALWAYS AS ((inspected_at AT TIME ZONE 'UTC')::DATE) STORED,

  -- API 的 coverageState。**刻意不加值域 CHECK**：Google 明講這是給人看的
  -- 敘述字串（"Submitted and indexed"、"Crawled - currently not indexed"…），
  -- 會隨介面文案改動、且會依帳號語系在地化，不是穩定的 enum。
  -- 硬綁 enum 只會讓某天 Google 改文案時整條 ingest 掛掉，卻換不到任何正確性。
  -- 這與下面 indexing_state 的處理刻意相反——差別在於後者是**文件化的 API enum**。
  coverage_state TEXT        NOT NULL,

  -- API 的 indexingState，是文件化的 enum，所以綁死值域。
  -- 若 Google 新增值，ingest 會**當場失敗**而不是靜默寫進一個沒人認得的字串。
  -- 這是刻意的：新的索引狀態是需要人看一眼、決定怎麼歸類的事件，
  -- 不該靠一個 'unknown' 降級桶把它藏起來（對照 013 的 unknown_ratio ——
  -- 那裡收 unknown 是因為上游 sanitizer 本來就會產生它，這裡沒有上游 sanitizer）。
  indexing_state TEXT        NOT NULL,

  -- API 的 lastCrawlTime。從未被抓取過的 URL 是 NULL——這是有意義的狀態
  -- （「Google 還沒來過」），不可用 epoch 之類的哨兵值假裝有值。
  last_crawl     TIMESTAMPTZ,

  ingested_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT gsc_url_inspection_uniq
    UNIQUE (property, url, inspected_on),

  -- 與 gsc_daily_metrics.page 同一個 btree 位元組上限考量。
  CONSTRAINT gsc_url_inspection_url_ck
    CHECK (url ~ '^https?://' AND octet_length(url) BETWEEN 8 AND 1024),

  -- 值域取自 Search Console API v1 urlInspection 文件。
  CONSTRAINT gsc_url_inspection_indexing_state_ck
    CHECK (indexing_state IN (
      'INDEXING_STATE_UNSPECIFIED',
      'INDEXING_ALLOWED',
      'BLOCKED_BY_META_TAG',
      'BLOCKED_BY_HTTP_HEADER',
      'BLOCKED_BY_ROBOTS_TXT'
    )),

  -- 不綁值域但要求非空：空字串代表 ingest 端沒對到欄位，那是 bug。
  -- 上界 200：這一欄不在任何索引裡（沒有 btree 位元組風險），但它是 Google
  -- 可任意改動的敘述字串，不設上限等於讓外部決定我們的列寬。
  CONSTRAINT gsc_url_inspection_coverage_state_ck
    CHECK (char_length(coverage_state) BETWEEN 1 AND 200),

  -- Google 不可能在我們查詢之後才抓取。違反 = 時區處理寫錯。
  CONSTRAINT gsc_url_inspection_last_crawl_ck
    CHECK (last_crawl IS NULL OR last_crawl <= inspected_at)
);

-- 「最近一次巡檢在什麼時候」與跨 URL 的批次檢視
CREATE INDEX IF NOT EXISTS gsc_url_inspection_inspected_idx
  ON gsc_url_inspection (inspected_on DESC);

-- 單一 URL 的狀態變化史（本表存在的主要理由）
CREATE INDEX IF NOT EXISTS gsc_url_inspection_url_inspected_idx
  ON gsc_url_inspection (url, inspected_on DESC);

-- 問題清單：只掃有問題的列。實務上絕大多數 URL 是 INDEXING_ALLOWED，
-- 所以這個 partial 索引遠小於全表。
-- INCLUDE 兩個狀態欄：問題清單一定要顯示這兩欄，不 INCLUDE 的話每一列都要
-- 回 heap 取值，index-only scan 直接失效。
CREATE INDEX IF NOT EXISTS gsc_url_inspection_problem_idx
  ON gsc_url_inspection (inspected_on DESC, url)
  INCLUDE (coverage_state, indexing_state)
  WHERE indexing_state <> 'INDEXING_ALLOWED';

-- ══════════════════════════════════════════════════════════════════════
-- 3. crawl_daily — 逐小時 crawler 流量聚合
-- ══════════════════════════════════════════════════════════════════════
--
-- 【⚠ 這張表的資料來源不是 Google Search Console】
-- Search Console API v1 只有四個 resource：searchAnalytics / sitemaps /
-- sites / urlInspection。**Crawl Stats 報表沒有公開 API**，
-- GSC 介面上那份「檢索統計」抓不下來。
-- 本表的資料只能來自我們自己的 log —— Loki（web-vitals / ingress 的 access log）
-- 或 Cloudflare logs。表名裡沒有 gsc_ 前綴就是為了讓這件事一眼可見，
-- 另外用 COMMENT ON 寫進 catalog，免得後人以為它是 GSC 匯入的、
-- 進而以為它跟 GSC 介面上的數字應該對得起來（對不起來，母體不同）。
--
-- 【彙總列的取捨：同樣不放】
-- 與 gsc_daily_metrics 同樣的理由：request_count 與 bytes 都可加總，
-- 下游自己 GROUP BY 就能得到任何切面，存彙總列只會引進 014 那個
-- 「忘了過濾就重複計算」的風險。
--
-- 但這張表有一個 014 沒有的陷阱要正面處理：**path_prefix 的哨兵值歧義**。
-- 若允許任意前綴共存（例如同時有 '/' 與 '/article' 兩列），
-- '/' 到底是「首頁這一個路徑」還是「全站合計」就沒有答案，
-- 而且兩種讀法下 SUM 的正確性剛好相反。這比 device='all' 更隱蔽，
-- 因為 '/' 看起來完全像一個正常的路徑值。
--
-- 解法：把 path_prefix 定義成**第一層路徑段的分桶**，用 regex 強制單層，
-- 讓所有桶天生互斥（disjoint），彙總只能靠 GROUP BY 得到：
--   '/'            = 網站根路徑本身
--   '/article'     = /article/... 底下全部
--   '/__other__'   = 不屬於任何具名桶的殘餘
-- 注意 '/__other__' 是**殘餘桶**不是**彙總桶**：它與其他桶互斥，
-- 加總它不會重複計算。這與 device='all' 是根本不同的東西，
-- 兩者長得像但語意相反，所以在這裡寫死。
-- '__other__' 這個名字不可能與真實路徑衝突（真實路徑不會長這樣），
-- 也不需要額外的 CHECK 去區分。
--
-- 【為什麼 path_prefix 用 regex 而 ua_group 用 enum —— 這個不一致是暫時的】
-- 複審正確地指出兩者是同一類東西（都是**我們定義的分桶**，不是從 log 撿來的
-- 原始值），照 ua_group 的論證，path_prefix 也該綁死 enum：新的第一層路徑段
-- 出現時應該當場失敗、由人決定開新桶還是併進 '/__other__'，
-- 而不是靜默長出一個沒人知道的桶、讓某個 dashboard 的「全站」組成悄悄改變。
-- 這裡暫時留 regex，唯一理由是**我還沒有經過查證的 vocus.cc 第一層路由清單**，
-- 用猜的值域填 enum 會在上線當天擋掉合法資料。
-- 待路由清單確認後應改為 enum（那是一個獨立的小 migration）。
--
-- 在那之前，regex 是**桶名的守衛而不是原始路徑的守衛**：percent-encode 的
-- 路徑（/%E5%B0%88%E9%A1%8C）與 @handle 都會被拒。這是刻意的——它們本來就
-- 該由 ingest 端映射成 '/__other__' 才寫進來。但要注意這代表
-- **ingest 端漏做映射時死的是整批**，不是那一列。

CREATE TABLE IF NOT EXISTS crawl_daily (
  -- UTC 日期。與 hour 一起構成時間桶。
  -- 刻意存 (date, hour) 兩欄而非單一 TIMESTAMPTZ：本表的主要查詢是
  -- 「某天各時段的分布」與「跨天同一時段的比較」，兩者都要 hour 獨立可 GROUP BY。
  date          DATE     NOT NULL,

  -- UTC 小時，0-23。
  hour          SMALLINT NOT NULL,

  -- crawler 分組。'other' 是殘餘桶（非 crawler 或未分類的 UA），與其他值互斥。
  -- 值域綁死：新的 crawler（例如未來的某個 AI bot）出現時，
  -- ingest 應該要當場失敗、由人決定給它一個新桶還是併進 'other'，
  -- 而不是靜默塞進去一個沒人定義的字串。
  ua_group      TEXT     NOT NULL,

  -- HTTP 狀態碼。
  status_code   SMALLINT NOT NULL,

  -- 第一層路徑分桶，定義見上方。
  path_prefix   TEXT     NOT NULL,

  request_count BIGINT   NOT NULL,

  -- 回應位元組總和。用 BIGINT：一小時的總流量輕易超過 INTEGER 上限（2.1GB）。
  bytes         BIGINT   NOT NULL,

  ingested_at   TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- 冪等 upsert 的衝突鍵。重跑同一區間得到同樣結果。
  CONSTRAINT crawl_daily_dim_uniq
    UNIQUE (date, hour, ua_group, status_code, path_prefix),

  CONSTRAINT crawl_daily_hour_ck
    CHECK (hour BETWEEN 0 AND 23),

  CONSTRAINT crawl_daily_ua_group_ck
    CHECK (ua_group IN (
      'googlebot-desktop', 'googlebot-smartphone', 'googlebot-image',
      'googlebot-other', 'bingbot', 'other-bot', 'human', 'other'
    )),

  -- HTTP 狀態碼的合法範圍。0 或 999 之類的 proxy 自創值擋在門外——
  -- 那些通常代表 log 解析沒對到欄位。
  CONSTRAINT crawl_daily_status_code_ck
    CHECK (status_code BETWEEN 100 AND 599),

  -- 單層路徑段，理由見上方。允許 '/'（根路徑）與 '/xxx'，
  -- 不允許 '/a/b'（多層會讓桶互相包含，破壞互斥性）。
  --
  -- 【octet_length 上限不可省 —— 複審實測抓到的漏洞】
  -- regex 只約束字元集，`*` 對長度完全不設限，而 path_prefix 在
  -- crawl_daily_dim_uniq 這個 unique 索引裡。實測 2,900 bytes 的隨機字元會撞
  --   ERROR: index row size 2936 exceeds btree version 4 maximum 2704
  -- 而**同樣長度的可壓縮字元（repeat('z',2900)）卻寫得進去**——
  -- 因為 btree 在檢查 2704 之前會先做 pglz 壓縮。
  -- 這正是 gsc_daily_metrics.page 註解裡說的「只在特定資料上才出現的失敗」，
  -- 本表原本漏了同一道防線。64 bytes 對「單層路徑段」綽綽有餘。
  CONSTRAINT crawl_daily_path_prefix_ck
    CHECK (path_prefix ~ '^/[A-Za-z0-9_.-]*$' AND octet_length(path_prefix) <= 64),

  -- 桶存在卻是 0 次請求沒有意義，通常代表聚合端產生了空桶。
  CONSTRAINT crawl_daily_request_count_ck
    CHECK (request_count > 0),

  -- bytes 可以是 0（例如 304 Not Modified 沒有 body），但不能是負數。
  CONSTRAINT crawl_daily_bytes_ck
    CHECK (bytes >= 0),

  -- 未來的桶一律是 bug（時區換算或視窗計算寫錯）。上下界與釘死 UTC 的理由
  -- 同 gsc_daily_metrics_date_ck。
  CONSTRAINT crawl_daily_date_ck
    CHECK (date BETWEEN DATE '2020-01-01' AND ((now() AT TIME ZONE 'UTC')::DATE + 1))
);

-- 時間範圍掃描（趨勢圖、新鮮度檢查）
CREATE INDEX IF NOT EXISTS crawl_daily_date_hour_idx
  ON crawl_daily (date DESC, hour DESC);

-- 「Googlebot 最近抓了哪些區塊」——固定 ua_group 看時間序列
CREATE INDEX IF NOT EXISTS crawl_daily_ua_date_idx
  ON crawl_daily (ua_group, date DESC);

-- 錯誤監控：只掃 4xx/5xx。正常情況下這是全表的一小部分。
CREATE INDEX IF NOT EXISTS crawl_daily_error_idx
  ON crawl_daily (date DESC, status_code)
  WHERE status_code >= 400;

-- ══════════════════════════════════════════════════════════════════════
-- 4. RLS —— 三表一律 default deny（與 013 完全一致）
-- ══════════════════════════════════════════════════════════════════════
--
-- 只 ENABLE，刻意不建立任何 policy：沒有 policy 的 RLS 表對所有非 bypass
-- 角色是「全部拒絕」。service_role 有 BYPASSRLS，管線照常讀寫。
-- 之後若要開放前端直讀，必須另開 migration 明確加 policy，不能靠預設。
--
-- 本檔刻意不含任何 ALTER POLICY：PostgreSQL 的 ALTER POLICY 沒有 IF EXISTS，
-- 帶它的 migration 天生非冪等（見 013 註解記錄的 0121_soft_delete 事故）。

ALTER TABLE gsc_daily_metrics  ENABLE ROW LEVEL SECURITY;
ALTER TABLE gsc_url_inspection ENABLE ROW LEVEL SECURITY;
ALTER TABLE crawl_daily        ENABLE ROW LEVEL SECURITY;

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
        'REVOKE ALL ON TABLE gsc_daily_metrics, gsc_url_inspection, crawl_daily FROM %I', r
      );
    END IF;
  END LOOP;
END
$$;

-- REVOKE ... FROM <role> 不會撤銷授予 PUBLIC 的權限（那是另一個獨立的 grantee）。
-- Supabase 預設不對 PUBLIC 授權，所以現況本來就安全；這一句是讓「將來有人
-- 對 public schema 下了 GRANT ... TO PUBLIC」時不會連帶開放這三張表。
REVOKE ALL ON TABLE gsc_daily_metrics, gsc_url_inspection, crawl_daily FROM PUBLIC;

-- ══════════════════════════════════════════════════════════════════════
-- 5. Catalog comments —— 讓「這是抽樣」與「來源不是 GSC」離開 migration 檔
-- ══════════════════════════════════════════════════════════════════════
--
-- 為什麼用 COMMENT ON 而不是只寫 SQL 註解（013 沒做，這是本檔新增的做法）：
-- SQL 註解只存在於這個檔案裡，下游要翻 repo 才看得到。COMMENT ON 寫進
-- pg_description，於是 `\d+`、Supabase Studio 的表格檢視、以及
-- **PostgREST 為有權限的角色產生的 OpenAPI** 都會直接顯示它。
-- 「這是抽樣不是全量」是本批表最容易被誤讀、且誤讀後果最嚴重的一件事，
-- 值得放在下游一定看得到的地方。
--
-- 【效益範圍要講準，不要高估】複審實測：無權限角色在 information_schema
-- 看到 0 列，所以 anon / authenticated 的 OpenAPI 裡根本沒有這三張表
-- （這正是第 4 段 RLS default deny 的預期結果）。也就是說本段的受益者是
-- **service_role 呼叫者、Supabase Studio、以及 psql `\d+`**，
-- 不是「任何用 API 讀的人」。這仍然涵蓋了所有真正會讀這些表的對象。
--
-- COMMENT ON 本身天生冪等（覆寫既有註解），不需要 IF NOT EXISTS。

COMMENT ON TABLE gsc_daily_metrics IS
  'Search Analytics API 逐日抽樣事實表。⚠ 這是 top-N 抽樣不是全量：API 每天每 property 每 search type 最多回 50,000 列，且官方明講只回 top rows、不保證涵蓋全部資料列。因此 SUM(clicks) 必然小於 GSC UI 上的當日總點擊，落差大小不可知。property 值域鎖成單一值以杜絕跨 property 重複計算。資料保留 16 個月、延遲 2-3 天。';

COMMENT ON COLUMN gsc_daily_metrics.position IS
  '1-based 加權平均排名。聚合時不可 AVG()，必須 SUM(position*impressions)/SUM(impressions)。對應 BigQuery searchdata_url_impression.sum_position（0-based 總和）：sum_position = (position-1)*impressions。';

COMMENT ON COLUMN gsc_daily_metrics.property IS
  '對應 BigQuery site_url。值域刻意鎖成單一值 https://vocus.cc/：實測 sc-domain:vocus.cc 與它回傳近乎相同的資料（配額共用 50K，數字絕對不可相加），鎖成單值讓跨 property 重複計算成為無法表示的狀態，而非需要查詢端自律的紀律問題。';

COMMENT ON TABLE gsc_url_inspection IS
  'URL Inspection API 索引狀態快照，每 URL 每日一列。⚠ 天生是抽樣：配額 2,000 QPD／property、600 QPM，一次一個 URL，不可能全站覆蓋。「表裡沒有這個 URL」意思是「我們沒查過它」，不等於「它沒被索引」。';

COMMENT ON TABLE crawl_daily IS
  '⚠ 資料來源不是 Google Search Console。Search Console API v1 只有 searchAnalytics/sitemaps/sites/urlInspection 四個 resource，Crawl Stats 報表沒有公開 API。本表資料來自我們自己的 log（Loki / Cloudflare logs），母體與 GSC 檢索統計不同，兩者數字對不起來是正常的。';

COMMENT ON COLUMN gsc_url_inspection.inspected_on IS
  '由 inspected_at 以 UTC 推導的生成欄位（GENERATED ALWAYS ... STORED），是冪等鍵 (property, url, inspected_on) 的成員：同一天重查同一 URL 會覆蓋，跨天保留歷史。⚠ upsert 時 on_conflict 參數要帶這一欄，但 payload 不可以帶（生成欄位，會回 SQLSTATE 428C9）。';

COMMENT ON COLUMN gsc_url_inspection.last_crawl IS
  'Google 上次抓取的時間；從未被抓取過是 NULL（有意義的狀態，不可用哨兵值假裝有值）。約束要求 last_crawl <= inspected_at，因此 ingest 端必須用**每列實際呼叫 API 的時刻**當 inspected_at；若整批共用 run 起始時刻，Google 在 run 進行中回報更新的 lastCrawlTime 會誤觸約束。';

COMMENT ON COLUMN crawl_daily.hour IS
  'UTC 小時 0-23，與 date 一起構成時間桶。⚠「是 UTC」這件事 schema 無法強制，只能靠 ingest 端遵守——這正是它必須寫進 catalog 而不只是 SQL 註解的原因。';

COMMENT ON COLUMN crawl_daily.path_prefix IS
  '第一層路徑段的分桶，regex 強制單層以保證各桶互斥。''/'' = 根路徑本身，''/__other__'' = 殘餘桶（非彙總桶，與其他桶互斥，加總不會重複計算）。刻意不設彙總哨兵值，避免 cwv_hourly.device=''all'' 那種重複計算風險。';
