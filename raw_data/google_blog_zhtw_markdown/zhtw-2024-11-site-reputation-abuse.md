# 更新網站信譽濫用行為政策
- **發佈日期**: 2024-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2024/11/site-reputation-abuse?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2024 年 11 月 19 日，星期二

我們致力於打擊垃圾內容並提供優質搜尋體驗，因此於[今年](https://developers.google.com/search/blog/2024/03/core-update-spam-policies?hl=zh-tw)稍早推出垃圾內容政策，對抗[網站信譽濫用行為](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw#site-reputation)。這種策略是指，上傳者在代管網站上發布第三方內容，試圖利用代管網站已建立的排名信號。這麼做的目的是讓該內容的排名比發布在其他網站上高，導致使用者獲得不佳的搜尋體驗。

自這項政策推出以來，我們已審查了可能涉及不同程度第一方參與的情況，例如與白標服務合作、授權協議、部分擁有權協議，以及其他複雜的商業安排。根據已評估的多數案例顯示，即使第一方參與程度很高，內容仍具有第三方本質，或試圖利用代管網站的排名信號，這類行為仍屬於不公平的濫用行為。

我們將闡明政策用語，進一步針對這類發布垃圾資訊的行為採取行動。
我們明確指出，只要在網站上使用第三方內容，意圖利用該網站的排名信號，即視為違反這項政策，無論是否有第一方參與或監督該內容都一樣。新版政策用語自即日起生效，內容如下：

> 網站信譽濫用行為是指在網站上發布第三方網頁，試圖利用代管網站的排名信號操縱搜尋排名的做法。

評估政策違規情形時，我們會考量許多因素來判斷第三方內容是否遭到濫用，並不會單純接受網站聲稱的內容製作方式。網站擁有者會在註冊的 [Search Console](https://search.google.com/search-console/about?hl=zh-tw) 帳戶收到[垃圾內容人工判決處罰](https://support.google.com/webmasters/answer/9044175?hl=zh-tw)通知，並可提交[重審要求](https://support.google.com/webmasters/answer/9044175?hl=zh-tw)。

請注意，並非所有第三方內容都違反這項政策。詳情請參閱[垃圾內容政策頁面](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw#site-reputation)，瞭解何者屬於/不屬於網站信譽濫用行為。

除了網站信譽濫用問題之外，我們也設有系統和方法，用於瞭解網站的某個版面是否獨立於網站的主要內容，或與其截然不同。將這些版面視為獨立網站，有助於確保公平競爭環境，避免網站子版面的排名因主網站的信譽而提升。我們會持續改善這些系統，提供來自各種網站的實用資訊。

我們會盡力瞭解網站各版面的差異，如果子版面不再受益於[全網站信號](https://developers.google.com/search/docs/appearance/ranking-systems-guide?hl=zh-tw)，就可能導致流量變化。這並不表示這些子版面已遭到降級或違反垃圾內容政策。即使這些事件位於同一網站中，我們也會個別評估。

這項網站信譽濫用行為政策的澄清說明有助於顯示最實用的搜尋結果、打擊操控行為，並確保所有網站都能根據內容品質獲得相同的排名機會。我們鼓勵網站擁有者熟悉這項新版政策，並專注於打造優質網站，提供[以使用者為優先，而非為了提高搜尋引擎排名而製作的內容](https://developers.google.com/search/docs/fundamentals/creating-helpful-content?hl=zh-tw)。

## 常見問題

### 什麼是第三方內容？

第三方內容是指由代管網站以外的實體建立的內容。個別實體的例子包括該網站的使用者、自由工作者、白標服務、由非代管網站直接聘雇的人員所建立的內容，以及[網站信譽政策](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw#site-reputation)中列出的其他例子。

### 使用任何第三方內容是否違反網站信譽濫用行為政策？

否，單純使用第三方內容並不違反網站信譽濫用行為政策。但如果在內容發布時，試圖利用代管網站的排名信號[操縱搜尋排名](#abuse-search-rankings)，這樣就會違反政策。我們的[政策頁面](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw#site-reputation)列舉了一些不違反政策的第三方內容使用示例。

### 自由接案內容是否違反網站信譽濫用行為政策？

否，雖然自由接案內容屬於第三方內容，但單純使用這類內容並不違反網站信譽濫用行為政策。但如果**一併**試圖利用代管網站的排名信號[操縱搜尋排名](#abuse-search-rankings)時，才會違反這項政策。

### 聯盟內容是否違反網站信譽濫用行為政策？

否，這項政策並非針對聯盟內容。這項政策的[說明文件](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw#site-reputation)明確指出，系統不會將加上[適當標示](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links?hl=zh-tw)的聯盟連結視為違反網站信譽濫用。

### 試圖利用代管網站的排名信號操縱搜尋排名，是什麼意思？

這類行為是指將第三方內容放置於已建立的網站，利用第三方內容網站的排名信號 (主要從其第一方內容獲得)，而非將內容放置於缺乏相同信號的其他網站。

### 如果我使用 [`noindex`](https://developers.google.com/search/docs/crawling-indexing/block-indexing?hl=zh-tw) 中繼標記，系統會自動移除人工判決處罰嗎？

不會。您還是需要在 Search Console 中回覆人工判決處罰，並說明內容已加上 noindex 中繼標記。建議您採取這項行動，而非讓網站的人工判決處罰生效。

### 如果我將收到人工判決處罰的內容移至新位置，可以解決網站信譽濫用問題嗎？

或許可以，但取決於您將內容移至何處：

* **將內容移至相同網站網域名稱中的子目錄或子網域**：這樣做無法解決潛在問題，且可能會被視為[試圖規避](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw#policy-circumvension)我們的垃圾內容政策，導致 Google 搜尋對網站採取更廣泛的行動。
* **將內容移至其他已建立的網站**：這樣做可以解決網站信譽濫用問題，因為移除這類內容後，網站的信譽就不會再受到濫用。不過，如果已建立的網站有自己的信譽，且第三方性質未變更，則可能會在移除內容的網站上造成網站信譽濫用問題。
* **將內容移至新網域**：如果新網域尚未建立信譽，且您遵守[垃圾內容政策](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw)，這項操作幾乎不會造成問題。

請注意，如果您移動內容，必須一併提交重審要求，才能移除人工判決處罰。

### 如果我移動違反政策的內容，可以將舊網站重新導向至新網站嗎？

如果您移動收到人工判決處罰的內容，請勿將[網址](https://developers.google.com/search/docs/crawling-indexing/301-redirects?hl=zh-tw)從舊網站重新導向至新網站，否則可能會再次導致網站信譽濫用問題。

### 如果我移動違反政策的內容，可以從舊網站連結至新網站嗎？

如果您從舊網站連結至新網站，請在舊網站的這些連結中使用 [`nofollow` 屬性](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links?hl=zh-tw)。

發文者：Google 搜尋品質團隊代表 [Chris Nelson](https://developers.google.com/search/blog/authors/chris-nelson?hl=zh-tw)

---

## 更新

* **2024 年 12 月 6 日更新**：新增[常見問題](#faq)，回覆網站擁有者對 Google 網站信譽濫用行為政策提出的新問題。
* **2025 年 1 月 21 日更新**：根據常見問題的意見回饋，我們更新了[網站信譽濫用行為政策](https://developers.google.com/search/docs/essentials/spam-policies?hl=zh-tw#site-reputation)的措辭，並在[人工判決處罰報告說明文件](https://support.google.com/webmasters/answer/9044175?hl=zh-tw#site-reputation-abuse&zippy=,site-reputation-abuse)中加入常見問題中的指引。這些修訂是為了讓政策用語更清楚，政策本身並未實質變更。
