# 錯誤的喜劇
- **發佈日期**: 2023-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/08/where-art-thou-error?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2023 年 8 月 24 日，星期四

我們不時會收到使用者的疑問，指出 Search Console 顯示的網站資料有誤，也不時會遇到使用者不瞭解發生錯誤的原因。這很容易理解，畢竟存取網站時可能會發生許多問題。不過，所有問題都可歸結至提供存取權的特定系統，無一例外。在以下簡短的參考故事中，我們會試著說明錯誤的類型，或許你就不會覺得這些錯誤很嚇人。馬上開始吧！

## 序言

我很喜歡書，小時候大家都夢想成為太空人和消防員時，我卻想開一間圖書館，並蓋在城堡裡。但後來我開始思考，大家造訪這間新圖書館、瀏覽書架上的書籍時，可能會遇到的所有問題。如你所見，我的城堡位在偏遠地區，而且每年都會擴建 (比如蓋護城河)，這讓繪製地圖的當地製圖師十分困擾。

## 第 1 章：DNS 錯誤

既然是城堡，位置就會有點隱密難找，但有地圖可以看，所以不用擔心。然而，如果地圖已過時，因而沒有標示護城河，或是過於老舊而字跡斑駁，那會怎樣樣？

![火柴人正在查看地圖，找不到通往圖書館的路](https://developers.google.com/static/search/blog/images/sticks/stick-no-path.jpg?hl=zh-tw)

這就是 DNS 錯誤 (與常見認知不同，其實與 Dungeons N Snakes 或 Dangerous Navigation System 無關)：用戶端查詢地圖 (DNS 伺服器)，但因各種原因找不到位置。可能的原因包括地圖上根本沒有標示圖書館的位置，這以 DNS 術語來說就是 [`NXDOMAIN`](https://www.iana.org/assignments/dns-parameters/dns-parameters.xhtml#dns-parameters-6) 錯誤；或是使用者無法理解地圖上的語言，這約等於 DNS 術語所說的 [`FormErr`](https://www.iana.org/assignments/dns-parameters/dns-parameters.xhtml#dns-parameters-6)。

最常造成 DNS 錯誤的原因是 DNS 伺服器的設定，或是缺少某些設定。也就是說，除非你自行管理 DNS 伺服器 (為圖書館訪客繪製地圖)，否則就必須聯絡 DNS 供應商 (即當地製圖師) 修正錯誤。如果不知道自己的 DNS 供應商，請嘗試詢問代管服務供應商，或是協助你註冊網域名稱的廠商。

雖然用戶端也可能會發生問題，例如因為沒戴眼鏡而看不清地圖上的字，但問題較可能出自地圖本身。

## 第 2 章：網路錯誤

在英勇的訪客知道通往城堡圖書館的路徑後，實際前往圖書館的旅程其實可能像展開大冒險：要經過地下城、穿越充滿食人魚的護城河，有時還要與噴火龍搏鬥一番。

![橋斷了，導致火柴人無法前往圖書館](https://developers.google.com/static/search/blog/images/sticks/stick-broken-bridge.jpg?hl=zh-tw)

網路錯誤就像訪客遇到的障礙：用戶端 (瀏覽器、檢索器等) 和伺服器之間的網路元件封鎖了流量。封鎖原因可能是發生意外，例如主路由器故障，也可能是刻意為之，例如遭到防火牆封鎖。

很遺憾，偵錯就像踢到腳趾一樣令人不快：你需要從用戶端到伺服器的路徑中，找出正在封鎖流量的元件。更糟的是，路徑中可能有數十個獨立元件，大多數元件都不是由用戶端或伺服器管理，也沒有任何快速方法可找出封鎖路徑的元件。不過幸好，造成封鎖的防火牆通常位於伺服器正前方或 CDN 末端。如果不放心自行處理防火牆，建議你與代管服務供應商或 CDN 聯絡。

## 第 3 章：伺服器錯誤

訪客抵達圖書館後，在圖書館內也可能發生問題。舉例來說，可能借書證被水泡壞了、再也找不到書籍，甚至那隻與訪客在前往圖書館的路上決鬥的惡龍，可能已經噴火燒盡整座城堡。

![圖書館燃起熊熊大火，因此火柴人無法使用圖書館服務](https://developers.google.com/static/search/blog/images/sticks/stick-fire.jpg?hl=zh-tw)

這基本上就是伺服器錯誤：服務發生問題，導致訪客無法取得所需內容 (書籍)。如果你找不出問題原因，請與伺服器管理員或代管服務供應商聯絡。很遺憾，訪客們無能為力，必須空手離開圖書館。

## 第 4 章：用戶端錯誤

愛書的訪客進入圖書館後，有時可能會詢問已由其他讀者借閱而不在館內的小說，或是鎖在管制區域，不開放借閱的小說。這些就是用戶端錯誤：使用者發出某種意義上「有誤」的要求，雖然有誤的原因可能只是你目前未提供該內容。

![火柴人在圖書館內尋找編號 7 的書，但找不到。那本書似乎不在書架上，或是採用難以辨識的字型。](https://developers.google.com/static/search/blog/images/sticks/stick-no-book.jpg?hl=zh-tw)

其他時候，訪客想找的大部頭書籍位於圖書館的管制區域，訪客需要滿足特定條件才能進入該區域，例如說出通關密語。

![火柴人位於圖書館內，但無法借閱管制區域內的書籍](https://developers.google.com/static/search/blog/images/sticks/stick-no-entry.jpg?hl=zh-tw)

簡而言之，所有用戶端錯誤其實皆應由用戶端修正：如要提供協助，你可以將網址重新導向 (好比推薦其他書籍)，但在大部分情況下，系統就是無法完成用戶端的要求。

## 結語

俗話說：「結果好，一切都好。」如果訪客能排除萬難，進入圖書館、找到書籍並順利借閱，最後就能盡情閱讀他們喜愛的閃亮吸血鬼故事，或是你網站上的內容。

如要進一步瞭解錯誤內容，以及這些錯誤與 Google 搜尋的關聯，請[參閱說明文件](https://developers.google.com/search/docs/crawling-indexing/http-network-errors?hl=zh-tw)。如果你喜歡我的火柴人故事，或是想針對火柴人接下來的發展提供意見，歡迎透過帳號名稱 [@googlesearchc](https://twitter.com/googlesearchc) 或[社群論壇](https://goo.gle/sc-forum)與我們聯絡。

發文者：[Gary Illyes](https://developers.google.com/search/blog/authors/gary-illyes?hl=zh-tw)
