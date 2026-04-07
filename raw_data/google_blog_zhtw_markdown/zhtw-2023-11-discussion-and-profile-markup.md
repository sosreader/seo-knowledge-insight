# 結構化資料新功能：討論區和個人資料頁面標記
- **發佈日期**: 2023-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/11/discussion-and-profile-markup?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 11 月 27 日，星期一

我們在此宣布，系統將支援在 Google 搜尋中使用[個人資料頁面](https://developers.google.com/search/docs/appearance/structured-data/profile-page?hl=zh-tw)和[討論區](https://developers.google.com/search/docs/appearance/structured-data/discussion-forum?hl=zh-tw)結構化資料，而在 Search Console 中也新增了相關報告。這類標記可與某些 Google 搜尋功能搭配使用，這些功能的設計宗旨，是要呈現來自社群媒體平台、論壇等社群的第一人稱觀點，因此，採用這類結構化資料，有助於確保 Google 搜尋在這些功能中顯示的內容盡可能正確且完整。

![插圖：搜尋結果中的觀點篩選器](https://developers.google.com/static/search/blog/images/perspectives-social.png?hl=zh-tw)

## 醒目顯示創作者資訊並識別論壇內容

![插圖：搜尋結果中的創作者資訊](https://developers.google.com/static/search/blog/images/social-profile-search-result.png?hl=zh-tw)

只要是由創作者 (個人或機構皆可) 分享第一手觀點的網站，就很適合使用 [`ProfilePage` 標記](https://developers.google.com/search/docs/appearance/structured-data/profile-page?hl=zh-tw)。這可讓 Google 搜尋更有效地識別創作者資訊，例如姓名或社群暱稱、個人資料相片、追蹤者人數或內容熱門程度。無論是[觀點](https://blog.google/products/search/google-search-perspectives/?hl=zh-tw)還是[討論和論壇](https://blog.google/products/search/google-search-discussions-forums-news/?hl=zh-tw)功能，都採用了 `ProfilePage` 標記。

![插圖：討論和論壇功能](https://developers.google.com/static/search/docs/images/discussions-and-forums-rich-result.png?hl=zh-tw)

[`DiscussionForumPosting` 標記](https://developers.google.com/search/docs/appearance/structured-data/discussion-forum?hl=zh-tw)適用於任何論壇式網站，這類網站會集結眾人分享的第一手觀點。藉由這種標記，Google 搜尋可更準確地識別網路上的論壇網站和線上討論區。只要是標有此標記的論壇，我們都會考量其內容是否適合顯示在「觀點」和「討論與論壇」功能中。但請注意，使用這個標記並不保證系統一定就會顯示相關內容。

## 比較問與答標記和論壇標記

如果你的問答主題使用者論壇已採用問與答標記，不妨一併參閱更新版的[問與答結構化資料說明文件](https://developers.google.com/search/docs/appearance/structured-data/qapage?hl=zh-tw)，瞭解更詳盡的全新討論區指南。

你不必在同一個網頁上同時使用這兩種結構化資料；建議你改用最符合所需用途的方法：

* **問與答論壇**：如果你的論壇結構是問題後接答案，請使用[問與答標記](https://developers.google.com/search/docs/appearance/structured-data/qapage?hl=zh-tw)。
* **一般論壇**：如果你的論壇結構較為籠統，且並非僅限問答內容，請使用 [`DiscussionForumPosting`](https://developers.google.com/search/docs/appearance/structured-data/discussion-forum?hl=zh-tw)。

## 使用 Search Console 驗證及監控你的結構化資料

為協助你監控討論串和個人資料頁面的標記問題，我們將針對個人資料頁面和討論區，推出 [Search Console 複合式搜尋結果報告](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)，讓你查看加上標記的網頁有哪些錯誤、警告和有效項目。此外，在複合式搜尋結果測試中，我們也為這兩項功能提供了支援，協助你測試及驗證標記。

![個人資料頁面的複合式搜尋結果狀態報告](https://developers.google.com/static/search/blog/images/profile-page-report.png?hl=zh-tw)
![討論區的複合式搜尋結果狀態報告](https://developers.google.com/static/search/blog/images/discussion-forum-report.png?hl=zh-tw)
