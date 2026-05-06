# 複合式搜尋結果與 Search Console Webmaster Conference Lightning Talks
- **發佈日期**: 2020-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/08/rich-results-search-console?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 8 月 11 日，星期二

幾個星期前，我們舉辦了另一場 [Webmaster Conference Lightning Talks](https://www.youtube.com/playlist?list=PLKoqnv2vTMUNf6w9wUu7RgxHkaTrq2Zpf&hl=zh-tw)，這次的主題是[複合式搜尋結果與 Search Console](https://www.youtube.com/watch?v=B4MlM1sJ5ZE&hl=zh-tw)。研討會期間，有眾多觀眾進入我們的聊天室提問。儘管我們當時已盡力回答問題，但顯然我們的打字速度跟不上觀眾的提問速度，因此我們決定在這篇網誌文章中繼續回答那些尚未解答的問題。

如果您錯過了那次活動，不妨參考下方提供的影片。這部影片會介紹該如何開始使用複合式搜尋結果，以及如何利用 Search Console 改進您的內容在 Google 搜尋結果中的呈現方式。

## 複合式搜尋結果與 Search Console 常見問題

### 實作結構化資料是否能讓網站的排名高於競爭對手？

[結構化資料](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data?hl=zh-tw)本身不是影響排名的一般因素，但是能協助 Google 理解網頁內容，讓 Google 更容易在相關情境下顯示網頁，以及在更多搜尋體驗中提供網頁資訊。

### 屬於電子商務類別網頁最好使用哪些結構化資料？

您不需要標記類別頁面上的眾多產品，只有當產品是頁面上的主要元素時，您才應該進行標記。

### 結構化資料應該包含多少內容？是否可能出現內容過多的問題？

您可以在網頁上實作不限數量的結構化資料，但請務必遵循[一般指南](https://developers.google.com/search/docs/appearance/structured-data/sd-policies?hl=zh-tw)中的規定。例如，標記的內容應一律對使用者顯示，而且是網頁的主要內容。

### 常見問題網頁的點擊次數和曝光次數到底是怎麼計算的？

[常見問題 (FAQ) 網頁](https://developers.google.com/search/docs/appearance/structured-data/faqpage?hl=zh-tw)含有特定主題的問答集。若常見問題網頁具有適當標記，即可在 Google 搜尋中以複合式搜尋結果的形式呈現，同時支援 Google 助理的「動作」功能，讓網站擁有者更容易觸及目標使用者。這些複合式搜尋結果含有常見問題摘要，可讓使用者展開及收合答案。每當這類結果出現在使用者的 Google 搜尋結果中，Search Console 就會計為一次曝光；如果使用者點擊連結並造訪網站，則會計為一次點擊。不過，如果點擊的作用只是展開及收合搜尋結果，Search Console 就不會計為點擊次數，因為這類點擊並未讓使用者進入網站。您可以透過[搜尋成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)中的 [搜尋外觀] 分頁，查看 FAQ 複合式搜尋結果的曝光次數和點擊次數。

### Google 是否會針對評論網站上的評論顯示複合式搜尋結果？

評論不得由商家或內容供應者撰寫或提供。我們的[評論摘錄指南](https://developers.google.com/search/docs/appearance/structured-data/review-snippet?hl=zh-tw#guidelines)指出：「評分必須由使用者直接提供。」發布由商家自行撰寫的評論違反指南規範，可能會導致[專人介入處理](https://support.google.com/webmasters/answer/9044175?hl=zh-tw#spammy-structured-markup)。

### Google 並未使用部分結構定義類型，為什麼我們還要使用這些類型？

雖然 Google 支援許多[結構定義類型](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=zh-tw)，但是其他搜尋引擎可能會使用別的類型來顯示複合式搜尋結果，因此您可能需要針對這些搜尋引擎實作相應的結構定義類型。

### 為什麼之前曾出現在 Google 搜尋中的複合式搜尋結果有時會消失？

Google 演算法會依據使用者的搜尋記錄、所在位置、裝置類型等多種因素來確定要顯示的搜尋結果，藉此為每位使用者提供最佳搜尋體驗。在某些情況下，Google 可能會判定某項功能比另一項功能更合適，甚至認定一般藍色連結對使用者最好。請參考[複合式搜尋結果狀態報告](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)，如果有效項目的數量並未減少，或是錯誤沒有突然增加，就代表實作沒有問題。

### 如何驗證動態產生的結構化資料？

如要檢查結構化資料的實作效果，最保險的做法是在 Search Console 上[檢查網址](https://support.google.com/webmasters/answer/9012289?hl=zh-tw)，這樣就能查看 Google 已編入索引的特定網頁版本資訊。您也可以使用公開的[複合式搜尋結果測試](https://goo.gle/richresults)工具來查看認定結果。如果無法透過這些工具看到結構化資料，就代表您的標記無效。

### 如何在 WordPress 中新增結構化資料？

許多 [WordPress 外掛程式](https://wordpress.org/plugins/search/structured+data/)都能協助您新增結構化資料。另外，請檢查您的主題設定，該設定可能也支援某些類型的標記。

### 在結構化資料測試工具淘汰之後，複合式搜尋結果測試是否會支援 Google 搜尋不支援的結構化資料？

[複合式搜尋結果測試](https://goo.gle/richresults)支援所有能在 Google 搜尋上觸發複合式搜尋結果的結構化資料。此外，隨著 Google 針對越來越多的結構化資料類型打造新的體驗，我們也會在複合式搜尋結果測試中增加支援這些類型。在準備淘汰結構化資料測試工具的同時，我們也會研究如何支援 Google 以外的通用工具。

## 敬請持續鎖定最新消息！

如果您錯過了先前的 Lightning Talks，請查看 [WMConf Lightning Talks 播放清單](https://www.youtube.com/playlist?list=PLKoqnv2vTMUNf6w9wUu7RgxHkaTrq2Zpf&hl=zh-tw)，並記得[訂閱我們的 YouTube 頻道](https://www.youtube.com/channel/UCWf2ZlNsCGDS89VBF_awNvA?sub_confirmation=1&hl=zh-tw)，後續會有更多精彩影片上線！強烈建議您在 YouTube 加入我們的首播活動，每一集都會有聊天室和問答環節，歡迎參加！

發文者：搜尋服務代表 [Daniel Waisberg](https://www.danielwaisberg.com)
