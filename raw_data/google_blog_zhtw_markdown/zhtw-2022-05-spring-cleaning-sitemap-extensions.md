# 春季大掃除：部分 Sitemap 擴充元素標記即將停用透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2022-05-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/05/spring-cleaning-sitemap-extensions?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 5 月 6 日，星期五

這些年來，我們推出了數種 Google Sitemap 擴充元素的標記和標記屬性，特別是[圖片](https://developers.google.com/search/docs/crawling-indexing/sitemaps/image-sitemaps?hl=zh-tw)和[影片](https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps?hl=zh-tw)擴充功能。大多數標記的作用都是為了讓網站擁有者能更輕鬆將資料傳送至 Google 搜尋。

在評估 Google Sitemap 擴充元素標記的值之後，我們決定正式淘汰部分標記和屬性，並從說明文件中移除這些標記和屬性。2022 年 8 月 6 日之後，已淘汰的標記對於索引和搜尋功能就不再發生作用。

如果您是 Sitemap 外掛程式開發人員或自行管理 Sitemap，則無須立即採取行動；可以將這些標記和屬性保持不變，不會有不良影響。日後，當這些更新納入到[圖片](https://developers.google.com/search/docs/crawling-indexing/sitemaps/image-sitemaps?hl=zh-tw)和[影片](https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps?hl=zh-tw)擴充元素的下一個架構版本，Search Console 可能會顯示警告。

以下是受影響的標記和屬性：

| Sitemap 擴充元素 | 已淘汰 XML 標記或屬性 | 建議 |
| --- | --- | --- |
| [圖片 Sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/image-sitemaps?hl=zh-tw) | `caption` | 遵循我們的[圖片最佳做法](https://developers.google.com/search/docs/appearance/google-images?hl=zh-tw#use-descriptive-alt-text)。 |
| `geo_location` |
| `title` |
| `license` | 請繼續使用 [IPTC 中繼資料](https://developers.google.com/search/docs/appearance/structured-data/image-license-metadata?hl=zh-tw)來提供授權資料。 |
| [影片 Sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps?hl=zh-tw) | `category` | 遵循我們的[影片最佳做法](https://developers.google.com/search/docs/appearance/video?hl=zh-tw)。 |
| `player_loc[@allow_embed]` |
|
| `player_loc[@autoplay]` |
| `gallery_loc` |
| `price[@all]` |
| `tvshow[@all]` |

簡化 Sitemap 擴充元素之後，我們也希望您能減少程式碼集的複雜性，這樣一來 Sitemap 整體上會更有秩序。如有任何問題或意見，請參閱我們的 [Sitemap 說明文件](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=zh-tw)，或透過 [Twitter](https://twitter.com/googlesearchc) 或[搜尋中心論壇](https://support.google.com/webmasters/community?hl=zh-tw)與我們聯絡。

發文者：Google 搜尋團 [Gary Illyes](https://garyillyes.com/+)
