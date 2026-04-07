# 將 Search Console 連結至數據分析
- **發佈日期**: 2022-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/03/connecting-data-studio?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 3 月 8 日，星期二

[Google Search Console](https://goo.gle/searchconsole) 能讓您深入分析網站在 Google 搜尋中的成效，但理解這些資料可能並不容易。如果您在自訂資訊主頁中設定顯示對**您**有用的資料圖表，這可能可以協助您運用資料提升決策品質。本文是一系列文章的第一篇，這系列文章的重點在於如何使用 [Google 數據分析](https://support.google.com/datastudio/answer/6283323?hl=zh-tw)匯出、強化及視覺化 Search Console 資料。

今天這篇文章會說明如何將 Search Console 資料導入到 Google 數據分析。我們會提供範例，說明如何將 Search Console 資料下載至 Google 試算表、搭配地理區域強化資料，以及將試算表連結至數據分析。

我們會在日後貼文中說明如何建立資料圖表，協助您監控及分析資料。

## 準備資料並連結至數據分析

如要將 Search Console 資料匯入到數據分析，可以採用以下兩種做法：

* 如果您希望在這裡顯示與 Search Console 中相同的資料，建議使用 Google 數據分析資料連接器。做法很簡單：請前往[連接器資料庫](https://datastudio.google.com/data?hl=zh-tw)，選擇 Search Console，然後找到要連結的資源。您可在[數據分析說明中心](https://support.google.com/datastudio/answer/7314895?hl=zh-tw)找到連接器指南。
* 如要強化 Search Console 提供的資料 (例如將國家/地區分成多個區域)，請先從網頁介面或透過 API 匯出資料。接著您可以透過 Google 試算表或 BigQuery 處理資料，並將其連結至數據分析。

在本文中，我們會介紹第二個選項，使用這種方式必須執行較多的步驟，可自訂的空間也較大。您必須完成以下三個主要步驟：

1. 匯出 Search Console 資料。
2. 在資料上新增自己的資料。
3. 將資料匯入至數據分析中。

### 匯出 Search Console 資料

如要匯出資料，請前往 Search Console 的[成效報表](https://search.google.com/search-console/performance/search-analytics?hl=zh-tw)，選擇日期範圍，按一下「匯出」，然後選擇「Google 試算表」。這樣做會建立新的試算表，我們將在下一個步驟進行改善。您也可以使用 [Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=zh-tw) 執行更多自動化解決方案，但不在這篇文章的討論範圍內。

![Search Console 成效報表匯出選項](https://developers.google.com/static/search/blog/images/search-console-data-export.png?hl=zh-tw "Search Console 成效報表匯出選項")

如要進一步瞭解您可使用的維度和指標，請參閱[成效報表說明文件](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#dimensions)。

### 強化 Search Console 資料

為了讓您瞭解強化 Search Console 資料的方式，我們會使用簡潔的 Google 試算表函式 [IMPORTDATA](https://support.google.com/docs/answer/3093335?hl=zh-tw)，這個函式可從網址匯入資料。在範例中，我們要匯入[按區域排列的 ISO 3166 國家/地區](https://gist.githubusercontent.com/richjenks/15b75f1960bc3321e295/raw/62749882ed0e9dffa3edd7a9a44a7be59df8402c/countries.md)表格。

針對您從 Search Console 匯出的資料新增工作表，並在第一個儲存格中輸入以下程式碼：

```
=IMPORTDATA("https://gist.githubusercontent.com/richjenks/15b75f1960bc3321e295/raw/62749882ed0e9dffa3edd7a9a44a7be59df8402c/countries.md", "|")
```

在 Search Console 工作表中，為「**Region**」(區域) 建立資料欄，然後使用 `VLOOKUP` 函式比對區域與國家/地區。

最終表格的樣貌請參考[範例工作表](https://docs.google.com/spreadsheets/d/1WoyovWWCLq9uaYfnsICL4uMQMApaoNhjMf8U4nl0ZHQ/?hl=zh-tw)。

嵌入：表格會顯示運用國家/地區資訊強化的 Search Console 資料

雖然我們在範例中強化的是地理資料，但您可以透過相同的程序來新增任何類型的資訊。舉例來說，如果您有查詢分類，就可以用來將查詢依類別分組。

### 將 Google 試算表連結至數據分析

最後，將 Google 試算表連結至數據分析。方法是前往[連接器資料庫](https://datastudio.google.com/data?hl=zh-tw)，選擇 Google 試算表，然後找出新建立的試算表；但請務必選擇正確的工作表。

資料進入數據分析後，系統就會開始進行視覺化作業...

## 繼續

在本系列的下一篇文章「[使用數據分析監控搜尋流量和其他更多資料](https://developers.google.com/search/blog/2022/03/monitoring-dashboard?hl=zh-tw)」中，我們會討論不同類型的資訊主頁，並提供逐步操作範例供您參考。

如有任何問題，歡迎隨時透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)或[數據分析社群](https://support.google.com/datastudio/threads?thread_filter=%28category%3Aconnect_to_data%29&hl=zh-tw)提問。此外，如果您使用 Twitter，請務必[追蹤我們](https://twitter.com/googlesearchc)；我們將在上面公告未來文章訊息，敬請期待！

發文者：搜尋服務代表 [Daniel Waisberg](https://www.danielwaisberg.com)
