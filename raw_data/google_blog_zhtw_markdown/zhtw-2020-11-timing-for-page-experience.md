# Google 搜尋服務導入網頁體驗的時機點
- **發佈日期**: 2020-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/11/timing-for-page-experience?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 11 月 10 日，星期二

這篇網誌文章已發布一段時間。部分資訊可能已經過時，例如圖片可能會有缺漏，連結也可能失效。請參閱有關[網頁體驗](https://developers.google.com/search/docs/appearance/page-experience?hl=zh-tw)的最新說明文件。

我們曾在[今年 5 月](https://developers.google.com/search/blog/2020/05/evaluating-page-experience?hl=zh-tw)宣布，[網頁體驗](https://developers.google.com/search/docs/appearance/page-experience?hl=zh-tw)信號將成為 Google 搜尋排名的考量指標之一。這些信號不僅能評估使用者與網頁的互動體驗，也能協助我們持續邁向長期以來的目標，確保使用者獲得最實用且愉快的網站體驗。過去幾個月來，我們發現使用者與 Lighthouse 和 PageSpeed Insights 互動次數的中位數增加了 70%，並有許多網站擁有者會利用 Search Console 的 Core Web Vitals 報告來尋找改善的契機。

現在，我們宣布自 2021 年 5 月起，網頁體驗信號將成為決定排名的依據之一。除了 Core Web Vitals 外，新的網頁體驗信號還結合了現有的搜尋服務信號，包括[行動裝置相容性](https://developers.google.com/search/blog/2015/02/finding-more-mobile-friendly-search?hl=zh-tw)、[HTTPS 安全性](https://developers.google.com/search/blog/2016/11/heres-to-more-https-on-web?hl=zh-tw)和[插頁式廣告指南](https://developers.google.com/search/blog/2016/08/helping-users-easily-access-content-on?hl=zh-tw)。

![Google 搜尋網頁體驗信號的構成要素說明圖](https://developers.google.com/static/search/blog/images/page-experience-signal.png?hl=zh-tw)

我們還會在 2021 年 5 月推出另一項 Google 搜尋變更，讓非 AMP 內容也能顯示在行動版「焦點新聞」功能中。屆時，任何符合 [Google 新聞內容政策](https://support.google.com/news/publisher-center/answer/6204050?hl=zh-tw)的網頁都能使用這項功能，且我們在決定搜尋結果排名時，將會優先考量擁有優質網頁體驗的網頁，無論該網頁使用的是 AMP 或任何其他網頁技術。

除了上述更新的推出時間外，我們還計劃測試一項視覺性指標，在搜尋結果中突顯出提供優質網頁體驗的網頁。

## Google 搜尋推出突顯優質網頁體驗的全新方式

我們認為，提供網頁體驗品質的相關資訊有助於使用者選擇要造訪哪些搜尋結果。搜尋結果中的網頁摘要或圖片預覽可提供網頁主題的背景資訊，讓使用者瞭解網頁能夠提供哪些內容。在搜尋結果中顯示視覺指標也能達成同樣目的，而我們正在開發的視覺指標將能突顯出符合所有網頁體驗條件的網頁。這項指標會在不久後進入測試階段，如果測試成功，便會在 2021 年 5 月上線。我們會在接下來的幾個月中分享更多相關資訊。

## 發布者改善網頁體驗時所需的工具

為了因應這些變更，我們推出多種工具，讓發布者能開始著手改善網頁體驗。這項過程的第一個步驟，就是全面審查整個網站的網頁，瞭解是否有改善的空間。Search Console 提供了 Core Web Vitals [報告](https://support.google.com/webmasters/answer/9205520?hl=zh-tw)，能讓您一覽網站成效並深入探討問題。找出改善程序的切入點後，便可利用 [PageSpeed Insights](https://web.dev/articles/vitals-tools?hl=zh-tw#pagespeed-insights) 和 [Lighthouse](https://web.dev/articles/vitals-tools?hl=zh-tw#lighthouse)，反覆調整並修正發現的問題。請前往 [web.dev/vitals-tools](https://web.dev/articles/vitals-tools?hl=zh-tw)，詳細瞭解開始改善所需的所有工具。

此外，對於想打造優質網頁體驗的發布者來說，AMP 將是[最簡單且符合成本效益的方式之一](https://blog.amp.dev/2020/11/10/create-great-page-experiences-with-amp/)。根據 AMP 團隊的[分析](https://blog.amp.dev/2020/10/13/meet-amps-page-experience-guide/)，大多數 AMP 網頁都能提供優質的網頁體驗。如果您是 AMP 發布者，請參閱近期推出的 [AMP 網頁體驗指南](https://amp.dev/page-experience)，這項診斷工具能為開發人員提供實際可行的建議。

Google 搜尋會繼續支援 AMP 內容。如果您發布了 AMP 版本的內容，Google 搜尋仍會連結到針對快取進行最佳化調整的 AMP 版本，協助您以最好的方式將內容提供給使用者，就像現在一樣。

## 結論

Google 搜尋的使命是協助使用者找到所有最相關的優質網站。
因此，推出上述更新是為了突顯優質網頁體驗，並確保使用者能找到所需資訊。我們不會停下腳步，計劃在未來納入更多網頁體驗信號，並每年更新信號的組合。希望我們提供的[工具和資源](https://developers.google.com/search/docs/appearance/page-experience?hl=zh-tw)能讓您輕鬆建立優質網站，從而打造出受使用者喜愛的網路生態系統。

如有任何問題或意見，歡迎造訪[說明論壇](https://support.google.com/webmasters/community/?hl=zh-tw)，或透過 [Twitter](https://twitter.com/googlesearchc) 告訴我們。

[發布者：Google 搜尋產品經理](https://twitter.com/jeffjose) Jeffrey Jose

---

## 更新

* **2021 年 6 月 15 日更新內容**：網頁體驗更新會逐步向世界各地的所有使用者推出，
  並將於 2021 年 8 月底前完成作業。
* **2021 年 8 月 4 日更新內容**：
  [清楚說明不會將安全瀏覽功能用做排名信號](https://developers.google.com/search/blog/2021/08/simplifying-the-page-experience-report?hl=zh-tw)。安全瀏覽系統仍是維持 Google 搜尋使用者安全無虞的重要關鍵，所有相關標記會繼續顯示在 Search Console 中，只是不會列於網頁體驗報表中而已。
* **2024 年 1 月 31 日更新**：
  [Interaction to Next Paint (INP)](https://web.dev/blog/inp-cwv-march-12?hl=zh-tw) 將於 2024 年 3 月 12 日取代 FID 成為 Core Web Vitals 的一部分。
* **2024 年 3 月 12 日更新**：[Interaction to Next Paint (INP)](https://web.dev/blog/inp-cwv-launch?hl=zh-tw) 已取代 FID 成為 Core Web Vitals 的一部分。
