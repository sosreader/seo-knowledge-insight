# 評估網頁體驗以打造更美好的網路環境
- **發佈日期**: 2020-05-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/05/evaluating-page-experience?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 5 月 28 日，星期四

這篇網誌文章已發布一段時間。部分資訊可能已經過時，例如圖片可能會有缺漏，連結也可能失效。請參閱有關[網頁體驗](https://developers.google.com/search/docs/appearance/page-experience?hl=zh-tw)的最新說明文件。

[我們的內部研究](https://ai.googleblog.com/2009/06/speed-matters.html)和[業界研究](https://blog.chromium.org/2020/05/introducing-web-vitals-essential-metrics.html)都顯示，使用者偏好可以提供絕佳網頁體驗的網站。近年來，Google 搜尋加入了多項新的搜尋結果排名依據，透過[網頁的載入速度](https://developers.google.com/search/blog/2018/01/using-page-speed-in-mobile-search?hl=zh-tw)和[行動裝置相容性](https://developers.google.com/search/mobile-sites?hl=zh-tw)等標準來評估使用者體驗。本月初，Chrome 團隊公布了[網站使用體驗核心指標報告](https://blog.chromium.org/2020/05/introducing-web-vitals-essential-metrics.html)，這是一套與速度、回應效能和視覺穩定性相關的指標，可協助網站擁有者衡量使用者的網頁體驗。

今天，我們將以這項檢測系統為基礎，提前公布 Google 搜尋排名機制未來的藍圖，說明導入這些網頁體驗指標後，排名機制會產生哪些變動。我們將導入一種新的信號，能夠結合 Core Web Vitals 報告與 Google 現有的網頁體驗信號，完整呈現使用者網頁體驗品質的全貌。

在此次更新中，我們也會將網頁體驗指標整合到行動版 Google 搜尋「焦點新聞」功能所使用的排名標準中，並移除登上「焦點新聞」所需的 AMP 必要條件。Google 將持續支援 AMP，也會在有可用的 AMP 頁面時繼續連結到這些頁面。我們也更新了開發人員工具，協助網站擁有者將自家網頁體驗調整至最佳狀態。

**關於時程的注意事項**：我們瞭解此時此刻許多網站擁有者正專注於應對 COVID-19 帶來的影響，而這也確實是當務之急。因此，本文中所述的排名機制變動將延至明年上線，我們也會在推行這些變動前，至少提前六個月發出通知。我們之所以現在就提供相關工具，是為了幫助您輕鬆上手，也因為網站擁有者一直要求我們盡早提供有關排名異動資訊，**但您不必立即採取行動**。

## 網頁體驗簡介

[網頁體驗](https://developers.google.com/search/docs/appearance/page-experience?hl=zh-tw)信號可從不同角度衡量使用者如何看待自己與網頁互動的體驗。只要針對這些因素進行最佳化，就能讓使用各種網路瀏覽器和裝置的使用者對網路環境更加滿意，並協助網站朝行動裝置使用者期望的方向改進。我們相信，這樣能提高使用者的參與度、讓交易過程更流暢，進而促進網路業績蒸蒸日上。

[網站使用體驗核心指標](https://web.dev/articles/vitals?hl=zh-tw#core-web-vitals)是一組以使用者為中心的實際使用情形況指標，可量化呈現使用者體驗的關鍵面向。這些指標會衡量網站可用性的各個面向，例如載入時間、互動性、載入時的內容穩定性 (例如避免畫面元素位移而讓人不小心按到不想要的按鈕，這會造成使用者反感)。

[![

](https://developers.google.com/search/blog/images/Accidental_Submit_Still.webp?hl=zh-tw)](https://developers.google.com/static/search/blog/images/AccidentalSubmit.webm?hl=zh-tw)

我們將結合來自 Core Web Vitals 報告的信號與現有的 Google 搜尋網頁體驗信號 (包括[行動裝置相容性](https://developers.google.com/search/blog/2015/02/finding-more-mobile-friendly-search?hl=zh-tw)、[HTTPS 安全性](https://developers.google.com/search/blog/2016/11/heres-to-more-https-on-web?hl=zh-tw)和[插頁式廣告指南](https://developers.google.com/search/blog/2016/08/helping-users-easily-access-content-on?hl=zh-tw))，完整呈現網頁體驗的全貌。我們將繼續致力於辨識及衡量網頁體驗的不同面向，因此計劃每年納入更多網頁體驗信號，希望能更滿足使用者不斷變化的需求，並擴大我們能夠衡量的使用者體驗面向。

![Google 搜尋網頁體驗信號的構成要素說明圖。](https://developers.google.com/static/search/blog/images/page-experience-signal.png?hl=zh-tw)

## 網頁體驗排名機制

優質的網頁體驗能讓使用者執行更多作業並加深互動程度；反之，如果網頁體驗不佳，可能會妨礙使用者在網頁上尋找有用的資訊。我們希望協助使用者更輕鬆地取得想要的資訊和網頁，並支援網站擁有者打造讓使用者滿意的體驗，這就是為什麼 Google 要在已納入搜尋結果排名考量的數百種信號之外，再加入網頁體驗信號的原因。

對部分開發人員來說，瞭解自家網站的 Core Web Vitals 報告分數並解決報告中指出的問題，是件勞心勞力的工作。為了減輕開發人員的負擔，我們[更新](https://web.dev/articles/vitals-tools?hl=zh-tw)了 Lighthouse 和 PageSpeed Insights 等熱門的開發人員工具，在其中顯示 Core Web Vitals 報告資訊及相關建議內容，同時，Google Search Console 也提供專屬的[報表](https://support.google.com/webmasters/answer/9205520?hl=zh-tw)，方便網站擁有者快速找出改善的契機。我們也正與外部工具開發人員合作，將 Core Web Vitals 報告整合到他們的產品中。

雖然網頁體驗的所有元素都十分重要，但我們仍會優先考量整體資訊最佳的網頁，即使網頁體驗的某些面向差強人意也無妨。良好的網頁體驗並不能取代精彩、關聯性高的內容。不過，如果有多個網頁都有類似的內容，想在 Google 搜尋結果中脫穎而出，網頁體驗就變得更加重要。

## 網頁體驗與行動版「焦點新聞」功能

行動版「焦點新聞」功能是 Google 搜尋最重要的全新內容體驗，這項功能目前著重於突顯 AMP 結果，這些結果都為了呈現良好網頁體驗而經過最佳化調整。過去幾年來，我們從「焦點新聞」功能中[激發出新的思維](https://blog.amp.dev/2018/03/08/standardizing-lessons-learned-from-amp/)，重新思考如何在網路上打造更優質的網頁體驗。

在推出網頁體驗排名更新的同時，我們也會一併更新使用「焦點新聞」功能的資格條件。AMP 將不再是報導登上行動裝置「焦點新聞」專區的必要條件，任何網頁都有機會呈現在該專區中。除了這項變動之外，網頁體驗也將和其他眾多經過評估的因素一樣，成為「焦點新聞」中決定排名的因素。跟之前相同的是，網頁仍必須遵循 [Google 新聞內容政策](https://support.google.com/news/publisher-center/answer/6204050?hl=zh-tw)才能顯示在「焦點新聞」中。如果網站擁有者目前已採用 AMP 格式發布網頁，或者另外為網頁準備 AMP 版本，都將不會感受到行為上有任何不同之處，「焦點新聞」仍會連結到 AMP 版本網頁。

## 總結

我們相信，只要改善網路體驗，使用者參與度就會隨之提高；將這些新信號整合到 Google 搜尋後，我們就能協助提升網路環境，為每個人打造更美好的網路生活。透過提前分享 Google 的網頁體驗更新藍圖，並推出支援工具，我們由衷希望能協助這個由網站創作者、開發人員和商家構成的多元生態系統，一同改善並提供更令人滿意的使用者體驗。

敬請持續關注我們未來發布的更新，進一步掌握變動生效時間等確切資訊。和往常一樣，如有任何問題或意見，歡迎造訪我們的[網站管理員論壇](https://support.google.com/webmasters/community/?hl=zh-tw)。

發文者：搜尋生態系統系統工程總監 [Sowmya Subramanian](https://twitter.com/sosubram)

---

## 更新

* **2021 年 6 月 15 日更新內容**：網頁體驗更新會逐步向世界各地的所有使用者推出，
  並將於 2021 年 8 月底前完成作業。
* **2021 年 8 月 4 日更新內容**：
  [清楚說明不會將安全瀏覽功能用做排名信號](https://developers.google.com/search/blog/2021/08/simplifying-the-page-experience-report?hl=zh-tw)。安全瀏覽系統仍是維持 Google 搜尋使用者安全無虞的重要關鍵，所有相關標記會繼續顯示在 Search Console 中，只是不會列於網頁體驗報表中而已。
* **2024 年 1 月 31 日更新內容**：
  [Interaction to Next Paint (INP)](https://web.dev/blog/inp-cwv-march-12?hl=zh-tw) 將於 2024 年 3 月 12 日取代 FID 成為 Core Web Vitals 的一部分。
* **2024 年 3 月 12 日更新內容**：[Interaction to Next Paint (INP)](https://web.dev/blog/inp-cwv-launch?hl=zh-tw) 已取代 FID 成為 Core Web Vitals 的一部分。
