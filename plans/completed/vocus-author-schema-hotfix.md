# Plan: vocus-web-ui Author Schema Hotfix

**Status**: planning
**Created**: 2026-05-02
**Source**: `output/meeting_prep_20260501_9180c44c.md` S10 P2-3 + P3-3
**Validation**: `data/seo-validation-log.jsonl`（已完成 2026-05-02）

## 目標

把本期 5/1 meeting-prep 中**前端工程可實作**的 SEO 建議落地到 `~/Documents/vocus-web-ui`，提升：

- L4 結構化資料：L2 → L3
- L5 分發（GEO 維度）：L2 → L3

並建立可重複的 `/seo-frontend-hotfix` 工作流的首次實戰驗證。

## 涵蓋範圍

兩項驗證後微調的建議：

1. **P2-3** — Profile Page schema + Organization schema（主軸）
2. **P3-3 FAQ schema 部分** — 重新定位為 GEO 工具（次要，可選）

## Worktree 設定

```bash
# 從 vocus-web-ui hotfix 分支起 worktree（使用者指定）
git -C ~/Documents/vocus-web-ui worktree add \
  ~/Documents/vocus-web-ui-seo-author-schema \
  -b hotfix/seo-author-schema-20260502 \
  hotfix
```

- **Base branch**: `hotfix`（vocus-web-ui 目前 hotfix 分支）
- **Worktree path**: `~/Documents/vocus-web-ui-seo-author-schema/`
- **新分支名**: `hotfix/seo-author-schema-20260502`

## 範圍選項（待決定）

### Option A：全部 author pages（推薦）

- ProfilePage schema 部署到所有 `/user/<id>` 路由
- Schema 是 static template，不分頁面數量
- 符合 2026 業界共識（all author pages + SameAs，AI Mode source selection 最高槓桿實作）
- **風險**：若 vocus 既有 schema 與本次衝突，可能要先盤點 + 處理 deprecated schema

### Option B：Top 50 作者頁面（meeting-prep 原建議）

- 只對 Top 50 高流量作者部署
- 需要先取 Top 50 清單（Ahrefs / GSC top organic landing pages）
- 工作量分散，但維護成本不下降（schema 是模板）
- **不推薦**：模板式 schema 應一次覆蓋所有，分批沒有實質好處

### Option C：先 1-2 個 sample author pages（最保守）

- 只在 1-2 個指定作者頁部署作為驗證
- 用 Schema.org Validator + Google Rich Results Test 驗證
- 通過後再 follow-up PR 擴大到全站
- **適用**：vocus-web-ui hotfix 分支不穩或既有 schema 結構不明時的 staging 策略

**建議**：先 C 後 A（兩個 PR：first PR sample，second PR 全站擴大）

## PR Scope 選項（待決定）

### Scope 1：只做 P2-3 schema（schema 統一一個 PR）

```
PR 1: ProfilePage + Organization + Person schema
├── components/schema/ProfilePageJsonLd.tsx (新)
├── components/schema/OrganizationJsonLd.tsx (新)
├── components/schema/PersonJsonLd.tsx (新)
├── app/user/[id]/page.tsx (注入 ProfilePage + Person)
├── app/layout.tsx 或 about page (注入 Organization)
├── __tests__/schema/*.test.tsx
└── 文件更新（CLAUDE.md schema section）
```

**估時**：4-6 hours
**測試重點**：
- Schema.org Validator 通過
- Rich Results Test 通過（即使 vocus 不會獲得 ProfilePage rich results，validator 通過代表結構正確）
- `pnpm lint` / `pnpm test` / `pnpm build` 通過
- E2E: author page 渲染含 JSON-LD script tag

### Scope 2：P2-3 + P3-3 FAQ schema 一起做

P3-3 FAQ schema 額外加入：
- 需要先盤點哪些 vocus 文章已有 Q&A 結構化內容
- 若沒有，FAQ schema 部署只是 template 但 validator 會 fail（FAQ 必須有 question/answer pair）
- **估時**：8-12 hours（多 4-6 hours 用於盤點 + 條件式渲染）

**不建議本次包含 P3-3**，理由：
1. FAQ schema 需要文章內容配合（內容團隊範疇）
2. 本次定位為「結構化資料快速落地」，混入內容相關工作會稀釋焦點
3. P3-3 應先在內容團隊 SOP 確認 Q&A 格式後再做（屬於後續 follow-up PR）

**建議**：本次只做 Scope 1（P2-3）；P3-3 等內容團隊回應後另開 PR。

## 實作步驟

### Phase 0：研究階段（worktree 內，不寫 code）

```bash
cd ~/Documents/vocus-web-ui-seo-author-schema

# 0.1 既有 schema 盤點
grep -rn "application/ld+json" app/ components/ --include="*.tsx" --include="*.ts"
grep -rn '"@type"' app/ components/ --include="*.tsx" --include="*.ts"

# 0.2 框架確認（Next.js App Router vs Pages Router）
ls app/ pages/ 2>/dev/null
cat next.config.* | head -40

# 0.3 找 author page 路由
find app/user pages/user -type d 2>/dev/null
find app -name "page.tsx" -path "*user*" 2>/dev/null

# 0.4 找 Person/User data 來源（Firebase / Firestore / API）
grep -rn "getUser\|fetchAuthor\|userById" app/ apis/ --include="*.tsx" --include="*.ts" | head -20
```

**輸出**：
- 既有 schema 清單（避免重複）
- 框架版本 + 路由結構
- 作者資料 schema（決定 ProfilePage 對映）

### Phase 1：Schema 元件實作

```
components/seo/schema/
├── ProfilePageJsonLd.tsx   # ProfilePage type + nested Person via mainEntity
├── OrganizationJsonLd.tsx  # vocus.cc Organization (homepage / about page)
├── PersonJsonLd.tsx        # 可重用 Person 元件（含 sameAs / jobTitle / knowsAbout）
└── index.ts                # exports
```

實作要點（基於 2026 驗證後最佳實踐）：

```tsx
// ProfilePageJsonLd.tsx — 範例結構
{
  "@context": "https://schema.org",
  "@type": "ProfilePage",
  "dateCreated": <author.created_at>,
  "dateModified": <author.updated_at>,
  "mainEntity": {
    "@type": "Person",
    "name": <author.name>,
    "alternateName": <author.username>,
    "identifier": <author.id>,
    "description": <author.bio>,
    "image": <author.avatar_url>,
    "url": "https://vocus.cc/user/<id>",
    "sameAs": [
      // 只連結明確同一人的社群帳號
      // 必填驗證：不可有拼寫差異
    ],
    "interactionStatistic": [
      {
        "@type": "InteractionCounter",
        "interactionType": "https://schema.org/FollowAction",
        "userInteractionCount": <author.follower_count>
      },
      {
        "@type": "InteractionCounter",
        "interactionType": "https://schema.org/WriteAction",
        "userInteractionCount": <author.post_count>
      }
    ]
  }
}
```

```tsx
// OrganizationJsonLd.tsx — homepage / about page only
{
  "@context": "https://schema.org",
  "@type": "Organization",  // 或 NewsMediaOrganization 視 vocus 定位
  "name": "vocus 方格子",
  "url": "https://vocus.cc",
  "logo": "https://vocus.cc/logo.png",
  "sameAs": [
    "https://www.facebook.com/vocus.tw",
    "https://twitter.com/vocus_tw"
    // 等
  ],
  "contactPoint": { ... }
}
```

### Phase 2：注入到頁面

- App Router：在 `app/user/[id]/page.tsx` 用 `<script type="application/ld+json">` 注入
- 或用 `generateMetadata` + Next.js 13+ Metadata API（若已用）
- Organization 加在 `app/layout.tsx`（root）或 `app/about/page.tsx`（about page）

### Phase 3：測試

```bash
# 單元測試（Vitest / Jest）
__tests__/schema/ProfilePageJsonLd.test.tsx
__tests__/schema/OrganizationJsonLd.test.tsx
__tests__/schema/PersonJsonLd.test.tsx
```

測試覆蓋：
- Render 含正確 JSON-LD script tag
- Required fields 必填驗證
- sameAs 陣列格式正確
- ProfilePage nested Person 結構正確

### Phase 4：手動驗證

```bash
pnpm dev &  # 啟動 dev server
# 用 playwright-cli 抓樣本 author page HTML（vocus.cc 在 WebFetch blocklist）
playwright-cli open http://localhost:3000/user/<sample-id>
playwright-cli snapshot --filename .playwright-cli/sample-author.yml

# 提取 JSON-LD
grep -A 30 'application/ld+json' .playwright-cli/sample-author.yml

# 用 Schema.org Validator
WebFetch: "https://validator.schema.org/?url=<encoded>"
WebFetch: "https://search.google.com/test/rich-results?url=<encoded>"
```

### Phase 5：每項獨立 commit

```
git commit -m "feat(seo): add ProfilePage + Person schema for author pages

對應 meeting-prep 20260501 S10 P2-3：作者頁面 schema 部署
驗證後修正：(a) 必須 nest Person via mainEntity (b) 範圍擴大至全部 author pages

驗證 sources:
- https://developers.google.com/search/docs/appearance/structured-data/profile-page
- https://almcorp.com/blog/schema-markup-detailed-guide-2026-serp-visibility/

預期成熟度提升：L4 結構化資料 L2→L3
"

git commit -m "feat(seo): add Organization schema for homepage and about page

對應 meeting-prep 20260501 S10 P2-3：vocus.cc 主域 Organization 標記
驗證後修正：Organization 應在 homepage/about，不在每個作者頁

驗證 source:
- https://developers.google.com/search/docs/appearance/structured-data/organization

預期 AI Mode source selection 提升（2026 最高槓桿實作）
"

git commit -m "test(seo): unit tests for schema components

涵蓋 ProfilePage, Organization, Person JsonLd
驗證 required fields, sameAs format, nested structure
"
```

### Phase 6：發 PR

```bash
git push -u origin hotfix/seo-author-schema-20260502
gh pr create --base hotfix --title "feat(seo): add ProfilePage + Organization schema for E-E-A-T uplift"
```

PR description template 詳見 `.claude/commands/seo-frontend-hotfix.md` Step 9。

### Phase 7：回填 source 報告

```bash
cd ~/Documents/seo-knowledge-insight

# meeting-prep S10 P2-3 加註已實作
# Edit output/meeting_prep_20260501_9180c44c.md：
# 在「⚠️ 驗證後微調」之後 append「✅ 已實作（2026-05-02）：vocus-web-ui PR #<num>」

# JSONL log
echo '{"date":"2026-05-02","source":"output/meeting_prep_20260501_9180c44c.md","item_id":"P2-3","pr_url":"<URL>","commits":3}' \
  >> data/seo-implementation-log.jsonl
```

## 風險與注意事項

| 風險 | 緩解 |
|------|------|
| vocus.cc 在 WebFetch blocklist（403） | 改用 `playwright-cli` 抓本地 dev server HTML 驗證 |
| `hotfix` 分支可能不穩，含進行中 hotfix work | Phase 0 先 `git status` + `git log -10` 確認無衝突 |
| 既有 schema markup 與本次衝突 | Phase 0 grep 既有 `application/ld+json`，若有則處理 deprecated schema |
| Top 50 vs 全部範圍未定 | 模板式 schema 建議全部，但 sample 路由（Option C）可先驗證 |
| Person `sameAs` 缺資料 | 第一版可省略 sameAs（optional field），後續 follow-up PR 補充 |
| FAQ schema for UGC 雙重立場 | 本次不做 P3-3，避免誤導內容團隊；等 SOP 確認 Q&A 格式後 follow-up |
| Organization subtype 選擇 | vocus 是 UGC 平台，建議用 `Organization`（generic）非 `NewsMediaOrganization`（會誤觸 Google News policy） |
| `hotfix` 是進行中 hotfix 分支，可能與 schema PR 範圍衝突 | 確認後若衝突，改 base 為 `develop-v4` 並通知 |

## 完成判準

- [ ] Schema 三個元件單元測試 ≥80% coverage
- [ ] `pnpm lint` 通過
- [ ] `pnpm test` 通過
- [ ] `pnpm build` 通過
- [ ] Schema.org Validator 通過（ProfilePage + Organization）
- [ ] Google Rich Results Test 通過（即使無 rich result 顯示，structure 必須有效）
- [ ] PR 建立並 link 至 source meeting-prep
- [ ] source meeting-prep S10 P2-3 加註已實作標記
- [ ] `data/seo-implementation-log.jsonl` 新增一筆

## 預期成果

- **量化**：L4 結構化資料 L2 → L3（meeting-prep S8 確認後計分）
- **AI Mode source selection**：vocus.cc 在 AI Mode citations / Knowledge Panel 能見度提升（GSC ProfilePage 報表追蹤，4-8 週後驗證）
- **E-E-A-T Authoritativeness**：作者 follower count + post count 作為客觀錨點（meeting-prep S6 評分依據）

## 後續 follow-up（不在本 PR 範圍）

1. **P3-3 FAQ schema**：等內容團隊確認 Q&A 格式 SOP 後另開 PR（GEO 用途，非 SERP 紅利）
2. **Person sameAs 補資料**：作者社群帳號回填（資料庫工作 + 第二輪 schema PR）
3. **Article schema 強化**：在文章頁加 `author` 連結至 ProfilePage（entity disambiguation）
4. **Speakable schema**：限 GNI publishers，vocus 不適用，不在 follow-up

## 等待使用者確認

開工前需要使用者裁決：

1. **範圍**：Option A（全部 author pages）/ Option B（Top 50）/ Option C（先 sample 1-2 個）
2. **PR Scope**：Scope 1（只 P2-3 schema）/ Scope 2（P2-3 + P3-3）。我建議 Scope 1
3. **Phase 0 完成後是否暫停確認**：發現既有 schema 衝突或 hotfix 分支不穩，是否回報後再進 Phase 1
