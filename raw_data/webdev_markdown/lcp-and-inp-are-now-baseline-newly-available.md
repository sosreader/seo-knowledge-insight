# LCP and INP are now Baseline Newly available
- **發佈日期**: 2025-12-17
- **作者**: web.dev
- **來源 URL**: https://web.dev/blog/lcp-and-inp-are-now-baseline-newly-available?hl=en
- **來源類型**: article
- **來源集合**: web-dev
---
Published: December 17, 2025

**Celebration:** These web features are now available in all three major browser engines, and are **Baseline Newly available** as of December 12, 2025.

With the release of Safari 26.2 on December 12th, web performance got a fantastic end of year gift with [Largest Contentful Paint (LCP)](/articles/lcp) and [Interaction to Next Paint (INP)](/articles/inp) becoming Baseline Newly available as the latest version of all major browsers now include the [Largest Contentful Paint API](https://developer.mozilla.org/docs/Web/API/LargestContentfulPaint) and [Event Timing API](https://developer.mozilla.org/docs/Web/API/PerformanceEventTiming) needed to measure these metrics. This was part of the [Interop 2025 project](/blog/interop-2025#core_web_vitals), and it's great to see these delivered this year!

## What this means

The [Core Web Vitals](/articles/vitals) have become a widely adopted standard for measuring web page experience both for web developers and with business stakeholders. They attempt to summarize the complex story of web performance into a number of key measures of how fast a page loads (LCP), how quickly it responds to interactions (INP), and how stable its contents are (CLS).

For a long time, these were only measurable in Chromium-based browsers such as Chrome and Edge. They were also not available at all on iOS devices where all browsers use the WebKit browser engine that powers Safari. This causes a blindspot where large proportions of a site's visitors may be having a very different experience without a site's knowledge. While many web performance improvements do benefit all browsers, some techniques and APIs are only available in some browsers. Additionally, the way browsers work internally, load pages, and handle interactions can be different from one another. Having only a partial view of your site's performance is far from ideal.

With all major browsers now supporting two of these metrics, we can now have a better view on the key loading and interactivity of a website. This will allow site owners to better understand performance issues and identify any improvements they can make, ultimately benefiting users and [business metrics](/case-studies).

## Will data from other browsers feed CrUX?

No. The [Chrome User Experience Report (CrUX)](https://developer.chrome.com/docs/crux) is only based on [eligible Chrome users](https://developer.chrome.com/docs/crux/methodology) and this won't change. This applies also to downstream systems that use this data like [PageSpeed Insights](https://pagespeed.web.dev/), [Google Search Console](https://developers.google.com/search/docs/appearance/core-web-vitals), and [CrUX Vis](https://cruxvis.withgoogle.com/#/).

This will also continue to exclude Chrome iOS users since they use the WebKit browser engine.

## How to measure from other browsers

CrUX data is still useful as a summary of a site's performance, and to benchmark against other sites on the web. However, as it is a high-level summary, we have [long recommended measuring more detailed field data](/articles/vitals#field_tools_to_measure_core_web_vitals) to help identify and improve performance.

Real User Monitoring (RUM) tools are now able to collect the additional field data, including those measured through the [web-vitals library](https://github.com/GoogleChrome/web-vitals) from the Chrome team. In most cases, this should automatically start to be included though your existing solutions, but check with your RUM provider if you have any questions.

Be aware that there [can be differences in RUM and CrUX](/articles/crux-and-rum-differences), and that is potentially even more true now these metrics are available in even more browsers that are not included in CrUX.

## Are there any differences in the implementations?

While all browser engines do broadly the same task in loading and displaying web pages, there are many differences in how these browsers are built, and in particular in their rendering pipelines that translate a website's code (primarily HTML, CSS, and JavaScript) into pixels on the screen.

The end of the rendering loop is broadly interoperable and is defined as the [`paintTime`](https://www.w3.org/TR/paint-timing/#the-paint-timing-mixin). However after this, there is a later `presentationTime` which is implementation-specific and aims to indicate when the pixels are actually drawn on the screen. Chrome measures LCP up until the end of `presentationTime`, while Firefox and Safari don't include `presentationTime` and so measure until the earlier `paintTime`. This results in slight milliseconds of difference between the measures. From Chrome 145, [the `paintTime` measure will also be exposed for LCP](https://chromestatus.com/feature/5162859838046208) for those that want to be able to compare like for like across browsers.

The same difference applies to INP as well.

The fact that other browsers have implemented these metrics, has helped identify [some outstanding issues](https://github.com/w3c/largest-contentful-paint/issues/) to be clarified and better defined. This again may lead to slight differences—though these are mostly in edge cases. This is the benefit of having multiple implementations and eyes on an API! We will [continue to work on these](https://github.com/web-platform-tests/interop/issues/1173) as well as any other improvements to the metrics.

However, despite these small differences, we are confident that LCP and INP are broadly interoperable, so we are happy with them being labelled Baseline Newly available. Those implementing RUM solutions or digging deep into the data may notice some of these differences, but web developers should be confident in measuring these metrics across browsers despite these minor differences.

## What about browsers that don't support these APIs?

Baseline Newly available features are only just available in the latest versions of all major browsers. Your user base may not immediately upgrade, or may not be able to upgrade depending on their operating system and provider. After 30 months, they will be considered Baseline Widely available as most users will likely be on supporting browsers.

However, as a measurement API rather than a core functionality of a website, you can safely measure these metrics for supporting browsers—as you've likely done up until now. Just be aware that you may be seeing a filtered view of your users—those who upgraded—particularly in the first few months.

## What about Cumulative Layout Shift?

The third Core Web Vital is [Cumulative Layout Shift (CLS)](/articles/cls), and is not part of the Interop 2025 project—though it has been [proposed for Interop 2026](https://github.com/web-platform-tests/interop/issues/1057). For now, it is not supported beyond Chromium-based browsers.

## Conclusion

The [Web Vitals](/articles/vitals) initiative's aim was to improve web performance by creating a set of standard APIs for the web platform to allow key metrics to be measured and broadly understood by website owners. It's great to see two of these metrics now being supported by all main browsers. We look forward to seeing what insights these provide website owners, and how this leads to improved user experiences!
