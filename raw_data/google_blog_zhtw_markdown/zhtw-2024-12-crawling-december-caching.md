# 檢索 12 月：HTTP 快取
- **發佈日期**: 2024-12-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2024/12/crawling-december-caching?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2024 年 12 月 9 日，星期一

請允許我們快取，麻煩您了。

多年來，隨著網際網路蓬勃發展，Google 檢索量也隨之增加。雖然 Google 的檢索基礎架構一直都支援啟發式快取機制，但可從本機快取傳回的要求數量逐漸減少：10 年前，總擷取次數中約有 0.026% 的內容可快取，雖然這數字並不高，但如今已降至 0.017%。

## 為什麼快取很重要？

網際網路就像一幅大型拼圖，而快取是其中非常重要的部分。快取功能可讓網頁在重新載入時快速載入，節省運算資源和自然資源，並為用戶端和伺服器省下大量昂貴的頻寬。

特別是如果你的網站規模龐大，且個別網址的內容很少變動，允許本機快取可能有助於提升檢索網站的效率。Google 的檢索基礎架構支援 [HTTP 快取標準](https://www.rfc-editor.org/rfc/rfc9111.html)定義的啟發式 HTTP 快取功能。具體來說，就是透過 `ETag` 回應和 `If-None-Match` 要求標頭，以及 `Last-Modified` 回應和 `If-Modified-Since` 要求標頭。

我們強烈建議您使用 `ETag`，因為這個值不像 `Last-Modified` 值容易出錯。如果您有這個選項，請同時設定這兩個值，網際網路使用者會感謝您。或許吧。

如果您認為有重大變更，可以自行決定是否要由用戶端重新整理快取內容。內容有重大變更時，建議您要求重新整理快取。假如您只更新了網頁底部的版權日期，可能就不屬於重大變更。

## `ETag` 和 `If-None-Match`

Google 檢索器支援 `ETag` 的條件要求，完全符合 [HTTP 快取標準](https://www.rfc-editor.org/rfc/rfc9111.html)定義。也就是說，如要向 Google 的檢索器傳送快取偏好設定信號，請將 `Etag` 值設為任何任意的 ASCII 字串 (通常是內容或版本號碼的雜湊，但也可以是 π 的一部分，由您決定)，該字串必須與存取網址所代管內容的表示法相符。舉例來說，如果您在同一個網址下代管相同內容的不同版本 (例如行動版和電腦版)，每個版本可能有其專屬的 `ETag` 值。

支援快取的 Google 檢索器會傳送 `ETag` 值，該值是先前在 `If-None-Match header` 中檢索該網址時傳回的值。如果檢索器傳送的 `ETag` 值與伺服器產生的目前值相符，伺服器應傳回 HTTP `304` (未修改) 狀態碼，且沒有 HTTP 主體。沒有 HTTP 主體這一點很重要，原因如下：

* 伺服器不需要耗費運算資源來實際產生內容，這樣可以省錢。
* 伺服器不需要傳輸 HTTP 主體，這樣可以省錢。

在用戶端 (例如使用者的瀏覽器或 Googlebot)，系統會從用戶端的內部快取中擷取該網址底下的內容。這項作業不需要傳輸資料，因此速度極快，除了能讓使用者滿意，還能節省資源。

## `Last-Modified` 和 `If-Modified-Since`

與 `ETag` 類似，Google 檢索器也支援 `Last-Modified based` 條件要求，完全符合 HTTP 快取標準的定義。從語意角度來看，這與 `ETag` 的運作方式相同，兩者都是透過 ID 決定資源是否可快取。從用戶端角度來看，這項功能提供與 `ETag` 相同的優勢。

如果您使用 `Last-Modified` 做為快取指令，請參考以下幾項建議：

1. `Last-Modified` 標頭中的日期格式必須符合 [HTTP 標準](https://www.rfc-editor.org/rfc/rfc9110.html)。為避免剖析問題，建議使用以下日期格式：「星期幾, DD Mon YYYY HH:MM:SS 時區」。例如：
   「Fri, 4 Sep 1998 19:15:56 GMT」。
2. 雖然 `Cache-Control` 標頭的 `max-age` 不是必填欄位，但建議您一併設定，協助檢索器判斷何時要重新檢索特定網址。將 `max-age` 欄位的值設為內容預期不變的秒數。例如：`Cache-Control: max-age=94043`。

## 範例

如果您和我一樣，不太瞭解啟發式快取的運作方式，建議您參考要求和回應鏈結的範例，或許有助於掌握相關概念。以下兩個鏈結 (一個用於 `ETag`/`If-None-Match`，另一個用於 `Last-Modified`/`If-Modified-Since`)，以視覺化方式呈現運作方式：

|  | `ETag`/`If-None-Match` | `Last-Modified`/`If-Modified-Since` |
| --- | --- | --- |
| **伺服器對檢索的回應：**這是檢索器用來儲存先決條件標頭欄位 `ETag` 和 `Last-Modified` 的回應。 | ``` HTTP/1.1 200 OK Content-Type: text/plain Date: Fri, 4 Sep 1998 19:15:50 GMT ETag: "34aa387-d-1568eb00" ... ``` | ``` HTTP/1.1 200 OK Content-Type: text/plain Date: Fri, 4 Sep 1998 19:15:50 GMT Last-Modified: Fri, 4 Sep 1998 19:15:56 GMT Cache-Control: max-age=94043 ... ``` |
| **後續檢索器條件要求：**條件要求會以先前要求儲存的先決條件標頭值為根據。這些值會傳回至伺服器，在 `If-None-Match` 和 `If-Modified-Since` 要求標頭中進行驗證。 | ``` GET /hello.world HTTP/1.1 Host: www.example.com Accept-Language: en, hu User-Agent: Googlebot/2.1 (+http://www.google.com/bot.html) If-None-Match: "34aa387-d-1568eb00" ... ``` | ``` GET /hello.world HTTP/1.1 Host: www.example.com Accept-Language: en, hu User-Agent: Googlebot/2.1 (+http://www.google.com/bot.html) If-Modified-Since: Fri, 4 Sep 1998 19:15:56 GMT ... ``` |
| **伺服器對條件要求的回應：**檢索器傳送的先決條件標頭值會在伺服器端進行驗證，因此伺服器會傳回 `304` HTTP 狀態碼給檢索器 (不含 HTTP 主體)。這會發生在每項後續要求中，直到先決條件驗證失敗 (伺服器端的 `ETag` 或 `Last-Modified` 日期有變更) 為止。 | ``` HTTP/1.1 304 Not Modified Date: Fri, 4 Sep 1998 19:15:50 GMT Expires: Fri, 4 Sep 1998 19:15:52 GMT Vary: Accept-Encoding If-None-Match: "34aa387-d-1568eb00" ... ``` | ``` HTTP/1.1 304 Not Modified Date: Fri, 4 Sep 1998 19:15:50 GMT Expires: Fri, 4 Sep 1998 19:15:51 GMT Vary: Accept-Encoding If-Modified-Since: Fri, 4 Sep 1998 19:15:56 GMT ... ``` |

如果您想讓使用者滿意，並想節省主機代管費用，請與您的代管服務或內容管理系統供應商或開發人員討論，瞭解如何為網站啟用 HTTP 快取。至少使用者會更滿意您提供的瀏覽體驗。

如要討論快取功能，請前往最接近的[搜尋中心產品討論社群](https://goo.gle/sc-forum)。如對我們的快取方式有任何意見，歡迎在這篇網誌文章中一起發布的[快取功能說明文件](https://developers.google.com/search/docs/crawling-indexing/overview-google-crawlers?hl=zh-tw#http-caching)中提供意見回饋。

發文者：[Gary Illyes](https://developers.google.com/search/blog/authors/gary-illyes?hl=zh-tw)

---

## 想進一步瞭解檢索嗎？請觀看完整的「檢索 12 月」系列影片：
