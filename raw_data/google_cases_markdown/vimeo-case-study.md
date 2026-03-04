# Vimeo 如何改善客戶的影片搜尋引擎最佳化
- **發佈日期**: 
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/case-studies/vimeo-case-study?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-case-studies
---
# Vimeo 如何改善客戶的影片搜尋引擎最佳化

發布日期：2023 年 1 月 25 日

## Vimeo 簡介

Vimeo 是全方位的影片解決方案，每天都有超過 2.6 億名使用者，新增 35 萬部新影片，目標是為所有人提供專業品質的影片。

## 挑戰

Vimeo 的客戶需要獨立實作及管理影片搜尋引擎最佳化 (SEO) 的最佳做法，包括在自家網站中新增結構化資料、提交 Sitemap、呼叫 Indexing API 等，而且這些知識都相當專業，難以擴充。此外，Vimeo 的章節功能 (按時間標記標示的影片片段) 並未啟用，因此無法顯示在 Google 搜尋結果中。

2022 年，Vimeo 採用 [Google 最佳做法](https://developers.google.com/search/docs/appearance/video?hl=zh-tw)來解決這些難題，當中包含導入 [`VideoObject`](https://developers.google.com/search/docs/appearance/structured-data/video?hl=zh-tw#video-object) 結構化資料，並為影片播放器套用最佳做法，藉此讓 Vimeo 客戶不需要執行額外作業，就能享有[重要時刻](https://developers.google.com/search/docs/appearance/video?hl=zh-tw#key-moments)等功能帶來的好處。

## 允許大規模建立影片索引

為了將索引功能最佳化，並讓內嵌影片盡可能出現在相關搜尋結果中，Vimeo 採用了 Google 針對使用 `iframe` 嵌入的影片播放器提供的新指引。搭配 `noindex` 使用的新 [`indexifembedded`](https://developers.google.com/search/blog/2022/01/robots-meta-tag-indexifembedded?hl=zh-tw) 規則，可透過內嵌將標記歸因。套用了這個 [`VideoObject`](https://developers.google.com/search/docs/appearance/structured-data/video?hl=zh-tw) 標記後，嵌入客戶網頁上的 Vimeo 影片就有資格編入索引，而客戶不必自行加入標記。這項變更會套用至 Vimeo 目前影片庫中超過 7.5 億部的嵌入影片，以及日後新增和嵌入的所有影片。

如果您是像 Vimeo 這類嵌入式影片播放器的開發人員，也可以協助您的客戶享有影片搜尋的好處，並改善在 Google 搜尋中的顯示方式。您只需要完成以下操作即可：

1. 將 [`VideoObject` 結構化資料](https://developers.google.com/search/docs/appearance/structured-data/video?hl=zh-tw)新增到每個來源播放器網頁 (即代管該播放器的網頁，使用者會在網頁中其他地方嵌入 `iframe`)。
2. 在 `embedUrl` 資源所指向的網頁上，除了 robots `noindex` 規則之外，再新增 [`indexifembedded`](https://developers.google.com/search/blog/2022/01/robots-meta-tag-indexifembedded?hl=zh-tw) 規則，這樣一來，只有嵌入到客戶網頁的影片能夠編入 Google 搜尋索引中：

   ```
   <meta name="robots" content="noindex, indexifembedded" />
   ```
3. 等待 Googlebot 重新檢索受影響的網頁。

## 運用結構化資料啟用重要時刻功能

當 Google 搜尋顯示[重要時刻](https://developers.google.com/search/docs/appearance/video?hl=zh-tw#key-moments)時，系統會進一步強化影片複合式搜尋結果，附上可展開且可捲動的時間列 (含有加上標籤的區隔)。

> 「Vimeo 的其中一項目標，是要盡可能讓影片發揮最佳效果，而協助使用者不必具備工程師或搜尋引擎最佳化專家技能，就能擴大觸及範圍和曝光率，是我們達成此目標的一環。將影片內容中的知識展現出來是我們的重點之一，而「重要時刻」功能讓這個目標能直接在客戶的搜尋結果網頁中實現，強化他們的影片價值。- Vimeo 產品資深資深總監 Alex Cherny

為了讓所有 Vimeo 章節都能顯示為 Google 搜尋的「重要時刻」，Vimeo 已在所有影片代管網頁中加入 [`Clip` 標記](https://developers.google.com/search/docs/appearance/structured-data/video?hl=zh-tw#clip)。此外，Vimeo 也導入了 [`Seek` 標記](https://developers.google.com/search/docs/appearance/structured-data/video?hl=zh-tw#seek)，因此，如果影片沒有 Vimeo 章節，Google 還是能自動識別重要時刻。

![查詢「Canary College Campus Tour」的搜尋結果，顯示一部校園導覽影片，附上醒目顯示影片各部分的「重要時刻」。](https://developers.google.com/static/search/case-studies/images/vimeo-key-moments.png?hl=zh-tw)

搜尋者點選其中任一區隔，就會前往該 Vimeo 嵌入式影片所在的創作者網頁，影片會從時間標記所選的位置開始播放。如果您是像 Vimeo 這類嵌入式影片播放器的開發人員，也可以[啟用重要時刻](https://developers.google.com/search/docs/appearance/video?hl=zh-tw#key-moments)功能。

如果要針對 `iframe` 嵌入功能實作「重要時刻」，您需要為 `iframe` 嵌入功能開發一個方法，將開始時間參數傳達給來源影片播放器。舉例來說，您可以使用 [`postMessage`](https://developer.mozilla.org/docs/Web/API/Window/postMessage) JavaScript 包裝函式來啟用這項通訊功能。JavaScript 嵌入不需要使用這類包裝函式，因為系統可以在相同的網址網頁管理播放器控制項。
