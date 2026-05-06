# 在 Google 圖片上顯示圖片的授權資訊透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2020-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/08/make-licensing-information-for-your?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 8 月 31 日，星期一

過去幾年來，我們持續與圖片授權業界合作，希望大家在利用 Google 圖片搜尋內容時，也能更加瞭解相關的授權規定。我們從 2018 年開始支援 [IPTC 圖片版權中繼資料](https://developers.google.com/search/docs/appearance/structured-data/image-license-metadata?hl=zh-tw)，接著在 2020 年 2 月針對可申請授權的圖片，[公布了](https://developers.google.com/search/docs/appearance/structured-data/image-license-metadata?hl=zh-tw)採用 Schema.org 和 IPTC 格式的新式中繼資料架構。從那時起，各種規模的網站、圖片平台和代理商就開始廣泛採用這項新標準。而現在，Google 圖片即將推出能夠突顯圖片授權資訊的新功能，讓使用者更容易瞭解如何以負責任的方式使用圖片。

## 新功能有什麼作用？

在搜尋結果網頁中，含有授權資訊的圖片將會標有「可申請授權」標記。當使用者開啟圖片檢視器時 (也就是選取圖片時所顯示的視窗)，系統便會顯示連結，讓使用者能夠前往由內容擁有者或授權人提供的授權詳細資料頁面和/或條款頁面。如果內容擁有者或授權人提供了能讓使用者取得圖片的其他頁面，系統也會一併顯示該頁面的連結。

![附上可申請授權標記的 Google 圖片搜尋結果](https://developers.google.com/static/search/blog/images/import/3e6cf9ac654f2f00d99206962a0d5e19.png?hl=zh-tw)

我們也簡化了搜尋過程，讓使用者更容易找到附有授權中繼標記的圖片。具體措施是改善 Google 圖片的 [使用權] 下拉式選單，支援篩選出創用 CC 授權圖片，以及具備商業授權或其他授權的圖片。

![新版使用權篩選器](https://developers.google.com/static/search/blog/images/import/f8c0d00ff4325ee3b02c88a7c012f9b9.png?hl=zh-tw)

## 這項改變能為圖片授權人帶來哪些好處？

* 如前文所述，如果圖片授權人提供了授權中繼資料，系統便能在圖片檢視器中顯示可申請授權標記、授權詳細資料頁面和可取得圖片的頁面，讓使用者更容易向授權人購買圖片或申請圖片授權。
* 如果圖片所在網頁無法讓使用者取得圖片 (例如作品集、文章或圖片庫等網頁類型)，那麼圖片授權人可以提供一個新網址，讓使用者直接從 Google 圖片前往能購買圖片或申請圖片授權的網頁。
* 如果您是圖片授權人，也可以讓發布商在購買您的圖片後套用中繼資料，這樣對方使用的圖片上就會顯示您的授權詳細資料 (這必須要求對方保留您提供的 IPTC 中繼資料，不能加以移除或更改)。

我們相信可以藉由這項改變進一步實現目標：協助使用者瞭解他們在 Google 圖片中所查看內容的性質和相關使用規範。

## 如何使用這些功能？

如要進一步瞭解這些功能、導入方式及相關問題的排解方法，請造訪 [Google Developers 說明頁面](https://developers.google.com/search/docs/appearance/structured-data/image-license-metadata?hl=zh-tw)和[常見問題頁面](https://support.google.com/webmasters/thread/31516792?hl=zh-tw)。

如要針對這些功能提供意見，請使用可申請授權圖片功能的開發人員頁面上的意見回饋工具，或是前往 [Google 網站管理員論壇](https://support.google.com/webmasters/community?hl=zh-tw)。此外，請持續關注接下來的線上即時諮詢時間，我們將在其中探討常見問題。

## 圖片授權人對這些功能有何看法？

「CEPIC 大約從 4 年前開始與 Google 合作，確保 Google 圖片可以顯示圖片的作者和版權所有人資訊。現在，我們終於實踐了這項計畫的最後一個關鍵環節，讓使用者能夠明確判斷哪些圖片可申請授權，而這一切都要感謝我們與 Google 合作所帶來的豐厚成果。很高興這次合作能為攝影經紀公司和廣大影像產業帶來難得的商機，感謝 Google 團隊。」
- **CEPIC 總裁 Alfonso Gutierrez**

IPTC 相片中繼資料處理團隊 (IPTC Photo Metadata Working Group) 的負責人 Michael Steidl 表示：「得益於 IPTC 和 Google 多年來的合作，現在，當熱門網站重複使用內嵌了 IPTC 相片中繼資料的圖片時，Google 圖片便能將該網站中對圖片有興趣的使用者引導回圖片供應商的網站。這對圖片供應商來說有極大的好處，也會促進供應商在圖片檔中加入 IPTC 中繼資料。」
- **IPTC 相片中繼資料處理團隊 (IPTC Photo Metadata Working Group) 負責人 Michael Steidl**

「Google 的可申請授權圖片功能在版權發展方面具有重要意義，因為使用者能夠更輕鬆地識別影像內容來源，並對內容申請授權。在這些功能開發期間，Google 不僅與 DMLA 及其成員密切合作、彼此分享工具和詳細資料，同時也收集了相關意見回饋，並協助我們的成員解決問題或疑慮。我們很期待繼續與 Google 合作，將這些功能部署至全球。」
- **數位媒體授權協會 (Digital Media Licensing Association) 會長 Leslie Hughes**

「現今的媒體環境瞬息萬變，圖片已經成為越來越多人在線上說故事及交流時不可缺少的元素。這種轉變意味著，使用者必須瞭解如何從正確的來源取得圖片授權以保護自身的安全，這些圖片的創作也必須持續獲得應有的投資。我們希望 Google 的做法能讓更多人瞭解授權圖片本身的價值，以及這些圖片的使用權利條件。」
- **Getty Images 與 iStock by Getty Images 內容資深副總裁 Ken Mainardis**

「有了 Google 的可申請授權圖片功能，現在使用者在 Google 圖片找到高品質的圖片後，系統可以引導他們遵照圖片版權規定購買圖片或申請圖片授權，整個程序比以往便利得多。另外，這項功能對專業攝影產業來說也是非常重要的里程碑，因為使用者現在可以更輕鬆找到圖片，並以安全、妥善的方式取得圖片授權。我們認為技術將會徹底改變企業尋找及購買圖片的方式，而這正是 EyeEm 成立的核心信念。因此，我們很高興從一開始便參與 Google 的可申請授權圖片專案，現在也非常樂見 Google 推出這些功能。」
- **EyeEm 共同創辦人 Ramzi Rizk**

「picturemaxx 擁有全球最大的數位圖片專業供應商和使用者網路，因此我們非常歡迎 Google 推出的可申請授權圖片功能。我們的客戶同時身兼創作者和版權管理者，對他們來說，讓使用者在搜尋引擎中看見自己的作品，跟使用者能看見版權和授權資訊一樣重要。為了利用這項功能，picturemaxx 將在不久後推出讓客戶向 Google 圖片提供自身圖片作品的功能，目前正在進行相關開發作業。」
- **picturemaxx 技術長 Marcin Czyzewski**

「在這個專案的開發過程中，Google 諮詢了 Alamy 和攝影業界的其他重要關鍵企業，並展開密切合作。可申請授權標記可以減少造成消費者混淆的情形，並協助大眾瞭解優質圖片創作與報導用圖片的價值。」
- **Alamy 產品總監 James Hall**

「Google 圖片的新功能可清楚指明如何正確取得創作者內容授權，這對圖片創作者和消費者雙方都有助益。我們很高興與 Google 緊密合作開發這項功能，這不僅保護了我們全球社群 100 多萬名圖片貢獻者的權益，也為他們的貢獻提供合理報酬。在這項功能開發期間，Google 也明確承諾支持內容創作生態系統。」
- **Shutterstock 內容營運部門副總裁 Paul Brennan**

「Google 圖片新推出的可申請授權圖片功能可以協助創意團隊發掘更多獨特內容。藉由將 Google 圖片打造成搜尋可授權內容的可靠管道，Google 可以為所有攝影經紀公司和獨立攝影師帶來更多曝光機會，並建立一套有效率的處理程序，協助使用者快速找到並取得最符合需求的可授權內容。」
- **PhotoShelter 執行長 Andrew Fingerman**

發文者：Google 圖片產品經理 Francois Spies
