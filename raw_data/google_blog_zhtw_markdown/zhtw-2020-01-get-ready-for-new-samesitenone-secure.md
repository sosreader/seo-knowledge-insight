# 準備好迎接全新的 Cookie 設定：SameSite=None; Secure透過集合功能整理內容你可以依據偏好儲存及分類內容。
- **發佈日期**: 2020-01-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/01/get-ready-for-new-samesitenone-secure?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2020 年 1 月 16 日，星期四

這篇文章同步發布於 [Chromium 開發人員網誌](https://blog.chromium.org/2019/10/developers-get-ready-for-new.html)，專門介紹 Chrome 的異動對於使用者日後瀏覽您的網站可能有哪些影響。

Chrome 在去年 5 月[宣布](https://blog.chromium.org/2019/05/improving-privacy-and-security-on-web)推出了 Cookie 的預設安全模型，採用全新的 Cookie 分類系統 ([規格](https://tools.ietf.org/html/draft-west-cookie-incrementalism-00))。這項措施是我們以改進網路隱私權與安全性為目標[持續努力](https://www.blog.google/products/chrome/building-a-more-private-web/?hl=zh-tw)的其中一環。

Chrome 預計會在 2020 年 2 月推出的 Chrome 80 版中導入新模型。Mozilla 和 Microsoft 也表明了會依自身的時間規劃在 Firefox 和 Edge 中導入新模型。儘管 Chrome 的異動還要幾個月才會實施，但負責管理 Cookie 的開發人員仍有必要立即評估自身是否準備妥當。這篇網誌文章將大致說明整體概念；如需開發人員指南，請參考 web.dev 網站的 [SameSite Cookie 說明](https://web.dev/samesite-cookies-explained?hl=zh-tw)。

## 瞭解跨網站使用 Cookie 與同網站使用 Cookie 的區別

一般而言，網站會整合外部服務來提供廣告、推薦內容、第三方小工具、社群媒體嵌入元素及其他功能。當您瀏覽網路時，這些外部服務可能會將 Cookie 儲存在您的瀏覽器中，再透過存取這些 Cookie 來提供個人化體驗或評估目標對象參與度。每個 Cookie 都有一個相關聯的網域。如果 Cookie 的關聯網域是對應至外部服務，而不是使用者網址列中的網站，Cookie 就屬於**跨網站** (或**第三方**) 使用。

有些跨網站使用 Cookie 的情況比較不明顯，比如某個實體擁有多個網站，並在這些資源中使用同一個 Cookie 就是如此。儘管 Cookie 和網站都屬於同一個實體，但只要 Cookie 與存取 Cookie 的網站不在同一個網域，就依然算是跨網站使用，因此 Cookie 會被視為屬於「第三方」。

![網站網域與 Cookie 網域不符](https://developers.google.com/static/search/blog/images/import/85745326a70c3265cf41353b15e75598.png?hl=zh-tw)

當網頁上的外部資源存取 Cookie 時，如果 Cookie 網域與網站的網域不符，Cookie 就屬於跨網站使用，亦即是由「第三方」使用。

相反地，如果 Cookie 網域符合使用者網址列中網站的網域，Cookie 就屬於**同網站**使用，亦即是由**第一方**使用。同網站 Cookie 的常見用途包括保持使用者在個別網站的登入狀態、記住使用者偏好設定及支援網站分析。

![網站網域與 Cookie 網域相符](https://developers.google.com/static/search/blog/images/import/5fbd233c5202ff716c0062fdbbe74968.png?hl=zh-tw)

當網頁上的資源存取 Cookie 時，如果 Cookie 網域與使用者所造訪網站的網域相符，Cookie 就屬於同網站使用，亦即是由「第一方」使用。

## 確保 Cookie 安全性和資訊公開的新模型

目前，如果 Cookie 只限在第一方使用情境下存取，開發人員就可以選擇運用 `SameSite=Lax` 或 `SameSite=Strict` 設定來防止外部存取。然而，實際上只有極為少數的開發人員採用這項建議做法，因此仍有大量同網站 Cookie 無謂地暴露在[跨網站偽造要求](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet)攻擊等威脅下。

為了保護更多網站和使用者，除非另外設定，否則新的預設安全模型一律會假定所有 Cookie 都不宜從外部存取。開發人員必須使用 `SameSite=None` 這項新的 Cookie 設定才能將 Cookie 設為開放跨網站存取。如果有 `SameSite=None` 屬性，則必須使用額外的 Secure 屬性，確保跨網站 Cookie 只能透過 HTTPS 連線存取。這種做法雖然無法減少跨網站存取行為帶來的風險，卻有助於防範網路攻擊。

除了立即保障安全的優勢外，聲明跨網站 Cookie 還能讓資訊更公開透明，並賦予使用者選擇空間。舉例來說，瀏覽器可以為使用者提供精細的控制設定，將僅限單一網站存取的 Cookie 與可透過多個網站存取的 Cookie 分開管理。

## 2020 年 2 月開始實施的 Chrome 違規處置

Chrome 預計在 2 月推出 80 版，屆時尚未聲明 SameSite 值的 Cookie 就會被視為 `SameSite=Lax` Cookie。只有設有 `SameSite=None`; Secure 的 Cookie 可供外部資源透過安全連線進行存取。[`SameSite=None`](https://chromestatus.com/feature/5088147346030592) 和 [Secure](https://chromestatus.com/feature/5633521622188032) 的 Chrome Platform Status 追蹤工具會持續更新，提供最新版本的發布資訊。

Mozilla 已確認會支援新的 Cookie 分類模型，並[表明](https://groups.google.com/forum/?hl=zh-tw#!msg/mozilla.dev.platform/nx2uP0CzA9k/BNVPWDHsAQAJ)會在 Firefox 中針對跨網站 Cookie 導入 `SameSite=None`; Secure 相關規範。Microsoft 最近則[宣布](https://groups.google.com/a/chromium.org/forum/?hl=zh-tw#!msg/blink-dev/AknSSyQTGYs/8lMmI5DwEAAJ)，他們計劃從 Microsoft Edge 80 版開始以實驗性質導入該模型。

## 準備方式和已知的複雜作業

如果您管理跨網站 Cookie，就必須將 `SameSite=None`; Secure 設定套用至這類 Cookie。雖然我們認為導入作業應該對大部分開發人員都很簡單，但仍強烈建議您立即著手測試，確認有哪些複雜和特殊情況，例如：

* 部分語言和程式庫尚未支援 None 值，需要開發人員直接設定 Cookie 標頭。這個 [GitHub 存放區](https://github.com/GoogleChromeLabs/samesite-examples)提供了以多種語言、程式庫和架構導入 `SameSite=None`; Secure 的操作說明。
* 部分瀏覽器 (包括 Chrome、Safari 和 UC 瀏覽器的某些版本) 可能會以非預期的方式處理 `None` 值，需要開發人員針對這些用戶端編寫例外狀況的程式碼。除了這些瀏覽器外，採用舊版 Chrome 技術的 Android WebView 也會發生同樣的狀況。[這份清單](https://www.chromium.org/updates/same-site/incompatible-clients)包含已知不相容的用戶端。
* 儘管我們之後才會對 Android WebView 強制執行新模型，仍建議應用程式開發人員針對透過 HTTP(S) 標頭和 Android `WebView` [CookieManager API](https://developer.android.com/reference/android/webkit/CookieManager?hl=zh-tw) 存取的 Cookie，根據與 `None` 相容的 Chrome 版本為 Android `WebViews` 聲明適當的 `SameSite cookie` 設定。
* 如果企業有部分服務 (例如內部應用程式或單一登入) 尚未準備好迎接在 2 月推出的新模型，企業的 IT 管理員就可能需要實施[特殊政策](https://www.chromium.org/administrators/policy-list-3/cookie-legacy-samesite-policies)，暫時將 Chrome 瀏覽器改回原本的運作方式。
* 如果您有同時供第一方和第三方使用的 Cookie，可以考慮針對這兩種情況使用不同的 Cookie，以便在第一方使用情境中享有 `SameSite=Lax` 的安全優勢。

「[SameSite Cookie 說明](https://web.dev/samesite-cookies-explained?hl=zh-tw)」一文針對上述情況提供了具體指南，並設有提問與回報問題的管道。

如要測試 Chrome 的新行為對網站或您管理的 Cookie 有何影響，請在 Chrome 76 以上版本中前往 `chrome://flags`，然後啟用「SameSite by default cookies」和「Cookies without SameSite must be secure」實驗設定。此外，系統也會自動為 Chrome 79 Beta 版的部分使用者啟用這些實驗設定。部分 Beta 版使用者在啟用實驗設定後，可能會遇到尚未支援新模式的服務不相容的問題。如要解決問題，使用者可以前往 `chrome://flags` 停用 Beta 版實驗設定。

如果您管理的是僅限由同網站存取的 Cookie (同網站 Cookie)，則無須採取任何行動；Chrome 會自動禁止外部實體存取這類 Cookie，即使缺少 SameSite 屬性或未設定任何值亦然。不過，我們強烈建議您運用適當的 SameSite 值 (Lax 或 Strict)，不要依賴預設的瀏覽器行為，因為不是所有瀏覽器都預設保護同網站 Cookie。

最後，如果您擔心廠商或自家網站的其他服務供應商是否做好準備，可以在網頁含有缺少必要設定的跨網站 Cookie 時，透過 Chrome 77 以上版本查看開發人員工具控制台是否顯示警告訊息：

中跨網站資源相關聯的 Cookie 已完成設定，但缺少「SameSite」屬性" class="l10n-absolute-url-src" l10n-attrs-original-order="alt,src,class" src="https://developers.google.com/static/search/blog/images/import/8d24302a9c952d4b695790da9a91047a.png" />

為了因應 2 月推出的 Chrome 80 版，部分供應商 (包括某些 Google 服務) 必須在前幾個月做出必要調整；建議您與合作夥伴聯絡，確認對方是否做好準備。

發文者：Chrome 與網路平台合作關係部門的 Barb Palser
