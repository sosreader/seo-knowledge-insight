# 在 Google 搜尋中醒目顯示您的客戶服務管道
- **發佈日期**: 2021-07-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/07/customer-support?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 7 月 7 日星期三

為了滿足客戶經常要尋找商家聯絡方式的需求，Google 致力於透過[各種方式](https://developers.google.com/search/docs/appearance/search-result-features?hl=zh-tw)提供這方面的優質資訊。如果您想幫助我們達成這個目標，歡迎採取下列做法，確保我們為您的商家或服務顯示最正確的資訊。

另一方面，這些最佳做法有助於確保使用者直接聯絡到商家本身，而不是宣稱與商家存在未能證實授權關係的第三方。Google 也能藉此為使用者顯示正確的支援資訊，例如列出公司的客服電話，而不是提供一般的總機號碼。

## 在網站中新增聯絡資訊頁面或支援頁面

請務必提供能讓訪客和 Googlebot 輕鬆找到的聯絡資訊頁面或支援頁面。舉例來說，在首頁底部或容易找到的選單中提供聯絡資訊頁面的連結，應該就能為訪客帶來幫助。Googlebot 通常可以在[檢索網站及建立網站索引](https://developers.google.com/search/docs/fundamentals/get-started?hl=zh-tw#crawling_indexing)時找到這類頁面。此外，您也可以在 [Sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview?hl=zh-tw) 納入聯絡頁面。

## 列出所有支援方式

在支援頁面或聯絡資訊頁面上，請提供您所有支援管道的完整資訊，例如電子郵件、即時通訊、社群媒體、電話等等。您可以考量自己的目標對象，以合適的方式說明這些資訊。

## 考慮提供可以查詢支援資訊的電話號碼

如果您沒有電話支援服務，不妨準備一組查詢電話號碼，讓使用者打進去後就能取得其他支援選項的資訊。這樣一來，Google 就能為認為有電話支援服務的使用者提供您的官方號碼，同時避免顯示聲稱提供官方支援服務的第三方號碼。

## 明確指出有權提供支援服務的單位

如果您授權讓第三方提供支援服務，建議您在支援頁面列出這些單位。這樣一來，客戶就能知道這些單位的支援服務是合法的，可以安心向他們尋求協助。如果您未與第三方合作，也請務必清楚說明，萬一有人宣稱與您合作，您的客戶就不會上當受騙。

## 精選摘要和 `nosnippet` 的應用

如果您已建立完善的支援頁面或聯絡資訊頁面，就能有效增加[精選摘要](https://support.google.com/websearch/answer/9351707?hl=zh-tw)顯示實用資訊的機會。雖然我們設法在精選摘要中顯示最相關的內容，但是呈現的效果不一定盡如人意。如果您不希望精選摘要顯示網站上的支援相關資訊，請使用 [`data-nosnippet` 標記](https://developers.google.com/search/docs/appearance/featured-snippets?hl=zh-tw#block-both)告知不希望顯示這些資訊。

## 設定 Google 商家檔案

如果您是當地商家，請務必建立 [Google 商家檔案](https://www.google.com/business/business-profile/?hl=zh-tw)並進行[編輯](https://support.google.com/business/answer/3039617?hl=zh-tw)，確保當中傳達優質的資訊。此外，也建議您[使用結構化資料提供當地商家資訊](https://developers.google.com/search/docs/appearance/structured-data/local-business?hl=zh-tw)。

如有任何問題，歡迎前往 [Google 搜尋中心社群](https://support.google.com/webmasters/community?hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 尋求協助。

發文者：搜尋公關 [Danny Sullivan](https://mastodon.social/@searchliaison)
