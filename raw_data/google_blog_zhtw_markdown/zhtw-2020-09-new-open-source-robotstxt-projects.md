# 新的開放原始碼 robots.txt 專案透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2020-09-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/09/new-open-source-robotstxt-projects?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 9 月 21 日，星期一

我們在去年向開放原始碼社群公開了自家生產系統中使用的 [robots.txt 剖析器和比對工具](https://github.com/google/robotstxt)。在那之後，我們便看到大家開始利用這些資源打造新工具、向開放原始碼程式庫[貢獻內容](https://github.com/google/robotstxt/pulls?q=is%3Apr+is%3Amerged) (這有效改善了我們的生產系統，我們對此深表謝意) 以及 [golang](https://github.com/google/robotstxt/issues/29)、[rust](https://github.com/google/robotstxt/issues/31) 等方便開發人員建構新工具的新版語言。

隨著 Google 的實習季即將結束，我們想特別介紹由 Google 搜尋開放原始碼團隊的兩名實習生 [Andreea Dutulescu](https://www.linkedin.com/in/andreea-nicoleta-dutulescu) 和 [Ian Dolzhanskii](https://www.linkedin.com/in/ian-dolzhanskiy-6297a119b/) 所開發的兩項與 robots.txt 相關的新功能。

## robots.txt 規格測試

首先，我們將推出 Andreea 為 robots.txt 剖析器開發人員建立的[測試架構](https://github.com/google/robotstxt-spec-test/)。該專案提供的測試工具可以驗證 robots.txt 剖析器是否遵循漫遊器排除通訊協定，或是遵循漫遊器排除通訊協定的程度。由於目前還沒有一種能夠全面評估解析器正確性的正式方法，因此開發人員可以利用 Andreea 建構的這項工具來建立遵循通訊協定的 robots.txt 解析器。

## Java robots.txt 剖析器和比對工具

其次，我們將推出 Ian 針對 [C++ robots.txt 剖析器建立的正式 Java 語言埠](https://github.com/google/robotstxt-java)。Java 是 GitHub 上[第 3 大熱門的程式語言](https://madnight.github.io/githut/#/pull_requests/2020/2)，而且同樣受到 Google 廣泛使用，因此 Java 語言埠無疑是最多人想使用的語言埠。這個解析器是 CSS 剖析器在函式和行為方面的直接翻譯，已通過大量 robots.txt 規則的奇偶測試。目前相關團隊已計劃在 Google 生產系統中使用 Java robots.txt 剖析器，我們希望您也能從中受益。

一如既往，我們歡迎您為這些專案做出貢獻。如果您利用 [C++ robots.txt 剖析器](https://github.com/google/robotstxt)或這些新功能製作了新東西，請告訴我們，我們也許能幫您推廣。發現錯誤時，您可以在 GitHub 上提出問題，也可以直接發出提取要求，協助我們進行修正。如果您對這些專案有任何疑問或意見，歡迎透過 [Twitter](https://twitter.com/googlesearchc) 反映給我們！

非常榮幸 Andreea 和 Ian 能夠加入我們，也很遺憾他們的實習即將結束。他們的貢獻有助於打造更好的網際網路環境，希望將來能歡迎他們回到 Google 發光發熱。

發文者：Google 搜尋開放原始碼團隊的 [Edu Pereda](https://twitter.com/epere4) 和 [Gary Illyes](https://garyillyes.com/+)
