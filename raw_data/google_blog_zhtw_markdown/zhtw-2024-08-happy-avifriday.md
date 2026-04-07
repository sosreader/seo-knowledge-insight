# 支援 Google 搜尋中的 AVIF
- **發佈日期**: 2024-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2024/08/happy-avifriday?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2024 年 8 月 30 日，星期五

近年來，AVIF 已成為網路上最常用的圖片格式之一。
很高興在此宣布，AVIF 現已成為 Google 搜尋中[支援的檔案類型](https://developers.google.com/search/docs/crawling-indexing/indexable-file-types?hl=zh-tw)，適用於 Google 圖片以及 Google 搜尋中任何使用圖片的位置。您無須採取任何特別的行動，Google 會為您的 AVIF 檔案建立索引。

![Googlebot 和 Crawley 會查看圖片是否與 AVIF 相容](https://developers.google.com/search/blog/images/googlebot-crawley-binoculars.avif?hl=zh-tw)

[AVIF](https://en.wikipedia.org/wiki/AVIF) 是一種以 AV1 影片壓縮標準為基礎的開放式圖片檔案格式。所有主要網路瀏覽器都支援這種格式，而且網路上各種服務和平台也都支援 AVIF 圖片檔案格式的圖片，包括 [WordPress](https://make.wordpress.org/core/2024/02/23/wordpress-6-5-adds-avif-support/)、[Joomla](https://issues.joomla.org/tracker/joomla-cms/41381) 和 [CloudFlare](https://blog.cloudflare.com/generate-avif-images-with-image-resizing/)。我們不建議您盲目地針對網站上的所有圖片進行全面更改：請花點時間評估哪種格式最符合您的特定需求。如果您選擇變更部分圖片的圖片檔案格式，因而導致檔案名稱或副檔名變更，請務必設定[伺服器端重新導向](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=zh-tw#serverside)。

如想瞭解其他與網站圖片搜尋引擎最佳化 (SEO) 相關的事項，請參閱我們的[圖片搜尋引擎最佳化 (SEO) 指南](https://developers.google.com/search/docs/appearance/google-images?hl=zh-tw)。如有其他問題，歡迎前往[搜尋中心產品討論社群](https://goo.gle/sc-forum)留言告訴我們。

發文者：Google 瑞士團隊的搜尋服務代表 [John Mueller](https://developers.google.com/search/blog/authors/john-mueller?hl=zh-tw)
