# 新增會員方案標記支援
- **發佈日期**: 2025-06-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2025/06/loyalty-program?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2025 年 6 月 10 日

![搜尋結果中的購物知識面板，顯示會員價](https://developers.google.com/static/search/docs/images/loyalty-program.png?hl=zh-tw)

購物者在線上購買產品時，會將會員福利 (例如價格較低、可賺取會員點數) 列為主要考量因素。今天，我們新增了支援功能，可在 [`Organization`](https://developers.google.com/search/docs/appearance/structured-data/organization?hl=zh-tw) 結構化資料下定義會員方案，並搭配 [`Product`](https://developers.google.com/search/docs/appearance/structured-data/product?hl=zh-tw) 結構化資料下的會員福利。

新增[會員結構化資料](https://developers.google.com/search/docs/appearance/structured-data/loyalty-program?hl=zh-tw)後，你的商家就能在產品搜尋結果中搭配會員福利一起顯示。

如果您沒有 Merchant Center 帳戶，但希望能夠提供商家會員方案，則在機構結構化資料中新增會員方案尤其重要。Merchant Center 已可讓您為自己的商家提供[會員方案](https://support.google.com/merchants/answer/12827255?hl=zh-tw)，因此，如果您有 Merchant Center 帳戶，建議您改為在其中定義會員方案。

## 使用複合式搜尋結果測試進行測試

在 [`Organization`](https://developers.google.com/search/docs/appearance/structured-data/organization?hl=zh-tw) 結構化資料中加入會員方案，並在[產品](https://developers.google.com/search/docs/appearance/structured-data/product?hl=zh-tw)結構化資料中加入會員福利後，就可以提交含有會員標記的網頁網址或程式碼片段，透過[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)來測試標記。透過這項工具，您就能確認標記是否有效。例如，以下是針對會員方案標記的測試：

![複合式搜尋結果測試中的會員方案標記](https://developers.google.com/static/search/blog/images/loyalty-program-rrt.png?hl=zh-tw)

我們希望這項新增功能可方便您新增商家會員方案和福利，並讓這些資訊能夠在 Google 購物體驗中顯示。如果您有任何問題或疑慮，請透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Astructured_data%29&hl=zh-tw)或 [LinkedIn](https://www.linkedin.com/showcase/googlesearchcentral/) 與我們聯絡。

發文者：Google 購物軟體工程師 [Irina Tuduce](https://developers.google.com/search/blog/authors/irina-tuduce?hl=zh-tw) 和 [Pascal Fleury](https://developers.google.com/search/blog/authors/pascal-fleury?hl=zh-tw)
