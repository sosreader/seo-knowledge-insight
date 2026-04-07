# 春季大掃除：網址參數工具透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2022-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/03/url-parameters-tool-deprecated?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 3 月 28 日，星期一

**簡單來說：**我們將於 1 個月後淘汰 Search Console 中的網址參數工具。目前使用這項工具的使用者無需採取任何行動。

![網址參數工具推出時的螢幕截圖](https://developers.google.com/static/search/blog/images/oldurlparam.png?hl=zh-tw)

2009 年的網址參數工具

[2009](https://developers.google.com/search/blog/2009/10/new-parameter-handling-tool-helps-with?hl=zh-tw) 年，Search Console 的前身「網站管理員工具」中推出網址參數工具時，網際網路環境比現在更不受規範。`SessionID` 參數很常見，CMS 難以整理參數，而瀏覽器則經常使連結損壞。網站擁有者可運用網址參數工具，指定特定參數影響自家網站內容的方式，更精細地控管 Google 檢索網站的方式。

經過多年開發，Google 越來越能準確預測哪些參數對網站有用，哪些沒用。事實上，網址參數工具中目前指定的參數設定中大約只有 1% 對於檢索有用處。由於這項工具對於 Google 和 Search Console 使用者價值都不高，我們將於 1 個月後淘汰網址參數工具。

今後您不需要在網站上指定網址參數函式，Google 檢索器會自動學習如何處理網址參數。

如果您要進一步控管設定，可以使用 [robots.txt 規則](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=zh-tw) (舉例來說，您可以在 `allow` 規則中指定參數順序) 或使用 [`hreflang`](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=zh-tw) 指定內容的各種語言版本。

如果您有問題或意見，可以透過 [Twitter](https://twitter.com/googlesearchc) 與我們聯絡。

發文者：搜尋團隊 [Gary Illyes](https://garyillyes.com/+)
