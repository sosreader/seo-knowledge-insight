# Timing for bringing page experience to Google Search
- **發佈日期**: 2020-11-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2020/11/timing-for-page-experience
- **來源類型**: article
- **來源集合**: google-search-central
---
Tuesday, November 10, 2020

It's been a while since we published this blog post. Some of the information may be outdated (for example, some images may be missing, and some links may not work anymore). Check out our updated documentation on [page experience](/search/docs/appearance/page-experience).

[This past May](/search/blog/2020/05/evaluating-page-experience), we announced that
[page experience](/search/docs/appearance/page-experience) signals would be included in
Google Search ranking. These signals measure how users perceive the experience of interacting with
a web page and contribute to our ongoing work to ensure people get the most helpful and enjoyable
experiences from the web. In the past several months, we've seen a median 70% increase in the
number of users engaging with Lighthouse and PageSpeed Insights, and many site owners using Search
Console's Core Web Vitals report to identify opportunities for improvement.

Today we're announcing that the page experience signals in ranking will roll out in May 2021.
The new page experience signals combine Core Web Vitals with our existing search signals including
[mobile-friendliness](/search/blog/2015/02/finding-more-mobile-friendly-search),
[HTTPS-security](/search/blog/2016/11/heres-to-more-https-on-web), and
[intrusive interstitial
guidelines](/search/blog/2016/08/helping-users-easily-access-content-on).

![A diagram illustrating the components of Search's signal for page experience](/static/search/blog/images/page-experience-signal.png)

The change for non-AMP content to become eligible to appear in the mobile Top Stories feature in
Search will also roll out in May 2021. Any page that meets the
[Google
News content policies](https://support.google.com/news/publisher-center/answer/6204050) will be eligible and we will prioritize pages with great page experience,
whether implemented using AMP or any other web technology, as we rank the results.

In addition to the timing updates described above, we plan to test a visual indicator that highlights
pages in search results that have great page experience.

## A New Way of Highlighting Great Experiences in Google Search

We believe that providing information about the quality of a web page's experience can be helpful
to users in choosing the search result that they want to visit. On results, the snippet or image
preview helps provide topical context for users to know what information a page can provide. Visual
indicators on the results are another way to do the same, and we are working on one that
identifies pages that have met all of the page experience criteria. We plan to test this soon and
if the testing is successful, it will launch in May 2021 and we'll share more details on the
progress of this in the coming months.

## The Tools Publishers Need for Improving Page Experience

To get ready for these changes, we have released a variety of tools that publishers can use to
start improving their page experience. The first step is doing a site-wide audit of your pages to
see where there is room for improvement. Search Console's
[report](https://support.google.com/webmasters/answer/9205520) for
Core Web Vitals gives you an overview of how your site is doing and a deepdive into issues. Once
you've identified opportunities, [PageSpeed
Insights](https://web.dev/articles/vitals-tools#pagespeed-insights) and [Lighthouse](https://web.dev/articles/vitals-tools#lighthouse)
can help you as you iterate on fixing any issues that you've uncovered. Head over to
[web.dev/vitals-tools](https://web.dev/articles/vitals-tools) for a roundup of
all the tools you need to get started.

Additionally, AMP is [one
of the easiest and cost-effective ways](https://blog.amp.dev/2020/11/10/create-great-page-experiences-with-amp/) for publishers looking to achieve great page experience
outcomes. Based on the [analysis](https://blog.amp.dev/2020/10/13/meet-amps-page-experience-guide/)
that the AMP team has done, the majority of the AMP pages achieve great page experiences. If
you're an AMP publisher, check out the recently launched [AMP
Page Experience Guide](https://amp.dev/page-experience), a diagnostic tool that provides developers with actionable advice.

We continue to support AMP content in Google Search. If you publish an AMP version of your content,
Google Search will link to that cache-optimized AMP version to help optimize delivery to users,
just as is the case today.

## Conclusion

At Google Search our mission is to help users find the most relevant and quality sites on the web.
The goal with these updates is to highlight the best experiences and ensure that users can find
the information they're looking for. Our work is ongoing, which is why we plan to incorporate more
page experience signals going forward and update them on a yearly basis. We hope that the
[tools and resources](/search/docs/appearance/page-experience) we've provided make it
easier for you to create great websites, and thereby build a web ecosystem that users love.

If you have questions or feedback, please visit our
[help forums](https://support.google.com/webmasters/community/) or let
us know through [Twitter](https://twitter.com/googlesearchc).

Posted by [Jeffrey Jose](https://twitter.com/jeffjose),
Product Manager on Search

---

## Updates

* **Update on June 15, 2021**: The page experience update is rolling out to all users globally.
  It will be complete by the end of August 2021.
* **Update on August 4, 2021**:
  [Clarified that Safe Browsing isn't used as a ranking signal](/search/blog/2021/08/simplifying-the-page-experience-report).
  Safe Browsing systems continue to play an important role to keep users of Google Search safe,
  and any flags will continue to be surfaced in Search Console outside of Page Experience
  report.
* **Update on January 31, 2024**:
  [Interaction to Next Paint (INP) will replace FID](https://web.dev/blog/inp-cwv-march-12)
  as a part of Core Web Vitals on March 12, 2024.
* **Update on March 12, 2024**:
  [Interaction to Next Paint (INP) has replaced FID](https://web.dev/blog/inp-cwv-launch) as a part of Core Web Vitals.
