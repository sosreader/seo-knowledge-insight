# Supporting AVIF in Google Search
- **發佈日期**: 2024-08-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2024/08/happy-avifriday
- **來源類型**: article
- **來源集合**: google-search-central
---
Friday, August 30, 2024

Over the recent years, AVIF has become one of the most commonly used image formats on the web.
We're happy to announce that AVIF is now a [supported file type](/search/docs/crawling-indexing/indexable-file-types)
in Google Search, for Google Images as well as any place that uses images in Google Search. You
don't need to do anything special to have your AVIF files indexed by Google.

![Googlebot and Crawley checking to see if they are AVIF compatible](/search/blog/images/googlebot-crawley-binoculars.avif)

[AVIF](https://en.wikipedia.org/wiki/AVIF) is an open image file
format based on the AV1 video compression standard. It's supported by all major web browsers, and
images in AVIF image file format are supported by a variety of services and platforms on the web,
including [WordPress](https://make.wordpress.org/core/2024/02/23/wordpress-6-5-adds-avif-support/),
[Joomla](https://issues.joomla.org/tracker/joomla-cms/41381),
and [CloudFlare](https://blog.cloudflare.com/generate-avif-images-with-image-resizing/).
It's not recommended to blindly make sweeping changes to images across a website: take the time
you need to evaluate which format works best for your specific needs. If you do choose to change
image file formats for some of your images, and if this results in changes to filenames or
extensions, make sure to set up [server-side redirects](/search/docs/crawling-indexing/301-redirects#serverside).

If you're curious about other aspects involved with optimizing SEO for your site's images, check
out our [guide to Image SEO](/search/docs/appearance/google-images). If you have more
questions, let us know in the [Search Central help community](https://goo.gle/sc-forum).

Posted by [John Mueller](/search/blog/authors/john-mueller),
Search Advocate, Google Switzerland
