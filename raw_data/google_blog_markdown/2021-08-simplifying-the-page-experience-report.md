# Simplifying the Page Experience report
- **發佈日期**: 2021-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2021/08/simplifying-the-page-experience-report
- **來源類型**: article
- **來源集合**: google-search-central
---
Wednesday, August 4, 2021

It's been a while since we published this blog post. Some of the information may be outdated (for example, some images may be missing, and some links may not work anymore). Check out our updated documentation on [page experience](/search/docs/appearance/page-experience).

The
[Page Experience report](https://support.google.com/webmasters/answer/10218333)
in Search Console
[launched](/search/blog/2021/04/more-details-page-experience) earlier this year to
offer publishers and site owners a way to quickly understand how their sites fare against the page
experience signals. Today, we’re launching a new version that simplifies the report by removing
the Safe Browsing and Ad Experience widgets from the Page Experience report, and fixes on how
missing data is handled.

As a reminder, the page experience ranking update started
[slowly rolling out](https://twitter.com/googlesearchc/status/1404886100087246848)
on June 15, 2021 and the rollout will be completed by August 31, 2021.

## Removal of the Safe Browsing and Ad Experience widgets

[Safe Browsing](https://safebrowsing.google.com/) systems at Google
are designed to keep users safe on the internet. Sometimes sites fall victim to third-party
hijacking, which can cause Safe Browsing warnings to be surfaced. We recognize that these issues
aren't always within the control of site owners, which is why we're clarifying that Safe Browsing
isn't used as a ranking signal and won’t feature in the Page Experience report. Any Safe Browsing
flags will continue to be surfaced in the Search Console outside of the Page Experience report.

Similarly, we're removing the
[Ad Experience](https://www.google.com/webmasters/tools/ad-experience-unverified)
widget to avoid surfacing the same information on two parts of Search Console. The Ad Experience
report will continue to be available as a standalone tool that you can use to review the status of
your site and identify ad experiences that violate the Better Ads Standards. To be clear, the Ad
Experience report was never used as a factor for page experience, so this change won't affect your
site’s page experience status.

![Updated graphic of the factors that make up page experience signal, namely Loading (LCP), Interactivity (FID), Visual Stability (CLS), Mobile Friendliness, HTTPS and No Intrusive Interstitials](/static/search/blog/images/volt-post-graphic-designed.png)

*Updated graphic of the factors that make up page experience signal, namely Loading (LCP),
Interactivity (FID), Visual Stability (CLS), Mobile Friendliness, HTTPS and No Intrusive
Interstitials.*

## Other improvements to the report

Along with the two updates mentioned above, we're rolling out more improvements to how the report
handles missing data:

* Added a "No recent data" banner to the
  [Core Web Vitals report](/static/search/blog/images/cwv-past-data.png)
  and
  [Page Experience report](/static/search/blog/images/volt-past-data.png).
* Fixed a bug that caused the report to show "Failing HTTPS" when Core Web Vitals data was
  missing.
* Rephrased the empty state text in the Page Experience report and Core Web Vitals report.

We hope the improvements make it easier to use the Page Experience report, and help you build
websites with great page experience.

If you have questions or feedback, please visit our
[help forums](https://support.google.com/webmasters/community/) or let
us know through [Twitter](https://twitter.com/googlesearchc).

Posted by Jeffrey Jose, Product Manager on Search

---

## Updates

* **Update on January 31, 2024**:
  [Interaction to Next Paint (INP) will replace FID](https://web.dev/blog/inp-cwv-march-12)
  as a part of Core Web Vitals on March 12, 2024.
* **Update on March 12, 2024**:
  [Interaction to Next Paint (INP) has replaced FID](https://web.dev/blog/inp-cwv-launch)
  as a part of Core Web Vitals.
