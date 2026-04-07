# New Location for the Google Crawlers' IP Range Files
- **發佈日期**: 2026-03-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2026/03/crawler-ip-ranges
- **來源類型**: article
- **來源集合**: google-search-central
---
Tuesday, March 31, 2026

Just a short note this time!

Currently, you find the JSON files listing Google's IP ranges under the
`/search/apis/ipranges/` directory on
`developers.google.com`. Since these ranges apply to more than
just Google Search crawlers, we're moving them to a more general location:
`developers.google.com/crawling/ipranges/`.

We've already
[updated our documentation](/crawling/docs/crawlers-fetchers/overview-google-crawlers)
to point to this new location. For the time being, the files will continue
to be available at the old `/search/` path as well to give
everyone time to update their systems. However, we encourage you to switch to
the new `/crawling/ipranges/` path as soon as possible. We will
eventually phase out the old locations and redirect them to the new ones
within 6 months.

Posted by
[Gary](/search/blog/authors/gary-illyes).
