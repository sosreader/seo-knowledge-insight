# 防範網站的部分內容遭到垃圾內容濫用
- **發佈日期**: 2021-05-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/05/prevent-portions-of-site-from-spam?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 5 月 26 日星期三

身為網站擁有者，您可能會提供數種管道供使用者進行互動，例如論壇、留言板、社群媒體平台、檔案上傳工具、代管服務或內部搜尋服務等。這類服務能讓使用者建立帳戶，以便在網站上張貼內容、上傳檔案或進行搜尋。遺憾的是，垃圾內容發布者經常利用這些服務，產生數百個無法為網路帶來任何附加價值或價值極為低落的垃圾網頁。在這種情況下，依據 [Google 網站管理員指南](https://developers.google.com/search/docs/essentials?hl=zh-tw)中載明的原則，Google 可能會對受影響的網頁採取專人介入處理。以下舉幾個例子說明：

![遭濫用的論壇/留言板](https://developers.google.com/static/search/blog/images/abused-forum.png?hl=zh-tw "遭濫用的論壇/留言板")
![遭濫用的檔案上傳工具以及垃圾 PDF 檔案](https://developers.google.com/static/search/blog/images/abused-file-uploader.png?hl=zh-tw "遭濫用的檔案上傳工具以及垃圾 PDF 檔案")
![遭濫用的代管服務](https://developers.google.com/static/search/blog/images/abused-free-hosting.png?hl=zh-tw "遭濫用的代管服務")
![遭濫用的內部搜尋結果](https://developers.google.com/static/search/blog/images/abused-internal-search-results.png?hl=zh-tw "遭濫用的內部搜尋結果")

這類垃圾內容可能會在多種層面上對您的網站和使用者造成損害：

* 因為網站某部分出現劣質內容，而影響整個網站的排名。
* 垃圾內容可能將使用者引導至無用內容或有害內容 (例如含有惡意軟體或網路詐騙行為的網站)，進而降低網站的信譽。
* 不相關內容帶來的未預期流量會使網站的速度變慢，並增加代管費用。
* 如果網頁中充斥第三方產生的垃圾內容，為了維護搜尋結果的品質，Google 可能會移除該網頁的搜尋結果或降低其排名。

我們將在這篇網誌文章中提供一些提示，協助防範垃圾內容發布者濫用您的網站。

## 封鎖自動建立帳戶的機制

如果您的網站能讓使用者建立帳戶，建議在建立機制中採用 Google 的 [CAPTCHA](https://www.google.com/recaptcha/about/?hl=zh-tw) 服務或類似的驗證工具，例如 [Securimage](https://www.phpcaptcha.org/) 或 [Jcaptcha](https://jcaptcha.sourceforge.net/)。這麼做可限制只有真人使用者能夠進行註冊，防止自動化指令碼在網站的公開平台上產生帳戶和內容。

您可要求新使用者在註冊新帳戶時必須驗證真實的電子郵件地址，藉此防止許多發布垃圾內容的漫遊器自動建立帳戶。此外，您也可以設定篩選器來封鎖可疑的電子郵件地址，或封鎖來自不信任電子郵件服務的地址。

## 開啟管理功能

建議針對建立評論和建立個人資料啟用管理功能，規定使用者必須擁有一定信譽才能張貼連結。請盡可能變更您的設定，禁止使用者張貼匿名文章，並指定新使用者發布的文章必須通過審核才能公開顯示。

## 監控網站的垃圾內容並清理問題

請在 [Search Console](https://support.google.com/webmasters/answer/9128669?hl=zh-tw) 中註冊並驗證網站的擁有權。您可以查看[安全性問題報告](https://support.google.com/webmasters/answer/9044101?hl=zh-tw)和[專人介入處理報告](https://support.google.com/webmasters/answer/9044175?hl=zh-tw)，瞭解 Google 是否偵測到任何問題，也可以透過「訊息」面板進一步瞭解詳情。

![Search Console 訊息通知網站出現濫發第三方垃圾內容問題](https://developers.google.com/static/search/blog/images/third-party-spam.png?hl=zh-tw)
