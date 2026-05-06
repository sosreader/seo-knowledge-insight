# 新版 Search Console 商家資訊報表：透過產品結構化資料擴大資格條件
- **發佈日期**: 2022-09-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/09/merchant-listings?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 9 月 13 日，星期二

Google 很高興在此宣布，我們放寬在 Google 搜尋使用加強型產品體驗的資格，現在只要透過 `Product` 結構化資料就能使用。這些加強型產品體驗先前僅適用於 Merchant Center 使用者。此外，我們也更新了 Search Console 中的說明文件和報表，讓您更容易瞭解這些體驗的相關規定。

## 放寬資格，開放直接銷售產品的網站使用

一直以來，Google 都在搜尋結果中為購物者提供豐富的產品體驗。為了讓網站擁有者更容易享有這類體驗，Google 已放寬使用資格，讓導入結構化資料的網站可以使用。對網站擁有者來說，體驗可以概略分為兩類：

* **商家資訊體驗**：適用於讓購物者在網站上購買產品的網頁。
* **產品摘要**：涵蓋範圍變得更廣，適用於含有產品資訊的網頁 (包括銷售產品、發布產品評論，和/或提供其他網站匯總資訊的網頁)。

最初，Google 搜尋結果中的產品摘要主要採用 schema.org 的 [`Product` 結構化資料](https://schema.org/Product)技術，而商家資訊體驗則主要透過 [Google Merchant Center 動態饋給](https://support.google.com/merchants/answer/7052112?hl=zh-tw)提供產品詳細資料。現在起，即使沒有 Google Merchant Center 帳戶，商家也可以在網頁上提供產品資料，藉此使用商家資訊體驗。使用資格能夠放寬，部分得益於近期 schema.org 中產品相關屬性和類型的擴充 (針對服飾尺寸和能源效率評分等領域)。

## Google 搜尋中可使用的加強型產品體驗

新增結構化資料後，您可能就能使用下列體驗。

![在搜尋結果中顯示商家資訊體驗的可能方式](https://developers.google.com/static/search/blog/images/merchant-listings-popular-products.png?hl=zh-tw "在搜尋結果中顯示商家資訊體驗的可能方式")

**圖 1.** 在搜尋結果中顯示商家資訊體驗的可能方式

商家資訊體驗提供的加強型體驗包含[購物知識面板](https://blog.google/products/shopping/bringing-free-retail-listings-google-search/?hl=zh-tw)和[熱門產品](https://www.blog.google/products/search/new-way-find-clothes-shoes-and-more-search/?hl=zh-tw)，另外還有 [Google 圖片](https://images.google.com/?hl=zh-tw)和 [Google 智慧鏡頭](https://lens.google/?hl=zh-tw)中的購物體驗。商家資訊和產品摘要所需的結構化資料，請參閱 [`Product` 結構化資料說明文件](https://developers.google.com/search/docs/appearance/structured-data/product?hl=zh-tw)。

![搜尋結果中的產品摘要範例](https://developers.google.com/static/search/blog/images/merchant-listings-product-snippet.png?hl=zh-tw "搜尋結果中的產品摘要範例")

**圖 2.** 搜尋結果中的產品摘要範例

雖然 Google 會從全球網站收集產品結構化資料，但購物體驗可能只限部分國家/地區使用。

## 推出適用於網站擁有者的全新 Search Console 報表

![Search Console 導覽側欄，顯示新報表連結](https://developers.google.com/static/search/blog/images/merchant-listings-report-navigation.png?hl=zh-tw)

為了讓網站能從這些體驗中得益，現有的 Search Console `Product` 結構化資料報表已替換成兩種報表：新的[商家資訊報表](https://search.google.com/search-console/r/merchant-listings?hl=zh-tw)，以及[產品摘要報表](https://search.google.com/search-console/r/product?hl=zh-tw) (其中含有舊版產品報表)。這些報表會歸類到 Search Console 導覽列中新的「購物」部分。

您可以透過這兩種報表掌握網站在實作標記方面的錯誤、警告和有效網頁。報表中的變更內容也已反映在[複合式搜尋結果測試工具](https://support.google.com/webmasters/answer/7445569?hl=zh-tw)。

### 新版商家資訊報表

* 找出搜尋結果中[免費產品資訊體驗](https://support.google.com/merchants/answer/9826670?hl=zh-tw)的結構化資料問題。
* 與銷售產品的網頁相關。
* 涵蓋更廣泛的 schema.org 結構化資料屬性和類型 (由 `Product` 類型所使用，目前支援進階用途，例如服飾尺寸和能源效率評分)。

### 產品摘要報表

* 找出搜尋結果中產品摘要的結構化資料問題。
* 與分享產品評論資訊或匯總多個網站產品資料的網頁相關。請注意，銷售產品的網頁可能也會包含產品評論。
* 因應商家資訊驗證獨立為專屬報表做出相關調整，取代舊版產品結構化資料報表。先前的驗證錯誤記錄會保留在此報表中。

產品結果曝光次數不會再顯示於產品摘要報表。您還是可以在成效報表中查看產品結果的曝光次數。

## 我該使用哪一種報表？

如果您是經營網路商店的商家，請採取以下做法：

* 針對銷售產品的網頁，請查看商家資訊報表。
* 如果您在沒有銷售產品的網頁上會發布產品評論，請一併查看產品摘要報表。

如果您不在線上銷售產品，但仍會發布含有產品結構化資料的網頁：

* 請查看產品摘要報表。

## 進一步瞭解產品結構化資料。

詳情請參閱 [`Product` 結構化資料](https://developers.google.com/search/docs/appearance/structured-data/product?hl=zh-tw)的最新說明文件。如有任何問題，歡迎前往我們的 [Google 搜尋中心論壇](https://support.google.com/webmasters/community?hl=zh-tw)尋求協助。

發文者：搜尋服務代表 [Alan Kent](https://twitter.com/akent99)
