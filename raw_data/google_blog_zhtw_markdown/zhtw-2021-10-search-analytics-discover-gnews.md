# Search Analytics API 現已支援 Google 探索、Google 新聞和規則運算式透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2021-10-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/10/search-analytics-discover-gnews?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 10 月 25 日，星期一

目前，如果您的網站有來自 Google 搜尋、Google 探索和 Google 新聞等平台的流量，可以在 Google Search Console 的[成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)中看到相關資料。而自從推出[探索](https://support.google.com/webmasters/answer/9216516?hl=zh-tw)和 [Google 新聞](https://support.google.com/webmasters/answer/10083653?hl=zh-tw)的成效報表後，我們便不斷收到使用者的建議，要求將這些資料也納入 [Search Analytics API](https://developers.google.com/webmaster-tools/search-console-api-original/v3/searchanalytics?hl=zh-tw)。我們很高興在此宣布，從今天開始您就能在 Search Analytics API 中看到這些資料。

您原先可以在 `searchType` 參數中依據 `news`、`video`、`image` 以及 `web` 等條件篩選 API 呼叫，現在我們將這項參數重新命名為 `type`，並支援另外兩個新的參數：`discover` (適用於 Google 探索) 和
`googleNews` (適用於 Google 新聞)。請注意，雖然我們將參數重新命名為 `type`，不過系統仍支援舊的名稱 `searchType`。

![包含新參數的 Search Analytics API 呼叫範例](https://developers.google.com/static/search/blog/images/search-analytics-api-discover-gnews.png?hl=zh-tw "包含新參數的 Search Analytics API 呼叫範例")

在 Search Console 成效報表中，部分指標和維度僅適用於某幾種資料類型，舉例來說，Google 探索報表就不支援查詢和排名。同樣地，如果您使用不支援的維度提出要求，API 就會傳回錯誤訊息。

此外，我們也在查詢和網頁維度中[支援規則運算式](https://developers.google.com/search/blog/2021/06/regex-negative-match?hl=zh-tw)，除了現有的比對方式外再加入兩個新的運算子：`includingRegex` 和 `excludingRegex`。

詳情請參閱 [Search Analytics API 說明文件](https://developers.google.com/webmaster-tools/search-console-api-original/v3/searchanalytics/query?hl=zh-tw)。如有任何問題，歡迎透過[搜尋中心社群](https://support.google.com/webmasters/community?hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 提問。

發文者：Search Console 團隊的 [Ziv Hodak](https://developers.google.com/search/blog/authors/ziv-hodak?hl=zh-tw) 和 Roman Priborkin
