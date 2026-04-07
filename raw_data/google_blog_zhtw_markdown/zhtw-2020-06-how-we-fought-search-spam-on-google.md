# Google 處理垃圾搜尋結果的成效 - 2019 年網路垃圾內容處置報告透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2020-06-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/06/how-we-fought-search-spam-on-google?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 6 月 9 日，星期二

![Googlebot 呈現 2019 年網路垃圾內容處置報告](https://developers.google.com/static/search/blog/images/web-spam-report-2019.png?hl=zh-tw)

Google 重視使用者的每一筆搜尋。因此，每當您利用 Google 搜尋找尋實用的相關資訊時，我們都希望盡可能確保您找到最優質的結果，這也是我們一直履行的承諾。

遺憾的是，網路上存在一些我們稱之為「垃圾內容」的干擾行為與內容，這些垃圾內容會導致使用體驗大打折扣，妨礙使用者尋找實用資訊。我們有多個團隊致力於防止搜尋結果中出現垃圾內容，努力不懈地在與垃圾內容發布者的對抗中制敵機先。與此同時，我們將繼續與網站管理員交流，協助他們遵循最佳做法，在 Google 搜尋中獲得理想表現，進而在開放網路中提供優質內容。

我們將在下文中回顧過去一年的表現，大致說明我們在 2019 年是如何防堵 Google 搜尋中的垃圾內容，以及為網站管理員社群提供的支援。

## 大規模防堵垃圾內容

我們的索引系統收錄了數千億個網頁，每天都會提供數十億次查詢服務，所以免不了有層出不窮的不肖人士企圖操控搜尋排名。事實上據我們觀察，**我們每天都會找到超過 250 億個垃圾資訊網頁**。這個驚人的數字顯示出垃圾內容發布者會長期持續大規模地在網路上散布垃圾內容。對此，我們會慎重以待，盡可能確保減少您在搜尋結果中看到的垃圾網頁。在我們的努力下，現在當使用者經由我們的搜尋結果造訪網頁時，已經有超過 99% 的機率不會受到垃圾內容干擾。

## 去年至今的成就

我們在 2018 年的報告中提到過，[使用者自製垃圾內容](https://developers.google.com/search/docs/advanced/guidelines/user-gen-spam?hl=zh-tw)的數量已減少 80%。令人高興的是，這類濫用行為的數量在 2019 年並未增加。垃圾內容連結依然是很常見的一種垃圾內容形式，但我們的團隊成功在 2019 年限制了這類垃圾內容的影響範圍。我們的系統攔截了超過 90% 的垃圾連結，同時削弱了付費連結或連結交換等手法的效果。

雖然駭客攻擊帶來的垃圾內容仍然很常見且不易解決，不過影響程度較前幾年已更為趨緩。我們仍持續在開發解決方案，希望能提高對這類內容的偵測效率、迅速通知受影響的網站管理員和平台，並[協助他們修復遭到入侵的網站](https://developers.google.com/web/fundamentals/security/hacked?hl=zh-tw)。

## 垃圾內容趨勢

我們在 2019 年的首要任務之一，就是利用機器學習系統改進杜絕垃圾內容的措施。我們的機器學習解決方案結合了成熟且歷經時間檢驗的人工強制處理措施，能有效協助辨識垃圾搜尋結果並防止使用者受到這類干擾。

過去幾年，我們觀察到有越來越多垃圾網站含有[自動產生的內容](https://developers.google.com/search/docs/advanced/guidelines/auto-gen-content?hl=zh-tw)和[剪輯內容](https://developers.google.com/search/docs/advanced/guidelines/scraped-content?hl=zh-tw)，而且多有令搜尋者不悅或危害搜尋者安全的行為，比如假按鈕、大量廣告、可疑的重新導向和惡意軟體。這類網站通常具有欺騙性，對使用者也沒有任何實際價值。與 2018 年相比，我們在 2019 年將這類垃圾內容對搜尋服務使用者的影響減少了超過 60%。

在提升垃圾內容攔截能力與效率的同時，我們也會持續努力減少帶來詐騙、詐欺等各種危害的網站。這類網站會偽裝成官方網站或具有公信力的網站來取信於使用者，導致他們因此洩漏個人機密資訊、損失錢財或使裝置感染惡意軟體，情況屢見不鮮。我們一直密切關注容易引來詐騙和詐欺的查詢，也持續努力在預防使用者受到這些垃圾內容手法的危害。

## 與網站管理員和開發人員攜手打造更美好的網路環境

在打擊垃圾內容方面，我們主要是仰賴自動化系統來偵測濫用行為，但這些系統並沒有無懈可擊到滴水不漏的地步。另外，任何 Google 搜尋使用者也都可以[檢舉搜尋到的垃圾內容](https://developers.google.com/search/docs/advanced/guidelines/report-spam?hl=zh-tw)、[網路詐騙](https://safebrowsing.google.com/safebrowsing/report_phish/?hl=zh-tw)或[惡意軟體](https://www.google.com/safebrowsing/report_badware/?hl=zh-tw)，協助我們抵禦垃圾內容和其他問題。我們在 2019 年收到了將近 23 萬次的垃圾搜尋結果檢舉，並成功對其中的 82% 採取了行動。我們衷心感謝您提出的所有檢舉，也感謝您協助我們維護安全的搜尋環境！

我們在收到檢舉或發現可疑內容時會怎麼做呢？一旦我們偵測到網站出現異常，當務之急便是通知網站管理員。為了讓網站管理員知道他們的網站在搜尋結果中的呈現方式可能受到問題影響，並提供一些切實可行的改進建議，我們在 2019 年總共寄出了超過 9,000 萬封訊息，當中約有 430 萬封訊息是關於違反《網站管理員指南》而遭到[專人介入處理](https://support.google.com/webmasters/answer/9044175?hl=zh-tw)的情況。

此外，我們也不斷想方設法為網站擁有者提供更妥善的協助，在 2019 年採取了許多改善通知效率的措施，比如推出[新版 Search Console 訊息](https://developers.google.com/search/blog/2019/12/search-console-messages?hl=zh-tw)、[WordPress 網站專用的 Site Kit](https://developers.google.com/search/blog/2019/10/site-kit-is-now-available-for-all?hl=zh-tw) 以及[新版 Search Console 中的 DNS 自動驗證](https://developers.google.com/search/blog/2019/09/auto-dns-verification?hl=zh-tw)。我們希望這些措施能讓網站管理員以更便利的方式驗證網站，並持續發揮作用；也希望網站管理員可以藉此快速掌握最新動態，更精準有效率地解決垃圾內容問題或駭客問題。

在致力於清理垃圾內容的同時，我們也沒忘記跟上網路發展，重新[調整了對 `"nofollow"` 連結的定位](https://developers.google.com/search/blog/2019/09/evolving-nofollow-new-ways-to-identify?hl=zh-tw)。如今，原本是為了防堵垃圾留言及標示贊助商連結所推出的 `"nofollow"` 屬性已有長足進步。然而我們不想止步於此，如同我們打擊垃圾內容的方式會不斷進步，我們認為現在正是讓網路進一步發展的時刻，因此推出了 `rel="sponsored"` 和 `rel="ugc"` 這兩種新的連結屬性，讓網站管理員能夠以更多方式對 Google 搜尋指出特定連結的性質。如今，這兩種屬性和 `rel="nofollow"` 網站都已成為我們處理網站排名的依據。對於這些新的 rel 屬性能受到世界各地網站管理員的接受與採用，我們著實興奮不已！

## 參與社群互動

一如既往，我們很珍惜去年與全球網站管理員交流的每個機會，能夠協助他們改善搜尋排名並獲得意見回饋，同樣使我們獲益良多。Google 在全球許多城市舉辦了超過 150 場的線上諮詢會和其他線上與線下活動，目標對象涵蓋各種群體，包括搜尋引擎最佳化 (SEO) 專員、開發人員、線上行銷人員和業主。在這些活動中，我們很高興看到[各界人士踴躍參與 Webmaster Conference](https://developers.google.com/search/blog/2019/09/join-us-at-webmaster-conference-in?hl=zh-tw)。這些 Webmaster Conference 活動以 12 種語言舉行，場地橫跨全球 15 個國家的 35 處地點，也曾在山景城首次以產品高峰會的形式舉辦。雖然我們目前還無法舉辦現場活動，但希望未來能多多舉行這類[活動](https://developers.google.com/search/events?hl=zh-tw)和線上活動。

[網站管理員產品討論社群](https://g.co/webmasterforum)也持續在為網站管理員提供解決方案和實用秘訣，2019 年總計增加了 3 萬多筆以十幾種語言發文的會話串。另外，為了確保您的問題都能獲得解答，我們也在 YouTube [推出了 #AskGoogleWebmasters](https://developers.google.com/search/blog/2019/08/you-askgooglewebmasters-we-answer?hl=zh-tw) 等系列影片 (例如《[破解搜尋引擎最佳化 (SEO) 的迷思](https://developers.google.com/search/blog/2019/06/a-new-series-on-seo-for-web-developers?hl=zh-tw)》)。

我們知道改善網路環境還有很長的路要走，也希望來年能繼續與您攜手共進。因此，請一定要關注我們的 [Twitter](https://twitter.com/googlesearchc)、[YouTube](https://www.youtube.com/channel/UCWf2ZlNsCGDS89VBF_awNvA?hl=zh-tw)、[網誌](https://developers.google.com/search/blog?hl=zh-tw)、[產品討論社群](https://support.google.com/webmasters/community?hl=zh-tw)，或是親身參與一場離您較近的[會議](https://developers.google.com/search/events?hl=zh-tw)，我們期待與您面對面交流！

![一張顯示人物互相擊掌的卡通圖片](https://developers.google.com/static/search/blog/images/web-spam-report-2019-footer.png?hl=zh-tw)

發文者：Google 搜尋關係團隊成員 [Cherry Prommawin](https://www.linkedin.com/in/cherry-prom/) 與 Google 搜尋品質分析人員 [Duy Nguyen](https://developers.google.com/search/blog/authors/duy-nguyen?hl=zh-tw)
