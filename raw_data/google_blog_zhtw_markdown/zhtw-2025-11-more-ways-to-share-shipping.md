# 更多與 Google 分享運送和退貨政策的方式
- **發佈日期**: 2025-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2025/11/more-ways-to-share-shipping?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2025 年 11 月 12 日，星期三

運送速度、費用和退貨政策是網購族群的主要考量因素。清楚提供出貨資訊，有助於建立顧客信任感並提升購物體驗。

去年，我們在 Search Console 推出[運送和退貨政策](https://developers.google.com/search/blog/2024/07/configure-shipping-and-returns-search-console?hl=zh-tw)，供已設定 Merchant Center 帳戶的商家使用。我們也首次開放所有商家[使用結構化資料新增機構層級的退貨政策](https://developers.google.com/search/blog/2024/06/structured-data-return-policies?hl=zh-tw)。

很高興宣布，我們現在擴大為商家提供運送和退貨資訊的選項，即使沒有 Merchant Center 帳戶也能使用。商家現在可以透過兩種不同的方式，向 Google 提供運送和退貨政策：直接在 Search Console 中設定，或使用新的機構層級結構化資料。

## 直接在 Search Console 中設定政策

![Search Console 中的運送和退貨設定頁面](https://developers.google.com/static/search/blog/images/sc-shipping-settings.png?hl=zh-tw)

我們將擴大 Search Console 設定中的「運送和退貨」功能，凡是 Google 認定為[線上商家](https://support.google.com/webmasters/answer/12660034?hl=zh-tw#online_merchant_def)的網站，皆可使用這項功能。

先前只有已設定 Merchant Center 帳戶的商家才能使用這項功能。
現在，如果 Google 認定你的網站是線上商家，你就能直接在 Search Console 中設定運送和退貨政策。這項功能提供以使用者介面為基礎的方法，可與 Google 分享資訊。

你可以使用這項替代方法這項資訊，不必使用結構化資料。請注意，Search Console 中設定的內容會優先於網站上的結構化資料。

「運送和退貨」設定將在接下來幾週內，逐步向所有國家/地區和語言推出。

## 新增機構層級運送政策標記

如果你想透過程式碼管理這項資訊，請使用新推出的[機構層級運送政策結構化資料](https://developers.google.com/search/docs/appearance/structured-data/shipping-policy?hl=zh-tw)。

這項新的標記支援功能，可搭配去年推出的機構層級*退貨*政策一起使用。現在你只要指定一般全網站運送政策，不必[為每項產品新增運送標記](https://developers.google.com/search/docs/appearance/structured-data/merchant-listing?hl=zh-tw#shipping)。如果運送政策適用於大多數產品，建議採用這個做法，因為這樣可以減少需要管理的標記數量。針對個別產品指定的運送政策，優先順序仍高於這些特定商品的機構層級一般政策。

建議在說明運送政策的頁面中，放置運送結構化資料 (嵌入 `Organization` 中)。接著提交含有運送標記的網頁網址，或貼上含有運送標記的程式碼片段，透過[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)來測試標記。透過這項工具，您就能確認標記是否有效。 例如，以下是運送政策標記的測試：

![複合式搜尋結果測試中的運送政策標記](https://developers.google.com/static/search/blog/images/shipping-policy-markup-rrt.png?hl=zh-tw)

如果你的網站是線上或當地商家，建議使用 `OnlineStore` 或 `LocalBusiness` 之一，或 `Organization` 的子類型。

我們仍建議為個別產品新增運送政策，以覆寫機構層級的運送政策，或在沒有適用於大多數產品的通用運送政策時使用。如果已指定產品層級運送政策，可以繼續使用，並視需要新增機構層級運送政策。

透過上述任一方法提供運送和退貨資訊後，你的出貨政策可能會出現在更多搜尋結果中，包括[知識面板](https://support.google.com/knowledgepanel/answer/9163198?hl=zh-tw)、[品牌檔案](https://support.google.com/merchants/answer/14998338?hl=zh-tw)和產品搜尋結果。有助於提升曝光度、展示免運費和快速出貨等出貨服務，最終吸引更多消費者。

希望這些新選項能協助所有商家輕鬆展示運送政策，並改善在搜尋結果中的呈現方式。如有任何問題或疑慮，歡迎透過 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)與我們聯絡。

發文者：Google 購物軟體工程師 [Pascal Fleury](https://developers.google.com/search/blog/authors/pascal-fleury?hl=zh-tw) 和 [Irina Tuduce](https://developers.google.com/search/blog/authors/irina-tuduce?hl=zh-tw)，以及產品經理 Jay Rana
