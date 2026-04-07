# Googlebot 即將支援 HTTP/2 檢索
- **發佈日期**: 2020-09-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/09/googlebot-will-soon-speak-http2?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 9 月 17 日，星期四

Googlebot 將從 2020 年 11 月開始透過 HTTP/2 檢索部分網站。

自從主流瀏覽器開始支援 HTTP 的下一個主要修訂版本 (即 [HTTP/2，簡稱 h2](https://en.wikipedia.org/wiki/HTTP/2))，網路專家就[向我們詢問過](https://support.google.com/webmasters/thread/3884161?hl=zh-tw) Googlebot 是否能透過升級後的新版通訊協定檢索內容。

現在我們在此宣布，Googlebot 將從 2020 年 11 月中開始支援透過 HTTP/2 檢索特定網站。

## 什麼是 HTTP/2

如前文所述，HTTP/2 是下一個 [HTTP 主要版本](https://tools.ietf.org/html/rfc7540)，HTTP 便是網際網路主要使用的資料傳輸通訊協定。HTTP/2 之所以比上一個版本更健全、迅速而有效率，原因在於採用了更加完善的架構，以及針對用戶端 (例如您的瀏覽器) 和伺服器實作的強大功能。如需更多資訊，請參閱我們以 [HTTP/2](https://developers.google.com/web/fundamentals/performance/http2?hl=zh-tw) 為題撰寫的長篇文章。

## 為何我們要做出這項調整

大體上，我們希望這項調整能讓系統在檢索時更有效率地使用伺服器資源。h2 可以讓 Googlebot 與伺服器之間只建立一個 TCP 連線，就能同步傳輸多個檔案，如此不需要多個連線也能享有同等效率；而且因為建立的連線越少，伺服器和 Googlebot 在檢索期間需要耗用的資源也就越省。

## 運作方式

在第一階段，我們會先透過 h2 檢索少量網站，然後判斷 h2 最初支援的功能 (例如要求多工作業) 可能對哪些網站有幫助，再逐漸將透過 h2 檢索的範圍擴大至這些網站。

在決定要透過 h2 檢索哪些網站時，Googlebot 會考量網站是否支援 h2，以及經由 h2 檢索是否能對網站和 Googlebot 有所助益。如果您的伺服器支援 h2，而且 Googlebot 已經在您的網站上檢索大量內容，那麼您或許已能使用升級連線，不必再採取任何行動。

即使您的伺服器仍然只支援 HTTP/1.1 也沒有關係，因為透過該通訊協定進行檢索並沒有明顯的缺點，檢索作業的品質和數量也將一如既往。

## 如何選擇不採用

儘管我們的初步測試顯示透過 HTTP/2 建立索引沒有任何問題或負面影響，但我們瞭解您可能基於各種原因而不希望自己的網站是透過 h2 進行檢索。如有這種需求，您可以指示伺服器在 Googlebot 嘗試透過 h2 檢索您的網站時傳回 [421 HTTP 狀態碼](https://tools.ietf.org/html/rfc7540#section-9.1.2)。如果您目前無法這麼做，也可以[傳送訊息告知 Googlebot 團隊](https://www.google.com/webmasters/tools/googlebot-report?hl=zh-tw)，但這只是暫時性的解決方案。

如果您對 Googlebot 和 HTTP/2 有其他疑問，請參閱以下[我們認為您可能詢問的問題](#questions)一節。如果該部分並未包含您的問題，歡迎透過 [Twitter](https://twitter.com/googlesearchc) 和[說明論壇](https://support.google.com/websearch/community?hl=zh-tw)向我們提問。

發文者：Jin Liang 和
[Gary Illyes](https://garyillyes.com/+)

## 我們認為您可能詢問的問題

### 為什麼現在要升級 Googlebot？

我們的軟體已經成熟到足以讓 Googlebot 透過 h2 進行檢索，因此能投入實際使用。

### 我需要盡快升級伺服器嗎？

您可以自行斟酌。不過，只有支援 h2 且明確可從中獲益的網站，我們才會改成以 h2 進行檢索。如果透過 h2 檢索對網站沒有明顯助益，Googlebot 就會繼續透過 h1 檢索網站。

### 如何測試我的網站是否支援 h2？

Cloudflare 有篇[Cloudflare](https://blog.cloudflare.com/tools-for-debugging-testing-and-using-http-2/)是關於如何測試網站是否支援 h2，當中提供了多種測試方法，建議您參考看看。

### 如何將我的網站升級至 h2？

具體做法因您的伺服器而異，建議洽詢您的伺服器管理員或代管服務供應商。

### 如何讓 Googlebot 透過 h2 檢索我的網站？

您無法指定讓 Googlebot 這麼做。雖然 Googlebot 可以透過 h2 檢索支援這項通訊協定的網站，但只有在網站和 Googlebot 都能受益的情況下才會這麼做。舉例來說，如果透過 h2 檢索網站對節省資源用量沒有明顯幫助，Googlebot 就可能繼續透過 HTTP/1.1 檢索網站。

### 為什麼 Google 不透過 h2 檢索所有支援 h2 的網站？

經過評估，我們發現透過 h2 進行檢索對於某些網站幾乎沒有幫助，比如 QPS 極低的網站便是如此。因此，我們決定只在對網站有明顯助益的情況下，才改成透過 h2 檢索網站。我們會繼續評估效能提升情況，將來可能會調整改用 h2 的標準。

### 如何得知我的網站是否經由 h2 檢索？

當在 Search Console 註冊的網站變成可以透過 h2 進行檢索時，網站擁有者就會在 Search Console 中收到日後可能有部分檢索流量是透過 h2 傳輸的訊息。您也可以查看伺服器記錄 (比如，如果您的網站是在 Apache 中執行，請查看 access.log 檔案)。

### Googlebot 支援哪些 h2 功能？

Googlebot 支援 h2 的大多數功能。我們仍在評估一些可能對轉譯作業有幫助的功能，比如伺服器推送。

### Googlebot 是否支援明文 HTTP/2 (h2c)？

否。您的網站必須使用 HTTPS 且支援 HTTP/2，才能透過 HTTP/2 進行檢索。新式瀏覽器的處理方式與此相同。

### Googlebot 會使用 ALPN 擴充功能來決定要使用哪個通訊協定版本進行檢索嗎？

應用層協定協商 (ALPN) 僅適用於接受經由 h2 檢索的網站，而且 h2 是唯一能收到回應的通訊協定。如果伺服器在傳輸層安全標準 (TLS) 握手期間做出回應，但連線使用的通訊協定版本不是 h2，Googlebot 就會停止檢索作業，改成透過 HTTP/1.1 進行檢索。

### 各項 h2 功能如何協助檢索作業？

h2 有很多優勢，最明顯的優勢如下：

* **多工與並行**：建立的 TCP 連線越少，代表耗用的資源越少。
* **標頭壓縮**：大幅縮減 HTTP 標頭的大小，可以節省資源。
* **伺服器推送**：這項功能尚未啟用，目前仍在評估階段。它可能對轉譯作業有幫助，但我們暫時無法下定論。

如要進一步瞭解特定 h2 功能，以及這些功能與檢索作業的關聯，請透過 [Twitter](https://twitter.com/googlesearchc) 向我們提問。

### h2 是否能讓 Googlebot 檢索更多內容或加速檢索作業？

h2 的主要優勢是能夠同時在伺服器端和 Googlebot 端節約資源。無論 Googlebot 是透過 h1 還是 h2 檢索網站，都不會影響網站索引的建立方式，因此這也不會影響 Googlebot 預計檢索網站的程度。

### 經由 h2 檢索的網站會有任何排名優勢嗎？

沒有。
