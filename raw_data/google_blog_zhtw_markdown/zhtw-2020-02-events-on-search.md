# 如何在 Google 搜尋中呈現您的活動透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2020-02-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/02/events-on-search?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 2 月 25 日，星期二

隨著時間邁入 2020 年，大家都開始規劃今年的行程。無論您要舉行任何類型的活動，都可以透過 Google 的活動搜尋服務協助使用者找到您的活動。

打算舉辦演唱會或工作坊嗎？只要加入活動標記，即可讓在搜尋「本週末的演唱會」、「附近的工作坊」等關鍵字的使用者發現您的活動。另外，使用者也會在搜尋體育館、當地酒吧等場所時發現您的活動。活動資訊可能會出現在特定場所的[知識面板](https://support.google.com/knowledgepanel/answer/9163198?hl=zh-tw)中，方便使用者進一步瞭解相應地點的情況。

![在 Google 搜尋中點選活動的螢幕截圖](https://developers.google.com/static/search/blog/images/import/b6558c62b1e66641a72e63b631e995c9.png?hl=zh-tw)
![活動到達網頁示例的螢幕截圖](https://developers.google.com/static/search/blog/images/import/2749ea50703c0e53df593ce0820e7454.png?hl=zh-tw)

## 支援新的地區和語言

Google 最近已在[德國](https://developers.google.com/search/blog/2019/12/events-launching-germany-spain?hl=de)和[西班牙](https://developers.google.com/search/blog/2019/12/events-launching-germany-spain?hl=es)推出活動搜尋服務，目前服務範圍共涵蓋九個國家/地區。如需完整的服務適用區域清單，請參閱[支援的區域和語言](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#region-availability)清單。

## 如何讓 Google 顯示您的活動

您可以透過下列三種方法讓 Google 顯示您的活動：

* 如果您在第三方網站 (例如售票網站或社交平台) 上張貼活動訊息，請確認對方是否已採用 Google 的活動搜尋服務，比如搜尋該平台顯示的熱門活動，看看是否出現相應的活動資訊。如果對方已與 Google 進行整合，您就能繼續在該第三方網站上張貼您的活動訊息。
* 如果您使用 WordPress 等 CMS，而且無法存取自身的 HTML，請確認該 CMS 是否提供可為網站添加結構化資料的外掛程式。或者，您也可以使用[資料螢光筆](https://support.google.com/webmasters/answer/2774099?hl=zh-tw)向 Google 告知您的活動資訊，這樣就無須編輯網站的 HTML。
* 如果您有把握自行編輯 HTML，可以[使用結構化資料直接與 Google 整合](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#integrate)。您將需要編輯活動網頁的 HTML。

## 遵循最佳做法

如果您已實作活動結構化資料，建議您檢查這些資料是否符合相關指南的要求。請特別注意以下事項：

* 務必加入[開發人員指南](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#datatypes)所列的必要屬性和建議屬性。
* 務必根據[指南](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw#guidelines)提供優質的活動詳細資料，例如利用說明欄位更詳細地介紹活動，而不是重複名稱、日期、地點等屬性，或醒目顯示其他的網站功能。
* 運用[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)來[測試及預覽結構化資料](https://support.google.com/webmasters/answer/7445569?hl=zh-tw)。

## 監控活動的 Google 搜尋成效

您可以透過 Search Console 查看使用者與活動訊息的互動情況：

* 使用 Search Console 的[成效報表](https://support.google.com/webmasters/answer/7576553?hl=zh-tw)，查看搜尋結果中特定活動訊息的[活動資訊或詳細資料](https://support.google.com/webmasters/answer/7042828?hl=zh-tw#job)檢視畫面資料。您也可以使用 [Search Console API](https://developers.google.com/webmaster-tools/search-console-api-original/v3/how-tos/search_analytics?hl=zh-tw) 自動擷取這些結果。
* 使用 Search Console 的[複合式搜尋結果狀態報告](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)，瞭解 Google 能夠或無法讀取您網站中的哪些內容，以及排解複合式搜尋結果錯誤。

![Search Console 複合式搜尋結果報告](https://developers.google.com/static/search/blog/images/import/9eb547e5e453bb20b57f84b9be5f82ff.png?hl=zh-tw)

如有任何疑問，請造訪[網站管理員中心說明論壇](https://support.google.com/webmasters/community/?hl=zh-tw)。

發文者：產品經理 Emily Fifer
