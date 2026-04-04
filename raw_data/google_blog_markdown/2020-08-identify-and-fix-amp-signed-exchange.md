# Identify and fix AMP Signed Exchange errors in Search Console
- **發佈日期**: 2020-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/08/identify-and-fix-amp-signed-exchange
- **來源類型**: article
- **來源集合**: google-search-central
---
Tuesday, August 18, 2020

Signed Exchanges (SXG) is a subset of the emerging family of specifications called
[Web Packaging](https://github.com/WICG/webpackage), which enables publishers to
safely make their content portable, while still keeping the publisher's integrity and
attribution. In 2019,
[Google Search started linking to signed AMP pages](/search/blog/2019/04/instant-loading-amp-pages-from-your-own)
served from Google's cache when available. This feature allows the content to be prefetched
without loss of privacy, while attributing the content to the right origin.

Today we are happy to announce that sites implementing SXG for their AMP pages will be able to
understand if there are any issues preventing Google from serving the SXG version of their page
using the Google AMP Cache.

Use the
[AMP report](https://support.google.com/webmasters/answer/7450883#sgx_warning_list)
to check if your site has any SXG related issues - look for issues with 'signed exchange' in
their name. We will also send emails to alert you of new issues as we detect them.

![Signed exchange report in Search Console](/static/search/blog/images/import/5e3a2136782093be8ecd2a1985f1573a.png)

To help with debugging and to verify a specific page is served using SXG, you can inspect a URL
using the
[URL Inspection Tool](https://support.google.com/webmasters/answer/9012289)
to find if any SXG related issues appear on the AMP section of the analysis.

You can diagnose issues affecting the indexed version of the page or use the "live" option which
will check validity for the live version currently served by your site.

![Signed exchange issue detail in Search Console](/static/search/blog/images/import/ca5e60bd413d590b1d548b4353fd9152.png)

To learn more about the types of SXG issues we can report on, check out this
[Help Center Article](https://support.google.com/webmasters/answer/7450883#sgx_warning_list)
on SXG issues. If you have any questions, you can ask in the
[help community](https://support.google.com/webmasters/threads?thread_filter=(category:search_console))
or the Google Webmasters [Twitter handle](https://twitter.com/googlesearchc).

Posted by [Amir Rachum](https://amir.rachum.com/), Search Console Software Engineer and Jeffrey Jose, Google Search Product Manager.
