# 提供購物者更完善的產品資訊
- **發佈日期**: 2021-02-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/02/product-information?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 2 月 26 日，星期五

Google 的使命是彙整全球資訊，而為購物者和零售商整理產品資訊是這項任務不可或缺的重要環節。去年，我們推出了多項全新服務，讓品牌和零售商能在 Google 上列出產品，透過 [Google 搜尋的產品知識面板](https://www.blog.google/products/shopping/bringing-free-retail-listings-google-search/?hl=zh-tw)或 [「購物」分頁](https://blog.google/products/shopping/its-now-free-to-sell-on-google?hl=zh-tw)呈現產品資訊。

為了盡可能讓使用者在 Google 搜尋中找到您的內容和產品，我們建議網站要以明確方式標示出所提到的產品。

我們將在以下幾個小節中說明相關規範，這些規範適用於製造商、零售商和發布商，能協助確保 Google 瞭解他們所販售或提到的產品。

## Google 如何識別線上與離線的產品

為了準確識別可供購物者購買的產品，Google 仰賴正確且可靠的產品資料。

建議您提供清楚明確的產品識別資訊，協助 Google 將販售資訊對應至產品，並將產品對應至相關搜尋。使用專屬產品 ID (例如全球交易品項識別碼 (GTIN™))、製造商零件編號 (MPN) 和品牌名稱等資訊，有助於增進 Google 對產品的瞭解。使用產品 ID 時，建議您遵循下列最佳做法：

* **專屬性：**每項產品都必須有一個專屬 ID，這個 ID 必須要能持續分享給生態系統中的其他人，不能出錯，並且要能同時在實體和數位商務系統中識別特定產品。
* **可供驗證：**產品的識別資訊 (例如製造商) 和其他產品資料必須要能透過可信任的來源加以驗證，讓市集網站能夠透過全球註冊資料庫 (也就是核發和管理 ID 的組織) 確認產品資料準確且完整。
* **全球通用：**電子商務讓全世界的連結更加緊密，採用全球生態系統通用的識別系統有助於每個國家/地區的相關人員順利識別產品。

Google [自 2015 年起採用 GTIN 做為標準產品 ID](https://commerce.googleblog.com/2015/09/reach-more-customers-online-add-gtins.html)，協助零售商在線上觸及更多客戶。

只要產品會透過多個賣方和市集販售，就能在「GS1 全球交易品項識別碼 (GTIN) 系統」註冊國際認可的標準 ID，以此做為商品在實體商店及電子商務平台上的專屬 ID。註冊 GTIN 也讓使用者能夠識別產品的來源。

## 適用於品牌與製造商的相關提示

品牌和製造商可透過 [Google Manufacturer Center](https://www.google.com/retail/solutions/manufacturer-center/?hl=zh-tw) 提交產品資料，藉此向 Google 提供專門用於識別自家產品的產品資訊。以下提供幾項實用提示，有助於 Google 瞭解您提供的資料：

* **確保產品擁有 GTIN：**您的產品必須擁有專屬的全球交易品項識別碼 (GTIN)，才能使用 Manufacturer Center。如要瞭解如何為產品指派 GTIN，請造訪[您所在地區的 GS1 網站](https://www.gs1.org/standards/get-barcodes)。
* **不要重複使用產品 ID：**請勿讓多個產品共用 GTIN。單一產品只應對應至單一 GTIN，重複使用 GTIN 會導致市集目錄資料過時或不一致，因而造成混淆。如果從未經授權的來源取得產品 ID (例如其他公司破產清算程序中販賣的 ID)，等於讓您的產品識別資訊建立在原先註冊的產品或公司之上，徒增風險。
* **客製化產品請遵循相應的產品 ID 最佳做法：**在特定情況下 (例如您的產品為手工、客製化或一次性產品)，品牌可採用自有方式來解決產品識別的問題，也就是使用專屬的庫存計量單位編號 (SKU) 或製造商零件編號 (MPN) 來管理產品。這類做法的重點在於，製造商的管理原則必須以專屬性、可供驗證和全球通用等三項特性為基礎，確保能受益於採用產品 ID 制度的優勢。

## 適用於零售商和第三方賣方的相關提示

零售商必須確保網站提供的產品識別資訊正確無誤。除了 [GTIN 的通用規範](https://support.google.com/merchants/answer/160161?hl=zh-tw)之外，Google 也建議您遵循下列規範：

* **提交優質的產品資料：**請透過[產品動態饋給](https://support.google.com/merchants/answer/9455788?hl=zh-tw)提交結構化資料給 Google，或在網站中加入[結構化資料標記](https://developers.google.com/search/docs/appearance/structured-data/product?hl=zh-tw)。
* **優先提供 GTIN：**只要販售的產品擁有 GTIN，零售商就必須提供 GTIN。您可以透過產品動態饋給或網頁上的結構化資料兩種管道提供 GTIN。如果產品沒有 GTIN，零售商和第三方賣方就需要仰賴品牌和製造商的零件編號來識別產品。
* **使用有效的專屬 GTIN：**請勿將既有的 GTIN 用於新產品。零售商不得自行編造 GTIN；除非零售商同時為產品的製造商，否則也不應自行向 GS1 註冊 GTIN。

## 適用於線上發布商的相關提示

發布商在建立內容 (例如評論產品或分享特定產品的最新優惠) 時，務必正確指明評論所提及的產品。這樣使用者在 Google 搜尋產品時，才能看到這些評論。Google 建議遵循下列規範：

* **使用精確無誤的產品名稱：**發布者在網頁上提及產品時應使用精確無誤的產品名稱，以便使用者和搜尋引擎準確瞭解參照的產品。
* **採用結構化資料：**建議您在評論產品時加入 GTIN 在內的各項[結構化資料](https://developers.google.com/search/docs/appearance/structured-data/product?hl=zh-tw)，這有助於搜尋引擎更清楚地判斷該針對哪些查詢顯示您的網頁。
* **使用有效的專屬 GTIN：**切勿為了在內容中提供 GTIN 而自行編造識別碼，也不要「借用」其他產品的 GTIN。

產品識別在商務交易中至關重要，能夠確保商家和消費者準確瞭解產品的來源和獨特性。這對網站和 Google 搜尋來說也是一樣，正確瞭解產品資訊有助於我們在適當的時機，將合適的產品呈現給適合的使用者。

如果您有任何疑問或意見，歡迎前往[搜尋中心說明論壇](https://support.google.com/webmasters/go/community?hl=zh-tw)提出，或是透過[其他管道](https://developers.google.com/search/help?hl=zh-tw)與我們聯絡。

發文者：Google 購物團隊產品資料產品經理 Randy Rockinson
