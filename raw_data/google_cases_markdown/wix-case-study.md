# Wix 如何透過 Google API 將統計資料和功能直接整合到 Wix UI 中，為使用者產生價值
- **發佈日期**: 
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/case-studies/wix-case-study?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-case-studies
---
# Wix 如何透過 Google API 將統計資料和功能直接整合到 Wix UI 中，為使用者產生價值

發布日期：2024 年 2 月 5 日

## 挑戰

Wix 為全球希望建立專業網站，並且打造網路形象的超過 2.5 億名使用者提供了一個平台。Wix 希望能藉由在 [Wix SEO 生態系統](https://www.wix.com/seo) (包括 [Wix Studio](https://www.wix.com/studio/marketing/seo)) 中整合 Google 工具，為使用者創造更多價值，讓從建立索引到產生數據分析報表的使用者歷程變得更加輕鬆豐富。

## 完成事項

在 2022 年和 2023 年期間，Wix 與 Google 合作，定義哪些 Google 統計資料和功能符合 Wix 網站擁有者的需求，然後諮詢 Google 團隊，使用可從 Google 的 API (例如 [Search Console API](https://developers.google.com/webmaster-tools?hl=zh-tw) 和 [Site Verification API](https://developers.google.com/site-verification?hl=zh-tw)) 公開取得的資料，製作了多份報表。這些報表收錄了 Google 產品的統計資料和功能，因此 Wix 選擇這些報表，並將其與 Wix 資訊結合，放在 Wix UI 中最能讓使用者一眼發現的位置。

為了盡可能讓大多數使用者輕鬆存取這些整合內容，Wix 決定針對不同使用者專業程度，導入一系列工具：

* [透過 Search Console 整合功能提交 Sitemap](#sitemaps)
* [Wix 網站檢查工具](#site-inspection)
* [Wix 數據分析報表](#analytics)

### 透過 Search Console 整合功能提交 Sitemap

Wix 會使用 [Site Verification API](https://developers.google.com/site-verification?hl=zh-tw) 和 [Search Console API](https://developers.google.com/webmaster-tools?hl=zh-tw) 建構相關功能，自動驗證網站擁有權，然後透過 Wix 資訊主頁，將該網站的 Sitemap 提交給 Search Console 驗證網域擁有權是所有 CMS 整合機制的基本步驟。

![Wix 將網站連結至 Search Console](https://developers.google.com/static/search/case-studies/images/wix-1.png?hl=zh-tw)
![授權 Wix 將網站連結至 Search Console](https://developers.google.com/static/search/case-studies/images/wix-2.png?hl=zh-tw)

### Wix 網站檢查工具

Wix 運用 Google 的 [URL Inspection API](https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect?hl=zh-tw) 將使用者的網頁傳送至 Google 的 API，直接在 Wix 資訊主頁中追蹤網站的索引問題，以及檢查使用者的網頁。這項整合功能會檢查特定網頁的建立索引狀態 (包括任何索引建立錯誤)、並且執行匯總作業與其他工作。這樣一來，Wix 使用者就能大致瞭解網站的健康狀態，並取得必要的修正資訊，確保 Google 能為網站內容建立索引。

![Wix 的網站檢查工具](https://developers.google.com/static/search/case-studies/images/wix-3.png?hl=zh-tw)

### Wix 數據分析報表

Wix 利用 [Search Console API 的報表功能](https://developers.google.com/webmaster-tools/v1/searchanalytics?hl=zh-tw)製作了 4 份新的報表，透過整合式 SEO 報表，協助使用者取得訪客與自家網站互動情形的深入分析詳細資料。Wix 使用者可以直接在 Wix 資訊主頁中追蹤點擊次數、曝光次數，以及流量與主要查詢的變化。

![顯示 Google 搜尋資料的 Wix 數據分析報表](https://developers.google.com/static/search/case-studies/images/wix-4.png?hl=zh-tw)

## 成果

將 Google 工具整合至 Wix 生態系統，已證實能為使用者帶來重大變革。

目前為止，目前已有超過 200 萬個 Wix 網站與自家的 Search Console 帳戶連結，並透過新的整合功能將 Sitemap 提交給 Google。此外，他們也定期使用網站檢查和數據分析報表等新功能，以排解建立索引錯誤、修正問題，並取得深入分析，瞭解這些功能帶給成效的變化。Wix 發現，這些使用者在透過 Wix 連結至自家 Search Console 帳戶後一年 (2022 年 7 月至 2023 年 7 月) 內，與連結前相比，平均流量提升了 15%。此外，某些使用者未將自家網站連結至 Search Console，因此無法取得新功能，也無法瞭解自家網站在搜尋結果中的成效。相較於這些使用者，已連結帳戶的類似使用者其 GPV (Gross Product Value，Wix 使用者在特定時間透過自家網站賺取的收益額) 提升了 15%。

15%

Wix 網站在使用新功能後
平均流量增幅

24%

Wix 電子商務網站在使用新功能後
每月 GPV 增幅

在一年 (2022 年 7 月至 2023 年 7 月) 內，使用新功能的 Wix 電子商務網站，每月 GPV 提高了 24%。Wix 發現，這些使用者在他們的 SEO 歷程中，運用了 Google 和 Wix 提供的其他工具，協助他們確定及修正策略。

此外，Wix 網站檢查工具也帶來了正面影響。Wix 報告顯示，在一年當中 (2022 年 7 月至 2023 年 7 月)，首次使用工具的網站平均流量增加 5%，平均 GPV 增加 16%這些結果顯示，能夠簡化使用者的網站監控程序，幫助他們更有效率地追蹤及修正影響搜尋引擎排名的問題。

Wix 的 SEO 主管 Nati Elimelech 表示：
*「將 Google 的 API 整合至 Wix 中，為我們的使用者帶來重大變革。不但能用於數據分析，還可以簡化整個網站的建立和最佳化程序。無論使用者的專業程度為何，他們都能在網路上取得成功，而這也確實反映出了整合機制的強大之處。這不僅僅是技術升級，更能讓所有人輕鬆取得實用的進階 SEO 工具，並且從中獲益。」*

如果您是 CMS 且有意與我們合作，請[填寫這份表單](https://forms.gle/taGyhNnAczn3VgGDA)，或透過[社群媒體](https://twitter.com/googlesearchc)與我們聯絡。
