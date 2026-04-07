# 如何在 Google 搜尋顯示暫停線上業務
- **發佈日期**: 2020-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/03/how-to-pause-your-business-online-in?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 3 月 26 日，星期四

隨著 COVID-19 的影響範圍日益擴大，我們看到世界各地的商家都在尋求暫停線上業務的方式。為了準備日後東山再起，再次為您的客戶提供服務，我們在下方大致介紹了暫停線上業務的建議做法，希望協助您盡量減少在 Google 搜尋方面受到的影響。這些建議做法適合任何經營線上形象的商家，特別是那些已暫停在線上販售產品或服務的商家。如需更多詳細資訊，請另行參閱[開發人員說明文件](https://developers.google.com/search/docs/crawling-indexing/pause-online-business?hl=zh-tw)。

## 建議做法：限制部分網站功能

如果您只是暫時停業，日後仍有計畫恢復線上業務，那麼我們建議您讓網站維持營運狀態，只限制部分功能。比如，您可以將商品標示為缺貨中，或是暫停開放購物車和結帳程序。我們之所以如此建議，是因為這可以盡量避免網站在 Google 搜尋中的排名受到負面影響。使用者還是能找到您的產品、閱讀評論或新增願望清單，所以日後要消費也很方便。

以下還有一些建議做法：

* **停用購物車功能**：這是最簡單的方法，也不會影響您的網站在 Google 搜尋中的曝光率。
* **讓客戶瞭解當前情況**：利用橫幅或彈出式視窗 div 為使用者提供正確資訊，讓他們瞭解您的業務現況。如果已知出貨會有所延遲，或是出貨時間、取貨或配送方式與平時不同，請務必提前說明，讓使用者早有心理準備。請務必遵循我們的[彈出式視窗與橫幅規範](https://developers.google.com/search/blog/2016/08/helping-users-easily-access-content-on?hl=zh-tw)。
* **更新結構化資料**：如果您的網站使用結構化資料 (例如[產品](https://developers.google.com/search/docs/appearance/structured-data/product?hl=zh-tw)、[書籍](https://developers.google.com/search/docs/appearance/structured-data/book?hl=zh-tw)和[活動](https://developers.google.com/search/docs/appearance/structured-data/event?hl=zh-tw))，請務必適當調整相關資訊 (反映目前的產品供應情形，或是將活動狀態改成已取消)。如果您有實體店面，請根據目前的營業時間更新[當地商家結構化資料](https://developers.google.com/search/docs/appearance/structured-data/local-business?hl=zh-tw)。
* **檢查 Merchant Center 動態饋給**：如果您使用 Merchant Center，請依照[供應情形 [availability] 屬性最佳做法](https://support.google.com/merchants/answer/6324448?hl=zh-tw)中的指示操作。
* **將更新內容告知 Google**：如果要讓 Google 重新檢索少量網頁 (例如首頁)，請使用 [Search Console](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl?hl=zh-tw)；如果需要重新檢索的網頁數量較多 (例如所有產品頁面)，請[使用 Sitemap](https://developers.google.com/search/docs/guides/submit-URLs?hl=zh-tw)。

如需更多資訊，請參閱[開發人員說明文件](https://developers.google.com/search/docs/crawling-indexing/pause-online-business?hl=zh-tw)。

## 不建議的做法：停用整個網站

在萬不得已的情況下，您可能會決定停用整個網站。然而，這種極端措施只宜短時間使用 (最多幾天)，因為即使實施得當，這仍可能對網站在 Google 搜尋中的成效產生極大影響。有鑑於此，我們強烈建議您改成只[限制部分網站功能](#limit)。提醒您，即使您目前未銷售任何商品，客戶還是可能會尋找與您的產品、服務和公司有關的資訊。

再次重申，我們不建議停用網站，但如果您判斷自己確實有這樣的需求，可以採取以下做法：

* 如果需要緊急停用網站 1 到 2 天的時間，請傳回含有 [503 HTTP 結果碼](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503)的資訊錯誤網頁，不要傳回所有內容。請務必遵循[停用網站的最佳做法](https://developers.google.com/search/docs/crawling-indexing/pause-online-business?hl=zh-tw#best-practices-disabling-site)。
* 如果需要停用網站的時間較長，請使用 200 HTTP 狀態碼，提供能建立索引的首頁充當使用者在 Google 搜尋中找到的預留位置。
* 如果您還在思考要採取何種做法，但急需在 Google 搜尋中隱藏網站，可以先[暫時從 Google 搜尋中移除網站](https://support.google.com/webmasters/answer/9689846?hl=zh-tw)。

如需更多資訊，請參閱[開發人員說明文件](https://developers.google.com/search/docs/crawling-indexing/pause-online-business?hl=zh-tw)。

**請謹慎執行**：為了詳細闡述為何我們不建議您停用整個網站，我們在下面列出了一些相關的副作用：

* 如果客戶在網路上找不到您的商家，就無法得知您的業務狀態。
* 客戶找不到或看不到有關您的商家與產品和服務的第一手資訊，例如評論、規格、之前的訂單、維修指南或手冊等內容。第三方資訊可能不如您提供的正確或完整，這往往會影響客戶日後的購買意願。
* 知識面板的資訊可能有所遺漏，比如缺少聯絡電話和您的網站標誌。
* Search Console 將驗證失敗，您會因此無法存取有關您的商家在 Google 搜尋中的任何成效資訊。Search Console 中的匯總報表會因為相關網頁已從索引中移除而遺失資料。
* 如果您的網站需要先重新建立索引，長時間停用就會使恢復作業的難度大幅提升。此外，我們無法確定此過程需要多久時間，也不能保證之後網站仍能在 Google 搜尋中獲得差不多的排名。

## 其他注意事項

除了處理網站營運事宜外，您可能還需要採取其他行動才能在 Google 搜尋中暫停線上業務。

* 如果您是活動舉辦方，請參閱[這篇文章](https://developers.google.com/search/blog/2020/03/new-properties-virtual-or-canceled-events?hl=zh-tw)，瞭解如何使用新的屬性來標示活動已延期、取消或改成線上舉行。
* 瞭解如何[變更營業時間或宣布暫時停業](https://support.google.com/business/answer/9773423?hl=zh-tw)。
* 查看 [Google for Small Business](https://smallbusiness.withgoogle.com/news/resources-for-smbs-impacted-by-coronavirus/#!/) 的資源，瞭解如何與客戶和員工溝通，實現遠距工作及修改廣告活動。
* 瞭解如何[對 Google 知識面板提出修改建議](https://support.google.com/knowledgepanel/answer/7534842?hl=zh-tw)，或是[聲明知識面板的擁有權](https://support.google.com/knowledgepanel/answer/7534902?hl=zh-tw) (如果尚未完成此程序)。

此外，別忘了在 Twitter 上追蹤 [@GoogleSearchC](https://twitter.com/googlesearchc) 和 [@GoogleMyBiz](https://twitter.com/GoogleMyBiz)，即時掌握最新資訊。

## 常見問題

**如果我只將網站關閉幾週，會怎麼樣？**

即使只將網站完全關閉幾週時間，Google 對網站的索引編制仍會受到負面影響，因此建議您改為[限制部分網站功能](#limit)。提醒您，即使您目前未銷售任何商品，客戶還是可能會尋找與您的產品、服務和公司有關的資訊。

**我可以排除所有非必要產品嗎？**

沒有問題。您可以[限制部分網站功能](#limit)，不開放客戶購買非必要產品。

**我可以要求 Google 在這段期間降低檢索頻率嗎？**

您可以[降低檢索頻率](https://developers.google.com/search/docs/crawling-indexing/reduce-crawl-rate?hl=zh-tw)，但大多數情況下我們不建議這麼做，因為這可能會影響搜尋結果的即時性。比如，Google 搜尋可能需要更多時間才會顯示您的產品已全部停止供應。不過，如果 Googlebot 的檢索作業會導致伺服器資源出現嚴重問題，這就不失為一個有效的解決方法。建議您為自己設定提醒，別忘了在準備恢復營業時重設檢索頻率。

**如何迅速為網頁建立索引或進行更新？**

如果要讓 Google 重新檢索少量網頁 (例如首頁)，請使用 [Search Console](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl?hl=zh-tw)；如果需要重新檢索的網頁數量較多 (例如所有產品頁面)，請[使用 Sitemap](https://developers.google.com/search/docs/guides/submit-URLs?hl=zh-tw)。

**如果我禁止特定地區存取我的網站，會有什麼影響？**

Google 通常會從美國進行檢索。如果您封鎖了美國地區，Google 搜尋通常就完全無法存取您的網站。我們不建議您暫時禁止整個地區的使用者存取您的網站；您可以改成針對個別地區[限制部分網站功能](#limit)。

**我應該使用移除工具將缺貨中的產品移除嗎？**

不用。這麼做將使客戶無法在 Google 搜尋中找到該產品的第一手資訊，客戶還可能在其他地方看到不正確或不完整的第三方資訊。建議做法是保留產品頁面並將產品狀態標示為缺貨中，讓客戶即使無法購買產品也能瞭解情況。如果您將產品從 Google 搜尋中移除，客戶就無法得知搜尋不到產品的原因。

---

我們瞭解停業是一件令人充滿壓力的大事，不是每個人都知道該怎麼做。即使您在停業後發現本來可以採取其他方式也不必擔心，因為資料都還在：我們致力於提供強大的系統，協助您的網站盡快在 Google 搜尋中恢復原本的表現。我們和您一樣希望這次的危機能盡早解決，也希望本文的資訊能協助您在危機解除後迅速讓線上業務重回軌道。如果在這段期間有任何問題，歡迎隨時前往我們的[公開頻道](https://developers.google.com/search/help?hl=zh-tw)尋求協助。

發文者：於瑞士蘇黎世家中工作的 [John Mueller](https://johnmu.com/)
