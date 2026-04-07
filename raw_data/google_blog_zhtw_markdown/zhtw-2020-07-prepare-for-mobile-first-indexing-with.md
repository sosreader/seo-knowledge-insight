# 多一點時間，「行動版內容優先索引系統」導入更周延透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2020-07-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/07/prepare-for-mobile-first-indexing-with?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 7 月 22 日，星期三

**已提供更新內容**：這篇文章已過時。請參閱新版的[行動版內容優先索引系統最佳做法](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=zh-tw)。

Google 多年來一直致力於改善[行動版內容優先索引系統](https://developers.google.com/search/blog/2016/11/mobile-first-indexing?hl=zh-tw)。我們已為最近檢索過的網站啟用行動版內容優先索引系統，並[為所有新網站預設啟用這套系統](https://developers.google.com/search/blog/2019/05/mobile-first-indexing-by-default-for?hl=zh-tw)。我們原本計劃在 2020 年 9 月[讓 Google 搜尋中的所有網站採用行動版內容優先索引系統](https://developers.google.com/search/blog/2020/03/announcing-mobile-first-indexing-for?hl=zh-tw)。但之後我們意識到，目前大環境尚未完全回歸常軌，大家可能無法時時刻刻專注於工作，因此我們決定將計畫執行時間展延到 2021 年 3 月底。預計到那個時候，我們就會全面轉換為行動版內容優先索引系統。

如果網站尚未準備好採用行動版內容優先索引系統，我們已在[先前的網誌文章](https://developers.google.com/search/blog/2018/12/mobile-first-indexing-structured-data?hl=zh-tw)中提到一些網站可能會遇到的阻礙。經過更多測試和評估，我們發現還有更多值得探討的問題，能協助您[更好的預備網站](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=zh-tw)。

## 確認 Googlebot 可以查看您的內容

在行動版內容優先索引系統中，我們只會從行動版網站獲得網站相關資訊，因此，請確認 Googlebot 能透過您的行動版網站查看完整內容和所有資源。請留意以下幾點：

### 行動版網站上的漫遊器 `meta` 標記

您應該在行動版網站上使用與電腦版相同的 [robots `meta` 標記](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=zh-tw)。如果您在行動版網站上使用不同的中繼標記 (例如 `noindex` 或 `nofollow`)，當網站啟用行動版內容優先索引系統後，Google 可能無法建立索引或追蹤網頁上的連結。

### 行動版網站上的延遲載入

相較於電腦版網站，延遲載入功能在行動版網站上更為常見，尤其是在載入圖片和影片時。建議您遵循[延遲載入最佳做法](https://developers.google.com/search/docs/crawling-indexing/javascript/lazy-loading?hl=zh-tw)。請特別注意，避免在主要內容上採用以使用者互動 (例如滑動、點擊或輸入) 為基礎的延遲載入設計，因為 Googlebot 不會觸發這些使用者互動操作。

舉例來說，如果您的電腦版網頁上有 10 張主要圖片，而行動版只有其中 2 張，另外 8 張圖片只有在使用者點擊 [`+`] 按鈕時才會從伺服器載入，如下所示：

![電腦版網頁有 10 張縮圖，而行動版有 2 張縮圖](https://developers.google.com/static/search/blog/images/import/23d844e245ad4882bd2b3cbf2fd65c2e.png?hl=zh-tw)

在此情況下，Googlebot 不會點擊按鈕來載入另外 8 張圖片，所以 Google 就無法看到這些圖片。這會造成這些圖片無法編入索引，也無法在 Google 圖片中顯示。請遵循 [Google 的延遲載入最佳做法](https://developers.google.com/search/docs/crawling-indexing/javascript/lazy-loading?hl=zh-tw)，並依據內容在可視區域中的可見度自動執行延遲載入。

### 留意您封鎖了哪些項目

有些資源會在行動版和電腦版網站上使用不同的網址，有時候這些版本會由不同的主機提供。如要讓 Google 檢索您的網址，請勿使用 [robots.txt 檔案](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=zh-tw)禁止 Google 檢索這些網址。

舉例來說，封鎖 `.css` 檔案的網址會造成 Googlebot 無法正確轉譯網頁，這可能會影響您網頁在搜尋服務中的排名。同樣地，封鎖圖片的網址則會讓這些圖片無法顯示在 Google 圖片中。

## 確認行動版網站的主要內容與電腦版網站相同

如果行動版網站提供的內容比電腦版網站少，請考慮更新行動版網站，並提供和電腦版網站相同的主要內容，也就是您想藉以獲得排名的內容依據，或是吸引使用者瀏覽您網站的動機。系統只會為行動版網站上顯示的內容建立索引，並以這些內容決定網站在搜尋服務中的排名。如果刻意讓行動版網站顯示比電腦版更少的內容，當 Google 為網站啟用行動版內容優先索引系統後，網站可能會失去部分流量，因為 Google 屆時將無法獲得完整資訊。

請比照電腦版網站，在行動版網站上使用既明確又有意義的相同標頭。缺少意義的標頭可能會對網頁在搜尋服務中的曝光率造成負面影響，因為我們可能無法完整瞭解網頁的內容。

例如，假設您電腦版網頁的標頭含有下列標記：

```
<h1>Photos of cute puppies on a blanket</h1>
```

那麼行動版網頁也應使用含有同樣文字的相同標頭標記，而不要使用以下標頭：

```
<h1>Photos</h1>
```

(不明確且缺乏具體意義的標頭)

```
<div>Photos of cute puppies on a blanket</div>
```

(未使用標頭標記)

## 檢查圖片和影片

請檢查行動版網站上的圖片和影片，確認是否遵循[圖片最佳做法](https://developers.google.com/search/docs/appearance/google-images?hl=zh-tw)和[影片最佳做法](https://developers.google.com/search/docs/appearance/video?hl=zh-tw)。我們特別建議您檢查以下項目：

### 圖片品質

請勿在行動版網站上使用尺寸太小或解析度較低的圖片。太小或畫質不佳的圖片可能無法顯示在 Google 圖片中，或者無法在建立索引時以有利的方式呈現。

舉例來說，如果您的電腦版網頁有 10 張主要圖片，且皆為正常大小、畫質良好的圖片，那麼在行動版網頁上，為了將這些圖片放入較小的螢幕而使用非常小的縮圖 (如下所示)，就不是理想的做法：

![電腦版網頁使用正常縮圖，而行動版使用迷你縮圖](https://developers.google.com/static/search/blog/images/import/8ebc2a3122fb22a2c80b2ef8aa041fa5.png?hl=zh-tw)

在這種情況下，Google 可能會將這些縮圖視為「畫質不佳」，因為縮圖的尺寸太小且解析度較低。

### 圖片的 alt 屬性

如[先前所述](https://developers.google.com/search/blog/2018/12/mobile-first-indexing-structured-data?hl=zh-tw)，請記得，使用缺乏具體意義的 alt 屬性，可能會對圖片在 Google 圖片中的呈現方式造成負面影響。

例如，理想的做法如下列範例所示 (有意義的替代文字)：

```
<img src="dogs.jpg" alt="A photo of cute puppies on a blanket" />
```

不理想的做法則像這樣 (沒有替代文字)：

```
<img src="dogs.jpg" alt="alt" />
```

以下示例為缺乏具體意義的替代文字：

```
<img src="dogs.jpg" alt="Photo" />
```

### 電腦版和行動版網站分別使用不同的圖片網址

如果在電腦版和行動版網站分別使用不同的圖片網址，當網站改用行動版內容優先索引系統時，可能會暫時流失來自 Google 圖片的流量。這是因為對 Google 索引系統而言，這些行動版網站上的圖片網址算是新的項目，而系統需要一些時間才能正確瞭解新的圖片網址。如要盡可能減少搜尋服務流量暫時流失的情況，請重新檢查您是否能保留電腦版網站使用的圖片網址。

### 影片標記

如果您的電腦版網站使用 schema.org 的 `VideoObject structured data` 來描述影片，請確認行動版中也包含 `VideoObject`，且提供相同的資訊。否則，我們的影片索引系統可能無法獲得足夠的影片資訊，導致您的影片無法顯示在搜尋服務中。

### 影片和圖片刊登位置

請務必將影片和圖片置於容易在行動版網頁上找到的位置。如果影片或圖片的位置不佳，會影響使用者在行動裝置上的體驗，Google 也可能不會在搜尋結果中顯示這些內容。

舉例來說，假設您在內容中嵌入了一部影片，並將這部影片置於電腦版網頁上容易找到的位置，如下所示：

![在電腦版網頁上容易找到影片](https://developers.google.com/static/search/blog/images/import/3761a0a4ef0fef972abdf5de171862ee.png?hl=zh-tw)

但在行動版網頁上，您在靠近頁面頂端的地方放了廣告，占去該頁面大部分的空間。這種做法可能導致該影片無法顯示在當前頁面中，而使用者必須向下捲動很久才能找到影片，就像這樣：

![使用者很難找到行動版網頁上的影片](https://developers.google.com/static/search/blog/images/import/248fd61c343805b8035d72303552ea9b.png?hl=zh-tw)

在這種情況下，我們的演算法可能不會將這個網頁視為有效的影片到達網頁，導致影片無法顯示在搜尋服務中。

如要進一步瞭解相關資訊和更多最佳做法，請參閱[行動版內容優先索引系統的開發人員指南](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing?hl=zh-tw)。

行動版內容優先索引系統這幾年來取得了長足進步；我們很高興能見證網路使用從電腦版演進至行動版的過程，也很感謝網站管理員協助我們配合使用者與網路互動的方式，建立適合的檢索及索引系統。我們要對各位在過去幾年付出的心力表達感激之意；正是因為有你們的努力，我們才能如此順利地推動本次轉移作業。我們會持續小心地監控及評估各種變化。如有任何問題，歡迎造訪我們的[論壇](https://support.google.com/webmasters/go/community?hl=zh-tw)或[公開活動](https://developers.google.com/search/events?hl=zh-tw)。

發文者：Google 行動版內容優先索引系統小組 [Yingxi Wu (吳螢西)](https://www.linkedin.com/in/yingxiwu)
