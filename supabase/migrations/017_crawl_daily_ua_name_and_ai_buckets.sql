-- 017_crawl_daily_ua_name_and_ai_buckets.sql
-- crawl_daily 新增 ua_name（具名 bot，進冪等鍵）+ 放寬 ua_group 值域
--
-- 【編號】新增前已現場 `ls supabase/migrations/` 確認：現況最大為 016，本檔為 017。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【為什麼要加 ua_name —— 分類法被烤進了儲存鍵】
-- ══════════════════════════════════════════════════════════════════════
--
-- 015 的冪等鍵是 (date, hour, ua_group, status_code, path_prefix)，
-- 也就是說**當下挑的分群方式，就是這份資料永遠的粒度**。
--
-- 這對 crawler 特別致命，因為 AI crawler 的分類一定會改：它們的行為與商業模式
-- 都還在變（今天只抓語料的 bot 明天可能開始回連）。等到要重新分類時，
-- **Loki 的原始 log 早就過了 168h 保留期，沒有東西可以重算**。
-- 粗桶不能分解成細桶——這與 014 的論證同形（p75 不能跨桶重組，
-- 所以未分群的 origin p75 必須另存一列）。同一條原則：
--
--     能不能事後重算，決定了現在必須存多細。
--
-- 所以改成：
--   ua_name  = **原始事實**，正規化後的具名 bot 識別字（進冪等鍵）
--   ua_group = **衍生標籤**，隨時可以由 ua_name 重算（不進冪等鍵）
--
-- 於是日後重新分類只是一句 UPDATE（或下游 view 重新 CASE WHEN），
-- 不需要原始 log，也不需要資料遷移。
--
-- 【本次是零成本的時機】crawl_daily 目前 0 列（本檔撰寫時以
-- `Prefer: count=exact` 確認），欄位與鍵都可以自由重構、沒有資料遷移問題。
-- 這件事現在不做，之後每過一小時成本就變高一點。
--
-- 【ua_name 用格式 CHECK，ua_group 用值域 CHECK —— 這個不對稱是刻意的】
-- ua_group 是我們定義的分類，出現沒定義的值代表 ingest 端與 schema 分岔了，
-- 應該當場失敗 ⇒ 綁死值域。
-- ua_name 是觀測到的事實，新的 crawler 隨時會冒出來，**綁死值域會讓
-- 「世界上出現了新 bot」變成一次 migration 才能記錄的事**，而在那之前
-- 整批寫入會被打回、資料直接遺失（正是我們最不想要的）。
-- 所以 ua_name 只約束格式與長度：格式讓它保持可比對（不會同一支 bot
-- 出現大小寫兩種寫法），長度是因為**它進了 unique 索引**——
-- 015 對 path_prefix 的實測記錄在此同樣適用：btree 索引列超過 2704 bytes 會炸，
-- 而且因為 pglz 會先壓縮，**同樣長度的可壓縮字串卻寫得進去**，
-- 於是那是一種「只在特定資料上才出現的失敗」。64 bytes 對識別字綽綽有餘。
--
-- ⚠ ua_name 刻意**不是完整 UA 字串**（隱私要求：不寫原始 log、不寫 IP、
-- 不寫完整 UA），是 classifier 比對出來的正規化識別字，例如
-- amazonbot / claude-searchbot / googlebot-smartphone。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【ua_group 放寬：五個新桶，依「這個 bot 影響什麼決策」分】
-- ══════════════════════════════════════════════════════════════════════
--
-- 2026-09-01 對 prod Loki 單一小時實測（證據：knowledge-base
-- .verification/2026-08-29-seo-capability/S4.1-crawl-dashboard/）：
-- crawler 流量 8,230 次，Googlebot 全家只佔 1,393（17%），
-- 而 015 的值域裡沒有任何一個桶裝得下另外那 6,000 多次。
--
--   ai-search-bot   會回連、會帶 referral 的 AI 搜尋抓取
--                   （Claude-SearchBot / Claude-User / OAI-SearchBot /
--                    ChatGPT-User / PerplexityBot / YouBot / ExaSearchBot）
--   ai-training-bot 純語料抓取，沒有面向使用者的搜尋介面
--                   （ClaudeBot / GPTBot / Bytespider / meta-webindexer / AIWebIndex）
--   ai-mixed-bot    同時做語料抓取與面向使用者的搜尋／助理介面（Applebot / Amazonbot）
--   seo-tool-bot    第三方 SEO 稽核爬蟲（Ahrefs / Semrush / DataForSeo / SERanking）
--   social-bot      分享預覽抓取（facebookexternalhit / meta-externalads / Dcard）
--
-- 【為什麼 ai-mixed-bot 必須獨立成一個值，而不是註解一句「有歧義」】
-- Applebot 同時餵 Siri／Spotlight 搜尋，Amazonbot 同時餵 Alexa，
-- 兩者都不是純語料抓取。把它們塞進 ai-training-bot 的後果不是「分類不精確」，
-- 而是**任何人 SUM(request_count) WHERE ua_group='ai-training-bot' 拿到的數字
-- 會靜默包含會回連的 bot**——而歧義只活在 COMMENT 裡，**COMMENT 不參與加總**。
-- 更糟的是這兩支在本站是 crawler 流量的最大宗（2,735/8,230 = 33%），
-- 等於那個桶主要由歧義項組成。
--
-- 獨立成桶之後三個數字都誠實：
--   ai-search-bot   = 「會回連」的**下界**
--   ai-training-bot = 「純成本」的**下界**
--   ai-mixed-bot    = 歧義本身，在資料裡看得見的一格
--
-- 原則：**不確定性要能被表示，不要用一次分類把它消掉。**
--
-- ══════════════════════════════════════════════════════════════════════
-- 【冪等性】
-- ══════════════════════════════════════════════════════════════════════
-- ADD COLUMN IF NOT EXISTS / DROP CONSTRAINT IF EXISTS + ADD CONSTRAINT /
-- CREATE INDEX IF NOT EXISTS / COMMENT ON —— 全部可重跑。
-- 本檔不含任何 ALTER POLICY（沒有 IF EXISTS，天生非冪等，見 013 註解的事故）。

-- ── 1. ua_name ────────────────────────────────────────────────────────
-- 目標表 0 列，所以 NOT NULL 不需要 DEFAULT 也不需要兩段式回填。
ALTER TABLE crawl_daily ADD COLUMN IF NOT EXISTS ua_name TEXT NOT NULL;

ALTER TABLE crawl_daily DROP CONSTRAINT IF EXISTS crawl_daily_ua_name_ck;
ALTER TABLE crawl_daily ADD CONSTRAINT crawl_daily_ua_name_ck
  CHECK (ua_name ~ '^[a-z0-9][a-z0-9._-]*$' AND octet_length(ua_name) <= 64);

-- ── 2. 冪等鍵改以 ua_name 為維度 ──────────────────────────────────────
-- ua_group 退出鍵：它是衍生標籤，同一個 ua_name 只會有一個 ua_group，
-- 重新分類時 upsert 會直接覆蓋該欄，不會產生第二列。
ALTER TABLE crawl_daily DROP CONSTRAINT IF EXISTS crawl_daily_dim_uniq;
ALTER TABLE crawl_daily ADD CONSTRAINT crawl_daily_dim_uniq
  UNIQUE (date, hour, ua_name, status_code, path_prefix);

-- ── 3. ua_group 值域放寬 ──────────────────────────────────────────────
ALTER TABLE crawl_daily DROP CONSTRAINT IF EXISTS crawl_daily_ua_group_ck;
ALTER TABLE crawl_daily ADD CONSTRAINT crawl_daily_ua_group_ck
  CHECK (ua_group IN (
    -- Google（沿用 015）
    'googlebot-desktop', 'googlebot-smartphone', 'googlebot-image', 'googlebot-other',
    -- 其他傳統搜尋引擎（沿用 015）
    'bingbot',
    -- 新增：依「影響什麼決策」分的五桶
    'ai-search-bot', 'ai-training-bot', 'ai-mixed-bot', 'seo-tool-bot', 'social-bot',
    -- 殘餘桶（沿用 015）。彼此互斥，加總不會重複計算。
    'other-bot', 'human', 'other'
  ));

-- ── 4. 索引 ───────────────────────────────────────────────────────────
-- 「某一支 bot 最近抓了什麼」——這是加了 ua_name 之後最直接的新查詢。
CREATE INDEX IF NOT EXISTS crawl_daily_ua_name_date_idx
  ON crawl_daily (ua_name, date DESC);

-- ── 5. Catalog comments ───────────────────────────────────────────────
COMMENT ON COLUMN crawl_daily.ua_name IS
  '正規化後的具名 crawler 識別字（amazonbot / claude-searchbot / googlebot-smartphone …），'
  '是本表的**原始事實**並構成冪等鍵的一部分。'
  '⚠ 不是完整 User-Agent 字串：本表只寫彙總計數，不寫原始 log、不寫 IP、不寫完整 UA。'
  '未命中任何具名 crawler 但 UA 含 bot/crawler/spider/slurp 者為 ''other-bot''；非 crawler 為 ''human''。'
  '值域刻意**不綁死**（只約束格式與長度）：新的 crawler 隨時會出現，綁死值域會讓'
  '「世界上多了一支 bot」變成必須先做 migration 才能記錄，而在那之前整批寫入會被打回、資料直接遺失。'
  '長度上限 64 bytes 是因為本欄在 unique 索引裡——btree 索引列超過 2704 bytes 會失敗，'
  '而 pglz 會先壓縮，所以那是一種只在特定資料上才出現的失敗。'
  '權威對照表在 scripts/crawl_taxonomy.py 的 TOKEN_TO_UA_GROUP。';

COMMENT ON COLUMN crawl_daily.ua_group IS
  'crawler 分群，是由 ua_name **衍生**的標籤，不屬於冪等鍵，可以隨時重算（UPDATE 或下游 view 重新分類）。'
  '分桶依據是「這個 bot 影響什麼決策」而非廠牌：'
  'ai-search-bot=會回連帶 referral 的 AI 搜尋（Claude-SearchBot/Claude-User/OAI-SearchBot/ChatGPT-User/PerplexityBot/YouBot/ExaSearchBot）；'
  'ai-training-bot=純語料抓取、沒有面向使用者的搜尋介面（ClaudeBot/GPTBot/Bytespider/meta-webindexer/AIWebIndex）；'
  'ai-mixed-bot=同時做語料抓取與面向使用者搜尋／助理介面（Applebot 餵 Siri、Amazonbot 餵 Alexa）——'
  '獨立成桶是因為把它們併進 ai-training-bot 會讓該桶的 SUM 靜默包含會回連的 bot，而歧義寫在 COMMENT 裡不會參與加總；'
  '於是 ai-search-bot 是「會回連」的下界、ai-training-bot 是「純成本」的下界、ai-mixed-bot 是歧義本身看得見的一格。'
  'seo-tool-bot=第三方 SEO 稽核（Ahrefs/Semrush/DataForSeo/SERanking），算 crawl budget 時必須扣掉，它們不是搜尋引擎；'
  'social-bot=分享預覽抓取（facebookexternalhit/meta-externalads/Dcard），突刺代表被轉發不是被索引。'
  'other-bot=UA 含 bot/crawler/spider/slurp 但不屬任何具名桶；human=UA 完全沒有 bot 跡象。'
  '所有桶互斥且窮盡，加總不會重複計算（刻意不設彙總哨兵值）。'
  '值域綁死（與 ua_name 相反）：出現沒定義的值代表 ingest 端與 schema 分岔，應當場失敗。';

COMMENT ON CONSTRAINT crawl_daily_dim_uniq ON crawl_daily IS
  '冪等鍵以 ua_name（原始事實）而非 ua_group（衍生標籤）為維度：'
  '分類法會改，而 Loki 只保留 168h，屆時沒有原始資料可以重算——粗桶不能分解成細桶。'
  '同 014 對 p75 不可跨桶重組的論證。';
