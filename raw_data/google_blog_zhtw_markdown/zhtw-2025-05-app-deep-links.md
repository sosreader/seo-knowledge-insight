# 應用程式深層連結：連結網站和應用程式
- **發佈日期**: 2025-05-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2025/05/app-deep-links?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2025 年 5 月 2 日，星期五

自 2013 年起，Google 搜尋就認識到[在以行動為主的時代，應用程式深層連結的重要性](https://developers.google.com/search/blog/2013/10/indexing-apps-just-like-websites?hl=zh-tw)。在本文中，我們將回顧應用程式深層連結的現況，並說明深層連結的定義、使用上的優點，以及如何有效導入。

![連結至購物行動應用程式的搜尋結果](https://developers.google.com/static/search/blog/images/search-results-to-deep-link.png?hl=zh-tw)

連結至購物行動應用程式的搜尋結果

## 將使用者順暢連結至應用程式中的內容

深層連結是特殊的 URI，可將使用者直接導向應用程式中的特定內容，而不只是行動應用程式的首頁。想像一下，使用者點按您網站或社群媒體上的產品搜尋結果，而系統會將他們直接帶往應用程式中的特定產品頁面。要實現這項功能，您需要在 iOS (稱為「通用連結」) 和 Android (稱為「應用程式連結」) 上設定深層連結。這兩種類型 Google 搜尋皆可支援。

## 深層連結的優點

* **提升使用者體驗：**如果使用者已安裝應用程式，即可直接前往應用程式中的內容。這樣一來，使用者平均可省下 2 到 3 次點擊，有更多時間與應用程式互動。
* **更精準且相關的行銷：**深層連結可讓您透過電子郵件、廣告活動和社群媒體貼文等行銷素材中的單一連結 (應用程式和網站都適用這類連結)，將使用者直接帶往您想讓他們看到的特定相關內容，以強化行銷活動的效益。
* **更優質的數據分析和更詳盡的報表：**深層連結可讓您更準確地將轉換歸因至特定頁面，進而分析應用程式內的使用者行為，這在評估不同廣告活動的成效時特別實用。

## 深層連結與 SEO

在網站中加入深層連結，即可將網站網址連結至相關應用程式頁面。這不會影響 Google 搜尋顯示內容的方式；搜尋服務會繼續使用網頁內容建立索引和排名。應用程式深層連結可讓使用者從搜尋結果直接前往相應的應用程式頁面 (如果已安裝)，進而提升使用者體驗。

由於 Google 搜尋會使用網頁內容建立索引和排名，因此務必只有在應用程式頁面包含與對應網頁相同的內容時，才新增深層連結。否則，Google 搜尋中顯示的網頁標題和摘要，可能會誤導使用者，讓他們點選後看到不符預期的內容。只要應用程式頁面與對應網頁的內容相符，版面配置或其他使用者體驗差異皆可接受。

Search Console 會提供您網站的 Android 應用程式深層連結成效資料。在[成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#zippy=,search-appearance)中，您可以使用 [Android 應用程式搜尋外觀篩選器](https://support.google.com/webmasters/answer/7576553?hl=zh-tw#zippy=,search-appearance)，查看 Android 應用程式深層連結何時被找到並向使用者顯示。

![Search Console 成效報表，顯示 Android 應用程式搜尋外觀篩選器](https://developers.google.com/static/search/blog/images/android-app-search-appearance-filter.png?hl=zh-tw)

Search Console 成效報表，顯示 Android 應用程式搜尋外觀篩選器

## 導入深層連結

如要設定網站和應用程式之間的深層連結，請參閱下列平台專屬的導入指南：

* **Android 應用程式**：使用[應用程式連結](https://developer.android.com/training/app-links?hl=zh-tw)。
  您可以在應用程式資訊清單檔案中，將應用程式與網站建立關聯。
* **iOS 應用程式**：導入[通用連結](https://developer.apple.com/documentation/Xcode/allowing-apps-and-websites-to-link-to-your-content)。
  做法：您可以在網站上設定 `apple-app-site-association` 檔案，並在應用程式中進行設定。

您也可以使用下列工具導入、驗證應用程式深層連結，並排解相關問題。

* [Play 管理中心的「深層連結」頁面](https://play.google.com/console/about/deeplinks/?hl=zh-tw)：提供現有設定的總覽資訊，針對未設定深層連結的廣告網址建立報表，並在無須發布新版本應用程式的情況下，發布應用程式深層連結修正項目。
* [Android Studio App Links Assistant](https://developer.android.com/studio/write/app-link-indexing?hl=zh-tw) (位於「工具」下方)：提供現有深層連結和驗證狀態的總覽資訊、每個連結的錯誤設定詳細資料，以及如何自動修正設定問題。
* [對 iOS 通用連結進行偵錯](https://developer.apple.com/documentation/technotes/tn3155-debugging-universal-links)：在 iOS 上測試、偵錯及設定通用連結。

希望這些提示能協助您為應用程式導入深層連結。如有其他問題，請參閱[深層連結速成課程](https://youtube.com/playlist?list=PLWz5rJ2EKKc-hZMZIfAUMBDR7kPC1m7HU&si=RzbiW8U9tZcuF8ay&hl=zh-tw)。

發文者：Google 搜尋關係與區域服務商家、Android 開發人員關係代表 [John Mueller](https://developers.google.com/search/blog/authors/john-mueller?hl=zh-tw)
