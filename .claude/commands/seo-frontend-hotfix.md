# /seo-frontend-hotfix — SEO 報告 → 前端 Hotfix → PR

**你（Claude Code）就是語意判斷引擎**——不呼叫任何外部 LLM API。WebFetch / WebSearch 是 built-in tools。

從本期 `/meeting-prep` 或 `/generate-report` 萃取「**前端工程可實作**」建議，**先驗證 2026 最佳實踐正確性**，再去 `~/Documents/vocus-web-ui` 修一版 hotfix 並發 PR。

---

## 用法

```
/seo-frontend-hotfix
/seo-frontend-hotfix <meeting-prep 路徑>
/seo-frontend-hotfix output/meeting_prep_20260501_9180c44c.md
/seo-frontend-hotfix --report output/report_20260501_7cd174e9.md
/seo-frontend-hotfix --dry-run         # 只驗證 + 規劃，不動 vocus-web-ui
```

預設輸入：最近一份 `output/meeting_prep_*.md`（若無則 fallback 到最近 `report_*.md`）。

---

## 設計原則

1. **資訊正確性優先**：SEO 建議若違反 2026 業界共識（如棄用的 schema、被 Google 限制的 rich results），**必須回頭修正 source 報告**，不直接實作
2. **工程可行範圍**：只挑前端工程能控制的（schema markup / meta tags / cache headers / CWV / sitemap / robots.txt），排除內容、社群、後端、組織決策
3. **小範圍 commit**：每項建議獨立 commit，PR 拆分清楚
4. **Worktree 隔離**：絕不直接動主 repo 工作分支

---

## 執行步驟

### Step 1：取得 actionable items

讀取輸入報告（預設最近 meeting-prep），萃取 Section 10「會議後行動核查表」的所有項目。

```bash
Glob: output/meeting_prep_*.md  # 取最新一份
# 或使用使用者指定路徑
```

對每項解析：
- **工具名**（`GSC` / `工程師排程系統` / `GA4` / `內部監控系統` / `內容企劃會議` / 等）
- **動作動詞**（部署 / 採樣 / 比對 / 啟動 / 規劃）
- **具體對象**（schema 類型、KW、path 等）
- **成熟度標籤**（L{X}→L{Y}）

### Step 2：篩選前端工程可實作

**保留**（前端工程可控）：
- 工具名包含「工程師排程系統」「前端」「frontend」
- 對象關鍵字包含 `schema`、`Schema`、`structured data`、`meta tag`、`OG`、`canonical`、`robots`、`sitemap`、`cache`、`CWV`、`LCP`、`INP`、`CLS`、`AMP`、`hreflang`

**排除**（非前端工程範圍）：
- GSC / GA4 / Ahrefs 操作（屬 SEO 操作）
- 內容企劃會議 / 社群媒體 / 內部策略會議（屬組織決策）
- 後端排查（5XX / 資料庫 / 快取設定）→ 標記交給後端團隊
- 採樣 / 比對 / 分析（屬資料分析，非實作）

輸出 `frontendCandidates`（典型 2-5 項）。

### Step 3：驗證資訊正確（CRITICAL）

對每個 `frontendCandidates` 項目，並行執行 2026 最佳實踐驗證：

```
WebSearch: "<schema type / 技術名稱> 2026 Google deprecated OR best practice"
WebSearch: "<schema type> rich results restriction 2026 publisher"
WebSearch: "Schema.org <Type> validator 2026 example"
```

**已知 2026 SEO 變動陷阱**（需特別檢查）：

| 項目 | 2026 實際狀態 | 誤導風險 |
|------|--------------|---------|
| FAQ schema rich results | Google 2023 限制至政府/醫療網站 | UGC 平台加 FAQ schema 不會出現在 SERP rich results |
| HowTo schema rich results | Google 2023 限制至桌機 | 行動端不顯示 |
| AMP | Google 2021 起降低 Top Stories 優先順序，部分功能 deprecated | 「AMP 修復」可能反映 deindex 而非結構復原 |
| Article schema vs NewsArticle | News 限定 Google News 認證發布商 | UGC 應用 Article 而非 NewsArticle |
| ProfilePage schema | 2024 Google 推出，仍在採用期 | ⚠️ 較新需確認最新指引 |
| Speakable schema | 2024 仍是 beta、僅限 GNI publishers | 一般網站加無效 |

對每項輸出「驗證結論」：

```
✅ 通過：建議與 2026 最佳實踐一致，可實作
⚠️ 需修正：建議部分正確，但需補充/微調（如 Profile Page 應同時 Person + ProfilePage）
❌ 駁回：建議違反 2026 最佳實踐（如 FAQ schema for UGC），不實作 + 回頭修正 source 報告
```

### Step 4：迭代錯誤資訊（避免誤導）

對每個 ❌ 駁回項：

1. **回頭修正 source meeting-prep**：在 S10 該項旁加註：
   ```markdown
   > ⚠️ **驗證後修正（YYYY-MM-DD）**：此建議與 2026 最佳實踐不符。
   > 證據：<WebSearch 來源 URL>
   > 改為：<新建議 / 改由其他維度處理>
   ```

2. **記錄至 `research/12-meeting-prep-insights.md`**：在「已知誤導」段（無則新建）append：
   ```markdown
   ### 已知誤導陷阱（驗證後修正）

   - **FAQ schema for UGC**（首次發現於 YYYY-MM-DD meeting-prep S10）
     - 錯誤建議：「部署 FAQ schema 提升 AIO 引用率」
     - 修正：Google 2023 限制 FAQ rich results 至政府/醫療網站，UGC 平台部署無 SERP 收益
     - 替代方案：聚焦明確答案段落 + 顧問署名（不需 schema 實作）
   ```

3. **記錄至 `data/seo-validation-log.jsonl`**（新檔）：
   ```bash
   echo '{"date":"YYYY-MM-DD","source":"<meeting-prep path>","item":"<建議內容>","verdict":"rejected","evidence_url":"<URL>","correction":"<新建議>"}' >> data/seo-validation-log.jsonl
   ```

### Step 5：建立 worktree

**禁止使用主 repo 直接修改**。從主分支建 worktree：

```bash
# 確認 vocus-web-ui 主分支名稱
git -C ~/Documents/vocus-web-ui branch --show-current
# 若主分支非 main，使用實際主分支

# 建立 worktree（從穩定主線分出）
SLUG=$(date +%Y%m%d)
git -C ~/Documents/vocus-web-ui worktree add \
  ~/Documents/vocus-web-ui-seo-hotfix-$SLUG \
  -b hotfix/seo-frontend-$SLUG \
  develop-v4   # 或 main，視專案實際主線
```

> **注意**：vocus-web-ui 主分支可能是 `develop-v4` 而非 `main`。先用 `git branch -a` 確認再起 branch。

切到 worktree：

```bash
cd ~/Documents/vocus-web-ui-seo-hotfix-$SLUG
```

### Step 6：探索前端架構（避免衝突）

```bash
# 找既有 schema markup
Grep: pattern="application/ld\\+json" --type ts --type tsx

# 找既有 meta 處理
Grep: pattern="next/head|generateMetadata" --type ts --type tsx

# 找 next.config / vercel.json
Glob: "next.config.*" "vercel.json" "Dockerfile"
```

確認：
- 既有 schema 結構（避免重複）
- 框架（Next.js App Router / Pages Router）
- 部署方式（影響 cache header 注入點）

### Step 7：實作 hotfix（每項獨立 commit）

對每個 ✅ 通過 + ⚠️ 需修正項實作。例：

```bash
# 範例：Profile Page schema 部署
# 1. 找 author page 元件
# 2. 加入 ProfilePage + Person JSON-LD
# 3. 寫測試（80% coverage）
# 4. commit
git add components/AuthorProfile/ProfilePageSchema.tsx
git commit -m "feat: add ProfilePage + Person schema for author pages

對應 meeting-prep 20260501 S10 P2-3：Top 50 作者頁面
schema 部署，目標 Authoritativeness L2→L3。

驗證：Schema.org ProfilePage 2024 推出，含 about:Person
nested type 為 2026 推薦結構。

Refs: output/meeting_prep_20260501_9180c44c.md"
```

每項 commit 必含：
- 對應 SEO 報告路徑
- 對應 S10 項目編號
- 2026 最佳實踐驗證來源
- 預期成熟度提升標籤

### Step 8：自動測試

```bash
pnpm install
pnpm lint
pnpm test            # 單元測試
pnpm test:e2e        # E2E（若 schema 影響渲染）
pnpm build           # 確認可 build
```

對 schema markup 變更，額外用 Schema.org Validator 驗證：

```bash
# 啟動 dev server
pnpm dev &
DEV_PID=$!

# 抓取一個範例 author page 的 HTML
curl -s http://localhost:3000/user/<sample-author> > /tmp/sample.html

# 提取 JSON-LD
grep -oP '(?<=<script type="application/ld\+json">)[^<]+' /tmp/sample.html

# 用 schema validator 驗證（手動或 API）
WebFetch: "https://validator.schema.org/?url=<encoded URL>"

kill $DEV_PID
```

### Step 9：發 PR

```bash
git push -u origin hotfix/seo-frontend-$SLUG

gh pr create --base develop-v4 --title "feat(seo): 前端 hotfix from meeting-prep $SLUG" --body "$(cat <<'EOF'
## Summary

從 meeting-prep YYYY-MM-DD 報告萃取的前端可實作項目，已通過 2026 最佳實踐驗證。

## Changes

- [✅ 通過項目 1] commit hash
- [✅ 通過項目 2] commit hash
- [⚠️ 微調項目 3] commit hash（原建議 X 修正為 Y）

## 駁回項目（不實作）

- [❌ 項目 N] 原因 + WebSearch 證據

## SEO 報告對應

- Source: `output/meeting_prep_<date>_<hash>.md`
- 影響成熟度維度：[L1 技術 / L4 結構化資料 / ...]

## Test plan

- [ ] `pnpm lint` 通過
- [ ] `pnpm test` 通過
- [ ] `pnpm build` 通過
- [ ] Schema.org Validator 驗證 author page JSON-LD
- [ ] Lighthouse SEO score 不下降
- [ ] CWV LCP/INP/CLS 無 regression（mobile + desktop）

## 驗證證據

每個 commit message 含 WebSearch 來源 URL，可追溯 2026 最佳實踐依據。

EOF
)"
```

### Step 10：回填 source 報告

PR 建立後，回 `~/Documents/seo-knowledge-insight`，在 source meeting-prep 的 S10 該項旁追加：

```markdown
> ✅ **已實作（YYYY-MM-DD）**：vocus-web-ui PR #<num>
```

並 append 一行至 `data/seo-implementation-log.jsonl`：

```bash
echo '{"date":"YYYY-MM-DD","source":"<meeting-prep path>","item_id":"<P2-3>","pr_url":"<PR URL>","commits":<n>}' >> data/seo-implementation-log.jsonl
```

---

## 安全規則

- ❌ **禁止**直接 push 到 `main` / `develop-v4` / `hotfix`（vocus-web-ui 主分支）
- ❌ **禁止**`--no-verify` 跳過 hooks
- ❌ **禁止**bypass schema validation
- ✅ 每個 schema 變更必須有對應測試
- ✅ PR 必須引用 source meeting-prep 路徑（追溯依據）
- ✅ 駁回項必須回頭修正 source 報告（迭代誤導）

---

## 輸出摘要

完成後告訴使用者：
- Source 報告路徑
- 候選 actionable items 數
- 通過 / 微調 / 駁回 計數
- 駁回項已回填修正
- Worktree 路徑 + 分支名稱
- Commit 數
- PR URL
- Lint / test / build 狀態
- 預期成熟度提升維度

---

## 不適用的情境（直接退回，不執行）

- meeting-prep S10 全部都是非前端類（GSC 操作、組織決策）→ 報告「無可實作項」
- vocus-web-ui 已有未推送的進行中 worktree 與本次衝突 → 列出衝突，請使用者裁決
- 主分支落後 origin >50 commits → 提醒先 pull，不擅自 rebase
