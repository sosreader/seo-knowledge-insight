# Search Console 規則運算式篩選器更新和使用小訣竅
- **發佈日期**: 2021-06-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/06/regex-negative-match?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 6 月 2 日星期三

不久前，我們宣布改進了 Search Console 成效報表的[資料篩選功能](https://developers.google.com/search/blog/2021/04/performance-report-data-filtering?hl=zh-tw)，很高興看到這項公告獲得不少[社群回響](https://twitter.com/googlesearchc/status/1379775388193320962)。

和往常一樣，我們這次也十分關注大家提供的意見。結果發現，很多人都希望規則運算式篩選器加入排除比對選項，讓這項功能更臻完善。

好消息是，從今天開始，**成效報表篩選器將同時支援比對吻合項目與排除吻合項目的規則運算式篩選器**。只要先在篩選器選取器中選取 [自訂 (規則運算式)] 選項，就可以在次要下拉式選單中看到相關選項，如以下螢幕截圖所示。進一步瞭解如何[篩選搜尋成效資料](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#filteringdata)。

![Search Console 成效報表規則運算式篩選器](https://developers.google.com/static/search/blog/images/negative-match-regex.png?hl=zh-tw "Search Console 成效報表規則運算式篩選器")

## 在 Search Console 中使用規則運算式的小訣竅

為了協助剛開始接觸規則運算式的使用者，我們也在這裡提供了一些實用的小訣竅。

首先，讓我們介紹一下規則運算式究竟是什麼。簡單來說，規則運算式是一種指定搜尋模式的字元序列，可以用來建立包含或排除不只單一字詞或詞組的進階篩選器。使用規則運算式時，您可以使用一些具有特殊涵義的中繼字元，例如定義搜尋條件的字元。如要查看 Search Console 支援的所有中繼字元，請參閱 [RE2 規則運算式語法參考資料](https://github.com/google/re2/blob/main/doc/syntax.txt)。

如果您想知道哪些情況應該使用規則運算式，而不是其他類型的篩選器，請參考下方列舉的一些使用情境：

* **區隔已經知道您品牌的使用者** - 使用規則運算式指定貴公司名稱的多個版本，包括有錯別字的版本。這樣一來，您就可以得知每個群組使用的查詢類型，以及每個目標對象分別是受到網站的哪些區塊吸引。舉例來說，如果貴公司名稱是 `Willow Tree`，建議您建立一個包含所有類似名稱的篩選器，例如：`willow tree|wilow tree|willowtree|willowtee` (`|` 中繼字元代表 OR 陳述式)。
* **分析網站特定區塊的流量** - 使用聚焦於網站上特定目錄的規則運算式，可協助您瞭解針對個別內容區塊的常見查詢。舉例來說，如果您的網址結構是 `example.com/[product]/[brand]/[size]/[color]`，當您想查看指向綠色鞋子的流量，但是對於品牌或尺寸沒有要求時，就可以使用 `shoes/.*/green` (`.*` 會比對任何字元，比對次數不限)。
* **瞭解使用者意圖** - 使用規則運算式分析哪些類型的查詢會將使用者導向網站上的不同區塊。
  舉例來說，您可能會關注含有疑問用語的查詢；而 `what|how|when|why` 查詢篩選器可能會傳回代表您的內容應能輕易解答問題的結果 (也許是常見問題集)。其他例子還有包含 (或不含) `buy|purchase|order` 之類交易用語的查詢。這些運算式也有助您瞭解使用者較常或較少使用哪些產品名稱。

歡迎前往 Search Console 說明中心查看[常見的規則運算式](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#regexp_glossary)。如果您對規則運算式有絕佳的應用方式，也歡迎在 Twitter 使用 `#performanceregex` 主題標記與大家分享。

如果您有任何問題或疑慮，歡迎前往 [Google 搜尋中心社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Asearch_console%29&hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 尋求協助。

發文者：搜尋服務代表 [Daniel Waisberg](https://www.danielwaisberg.com)
