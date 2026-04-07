# 在 Google 搜尋中啟用影片重要時刻的全新方式
- **發佈日期**: 2021-07-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/07/new-way-key-moments?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 7 月 19 日，星期一

自 2019 年推出[影片重要時刻](https://developers.google.com/search/docs/appearance/video?hl=zh-tw#key-moments)後，我們便持續擴充及改善這項功能。我們不斷改進設計，並讓重要時刻功能適用於更多影片 (包括行動裝置和桌上型電腦)，只要是 Google 搜尋的服務區域都能使用這項功能。重要時刻功能幫助更多人與影片中最相關的片段直接互動，像翻閱書中章節那樣瀏覽影片。

現在，我們推出一種全新方法，可以讓您為網站上的影片啟用重要時刻功能，省去手動為各個片段加上標籤的麻煩。只要告知 Google 您的網址模式，讓系統能直接跳至影片中特定的時間戳記即可，Google 會隨即運用 AI 辨識影片中的重要時刻，並直接在搜尋結果中顯示連結，引導使用者前往這些時間點。

如果偏好以手動方式為影片的重要時刻加上標記，可以繼續使用 [`Clip` 標記](https://developers.google.com/search/docs/appearance/structured-data/video?hl=zh-tw#clip)。或者，您也可以使用 [`nosnippet` `meta` 標記](https://developers.google.com/search/docs/advanced/appearance/good-titles-snippets?hl=zh-tw#nosnippet)來停用重要時刻功能。
![Google 搜尋中的重要時刻](https://developers.google.com/static/search/blog/images/key-moments-example1.png?hl=zh-tw)
![Google 搜尋中的重要時刻](https://developers.google.com/static/search/blog/images/key-moments-example2.png?hl=zh-tw)

我們在 Google I/O 大會期間首次[宣布](https://developers.google.com/search/blog/2021/05/search-io-2021?hl=zh-tw)將進行 [`SeekToAction`](https://developers.google.com/search/docs/appearance/structured-data/video?hl=zh-tw#seek) 的 Beta 版測試，這項功能於今天通過測試階段，任何有影片內容的網站都支援使用這項標記。設定這項標記時，請記住以下幾點：

* 您的網址必須具備深層連結，可將使用者導向影片開頭以外的其他時間點。舉例來說，`https://www.example.com/example?t=30` 會從影片開頭的 30 秒後開始播放。
* 您可以將 [`SeekToAction` 標記](https://developers.google.com/search/docs/appearance/structured-data/video?hl=zh-tw#seek)用於想讓 Google 自動識別重要時刻的所有影片網頁，並請同時遵循其他的[指南規範](https://developers.google.com/search/docs/appearance/structured-data/video?hl=zh-tw#clip-guidelines)。如要瞭解詳細的範例，請參閱[這篇文章](https://developers.google.com/search/docs/appearance/structured-data/video?hl=zh-tw#seektoaction)。
* Google 必須能夠[擷取影片內容檔案](https://developers.google.com/search/docs/appearance/video?hl=zh-tw#allow-fetch)，才能自動識別影片中的重要時刻。

請注意，`SeekToAction` 標記僅適用於內嵌於您網站上的影片，如果您將影片張貼到您無法控制其 schema.org 標記的平台上，請與該平台聯絡，瞭解對方是否支援這項標記。

希望 `SeekToAction` 標記能讓您以更輕鬆、更有效率的方式啟用重要時刻功能，吸引使用者與您的影片進行更深入的互動。如有任何疑問，歡迎前往[論壇](https://support.google.com/webmasters/community?hl=zh-tw)發文提問、[在 Twitter 上透過 @googlesearchc](https://twitter.com/googlesearchc)與我們聯絡，或者直接在說明文件頁面中提供意見回饋。

發文者：產品經理 [Danielle Marshak](https://www.linkedin.com/in/daniellemarshak/)
