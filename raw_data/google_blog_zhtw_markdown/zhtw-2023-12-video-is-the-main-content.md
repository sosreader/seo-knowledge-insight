# 影片模式現在只會顯示以影片為主要內容的網頁
- **發佈日期**: 2023-12-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/12/video-is-the-main-content?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 12 月 4 日，星期一

[今年稍早](https://developers.google.com/search/blog/2023/04/simplifying-video?hl=zh-tw)，我們進行了調整，改成當影片是網頁的主要內容時，只在主要 Google 搜尋結果網頁上搜尋結果旁邊顯示影片縮圖。今天，我們將這項變更擴大到影片模式中的搜尋結果，方便使用者進一步找到想看的影片內容，而不需要搜尋整個網頁以找到該影片。這項異動將從今天開始推行，最多可能需要一週的時間才能完成。

![Google 搜尋結果中的影片模式](https://developers.google.com/static/search/blog/images/video-mode-on-google.png?hl=zh-tw "Google 搜尋結果中的影片模式")

本次更新後，使用者在影片模式中點選搜尋結果後，系統只會將使用者導向影片為主要內容的網頁。以下提供一個網頁範例，其中影片是網頁的主要內容：影片位於不需捲動且顯眼的位置，而且網頁的主要用途是觀看影片。

![以影片為網頁主要內容的網頁](https://developers.google.com/static/search/docs/images/dedicated-video-page.png?hl=zh-tw "以影片為網頁主要內容的網頁")

以下列舉幾種網頁類型，其中的影片是用於補充文字內容，而非網頁的主要重點：

* 網誌文章：影片與文字相輔相成，而非網頁的主要內容
* 產品詳細資料網頁：含有補充影片
* 影片類別網頁：列出多個同樣顯眼的影片

隨著更新推出，Search Console 的[影片索引報表](https://support.google.com/webmasters/answer/9495631?hl=zh-tw)會顯示這項異動帶來的影響。非網頁主要內容的影片在 Search Console 中會顯示為「沒有任何影片編入索引」。此外，我們也會在報表中新增理由，說明這些影片未編入索引的原因：「網頁的主要內容不是影片」，而是取代下列問題，藉此簡化報表內容：

* 無效的影片網址
* 不支援的影片格式
* 不明的影片格式
* 內嵌資料網址無法做為影片網址
* 影片在可視區域外
* 影片畫面太小
* 影片畫面高度過高

![Search Console 中的影片索引報表，並附上新問題摘要：網頁的主要內容不是影片](https://developers.google.com/static/search/blog/images/video-is-main-content-search-console.png?hl=zh-tw)

由於這些影片不會再顯示於影片模式中，因此具有已編入索引影片的網頁數量應該會減少。此外，Search Console 中[成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)、[影片索引報表](https://support.google.com/webmasters/answer/9495631?hl=zh-tw)，以及[影片複合式搜尋結果報告](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)中的影片曝光次數也會減少。

如要進一步瞭解為影片建立索引的最佳做法，請參閱[影片最佳做法指南](https://developers.google.com/search/docs/appearance/video?hl=zh-tw)。如有任何疑問，歡迎前往[搜尋中心產品討論社群](https://goo.gle/sc-forum)發文提問，和志同道合的專家一起討論。

發文者：Google 搜尋產品經理 [Cory Benavente](https://developers.google.com/search/blog/authors/cory-benavente?hl=zh-tw)
