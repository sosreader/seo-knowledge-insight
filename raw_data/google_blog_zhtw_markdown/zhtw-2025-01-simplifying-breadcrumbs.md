# 簡化行動搜尋結果中的可見網址元素
- **發佈日期**: 2025-01-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2025/01/simplifying-breadcrumbs?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2025 年 1 月 23 日，星期四

行動版搜尋使用者很快就會看到搜尋結果以更簡潔、更流暢的方式顯示網址。我們最初在[「網站階層」功能](https://googleblog.blogspot.com/2009/11/new-site-hierarchies-display-in-search.html)中推出了導覽標記元素，但發現這項元素在小螢幕上會遭到截斷，因此對使用行動裝置搜尋的使用者而言並不實用。自即日起，我們將逐步更新，在 Google 搜尋支援的所有語言和地區，不再於行動搜尋結果中顯示導覽標記 (電腦版搜尋結果仍會顯示導覽標記)。

顯示畫面如下。在電腦上，[可見網址](https://developers.google.com/search/docs/appearance/visual-elements-gallery?hl=zh-tw#visible-url)仍包含兩個部分：網域和導覽標記。

![電腦版搜尋結果中顯示的可見網址元素外觀](https://developers.google.com/static/search/blog/images/breadcrumb-on-desktop.png?hl=zh-tw)

在行動裝置上，可見網址會簡化為僅顯示網域：

![行動搜尋結果中顯示的可見網址元素外觀](https://developers.google.com/static/search/blog/images/breadcrumb-on-mobile.png?hl=zh-tw)

如果您使用[導覽標記標記](https://developers.google.com/search/docs/appearance/structured-data/breadcrumb?hl=zh-tw)，則無需採取任何行動，因為我們會繼續支援在電腦版搜尋結果中使用導覽標記標記。Search Console 中的[導覽標記複合式搜尋結果報表](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)仍會繼續提供，您仍可在[複合式搜尋結果測試](https://support.google.com/webmasters/answer/7445569?hl=zh-tw)中導入及測試導覽標記標記。

我們希望這項異動能讓使用者在行動裝置上搜尋時，更容易找到所需內容。如有任何意見回饋、問題或評論，歡迎前往 [LinkedIn](https://www.linkedin.com/showcase/googlesearchcentral/) 與我們交流，或是在 [Google 搜尋中心社群](https://support.google.com/webmasters/community?hl=zh-tw)發文提問。

發文者：Google 搜尋產品經理 Caitlin Dorsey
