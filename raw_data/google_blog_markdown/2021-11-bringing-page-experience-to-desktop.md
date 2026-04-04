# Timeline for bringing page experience ranking to desktop
- **發佈日期**: 2021-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/11/bringing-page-experience-to-desktop
- **來源類型**: article
- **來源集合**: google-search-central
---
Thursday, November 4, 2021

It's been a while since we published this blog post. Some of the information may be outdated (for example, some images may be missing, and some links may not work anymore). Check out our updated documentation on [page experience](/search/docs/appearance/page-experience).

At I/O 2021, we [previewed](https://youtu.be/h00kn5J-F2Q?t=430) our
plans to bring page experience ranking to desktop. Today we're announcing more details, including
the timeline for these changes. This work builds on top of the [page
experience update](/search/blog/2021/04/more-details-page-experience) we rolled out on mobile between June and August 2021.

## Rollout will begin in February 2022

We'll begin using page experience as part of our desktop ranking systems beginning in February
2022. The rollout will be complete by the end of March 2022. This ranking launch will be based on
the same [page experience signals](/search/docs/guides/page-experience) that we rolled
out for mobile earlier this year. We are also planning to help site owners understand how their
desktop pages are performing with regards to page experience using a Search Console report which
will launch before desktop becomes a ranking signal.

This means the same three [Core Web Vitals metrics](https://web.dev/articles/vitals):
[LCP](https://web.dev/articles/lcp), [FID](https://web.dev/articles/fid),
and [CLS](https://web.dev/articles/cls), and their associated thresholds will
apply for desktop ranking. Other aspects of page experience signals, such as HTTPS security and
absence of intrusive interstitials, will remain the same as well. While the mobile-friendliness
signal continues to be a part of mobile ranking, it won't be a factor for desktop. When a site
has [separate desktop and mobile URLs](/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing)
with an appropriate configuration, the desktop signal is based on the URLs that desktop users see.

| Factor | Mobile | Desktop |
| --- | --- | --- |
| Largest Contentful Paint (LCP) |  |  |
| Cumulative Layout Shift (CLS) |  |  |
| First Input Delay (FID) |  |  |
| HTTPS Security |  |  |
| Absence of intrusive interstitials |  |  |
| Mobile friendliness |  | (Not applicable) |

We hope this blog post provides you with details for you to [understand
and optimize your page experience](/search/docs/appearance/page-experience#optimize) in preparation for the upcoming changes, and in turn help you build better websites.

If you have questions or feedback, please visit our [help
forums](https://support.google.com/webmasters/community/) or let us know through [Twitter](https://twitter.com/googlesearchc).

Posted by Jeffrey Jose, Product Manager on Search

---

## Updates

* **Update on January 17, 2022**: Search Console now has a dedicated 'Desktop' section in the
  [Page Experience report](https://search.google.com/search-console/page-experience).
* **Update on February 22, 2022**: The page experience update is now slowly
  rolling out for desktop. It will be completed by the end of March 2022.
* **Update on January 31, 2024**:
  [Interaction to Next Paint (INP) will replace FID](https://web.dev/blog/inp-cwv-march-12)
  as a part of Core Web Vitals on March 12, 2024.
* **Update on March 12, 2024**:
  [Interaction to Next Paint (INP) has replaced FID](https://web.dev/blog/inp-cwv-launch)
  as a part of Core Web Vitals.
