# 重溫漫遊器：robots.txt  - 靈活控制機器人探索網站的方式
- **發佈日期**: 2025-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2025/03/robotstxt-flexible-way-to-control?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2025 年 3 月 7 日，星期五

長期以來，網站擁有者使用 robots.txt 超過 30 年，這種檔案受到檢索器營運者 (例如網站擁有者、服務和搜尋引擎的工具) 的廣泛支援。在本期[重溫漫遊器系列](https://developers.google.com/search/blog/2025/02/intro-robots-refresher?hl=zh-tw)中，我們將深入探討 robots.txt 如何靈活指示漫遊器在網站上要執行或不執行的動作。

## 開始使用 robots.txt

這些檔案的運作方式很簡單：建立名為「robots.txt」的文字檔，然後上傳到網站即可。如果您使用內容管理系統 (CMS)，操作方式可能更加簡單。如果要檢索整個網站，您可以讓 robots.txt 檔案保持空白 (或完全不上傳)，也可以新增規則來管理檢索作業。舉例來說，如果要指示所有漫遊器 (也稱為檢索器、自動尋檢程式) 不要檢索「加入購物車」頁面，可以在 robots.txt 檔案寫入以下內容：

```
user-agent: *
disallow: /cart
```

## 其他可透過 robots.txt 執行的特定操作

robots.txt 就像瑞士刀，可以控制不同漫遊器在網站上要執行或不執行的動作：檔案內容可以只有簡單幾行，也可以包含指定特定網址模式的複雜規則。您可以根據個人需求使用 robots.txt 檔案 (例如不想讓特定內容遭到檢索)，也可以用來解決技術問題 (例如[不必要的分頁網頁](https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading?hl=zh-tw#avoid-indexing-variations)) 或編輯內容。舉例來說，您可以：

|  |  |
| --- | --- |
| **將相同規則告知多個 (但非所有) 漫遊器**  這個群組會指示 `examplebot` 和 `otherbot` 遠離 `/search` 路徑。 | ``` user-agent: examplebot user-agent: otherbot disallow: /search ``` |
| **指示一個漫遊器避開包含特定文字的路徑**  舉例來說，您可以指示 `documentsbot` 不要檢索名稱中含有「.pdf」的任何檔案。 | ``` user-agent: documentsbot disallow: *.pdf ``` |
| **指示漫遊器可以檢索網誌，但不要檢索草稿** | ``` user-agent: documentsbot allow: /blog/ disallow: /blog/drafts/ ``` |
| **禁止檢索器檢索網站的部分內容，但允許其他檢索器存取網站**  這個 robots.txt 檔案會禁止上述 `aicorp-trainer-bot` 存取首頁以外的任何內容，同時允許其他檢索器 (例如搜尋引擎) 存取網站。 | ``` user-agent: * allow: /  user-agent: aicorp-trainer-bot disallow: / allow: /$ ``` |
| **留言給未來的自己**  您可以在一行開頭使用 `#`，提醒自己為何在該處設置特定規則。 | ``` # I don't want bots in my highschool photos user-agent: * disallow: /photos/highschool/ ``` |

詳情請參閱 [robots.txt 實用規則清單](https://developers.google.com/search/docs/crawling-indexing/robots/create-robots-txt?hl=zh-tw#useful-robots.txt-rules)。

## 實際修改 robots.txt 檔案

[漫遊器排除通訊協定 (REP)](https://datatracker.ietf.org/doc/rfc9309/) 會將規則 (「allow」或「disallow」) 放在一起，並指定這些規則適用於哪些漫遊器。您不需要學習程式設計或使用工具，只要將這些規則放在文字檔中，然後上傳到網站即可。

對大多數網站來說，這種做法更加簡單！如果您使用的是 CMS，其中通常會內建一些功能，可協助變更 robots.txt 檔案。舉例來說，有些 CMS 可讓您使用核取方塊或簡易表單自訂 robots.txt 檔案；大部分 CMS 都提供外掛程式，協助您設定及撰寫 robots.txt 檔案的規則。如要查看 CMS 提供的可用選項，請輸入以下搜尋字詞：CMS 名稱 + "編輯 robots.txt 檔案"。

設定完成後，您也可以進行測試，確認檔案設定符合預期。網路社群建立了許多測試工具來協助處理這個問題，例如 [TametheBot 的 robots.txt 測試工具](https://tamethebots.com/tools/robotstxt-checker)，以及這個 [robots.txt 剖析器](https://www.realrobotstxt.com/) (使用[開放原始碼 robots.txt 剖析器程式庫](https://github.com/google/robotstxt))。

如有任何 robots.txt 相關問題，歡迎前往 [LinkedIn](https://www.linkedin.com/showcase/googlesearchcentral/) 與我們交流，或是在[社群論壇](https://support.google.com/webmasters/community?hl=zh-tw)與志同道合的專家討論。

發文者：Google 搜尋關係團隊，[Martin Splitt](https://developers.google.com/search/blog/authors/martin-splitt?hl=zh-tw) 和 [John Mueller](https://developers.google.com/search/blog/authors/john-mueller?hl=zh-tw)

---

## 請參閱「重溫漫遊器」系列的其他影片：
