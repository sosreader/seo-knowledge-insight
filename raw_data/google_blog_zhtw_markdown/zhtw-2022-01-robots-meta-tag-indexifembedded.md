# 全新漫遊器標記：indexifembed透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2022-01-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/01/robots-meta-tag-indexifembedded?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 1 月 21 日，星期五

今天，我們推出了全新的漫遊器標記「[`indexifembedded`](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=zh-tw#indexifembedded)」，讓您可以進一步控管系統將內容編入索引的情況。你可以透過 `indexifembedded` 標記讓 Google 知道，某項內容雖然透過 [`iframes`](https://developer.mozilla.org/docs/Web/HTML/Element/iframe) 和類似的 HTML 標記嵌入到其他網頁，甚至該內容網頁設有 `noindex` 標記，您還是希望系統將該內容編入索引。

`indexifembedded` 標記所處理的這項常見問題，對於媒體發布商影響特別大：他們可能希望自家內容在嵌入到第三方網頁的情況下，可以納入索引中，但不一定想自行將自家媒體頁面編入索引中。他們不希望系統將媒體網頁編入索引，因此目前在這類網頁上使用了 `noindex` 標記。然而 `noindex` 標記也會防止系統建立索引時在其他網頁中嵌入該內容。

新的漫遊器標記 `indexifembedded` 用於搭配 `noindex` 標記運作，前提是這個含有 `noindex` 的網頁必須透過 `iframe` 或類似的 HTML 標記 (例如 [`object`](https://developer.mozilla.org/docs/Web/HTML/Element/object)) 嵌入到其他網頁。舉例來說，如果 `podcast.host.example/playpage?podcast=12345` 同時含有 `noindex` 和 `indexifembedded` 標記，表示 Google 可以在建立索引時，將該網頁上代管的內容嵌入到 `recipe.site.example/my-recipes.html` 中。

如要限定您的內容只有在嵌入到其他網頁時才納入索引，請務必新增 `indexifembedded` 並搭配 `noindex` 標記。例如：

```
<meta name="googlebot" content="noindex" />
<meta name="googlebot" content="indexifembedded" />
<!-- OR -->
<meta name="googlebot" content="noindex,indexifembedded" />
```

或者，您也可以在 HTTP 標頭中指定標記：

```
X-Robots-Tag: googlebot:noindex
X-Robots-Tag: googlebot:indexifembedded
...
OR
…
X-Robots-Tag: googlebot:noindex,indexifembedded
```

目前，只有 Google 支援 `indexifembedded` 標記。

希望這個新標記對您有幫助。如有任何問題或意見，歡迎前往 [Twitter](https://twitter.com/googlesearchc) 和我們的[說明論壇](https://support.google.com/webmasters/community?hl=zh-tw)告訴我們。

發文者：[Weizi Wang](https://www.linkedin.com/in/weizi-wang-2a32ab111/) 和 [Gary Illyes](https://garyillyes.com/+)
