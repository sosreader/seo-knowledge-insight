# Improving prominence reporting in the Search Console video indexing report
- **發佈日期**: 2023-06-01
- **作者**: Google Search Central
- **來源 URL**: https://developers.google.com/search/blog/2023/06/video-indexing-specific-issues
- **來源類型**: article
- **來源集合**: google-search-central
---
Monday, June 12, 2023

One of the main reasons for Google not to index a video on your pages is that Google couldn't identify a
prominent enough video to qualify as the video for this page.

In order to help you better understand this issue and provide you with more actionable reasons, we are breaking
down the "Google could not determine the prominent video on the page" reason into three more specific
reasons. Here's a summary of what you need to do to resolve these issues and make your video eligible for indexing:

* **Video outside the viewport**: Reposition the video on the page so that the entire
  video is inside the renderable area of the page and seen when the page loads.
* **Video too small**: Increase the height of the video so that it's larger than 140px or
  the width of the video so that it's larger than 140px and at least a third of the page's width.
* **Video too tall**: Decrease the height of the video so that it's smaller than 1080px.

![Search Console video indexing report including the new reasons](/static/search/blog/images/video-indexing-specific-issues.png)

Since the Search Console video indexing report shows 3 months of historical data, you may still see the "Google could not
determine the prominent video on the page" in the list of reason in the
Video Indexing report, but it has no effect on your pages.

The new reasons will also appear when applicable while
[inspecting a
specific video page URL](https://support.google.com/webmasters/answer/9012289).

We hope these changes will make it easier for you to understand video indexing,
and fix any issues on your video pages. If you have any questions or concerns, please reach
out to us via the [Google
Search Central Community](https://support.google.com/webmasters/threads?thread_filter=(category:search_console)) or on [Twitter](https://twitter.com/googlesearchc).

Posted by Shachar Nudler, Software Engineer, and
[Moshe Samet](/search/blog/authors/moshe-samet), Product Manager
