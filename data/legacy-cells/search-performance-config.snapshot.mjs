// search-performance-config.snapshot.mjs — 唯讀快照，勿手動編輯
//
// 來源：sosreader/seo-automation repo 的 config.mjs（private repo，本 repo 的
// GitHub Actions GITHUB_TOKEN 沒有跨 repo checkout 權限，也沒有另外的 PAT secret，
// 見 export_legacy_gsc_cells.py 的 --config 選項與其 CI workflow）。
// 只複製 export_legacy_gsc_cells.py 解析用得到的 SEARCH_PERFORMANCE 與 CELL 兩個
// const，其餘 config.mjs 內容（CONFIG／AI_EXPOSURE／GA4 等）與本腳本無關，不複製。
//
// 來源檔最後修改：commit 1214bef3775447343feff3d2456a5128b478bedc（2026-08-14）
// 本檔複製日期：2026-09-08
// 若 seo-automation/config.mjs 的 SEARCH_PERFORMANCE／CELL 改了（新增/刪除 pattern、
// 改 cell 起始格號），要手動重新複製這份快照，否則 CI 跑出來的 20 格會跟舊爬蟲當下
// 的實際行為脫節而不自知——export_legacy_gsc_cells.py 只驗證「能不能解析」，
// 驗不出「內容是不是最新」。

export const SEARCH_PERFORMANCE = {
  days: 7,
  /** G20~G34（15 筆）：網頁 7 筆 + 關鍵字 8 筆，順序即 cell 順序 */
  queryPage: [
    { label: "首頁", type: "page", pattern: "^https://vocus\\.cc/$" },
    { label: "/article/", type: "page", pattern: "/article/" },
    { label: "/post", type: "page", pattern: "/post" },
    { label: "/user", type: "page", pattern: "/user" },
    { label: "/salon/", type: "page", pattern: "/salon/" },
    { label: "/tags/", type: "page", pattern: "/tags/" },
    { label: "/search", type: "page", pattern: "/search" },
    { label: "影評", type: "query", pattern: "影評" },
    { label: "電影", type: "query", pattern: "電影" },
    { label: "評價", type: "query", pattern: "評價" },
    { label: "攻略", type: "query", pattern: "攻略" },
    { label: "股", type: "query", pattern: "股" },
    { label: "劇", type: "query", pattern: "劇" },
    { label: "保養", type: "query", pattern: "保養" },
    { label: "必買", type: "query", pattern: "必買" },
  ],
  /** G38~G42（5 筆）：搜尋結果的三種搜尋類型 + 探索 + Google News */
  multiType: [
    { label: "圖片", path: "performance/search-analytics", searchType: "image" },
    { label: "影片", path: "performance/search-analytics", searchType: "video" },
    { label: "新聞", path: "performance/search-analytics", searchType: "news" },
    { label: "探索", path: "performance/discover" },
    { label: "Google News", path: "performance/google-news" },
  ],
};

/** 試算表 G 欄 cell 對應（只保留本腳本用得到的兩個鍵） */
export const CELL = {
  queryPage: 20,              // G20~G34 (15 筆) — 官方 GSC（見 SEARCH_PERFORMANCE）
  multiType: 38,              // G38~G42 (5 筆)  — 官方 GSC（見 SEARCH_PERFORMANCE）
};
