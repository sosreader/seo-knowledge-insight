# Google 如何為語言或指令碼不一致的文件產生標題
- **發佈日期**: 2022-06-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/06/title-script-misalignment?hl=zh-tw
- **來源類型**: article
- **來源集合**: google-search-central-zh
---
2022 年 6 月 3 日，星期五

我們在本週對演算法進行一些改善，以識別標題元素與內容採用不同語言或指令碼撰寫的文件，並選擇與文件語言和指令碼相似的標題。這個機制是以一般原則為根據，也就是文件標題應以主要內容的語言或指令碼撰寫。
我們[將使用網頁搜尋結果標題的標題元素以外的內容](https://developers.google.com/search/blog/2021/09/more-info-about-titles?hl=zh-tw#examples-of-going-beyond-title-elements)，而這是其中一個原因。

## 多語言標題

多語言標題會用兩種不同的語言或指令碼重複相同的詞組。
最常用的模式就是在原文標題文字中附加英文版本。

> गीतांजलि की जीवनी - Geetanjali Biography in Hindi

在這個範例中，標題是由兩個部分組成 (以連字號分隔)，以不同的語言 (北印度文和英文) 表示相同的內容。雖然標題使用兩種語言，但文件本身僅使用北印度文撰寫。我們的系統偵測到這種不一致的狀況，可能只使用北印度文的標題文字，例如：

> गीतांजलि की जीवनी

## 拉丁字母書寫的標題

音譯是指將用一種語言撰寫的內容轉換為另一種使用不同字集或字母的語言。例如，假設某首歌曲的網頁標題是以北印度文撰寫，但是經過音譯後卻使用了拉丁字元，而非北印度文的梵文字母，例如：

> jis desh me holi kheli jati hai

在這種情況下，我們的系統會嘗試使用網頁上主要的字集來尋找替代標題，在這個案例中可能是：

> जिस देश में होली खेली जाती है

## 摘要

一般來說，我們的系統通常會使用網頁的標題元素。如果是多語言或音譯標題，我們的系統會尋找符合網頁主要語言的替代文字。因此，最好是提供與網頁主要內容的語言和/或字集相符的標題。

歡迎您繼續在[論壇](https://support.google.com/webmasters/community?hl=zh-tw)中 (包括這個主題現有的[英文](https://support.google.com/webmasters/thread/122879386/your-feedback-on-titles-shown-in-search-results?hl=zh-tw)和[日文](https://support.google.com/webmasters/thread/125182163/%E6%A4%9C%E7%B4%A2%E7%B5%90%E6%9E%9C%E3%81%AB%E8%A1%A8%E7%A4%BA%E3%81%95%E3%82%8C%E3%82%8B%E3%82%BF%E3%82%A4%E3%83%88%E3%83%AB%E3%81%AB%E9%96%A2%E3%81%99%E3%82%8B%E3%83%95%E3%82%A3%E3%83%BC%E3%83%89%E3%83%90%E3%83%83%E3%82%AF?hl=ja)討論串) 提供更多意見。

發文者：Google 搜尋團隊的 [Koji Kojima](https://www.linkedin.com/in/koji-kojima-37723b263/)
