# x-default 如何提供協助
- **發佈日期**: 2023-05-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/05/x-default?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2013 年 5 月 8 日 星期一

最近有許多問題使我們發現，有些網站已使用 `hreflang` 協助搜尋使用者找到正確的網頁版本，但這些網站可能未充分利用 `hreflang x-default` 值。提醒您，這是一款十分強大的工具，能做到的事情可能超乎您想像。

當網站不支援使用者語言和區域時，可使用 `hreflang x-default` 值，針對部分內容指定不限語言和區域的網址。這個值可與其他 `hreflang` 值搭配使用，如果是以特定語言和區域為目標的內容，可透過後者指定網址版本。

舉例來說，如果網頁有英文和西班牙文版本的 `hreflang` 註解，以及指向英文版本的 `x-default` 值，由於有 `x-default` 註解，系統會將法文使用者導向英文版頁面。`x-default` 網頁可以是語言和國家/地區選取器頁面、當使用者所在地區沒有對應內容時，系統將他們重新導向的目標頁面，或者是您認為可做為預設版本的頁面。當然，您可能無法提供所有網頁的本地化版本，這沒關係，您可以只在網站的某些部分加入 `hreflang` 註解，不會有任何問題。

那麼，`x-default` 如何協助網站擁有者？您已經瞭解它如何協助 Google，為相應使用者提供適合的網頁，但還有其他更多功能！

## 1. 網址搜尋

雖然在此不會多加說明，但您在 `hreflang` 註解 (包括 `x-default`) 中指定的網址，可能會用於搜尋網址。舉例來說，這對於結構複雜的大型網站十分實用，因為這類網站很難確認網站上每個本地化的網址都已正確連結。

從實務上來看，這代表系統會擷取以下示例中的 `href` 屬性，並可能安排檢索作業：

```
<link rel="alternate" href="https://example.com/en-us" hreflang="en-us" />
<link rel="alternate" href="https://example.com/country-selector" hreflang="x-default" />
```

## 2. 轉換

您的目標很有可能是在某種程度上轉換到達您網頁的使用者。[Ryte 將轉換解釋為](https://ryte.com/wiki/Conversion)「由公司事先定義為目標的指定動作所產生的結果」。舉例來說，如果使用者到達您的網頁，查看關於「[咆哮山莊](https://en.wikipedia.org/wiki/Wuthering_Heights)」的論文，您可能會將轉換計為使用者已閱讀大部分論文內容。當然，轉換的形式有很多種；畢竟目標是由您自行定義。

不過，如果您只想以德文發布論文，則非德文講者就不太可能在該網頁上進行轉換，因此建議您將他們將傳送到其他頁面，讓他們可以用其他方式轉換。您可以使用 `hreflang="x-default"` 進行表達，如下所示：

```
<link rel="alternate" href="https://example.com/de/stürmische-höhen" hreflang="de" />
<link rel="alternate" href="https://example.com/lang-selector" hreflang="x-default" />
```

如要進一步瞭解 `hreflang`，請[查看我們的說明文件](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=zh-tw)，其中也會詳細說明 `x-default` 的相關內容。如果您想與我們討論 `hreflang`，歡迎前往 [Google 搜尋中心論壇](https://support.google.com/webmasters/community?hl=zh-tw)和 [Twitter](https://twitter.com/googlesearchc) 與我們交流。

發文者：[Gary Illyes](https://developers.google.com/search/blog/authors/gary-illyes?hl=zh-tw)
