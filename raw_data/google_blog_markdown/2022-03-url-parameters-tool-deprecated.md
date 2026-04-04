# Spring cleaning: the URL Parameters tool
- **發佈日期**: 2022-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2022/03/url-parameters-tool-deprecated
- **來源類型**: article
- **來源集合**: google-search-central
---
Monday, March 28, 2022

**In short:** We're deprecating the URL Parameters tool in Search Console in 1 month. There's
no action required from the current users of the tool.

![Screenshot of the URL parameter tool at its launch](/static/search/blog/images/oldurlparam.png)

The URL Parameters tool in 2009

When the URL Parameters tool launched in
[2009](/search/blog/2009/10/new-parameter-handling-tool-helps-with) in Search Console's
predecessor, Webmaster Tools, the internet was a much wilder place than it is today.
`SessionID` parameters were very common, CMSes had trouble organizing parameters, and
browsers often broke links. With the URL Parameters tool, site owners had granular control over
how Google crawled their site by specifying how certain parameters affect the content on their
site.

Over the years, Google became much better at guessing which parameters are useful on a site and
which are —plainly put— useless. In fact, only about 1% of the parameter
configurations currently specified in the URL Parameters tool are useful for crawling. Due to the
low value of the tool both for Google and Search Console users, we're deprecating the URL
Parameters tool in 1 month.

Going forward you don't need to do anything to specify the function of URL parameters on your
site, Google's crawlers will learn how to deal with URL parameters automatically.

If you need more control, you can use
[robots.txt rules](/search/docs/crawling-indexing/robots/intro) (for example, you can specify
parameter orders in an `allow` rule) or use
[`hreflang`](/search/docs/specialty/international/localized-versions) to specify
language variations of content.

If you have questions or comments, you can catch us on
[Twitter](https://twitter.com/googlesearchc).

Posted by [Gary Illyes](https://garyillyes.com/+), Search Team
