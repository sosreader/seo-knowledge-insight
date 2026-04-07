# 更新徵人啟事規範，為求職者提供更優質的搜尋結果透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2021-07-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/07/job-posting-updates?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 7 月 13 日，星期二

尋找工作的過程可能相當費時，而應徵結果也有可能徹底改變人生，因此我們相當重視求職者在 Google 搜尋的使用體驗，並將提供真實、即時且值得信賴的內容視為首要任務。

為了進一步瞭解使用者的想法，我們邀請全球數萬名求職者分享更多在線上應徵工作的經驗。根據這些意見回饋，我們才能找出有助於改善搜尋結果品質的共通主題，進而在今天宣布推出全新的[結構化資料屬性](https://developers.google.com/search/docs/appearance/structured-data/job-posting?hl=zh-tw#direct-apply)和[編輯內容政策](https://developers.google.com/search/docs/appearance/structured-data/job-posting?hl=zh-tw#editorial)。

## 全新 `directApply` 屬性

您可以選擇使用 [`directApply` 屬性](https://developers.google.com/search/docs/appearance/structured-data/job-posting?hl=zh-tw#direct-apply)，表明徵人啟事是否提供「直接應徵」功能。我們是透過使用者應徵工作時的操作來定義「直接應徵」功能；若網頁具備這種功能，就表示能為使用者提供簡單快速的應徵流程。

如果您的網站提供下列其中一項功能，就有可能提供直接應徵功能：

* 使用者能在您的網站上完成應徵流程。
* 使用者從 Google 到達您的網頁後，只要點選應徵按鈕並提供使用者資訊一次，就能完成應徵流程。

![符合定義的直接應徵流程插圖](https://developers.google.com/static/search/blog/images/direct-apply-illustrations.png?hl=zh-tw)

我們仍在努力將相關資訊整合至 Google，與此同時，這項屬性可能不會立刻對 Google 搜尋產生任何效果。

## 新增編輯內容政策

為確保使用者能理解您的內容，且便於應徵工作，我們針對 Google 搜尋上的徵人啟事新增了[編輯內容政策](https://developers.google.com/search/docs/appearance/structured-data/job-posting?hl=zh-tw#editorial)。這項政策涵蓋關於各方面的規範，包括妨礙理解的文字和圖片、過多的擾人廣告，或是對於徵人啟事沒有任何附加價值的內容。此外，徵人啟事也必須遵循基本的文法規則，例如使用正確用字。

本政策有助於改善搜尋結果品質及開發新的產品功能。

為了讓網站擁有者能有充裕的時間完成規定事項，新的編輯內容政策將於 2021 年 10 月 1 日生效。詳情請參閱[開發人員說明文件](https://developers.google.com/search/docs/appearance/structured-data/job-posting?hl=zh-tw#editorial)。

## 網站擁有者可在解決常見問題後提升求職者的信任度

我們的研究結果指出，您可以解決網站上涉及下列層面的問題，藉此提升求職者的信任度：

* **確認網站上沒有包含詐騙或垃圾資訊的徵人啟事**。這類徵人啟事並不代表實際的工作機會。請確保個別網頁只有一筆工作機會的標記，而且求職者確實能夠應徵這份工作。
* **務必提供優質的使用者體驗**。根據使用者的意見回饋，如果網站在非必要情況下索取使用者資訊、提供品質低落的網頁 (例如放送過多或妨礙理解的廣告)，以及/或者要求完成複雜的應徵程序 (例如多次重新導向)，就會對使用者體驗造成負面影響。使用者體驗不佳也會降低求職者完成應徵的比率。
* **移除過期的徵人啟事**。請勿將不再接受應徵的徵人啟事保持開啟狀態，因為求職者常會抱怨應徵後未收到僱主的回覆。從網站上移除工作機會時，請務必一併移除相關標記，或更新 [`validThrough`](https://developers.google.com/search/docs/appearance/structured-data/job-posting?hl=zh-tw#valid-through) 屬性。建議您使用 [Indexing API](https://developers.google.com/search/apis/indexing-api/v3/quickstart?hl=zh-tw) 將最新異動告知我們。如果在到達的網頁上發現過期的徵人啟事 (尤其是經過好幾次重新導向後)，求職者會感到非常失望。
* **確保徵人啟事列出實際日期**。使用者會以資訊即時性為依據，評估職缺是否開放應徵、獲得聘用的機會，以及職位的吸引力等等。切勿將舊的工作機會當成新的工作機會進行發布，也不得在徵人啟事內容沒有任何改變的情況下更新 [`DatePosted`](https://developers.google.com/search/docs/appearance/structured-data/job-posting?hl=zh-tw#date-posted) 屬性。
* **請勿在徵人啟事或標記中加入錯誤或誤導性資訊**，包括不實的薪資、工作地點/時間、聘僱類型或其他具體工作詳情。為避免這種狀況，請確認徵人啟事如實描述工作內容，並加上可準確表示相關資訊的標記。

我們會努力確保 Google 搜尋結果不僅值得信賴，還能為使用者提供優質的體驗。凡是旨在協助求職者尋找工作的網站，肯定都是和 Google 朝著相同的目標邁進。如有任何疑問或想法，歡迎透過 [Google 搜尋中心社群](https://support.google.com/webmasters/community?hl=zh-tw)或 [Twitter](https://twitter.com/googlesearchc) 與我們聯絡。

張貼者：Google 搜尋產品經理 Gilad Orly
