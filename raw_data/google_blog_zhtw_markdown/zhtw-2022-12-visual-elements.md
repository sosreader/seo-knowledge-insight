# Google 搜尋的視覺元素
- **發佈日期**: 2022-12-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/12/visual-elements?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 12 月 13 日，星期二

走進圖書館，索取一本書，卻沒指明哪一本。館員露出困惑的表情，然後可能會問您一大堆問題，試著搞懂是哪本書：書實在太多了 (具體數字是[超過 129,864,880](https://booksearch.blogspot.com/2010/08/books-of-world-stand-up-and-be-counted.html) 本)。上述對話其實很像我們在 Twitter 上觀察到的現象，有人試著要討論搜尋結果網頁的某項搜尋功能或 UI 元素，但：要怎麼稱呼那些星號？又該怎麼讓這些東西隨著我的網站一起顯示？

![Googlebot 在繪製搜尋結果並新增視覺元素註解，而 Crawley 努力提供協助，帶來許多美術用品和三角形木作工具](https://developers.google.com/static/search/blog/images/googlebot-paints-visual-elements.png?hl=zh-tw)

Google 搜尋結果網頁不是由超過 129,864,880 個元素組成，但想要識別出您要搜尋的特定元素，可能有點難度。元素之間可能非常類似，有時甚至全然難以辨別，而有時這些元素則有多種口語稱呼，不易聽懂。因此想改善這種情形。

## 視覺元素庫隆重登場

全新的[視覺元素庫](https://developers.google.com/search/docs/appearance/visual-elements-gallery?hl=zh-tw)旨在協助您識別搜尋結果網頁中最常見和最重要的視覺元素。其中收錄了 22 個視覺元素，包括最有可能出現在搜尋結果網頁上的元素，以及與網站擁有者、SEO 專員密切相關的元素，包括：

* [**來源資訊**](https://developers.google.com/search/docs/appearance/visual-elements-gallery?hl=zh-tw#attribution)：可協助使用者以視覺化方式辨識搜尋結果來源的元素，例如網站名稱、網址和網站小圖示。
* [**文字搜尋結果**](https://developers.google.com/search/docs/appearance/visual-elements-gallery?hl=zh-tw#text-result)：過去稱為「10 個藍色連結」和「網頁搜尋結果」，文字結果是自 1995 年以來就存在的元素，當時我們仍名為 [Backrub](https://about.google/our-story/?hl=zh-tw)。我們相信「文字搜尋結果」這個名稱能更準確表示搜尋結果的依據，也就是已建立索引網頁的文字內容。
* **[影片](https://developers.google.com/search/docs/appearance/visual-elements-gallery?hl=zh-tw#video-result)和[圖片搜尋結果](https://developers.google.com/search/docs/appearance/visual-elements-gallery?hl=zh-tw#image-result)**：過去稱為「圖片和影片通用結果」，影片和圖片搜尋結果的依據，是在個別到達網頁的脈絡中編入索引的個別媒體。
* [**探索功能**](https://developers.google.com/search/docs/appearance/visual-elements-gallery?hl=zh-tw#exploration)：通常稱為「其他人也問了以下問題」，這些視覺元素可協助使用者拓展搜尋的可能性。

每個元素群組都配有一個抽象的插圖，說明視覺元素在搜尋結果網頁中可能呈現的樣子，並附有標籤，說明每個元素的名稱，以及您可以到哪裡查看更多資訊，瞭解如何為自家網站改變或啟用元素。此外，抽象插圖設計也有助於讓指南在 18 種語言的搜尋中心保有一致性。

## 未來的視覺元素

我們的新設定可讓我們輕鬆在元素庫中新增視覺元素，無需太多管理；實際上這也是我們計畫的一部分：當某個視覺元素在搜尋結果網頁變得常用，我們就可以新增到元素庫。不過，我們預計的做法是，只加入對於網站擁有者和 SEO 專員具有一定意義的元素。

我們設計這個全新的元素庫，是為了讓大家更容易討論及瞭解搜尋結果網頁中顯示的元素。如果您想與我們討論這些內容，請在 [Twitter](https://twitter.com/googlesearchc) 或[搜尋中心說明論壇](https://support.google.com/webmasters/community?hl=zh-tw)留言。此外，您也可以直接在說明文件網頁中透過「提供意見」按鈕，讓我們知道您的想法。

發文者：[Lizzi Sassman](https://www.okaylizzi.com/+) 和 [Gary Illyes](https://garyillyes.com/+)
