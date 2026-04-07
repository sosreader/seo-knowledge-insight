# Search Console API 相關更新內容
- **發佈日期**: 2020-12-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/12/search-console-api-updates?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 12 月 9 日，星期三

我們在幾個月前宣布要[升級 API 基礎架構](https://developers.google.com/search/blog/2020/08/search-console-api-announcements?hl=zh-tw)，以此提升 [Search Console API](https://developers.google.com/webmaster-tools?hl=zh-tw) 效能來因應日益增長的使用需求。今天，很高興能向您介紹其他幾項即將推出的改善措施：

* 在 Search Console API 中加入最新資料功能和新聞篩選器
* Sitemap API 支援網域資源
* 提供如何[遷移探索文件](https://developers.google.com/search/blog/2020/08/search-console-api-announcements?hl=zh-tw#discovery-document-changes)的說明

如果您會自行呼叫 API，請參閱下文。

## Search Console API 中的最新資料功能與新聞篩選器

先前，我們已在[成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)中提供一天內的最新資料，現在您只要在傳遞要求參數 `dataState` 時將值設為 `all`，就可以透過 API 存取這些資料。在透過這個值獲得的資料中，會包含尚未最終確定的最新資料，如果您只想要取得最終資料，可以傳遞設為 `final` 的參數值，或完全不傳遞此參數，這樣根據預設就只會取得最終資料。

幾個月前，我們在成效報表中新增了 [Google 搜尋「新聞」分頁的篩選器](https://twitter.com/googlesearchc/status/1285559587576467456)，現在 API 也能顯示這項資訊，您只要將要求中的 `searchType` 參數值設為 `news` 即可存取。

## Sitemap API 支援網域資源

如同其他 Search Console API，Sitemaps API 現在也支援網域資源。您可以查詢、新增和刪除[網域資源](https://support.google.com/webmasters/answer/34592?hl=zh-tw#domain_property)中的 Sitemap，例如：

`GET https://www.googleapis.com/webmasters/v3/sites/sc-domain:example.com/sitemaps`

## 探索文件遷移作業

我們將停止支援 Webmasters 探索文件。如果您使用[外部 API 程式庫](https://developers.google.com/api-client-library?hl=zh-tw)來查詢 Search Console API，或是直接查詢 [Webmasters API 探索文件](https://www.googleapis.com/discovery/v1/apis/webmasters/v3/rest)，就必須更新 API 呼叫以納入下列變更。

### API 程式庫異動

如要瞭解 API 程式庫異動的最新資訊，請參閱 [Java](https://developers.google.com/webmaster-tools/search-console-api-original/v3/quickstart/quickstart-java?hl=zh-tw) 和 [Python](https://developers.google.com/webmaster-tools/search-console-api-original/v3/quickstart/quickstart-python?hl=zh-tw) 快速入門導覽課程指南，以取得更新版 API 使用指南。

#### Java

請在執行任何 Webmasters 服務相關的匯入作業時，將 `webmasters` 套件變更為 `searchconsole.v1` 套件，並將服務名稱 `Webmasters` 變更為 `SearchConsole`。例如：

* 匯入 API 服務：

  `import com.google.api.services.webmasters.Webmasters;`

  `import com.google.api.services.searchconsole.v1.SearchConsole;`
* 匯入回應物件：

  `import com.google.api.services.webmasters.model.WmxSite;`

  `import com.google.api.services.searchconsole.v1.model.WmxSite;`

請注意，除了服務物件之外，其他 API 物件都與過去完全相同，變更的只有**套件**。

#### Python

請在建立 Webmasters 服務物件時，進行下列變更：

`webmasters_service = build('webmasters', 'v3', http=http)`

`webmasters_service = build('searchconsole', 'v1', http=http)`

同樣地，物件的行為也沒有任何改變。

### 直接查詢探索文件

探索文件查詢作業的變更包括：

* 網址變更

  `https://www.googleapis.com/discovery/v1/apis/webmasters/v3/rest`

  `https://searchconsole.googleapis.com/$discovery/rest`
* 內容變更
  + `name` 欄位已從 `webmasters` 變更為 `searchconsole`。
  + `version` 欄位已從 `v3` 變更為 `v1`。

如有任何問題，歡迎透過[搜尋中心社群](https://support.google.com/webmasters/community?hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 提問。

發布者：Search Console 團隊的 Nati Yosephian、Gilad Amar 和 Michael Huzman
