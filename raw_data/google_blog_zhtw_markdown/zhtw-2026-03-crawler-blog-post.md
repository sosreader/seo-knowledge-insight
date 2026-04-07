# Googlebot 內部運作：揭開檢索、擷取和處理位元組的神秘面紗
- **發佈日期**: 2026-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2026/03/crawler-blog-post?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2026 年 3 月 31 日，星期二

如果您收聽過[第 105 集的「Search Off the Record」Podcast](https://www.youtube.com/watch?v=JpweMBnpS4Q&hl=zh-tw)，可能會聽到我們深入探討一個貼近我們內在核心 (與伺服器) 的主題：Googlebot 的內部運作方式。

長期以來，「Googlebot」這個名稱讓人聯想到的形象，就是一個不知疲倦的機器人，系統化地讀取網際網路。但實際情況比這複雜一點，也更有趣。今天，我們要深入探討我們的檢索基礎架構，特別著重於我們自己也深感苦惱的部分：位元組大小限制。

## 首先，Googlebot 並非單一程式

我們先來釐清歷史上的誤稱。2000 年代初期，Google 只有一項產品，因此只有一個檢索器。「Googlebot」這個名稱就此沿用至今。但如今 Googlebot 只是某個類似集中式檢索平台的使用者之一。

在伺服器記錄中看到 Googlebot 時，您看到的只是 Google 搜尋。其他數十個用戶端 (包括 Google 購物、AdSense 等) 也會透過這個相同的基礎架構，以不同的檢索器名稱傳送檢索要求。如要瞭解較大的用戶端，請參閱 [Google 檢索器基礎架構網站](https://developers.google.com/crawling/docs/crawlers-fetchers/overview-google-crawlers?hl=zh-tw)。

## 2 MB 限制：您的位元組會發生什麼情況？

這部分有點令人困惑。檢索器基礎架構的每個用戶端都必須為擷取作業做一些設定。這些設定包括使用者代理程式字串、檢索器會在 robots.txt 中尋找哪些使用者代理程式符記，以及檢索器會從單一網址擷取多少位元組。

Googlebot 目前會針對每個網址擷取最多 2 MB 的內容 (PDF 除外)。也就是說，Googlebot 只會檢索資源的前 2 MB，包括 HTTP 標頭。PDF 檔案大小上限為 64MB。

圖片和影片檢索器通常有廣泛的閾值範圍，主要取決於所擷取的產品。舉例來說，擷取網站小圖示的上限可能很低，不像圖片搜尋。

如果其他檢索器未指定限制，則無論內容類型為何，預設值為 15 MB。

這對伺服器透過網路傳送的位元組有什麼影響？

1. **部分擷取：**如果 HTML 檔案超過 2 MB，Googlebot 不會拒絕該網頁，而是會在 2 MB 截斷點停止擷取。請注意，這項限制包含 HTTP 要求標頭。
2. **處理截斷的檔案：**下載的部分 (前 2 MB 的位元組) 會傳送至我們的索引系統和網路轉譯服務 (WRS)，就像是完整的檔案一樣。
3. **未顯示的位元組：**系統會完全忽略超過 2 MB 閾值「之後」的位元組。系統不會擷取、轉譯這些資料或為其建立索引。
4. **匯入資源：**WRS 會使用 Googlebot 擷取 HTML 中參照的所有資源 (媒體、字型和少數特殊檔案除外)，就像擷取上層 HTML 一樣。這些資源本身有針對每個網址獨立計算的位元組計數器，不會計入上層網頁的大小。

對絕大多數網站而言，2 MB 的 HTML 酬載量非常龐大，您絕不會達到這個上限。不過，如果網頁包含龐大的內嵌 base64 圖片、大量內嵌 CSS/JavaScript 區塊，或開頭是數 MB 的選單，可能會不小心將實際文字內容或重要結構化資料推到 2 MB 限制之後。如果沒有擷取這些重要位元組，Googlebot 就會認為這些位元組不存在。

## 轉譯位元組

當檢索器成功擷取位元組 (最多可達上限) 後，就會交棒給 WRS。WRS 會處理 JavaScript 並執行類似新式瀏覽器的用戶端程式碼，瞭解網頁的最終視覺和文字狀態。轉譯作業會提取並執行 JavaScript 和 CSS 檔案，以及處理 XHR 要求，以便更瞭解網頁的文字內容和結構 (不會要求圖片或影片)。每個要求資源的大小上限也為 2 MB。

不過請注意，WRS 只能執行檢索器實際擷取的程式碼。此外，[WRS 是以無狀態方式運作](https://developers.google.com/search/docs/crawling-indexing/javascript/fix-search-javascript?hl=zh-tw)，會在每次要求之間清除本機儲存空間和工作階段資料。這可能會對系統如何解讀動態的、依附 JavaScript 的元素造成影響。

## 位元組的最佳做法

為確保 Googlebot 能有效擷取及解讀您的內容，請記住下列位元組層級的最佳做法：

* **保持 HTML 簡潔：**將大量 CSS 和 JavaScript 移至外部檔案。雖然初始 HTML 文件的大小上限為 2 MB，但系統會分別擷取外部指令碼和樣式表 (受各自的限制)。
* **順序很重要：**將最重要的元素 (例如中繼標記、`<title>` 元素、`<link>` 元素、標準網址和必要結構化資料) 放在 HTML 文件中較高的位置。這樣可確保這些項目不太可能出現在截斷處下方。
* **監控伺服器記錄：**隨時留意伺服器回應時間。如果伺服器難以提供位元組，檢索器會自動減少檢索次數，避免基礎架構過載，進而降低檢索頻率。

**請注意，這項限制並非一成不變**，隨著網路演進和 HTML 網頁大小增加，這項限制可能會隨之變動。(或縮小。希望可以縮小。)

檢索並非魔法，而是經過精心調度的大規模位元組交換。瞭解中央擷取基礎架構如何擷取及限制這些位元組，有助於確保網站最重要的內容不會被遺漏。

祝您大獲成功！

想進一步瞭解幕後花絮嗎？歡迎在 YouTube 觀看[第 105 集的 Search Off the Record Podcast](https://www.youtube.com/watch?v=JpweMBnpS4Q&hl=zh-tw)，或透過您慣用的平台收聽！

發文者：[Gary](https://developers.google.com/search/blog/authors/gary-illyes?hl=zh-tw)
