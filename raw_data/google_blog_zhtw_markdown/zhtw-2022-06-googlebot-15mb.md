# Googlebot 和 15 MB 的內容
- **發佈日期**: 2022-06-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/06/googlebot-15mb?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 6 月 28 日，星期二

最近幾天，我們收到了大量關於 [Googlebot 說明文件](https://developers.google.com/search/docs/crawling-indexing/googlebot?hl=zh-tw)近期更新內容的問題。也就是說，我們記錄到，Googlebot 在擷取[特定檔案類型](https://developers.google.com/search/docs/crawling-indexing/indexable-file-types?hl=zh-tw)時，只「看見」前 15 [MB](https://en.wikipedia.org/wiki/Megabyte#-_-) 的內容。這並非新的門檻，這個門檻已經存在好幾年了。我們之所以將這一點加入說明文件中，是因為對某些人來說，這個門檻在偵錯時可能很實用，而且也很少發生變化。

這項限制僅適用於 Googlebot 首次發出要求時收到的[位元組](https://en.wikipedia.org/wiki/Byte#;)) (內容)，並不適用於網頁中參照的資源。

**2023 年 3 月 16 日**：為了進一步說明，每個子資源擷取 (尤其是 CSS 和 JavaScript) 都設有 15 MB 的限制。

舉例來說，當您開啟 `https://example.com/puppies.html` 時，您的瀏覽器一開始會下載 HTML 檔案的位元組，然後可能會根據這些位元組，針對外部 JavaScript、圖片透過 HTML 中的網址所參照的任何內容發出進一步的要求。Googlebot 也會執行相同的動作。

**15 MB 的限制對我有什麼影響？**
很可能沒有什麼影響。網路上有[極少數的網頁](https://twitter.com/paulcalvano/status/1541402096897069056)大小較大。您 (親愛的讀者) 不太可能擁有這類的網頁，因為 [HTML 檔案的中位數大小約為 15 MB 的 500 分之一](https://httparchive.org/reports/page-weight#bytesHtml)：30 [KB](https://en.m.wikipedia.org/wiki/Kilobyte)。不過，如果您是超過 15 MB 大小的 HTML 網頁的擁有者，建議您至少將部分內嵌指令碼和 CSS 灰塵遷移到外部檔案。

**超過 15 MB 的內容會怎麼樣？**
Googlebot 會捨棄超過 15 MB 的內容，只有前 15 MB 的內容才會編入索引。

**15 MB 的限制適用於哪些內容類型？**
15 MB 的限制適用於 Googlebot (Googlebot Smartphone 和 Googlebot Desktop) 在擷取 [Google 搜尋支援的檔案類型](https://developers.google.com/search/docs/crawling-indexing/indexable-file-types?hl=zh-tw)時所擷取的內容。

**這是否代表 Googlebot 看不到我的圖片或影片？**
否。Googlebot 會透過多次連續擷取來分別擷取在 HTML 中透過網址 (例如 `<img src="https://example.com/images/puppy.jpg" alt="cute puppy looking very disappointed" />`) 所參照的影片和圖片。

**資料 URI 會增加 HTML 檔案大小？**
可以。使用 [data URIs](https://en.wikipedia.org/wiki/Data_URI_scheme) 會增加 HTML 檔案大小，因為這些內容是包含在 HTML 檔案中。

**如何查詢網頁大小？**
您可以使用多種方法查詢網頁大小，但最簡單的方法可能是使用您自己的瀏覽器及其開發人員工具。剛往常一樣載入頁面，然後啟動開發人員工具並切換至「網路」分頁。重新載入頁面，您應該會看到瀏覽器為了轉譯網頁而發出的所有要求。其中最上方的要求就是您要尋找的項目，而「大小」欄中會顯示該網頁位元組大小。

例如，在 [Chrome 開發人員工具](https://developer.chrome.com/docs/devtools?hl=zh-tw)中可能會顯示以下內容，「大小」欄位中顯示 150 kB：

![Chrome 開發人員工具的「網路」分頁](https://developers.google.com/static/search/blog/images/scsh-googlebot15mb.png?hl=zh-tw)

如果您喜歡嘗試不同事物，可以在指令列中使用 [cURL](https://curl.se/)：

```
curl \
-A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36" \
-so /dev/null https://example.com/puppies.html -w '%{size_download}'
```

如有其他問題，歡迎前往 [Twitter](https://twitter.com/googlesearchc) 和[搜尋中心論壇](https://support.google.com/webmasters/community?hl=zh-tw)與我們交流。如果您需要關於說明文件的更多資訊，請向我們提供有關網頁本身的意見回饋。

發文者：[Gary Illyes](https://garyillyes.com/+)
