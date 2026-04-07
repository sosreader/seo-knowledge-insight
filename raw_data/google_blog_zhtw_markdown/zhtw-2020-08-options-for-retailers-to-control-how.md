# 零售商能夠過更多選項掌控已檢索產品資訊在 Google 上的呈現方式
- **發佈日期**: 2020-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/08/options-for-retailers-to-control-how?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 8 月 21 日，星期五

今年稍早，Google 推出了方便購物者[在搜尋服務中尋找服飾、鞋款和其他零售產品](https://www.blog.google/products/search/new-way-find-clothes-shoes-and-more-search/?hl=zh-tw)的全新體驗，並於近期宣布即將在 [Google 搜尋的產品知識面板中顯示零售資訊](https://blog.google/products/shopping/bringing-free-retail-listings-google-search/?hl=zh-tw)。除了 Google 搜尋帶來的全新體驗外，零售商還能藉由通行全球的產品[複合式搜尋結果](https://developers.google.com/search/docs/appearance/structured-data/product?hl=zh-tw)，向數百萬名 Google 使用者展示自己的產品資訊。

如果零售商和品牌想利用這項體驗，最佳做法就是使用 schema.org 標記在自家網站上註解產品資訊，或直接在 [Google Merchant Center](https://www.google.com/retail/get-started/?hl=zh-tw) 提交這項資訊。零售商可以參閱我們的說明文件，進一步瞭解如何[利用「Google 跨平台顯示」計畫展示產品](https://support.google.com/merchants/answer/9199328?hl=zh-tw)，或是[在網站中新增 schema.org 標記](https://developers.google.com/search/docs/appearance/structured-data/product?hl=zh-tw)。

雖然上述流程最能確保產品資訊出現在搜尋體驗中，但是 Google 也可能在搜尋體驗中納入自身檢索到的零售相關內容，即使該內容並不是以 schema.org 標記標出，也不是透過 Marchant Center 所提供亦然。這麼做是為了確保使用者在 Google 搜尋資訊時，能看到大量零售商提供的各種產品。

我們相信這種做法可為零售生態系統帶來正面效益，但也知道有些零售商會想掌控自身產品資訊在這項體驗中的呈現方式。零售商可以利用 Google 搜尋的現有機制達成這個目的，詳情請見下文。

## 控制預覽偏好設定

零售商可以透過多種方式來控管在 Google 上顯示的資料。我們去年[宣布](https://developers.google.com/search/blog/2019/09/more-controls-on-search?hl=zh-tw)的異動就是在提供這些方式，讓網站擁有者和零售商能利用偏好設定，指定要在網站的 Google 搜尋結果中顯示哪些預覽資訊。為了達成這個目標，請使用一組 robots `meta` 標記和一個 HTML 屬性。

您可以透過以下方式[實施這些控制](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=zh-tw)，選擇要在 Google 顯示哪些產品和產品資料。

### `nosnippet` robots `meta` 標記

您可以利用這個 `meta` 標記，表明不希望搜尋結果顯示相應網頁的摘要。Google 會根據這個標記，從搜尋結果中完全移除相應網頁的文字、圖片和複合式摘要，該網頁也不會顯示在任何產品資訊功能中。

![採用和未採用 nosnippet 漫遊器中繼標記時分別產生的 Google 搜尋結果](https://developers.google.com/static/search/blog/images/import/89d64d3aa1cfd57b3f83626359f60d5a.png?hl=zh-tw)

### `max-snippet:[number]` robots `meta` 標記

您可以利用這個 `meta` 標記指定 Google 搜尋結果要針對您的網頁顯示的摘要字元長度上限。如果結構化資料 (例如產品名稱、說明、價格、供應情形) 的長度超過摘要長度上限，系統就不會在任何產品資訊功能中顯示該網頁。

![採用和未採用 max-snippet 漫遊器中繼標記時分別產生的 Google 搜尋結果](https://developers.google.com/static/search/blog/images/import/f8cb2a46d601cfc5d86f03ee30f55b62.png?hl=zh-tw)

### `max-image-preview:[setting]` robots `meta` 標記

您可以利用這個 `meta` 標記指定網頁圖片的預覽大小上限，可用的值有 `none`、`standard` 和 `large`。

![採用和未採用 max-image-preview 漫遊器中繼標記時分別產生的 Google 搜尋結果](https://developers.google.com/static/search/blog/images/import/c2196a84cb4d9246098b959d6e3c9d4b.png?hl=zh-tw)

### `data-nosnippet` HTML 屬性

您可以利用這項屬性，指定不要包含在 Google 搜尋結果預覽摘要中的網頁區段。如果應用於與商品 (價格、供應情形、評分、圖片) 相關的屬性，Google 就會移除相應網頁的文字、圖片和複合式摘要，並從自然產品資訊功能中移除相關產品資訊。

![採用和未採用 data-nosnippet 漫遊器中繼標記時分別產生的 Google 搜尋結果](https://developers.google.com/static/search/blog/images/import/92dcb3c74e54cabfe82c47f9e505c716.png?hl=zh-tw)

關於偏好設定的其他注意事項：

* 偏好設定不適用於透過網頁本身的 schema.org 標記提供的資訊。您需要先移除 schema.org 標記，這些停用機制才會生效。
* 停用偏好設定不適用於透過 Google Merchant Center 提交的產品資料。您可以透過 Google Merchant Center 提供的機制，[選擇停止讓 Google 跨平台顯示產品](https://support.google.com/merchants/answer/191180?hl=zh-tw)。

使用 `nosnippet` 和 `data-nosnippet` 等機制只會影響資料的顯示方式，以及資料是否適用特定體驗。顯示限制不會影響網頁在 Google 搜尋中的排名。若是選擇不顯示某些產品資料，可能會導致產品無法顯示在複合式搜尋結果和其他 Google 產品搜尋結果中。

我們希望這些做法可以協助您更輕鬆地從 Google 搜尋中獲得最大價值，進而達成業務目標。全世界的零售商都可以利用這些做法，在所有國家/地區提供一致的搜尋結果。如需更多資訊，請參閱[有關 `meta`記的開發人員說明文件](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=zh-tw)。

如有任何問題，您可以[與我們聯絡](https://developers.google.com/search/help?hl=zh-tw)或前往[說明論壇](https://support.google.com/webmasters/go/community?hl=zh-tw)提問。

發文者：產品經理 Bernhard Schindlholzer
