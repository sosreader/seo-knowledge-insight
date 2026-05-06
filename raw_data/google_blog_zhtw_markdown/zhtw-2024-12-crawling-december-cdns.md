# 檢索 12 月：CDN 和檢索
- **發佈日期**: 2024-12-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2024/12/crawling-december-cdns?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2024 年 12 月 24 日，星期二

內容傳遞網路 (CDN) 特別適合用來降低網站的延遲時間，一般來說可避免網站流量相關的麻煩。畢竟，這就是他們的主要用途：即使網站流量很高，也能快速傳送內容。CDN 中的「"D"」是指全球內容傳遞或發布，因此將資料傳輸給使用者的時間，會比單純在某個資料中心代管內容的情況要短。在本文中，我們將探討如何使用 CDN 改善網站的檢索和使用者體驗，並進一步說明檢索 CDN 支援網站時的幾項細微差異。

## 重點回顧：什麼是 CDN？

CDN 基本上是原始伺服器 (網站所在位置) 和使用者之間的中介，會為他們提供 (部分) 檔案。從歷史角度來看，**CDN 最重視的功能就是快取**，也就是說，一旦使用者要求您網站上的網址，CDN 就會將該網址的內容儲存在快取中一段時間，這段時間內您的伺服器就不必重覆提供該檔案。

**CDN 可從使用者附近的位置提供內容，大幅提升網站速度**。舉例來說，如果澳洲使用者存取德國託管的網站，CDN 會從澳洲的快取檔案為該使用者提供服務，減少全球的往返傳輸時間。無論是否以光速傳輸，[距離還是相當遙遠](https://www.youtube.com/watch?v=gYqF6-h9Cvg&hl=zh-tw)。

最後，**CDN 是保護網站免受超載和某些安全威脅的絕佳工具**。CDN 可根據其管理的全球流量建立可靠的流量模型，以便偵測流量異常，並封鎖看似過度或惡意的存取行為。舉例來說，2024 年 10 月 21 日，[Cloudflare 系統](https://blog.cloudflare.com/ddos-threat-report-for-2024-q3/)自動偵測並緩解了持續約一分鐘的 4.2 [Tbps](https://wikipedia.org/wiki/Data-rate_units#Terabit_per_second) *(註：這是非常大的數字)* DDoS 攻擊。

## CDN 對網站的幫助

您可能擁有市面上能買到的最快伺服器和最佳上行鏈結，因此可能認為沒必要加速，但 CDN 在長期而言可為您省錢，尤其是如果您的網站規模龐大：

* **CDN 快取**：如果媒體、JavaScript 和 CSS 等資源，甚至是 HTML 都是從 CDN 快取中提供，您的伺服器就不需要花費運算和頻寬來提供這些資源，進而減少伺服器負載。這通常也表示網頁在使用者的瀏覽器中載入速度更快，[進而提高轉換率](https://www.thinkwithgoogle.com/_qs/documents/9757/Milliseconds_Make_Millions_report_hQYAbZJ.pdf)。
* **流量洪流保護**：CDN 特別擅長識別及封鎖過多或惡意流量，即使有惡意漫遊器或不肖人士意圖使伺服器超載，使用者仍可造訪您的網站。
  除了防洪功能之外，這些用於封鎖不良流量的控制項，也可用於封鎖不想要的流量，例如特定的檢索器、符合特定模式的用戶端，或是持續使用相同 IP 位址的網路小白。雖然您也可以在伺服器或防火牆上執行這項操作，但使用 CDN 的使用者介面通常會更簡單。
* **可靠性**：即使網站發生異常，某些 CDN 仍可為使用者提供網站內容。當然，這可能只適用於靜態內容，但這可能就足以確保他們不會轉向其他地方尋求服務。

簡而言之，CDN 是您的好幫手。如果您的網站規模龐大，或是預期會有 (甚至已經收到) 大量流量，建議您根據價格、效能、可靠性、安全性、客戶支援、擴充性和未來擴展需求等因素，找出最符合需求的 CDN。請洽詢您的代管服務或 CMS 供應商，瞭解可用的選項 (或是您是否已使用其中一種)。

## 檢索對使用 CDN 的網站有何影響

在檢索方面，CDN 也能提供協助，但可能會導致一些檢索問題 (雖然很少見)。以下會詳細說明。

### CDN 對檢索頻率的影響

我們的檢索基礎架構可讓 CDN 支援的網站提高檢索頻率，這項資訊是根據提供檢索器存取網址的服務 IP 位址推斷而來。這麼做通常都能獲得不錯的效果，至少在大多數情況下是如此。

假設您今天開始經營圖庫相片網站，而且剛好有 1,000,007 張圖庫相片。您會為所有內容建立到達網頁、類別頁面和詳細資料頁面，因此網站上會出現許多網頁。我們在[檢索容量限制](https://developers.google.com/crawling/docs/crawl-budget?hl=zh-tw#crawl-capacity-limit)的說明文件中說明，雖然 Google 搜尋會嘗試盡可能快速檢索這些網頁，但檢索也不應造成伺服器過載。如果伺服器在面臨大量檢索要求時開始回應緩慢，Google 會施行節流，避免伺服器超載。如果檢索基礎架構偵測到你的網站有 CDN 支援，就會假設你的伺服器可以處理更多同時要求，因此將啟動節流的閾值提高，進而加快檢索線上商店的速度。

不過，在首次存取網址時，CDN 的快取是「冷的」，也就是說，由於尚未有人要求該網址，因此 CDN 尚未快取該網址的內容，因此原始伺服器仍需至少提供一次該網址，才能為 CDN 的快取「暖機」。這與 [HTTP 快取的運作方式](https://developers.google.com/search/blog/2024/12/crawling-december-caching?hl=zh-tw)非常相似。

簡而言之，即使您的線上商店有 CDN 支援，伺服器仍須至少提供一次這 1,000,007 個網址。完成初始服務後，CDN 才能協助您處理快取。這會對「檢索預算」造成重大負擔，且幾天內的檢索頻率可能會偏高；因此，如果您打算一次發布多個網址，請務必留意這一點。

### CDN 對算繪的影響

如同我們在第一篇[關於資源檢索的「檢索 12 月」網誌文章](https://developers.google.com/search/blog/2024/12/crawling-december-resources?hl=zh-tw)中所述，將資源分割為各自的主機名稱或 CDN 主機名稱 (`cdn.example.com`)，或許能讓我們的網頁算繪服務 (WRS) 更有效率地算繪網頁。不過，這項做法有一個缺點：由於連線至不同主機名稱會產生額外負擔，導致網頁效能變慢，因此您需要仔細考量[網頁體驗](https://developers.google.com/search/docs/appearance/page-experience?hl=zh-tw)與算繪效能。

如果您使用 CDN 備份主機，就能避免這個問題：只需查詢一個主機名稱，且重要的算繪資源可能會從 CDN 快取提供，您的伺服器就不必提供這些資源 (且不會影響網頁體驗)。

最後，請選擇最適合貴商家的解決方案：為靜態資源使用不同的主機名稱 (`cdn.example.com`)、使用 CDN 備份主要主機名稱，或同時採用這兩種做法。Google 的檢索基礎架構可支援這兩種方式，不會有任何問題。

## CDN 過度保護

由於 CDN 的洪流防護機制和檢索器的檢索方式，有時系統可能會將您網站上需要的漫遊器列入 CDN 的封鎖清單，通常是在網頁應用程式防火牆 (WAF) 中。這會導致檢索器無法存取您的網站，最終可能導致您的網站無法顯示在搜尋結果中。封鎖可能發生在多種情況下，其中有些情況會對網站在 Google 搜尋結果中的呈現方式造成更嚴重的影響，而且由於封鎖發生在 CDN 端，因此您可能很難 (或根本無法) 控制。為了方便說明，我們將這些區塊分為兩個類別：硬式封鎖和軟式封鎖。

### 硬式封鎖

硬式封鎖是指 CDN 以某種形式傳送回應給檢索要求，表示發生錯誤。可能的形式包括：

* **HTTP `503`/`429` 狀態碼**：傳送[這些狀態碼](https://developers.google.com/crawling/docs/troubleshooting/http-status-codes?hl=zh-tw#5xx-server-errors)是發出暫時封鎖信號的首選方式。這樣一來，您就能有時間因應 CDN 意外封鎖的情況。
* **網路逾時**：CDN 的網路逾時會導致受影響的網址從 Google 搜尋索引中移除，因為這些[網路錯誤屬於終端「硬式」錯誤](https://developers.google.com/crawling/docs/troubleshooting/dns-network-errors?hl=zh-tw)。此外，這些項目還可能會大幅影響網站的檢索頻率，因為這會向我們的檢索基礎架構傳達網站超載的訊息。
* **隨機錯誤訊息，並附上 HTTP `200` 狀態碼**：也稱為[軟式錯誤](https://developers.google.com/search/docs/crawling-indexing/troubleshoot-crawling-errors?hl=zh-tw#soft-404-errors)，這類錯誤特別嚴重。如果 Google 認為錯誤訊息屬於「硬式」錯誤 (例如 HTTP `500`)，就會從 Google 搜尋中移除該網址。如果 Google 無法將錯誤訊息偵測為「硬式」錯誤，則所有顯示相同錯誤訊息的網頁都可能會從 Google 搜尋索引中移除，視為重複內容。由於 Google 索引系統沒有動力要求重新檢索重複的網址，因此要解決這個問題可能需要更多時間。

### 軟式封鎖

當 CDN 顯示「你確定你是人類嗎」插頁時，可能會出現類似的問題 (很明顯是故意)。

![Crawley 對被稱為人類感到困惑](https://developers.google.com/static/search/blog/images/crawling-december-crawley-confused.png?hl=zh-tw)

我們的檢索器其實相信自己不是人類，也不會假裝成人類。檢索器只想進行檢索。不過，當插頁顯示時，檢索器只會看到插頁，而非您精彩的網站。針對這些機器人驗證插頁，我們強烈建議您以 503 HTTP 狀態碼的形式，向檢索器等自動化用戶端傳送明確的信號，表示內容暫時無法使用。這樣一來，系統就不會自動將內容從 Google 索引中移除。

### 偵錯封鎖

如果同時出現硬式和軟式封鎖，最簡單的檢查方法就是使用 [Search Console 中的網址檢查工具](https://support.google.com/webmasters/answer/9012289?hl=zh-tw)，並觀察算繪圖片：如果能顯示您的網頁，表示一切正常；如果顯示空白網頁、錯誤或有機器人驗證的網頁，建議您與 CDN 相關單位聯絡。

此外，為了協助解決這些非預期的封鎖問題，Google、其他搜尋引擎和其他檢索器營運者會發布[我們的 IP 位址](https://developers.google.com/search/docs/crawling-indexing/verifying-googlebot?hl=zh-tw)，協助您辨識我們的檢索器，並在您認為適當的情況下，從 WAF 規則中移除封鎖的 IP 位址，甚至將這些 IP 位址加入許可清單。這項操作的位置取決於您使用的 CDN；幸運的是，大多數 CDN 和獨立的 WAF 都有非常實用的說明文件。以下是我們在稍微搜尋後找到的幾個例子 (截至本篇文章發布時)：

* Cloudflare：<https://developers.cloudflare.com/bots/get-started/free/#visibility>
* Akamai：<https://www.akamai.com/products/bot-manager>
* Fastly：<https://www.fastly.com/products/bot-management>
* F5：<https://clouddocs.f5.com/bigip-next/20-2-0/waf_management/waf_bot_protection.html>
* Google Cloud：[https://cloud.google.com/armor/docs/bot-management](https://cloud.google.com/armor/docs/bot-management?hl=zh-tw)

如果您希望網站顯示在搜尋引擎中，強烈建議您檢查所需的檢索器是否能存取您的網站。請注意，IP 可能會在你不知情的情況下自動加入封鎖清單，因此建議不時查看封鎖清單，確保網站在搜尋和其他方面獲得成功。如果封鎖清單很長 (就像這篇網誌文章一樣)，請嘗試只查看 IP 範圍的前幾個區隔，例如，不要查看 `192.168.0.101`，只看 `192.168`。

這是[「檢索 12 月」系列網誌文章](https://developers.google.com/search/blog?hl=zh-tw#crawling-december)的最後一篇文章，希望您喜歡這些文章，就像我們喜歡撰寫這些文章一樣。如果您有... 等等... 您知道該怎麼做了。

發文者：[Martin Splitt](https://developers.google.com/search/blog/authors/martin-splitt?hl=zh-tw) 和 [Gary Illyes](https://developers.google.com/search/blog/authors/gary-illyes?hl=zh-tw)

---

## 想進一步瞭解檢索嗎？請觀看完整的「檢索 12 月」系列影片：
