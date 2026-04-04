# Video mode now only shows pages where video is the main content
- **發佈日期**: 2023-12-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/12/video-is-the-main-content
- **來源類型**: article
- **來源集合**: google-search-central
---
Monday, December 4, 2023

[Earlier this year](/search/blog/2023/04/simplifying-video), we made a change to only
show video thumbnails next to results on the main Google Search results page when the video is
the main content of a page. Today, we're extending this change to search results in Video mode to
better connect users with the video content they're looking for (rather than having to comb
through a page to find that video). This change will start rolling out today, and it could take
up to a week to complete.

![Video mode in Google Search results](/static/search/blog/images/video-mode-on-google.png "Video mode in Google Search results")

With this update, clicking a result in Video mode will only take users to a page where the video
is the main content. Here's an example of a page where the video is the main content of the page:
the video is above the fold, it's prominent, and the main purpose of the page is to watch that
video.

![a web page where the video is the main content on the page](/static/search/docs/images/dedicated-video-page.png "A web page where the video is the main content on the page")

Here are some examples of page types where the video is supplementary to the textual content, and
not the primary focus of the page:

* A blog post where the video is complementary to the text rather than the primary content of
  the page
* A product details page with a complementary video
* A video category page that lists multiple videos of equal prominence

As the update rolls out, you'll see the impact of this change in your Search Console
[video indexing report](https://support.google.com/webmasters/answer/9495631).
Videos that aren't the main content of the page will appear as "No video indexed" in Search
Console. We're also adding a new reason to the report to explain why these videos are not indexed:
"Video is not the main content of the page", which simplifies the report by replacing the
following issues:

* Invalid video URL
* Unsupported video format
* Unknown video format
* Inline data URLs cannot be used for video URLs
* Video outside the viewport
* Video too small
* Video too tall

![Video indexing report in Search Console](/static/search/blog/images/video-is-main-content-search-console.png)

Since these videos will no longer be shown in Video mode, you can expect to see a decrease in
the number of pages with indexed videos. This decrease will also appear in the number of video
impressions in the [performance report](https://support.google.com/webmasters/answer/7576553),
[video indexing report](https://support.google.com/webmasters/answer/9495631), and
the [video rich results report](https://support.google.com/webmasters/answer/7552505)
in Search Console.

To learn more about video indexing best practices, check out the [video best practices guide](/search/docs/appearance/video).
For questions, feel free to post in our [Search Central help community](https://goo.gle/sc-forum),
where you can join a discussion with like-minded experts.

Posted by [Cory Benavente](/search/blog/authors/cory-benavente),
Product Manager, Google Search
