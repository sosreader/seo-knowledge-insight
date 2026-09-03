-- 024_ai_sov.sql
-- AI 答案 share of voice（SoV）監測：逐次原始回應表 + 三個週級聚合視圖（S6.2）
--
-- 【編號】023 已被另一個分支占用（磁碟上看不到，team-lead 於派工時指明），
-- 本檔取 024。013 的註解記過一次同編號相撞的事故
-- （`duplicate key ... Key (version)=(012)`），「往上加 1」不是可靠做法。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【這張表量的是什麼，以及它的成熟度】
-- ══════════════════════════════════════════════════════════════════════
--
-- 對一組固定的 prompt panel（data/ai_sov_prompts.json，repo 內靜態清單）
-- 反覆詢問 LLM，記錄回應裡的 citation 有沒有出現 vocus.cc、出現在第幾位。
--
-- ⚠ 這是**低成熟度指標**。三件事必須寫在資料庫的 catalog 註解裡，
--   因為它的受害者是「直接查這張表畫圖的下一個人」：
--
--   1. **單次回應不可解讀。** 同一個 prompt 問兩次，LLM 可能給完全不同的來源
--      組合——這是 sampling temperature 與檢索端的本質變異，不是站方可見度變了。
--      所以每個 prompt 一次 run 要重複 N 次（預設 3），且**只看週級趨勢**。
--   2. **分母不是「所有回應」。** 有一類回應根本沒有觸發檢索、零 citation
--      （grounding='ungrounded'）。把它算進「沒引用 vocus」的分母，會讓
--      provider 端的檢索行為變動偽裝成站方可見度下降。聚合視圖一律以
--      grounded 回應為分母，並同時把 ungrounded 佔比曝出來當降級訊號。
--   3. **樣本數很小。** 36 prompt × 3 次 = 一週 108 列。任何小於幾個百分點的
--      週間變化都在雜訊裡；判讀規則見報告 S6.2-ai-sov/design-and-smoke.md。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【為什麼要有 week_start 這一欄，而不是只存 run_at】
-- ══════════════════════════════════════════════════════════════════════
--
-- 資料品質 gate 的空段檢查（scripts/data_quality_gate.py expected_timestamps）
-- 用 `_floor_to_cadence()` 把週頻管線的預期時間點對齊到**週一 00:00 UTC**，
-- 然後拿這個集合跟表裡實際出現的時間戳做集合比對。時間戳若是 run_at
-- （週一 06:20 之類），它跟預期的週一 00:00 永遠對不上，空段檢查會把
-- 每一週都判成缺席——這不是門檻調不調的問題，是對齊方式本身錯了。
-- cwv_hourly 的 CrUX 那條週頻管線正是先把時間戳對齊到週一才過得了這關。
--
-- 所以 week_start 是**桶標籤**（永遠是週一），run_at 是**事實**（實際跑的時刻），
-- 兩者都存。CHECK 綁死兩件事讓錯誤標籤無法被表示：
--   - week_start 必須是 ISO 週一（ISODOW = 1）
--   - run_at 的 UTC 日期必須落在 [week_start, week_start+6] 內
-- 沒有第二個約束的話，「跑在第 3 週卻標成第 1 週」是可以寫進去的，
-- 而它的錯誤形式是靜默的（趨勢圖上一條看起來很正常的線）。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【冪等性】
-- ══════════════════════════════════════════════════════════════════════
--
-- 唯一鍵 (week_start, provider, model, prompt_id, repeat_idx)：同一週重跑
-- 整個 panel 會**覆蓋**該週的列，不是追加。這是刻意的——「一週量一次」是
-- 這個指標的設計前提（見上方第 1 點），同一週的第二次量測是重跑不是新樣本，
-- 追加會讓週級比例的分母隨重跑次數浮動，變成一個沒有定義的數字。
--
-- PostgreSQL 的 ADD CONSTRAINT 沒有 IF NOT EXISTS（021/022 註解已記過），
-- 一律 DROP CONSTRAINT IF EXISTS 前置。CREATE TABLE IF NOT EXISTS /
-- CREATE INDEX IF NOT EXISTS / CREATE OR REPLACE VIEW / COMMENT ON / GRANT
-- 天生冪等；CREATE POLICY 沒有 IF NOT EXISTS → DROP POLICY IF EXISTS 前置（照 018/020/022）。
-- 本檔可重跑任意次。
--
-- 【lock 影響】只建新表與新視圖，不 ALTER 任何既有表，對既有管線零 lock 影響。


-- ══════════════════════════════════════════════════════════════════════
-- 1. ai_sov_response —— 逐次原始回應（一列 = 一個 prompt 的一次重複）
-- ══════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS ai_sov_response (
  -- 週桶標籤，永遠是 UTC 的 ISO 週一（見上方說明）。
  week_start      DATE             NOT NULL,

  -- 這一列實際被查詢的時刻。與 week_start 的關係由 run_at_in_week_ck 綁死。
  run_at          TIMESTAMPTZ      NOT NULL,

  -- provider 是「哪一家」（openai / fake / 未來的 perplexity…），
  -- model 是那一家底下的具體模型。分兩欄而不是一欄串起來：換模型不換家時，
  -- 趨勢要能同時看「這一家整體」與「這個模型」兩個切面。
  provider        TEXT             NOT NULL,
  model           TEXT             NOT NULL,

  -- 對應 data/ai_sov_prompts.json 的 id / theme。theme 冗餘存一份是刻意的：
  -- panel 是 repo 內的檔案，會隨時間改；歷史列必須保住「當時是哪個主題」，
  -- 否則主題改名就會讓舊資料的分群靜默漂移。
  prompt_id       TEXT             NOT NULL,
  prompt_theme    TEXT             NOT NULL,

  -- 同一個 prompt 在同一次 run 內的第幾次重複，0-based。
  repeat_idx      SMALLINT         NOT NULL,

  -- 'grounded' = 這次回應至少帶回一個 citation；'ungrounded' = 零 citation。
  -- ungrounded 的回應**沒有引用任何人**，把它算進 SoV 的分母等於把 provider
  -- 端的檢索行為變動記到站方頭上。聚合視圖一律排除，並另外把它的佔比
  -- 當靜默降級訊號監測（quality_gate_config.py 的 DegradationConfig）。
  grounding       TEXT             NOT NULL,

  -- 這次回應的 citation 裡有沒有 vocus.cc（含子網域；創作者自訂網域**不算**，
  -- 見 scripts/ai_sov_providers.py is_target_domain() 的已知缺口說明）。
  cited           BOOLEAN          NOT NULL,

  -- vocus.cc 第一次出現在 citation 序列裡的位置，1-based。
  -- 序列＝回應中 citation 依出現順序、以 URL 去重後的清單（cited_urls 的順序）。
  citation_rank   SMALLINT,

  citation_count  SMALLINT         NOT NULL,

  -- 去重後、依出現順序保留的 citation URL 與其網域。
  -- domain 另存一份而不是每次從 URL 現算：網域正規化規則（去 www.、去 port、
  -- 轉小寫）會隨時間調整，歷史列要保住當時的判定，否則規則一改，
  -- 過去每一週的競品佔比都會跟著變，趨勢就不再是趨勢。
  cited_urls      TEXT[]           NOT NULL,
  cited_domains   TEXT[]           NOT NULL,

  -- 回應全文**不入庫**：它是 LLM 生成的自由文本，可能含個資或引用片段，
  -- 而 SoV 的判讀完全不需要它。只留長度與 sha256 摘要，用來事後比對
  -- 「這兩次回應是不是同一份」（重複度過高 = provider 端有快取，
  -- 那會讓 N 次重複失去變異性抽樣的意義）。
  response_chars  INTEGER          NOT NULL,
  response_hash   TEXT             NOT NULL,

  ingested_at     TIMESTAMPTZ      NOT NULL DEFAULT now(),

  -- 冪等 upsert 的衝突鍵（見模組頂端【冪等性】）。
  CONSTRAINT ai_sov_response_uniq
    UNIQUE (week_start, provider, model, prompt_id, repeat_idx)
);

-- ── CHECK：讓錯誤狀態無法被表示（013/015/022 一路下來的紀律）──────────

-- 週桶標籤必須是 ISO 週一。gap 檢查對齊到週一，標成別的日子在集合比對時
-- 永遠對不上，而且失敗形式是「每一週都被判成空段」這種看似門檻問題的假象。
ALTER TABLE ai_sov_response DROP CONSTRAINT IF EXISTS ai_sov_response_week_start_ck;
ALTER TABLE ai_sov_response ADD CONSTRAINT ai_sov_response_week_start_ck
  CHECK (EXTRACT(ISODOW FROM week_start) = 1);

-- run_at 必須落在它自己宣稱的那一週內。用 (run_at AT TIME ZONE 'UTC')::DATE
-- 而不是直接跟 week_start 比較：TIMESTAMPTZ 對 DATE 的隱式轉換會吃 session
-- 的 TimeZone 設定，同一列在不同連線下可能一次通過一次失敗（理由同
-- gsc_daily_totals_date_ck 釘死 UTC 的那段註解）。
ALTER TABLE ai_sov_response DROP CONSTRAINT IF EXISTS ai_sov_response_run_at_in_week_ck;
ALTER TABLE ai_sov_response ADD CONSTRAINT ai_sov_response_run_at_in_week_ck
  CHECK ((run_at AT TIME ZONE 'UTC')::DATE BETWEEN week_start AND week_start + 6);

ALTER TABLE ai_sov_response DROP CONSTRAINT IF EXISTS ai_sov_response_grounding_ck;
ALTER TABLE ai_sov_response ADD CONSTRAINT ai_sov_response_grounding_ck
  CHECK (grounding IN ('grounded', 'ungrounded'));

-- grounding 是 citation_count 的函數，不是獨立事實。寫成 CHECK 而不是
-- generated column 是為了讓「寫入端算錯」直接撞牆——generated column 會
-- 默默幫忙算對，反而蓋掉上游的 bug。
ALTER TABLE ai_sov_response DROP CONSTRAINT IF EXISTS ai_sov_response_grounding_consistency_ck;
ALTER TABLE ai_sov_response ADD CONSTRAINT ai_sov_response_grounding_consistency_ck
  CHECK ((grounding = 'grounded') = (citation_count > 0));

-- rank 與 cited 必須成對出現，且 rank 不能超出這次的 citation 數。
-- 「cited=true 但 rank 是 NULL」與「cited=false 卻有 rank」都是解析端的
-- 典型錯誤，兩者在報表上都不會報錯，只會讓平均排名偷偷偏移。
ALTER TABLE ai_sov_response DROP CONSTRAINT IF EXISTS ai_sov_response_rank_pairing_ck;
ALTER TABLE ai_sov_response ADD CONSTRAINT ai_sov_response_rank_pairing_ck
  CHECK (
    (cited AND citation_rank IS NOT NULL AND citation_rank >= 1 AND citation_rank <= citation_count)
    OR (NOT cited AND citation_rank IS NULL)
  );

-- 陣列長度必須與 citation_count 一致（三個欄位描述的是同一件事，不可各說各話）。
ALTER TABLE ai_sov_response DROP CONSTRAINT IF EXISTS ai_sov_response_arrays_ck;
ALTER TABLE ai_sov_response ADD CONSTRAINT ai_sov_response_arrays_ck
  CHECK (
    cardinality(cited_urls) = citation_count
    AND cardinality(cited_domains) = citation_count
  );

ALTER TABLE ai_sov_response DROP CONSTRAINT IF EXISTS ai_sov_response_counts_ck;
ALTER TABLE ai_sov_response ADD CONSTRAINT ai_sov_response_counts_ck
  CHECK (repeat_idx >= 0 AND citation_count >= 0 AND response_chars >= 0);

-- sha256 hex。形狀鎖住是為了擋「不小心把回應全文塞進這一欄」——
-- 那是本表最不想發生的事（見欄位註解），而它不會有任何錯誤訊號。
ALTER TABLE ai_sov_response DROP CONSTRAINT IF EXISTS ai_sov_response_hash_ck;
ALTER TABLE ai_sov_response ADD CONSTRAINT ai_sov_response_hash_ck
  CHECK (response_hash ~ '^[0-9a-f]{64}$');

-- 唯一的查詢型態是「依週掃描」（趨勢圖、新鮮度、空段檢查）。
-- unique constraint 附帶的索引以 week_start 開頭，理論上夠用，但它的
-- 用途主要是 upsert 衝突偵測；另建一個純 week_start DESC 的索引讓
-- 「最新一週」這個最常見的查詢不必掃複合索引的前綴（理由同 015/022）。
CREATE INDEX IF NOT EXISTS ai_sov_response_week_idx
  ON ai_sov_response (week_start DESC);


-- === RLS：與 013/015/016/022 完全一致的 default deny ===
ALTER TABLE ai_sov_response ENABLE ROW LEVEL SECURITY;

-- 縱深防禦第一層：撤掉 Supabase 對 public schema 的預設 GRANT。
-- 角色不存在（本機純 postgres）時跳過，與 013/015/016/022 的 role 判斷同款。
DO $$
DECLARE
  r TEXT;
BEGIN
  FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('REVOKE ALL ON TABLE ai_sov_response FROM %I', r);
    END IF;
  END LOOP;
END
$$;

-- 縱深防禦第二層：REVOKE ... FROM <role> 不會撤銷授予 PUBLIC 的權限
-- （那是獨立的 grantee），理由同 015/022。
REVOKE ALL ON TABLE ai_sov_response FROM PUBLIC;


-- === Catalog comments ===
COMMENT ON TABLE ai_sov_response IS
  'AI 答案 share of voice 的**逐次原始回應**：一列 = prompt panel 裡的一個 prompt 在某一週的第 N 次重複。'
  '⚠ 【低成熟度指標，單次回應與單週單點都不可解讀】同一個 prompt 問兩次可能得到完全不同的來源組合，'
  '那是 LLM 取樣與檢索端的本質變異，不是站方可見度變了。判讀一律走週級聚合視圖 ai_sov_weekly，'
  '且需要 4 週以上的序列才談得上趨勢。'
  '⚠ 【分母是 grounded 回應，不是全部回應】grounding=''ungrounded'' 的回應零 citation、沒有引用任何人，'
  '算進分母會讓 provider 端的檢索行為變動偽裝成站方可見度下降。ai_sov_weekly 已排除，'
  '並把 ungrounded_ratio 另外曝出來當降級訊號。自己寫查詢時務必比照，否則得到的是一個會自己漂移的數字。'
  '⚠ 【樣本很小】36 prompt × 3 次 = 一週 108 列。幾個百分點的週間變化在雜訊裡。'
  '⚠ 【SoV 下降不等於站方問題】先用同一份資料的 ai_sov_weekly_domain 看同類競品網域是不是同步下降'
  '（背離產業判別法，見報告 .verification/2026-08-29-seo-capability/S6.2-ai-sov/design-and-smoke.md）。'
  '冪等性：同一週重跑整個 panel 會覆蓋該週的列，不是追加——「一週量一次」是這個指標的設計前提。';

COMMENT ON COLUMN ai_sov_response.week_start IS
  '週桶標籤，永遠是 UTC 的 ISO 週一（CHECK 綁死）。資料品質 gate 的空段檢查把週頻管線對齊到週一 00:00 UTC 做集合比對，'
  '時間戳若用 run_at 就永遠對不上、每一週都會被判成空段。run_at 才是實際執行時刻，兩者不可互換。';

COMMENT ON COLUMN ai_sov_response.grounding IS
  '''grounded'' = 這次回應至少帶回一個 citation；''ungrounded'' = 零 citation。'
  '⚠ ungrounded 不代表「沒引用 vocus」，是「沒引用任何人」——它通常表示 provider 這次沒有觸發檢索'
  '（模型改版、工具停用、prompt 被安全政策擋下）。它的佔比是本管線的靜默降級指標：'
  '總量看起來正常、SoV 卻整批下滑時，先看這個數字有沒有同步上升。';

COMMENT ON COLUMN ai_sov_response.citation_rank IS
  'vocus.cc 第一次出現在 citation 序列的位置，1-based；未被引用時為 NULL（CHECK 綁死成對關係）。'
  '序列定義＝回應中 citation 依出現順序、以 URL 去重後的清單，也就是 cited_urls 的順序。'
  '⚠ 這不是 SERP 排名，不同 provider 的 citation 呈現方式不同，跨 provider 比較 rank 沒有意義。';

COMMENT ON COLUMN ai_sov_response.response_hash IS
  '回應全文的 sha256 hex。**全文刻意不入庫**（自由生成文本，可能含個資或第三方內容片段，而 SoV 判讀不需要它）。'
  '同一 prompt 多次重複若 hash 全部相同，代表 provider 端有快取，N 次重複就失去變異性抽樣的意義——'
  '那時 N 次的比例是假的精確度，要在報告裡標明。';


-- ══════════════════════════════════════════════════════════════════════
-- 2. 週級聚合視圖 —— 判讀一律走這裡，不直接查底表
-- ══════════════════════════════════════════════════════════════════════
--
-- 【security_invoker = true 不可省】理由見 016 的完整論證：預設的 view 是
-- security definer 語意，會繞過底表的 RLS default deny。三個視圖全部照抄不改。

-- 2a. 每 prompt 每週的被引用比例
CREATE OR REPLACE VIEW ai_sov_weekly_prompt
  WITH (security_invoker = true) AS
SELECT
  week_start,
  provider,
  model,
  prompt_id,
  prompt_theme,
  count(*)::INTEGER                                                AS responses,
  count(*) FILTER (WHERE grounding = 'grounded')::INTEGER          AS grounded_responses,
  count(*) FILTER (WHERE cited)::INTEGER                           AS cited_responses,
  -- 分母是 grounded 不是 responses（見底表註解）。分母為 0 時回 NULL 而不是 0——
  -- 「這週這個 prompt 一次都沒觸發檢索」與「觸發了但沒引用我們」是兩件事，
  -- 用 0 表示前者就是任務書禁止的「查不到資料以 0 呈現」。
  CASE WHEN count(*) FILTER (WHERE grounding = 'grounded') = 0 THEN NULL
       ELSE count(*) FILTER (WHERE cited)::DOUBLE PRECISION
            / count(*) FILTER (WHERE grounding = 'grounded')
  END                                                              AS cite_rate,
  avg(citation_rank) FILTER (WHERE cited)                          AS avg_citation_rank
FROM ai_sov_response
GROUP BY week_start, provider, model, prompt_id, prompt_theme;

COMMENT ON VIEW ai_sov_weekly_prompt IS
  '每個 prompt 每週的被引用比例。cite_rate 的分母是 grounded 回應數，不是總回應數；'
  '該週該 prompt 完全沒有 grounded 回應時 cite_rate 為 NULL（不是 0，那會被誤讀成「有機會但沒被引用」）。'
  '⚠ 單一 prompt 一週只有 3 個樣本，比例只會是 0 / 0.33 / 0.67 / 1，逐 prompt 的週間變化幾乎全是雜訊；'
  '這個視圖的用途是找「長期為 0 的主題」，不是看單週漲跌。';

-- 2b. 每週整體 SoV
CREATE OR REPLACE VIEW ai_sov_weekly
  WITH (security_invoker = true) AS
SELECT
  week_start,
  provider,
  model,
  sum(responses)::INTEGER                                          AS responses,
  sum(grounded_responses)::INTEGER                                 AS grounded_responses,
  sum(cited_responses)::INTEGER                                    AS cited_responses,
  count(*)::INTEGER                                                AS prompts_measured,
  count(*) FILTER (WHERE cite_rate IS NOT NULL)::INTEGER           AS prompts_with_grounded_answer,
  -- pooled：把所有 grounded 回應倒進同一個池子算比例。受「某些 prompt 特別容易
  -- 觸發檢索」影響——那些 prompt 會貢獻比較多分母，等於被加權。
  CASE WHEN sum(grounded_responses) = 0 THEN NULL
       ELSE sum(cited_responses)::DOUBLE PRECISION / sum(grounded_responses)
  END                                                              AS sov_pooled,
  -- macro：每個 prompt 先各自算比例再取平均，每個 prompt 權重相同。
  -- **這個是頭條數字**：panel 的設計意圖就是「12 個主題各佔一份」，
  -- pooled 會讓檢索觸發率高的主題悄悄放大自己的權重。
  avg(cite_rate)                                                   AS sov_macro,
  CASE WHEN sum(responses) = 0 THEN NULL
       ELSE 1 - sum(grounded_responses)::DOUBLE PRECISION / sum(responses)
  END                                                              AS ungrounded_ratio
FROM ai_sov_weekly_prompt
GROUP BY week_start, provider, model;

COMMENT ON VIEW ai_sov_weekly IS
  '每週整體 AI 答案 share of voice。**頭條數字是 sov_macro**（每個 prompt 權重相同，對齊 panel「12 主題各一份」的設計意圖）；'
  'sov_pooled 併在旁邊供對照，兩者差很多時代表某些主題的檢索觸發率明顯高於其他主題。'
  '⚠ 【讀之前先看 ungrounded_ratio 與 prompts_with_grounded_answer】ungrounded_ratio 跳升時，'
  'SoV 的變化多半來自 provider 端的檢索行為，不是站方可見度——這是本指標最常見的誤判來源。'
  '⚠ 【需要 4 週以上才談趨勢】一週 108 個樣本，單週的幾個百分點在雜訊裡。'
  '⚠ 【下降時先做背離產業判別】用 ai_sov_weekly_domain 看同類 UGC／內容平台網域是不是同步下降：'
  '同步下降＝產業或 provider 端現象；只有 vocus.cc 下降＝站方獨立訊號。方法論出處見'
  'reports/2026-05-24-seo-weekly-report-20260522-indexing-recovery.md 的「AI 引擎背離偵測法」。';

-- 2c. 每週各網域的引用佔比（競品／背離產業判別的資料來源）
CREATE OR REPLACE VIEW ai_sov_weekly_domain
  WITH (security_invoker = true) AS
WITH grounded AS (
  SELECT week_start, provider, model, cited_domains
  FROM ai_sov_response
  WHERE grounding = 'grounded'
),
totals AS (
  SELECT week_start, provider, model, count(*)::INTEGER AS grounded_responses
  FROM grounded
  GROUP BY week_start, provider, model
),
per_domain AS (
  -- 一個回應引用同一個網域兩次只算一次：cited_domains 在寫入端已隨 cited_urls
  -- 去重，但去重的是 URL 不是 domain，同站兩篇文章會留下兩個相同 domain。
  -- 這裡要算的是「多少個回應提到這個網域」，所以在 LATERAL 內先把 domain 去重，
  -- 讓每個回應對每個 domain 恰好貢獻一列，外層直接 count(*) 即可。
  -- **不可**改寫成 count(DISTINCT g.*)：grounded 這個 CTE 沒有選出唯一鍵，
  -- 兩個不同 prompt 若剛好引用同一組網域，整列會完全相同而被 DISTINCT 併成一個，
  -- 得到一個偏低且不會報錯的分子。
  SELECT g.week_start, g.provider, g.model, x.d AS domain,
         count(*)::INTEGER AS responses_citing
  FROM grounded g
  CROSS JOIN LATERAL (
    SELECT DISTINCT u FROM unnest(g.cited_domains) AS u
  ) AS x(d)
  GROUP BY g.week_start, g.provider, g.model, x.d
)
SELECT
  p.week_start,
  p.provider,
  p.model,
  p.domain,
  p.responses_citing,
  t.grounded_responses,
  p.responses_citing::DOUBLE PRECISION / t.grounded_responses AS domain_share
FROM per_domain p
JOIN totals t
  ON t.week_start = p.week_start AND t.provider = p.provider AND t.model = p.model;

COMMENT ON VIEW ai_sov_weekly_domain IS
  '每週每個被引用網域出現在多少個 grounded 回應裡，以及佔 grounded 回應的比例。'
  '這是**背離產業判別法**的資料來源：vocus.cc 的 SoV 下降時，先看同類 UGC／內容平台網域'
  '（例如其他中文寫作平台、論壇、部落格站）是不是同步下降。同步＝產業或 provider 端現象；'
  '只有 vocus.cc 下降＝站方獨立訊號，這時才值得往內容或索引方向查。'
  '⚠ domain_share 的分母是該週 grounded 回應總數，各網域的 share 相加會大於 1'
  '（一個回應通常引用多個網域），這不是錯誤，不要拿去當百分比堆疊圖的分子。';


-- ══════════════════════════════════════════════════════════════════════
-- 3. seo_dashboard_ro 的讀取權
-- ══════════════════════════════════════════════════════════════════════
--
-- 【為什麼在這一支】019 定下的原則：授予讀取權的動作應該和產生資料的那一步
-- 在同一個變更裡，否則就是「沒人記得為什麼存在的授權」。
--
-- 【兩件事缺一不可】底表是 ENABLE RLS + 零 policy 的 default deny，
-- 只 GRANT 不加 policy 的話這個角色一列都讀不到，而且會回 HTTP 200 + 空陣列、
-- 不會報錯（018 說的「最難察覺的失敗形狀」）。
--
-- 【視圖也要 GRANT】security_invoker = true 的視圖不會替呼叫者繞過權限：
-- 讀視圖需要視圖本身的 SELECT 權，底表的 RLS policy 也照樣套用。兩層都要給。
--
-- 【逐物件列名，不用 ALL TABLES】理由見 018：ALL TABLES 會讓之後任何人新建的表
-- 自動落進這個角色的讀取範圍，而那個人不會知道。

GRANT SELECT ON TABLE ai_sov_response TO seo_dashboard_ro;
GRANT SELECT ON ai_sov_weekly_prompt  TO seo_dashboard_ro;
GRANT SELECT ON ai_sov_weekly         TO seo_dashboard_ro;
GRANT SELECT ON ai_sov_weekly_domain  TO seo_dashboard_ro;

-- USING (true)：本表沒有租戶維度，範圍寫在 GRANT 的物件清單上（只有這幾個物件），
-- 不需要在 policy 述詞上再裁切——與 018/020/022 對其餘表的處理一致。
DROP POLICY IF EXISTS seo_dashboard_ro_select ON ai_sov_response;
CREATE POLICY seo_dashboard_ro_select ON ai_sov_response
  FOR SELECT TO seo_dashboard_ro USING (true);


-- ══════════════════════════════════════════════════════════════════════
-- === 套用後應成立的狀態 ===
-- ══════════════════════════════════════════════════════════════════════
--
-- 結構：
--   ai_sov_response 存在，relrowsecurity = true，
--   pg_policies 對它恰一條（seo_dashboard_ro_select，cmd=SELECT，roles={seo_dashboard_ro}）。
--   三個視圖存在，reloptions 皆含 security_invoker=true。
--
-- 寫入行為（測資以 week_start='2026-08-31'（週一）為例）：
--   week_start='2026-09-01'（週二）                      → 被 week_start_ck 擋下
--   run_at='2026-09-08T00:00Z' 配 week_start='2026-08-31' → 被 run_at_in_week_ck 擋下
--   grounding='grounded' 配 citation_count=0             → 被 grounding_consistency_ck 擋下
--   cited=true 配 citation_rank=NULL                     → 被 rank_pairing_ck 擋下
--   cited=false 配 citation_rank=1                       → 被 rank_pairing_ck 擋下
--   cited=true 配 citation_rank=5、citation_count=3      → 被 rank_pairing_ck 擋下
--   cardinality(cited_urls)=2 配 citation_count=3        → 被 arrays_ck 擋下
--   response_hash='not-a-hash'                           → 被 hash_ck 擋下
--   合法列（週一、rank 成對、陣列長度一致、hash 為 64 位 hex）→ 成功
--   同一組 (week_start, provider, model, prompt_id, repeat_idx) 連續 upsert 兩次
--     → 表內仍只有一列，第二次的值覆蓋第一次
--
-- 視圖語意：
--   某 prompt 該週三次全部 ungrounded → ai_sov_weekly_prompt.cite_rate 為 NULL（不是 0）
--   ai_sov_weekly.sov_macro 為各 prompt cite_rate 的平均（NULL 不參與平均）
--   ai_sov_weekly_domain 各 domain 的 domain_share 相加可大於 1（一個回應多網域）
--
-- 權限（開一道窄門，不是把門拆了——018/019/020/022 沿用的驗收方式）：
--   has_table_privilege('seo_dashboard_ro','ai_sov_response','SELECT')     → true
--   has_table_privilege('seo_dashboard_ro','ai_sov_weekly','SELECT')       → true
--   has_table_privilege('seo_dashboard_ro','seo_change_log','SELECT')      → false（不變）
--   has_table_privilege('seo_dashboard_ro','qa_items','SELECT')            → false（不變）
--   information_schema.role_table_grants where grantee='seo_dashboard_ro'
--     → 022 收尾時的 8 列 + 本檔新增的 4 個物件，共 12 列，全部是 SELECT。
--
-- 既有資料：本檔不 ALTER 任何既有表、不寫入也不刪除任何既有列。
