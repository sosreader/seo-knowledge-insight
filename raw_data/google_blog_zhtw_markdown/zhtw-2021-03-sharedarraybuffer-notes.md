# 關於 SharedArrayBuffer 物件郵件的說明
- **發佈日期**: 2021-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/03/sharedarraybuffer-notes?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 3 月 19 日，星期五

**2021 年 5 月 6 日更新**：Chrome 團隊原先預計在 Chrome 91 版中對電腦環境下的 `SharedArrayBuffer` 物件加以限制，但由於出現未預期的狀況，現已決定延後至 Chrome 92 版推出。

有些人可能已經從 Google Search Console 收到主旨為「`SharedArrayBuffers` 的新規定」的電子郵件。由於有人反映這封郵件的內容難以理解，因此我們想進一步深入分析相關問題，協助您決定接下來採取哪些步驟較為合適。
此外，我們也更新了[跨來源隔離的啟用指南](https://web.dev/articles/cross-origin-isolation-guide?hl=zh-tw)，納入更多詳細資訊。

## 為什麼我會收到上述郵件？

您先前會收到上述郵件，是因為當時系統偵測到您網站的 JavaScript 在使用 [`SharedArrayBuffer`](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer) 物件。
這可能是由網站中的架構、程式庫或其他第三方內容所造成。

## 什麼是 `SharedArrayBuffer`？

`SharedArrayBuffer` 是一個讓網站執行緒共用記憶體空間的 JavaScript 物件。
這個物件在名為 [Spectre](https://developers.google.com/web/updates/2018/02/meltdown-spectre?hl=zh-tw) 的安全漏洞被發現前已在各家網站上廣為使用。
然而，由於 Spectre 是 CPU 層級的安全漏洞，在可預見的將來也不太可能修正，因此瀏覽器已決定停用 `SharedArrayBuffer` 物件。

儘管 Chrome 會在以[網站隔離](https://security.googleblog.com/2018/07/mitigating-spectre-with-site-isolation.html)做為暫時因應措施的電腦上重新啟用該物件，但是[跨來源隔離](https://web.dev/articles/coop-coep?hl=zh-tw)已成為安全啟用 `SharedArrayBuffer` 物件的標準方式。
Chrome 92 版預計於 2021 年 5 月下旬推出，並開始使用跨來源隔離功能限制 `SharedArrayBuffer` 物件。
另外，Firefox 也在 76 版中，以跨來源隔離環境啟用 `SharedArrayBuffer` 物件。
我們希望其他瀏覽器都能盡快跟進。

## 瞭解網站使用 `SharedArrayBuffer` 物件的情形

做法有兩種：

1. 使用 [Chrome 開發人員工具](https://developers.google.com/web/tools/chrome-devtools?hl=zh-tw)檢查重要網頁。
2. (進階) 使用 [Reporting API](https://developers.google.com/web/updates/2018/09/reportingapi?hl=zh-tw) 將淘汰報表傳送至回報端點。

如果想知道以上做法的具體步驟，請參閱[確認網站使用 `SharedArrayBuffer` 物件的位置](https://web.dev/articles/cross-origin-isolation-guide?hl=zh-tw)。

## 後續步驟

建議您接著採取下列步驟：

1. 找出網站上使用 `SharedArrayBuffer` 物件的位置。
2. 判斷是否有必要使用該物件。
3. 修正問題：移除相關功能或[啟用跨來源隔離](https://web.dev/articles/cross-origin-isolation-guide?hl=zh-tw)。

如果您不曾聽聞過 `SharedArrayBuffer` 物件，Search Console 卻傳送相關郵件給您，很可能是因為您網站上的第三方資源正在使用該物件。
找出受影響的網頁和資源擁有者的身分後，請與資源提供者聯絡並要求修正問題。

Chrome 92 版推出後，`SharedArrayBuffer` 物件將無法在沒有跨來源隔離的環境中運作。從實務上來看，這代表 Chrome 使用者在瀏覽您的網站時，可能會遇到類似 `SharedArrayBuffer` 物件不受支援等情況時會出現的效能劣化體驗。

不論您是否收到相關郵件，我們都希望以上說明對您有所幫助。
如有任何疑問，建議您前往 [Search Central 產品討論社群](https://support.google.com/webmasters/community?hl=zh-tw)提問，尋求其他專家的意見。

發文者：Chrome 開發人員服務代表 [Eiji Kituram](https://blog.agektmr.com/)
