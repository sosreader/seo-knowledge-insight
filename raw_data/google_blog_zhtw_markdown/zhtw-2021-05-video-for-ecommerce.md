# 電子商務網站的影片搜尋引擎最佳化 (SEO) 最佳做法
- **發佈日期**: 2021-05-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/05/video-for-ecommerce?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 5 月 12 日，星期三

電子商務網站上越來越常出現影片。如果您是網站擁有者，可以利用影片讓購物者更深入地瞭解您銷售的產品，或是建立良好信譽，讓大眾認為您是值得信賴的專家。此外，影片在 Google 搜尋中會看起來很顯眼。藉由在 Google 展示影片內容，您可以讓更多人透過不同管道發現您的網站，進而提升商家知名度和網站參與度。

## 影片出現在 Google 搜尋結果中的位置

Google 搜尋結果網頁或「影片」分頁上都會顯示影片內容。影片通常會以縮圖和實用資訊 (如播放時長和摘要文字) 的形式顯示。此外，Google 現在可以醒目顯示影片內容中的[重要時刻](https://developers.google.com/search/docs/appearance/video?hl=zh-tw#key-moments)，讓使用者能瀏覽圖書章節一樣觀看影片。使用者輕觸某個重要時刻後，系統就會將他們導向您的網站，並讓他們從相應時刻開始觀看影片。

![在含有影片的 Google 搜尋結果網頁上，重要時刻的呈現方式示例。](https://developers.google.com/static/search/blog/images/video-for-ecommerce-1.gif?hl=zh-tw)

## 影片在電子商務網站上的常見用途

影片可以為造訪電子商務網站的購物者提供引人入勝的體驗，也可能對在 Google 搜尋網頁上尋找相關內容的使用者有所幫助。以下是在電子商務網站上使用影片的常見方式：

**產品頁面：**產品頁面常嵌有影片，因為與單純使用靜態圖片相比，影片可以提供更豐富的產品資訊，展示概念構想或功能相關內容。舉例來說，概念構想內容可能會顯示一家人在公園裡使用野餐籃愉快地野餐，功能相關內容則可能會說明如何折疊嬰兒手推車以便收納。使用者透過 Google 搜尋調查想購買的商品時，這類影片就相當實用。

**文章和網誌文章：**網站的文章或網誌文章中也可能含有影片，分享所售商品的比較/評估評論，或是分享背景故事，介紹您商家的獨特之處。不論使用者仍在調查商品或是已經準備購物，都能夠在不同類型的內容中找到實用資訊。此外，許多購物者也對您的商家本身感興趣，例如您對資源回收或社區支援的態度。

**直播：**進階網站可能也支援嵌入直播，讓觀眾與主持人互動，進而與客戶建立更緊密的關係。無論您想事先排定直播時間，或是臨時發起直播，都沒問題。部分影視串流服務可讓您將直播嵌入自己的網頁，因此您可以充分運用他們的基礎架構，吸引客戶繼續瀏覽您的網站。如果您將直播內容錄製下來，可以將這段影片做為一般影片保留在網站上。這樣一來，這段影片就能在 Google 搜尋中保留更長時間，供尋找相關內容的使用者觀看。

您還可以透過其他方式運用影片來支援電子商務，包括將影片放上社群媒體。將影片交由社群媒體平台代管後，您通常不須執行任何額外操作，因為平台會負責確保 Google 能為該影片建立索引。

## 充分運用 Google 搜尋和探索功能

按照以下提示操作，可以協助 Google 為您電子商務網站上代管的影片內容建立索引。如果您使用的 CMS 或電子商務平台無法讓您直接控管 HTML 標記，您可能需要尋找合適的外掛程式：

* 在含有影片內容的網頁上加入 [`Video` 結構化資料](https://developers.google.com/search/docs/appearance/structured-data/video?hl=zh-tw)。由於 Google 可能無法檢索須經使用者互動才會顯示的影片，如果產品頁面的媒體輪轉介面中嵌有影片，就更應該加入上述結構化資料。
* 如果您希望盡量提高某些影片的曝光率，建議您專門建立一個頁面，用來說明這些影片的內容。舉例來說，「如何清潔 X 牌咖啡機」頁面吸引的流量，可能不同於 X 牌產品頁面；這類產品頁面含有解說影片和大量其他資訊。您也可以將同一部影片同時放在專屬說明網頁和產品頁面中。
* ![Google 搜尋結果中，影片「直播」標記的顯示示例。](https://developers.google.com/static/search/blog/images/video-for-ecommerce-2.png?hl=zh-tw)
  為直播內容新增結構化資料，讓影片顯示[「直播」標記](https://developers.google.com/search/docs/appearance/video?hl=zh-tw#live-badge)，有助於在直播開始時吸引使用者注意。使用 [Indexing API](https://developers.google.com/search/apis/indexing-api/v3/quickstart?hl=zh-tw)，在直播開始和結束時向 Google 提供即時資訊。直播活動結束後，您可以提供直播錄製內容供使用者觀看，但這類影片無法顯示「直播」標記。
* 建立並提交[影片 Sitemap 檔案](https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps?hl=zh-tw)有助於 Google 找到所有含有影片內容的網頁。
* 除了 `Video` 結構化資料外，您也可以考慮加入與各個網頁有關的結構化資料，例如 [`Product`](https://developers.google.com/search/docs/appearance/structured-data/product?hl=zh-tw)、[`HowTo`](https://developers.google.com/search/docs/appearance/structured-data/how-to?hl=zh-tw) 或 [`Q&A`](https://developers.google.com/search/docs/appearance/structured-data/qapage?hl=zh-tw) 標記。

如需更多資訊，請參閱[這些新資源](https://developers.google.com/search/blog/2021/03/new-resources-for-video-seo?hl=zh-tw)，概略瞭解影片在 Google 上的呈現方式，以及含有影片的網站適用的[最佳做法](https://developers.google.com/search/docs/appearance/video?hl=zh-tw)。

發文者：Google 搜尋中心團隊的搜尋服務代表 [Alan Kent](https://twitter.com/akent99)
