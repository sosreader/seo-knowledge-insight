# 如何提供合格連結以及垃圾連結相關更新提醒
- **發佈日期**: 2021-07-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/07/link-tagging-and-link-spam-update?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 7 月 26 日，星期一

![Googlebot 與自動尋檢程式好友一起思考關於連結的問題](https://developers.google.com/static/search/blog/images/linkupdate/linkspam-blog-1.png?hl=zh-tw)

現今的網路創作者如果想透過網站和網誌營利，有多種方式可以選擇。不過，其中部分方式可能會產生連出連結，如果未經適度控制並正確加上註解，可能會違反我們的[品質指南](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw#link-spam)。在這篇文章中，我們想要分享如何處理可能屬於商業性質的連結，以及我們採取了哪些措施，以持續降低垃圾連結對搜尋結果的影響。

## 最佳做法

Google 能透過多種方式瞭解哪些內容可能對搜尋者有幫助，連結就是其中一種方式；只要是以正當方式獲得連結，就能為連結的網站帶來正面影響。最佳做法是避免採用任何違反[連結配置](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw#link-spam)的連結方式，尤其是連結到其他網站時，請務必[說明這些連出連結的性質](https://developers.google.com/search/docs/advanced/guidelines/qualify-outbound-links?hl=zh-tw)。以下提供一些具體規範，能協助網站擁有者管理付費連結、贊助商連結或其他屬於商業性質的連結。

## 聯盟連結

![什麼是聯盟連結](https://developers.google.com/static/search/blog/images/linkupdate/linkspam-blog-Affiliate.png?hl=zh-tw)

在網頁上發布聯盟連結 (例如產品評論和購物指南)，是網誌和發布者透過流量營利時的常見方式。一般來說，在網站上運用聯盟連結營利是可以接受的做法。我們會要求參與聯盟計畫的網站[利用 `rel="sponsored"` 說明自家網站與連結的關係](https://developers.google.com/search/docs/advanced/guidelines/qualify-outbound-links?hl=zh-tw)，無論是手動或動態建立的連結都必須提供這項資訊。

我們持續致力於[改善產品相關搜尋的排名，並獎勵優質內容](https://developers.google.com/search/blog/2021/04/product-reviews-update?hl=zh-tw)，一旦發現網站無法適當說明聯盟連結的性質，就可能會採取[專人介入處理](https://support.google.com/webmasters/answer/9044175?hl=zh-tw)，藉此防範這些連結影響搜尋結果，且系統也可能會透過演算法進行處置。無論是專人介入處理和演算法處置，都可能對網站在 Google 搜尋中的排名產生影響，因此請盡量避免可能導致網站遭到處置的做法。

## 贊助商文章和客座文章

![什麼是贊助商文章和客座文章](https://developers.google.com/static/search/blog/images/linkupdate/linkspam-blog-Sponsored.png?hl=zh-tw)

接受其他網站的贊助商文章和客座文章，是另一種能透過網站營利的常見方法。這類文章是由某個網站 (或以該網站的名義) 撰寫，然後再發布到其他網站上。依據過往的觀察，許多網站會為了獲得連結而發布[劣質的贊助商和客座文章廣告活動](https://developers.google.com/search/blog/2017/05/a-reminder-about-links-in-large-scale?hl=zh-tw)。

雖然在偵測和打擊這類[連結配置](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw#link-spam)方面我們已經獲得顯著的成效，但仍強烈建議網站擁有者為這些連結加上[適當的 rel 值](https://developers.google.com/search/docs/advanced/guidelines/qualify-outbound-links?hl=zh-tw)。與聯盟連結的處理方式類似，如果我們偵測到網站透過浮濫的贊助商文章和客座文章來發布或取得這類連結，且未加上適當的連結標記，我們可能會透過演算法進行處置，並採取專人介入處理。

## 改善系統以打擊垃圾連結

在過去二十年來，由於我們不斷改善排名系統和垃圾內容偵測系統，發布垃圾連結所能獲得的效果整體而言已大不如前。能有這樣的成果，也要感謝大多數網站遵守我們的指南規範，致力於打造具有絕佳使用者體驗的網站，並提供優質內容。不過，雖然成果豐碩，但仍有進步空間，特別是我們發現有的網站會為了操控排名而刻意建立垃圾連結，且時常試圖欺騙我們的系統。

為了持續改善搜尋結果的品質，我們今天將推出新的垃圾連結杜絕措施：「垃圾連結更新」。我們將在未來兩週內逐步推出這項演算法更新，找出多種語言中的垃圾連結並讓其失效，效果比以往更好，可偵測範圍也更廣。我們的演算法會重新評估垃圾連結，如果網站涉及採用這類連結，其搜尋結果排名將會受到影響。

跟之前一樣，網站擁有者應該確保網站上的連出和連入連結都遵守[連結最佳做法](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw#link-spam)。與其操控連結，專注於製作優質內容並改善使用者體驗更能獲得良好成效。別忘了，為連結加上合適的標記以提升網站知名度，並運用適當標記的聯盟連結來將網站流量轉換為收益。

如有任何疑問，歡迎前往 [Google 搜尋中心社群](https://support.google.com/webmasters/community?hl=zh-tw)與專家交流，或透過[各種公開管道](https://developers.google.com/search/help?hl=zh-tw)與我們聯絡。

發文者：Google 搜尋品質分析師 [Duy Nguyen](https://developers.google.com/search/blog/authors/duy-nguyen?hl=zh-tw)
