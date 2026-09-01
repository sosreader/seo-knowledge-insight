-- 017_crawl_daily_ua_group_ai_buckets.sql
-- 放寬 crawl_daily.ua_group 的值域，讓 AI crawler 不再被壓進單一 other-bot
--
-- 【編號】新增前已 `ls supabase/migrations/` 確認：現況最大為 016，故本檔為 017。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【為什麼要改 —— 015 定值域時還沒有 log 實測資料】
-- ══════════════════════════════════════════════════════════════════════
--
-- 015 定的 8 個值（googlebot-desktop / -smartphone / -image / -other、
-- bingbot、other-bot、human、other）是在**沒有實際 log 分佈**的前提下訂的。
-- 2026-09-01 對 prod Loki `{job="loki.source.kubernetes.envoy_proxy"}`
-- 做的單一小時實測（證據：knowledge-base .verification/2026-08-29-seo-capability/
-- S4.1-crawl-dashboard/02-crawler-distribution-2026-09-01T08Z.md）顯示：
--
--   該小時 crawler 流量 8,233 次，其中
--     Googlebot 全家          1,344  (16%)
--     AI crawler 合計         4,413  (54%)   ← 沒有任何桶裝得下
--       其中 Amazonbot 1,458 / Applebot 1,277 / Claude-SearchBot 638 /
--            OAI-SearchBot 254 / Bytespider 163 / ChatGPT-User 65 /
--            PerplexityBot 37 / ClaudeBot 36 ...
--     SEO 工具 bot              889  (11%)
--     社群預覽 bot              858  (10%)
--
-- 照 015 的值域寫入，上面 75% 的流量會全部落進 `other-bot`——那會是全表最大的
-- 單一桶，而且正好是這張表唯一新增的情報（GSC 看不到 AI crawler，
-- Crawl Stats 報表也沒有公開 API）。壓平之後 crawl_daily 只能回答
-- 「Googlebot 有沒有在抓」，回答不了「AI crawler 吃掉多少 crawl budget」。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【分桶依據：這個 bot 影響什麼決策，不是它是哪一家的】
-- ══════════════════════════════════════════════════════════════════════
--
--   ai-search-bot   會回連、會帶 referral 流量的 AI 搜尋抓取。
--                   Claude-SearchBot / Claude-User / OAI-SearchBot /
--                   ChatGPT-User / PerplexityBot / YouBot / ExaSearchBot。
--                   這一桶成長 = 內容正在被 AI 搜尋引用，是資產。
--
--   ai-training-bot 純語料抓取，不回連。
--                   ClaudeBot / GPTBot / Bytespider / meta-webindexer /
--                   AIWebIndex / Amazonbot / Applebot。
--                   這一桶成長 = 只有頻寬成本沒有回流，是要不要進 robots.txt 的依據。
--
--   seo-tool-bot    第三方 SEO 稽核爬蟲（Ahrefs / Semrush / DataForSeo /
--                   SERanking）。**看 crawl budget 時必須能扣掉**——它們不是
--                   搜尋引擎，卻能佔到 11%，混進總量會讓「站被抓得很勤」變成假象。
--
--   social-bot      分享預覽抓取（facebookexternalhit / meta-externalads /
--                   Dcard-link-preview-bot）。突刺代表內容正在被轉發，
--                   語意跟「被索引」完全不同，不該跟 crawler 混在一起看。
--
-- 【Applebot 歸在 ai-training-bot 是一個有爭議的判斷】
-- Applebot 同時餵 Siri / Spotlight 搜尋與 Apple Intelligence，
-- 嚴格說它跨 search 與 training 兩類。這裡歸 training 的理由是：
-- 它對 vocus.cc 的可觀測回流是零（沒有 Apple 來源的 referral），
-- 成本面的行為比較接近 training。若日後量到 Apple 來源流量應重新歸類。
-- 同一件事也適用 Amazonbot。這個判斷寫進 COMMENT 讓下游看得到，不是藏在 migration 裡。
--
-- ══════════════════════════════════════════════════════════════════════
-- 【冪等性】
-- ══════════════════════════════════════════════════════════════════════
-- `ALTER TABLE ... DROP CONSTRAINT IF EXISTS` + `ADD CONSTRAINT` 是冪等的
-- （重跑先刪再加，結果相同）。這與 013 註解記錄的 `ALTER POLICY` 事故不同：
-- ALTER POLICY 沒有 IF EXISTS，天生非冪等；DROP CONSTRAINT 有。
--
-- 【這是純放寬，不是改語意】
-- 新值域是舊值域的**嚴格超集**，既有列全數仍然合法，不需要也不會動到任何資料。
-- 因此不需要 NOT VALID + VALIDATE 的兩段式；直接 ADD 即可，
-- 全表掃描的成本在放寬的情況下只是確認既有列合格。

ALTER TABLE crawl_daily DROP CONSTRAINT IF EXISTS crawl_daily_ua_group_ck;

ALTER TABLE crawl_daily ADD CONSTRAINT crawl_daily_ua_group_ck
  CHECK (ua_group IN (
    -- Google（沿用 015）
    'googlebot-desktop', 'googlebot-smartphone', 'googlebot-image', 'googlebot-other',
    -- 其他傳統搜尋引擎（沿用 015）
    'bingbot',
    -- 新增：依「影響什麼決策」分的四桶
    'ai-search-bot', 'ai-training-bot', 'seo-tool-bot', 'social-bot',
    -- 殘餘桶（沿用 015）。彼此互斥，加總不會重複計算。
    'other-bot', 'human', 'other'
  ));

COMMENT ON COLUMN crawl_daily.ua_group IS
  'crawler 分組。值域綁死，ingest 端遇到沒定義的 crawler 必須當場失敗、由人決定開新桶還是併進殘餘桶，'
  '而不是靜默塞進一個沒人定義的字串。'
  '分桶依據是「這個 bot 影響什麼決策」而非廠牌：'
  'ai-search-bot=會回連帶 referral 的 AI 搜尋（Claude-SearchBot/OAI-SearchBot/ChatGPT-User/PerplexityBot/YouBot/ExaSearchBot/Claude-User）；'
  'ai-training-bot=純語料抓取不回連（ClaudeBot/GPTBot/Bytespider/meta-webindexer/AIWebIndex/Amazonbot/Applebot）；'
  'seo-tool-bot=第三方 SEO 稽核（Ahrefs/Semrush/DataForSeo/SERanking），算 crawl budget 時必須扣掉，它們不是搜尋引擎；'
  'social-bot=分享預覽抓取（facebookexternalhit/meta-externalads/Dcard），突刺代表被轉發不是被索引。'
  '⚠ Applebot 與 Amazonbot 歸在 ai-training-bot 是有爭議的判斷：兩者也餵各自的搜尋產品，'
  '歸此桶的理由是對本站的可觀測回流為零；若日後量到該來源的 referral 應重新歸類。'
  'other-bot=UA 含 bot/crawler/spider/slurp 但不屬任何具名桶；human=UA 完全沒有 bot 跡象。'
  '所有桶互斥且窮盡，加總不會重複計算（刻意不設彙總哨兵值）。'
  '權威對照表在 scripts/ingest_crawl_hourly.py 的 TOKEN_TO_UA_GROUP，改動需與本 CHECK 同一個 PR。';
