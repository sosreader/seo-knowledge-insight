# 網頁體驗更新的更多時程、工具與詳細資料透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2021-04-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/04/more-details-page-experience?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 4 月 19 日，星期一

**2021 年 8 月 4 日更新內容**：
[清楚說明不會將安全瀏覽功能用做排名信號](https://developers.google.com/search/blog/2021/08/simplifying-the-page-experience-report?hl=zh-tw)。安全瀏覽系統仍是維持 Google 搜尋使用者安全無虞的重要關鍵，所有相關標記會繼續顯示在 Search Console 中，只是不會列於網頁體驗報表中而已。
**2021 年 6 月 15 日最新消息**：網頁體驗更新會逐步向世界各地的所有使用者推出，
並將於 2021 年 8 月底前完成作業。

去年 11 月，我們曾[宣布](https://developers.google.com/search/blog/2020/11/timing-for-page-experience?hl=zh-tw)將於今年在 Google 搜尋中推出網頁體驗排名變更內容，稱為「網頁體驗更新」。為協助發布者和網站擁有者改善網頁體驗並做好萬全準備，我們在此宣布幾項重要更新：

1. [將於今年 6 月中旬逐步推出](#gradual-rollout)
2. [更新涵蓋內容的詳細資料](#details)
3. [Search Console 新推出的「網頁體驗」報表](#new-report)
4. [Google 搜尋中的所有內容皆支援 Signed Exchange](#sxg)

## 將於今年 6 月中旬逐步推出

自 2021 年 6 月中旬，我們將開始使用網頁體驗功能，做為排名系統的一部分。
然而直到 8 月底前，網頁體驗不會在這些系統中扮演完整的角色。就好比您在準備菜餚時為食物加料一般，我們不會一次加入混合所有調味料，而是在這段時間範圍內慢慢加味。

如前所述，雖然這項更新旨在強調能提供絕佳的使用者體驗的網頁，但網頁體驗依然是我們系統考量的要素之一。因此，我們通常不建議您在網站上進行大幅變動。此外，由於我們會逐步推出這項功能，因此將能監控任何非預期或非預期的問題。

我們希望本次調整後的發布時程能助您繼續改善自身網站，以提升網頁體驗為目標。在這項變更進行前，我們也收集了各方意見，確保能提供有效指導與[回答問題](https://support.google.com/webmasters/thread/104436075?hl=zh-tw)，以便在網站擁有者遇到與改善使用者網頁體驗相關的問題時，可提供有效幫助。

## 更新涵蓋內容的詳細資料

與先前[宣布](https://developers.google.com/search/blog/2020/05/evaluating-page-experience?hl=zh-tw#page-experience-and-the-mobile-top-stories-feature)的內容相同，網頁體驗更新將涵蓋各種[網頁體驗信號](https://developers.google.com/search/docs/appearance/page-experience?hl=zh-tw#signals)，包括三項[網站使用體驗核心指標](https://web.dev/vitals?hl=zh-tw)：[LCP](https://web.dev/lcp?hl=zh-tw)、[FID](https://web.dev/fid?hl=zh-tw) 和 [CLS](https://web.dev/cls?hl=zh-tw) (以及 [Chrome 近期對 CLS 的修正](https://web.dev/evolving-cls/?hl=zh-tw))。此外，Google 搜尋的焦點新聞輪轉介面功能也會更新，只要是符合 [Google 新聞政策](https://support.google.com/news/publisher-center/answer/6204050?hl=zh-tw)的內容，就會顯示在焦點新聞輪轉介面中。也就是說，任何網頁不論網站使用體驗核心指標報告的分數或網頁體驗狀態如何，無需使用 AMP 格式，都將能顯示在焦點新聞輪轉介面中。

我們也為 Google 新聞應用程式推出了類似更新內容，Google 新聞應用程式是一個重要的平台，可讓世界各地的使用者查看當天的重要新聞。在網頁體驗更新中，我們將擴展非 AMP 內容的使用範圍，以便提升 [news.google.com](https://news.google.com/?hl=zh-tw) 和 Google 新聞應用程式的核心體驗。

此外，我們將不再顯示用來指出 AMP 內容的 AMP 徽章圖示。我們將於 6 月中旬推出網頁體驗更新，屆時您會在我們的產品中看到這項異動。
我們會繼續測試其他有助找出良好網頁體驗內容的方法，並且在有更多資訊可分享時通知您。

如需更多資訊，請參閱我們最近在搜尋中心論壇上發布的[網站使用體驗核心指標報告與網頁體驗常見問題](https://support.google.com/webmasters/thread/104436075?hl=zh-tw)。如果您是 AMP 發布者，請參閱 AMP 團隊撰寫的 [AMP 網頁體驗指南](https://blog.amp.dev/2020/10/13/meet-amps-page-experience-guide/)，其中針對如何讓 AMP 網頁展現出最佳效果，提供了量身打造的建議。

## Search Console 新推出的「網頁體驗」報表

為了提供可做為行動依據的深入分析資料，我們推出了[網頁體驗報表](https://support.google.com/webmasters/answer/10218333?hl=zh-tw)。這份報表結合了現有網站體驗核心指標報告與其他網頁體驗信號的元件，例如 HTTPS 安全性、行動裝置相容性，和排除插頁式廣告干擾。

網頁體驗報表提供了寶貴的指標，例如在特定期間擁有良好網頁體驗和搜尋曝光度的網址百分比，有助於快速評估網頁成效。您也可以深入剖析網頁體驗信號的元件，藉此進行深入分析，發掘出更多改善的機會。

![Search Console 中的網頁體驗報表](https://developers.google.com/static/search/blog/images/page-experience-report.png?hl=zh-tw)

除了推出「網頁體驗」報表外，我們也更新了[搜尋成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)，可讓您篩選出有良好網頁體驗的頁面，持續追蹤這類網頁與相同網站上其他網頁的比較情形。

## Google 搜尋中的所有內容皆支援 Signed Exchange

今天我們也宣布，將針對所有網頁正式推出 [Google 搜尋的 Signed Exchange (SXG)](https://developers.google.com/search/docs/appearance/signed-exchange?hl=zh-tw)。Google 搜尋先前只[支援](https://blog.amp.dev/2019/05/22/privacy-preserving-instant-loading-for-all-web-content/)採用 AMP 架構的 SXG。

SXG 可讓 Google 搜尋利用[相容瀏覽器](https://web.dev/signed-exchanges/?hl=zh-tw#browser-compatibility)中的隱私保護預先擷取技術，藉此提升網頁體驗。這項技術可讓 Google 搜尋在前往頁面前先載入網頁的主要資源 (HTML、JavaScript、CSS)，加快瀏覽器顯示網頁的速度。

**注意**：使用 SXG 並非享有網頁體驗優勢的必要條件，而是改善網頁體驗的技術之一。

Nikkei 是日本的大型出版公司，持續在 [Nikkei Style](https://style.nikkei.com) 上測試 SXG，並且發現最大內容繪製 (LCP) 減少了 300 毫秒。此外還發現在進行這項測試的 Android Chrome 中，使用者參與度提升了 12%，單次工作階段網頁瀏覽量也提升了 9%。為了在他們的網站上導入 SXG，Nikkei 選擇了 [`nginx-sxg-module`](https://github.com/google/nginx-sxg-module)，也就是 NGINX 伺服器的開放原始碼擴充功能。

如要進一步瞭解 SXG 工具，請參閱 [Signed Exchange (SXG)](https://web.dev/signed-exchanges/?hl=zh-tw#tooling)。如需設定 SXG 的操作說明，請參閱[如何使用 Web Packager 設定 Signed Exchange](https://web.dev/signed-exchanges-webpackager/?hl=zh-tw)。

## 攜手打造更優質的網路體驗

我們對網頁體驗的願景，是與您攜手打造出使用者喜愛的網路生態系統。我們正努力在 2021 年 6 月中旬發布排名之前，確保您能取得適合的工具和資源。

希望這次分享的更新內容可協助您更輕鬆地建立出優質網站。
如有任何疑問或意見，歡迎造訪我們的[說明論壇](https://support.google.com/webmasters/community/?hl=zh-tw)，查看近期發布的[常見問題](https://support.google.com/webmasters/thread/104436075?hl=zh-tw)，或透過 [Twitter](https://twitter.com/googlesearchc) 告訴我們。

發布者：Google 搜尋產品經理 [Jeffrey Jose](https://twitter.com/jeffjose)
