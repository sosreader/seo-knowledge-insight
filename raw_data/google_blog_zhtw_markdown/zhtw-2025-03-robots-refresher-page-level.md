# 重溫漫遊器：頁面層級精細程度
- **發佈日期**: 2025-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2025/03/robots-refresher-page-level?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2025 年 3 月 14 日，星期五

有了 [robots.txt 檔案](https://developers.google.com/search/docs/crawling-indexing/robots/intro?hl=zh-tw)，網站擁有者就能輕鬆控管檢索器可存取網站的哪些部分。為了協助網站擁有者進一步指明搜尋引擎和網路檢索器該如何使用其網頁，參與制定網路標準的社群在 1996 年[提出 robots `meta` 標記](https://www.w3.org/Search/9605-Indexing-Workshop/ReportOutcomes/Spidering.txt)，這比 `meta` 標記在 HTML 中提出的時間晚了幾個月 (據說這也是 Google 成立之前的事)。後來，我們新增了 [`X-Robots-Tag` HTTP 回應標頭](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Robots-Tag)。這些指示會與網址一併傳送，因此檢索器只能在未透過 robots.txt 檔案禁止檢索網址的情況下，才會將這些指示納入考量。這些元素共同組成漫遊器排除通訊協定 (REP)。

## 漫遊器 `meta` 標記簡介

[中繼標記 (或元素)](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/meta) 是一種納入機器可讀中繼資料的方式。漫遊器 `meta` 標記是 `meta` 標記的一種「類型」，適用於檢索器，包括搜尋引擎檢索器。這類標記用來表示：內容是否遭到封鎖而無法建立索引？是否應避免檢索網頁上的連結？只要使用 robots `meta` 標記，就能輕鬆在網頁上直接提供這類資訊。

## 適用於任何網址的漫遊器排除通訊協定

為了替非 HTML 內容提供相同等級的控制項，我們建立了「`X-Robots-Tag`」HTTP 回應標頭。這些 [HTTP 標頭](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers)也屬於 REP 的一部分。這類標頭支援與 robots `meta` 標記相同的值，而且可以新增至任何在線上提供的內容。除了 HTML 之外，Google 支援將這類標頭運用於 PDF、文件檔案，甚至圖片等內容。這些檔案格式大多沒有等同於 `meta` 標記的機制，因此 HTTP 回應標頭會很有用。

## 開始使用漫遊器 `meta` 標記和標頭

語法簡單且可擴充。這些規則通常是由網頁程式開發人員或內容管理系統 (CMS) 實作，網站擁有者可以透過核取方塊或下拉式選單來選取偏好設定。這些控制項可控管特定的檢索器 (例如 Googlebot)，或是不指定特定名稱，這樣就能控管支援這些值的所有檢索器。

舉例來說，下列規則會告知所有檢索器不要使用相關聯的網頁建立索引：

* 在網頁上以 HTML `meta` 標記的形式：

  ```
  <meta name="robots" content="noindex">
  ```

  查看現有的 `meta` 標記或回應標頭稍微複雜一點，必須直接檢查網頁內容或標頭。您可以查看任何網頁上的 HTML `meta` 標記，方法是查看瀏覽器中的網頁來源，或是使用 Chrome 的開發人員工具[檢查網頁](https://developer.chrome.com/docs/devtools/elements?hl=zh-tw)。
* 以 [HTTP 回應標頭](https://developer.mozilla.org/en-US/docs/Glossary/Response_header)的形式：

  ```
  X-Robots-Tag: noindex
  ```

  您可以使用 Chrome 開發人員工具，在[網路面板](https://developer.chrome.com/docs/devtools/network/overview?hl=zh-tw)中檢查個別網址的 HTTP 回應標頭。

其他用途範例：

|  |  |
| --- | --- |
| 不要顯示這個網頁或文件的摘要。 | 在 HTTP 標頭中：    ``` X-Robots-Tag: nosnippet ```  或在 HTML 中：    ``` <meta name="robots" content="nosnippet"> ``` |
| 不要在 `ExampleBot-News` 中為這個網頁建立索引，針對其他項目則無指定偏好。  這些控制項會明確指定一個檢索器。 | ``` X-Robots-Tag: examplebot-news: noindex ```  或    ``` <meta name="examplebot-news" content="noindex"> ``` |
| `ExampleBot` 不應顯示摘要，此外，所有檢索器都不應追蹤這個網頁上的連結。  請注意，系統會套用最嚴格的有效指令，因此針對 `ExampleBot`，指令會合併為「`nosnippet, nofollow`」。 | ``` X-Robots-Tag: examplebot: nosnippet X-Robots-Tag: nofollow ```  或    ``` <meta name="examplebot" content="nosnippet"> <meta name="robots" content="nofollow"> ``` |

## 選擇 REP 機制

如何選擇要使用哪個方案？基本上，robots.txt 和網頁層級控制項類似，但無法完全互換。有時會有某個特定動作只能透過其中一種機制執行，例如，如果您想停止檢索動作 (例如針對無限的搜尋結果網頁，可透過 robots.txt 執行)、需要控制 FTP 伺服器 (可透過 robots.txt 執行)，或是不想顯示某個網頁的摘要 (只能透過網頁層級元素執行)。如果不需要區分封鎖檢索和封鎖索引的差異，可以使用 robots.txt 進行更廣泛的控管 (封鎖網站的大部分內容)，以及使用網頁層級控管封鎖個別網頁。

## 漫遊器排除通訊協定：強大且持續更新的標準

這些控制項全都具備可擴充性。多年以來，網站擁有者、檢索器營運者和搜尋引擎一直合作改進這些技術。一開始這個通訊協定只包含 `noindex` 和 `nofollow` 等少數值，後來才採用 `nosnippet`、`noarchive` 和 `max-snippet:` 等更多值。有時值會淘汰，例如 `noodp` 就是如此，因為該值使用了 [DMOZ/開放式目錄專案](https://en.wikipedia.org/wiki/DMOZ)在目錄關閉前提供的摘要。其中有 Google 為網站擁有者提供的[大量值](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag?hl=zh-tw#directives)，以及其他大型檢索器作業者的類似值。

在 REP 的範疇內，網站擁有者可以控管檢索項目，以及檢索引擎如何使用檢索到的資料。他們可以針對網站的大部分內容進行廣泛的控管，也可以針對個別網頁或網頁中的圖片進行精細的控管。這些控制項廣為人知，可在所有常見內容管理系統中使用，並受到商業營運者廣泛支援，目前也用於網路上的數十億個主機。

發文者：搜尋關係團隊代表 [John Mueller](https://developers.google.com/search/blog/authors/john-mueller?hl=zh-tw)

---

## 請參閱「重溫漫遊器」系列的其他影片：
