# Google 搜尋處理多語言搜尋的方式
- **發佈日期**: 2023-09-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/09/multilingual-searches?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 9 月 8 日，星期五

在世界各地許多國家/地區中，使用者通常不只會說一種語言，使用多種語言搜尋也很常見。為了提供最佳內容，Google 會使用多種方式，自動判斷搜尋結果最適合以哪種語言顯示。

## Google 如何自動判斷搜尋結果的語言

我們理解，有些使用者可能以為 Google 搜尋只會顯示符合其語言設定的搜尋結果，但這樣的做法並不像聽起來那麼實用。

瀏覽器、行動裝置和電腦都有各自獨立的語言設定。因此，使用者可能將瀏覽器設為一種語言，並將行動裝置或電腦設為其他語言。

Google 搜尋也有語言設定，但這是為了[顯示語言](https://support.google.com/websearch/answer/3333234?hl=zh-tw)的部分，也就是搜尋結果周圍的按鈕和選單文字所使用的語言。搜尋結果本身不需要與顯示語言相符，這是因為我們有充分理由這樣做。Google 搜尋的使用者中，約有半數是以多語言搜尋，且搜尋時通常使用與設定不同的語言。

不過，Google 搜尋會考量上述所有設定和其他因素，[自動判斷顯示搜尋結果時最實用的語言](https://support.google.com/websearch/answer/13511324?hl=zh-tw)。也就是說，多語搜尋者不用經常變更一或多個語言設定，就能以他們使用的其他語言取得搜尋結果。

舉例來說，位於法國的使用者可使用法文、英文或阿拉伯文搜尋，然後預期系統以合適的語言顯示搜尋結果。同樣地，由於有些鍵盤輸入不易，印度的使用者可能會使用拉丁字母而非 देवनागरी (Devanāgarī) 字元，以北印度文搜尋，但想要收到以這兩種方式撰寫的北印度文搜尋結果。

有時候，即使系統顯示的搜尋結果語言，與使用者的語言設定或用於搜尋的語言不同，仍可能出現實用的搜尋結果。如果系統偵測到使用者所在地區的常用語言不只一種，就有可能發生這種情況。

## 如何篩選特定語言的搜尋結果

自動化系統無法篩選出單一語言的搜尋結果，但我們提供的搜尋結果語言篩選器可協助你解決這個問題。

這個篩選器很適合用來將網頁搜尋結果的範圍縮小至所選的一或多種語言。不過，這項功能並非完美。如果無法準確偵測語言 (例如使用多種語言撰寫的網頁)，可能就無法正常運作，而且可能不支援部分搜尋結果功能。

如要瞭解如何啟用及使用這個篩選器，請參閱[搜尋結果語言篩選器](https://support.google.com/websearch/answer/13485060?hl=zh-tw)說明頁面。以下是啟用該功能後，德文使用者會看到的情形 (「Werkzeug」德文的意思是「工具」)：

![顯示語言設定為德文的螢幕截圖](https://developers.google.com/static/search/blog/images/language-settings-2023-09.png?hl=zh-tw)

你也可以先使用[進階搜尋頁面](https://www.google.com/advanced_search?hl=zh-tw)，依語言篩選結果，再開始搜尋。無論採用哪一種選項，你都可以視需要彈性篩選一次。

## 內容製作者應如何為多語搜尋者考量

如果發布商在常用多種語言的地區製作內容，建議使用那些語言製作內容，而不是只使用一種廣為理解的語言。使用者喜歡以自己偏好語言撰寫的內容，Google 也會希望有可用內容時可以顯示這些內容。

此外，製作多語言內容的使用者也應確保內容符合相關技術指南，如以下說明頁面所述：[向 Google 說明網頁的本地化版本](https://developers.google.com/search/docs/specialty/international/localized-versions?hl=zh-tw)。

## 我們如何持續改善語言比對功能

在大部分情況下，我們都能正確取得語言意圖，但世界各地的語言偏好卻十分複雜。因此，為了向多語人士提供服務，我們持續實驗各種功能，例如[雙語搜尋](https://blog.google/intl/en-in/company-news/inside-google/google-for-india-2022-product-announcements/?hl=zh-tw)，以及最近宣布可[在英文和北印度文之間切換的 SGE 生成式 AI 回應](https://blog.google/products/search/google-search-generative-ai-india-japan/?hl=zh-tw)。

過去幾個月來，我們還推出了一系列的更新，藉此改善語言比對系統，包括大約兩週前的最新更新。綜合以上情況，這些做法應該能夠進一步比對使用者搜尋時所用的語言，同時仍讓多語搜尋者能彈性地存取多種語言的搜尋結果。

此外，我們也會持續改善自動化系統判斷搜尋結果顯示語言的方式，持續以使用者偏好的語言盡可能列出最實用的資訊。

發文者：軟體工程師 Sunny Nahar、產品經理 Ali Tawfiq 和 Google 搜尋公關 [Danny Sullivan](https://developers.google.com/search/blog/authors/danny-sullivan?hl=zh-tw)
