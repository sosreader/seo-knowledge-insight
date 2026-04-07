# 使用數據分析監控搜尋流量和其他更多資料
- **發佈日期**: 2022-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/03/monitoring-dashboard?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 3 月 30 日，星期三

本文將說明如何使用數據分析為搜尋流量建立監控資訊主頁。Search Console 提供立即可用的圖表和篩選功能，而數據分析可讓您自訂專屬圖表，並與其他資料並排查看，例如 Google Ads、Analytics、YouTube、BigQuery 等。如果您錯過了這個系列先前的文章，請參閱[將 Search Console 連結至數據分析](https://developers.google.com/search/blog/2022/03/connecting-data-studio?hl=zh-tw)一文。

在深入說明如何建立資訊主頁之前，我們想先與數據分析使用者分享一些好消息：從今天起，Search Console 連接器會納入探索和 Google 新聞流量資料，與[最近新增](https://developers.google.com/search/blog/2021/10/search-analytics-discover-gnews?hl=zh-tw)至 API 的資料類似。

在這篇文章中，我們會提供一個資訊主頁供您使用，您可以輸入自己的資料，並輕鬆地切換不同的 Search Console 資源、資料類型和裝置等。您可以將相關資料連結至[這個範本](https://datastudio.google.com/reporting/7300a2df-97a2-408a-b10c-43acd2270fe6/page/6zXD/preview?hl=zh-tw)，監控自家網站的 Google 搜尋流量。

請繼續閱讀下文，進一步瞭解資訊主頁。

## 使用資訊主頁的建議方式和原因

建立資訊主頁時，建議您一律先從定義用途開始，大部分都屬於下列三個選項之一：

* **監控成效**：迅速找出資料異動，例如監控網站上重要網頁的網址點擊次數和點閱率 (CTR)。
* **資料探索**：從資料中取得深入分析資訊，例如分析不同國家/地區、裝置或網站版面的搜尋成效模式。
* **公開發布資訊**：發布有趣的趨勢和模式，例如分享按產業區隔的匯總資料。

本文會說明監控成效資訊主頁，應該有助您即時找出問題。一般來說，這類資訊主頁會使用折線圖或長條圖等簡單的視覺化圖表和表格，方便快速解讀。如果發現問題，搜尋引擎最佳化 (SEO) 專家或分析人員可以進一步探索資料 (詳情請見下一篇文章)。

## 搜尋流量監控資訊主頁

如前文所述，這篇文章提供[範本](https://datastudio.google.com/reporting/7300a2df-97a2-408a-b10c-43acd2270fe6/page/6zXD/preview?hl=zh-tw)讓您監控 Google 搜尋的成效。本節將討論如何將搜尋資料整合至數據分析、資訊主頁提供的功能和資料，以及我們做出一些設計決策的原因。

### 設定 Search Console 連接器

登入[數據分析](https://datastudio.google.com/?hl=zh-tw)，建立 [Search Console 資料來源](https://support.google.com/datastudio/answer/7314895?hl=zh-tw)，然後選擇「網址曝光」表格，其中包含網址層級基礎上的網站、圖片、影片、新聞、探索和 googleNews 相關資料。您在這裡選擇的「資源參數」將成為報表的預設參數，但您可以透過篩選器存取其他參數，詳情請參閱下文。如要進一步瞭解這些資料，請參閱[成效報表說明網頁](https://support.google.com/webmasters/topic/9384513?hl=zh-tw)。

![建立 Search Console 資料連接器](https://developers.google.com/static/search/blog/images/search-console-data-studio.png?hl=zh-tw "建立 Search Console 資料連接器")

### 使用篩選器和日期控管資料

報表標頭提供多個選項，可用來篩選圖表中的資料：

1. 使用[資料控管](https://support.google.com/datastudio/answer/7415591?hl=zh-tw)功能切換您有權存取的 Search Console 資源。
2. 選擇要在報表中查看的日期範圍。根據預設，系統會顯示最近 28 天與再往前回推 28 天的比較資料。
3. 建立篩選器以細查資料：
   * **網頁**：這個篩選器可用來納入或排除您網站中的一或多個網頁。提示：您可以[使用規則運算式](https://developers.google.com/search/blog/2021/06/regex-negative-match?hl=zh-tw)，方法與在 Search Console 中使用運算式類似。
   * **類型**：這個篩選器可用來選擇不同的資料類型，包括探索和 Google 新聞。一次只能選擇一個類型。
   * **國家/地區**：這個篩選器可用來納入或排除一或多個國家/地區。
   * **裝置**：這個篩選器可用來選擇一或多個裝置類別。

![可在資訊主頁控管資料的選項](https://developers.google.com/static/search/blog/images/search-console-dashboard-filters.png?hl=zh-tw "可在資訊主頁控管資料的選項")

### 監控點擊次數和點閱率的長期變化

折線圖是最有效的視覺化工具，能夠清楚顯示指標的長期變化。在這個範例中，我們選擇同時查看「點擊次數」和「網站點閱率」。在折線圖中，您會看到週末和平日的模式截然不同 (這也是為什麼設定折線圖的日期範圍時，務必要使用 7 的倍數)，請特別留意那些規律模式出現變化的日期！

請注意，這張圖片顯示的是工作導向網站的流量，流量在平日較高，在週末則較低。
這個模式可能和您的網站截然不同。

![折線圖，顯示點擊次數和點閱率趨勢的長期變化](https://developers.google.com/static/search/blog/images/search-console-line-chart.png?hl=zh-tw "折線圖，顯示點擊次數和點閱率趨勢的長期變化")

這份報表並未納入 Google Analytics 資料，但您可以考慮加入一張圖表，藉此顯示網站有多少轉換來自 Google 搜尋的自然流量。瞭解如何[將 Google Analytics 連結到](https://support.google.com/datastudio/answer/6370352?hl=zh-tw)數據分析，這有助於取得詳細資訊。

### 細查特定網址或網站版面

分析趨勢和模式時，圖表較為實用，但如果想更深入瞭解相關資訊，建議您使用表格來分析特定網址或一組網址。例如：

* 使用「網頁」篩選器，讓報表只顯示網站的特定版面。
* 使用「國家/地區」篩選器，即可查看不同網頁在指定國家/地區的成效。
* 使用「類型」篩選器來分析每種資料類型的網址層級成效。

![顯示網址細查資料的表格](https://developers.google.com/static/search/blog/images/search-console-drill-down.png?hl=zh-tw "顯示網址細查資料的表格")

## 其他實用提示

### 提示 #1：讓資訊主頁適合透過行動裝置瀏覽

大多數資訊主頁都不需要調整為適合透過行動裝置瀏覽，因為使用者會透過電腦存取。不過，如果在上下班通勤時經常需要監控資訊主頁的話，適合透過行動裝置瀏覽就很重要。

為了在監控資訊主頁中提供良好的行動裝置體驗，請將「[報表和網頁版面配置](https://support.google.com/datastudio/answer/7355651?hl=zh-tw)」底下的「顯示模式」設為「符合寬度」，資訊主頁的寬度就會隨著螢幕大小自動調整。選擇這個選項後，請務必查看報表在不同螢幕大小上的效果。

### 提示 #2：縮短網址字串

如果報表包含單一網域 (不含子網域)，建議您將網域名稱從報表中移除，讓表格更加簡潔。舉例來說，如果您要為 `example.com/cool-dashboards/search` 建立報表，則只會看到 `/cool-dashboards/search`。如要這麼做，您可以使用以下規則運算式建立[計算結果欄位](https://support.google.com/datastudio/answer/6299685?hl=zh-tw)，將網域名稱從網址中移除。
以 `.com` 網域名稱為例，您可以使用以下運算式：

```
REGEXP_EXTRACT(Landing Page, ".*\\.com/(.*)$")
```

## 下一步：最佳化搜尋作業的進階圖表

在下一篇文章「[使用 Search Console 泡泡圖最佳化網站成效](https://developers.google.com/search/blog/2022/04/performance-optimization-bubble-chart?hl=zh-tw)」中，我們將說明進階圖表，這可能有助您瞭解在進行最佳化搜尋作業時該聚焦於何處。

如有任何問題，歡迎隨時透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)或[數據分析社群](https://support.google.com/datastudio/threads?thread_filter=%28category%3Aconnect_to_data%29&hl=zh-tw)提問。此外，如果您使用 Twitter，請務必[追蹤我們](https://twitter.com/googlesearchc)，我們會在上面公告最新文章的相關資訊。

*祝您使用資訊主頁愉快！*

發文者：搜尋服務代表 [Daniel Waisberg](https://www.danielwaisberg.com)
