# Search Console Discover report now includes Chrome data
- **發佈日期**: 2021-02-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/02/search-console-performance-discover-chrome
- **來源類型**: article
- **來源集合**: google-search-central
---
Tuesday, February 02, 2021

Discover is a popular way for users to stay up-to-date on all their favorite topics, even when they’re not searching for something specific.
Publishers and site owners can already access the [Discover performance report](https://support.google.com/webmasters/answer/9216516)
to review important metrics about how their websites perform in Discover in the Google app on Android or iOS.

Another way people encounter Discover content is when they open a new tab in Chrome on Android or iOS, where Discover also lives.
Previously, Discover traffic from Chrome hasn’t been included in the existing Discover performance report.

We are now providing a single place in Search Console to see all your site’s Discover impressions and click stats, including from Chrome.

![Google Search Console Discover performance report](/static/search/blog/images/search-console-discover-performance-report.png "Google Search Console Discover performance report")

Over the course of the next few months, this data will gradually appear in your site's Search Console Discover performance report.
This means your site's reported traffic levels may rise from where they were.

Starting with a small percentage of traffic today and rolling out gradually, Discover traffic from Chrome will be using a
new [origin](https://web.dev/articles/same-site-same-origin#origin) referrer `https://www.google.com/`
so it is consistent with what’s used for Discover on the Google app. This will replace the previous
`www.googleapis.com/auth/chrome-content-suggestions` referrer.

For questions or comments on the report, you can drop by our Search Central [help forums](https://support.google.com/webmasters/go/community),
or contact us through [our other channels](/search/help). Also see
our [Google Discover and your website](/search/docs/advanced/mobile/google-discover) page that explains more
about how Discover content may appear, along with tips to consider.

Posted by Janice Wong and [Ziv Hodak](/search/blog/authors/ziv-hodak), Product Managers
