# Search Console 推出含品牌名稱的查詢篩選器
- **發佈日期**: 2025-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2025/11/search-console-branded-filter?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2025 年 11 月 20 日，星期四

**2026 年 3 月 11 日更新**：所有符合資格的網站現在都能使用含品牌名稱的查詢篩選器。
詳情請參閱[適用範圍一節](https://developers.google.com/search/blog/2025/11/search-console-branded-filter?hl=zh-tw#rollout-and-availability)。

繼上個月推出[查詢群組](https://developers.google.com/search/blog/2025/10/search-console-query-groups?hl=zh-tw)後，很高興在此宣布，我們將在 [Search Console 成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)中新增「含品牌名稱的查詢篩選器」這項工具，讓您依查詢類型分析網站成效。這項新功能可自動區分含品牌名稱和不含品牌名稱的查詢，協助您分析帶動網站流量的查詢。

## 什麼是含品牌名稱的查詢？

含品牌名稱的查詢是指包含品牌名稱 (例如 Google)、品牌名稱的變體或錯別字 (例如 Gogle)，以及品牌相關產品或服務 (例如 Gmail) 的查詢。

區分熟悉您品牌和不熟悉您品牌的使用者流量，有時並不容易。分別著重於含品牌名稱的查詢和不含品牌名稱的查詢，有助於進一步瞭解流量模式。含品牌名稱的查詢通常會帶出網站中排名較高的網頁，並帶來較高的點閱率，而不含品牌名稱的查詢則可帶來自然成長，因為這類查詢會顯示新使用者在沒有前往網站的初始意圖下，如何找到您的內容。

## 含品牌名稱的查詢篩選器運作方式

您可以在[搜尋結果成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)中使用這個新篩選器，將查詢資料劃分為兩種不同的檢視畫面：

1. **含品牌名稱：**顯示包含品牌名稱或密切相關產品的查詢成效資料 (例如 google.com 的 Gmail)。
2. **不含品牌名稱：**顯示所有其他查詢的成效資料。

在搜尋結果成效報表中，您可以對所有搜尋類型 (網頁、圖片、影片和新聞) 套用這個篩選器。套用後，您就能查看各種指標 (例如曝光次數、點擊次數、平均排名和點閱率)，這些指標僅限於所選群組。

![Search Console 含品牌名稱的查詢篩選器](https://developers.google.com/static/search/blog/images/search-console-branded-queries-filter.png?hl=zh-tw)

此外，我們在[深入分析報表](https://support.google.com/webmasters/answer/16308503?hl=zh-tw)中新增了資訊卡，顯示含品牌名稱流量與不含品牌名稱流量的總點擊次數明細，協助您評估品牌認知，並比較已認識您品牌的使用者流量，以及無明確意圖造訪您網站的使用者流量。

![Search Console 深入分析的含品牌名稱流量資訊卡](https://developers.google.com/static/search/blog/images/insights-branded-traffic-card.png?hl=zh-tw)

## 系統如何識別含品牌名稱的查詢？

含品牌名稱與不含品牌名稱的分類方式，「並非」根據納入或排除關鍵字的規則運算式方法 (這類方法已在「依查詢篩選」部分提供)。這項分類作業是由內部 AI 輔助系統執行。包括所有語言的網站品牌名稱、錯別字，以及未提及品牌名稱但指涉該網站獨特產品或服務的查詢。

由於品牌分類具有動態和取決於情境的性質，系統有時可能會誤判某些查詢。這個篩選器可以讓您更輕鬆地在 Search Console 中區隔及分析資料，但不會影響 Google 搜尋排名的運作方式。

## 推出時間和適用範圍

含品牌名稱的查詢篩選器將在**未來幾週內逐步推出**。
如果報表中未顯示這個選項，可能是下列原因所致：

* 這項功能僅適用於頂層資源 (不適用於網址路徑資源，例如 `https://example.com/path`，或子網域資源，例如 `developers.google.com`)。
* 只有查詢量和曝光次數足夠的網站，才能使用這項功能。

建議您深入瞭解成效報表，探索這項新區隔，更清楚地掌握網站成效。由於這是 Search Console 中新推出的分析功能，我們非常歡迎您提供意見回饋。你可以透過資訊卡上的「喜歡」和「不喜歡」按鈕提供意見回饋，並視需要使用「提交意見回饋」連結。也歡迎在 [LinkedIn](https://www.linkedin.com/showcase/googlesearchcentral/) 分享意見，或在 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)發文。

發文者：Search Console 軟體工程師 Michael Huzman
