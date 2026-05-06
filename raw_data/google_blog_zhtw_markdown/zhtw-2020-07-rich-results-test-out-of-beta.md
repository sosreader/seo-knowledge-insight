# 複合式搜尋結果測試已通過測試階段
- **發佈日期**: 2020-07-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/07/rich-results-test-out-of-beta?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 7 月 7 日，星期二

今天我們很高興宣布，[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)已通過測試階段，能夠全面支援所有 Google 搜尋複合式搜尋結果。此外，我們也準備淘汰結構化資料測試工具，雖然這項工具目前仍開放使用，但我們強烈建議您從現在就改用複合式搜尋結果測試來驗證結構化資料。

**更新**：我們已於 2020 年 12 月 14 日宣布[將服務的重心重新移回結構化資料測試工具，而不會淘汰](https://developers.google.com/search/blog/2020/12/structured-data-testing-tool-update?hl=zh-tw)。

複合式搜尋結果是一種 Google 搜尋功能，能為搜尋結果提供比標準藍色連結更豐富的資訊。這類搜尋結果是根據[結構化資料](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=zh-tw)產生，可以包含輪轉介面、圖片或其他非文字元素。為了協助您檢測結構化資料及預覽複合式搜尋結果的效果，我們在過去幾年中開發了複合式搜尋結果測試。

這項新工具能提供更優質的服務，原因如下：

* 能依據提供的標記，顯示網頁適用於哪些搜尋功能強化項目
* 能更有效率地處理以動態方式載入的結構化資料標記
* 能夠轉譯行動版以及電腦版的搜尋結果
* 驗證結果與 Search Console 報告完全一致

您可以使用複合式搜尋結果測試來檢測網頁的程式碼片段或網址，測試工具會傳回在網頁上偵測到的錯誤和警告。請注意，「錯誤」會導致網頁無法以複合式搜尋結果的形式呈現，而「警告」的問題雖然可能會使搜尋結果的外觀受到限制，但網頁仍能呈現為複合式搜尋結果。舉例來說，如果工具的警告指出網頁缺少圖片屬性，該網頁仍會以複合式搜尋結果的形式呈現，只是無法顯示圖片。

以下列舉幾項使用此工具時會看到的內容。

![複合式搜尋結果測試中的有效結構化資料](https://developers.google.com/static/search/blog/images/import/fc7217406295798b3dceca0cfbcc7222.jpg?hl=zh-tw)
![程式碼瀏覽器在複合式搜尋結果測試中顯示偵測到的錯誤](https://developers.google.com/static/search/blog/images/import/8ef46cf2f497dd7077c705e002163c4a.jpg?hl=zh-tw)
![複合式搜尋結果測試的搜尋結果預覽畫面](https://developers.google.com/static/search/blog/images/import/bf2dfef0b7b5edbb2396bff8f304bf4f.jpg?hl=zh-tw)

歡迎進一步瞭解[複合式搜尋結果測試](https://support.google.com/webmasters/answer/7445569?hl=zh-tw)。如果您有任何意見，請透過[產品討論社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Astructured_data%29&%3Bmax_results=20&hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 告訴我們。

*發文者：Search Console 產品經理 [Moshe Samet](https://www.linkedin.com/in/moshe-samet-5465326/)*
