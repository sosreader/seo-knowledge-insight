# Screaming Frog SEO Spider Update – Version 23.0
- **發佈日期**: 2025-10-20
- **作者**: screamingfrog
- **來源 URL**: https://www.screamingfrog.co.uk/blog/seo-spider-23/
- **來源類型**: article
- **來源集合**: screaming-frog
---
We’re quite pleased to announce **Screaming Frog** SEO Spider version 23.0, codenamed internally as ‘Rush Hour’.

The SEO Spider has a number of integrations, and the core of this release is keeping these integrations updated for users to avoid breaking changes, as well as smaller feature updates.

So, let’s take a look at what’s new.

---

## 1) Lighthouse & PSI Updated to Insight Audits

Lighthouse and PSI are being updated with the latest improvements to PageSpeed advice, which has now been reflected in the SEO Spider.

This comes as part of the evolution of [Lighthouse performance audits](https://developer.chrome.com/blog/moving-lighthouse-to-insights) and DevTools performance panel insights into consolidated and consistent audits across tooling.

![PSI Insight Audits](https://www.screamingfrog.co.uk/wp-content/uploads/2025/10/psi-insight-audits.png)

In [Lighthouse 13](https://developer.chrome.com/blog/lighthouse-13-0) some audits have been retired, while others have been consolidated or renamed.

The updates are fairly large and include changes to audits and naming in Lighthouse that users have long been familiar with, including breaking changes to the API. For example, previously separate insights around images have been consolidated into a single ‘Improve Image Delivery’ audit.

There are pros and cons to these changes, but after the initial frustration with having to re-learn some processes, the changes do mostly make sense.

The groupings make providing some recommendations more efficient, and it’s still largely possible to get the granular detail required in bulk from consolidated audits.

To get ahead of the (breaking) changes, we have updated our PSI integration to match those across Lighthouse and PSI for consistency.

The changes to [PageSpeed Issues](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/) are listed below.

**7 New Issues –**

* [Document Request Latency](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/document-request-latency/)
* [Improve Image Delivery](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/improve-image-delivery/)
* [LCP Request Discovery](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/lcp-request-discovery/)
* [Forced Reflow](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/forced-reflow/)
* [Avoid Enormous Network Payloads](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/avoid-enormous-network-payloads/)
* [Network Dependency Tree](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/network-dependency-tree/)
* [Duplicated JavaScript](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/duplicated-javascript/)

**11 Removed or Consolidated Issues –**

* Defer Offscreen Images
* Preload Key Requests
* Efficiently Encode Images (now part of ‘[Improve Image Delivery](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/improve-image-delivery/)‘)
* Properly Size Images (now part of ‘[Improve Image Delivery](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/improve-image-delivery/)‘)
* Serve Images in Next-Gen Formats (now part of ‘[Improve Image Delivery](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/improve-image-delivery/)‘)
* Use Video Formats for Animated Content (now part of ‘[Improve Image Delivery](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/improve-image-delivery/)‘)
* Enable Text Compression (now part of ‘[Document Request Latency](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/document-request-latency/)‘)
* Reduce Server Response Times (TTFB) (now part of ‘[Document Request Latency](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/document-request-latency/)‘)
* Avoid Multiple Page Redirects (now part of ‘[Document Request Latency](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/document-request-latency/)‘)
* Preconnect to Required Origins (now part of ‘[Network Dependency Tree](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/network-dependency-tree/)‘)
* Image Elements Do Not Have Explicit Width & Height (now part of ‘[Layout Shift Culprits](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/avoid-large-layout-shifts/)‘)

**6 Renamed Issues –**

* Eliminate Render-Blocking Resources (now ‘[Render Blocking Requests](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/eliminate-render-blocking-resources/)‘)
* Avoid Excessive DOM Size (now ‘[Optimize DOM Size](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/avoid-excessive-dom-size/)‘)
* Serve Static Assets with an Efficient Cache Policy (now ‘[Use Efficient Cache Lifetimes](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/serve-static-assets-with-an-efficient-cache-policy/)‘)
* Ensure Text Remains Visible During Webfont Load (now ‘[Font Display](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/ensure-text-remains-visible-during-webfont-load/)‘)
* Avoid Large Layout Shifts (now ‘[Layout Shift Culprits](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/avoid-large-layout-shifts/)‘)
* Avoid Serving Legacy JavaScript to Modern Browsers (now ‘[Legacy JavaScript](https://www.screamingfrog.co.uk/seo-spider/issues/pagespeed/avoid-serving-legacy-javascript-to-modern-browsers/)‘)

Older metrics, such as first meaningful paint, have also been removed.

If you’re running [automated crawl reports in Looker Studio](https://www.screamingfrog.co.uk/seo-spider/tutorials/how-to-automate-crawl-reports-in-data-studio/) and have selected PageSpeed data, then you will find that some columns will not populate after updating.

The next time you ‘edit’ the scheduled crawl task, you will also be required to make some updates due to these breaking changes.

The SEO Spider provides an in-app warning, and advice in our [Looker Studio Export Breaking Changes FAQ](https://www.screamingfrog.co.uk/seo-spider/faq/#looker-studio-reported-changed) on how to solve it quickly.

---

## 2) Ahrefs v3 API Update

The SEO Spider has been updated to integrate v3 of the Ahrefs API after they announced plans to retire v2 of the API and introduced [Ahrefs Connect](https://docs.ahrefs.com/docs/ahrefs-connect/introduction) for apps.

![Ahrefs v3 API](https://www.screamingfrog.co.uk/wp-content/uploads/2025/10/ahrefs-v3.png)

This allows users on *any paid plan* (not just enterprise) to access data from their latest API via our integration. The format is similar to the previous integration; however, users will be required to re-authenticate using the new OAuth flow introduced by Ahrefs.

You’re able to pull metrics around backlinks, referring domains, URL rating, domain rating, organic traffic, keywords, cost and more.

![Ahrefs config metrics](https://www.screamingfrog.co.uk/wp-content/uploads/2025/10/ahrefs-config.png)

Metrics have been added, removed and renamed where appropriate. Read more on the [Ahrefs integration](https://www.screamingfrog.co.uk/seo-spider/user-guide/configuration/#ahrefs) in our user guide.

---

## 3) Auto-Deleting Crawls (Crawl Retention)

Crawls are automatically saved and available to be opened or deleted via the ‘File > Crawls’ menu in default database storage mode. To date, the only way to delete database crawls was to delete them manually via this dialog.

However, users are now able to automate deleting crawls via new ‘[Crawl Retention](https://www.screamingfrog.co.uk/seo-spider/user-guide/configuration/#crawl-retention)‘ settings available in ‘File > Settings > Crawl Retention’.

You do not need to worry about disappearing crawls, as by default the crawl retention settings are set to ‘Never’ automatically delete crawls.

![Crawl Retention settings](https://www.screamingfrog.co.uk/wp-content/uploads/2025/10/crawl-retention.png)

The crawl retention functionality allows users to automatically delete crawls after a period of time, which can be useful for anyone who doesn’t want to keep crawls but does want to take advantage of the scale that database [storage mode](https://www.screamingfrog.co.uk/seo-spider/user-guide/configuration/#storage) offers (over memory storage).

As part of this feature, we also introduced the ability to ‘Lock’ projects or specific crawls in the ‘File > Crawls’ menu from being deleted. If you wish to lock a single crawl or all crawls in a project, just right click and select ‘Lock’.

!['Lock' crawls from crawl retention settings](https://www.screamingfrog.co.uk/wp-content/uploads/2025/10/locking-crawls.png)

For project folders, this will lock all existing and future crawl files, including scheduled crawls, from being automatically deleted via the retention policy settings.

---

## 4) Semantic Similarity Embedding Rules

You can now set embedding rules via ‘Config > Content > Embeddings’, which allows you to define URL patterns for [semantic similarity analysis](https://www.screamingfrog.co.uk/seo-spider/tutorials/how-to-identify-semantically-similar-pages-outliers/).

![Embedding Filter Rules](https://www.screamingfrog.co.uk/wp-content/uploads/2025/10/embedding-filter-rules.png)

This means if you’re using [vector embeddings for redirect mapping](https://www.screamingfrog.co.uk/seo-spider/tutorials/how-to-use-vector-embeddings-for-redirect-mapping/), as an example, you can add a rule to only find semantic matches for the staging site on the live website (so pages from the staging website itself are not considered as well).

![Using embeddings for redirect mapping](https://www.screamingfrog.co.uk/wp-content/uploads/2025/10/embedding-filter-rules-results.png)

In the above, the closest semantically similar address can only be the staging site for the live site.

This can also be used in a variety of other ways, such as if you wanted to see the closest matches between two specific areas of a website, or between a page and multiple external pages.

---

## 5) Display All Links in Visualisations

It’s now possible to see all inlink and outlink relationships in our [site visualisations](https://www.screamingfrog.co.uk/seo-spider/tutorials/site-architecture-crawl-visualisations/).

You can right-click on a node and select to ‘Show Inlinks’, ‘Show Inlinks to Children’ of a node, or perform the same for ‘Outlinks’.

![Show Inlinks in a Crawl Visualisation](https://www.screamingfrog.co.uk/wp-content/uploads/2025/10/show-inlinks-crawl-visualisation.png)

This will update the visualisation to show all incoming links, which can be useful when analysing internal linking to a page or a section of a website –

![Displaying all Inlinks in the crawl visualisation](https://www.screamingfrog.co.uk/wp-content/uploads/2025/10/show-inlinks-crawl-visualisation-clicked.png)

Linking nodes are highlighted in green, while other nodes are faded to grey.

This option is available across all force-directed diagrams, including the 3D visualisations.

[](https://www.screamingfrog.co.uk/wp-content/uploads/2025/10/inlinks-3d-vis.mp4)

---

## 6) Display Links in Semantic Content Cluster Diagram

Similar to site visualisations, you’re now also able to right-click and ‘Show Inlinks’ or outlinks within the semantic [Content Cluster Diagram](https://www.screamingfrog.co.uk/seo-spider/tutorials/how-to-identify-semantically-similar-pages-outliers/#contentcluster).

![Show Inlinks in Content Cluster Diagram](https://www.screamingfrog.co.uk/wp-content/uploads/2025/10/inlinks-content-cluster-diagram.png)

As well as viewing all internal links to a page, you can also select to ‘Show Inlinks Within Cluster’, to see if a page is benefiting from links from semantically similar pages.

![Show Inlinks within Cluster Content Cluster Diagram](https://www.screamingfrog.co.uk/wp-content/uploads/2025/10/inlinks-within-cluster-content-cluster-diagram.png)

This can be a useful way to visually identify internal link opportunities or gaps in internal linking based upon semantics.

---

## Other Updates

Version 23.0 also includes a number of smaller updates and bug fixes.

* **Limit Crawl Total Per Subdomain** – Under ‘Config > Spider > Limits’ you can limit the number of URLs crawled per subdomain. This can be useful in a variety of scenarios, such as crawling a sample number of URLs from X number of domains in list mode.
* **Improved Heading Counts** – The ‘Occurrences’ count in the [h1](https://www.screamingfrog.co.uk/seo-spider/user-guide/tabs/#h1) and [h2](https://www.screamingfrog.co.uk/seo-spider/user-guide/tabs/#h2) tabs was limited to ‘2’, as only two headings are extracted by default. While only the first two h1 and h2 headings will continue to be extracted, the occurrence number will show the total number of each on a page.
* **Move Up & Down Buttons for Custom Search, Extraction & JS for Ordering** – The ordering (top to bottom) impacts how they are displayed in columns in tabs (from left to right), so this can now be adjusted without having to delete and add.
* **Configurable Percent Encoding of URLs** – While percent encoding of URLs is uppercase, a small number of servers will redirect to lowercase only and error. This is therefore configurable in ‘Config > URL Rewriting’.
* **Irish Language Spelling & Grammar Support** – Just for the craic!
* **Updated AI Models for System Prompts & JS Snippets** – OpenAI system prompts have been updated to use ‘gpt-5-mini’, Gemini to ‘gemini-2.5-flash’ and Anthropic to ‘claude-sonnet-4-5’. As always, we recommend reviewing these models, and costs prior to use.
* **New Exports & Reports** – There’s a new ‘All Error Inlinks’ bulk exports under ‘Bulk Export > Response Codes > Internal/External’ which combine no response, 4XX and 5XX errors. There is also a new ‘Redirects to Error’ report under ‘Reports > Redirects’, which includes any redirects which end up blocked, no response, 4XX or 5XX error.
* **Redirection (HTTP Refresh) Filter** – While these were reported and followed, a new filter has been introduced to better report these.

That’s everything for version 23.0!

Thanks to everyone for their continued support, feature requests and feedback. Please let us know if you experience any issues with this latest update via our [support](https://www.screamingfrog.co.uk/seo-spider/support/).

---

## Small Update – Version 23.1 Released 18th November 2025

We have just released a small update to version 23.1 of the SEO Spider. This release is mainly bug fixes and small improvements –

* Add [Shopify web bot auth](https://help.shopify.com/en/manual/promoting-marketing/seo/crawling-your-store) header names to presets in HTTP Header config.
* Add ‘Indexability’ columns to ‘Directives’ tab.
* Mark Google rich result feature ‘Practice Problems’ as deprecated.
* Remove deprecation warning for ‘Book Actions’ Google rich result feature.
* Updated Gemini image generation default model.
* Rev to Java 21.0.9.
* Fixed issue not showing srcset images in lower ‘Image Details’ tab, when ‘Extract Images from srcset Attribute’ not enabled.
* Fixed ‘Reset Columns for All Tables’ not working in certain scenarios.
* Fixed issue with Multi-Export hanging when segments are configured.
* Fixed issue with old configs defaulting to percent encoding mode ‘none’, rather than upppercase.
* Fixed right-click Inlinks/Outlinks etc not working in some visualisations.
* Fixed the content cluster diagram axis in dark mode.
* Fixed spell check happening on partial words.
* Fixed bug with GA/GSC accounts from another instance affecting each other.
* Fixed ‘Blocked by Robots.txt’ URLs also appearing as ‘No Response’ filter.
* Fixed various unique crashes.

## Small Update – Version 23.2 Released 16 December 2025

We have just released a small update to version 23.2 of the SEO Spider. This release is mainly bug fixes and small improvements –

* Re-introduce the PageSpeed Opportunities Summary report. Unfortunately, not all data is available for all PageSpeed opportunities.
* Updated trusted certificate discovery, so the site visited is now configurable.
* Updated the AlsoAsked Custom JS Snippet.
* Updated log4j to version 2.25.2.
* Fixed cells with green text being invisible when highlighted.
* Fixed –load-crawl uses wrong config to validate exports.
* Fixed issue with showing too many Google Chrome Console errors.
* Fixed issue with ‘Low Memory’ warning not showing in some low memory situations.
* Fixed issue with crawls sometimes freezing on macOS.
* Fixed issue with ‘Archive Website’ causing ‘undefined’ image URL to be loaded.
* Fixed issue with crawl comparison fogetting config.
* Fixed issue with Ahrefs failing for values outside of 32bit signed range.
* Fixed issue with visual custom extraction using the saved user agent rather than from the current editing config.
* Fixed issue with missing argument for option: crawl-google-sheet in Scheduled Task.
* Fixed various unique crashes.

## Small Update – Version 23.3 Released 18 February 2026

We have just released a small update to version 23.3 of the SEO Spider. This release is mainly bug fixes and small improvements –

* With Google’s update on [Googlebot’s file size limits](https://developers.google.com/search/docs/crawling-indexing/googlebot?_gl=1*1ykadrw*_up*MQ..*_ga*NjA1NDM0NzYzLjE3NzEyMzEwNzk.*_ga_SM8HXJ53K2*czE3NzEyMzEwNzgkbzEkZzAkdDE3NzEyMzEwNzgkajYwJGwwJGgw#how-googlebot-accesses-your-site) actually being 2mb rather than previously communicated 15mb, we have updated our [SEO issues](https://www.screamingfrog.co.uk/seo-spider/issues/) in the tool to ‘[HTML Document Over 2MB](https://www.screamingfrog.co.uk/seo-spider/issues/validation/html-document-over-2mb/)‘ and ‘[Resource Over 2mb](https://www.screamingfrog.co.uk/seo-spider/issues/validation/resource-over-2mb/)‘ and made the limits configurable in ‘Config > Spider > Preferences’.
* Removed deprecated ‘Gemini text-embedding-004’ and replaced with ‘gemini-embedding-001’ for default Gemini embedding prompts.
* Created a ‘[Non-Indexable Page Inlinks Only](https://www.screamingfrog.co.uk/seo-spider/issues/links/non-indexable-page-inlinks-only/)‘ bulk export, available via ‘Bulk Export > Links’.
* Rev Java to 21.0.10.
* Updated Log4j to 2.25.3 to fix TLS hostname issue.
* Fixed issue with only account name being used for command line GSC & GA4 crawls and account properties being ignored.
* Fixed issue with Content Cluster Diagram segment names not being escaped.
* Fixed issue with Cluster 0 showing in Content Cluster Diagram.
* Fixed various unique crashes.

The post [Screaming Frog SEO Spider Update – Version 23.0](https://www.screamingfrog.co.uk/blog/seo-spider-23/) appeared first on [Screaming Frog](https://www.screamingfrog.co.uk).
