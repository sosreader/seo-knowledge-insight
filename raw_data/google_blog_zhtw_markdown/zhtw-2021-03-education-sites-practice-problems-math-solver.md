# 為教育網站提供的新功能：練習題與數學解題工具結構化資料透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2021-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/03/education-sites-practice-problems-math-solver?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2021 年 3 月 25 日，星期四

據[聯合國教科文組織](https://en.unesco.org/covid19/educationresponse)統計，全球有將近 15 億學生因為 COVID-19 而被迫中斷學業。幾乎在一夕之間，無論是學生、家長還是教育工作者都必須適應新的學習常態。很多人轉而從 Google 尋找教育和學習資源，我們也力求提供各種方法，幫助使用者找到所需資訊。

本文詳細說明了該如何在[練習題](https://developers.google.com/search/docs/appearance/structured-data/practice-problems?hl=zh-tw)和[數學解題工具](https://developers.google.com/search/docs/appearance/structured-data/math-solvers?hl=zh-tw)網頁上實作結構化資料，讓這些網頁在 Google 搜尋中顯示為複合式搜尋結果 (請注意，即使符合複合式搜尋結果的顯示條件，並不保證網站一定會出現在搜尋結果中)。另外，為了方便您檢查實作方式是否正確，我們也提供了[複合式搜尋結果狀態報告](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)。

練習內容和數學輔助是學生最迫切需要的一些資訊。練習教材可以幫助使用者衡量自己對於某個概念的理解程度，解題工具則能在他們解題不順利時提供說明，讓他們茅塞頓開。無論您的網站提供以上何種教材，這兩項功能都有利於網站提高在 Google 搜尋結果網頁中的品牌意識，網站也可能因為呈現效果更好而獲得更多流量。

如果您的網站上有符合條件的內容，歡迎按照本文介紹的最佳做法善用這些全新架構。

## 練習題標記

Google 能將練習題以複合式搜尋結果的形式呈現，方便使用者預覽網站上的學習內容。您可以在說明文件中查看完整的[規範](https://developers.google.com/search/docs/appearance/structured-data/practice-problems?hl=zh-tw#guidelines)清單。此外，我們特別建議您留意以下規範：

* 請針對您想呈現複合式搜尋結果的每個練習題加上 `Quiz` 屬性。結構化資料必須位於供使用者與練習題互動的網頁上。
* 網頁必須含有所有必要的結構化資料屬性 (詳見[必要的 `Quiz` 屬性](https://developers.google.com/search/docs/appearance/structured-data/practice-problems?hl=zh-tw#structured-data-type-definitions))。
* 每個概念至少要標記兩個練習題 (例如標記「二次方程式」的兩個練習題)。請著重標記出您希望以練習題複合式搜尋結果形式呈現的概念和問題。這些內容可位於不同網頁上。

![Google 搜尋中的練習題複合式搜尋結果](https://developers.google.com/static/search/blog/images/practice-problems-rich-result.png?hl=zh-tw "Google 搜尋中的練習題複合式搜尋結果")

使用者當前關注的主題，還有年級、課程標準等等與他們自身相關的條件，都可能是他們在挑選學習教材時會考量的重要項目。我們從研究中得知，使用者會從這些信號來判斷線上學習內容是否符合學校的教學內容，因此很推薦您加入所有與內容相關的建議屬性。

## 數學解題工具標記

數學解題工具網頁會提供工具，讓使用者能輸入數學方程式並獲得解題說明。舉例來說，使用者可以輸入如 x^4 - 3x = 0 這樣的方程式，然後查看網站提供的解題說明步驟。只要在網站上使用數學解題工具結構化資料，當使用者在 Google 搜尋列中輸入數學方程式時，Google 搜尋就能在搜尋結果中特別突顯您的網站。

![Google 搜尋中的數學解題工具複合式搜尋結果](https://developers.google.com/static/search/blog/images/math-solver-rich-result.png?hl=zh-tw "Google 搜尋中的數學解題工具複合式搜尋結果")

數學解題工具結構化資料僅適用於能夠實際解題的網頁；如果使用者無法在網頁上提交數學方程式以取得解題步驟，您就不應該在網頁上加入這項結構化資料。如要進一步瞭解詳細的實作資訊，請參閱[開發人員說明文件](https://developers.google.com/search/docs/appearance/structured-data/math-solvers?hl=zh-tw)。

## 運用 Search Console 對練習題和數學解題工具標記進行偵錯及監控

為了方便您監控標記問題，我們也[在 Search Console 中推出了練習題和數學解題工具的報告](https://support.google.com/webmasters/answer/7552505?hl=zh-tw)，針對含有這類結構化資料的網頁列出所有錯誤、警告和有效項目。

您可以從這些報告中瞭解 Google 能否讀取您網站的各項內容，並排解複合式搜尋結果的相關錯誤。而且在修正問題後，您也可以使用這份報告來進行驗證，讓 Google 重新檢索原本有問題的網頁。請參閱[這篇文章](https://www.youtube.com/watch?v=Vmfvf8nG09k&hl=zh-tw)，進一步瞭解如何使用報告監控複合式搜尋結果。

![Search Console 中的練習題報告](https://developers.google.com/static/search/blog/images/practice-problems-search-console.png?hl=zh-tw "Search Console 中的練習題報告")

您也可以使用[複合式搜尋結果測試](https://search.google.com/test/rich-results?hl=zh-tw)來提交程式碼片段或網頁網址，以此測試結構化資料。測試結果會顯示結構化資料是否有任何錯誤並提供相關建議。

![複合式搜尋結果測試中的練習題測試結果](https://developers.google.com/static/search/blog/images/practice-problems-rich-results-test.png?hl=zh-tw "複合式搜尋結果測試中的練習題測試結果")

歡迎提供您對練習題或數學解題工具結構化資料的想法和使用經驗，請透過 [Twitter](https://twitter.com/googlesearchc) 或[搜尋中心產品討論社群](https://support.google.com/webmasters/threads?thread_filter=%28category%3Astructured_data%29&hl=zh-tw)將任何意見回饋告訴我們。

發文者：學習與教育搜尋產品經理 [Michael Le](https://www.linkedin.com/in/michael-l%C3%AA/)
