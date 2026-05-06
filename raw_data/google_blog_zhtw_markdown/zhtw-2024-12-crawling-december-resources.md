# 檢索 12 月：Googlebot 檢索的運作方式和原因
- **發佈日期**: 2024-12-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2024/12/crawling-december-resources?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2024 年 12 月 3 日，星期二

您可能知道 Google 搜尋需要一些前製作業，才能讓網頁顯示在 Google 搜尋結果中。其中一個步驟就是「檢索」。Googlebot 負責處理 Google 搜尋的檢索作業，這個程式在 Google 伺服器上運作，會擷取網址、處理網路錯誤、重新導向和其他可能在檢索過程中遇到的網路問題。其中還有許多細節，但通常都不會提到。在這個月，我們每週都會探討其中一些細節，因為這些細節可能會對網站檢索方式產生重大影響。

## 快速回顧：什麼是檢索？

[檢索](https://developers.google.com/search/docs/fundamentals/how-search-works?hl=zh-tw#crawling)是指發現新網頁、重新造訪更新的網頁，並下載這些網頁的程序。簡而言之，Googlebot 會取得網址，向代管該網址的伺服器傳送 HTTP 要求，然後處理該伺服器的回應，可能會重新導向、處理錯誤，並將網頁內容傳遞至 Google 索引系統。

不過，現代網頁並非只有純 HTML，如果網頁包含其他資源怎麼辦？檢索這些資源會對「檢索預算」造成什麼影響？這些資源能否在 Google 端快取？尚未檢索的網址與已建立索引的網址之間有差異嗎？本文將回答這些問題，並提供更多相關資訊！

## Googlebot 和檢索網頁資源

除了 HTML 之外，現代網站還會結合使用 JavaScript 和 CSS 等不同技術，為使用者提供優異體驗和實用功能。透過瀏覽器存取這類網頁時，瀏覽器會先下載父層網址，這個網址會代管開始為使用者建構網頁所需的資料，也就是網頁的 HTML。這類初始資料可能包含 JavaScript 和 CSS 等資源的參照網址，也包含瀏覽器會再次下載的圖片和影片，最後建構出最終網頁並呈現給使用者。

[Google 也會執行相同程序](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics?hl=zh-tw)，但做法略有不同：

1. Googlebot 從父層網址 (網頁的 HTML) 下載初始資料。
2. Googlebot 將擷取的資料傳送至網路轉譯服務 (WRS)。
3. WRS 透過 Googlebot 下載原始資料中參照的資源。
4. WRS 採用與使用者瀏覽器一樣的方式，運用所有下載的資源建構網頁。

與瀏覽器相比，由於排程限制 (例如伺服器解譯負載，伺服器會代管轉譯網頁所需的資源)，每個步驟之間的時間可能會大幅延長。這時就要提到[檢索預算](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=zh-tw#general_theory)了。

檢索轉譯網頁所需的資源，會耗用代管資源的主機名稱的檢索預算。為了改善這種情形，WRS 會嘗試快取轉譯網頁中參照的每個資源 (JavaScript 和 CSS)。WRS 快取的存留時間 (TTL) 不會受到 HTTP 快取指令的影響；相反地，WRS 會快取最多 30 天內的所有內容，這有助於保留網站的檢索預算，以便執行其他檢索工作。

從網站擁有者的角度來看，管理檢索的方式和資源可能會影響網站的檢索預算。建議您採取以下做法：

1. **盡可能減少資源使用量**，以便提供優質的使用者體驗；轉譯網頁所需的資源越少，轉換期間要使用的檢索預算就越少。
2. **謹慎使用快取清除參數**，只要資源的網址有變更，Google 就可能需要重新檢索這些資源，即使內容沒變也一樣。這樣勢必會耗用檢索預算。
3. **將資源代管在主網站以外的主機名稱上**，例如採用 CDN 或在其他子網域上代管資源。這會將檢索預算問題轉移至提供資源的主機。**2024 年 12 月 6 日更新：**由於連線至不同主機名稱會產生額外負擔，導致網頁效能變慢，因此[不建議將這項策略用於呈現網頁所需的關鍵性的資源](https://web.dev/articles/optimize-lcp?hl=zh-tw#different-origin) (例如 JavaScript 或 CSS)。不過，對於較大型的非關鍵性的資源 (例如影片或下載內容)，建議採用這種做法。

這些要點也適用於媒體資源。如果 Googlebot (或更具體地說，分別為 `Googlebot-Image` 和 `Googlebot-Video`) 擷取這些資源，就會耗用網站的檢索預算。

您可能會想將 [robots.txt](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=zh-tw) 也加入清單，但從轉譯角度來看，禁止檢索資源通常會導致問題。如果 WRS 無法擷取轉譯關鍵資源，Google 搜尋可能就無法擷取網頁內容，也無法讓網頁在 Google 搜尋中排名。

## Googlebot 會檢索哪些內容？

要分析 Google 檢索了哪些資源，最好的來源是網站的原始存取記錄，其中包含瀏覽器和檢索器要求的每個網址項目。如要瞭解如何在存取記錄中識別 Google 檢索器，請參閱[開發人員說明文件](https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers?hl=zh-tw)中的 IP 範圍。

當然，第二個最佳資源是 [Search Console 檢索統計資料報告](https://support.google.com/webmasters/answer/9679690?hl=zh-tw)，這份報告會依檢索器列出各種類型的資源：

![Search Console 中的「檢索統計資料」報告，顯示 Googlebot 檢索的不同類型資源](https://developers.google.com/static/search/blog/images/crawling-december-sc-crawl-report.png?hl=zh-tw)

最後，如果您對檢索和轉譯有興趣，並想與其他人討論相關主題，歡迎加入[搜尋中心社群](https://goo.gle/sc-forum)，您也可以在 [LinkedIn](https://www.linkedin.com/showcase/googlesearchcentral/) 上找到我們。

發文者：[Martin Splitt](https://developers.google.com/search/blog/authors/martin-splitt?hl=zh-tw) 和 [Gary Illyes](https://developers.google.com/search/blog/authors/gary-illyes?hl=zh-tw)

---

## 更新

* **2024 年 12 月 6 日更新**：註明透過不同來源提供資源會對成效造成影響。

---

## 想進一步瞭解檢索嗎？請觀看完整的「檢索 12 月」系列影片：
