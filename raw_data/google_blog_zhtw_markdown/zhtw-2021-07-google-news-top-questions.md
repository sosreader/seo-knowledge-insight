# 關於 Google 新聞顯示方式的部分常見問題與解答
- **發佈日期**: 2021-07-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/07/google-news-top-questions?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
這篇網誌文章已發布一段時間。部分資訊可能已經過時，例如圖片可能會有缺漏，連結也可能失效。請查看[出版品頁面更新內容](https://support.google.com/news/publisher-center/answer/14859160?hl=zh-tw)。

2021 年 7 月 16 日星期五

Google 從多位值得信賴的發布者取得兼具關聯性和公信力的新聞內容，供使用者閱讀，希望可以幫助大眾瞭解全球動態。今天，我們將針對發布者提出的一些常見問題提供解答，讓發布者更加瞭解 Google 新聞和 Google 搜尋顯示新聞內容的方式。

## Google 會在哪裡顯示新聞內容？

[多種 Google 產品](https://newsinitiative.withgoogle.com/hownewsworks/products/)都可能會顯示新聞內容，包括 Google 新聞、Google 搜尋、Google 助理、YouTube 和 Google 探索。本篇文章會將焦點放在Google 新聞和 Google 搜尋中的[新聞平台](https://support.google.com/news/publisher-center/answer/9607026?hl=zh-tw)，因為大部分發布者提出的問題都與上述產品有關。

[Google 新聞](https://news.google.com/about/?hl=zh-tw) (包含 Google 新聞 iOS 和 Android 版應用程式以及 [news.google.com](https://news.google.com/?hl=zh-tw)) 提供一系列豐富的功能，協助使用者找到最新消息的連結，以及追蹤特定主題和新聞來源。舉例來說，「為您推薦」動態消息包含[根據您的興趣](https://support.google.com/googlenews/answer/9005601?hl=zh-tw)顯示的新聞報導，而應用程式中的「頭條新聞」版面則是對特定地區的所有使用者提供具有新鮮感和新聞價值的新聞報導。使用者也可以在 Google 新聞中搜尋內容連結。

![Google 新聞頭條新聞](https://developers.google.com/static/search/blog/images/Google-News-Headlines.png?hl=zh-tw "Google 新聞頭條新聞")

Google 搜尋可在網頁搜尋結果中顯示新聞內容連結，但 Google 搜尋本身其實也包含兩個新聞專屬平台。「焦點新聞」輪轉介面通常會顯示在 Google 搜尋結果頁面的頂端，當使用者針對近期運動賽事或最新科學突破等時下熱門主題搜尋相關資訊時，系統就會醒目顯示相關新聞報導。使用者在運用 Google 搜尋時，點選「新聞」分頁可以將搜尋範圍限定在與新聞相關的搜尋結果，掌握更全面的新聞背景資訊。

![Google 新聞焦點新聞](https://developers.google.com/static/search/blog/images/Google-News-TopStories.png?hl=zh-tw "Google 新聞焦點新聞")

## 我的網站能顯示在這些位置嗎？

您的網站會自動納入 Google 新聞和 Google 搜尋的新聞平台，無需提出申請。您只需要製作符合下列條件的相關內容即可：

* 具備高度[專業性、權威性和可信度](https://developers.google.com/search/blog/2019/08/core-updates?hl=zh-tw)。
* 長期持續製作原創的新聞相關內容。
* 遵守《[Google 新聞政策](https://support.google.com/news/publisher-center/answer/6204050?hl=zh-tw)》。

我們過去曾開放使用者申請在這些新聞產品中顯示新聞內容，但在近兩年前 (2019 年 12 月）終止了這項申請程序，改為[推出](https://developers.google.com/search/blog/2019/12/google-publisher-center?hl=zh-tw)新聞發布者中心。這項變更讓我們得以在整個網路世界中找到更多適合的新聞內容，包括過去可能錯失的遺珠，因為當時有些網站擁有者並不知道必須申請才能顯示他們的新聞內容。

本文介紹的詳細資格規定僅適用於「Google 新聞」、「焦點新聞」和 Google 搜尋中的「新聞」分頁。
這些詳細資訊並不會影響 Google 搜尋中網頁搜尋結果的顯示方式。進一步瞭解如何[讓 Google 顯示您的網站](https://developers.google.com/search/docs/fundamentals/get-on-google?hl=zh-tw)。

## 如何得知 Google 是否顯示我的網站？

建議您在 Search Console 中，針對 [Google 新聞](https://support.google.com/webmasters/answer/10083653?hl=zh-tw)和 [Google 搜尋](https://support.google.com/webmasters/answer/7576553?hl=zh-tw) (以「新聞」搜尋類型篩選搜尋結果) 查看 Search Console 的成效報表。透過這份報表，您可以瞭解自家網站是否獲得來自 Google 新聞和 Google 搜尋內新聞平台的流量。如果是的話，表示您的內容符合顯示資格且具相關性。如要進一步瞭解如何追蹤成效，請參閱[評估 Google 新聞的影響力](https://support.google.com/news/publisher-center/answer/9603442?hl=zh-tw)。

![在 Search Console 中查看 Google 新聞成效](https://developers.google.com/static/search/blog/images/google-news-report-search-console.png?hl=zh-tw "在 Search Console 中查看 Google 新聞成效")
**注意**：雖然您可以在 Google 新聞或 Google 搜尋的「新聞」分頁中使用 `site:` 搜尋查詢，查看這些網頁是否已建立索引，但這不代表這些網頁都能顯示在新聞搜尋結果中。

## 該怎麼做才能提高曝光率？

您的網站會自動納入 Google 新聞和 Google 搜尋的新聞平台，無需提出申請。系統找到適合顯示的內容後，就會根據多種因素[自動決定](https://support.google.com/news/publisher-center/answer/9606702?hl=zh-tw)排名，包括內容關聯性、醒目性、權威性、新鮮度、地理位置和語言。

您可以透過[新聞發布者中心](https://support.google.com/news/publisher-center/answer/9606538?hl=zh-tw)定義網站的特定詳細資料 (例如 RSS 動態消息、網站網址、影片和其他資訊)，協助管理您的品牌，方便 Google 為您的網站建立索引。新聞發布者中心還可以用來為出版品建立「新聞來源」頁面，如果您還沒有這樣的頁面，也可以考慮這麼做。這樣一來，如果 Google 新聞使用者想要[追蹤](https://support.google.com/googlenews/answer/9010862?hl=zh-tw#zippy=,follow-an-interest)新聞出版品及查看最新內容，就可以透過該頁面進行。

雖然新聞發布者中心可協助您管理符合資格的內容，但資格通過與否是由系統的自動程序判定。也就是說，[獲准](https://support.google.com/news/publisher-center/answer/9547901?hl=zh-tw)使用新聞發布者中心後，即使透過該平台提交內容或擁有新聞來源網頁，也不代表您的內容會顯示在以下位置：

* Google 新聞的搜尋結果
* Google 新聞的功能 (例如「為您推薦」或「頭條新聞」)
* Google 搜尋的新聞平台 (例如「焦點新聞」或「新聞」分頁)

如果您不希望 Google 新聞顯示您的內容，可以[封鎖存取權](https://support.google.com/news/publisher-center/answer/9605477?hl=zh-tw)，同時不影響 Google 搜尋繼續為您的網站建立索引和排名。

## 我已遵循你提供的所有建議，為什麼系統仍未顯示我的網站？

請務必定期製作優質的新聞內容，並強化內容的專業性、權威性和可信度。如需相關實用建議，歡迎參閱我們[關於核心更新的網誌文章](https://developers.google.com/search/blog/2019/08/core-updates?hl=zh-tw)。我們的系統會定期執行，並自動偵測網站是否已符合相關評估標準。

當然，自動化系統不可能完美無缺，因此我們會持續進行改善。自從我們在近兩年前終止申請程序後，目前採用的自動化系統已協助上千位新發布者透過 Google 新聞和 Google 搜尋的新聞平台吸引訪客，受惠發布者包括全國性的新聞品牌，以及新興的在地出版社。

此外，我們也鼓勵所有使用者造訪「[Google 平台呈現新聞的方式](https://newsinitiative.withgoogle.com/hownewsworks/mission/)」網站，深入瞭解相關資訊。

發文者：Google 搜尋公關 Danny Sullivan
