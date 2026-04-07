# 簡化網頁體驗報表透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2021-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/08/simplifying-the-page-experience-report?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 8 月 4 日，星期三

今年稍早，Search Console [推出了](https://developers.google.com/search/blog/2021/04/more-details-page-experience?hl=zh-tw)[網頁體驗報表](https://support.google.com/webmasters/answer/10218333?hl=zh-tw)，讓發布者和網站擁有者能夠快速瞭解網站在網頁體驗信號方面的成效表現。而今天，我們隆重推出新的版本，從網頁體驗報表中移除「安全瀏覽」和「廣告體驗」小工具，以便提供簡化的報表，並修正資料遺失問題的處理方式。

提醒您，網頁體驗排名更新已於 2021 年 6 月 15 日[開始逐步推出](https://twitter.com/googlesearchc/status/1404886100087246848)，並將於 2021 年 8 月 31 日完成作業。

## 移除「安全瀏覽」和「廣告體驗」小工具

確保使用者在網際網路上安全無虞，是 Google [安全瀏覽](https://safebrowsing.google.com/?hl=zh-tw)系統的設計宗旨。有時候，網站會遭受第三方駭客攻擊，進而觸發安全瀏覽警告。我們瞭解，這類問題並非總是在網站擁有者的掌握之內，因此我們才會在這裡清楚說明為何不將安全瀏覽功能用做排名信號，以及為何不在網頁體驗報表顯示這項資訊。但請放心，所有安全瀏覽標記都會繼續在 Search Console 中顯示，只是不會列於網頁體驗報表中而已。

同樣地，我們也會移除[廣告體驗](https://www.google.com/webmasters/tools/ad-experience-unverified?hl=zh-tw)小工具，以免相同的資訊出現在 Search Console 的兩個地方。我們仍會以獨立工具的方式提供廣告體驗報告，方便您查看網站的狀態，並找出哪些廣告體驗違反了廣告體驗提升標準。明確來說，我們從未將廣告體驗報告當做是評估網頁體驗的其中一項依據，因此這項異動不會影響您網站的網頁體驗狀態。

![以上新版圖表顯示構成網頁體驗信號的各種因素，包括載入 (LCP)、互動性 (FID)、視覺穩定性 (CLS)、行動裝置相容性、HTTPS 和沒有會造成干擾的插頁式廣告](https://developers.google.com/static/search/blog/images/volt-post-graphic-designed.png?hl=zh-tw)

以上新版圖表顯示構成網頁體驗信號的各種因素，包括載入 (LCP)、互動性 (FID)、視覺穩定性 (CLS)、行動裝置相容性、HTTPS 和沒有會造成干擾的插頁式廣告。

## 針對報表採取的其他改善措施

除了上述兩項更新之外，我們也採取了其他改善措施，改進報表處理資料遺失問題的方式：

* 在[網站體驗核心指標報告](https://developers.google.com/static/search/blog/images/cwv-past-data.png?hl=zh-tw)和[網頁體驗報表](https://developers.google.com/static/search/blog/images/volt-past-data.png?hl=zh-tw)中新增「沒有最近的資料」橫幅。
* 修正錯誤：當網站體驗核心指標資料遺失時，報告顯示「HTTPS 失敗」。
* 改寫網頁體驗報表和網站體驗核心指標報告中的空白狀態文字。

我們希望這些改善措施能讓您更輕鬆地使用網頁體驗報表，並協助您打造提供優質網頁體驗的網站。

如有任何問題或意見，歡迎造訪[說明論壇](https://support.google.com/webmasters/community/?hl=zh-tw)，或透過 [Twitter](https://twitter.com/googlesearchc) 告訴我們。

發布者：Google 搜尋產品經理 Jeffrey Jose
