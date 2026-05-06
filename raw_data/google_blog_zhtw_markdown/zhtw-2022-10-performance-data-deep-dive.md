# 深入瞭解 Search Console 的成效資料篩選與限制透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2022-10-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/10/performance-data-deep-dive?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 10 月 19 日，星期三

Google 搜尋成效資料是 Search Console 中最廣為使用的資料，可同時透過[成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)和 [Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=zh-tw) 來使用。本文詳細說明 Google 提供的資料，以及 Google 如何處理資料，包括隱私權篩選功能，以及與服務延遲、儲存和處理資源相關的其他限制。
您知道這些系統的運作方式嗎？讓我們深入探索。

如果您是第一次使用 Search Console，請參閱[成效報表簡介](https://support.google.com/webmasters/answer/10268906?hl=zh-tw)。

## 搜尋成效基本須知

成效報表中有四種指標會顯示搜尋流量的變化趨勢。
本文提供[各項指標的計算方式](https://support.google.com/webmasters/answer/7042828?hl=zh-tw)，摘要說明如下：

* 點擊次數：從 Google 搜尋結果連到資源的使用者點擊次數。
* 曝光次數：使用者在 Google 搜尋結果中看到資源的次數。
* CTR (點閱率)：將點擊次數除以曝光次數後所得到的數字。
* 排名：網址、查詢或網站整體搜尋結果的平均排名。

每一項指標都可以針對不同維度加以分析。您可以查看每項查詢、網頁、國家/地區、裝置或搜尋外觀在為網站帶來流量方面所得獲得的成效。

您可以透過多種方式存取搜尋成效資料，包括[產品介面](https://search.google.com/search-console/performance/search-analytics?hl=zh-tw)、[Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=zh-tw)、[Looker Studio 連接器](https://developers.google.com/search/blog/2022/03/connecting-data-studio?hl=zh-tw)和試算表 (必須從介面手動下載)。

如果您使用產品介面，可以透過篩選器或圖表下方的維度表格取得維度，如下圖所示。

![Search Console 中的成效報表](https://developers.google.com/static/search/blog/images/search-console-performance-report.png?hl=zh-tw)

這些資料可用來提高網站能見度，從 Google 獲得更多流量。如需您可以執行的分析類型範例，請參閱這份[最佳化圖表範例](https://developers.google.com/search/blog/2022/04/performance-optimization-bubble-chart?hl=zh-tw)。

## 資料篩選與限制

報表介面及匯出的資料都會經過匯總，並以不同方式篩選。以下是資料的兩大限制：隱私篩選和每日資料列上限。

### 隱私權篩選

有些查詢 (稱為匿名查詢) 並不包含在 Search Console 資料中，目的是保護查詢使用者的隱私權。

匿名查詢是指在二至三個月內，未有超過數十位使用者發出的查詢。為了保護隱私權，實際查詢資料不會顯示在 Google 搜尋成效資料中。
因此，我們將這類查詢稱為「匿名查詢」。雖然系統一律會在資料表中忽略實際的匿名查詢，但這些查詢會納入圖表總數中，除非您依查詢進行篩選。

我們來查看以下範例以說明這一點。請注意，以下插圖僅將隱私權篩選列入考量，但是下一個區段討論的每日資料列上也可能是考量因素之一，請繼續閱讀下文以瞭解詳情。假設下表顯示了為網站查詢的所有流量，將非匿名查詢的流量分項列出。一般情況下，網站通常會有超過四個分項的非匿名查詢，但就本例而言，就只四個分項的非匿名查詢。

|  |  |
| --- | --- |
| **查詢** | **點擊次數** |
| 經典文學 | 150 |
| 詩詞 | 125 |
| 科幻小說 | 100 |
| 非小說 | 75 |
| *分項查詢總數* | *450* |
| *總計* | *550* |

如果您將所有分項查詢相加，如圖表所示，就會有 450 次點擊。網站的整體點擊次數也達到 550 次。這個數字較高，因為其中包含所有分項點擊以及匿名化查詢中未列出的點擊。

但實際上，使用 Search Console 報表時，您可能會注意到這類差異主要分為兩種。

1. 報表表格或 API 都沒有匿名化查詢的資料列 (這裡加入資料列是為了方便說)，因此如果將所有資料列的點擊次數加總，就會發現資料列的點擊次數與圖表中的總數並不一樣。例如，如果將資料列點擊次數加總，總數會是 450，但圖表中的總數卻是 550。
2. 每次套用篩選器時，系統就會忽略匿名化查詢，因此，如果您將圖表中的點擊總數與分別包含 `some_string` 與不包含 `some_string` 的點擊總數進行比較，就會發現有所差異。在這個範例中，如果您使用篩選器僅加入含有「小說」查詢的點擊次數，會顯示 175 次點擊；如果排除含有「小說」查詢的點擊次數，則會顯示 275 次點擊，總計為 450 次點擊，而在圖表中總計則有 550 次點擊。

### 每日列數上限

由於服務延遲、儲存、處理資源與其他方面的相關限制，Search Console 對可顯示或匯出的資料量設有限制。這些限制並不會影響 Search Console 中的大多數資源。少數非常大型的網站可能會受到這項限制的影響，但即使是這類的網站，我們認為其餘的資料也足以建立具代表性的資料樣本。

您可以透過 Search Console 使用者介面匯出的資料上限為 1,000 列資料。
目前，透過 [Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query?hl=zh-tw) (和透過 [Looker Studio 連接器](https://developers.google.com/search/blog/2022/03/connecting-data-studio?hl=zh-tw)) 匯出的資料上限，是每個網站每天可針對每種搜尋類型匯出 50,000 列的資料 (並非所有情況都能匯出這麼多的資料)。API 傳回的預設資料列為 1,000 列，但您可以使用 `rowLimit` 將資料列增加至 25,000 列，再使用 `startRow` 透過分頁功能提取 25,001 列到 50,000 列的資料。請參閱[這篇文章](https://developers.google.com/webmaster-tools/v1/how-tos/all-your-data?hl=zh-tw)，瞭解如何取得可用資料。

如果是與查詢或網址維度 (例如國家/地區、裝置和搜尋外觀) 不相關的要求，Search Console 就會顯示並匯出所有資料。

## 資源與意見回饋

如要進一步瞭解這個主題，請參閱[成效說明文件](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)。您可以透過這份說明文件，進一步瞭解可用資料、如何使用成效報表，以及圖表中可能會出現的差異相關詳情。

如果您有任何問題或疑慮，請透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 與我們聯絡。

發文者：搜尋服務代表 [Daniel Waisberg](https://www.danielwaisberg.com)
