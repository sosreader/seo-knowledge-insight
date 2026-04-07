# 簡化 Google 搜尋結果中的影片呈現畫面
- **發佈日期**: 2023-04-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/04/simplifying-video?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 4 月 13 日星期四

今天我們進行了一項調整，只有在網頁的主要內容是影片時，Google 搜尋結果旁邊才會顯示影片縮圖。
這麼做能讓使用者輕鬆瞭解造訪網頁時可能看到的內容。

先前我們顯示影片縮圖的方式有兩種。
如果影片是網頁的主要內容，影片縮圖會顯示在網頁資訊的開頭：

![Google 搜尋中的影片搜尋結果](https://developers.google.com/static/search/blog/images/video-result.png?hl=zh-tw)

這項做法維持不變。另一種格式則適用於影片出現在網頁上，但不是網頁主要元素的情況。
在這種情況，縮圖會顯示在網頁資訊的結尾：

![文字搜尋結果的影片縮圖](https://developers.google.com/static/search/blog/images/video-thumbnail-on-text-result.png?hl=zh-tw)

這個第二種格式即將淘汰。在實驗中，這項異動會對發布者的整體參與度影響很小。

![如果影片不是網頁上的主要元素，我們將不會在文字搜尋結果中顯示網頁上影片的縮圖。](https://developers.google.com/static/search/blog/images/simplifying-video-search-results.png?hl=zh-tw)

這項異動會影響 Search Console 的[成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)中影片的搜尋外觀回報指標。[影片索引報告](https://support.google.com/webmasters/answer/9495631?hl=zh-tw)和[影片強化報告](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)中會顯示註解。

如要進一步瞭解為影片建立索引的最佳做法，請參閱[影片最佳做法指南](https://developers.google.com/search/docs/appearance/video?hl=zh-tw)。如有任何疑問，歡迎前往[搜尋中心產品討論社群](https://goo.gle/sc-forum)發文提問，和志同道合的專家一起討論。

發文者：Google 搜尋產品經理 [Cory Benavente](https://developers.google.com/search/blog/authors/cory-benavente?hl=zh-tw)
