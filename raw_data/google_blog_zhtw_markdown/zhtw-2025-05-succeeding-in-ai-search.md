# 在 Google 搜尋的 AI 體驗中，確保內容表現良好的最佳方法
- **發佈日期**: 2025-05-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2025/05/succeeding-in-ai-search?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2025 年 5 月 21 日，星期三

身為網站擁有者、發布商或創作者，您可能會想知道如何在 AI 搜尋體驗 (例如 AI 摘要和[全新的 AI 模式](https://blog.google/products/search/google-search-ai-mode-update/?hl=zh-tw)) 中取得最佳成效。Google 長期以來建議的核心原則在這些新型態的體驗中也一樣適用。請專注於訪客，並提供獨特且能滿足他們需求的內容。這樣一來，無論 Google 搜尋服務如何演進，您都能掌握先機，因為我們的核心目標始終不變：協助使用者找到優質的原創內容，為他們帶來獨特價值。掌握這個概念之後，以下提供一些在 Google 搜尋 (包含 AI 體驗) 中取得成功的考量重點。

## 專注於為使用者提供獨特且有價值的內容

許多人常常會問如何製作「Google 想要的」內容。我們的答案是，Google 希望顯示符合使用者需求的內容。專注於製作獨特的非商品內容，讓透過 Google 搜尋前來的訪客和網站本身的讀者覺得實用且滿意。如此一來，您在 AI 搜尋體驗中就步上了正軌，使用者會提出更長、更具體的問題，以及進一步深入探索的後續查詢問題 (順帶一提，獨特且有價值的內容對於藍色連結結果也很重要)。您可以參閱[這篇說明](https://developers.google.com/search/docs/fundamentals/creating-helpful-content?hl=zh-tw)，瞭解如何製作實用、可靠，且以使用者為優先的內容，並自行評估內容。

## 提供良好的網頁體驗

即使內容再好，如果使用者造訪的網頁雜亂、難以瀏覽，或難以找到所需的主要資訊，也可能會讓使用者失望。無論使用者是透過傳統或 AI 搜尋結果前來，請務必提供[良好的網頁體驗](https://developers.google.com/search/docs/appearance/page-experience?hl=zh-tw)，例如網頁是否能在各裝置上正常顯示、體驗延遲情形，以及訪客是否能輕鬆區分主要內容和其他內容。

## 確保我們可以存取您的內容

請確認你的網頁符合 [Google 搜尋技術規定](https://developers.google.com/search/docs/essentials/technical?hl=zh-tw)，以便我們找到、檢索及建立索引，並考慮將網頁顯示在搜尋結果中。這包括確認 Googlebot 未遭封鎖、網頁運作正常 (Google 收到 HTTP `200 (success)` 狀態碼)，以及網頁含有可建立索引的內容。只要符合技術規定，一般搜尋 (包括 AI 格式) 就會納入考量。

## 使用預覽控制項管理瀏覽權限

搜尋功能可讓網站擁有者控管資訊卡中顯示的內容，包括 AI 格式。請使用 [`nosnippet`、`data-nosnippet`、`max-snippet`](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=zh-tw) 或 [`noindex`](https://developers.google.com/search/docs/crawling-indexing/block-indexing?hl=zh-tw) 設定顯示偏好設定。權限越嚴格，內容在 AI 體驗中顯示的方式就會受到越多限制。

## 確認結構化資料與顯示內容相符

[結構化資料](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=zh-tw)可用於以機器可讀的方式分享內容相關資訊，讓系統能加以考量，並讓網頁符合[特定搜尋功能和複合式搜尋結果](https://developers.google.com/search/docs/appearance/structured-data/search-gallery?hl=zh-tw)的使用資格。如果使用的是結構化資料，請務必[遵循我們的規範](https://developers.google.com/search/docs/appearance/structured-data/sd-policies?hl=zh-tw)，例如確保標記中的所有內容也能在網頁上顯示，以及[驗證結構化資料標記](https://support.google.com/webmasters/answer/7445569?hl=zh-tw)。

## 透過多模態內容取得成功

透過 AI 技術的力量，使用者可以執行[多模態搜尋](https://blog.google/products/search/ai-mode-multimodal-search/?hl=zh-tw)，拍攝相片或上傳圖片，並針對相片提出問題，接著取得豐富且完整的回覆，以及可以深入探索的連結。如要成功做到這點，請在網頁上加入高品質的[圖片](https://developers.google.com/search/docs/appearance/google-images?hl=zh-tw)和[影片](https://developers.google.com/search/docs/appearance/video?hl=zh-tw)，以輔助文字內容，並確保 [Merchant Center](https://support.google.com/merchants/answer/12159157?hl=zh-tw) 和 [商家檔案](https://developers.google.com/search/docs/appearance/establish-business-details?hl=zh-tw) 資訊保持最新狀態。

## 瞭解造訪的完整價值

我們發現，如果使用者點按的是含有 AI 摘要的搜尋結果網頁，這類點擊的品質會比較高，也就是說這類使用者較有可能在這些網站上瀏覽更長的時間。這是什麼原因呢？
與傳統搜尋相比，AI 結果可提供更多與主題相關的背景資訊，並顯示更多相關的輔助連結。這樣做或許能提供更高參與度的目標對象，並為您帶來新的訪客，但如果您過度專注於點擊次數，而非 Google 搜尋帶來的整體訪客價值，可能就無法為這些目標對象進行最佳化。建議您查看網站上的各種轉換指標，例如銷售、訂閱、更高參與度的目標對象，或商家資訊查詢。

## 隨著使用者需求進化

Google 搜尋中唯一可以預測的，就是搜尋服務會持續演進，因為使用者的需求也不斷變化。經典的「十個藍色連結」格式已變更，以滿足尋找圖像、影片、新聞和其他類型內容的使用者需求。電腦顯示畫面也進化為行動裝置友善顯示畫面。Google 搜尋已進化至可處理語音查詢或「多模態」查詢，例如拍攝花朵的照片，並要求搜尋服務從相片中辨識花朵。

我們的 AI 體驗代表了 Google 搜尋的又一次演進，讓我們持續以最佳方式滿足不斷變化的使用者需求。這項演進也為網站擁有者帶來新商機。有了 AI 摘要和 AI 模式，使用者會更頻繁地使用 Google 搜尋，提出更複雜的新問題，並對搜尋結果更加滿意。AI 摘要會以多種方式顯示連結，並在結果頁面中顯示更多來源，方便使用者點選連結，探索網路上的內容。

希望這些提示能協助你在傳統和 AI 搜尋結果中，都能透過優質內容獲得成功。如要進一步瞭解相關資訊，請參閱我們的新版說明頁面：[AI 功能和您的網站](https://developers.google.com/search/docs/appearance/ai-features?hl=zh-tw)，以及 [Google 搜尋的生成式 AI 內容使用指南 (適用於網站)](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content?hl=zh-tw)。

發文者：Google 搜尋關係團隊的 [John Mueller](https://developers.google.com/search/blog/authors/john-mueller?hl=zh-tw)
