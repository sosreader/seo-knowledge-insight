# L4 External Sources — 擴充領先期內容

> Status: **Phase 1-3 fetch 完成**（2026-03-14）
> Branch: `worktree-l4-external-sources`

## 目標

L4（領先期）內容從 36 筆佔 2.4% → 突破 100 筆佔 6%+。引入天生偏 L4 的外部來源。

## 來源

| # | 來源 | 整合方式 | 文章數 | 狀態 |
|---|------|---------|--------|------|
| 1 | Ahrefs Blog | WP REST API + L4 分類篩選 | 271 | fetch 完成 |
| 2 | Search Engine Journal | RSS feed + L4 分類/slug 篩選 | 3 | fetch 完成 |
| 3 | Growth Memo (Kevin Indig) | Substack RSS | 14 | fetch 完成 |

## 完成項目

- [x] 3 個 fetch scripts（01e/01f/01g）
- [x] config.py DIR_COLLECTION_MAP 更新
- [x] Makefile targets 更新
- [x] .gitignore 更新
- [x] 112 unit tests（全部通過）
- [x] E2E 驗證（--limit 3 + 全量 fetch）
- [x] SSRF 防護 + empty slug guard + naive datetime 修正
- [x] CLAUDE.md 更新

## 待辦

- [ ] `/extract-qa` — 288 篇文章 Q&A 萃取
- [ ] `/dedupe-classify` — 去重 + 分類 + maturity 自動判斷
- [ ] L4 分布驗證（目標 >= 100 筆，佔比 >= 6%）
- [ ] Retrieval eval 回歸驗證
- [ ] Golden dataset 擴充（+5 L4 cases）
- [ ] Supabase sync
- [ ] Lambda 部署

## 技術決策

| 決策 | 選擇 | 原因 |
|------|------|------|
| Ahrefs 整合方式 | WP REST API（非 sitemap） | Blog 無獨立 sitemap；WP API 支援分類篩選 + 分頁 + 內容直接取得 |
| Ahrefs 分類篩選 | technical-seo + ai-search + enterprise-seo + data-studies | 4 個分類共 271 篇，L4 密度最高 |
| Growth Memo feed URL | growth-memo.com/feed（非 kevin-indig.com） | Kevin Indig 已遷移至自訂域名 |
| SEJ 策略 | RSS + category filter | RSS 只有 20 篇最新，L4 篩選後 3 篇；未來可考慮 WP API 擴充 |
| Raw data gitignore | 與 medium/ithelp 一致 | 避免 repo 膨脹；raw_data 是 pipeline 中間產物 |
