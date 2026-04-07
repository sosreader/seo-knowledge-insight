# 改善 Search Console 影片索引報表中的顯著性報告功能
- **發佈日期**: 2023-06-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/06/video-indexing-specific-issues?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 6 月 12 日，星期一

Google 沒有將網頁中的影片編入索引的主要原因之一，是 Google 無法識別出足夠顯眼的影片，能被判定為這個網頁的影片。

為協助您進一步瞭解這個問題，並為您提供更多可做為行動依據的因素，我們將「Google 無法判斷網頁上是否有顯眼的影片」錯誤分為三個明確的原因。以下摘要說明該做什麼來解決這些問題，並且讓影片能編入索引：

* **影片在可視區域外**：重新調整影片在網頁上的位置，讓整部影片位於網頁中可轉譯的區域，並在網頁載入時顯示。
* **影片過小**：請將影片高度增加到 140 像素以上，或將寬度增加到 140 像素以上，且至少占網頁寬度的三分之一。
* **影片過高**：請將影片高度降低到小於 1080 像素。

![包含新原因的 Search Console 影片索引報表](https://developers.google.com/static/search/blog/images/video-indexing-specific-issues.png?hl=zh-tw)

由於 Search Console 影片索引報表會顯示 3 個月的歷來資料，因此「影片索引報表」中的原因清單仍可能顯示「Google 無法判斷網頁上顯眼的影片」，但這對網頁沒有影響。

在[檢查特定影片網頁網址](https://support.google.com/webmasters/answer/9012289?hl=zh-tw)時，系統也會顯示新原因 (如適用)。

希望這些改變可以讓您更容易瞭解影片索引，並修正影片網頁上的任何問題。如果您有任何問題或疑慮，請透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 與我們聯絡。

發文者：軟體工程師 Shachar Nudler 和產品經理 [Moshe Samet](https://developers.google.com/search/blog/authors/moshe-samet?hl=zh-tw)
