# 在 Google 搜尋服務中呈現新聞報導的最佳做法透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2020-02-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/02/best-practices-for-news-coverage-with?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 2 月 28 日，星期五

大型公眾事件或活動的情勢往往瞬息萬變，而如何即時掌握最新資訊便是新聞發布者需要面對的一項重要課題。這份指南將重點介紹新聞發布者可以利用哪些工具，為使用者打造引人入勝的複合式搜尋體驗。

## 在 AMP 網頁中加入「文章」結構化資料

只要在新聞、網誌和體育報導的 AMP 網頁中加入「文章」結構化資料，即可大幅提升這些內容在 Google 搜尋結果中的顯示效果，比如讓內容出現在焦點新聞輪轉介面和代管輪轉介面中，或是以影像故事的形式呈現。如需瞭解為報導加上標記的方式，請參閱[這篇文章](https://developers.google.com/search/docs/appearance/structured-data/article?hl=zh-tw)。

[複合式搜尋結果測試](https://search.google.com/test/rich-results?e=SuitSdEmbeddedContent&hl=zh-tw)工具已支援測試及驗證 [AMP 文章標記](https://developers.google.com/search/docs/appearance/structured-data/article?hl=zh-tw#amp-sd)。只要輸入網頁的網址或是程式碼片段，複合式搜尋結果測試就會顯示在網頁上找到的 AMP 文章 (和其他複合式搜尋結果類型)，並列出在這類文章中發現的錯誤與相關建議。您也可以保存測試記錄並分享測試結果。

另外，我們也建議您[提供發布日期](https://developers.google.com/search/docs/appearance/publication-dates?hl=zh-tw)，因為這樣一來，Google 就可以在搜尋結果中對有需要的使用者顯示這項資訊。

## 標記即時串流影片內容

直播事件或活動的影片時，只要[將影片加上 BroadcastEvent 標記](https://developers.google.com/search/docs/appearance/structured-data/video?hl=zh-tw#livestream-guidelines)，影片上就會顯示「直播」標記。我們強烈建議您使用 Indexing API，確保系統可以及時檢索到您的即時串流影片內容並建立索引。Indexing API 可讓網站擁有者在新增或移除特定類型的網頁時直接通知 Google，方便 Google 為這些網頁安排新的檢索時間，進而在內容更新時帶來更多相關使用者的瀏覽流量。如果網站上有許多網頁包含時效較短的資訊 (例如即時串流影片)，Indexing API 便能協助您即時在搜尋結果中顯示最新內容。如需 Indexing API 使用入門，請參閱[這篇文章](https://developers.google.com/search/apis/indexing-api/v3/quickstart?hl=zh-tw)。

## AMP 網頁限定：更新快取及使用元件

如果想確保您的 AMP 內容在新聞披露當下立即發布最新資訊，請採取下列措施。

### 更新快取

當使用者點選 AMP 網頁，Google AMP 快取就會自動要求更新，以便在快取內容後為下一位使用者提供最新內容。不過，如果您希望在原始網域上的內容改變時立即強制更新快取，也可以傳送[更新要求給 Google AMP 快取](https://developers.google.com/amp/cache/update-cache?hl=zh-tw)。如果您的網頁內容會隨著即時新聞事件的發展持續更新，這種做法就相當實用。

### 使用與新聞相關的 AMP 元件

* [`<amp-live-list> </amp-live-list>`](https://amp.dev/documentation/components/amp-live-list/)：將即時內容加入您的報導，並讓系統根據來源文件更新報導內容。如果您不想在後端設定任何額外服務，又希望能輕鬆重新載入內容，就很適合採用這種做法。[瞭解如何實作 `<amp-live-list></amp-live-list>`](https://amp.dev/documentation/examples/news-publishing/live_blog/?format=websites)。
* [`<amp-script></amp-script>`](https://amp.dev/documentation/components/amp-script/)：在 AMP 網頁中執行您自己的 JavaScript。這種做法既靈活又有彈性，您可以將要發布在電腦版網頁或非 AMP 行動版網頁上的任何內容搬移至 AMP 網頁中。`<amp-script></amp-script>` 支援 WebSocket、互動式可擴充向量圖形等技術，所以您可以藉此製作選舉報導地圖、即時圖表、意見調查等引人注目的新聞網頁。目前 AMP 團隊正在積極徵求對於這項新功能的使用意見，如果這項功能因為某些因素不能滿足您的使用需求，請[告訴我們](https://github.com/ampproject/amphtml/issues/new/choose)。

如有任何疑問，歡迎透過[論壇](https://support.google.com/webmasters/community?hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 與我們聯絡。

發文者：AMP 團隊的 [Patrick Kettner](https://twitter.com/patrickkettner) 和 Naina Raisinghani
