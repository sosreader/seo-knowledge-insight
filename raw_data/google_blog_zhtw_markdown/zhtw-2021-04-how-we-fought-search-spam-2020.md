# Google 於 2020 年處理垃圾搜尋結果的成效
- **發佈日期**: 2021-04-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/04/how-we-fought-search-spam-2020?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 4 月 29 日星期四

![Googlebot 和好友「自動尋檢程式」正在閱讀 2020 年網路垃圾內容處置報告](https://developers.google.com/static/search/blog/images/webspamreport2020/WebspamReport2020_1.png?hl=zh-tw)

Google 搜尋是一款功能強大的工具，可協助您在開放的網路環境中找到實用資訊。然而，並非所有的網頁都立意良善。許多網頁會明目張膽地欺騙使用者，而這正是我們每天面對的挑戰。為了確保您的安全，同時避免搜尋體驗受到干擾性內容和惡意行為侵擾，Google 搜尋於 2020 年投注許多心力，締造了不少創舉。

## 以更聰明的方式打擊垃圾內容

自 Google 搜尋問世以來，我們就一直在[打擊垃圾內容](https://www.youtube.com/watch?v=oJixNEmrwFU&hl=zh-tw)，而近年來人工智慧 (AI) 的進步也帶來前所未有的可能性，讓我們能徹底革新舊有方式。

透過結合對垃圾內容的深入瞭解以及 AI，我們在去年建立了 Google 杜絕垃圾內容的 AI 技術，在掌握已知和最新的垃圾內容趨勢方面，都發揮了驚人的成效。舉例來說，我們致力於打擊內含自動產生和剪輯內容的網站，相較於幾年前總量減少超過 80%。

然而在 2020 年，儘管我們改良了偵測技術，讓成效提升超過 50%，還[從搜尋結果中移除了大部分遭入侵的垃圾內容](https://www.youtube.com/watch?v=TnhKznlJfTM&hl=zh-tw)，這類內容仍舊相當猖獗，而有安全漏洞的網站數量也居高不下。

這不是我們單槍匹馬就能解決的問題。即使我們能偵測並防範所有垃圾內容，駭客還是會不斷利用安全性漏洞，除非我們將這類漏洞一一排除。不過，網站擁有者卻可以採取適當的安全措施來保護網站：比起將遭入侵的網站復原，直接防範駭客入侵網站是較為簡便的方式。您可以透過 Google 提供的資源瞭解[有心人士入侵網站的常見方式](https://developers.google.com/web/fundamentals/security/hacked/top_ways_websites_get_hacked_by_spammers?hl=zh-tw)，以及如何[使用 Search Console](https://developers.google.com/web/fundamentals/security/hacked/use_search_console?hl=zh-tw) 檢查[網站是否遭到入侵](https://developers.google.com/web/fundamentals/security/hacked?hl=zh-tw)。請確實詳閱以上內容，與我們一同打造安全的上網環境！

去年發生很多大事，包括全球爆發疫情，這促使我們投注大量心力，針對與這些重要主題相關的數十億筆搜尋結果提供額外保障。舉例來說，尋找附近的 COVID 檢測地點時，您不用擔心會看到胡言亂語的垃圾內容，也不用擔憂系統可能會將您重新導向網路詐騙網站。除了清除垃圾內容外，我們也與其他幾個搜尋團隊合作，確保您能在最關鍵的時空環境下，獲得最新且最優質的資訊。

## 避免接觸到垃圾內容

系統在 Google 上顯示一系列搜尋結果前，其實[進行了許多幕後工作](https://www.google.com/search/howsearchworks/?hl=zh-tw)。我們每天都會尋找、檢索數十億個網頁並為其建立索引，而這些網頁中有許多垃圾內容；事實上，我們每天都會發現 400 億個垃圾資訊網頁。下文將說明我們如何確保您在搜尋實用資訊時，不會受到垃圾內容干擾。

![Google 如何在每個步驟防範垃圾內容](https://developers.google.com/static/search/blog/images/webspamreport2020/WebspamReport2020_EverySteps.png?hl=zh-tw)

這張圖表說明了我們防範垃圾內容的方式。

首先，我們的系統會在檢索網頁或其他內容時偵測垃圾內容。所謂檢索，是指自動系統造訪內容的情況，此時系統會考慮將內容納入用來提供搜尋結果的索引之中。部分被偵測為垃圾資訊的內容則不會加進索引。

對於透過 Sitemap 和 [Search Console](https://search.google.com/search-console/about?hl=zh-tw) 找到的內容，這些系統也會執行上述工作。舉例來說，Search Console 提供[要求建立索引](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl?hl=zh-tw)功能，方便創作者通知我們有新網頁需要盡快新增到索引中。我們的觀察顯示，垃圾內容發布者會入侵含有安全漏洞的網站，假裝是這些網站的擁有者，然後在 Search Console 中驗證他們的身分，並使用這項工具要求 Google 檢索他們建立的眾多垃圾資訊網頁，最後將其編入索引。但幸虧有 AI 協助，我們得以找出可疑的驗證作業，防止垃圾內容網址透過上述方法進入索引當中。

接下來，我們的系統會對索引涵蓋的內容進行分析。當您執行搜尋時，系統會重新檢查相符的內容是否可能含有垃圾內容。如果是的話，這些內容就不會顯示在熱門搜尋結果中。我們也會使用這類資訊來改善系統，避免將這些垃圾內容全數編入索引。

結果顯示，多虧了這套由 AI 輔助的自動化系統，使用者在熱門搜尋結果中實際看到的垃圾內容可說是少之又少。我們預估透過這些自動化系統，在經由搜尋而造訪網站的訪客中，有超過 99% 的人會完全不受垃圾內容干擾。至於剩下的極少部分，我們的團隊會採取[專人介入處理](https://support.google.com/webmasters/answer/9044175?hl=zh-tw)，並善用這些處理經驗進一步改善自動化系統。

## 保護您不受垃圾內容以外的威脅干擾

![除了垃圾內容以外，Googlebot 和好友也會保護您不受其他威脅干擾](https://developers.google.com/static/search/blog/images/webspamreport2020/WebspamReport2020_2.png?hl=zh-tw)

除了垃圾內容外，我們也在 2020 年投入更多心力，協助防範其他類型的濫用行為，這當中有很多都可能造成重大財務和人身傷害。

我們在 2020 年大幅改善服務涵蓋範圍，保護更多使用者不受線上詐騙和詐欺侵害。線上詐騙手法千變萬化，比起傳統的網路垃圾內容，可能會以更多樣的方式帶來負面影響。舉例來說，許多詐騙份子會假借熱門服務和產品的名義提供客戶服務的電話號碼，為的只是要誘騙使用者透過銀行轉帳或禮物卡付款給他們。這類詐騙行為通常稱為「客戶服務詐騙」或「技術支援詐騙」，目前已有[數十萬名使用者](https://www.ftc.gov/system/files/documents/reports/consumer-sentinel-network-data-book-2020/csn_annual_data_book_2020.pdf)檢舉這個手法。不論是以上哪種方式，使用者都可能因詐騙份子而損失[數百美元](https://www.ftc.gov/news-events/blogs/data-spotlight/2019/03/older-adults-hardest-hit-tech-support-scams)的錢財。

![搜尋結果中的客戶服務詐騙示例](https://developers.google.com/static/search/blog/images/webspamreport2020/WebspamReport2020_ScamExample.png?hl=zh-tw)
