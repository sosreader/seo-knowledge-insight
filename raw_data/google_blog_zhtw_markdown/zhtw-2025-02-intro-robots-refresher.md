# 重溫漫遊器：介紹新系列
- **發佈日期**: 2025-02-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2025/02/intro-robots-refresher?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2025年 2 月 24 日，星期一

我們不時會收到使用者的疑問，詢問有關 robots.txt、漫遊器中繼標記，以及這些標記提供的控制功能。繼 [12 月關於檢索的系列文章](https://developers.google.com/search/blog?hl=zh-tw#crawlingdecember)之後，我們認為現在是時候來個輕鬆的複習了。因此，如果您對這些控制項感到好奇，歡迎繼續閱讀這一系列新的網誌文章！

讓我們從最一開始的 robots.txt 開始談起。

## 什麼是 robots.txt？

「[robots.txt](https://en.wikipedia.org/wiki/Robots.txt)」是任何網站都能提供的檔案。最簡單的說法是，這是儲存在伺服器上的文字檔案。[幾乎所有網站都有 robots.txt 檔案](https://almanac.httparchive.org/en/2024/seo#robotstxt)。如要查看該檔案，請在網域名稱結尾加上 `/robots.txt`，然後瀏覽該地址。舉例來說，這個網站的 robots.txt 檔案位於 `developers.google.com/robots.txt`。

大多數網站都會使用內容管理系統 (CMS) 自動建立這些檔案，但即使您是「手動」製作網站，也能輕鬆建立這些檔案。我們會在日後的文章中介紹一些變化版本。

## 這些檔案的用途為何？

robots.txt 檔案會告訴網站檢索器，網站的哪些部分可供自動存取 (我們稱為檢索)，哪些部分則不行。這項功能可讓網站處理整個網站、網站的部分內容，甚至是網站中的特定檔案。除了機器可讀之外，這些檔案也屬於人類可讀。也就是說，關於是否允許特定檢索器以自動化方式存取網頁，總是有簡單明瞭的「是」或「否」的答案。

對於任何要建構檢索器的人來說，遵循這些指令都是標準做法，開發人員也能輕鬆支援這些指令。開發人員可以使用的[開放原始碼程式庫數量超過 1000 個](https://github.com/search?q=robots.txt&type=repositories)。這個檔案會向檢索器提供指示，以便為網站執行最理想的檢索作業。現代網站有時相當複雜，要自動瀏覽這些網站可能很難，而 robots.txt 規則可協助檢索器專注於適當的內容。這也有助於檢索器避開動態建立的網頁，因為這類網頁可能會對伺服器造成負擔，並使檢索效率不必要地降低。由於 robots.txt 檔案在技術上很實用，而且有助於與網站擁有者建立關係，因此大多數商業檢索器營運者都會遵循。

## 由公眾建構及擴充

robots.txt 檔案幾乎與網際網路同時出現，是讓網際網路正常運作的必要工具之一。HTML 是網頁的基礎，於 1991 年發明，第一個瀏覽器則在 1992 年問世，而 robots.txt 則在 1994 年誕生。也就是說，這種檔案比 1998 年創立的 Google 更早出現。自此之後，格式幾乎沒有變動，[早期檔案](https://web.archive.org/web/19990123235553/http://nexor.com/robots.txt)現在仍可正常使用。經過三年的全球社群參與，這項技術在 2022 年成為 [IETF 提案標準](https://datatracker.ietf.org/doc/rfc9309/)。

如果您有網站，很可能也有 robots.txt 檔案。圍繞 robots.txt 的社群十分活躍，有數千種軟體工具可協助建立、測試、管理或瞭解各種形狀和大小的 robots.txt 檔案。然而，robots.txt 的優點是不需要使用複雜的工具，只要在瀏覽器中讀取檔案即可，如果是您管理的網站，則可使用簡單的文字編輯器進行調整。

## 未來展望…

robots.txt 的格式相當彈性，具有成長空間，公共網路社群可對其進行擴展，而檢索器也可以在適當情況下宣告擴充功能，不會影響現有的使用方式。2007 年發生過這樣的情形，當時[搜尋引擎推出了「sitemap」](https://searchengineland.com/search-engines-unite-on-sitemaps-autodiscovery-10952)指令。這種情況也經常發生於檢索器營運者和搜尋引擎支援新的「使用者代理程式」時 (例如用於 AI 用途的使用者代理程式)。

robots.txt 會繼續存在。新檔案格式需要幾年的時間才能在更廣大的網際網路社群中定案，而開發適當的工具，讓這些格式在生態系統中發揮作用，所需時間更長。這項技術簡單、精細、富表現力，廣受使用者接受與認同，而且運作方式和過去數十年來一樣。

想進一步瞭解相關細節嗎？敬請密切留意「搜尋中心」網誌上「重溫漫遊器」(Robots Refresher) 系列文章！

發文者：Google Zurich 搜尋關係團隊 [John Mueller](https://developers.google.com/search/blog/authors/john-mueller?hl=zh-tw)

---

## 請參閱「重溫漫遊器」系列的其他影片：
