# 成效報表功能改良：資料篩選和比較模式
- **發佈日期**: 2021-04-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/04/performance-report-data-filtering?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 4 月 7 日星期三

使用者可以透過 Search Console 的[成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)，瞭解其他人在 Google 上找到網站的方式。如今，為了提供更加實用的報表，我們推出了兩項改良功能：規則運算式 (regex) 篩選器和更新版的比較模式。

## 篩選器現可支援規則運算式

您可以在成效報表中使用篩選器來細分資料。目前為止，使用者可以根據以下三種模式篩選查詢和網頁網址：包含字串、不含字串、以及完全相符的字串。Search Console 之前並不支援較為複雜的情況，例如查詢中包含選用字串。

但現在，我們推出了[規則運算式](https://en.wikipedia.org/wiki/Regular_expression)這種篩選資料的新方法，可讓您建立更複雜的查詢並於網頁層級進行篩選作業，以及解答更多與查詢和篩選器相關的疑問。舉例來說，假設貴公司的名稱是 'cats and dogs'，但有時會縮寫為 'cats & dogs' 或 'c&d'，這種情況就可以利用規則運算式篩選器，只要輸入「`cats and dogs|cats & dogs|c&d`」做為定義值，即能囊括所有與品牌相關的查詢。

如要使用新的規則運算式篩選器，請在點選查詢或網頁後，於「篩選器」下拉式選單選取 [自訂]。如要瞭解詳情，請前往[規則運算式篩選器](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#regex_filter)說明中心頁面。

![Search Console 成效報表的規則運算式篩選器](https://developers.google.com/static/search/blog/images/performance-regex-filter.png?hl=zh-tw "Search Console 成效報表的規則運算式篩選器")

有時報表並不會顯示查詢和網頁，這是[為了保護使用者隱私](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#aboutdata)或儲存空間限制所致。為了確保使用者清楚瞭解這點，我們新增了提醒功能，每當查詢或網頁套用相關篩選器時，系統就會顯示提醒。

## 更新版的比較模式

您可能已在使用[比較模式](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#comparingdata)來解答比較型的疑問。先前，如果您選取多個指標，表格並不會納入有相對百分比差異的比較欄。

但即日起，比較模式不僅可以完整支援選取多個指標的情況，還新增了加強版介面，方便您並排查看結果，幾乎可說是讓資料表的可用空間增加一倍。此外，在點選查詢或網頁後，如果要利用新的規則運算式篩選器，現在也提供比較模式。

![Search Console 成效報表的比較模式](https://developers.google.com/static/search/blog/images/performance-comparison-mode.png?hl=zh-tw "Search Console 成效報表的比較模式")

我們希望這些改善措施能協助您充分運用成效報表，並提供寶貴的深入分析，讓您瞭解網站在 Google 上的成效資料。
如果您有任何問題或疑慮，歡迎前往 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc)尋求協助。

發文者：Search Console 產品經理 [Ziv Hodak](https://developers.google.com/search/blog/authors/ziv-hodak?hl=zh-tw)
