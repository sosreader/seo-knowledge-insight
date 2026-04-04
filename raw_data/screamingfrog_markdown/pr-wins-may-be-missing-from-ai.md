# Out of Cite: Why Your PR Wins May Be Missing From AI Search
- **發佈日期**: 2025-07-22
- **作者**: Chris Jones
- **來源 URL**: https://www.screamingfrog.co.uk/blog/pr-wins-may-be-missing-from-ai/
- **來源類型**: article
- **來源集合**: screaming-frog
---
Large Language Models (LLMs) like ChatGPT, Gemini and DeepSeek are disrupting search marketing.

More people are asking LLM-powered tools the questions they would usually ask Google or Bing – and they trust the information and recommendations they receive. A recent YouGov poll found [50% of young people](https://www.thedrum.com/opinion/2024/12/17/it-s-important-know-what-llms-are-saying-about-your-brand-here-s-how) have been directly influenced by LLMs when making brand and product choices.

This matters for Digital PR and the brands we serve. LLMs represent brands as entities similar to traditional search engines, drawing on the context and associations within their training data. ​And there are citation links within AI Overviews and, depending on the search features, when LLMs are used.​

So, as an industry, we need to make sure our clients’ brands are visible in AI search and control the narrative when they are. The priority strategy here would be, just like with traditional offsite SEO, to build quality and relevant brand mentions and backlinks in the media.

But there’s a catch. Many major news sites are blocking access to web crawlers that feed information to AI models, which limits what LLMs can use in terms of information to give you an answer. The main reason being due to ongoing [legal proceedings](https://pressgazette.co.uk/platforms/news-publisher-ai-deals-lawsuits-openai-google/) to stop unauthorised and unpaid use of their articles.

If a news site is blocking some or all AI crawler bots, then an LLM won’t find your coverage and won’t cite your client. Your PR wins will be missing from AI search.

LLMs are hungry for content, but can they see yours?

---

## Key Findings

* Using a seed list of 72 major national, regional and consumer news sites, we recorded which allow or block 11 of the most-common AI crawler bots in robots.txt or page meta tags.
* 75% of news sites block at least one AI crawler bot (54 out of 72).
* OpenAI’s GPTBot is the most blocked bot – by 58% of news sites.
* MailOnline, iNews, Metro and BBC News block 91% of crawler bots.
* Regional news sites are the most likely to block AI crawler bots – 8 on average.

---

## Digital PR in the Age of LLMs

The coming wave of AI technology can feel exciting yet overwhelming. But while the way people find and consume information is changing, the basic foundations of good PR and brand building remain the same.

Trustworthy, informative and authoritative voices will continue to be heard the loudest. The ‘traditional’ search results will remain important to LLM citations. Content strategies should continue to prioritise brand-owned content that answers the questions being asked by target audiences, alongside earned media coverage on relevant and quality news sites.

Sounds simple? It is, but our strategies and reporting need to evolve. Every good Digital PR should have a basic understanding of how LLMs work and which news sites allow or block their crawlers.

That’s where this study comes in.

---

## The New Battleground for Brand Authority: AI Answers

Websites now serve both human and AI. The emergence of gen-AI tools like ChatGPT, Gemini and DeepSeek have revolutionised how people find and trust information online.

Traditional search engines (e.g., Google, Bing, Yahoo!) rely on a keyword-query-to-links model, but LLM-powered search focuses on generating conversational and synthesised responses from high-quality content aggregated from across the internet.

This has changed user experience, as LLMs bypass the need for searchers to sift through multiple sites to find the information they’re looking for from trusted sites. AI tools can deliver trustworthy and contextualised answers to questions instantly, making them a go-to information source.

Now that more people are switching to AI-driven search, visibility within these tools must underpin offsite SEO strategies – including Digital PR.

Unlike traditional search engines, where page ranking can be influenced by tried and tested SEO and link-building activity, LLMs operate differently by generating responses based on a mix of training data, embedded knowledge and, in some cases, real-time information scanning from integrated retrieval tools.

This poses a new challenge for digital PRs. If major media outlets block AI crawlers from their sites, then high-quality press coverage may not be included in AI-generated answers and recommendations.

---

## The Media vs LLMs – What’s the Latest?

Content owners, including some news publishers, are in a headlock with tech firms. They believe LLM developers are acting unethically and unlawfully by using copyrighted data to train their models without permission or compensation. AI companies contest this, citing the societal value of their products and the legal exemptions.

The UK Government is [currently considering how best to resolve this](https://www.gov.uk/government/consultations/copyright-and-artificial-intelligence/copyright-and-artificial-intelligence) by clarifying the law and the addition of new exceptions in this area. However, it has been criticised as being too slow to act on this issue and for siding with Big Tech. Policymakers find themselves in a tricky spot, as both the creative industries and AI sector are hugely important to the UK’s economy and global standing.

Some media owners are striking licensing deals with AI firms to access and use their content, while others are attempting to sue them for unlawful practice. It’s reported OpenAI is paying publishers between $1 million and $5 million a year to license copyrighted news articles to train its AI models. It’s a fast-moving situation, but here’s a [regularly updated list](https://pressgazette.co.uk/platforms/news-publisher-ai-deals-lawsuits-openai-google/) of who’s signing and who’s suing by the Press Gazette.

At the time of writing, Cloudflare, which hosts around a fifth of the internet, had just announced publishers using its services would [automatically be able to block AI bots](https://www.bbc.co.uk/news/articles/cvg885p923jo) from accessing their content without permission. In time, sites would also be able to ask for payment in return for access.

But in the meantime, one easy way news publishers can try to stop these companies from using their content is to block their user agents – or ‘crawler bots’ – from reading and scraping text from their websites via robots.txt. And this is the main focus of our study.

---

## What Are AI Crawler Bots?

Every website on the internet can use the “[Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309.html)” method to control how its content may be accessed, if at all, by automatic clients known as crawlers.

Allowing or disallowing bot access requires websites to configure the [robots.txt file](https://developers.google.com/search/docs/crawling-indexing/robots/create-robots-txt#:~:text=of%20each%20rule.-,Upload%20the%20robots.txt%20file,if%20Google%20can%20parse%20it.). This is a plain text file named robots.txt placed in the root directory of a website. It specifies rules by identifying the name of the user-agent associated with the crawler, then using ‘allow’ or ‘disallow’ directive followed by the path(s) to permit or block crawler access to specific parts of the site.

The only caveat is that they are instructions and not rules. Well-behaved bots (like Googlebot) will follow it, but bad bots may ignore it.

Like the crawler bots that came before them, AI crawler bots are also instructed by robots.txt. But web publishers, including the media, are torn on whether to allow them access to their sites…and their content.

Below is an example of what robots.txt looks like in practice:

```
Disallow: /
#
User-agent: CCBot
User-agent: AI2Bot
User-agent: Ai2Bot-Dolma
User-agent: Amazonbot
User-agent: anthropic-ai
User-agent: Applebot-Extended
User-agent: Bytespider
User-agent: CCBot
User-agent: ChatGPT-User
User-agent: Claude-Web
User-agent: ClaudeBot
User-agent: cohere-ai
User-agent: Diffbot
User-agent: FacebookBot
User-agent: FriendlyCrawler
User-agent: Google-Extended
User-agent: GoogleOther
User-agent: GoogleOther-Image
User-agent: GoogleOther-Video
User-agent: GPTBot
```

Sites can also choose to block AI crawler bots another way, most notably Bing’s crawler, through on-page meta tags such as:

<meta name=”robots” content=”noarchive”>

or

<meta name=”bingbot” content=”noarchive”>

Designed to find and crawl the content on websites, AI-crawler bots are not dissimilar to search engine crawlers. But, while these evaluate and index webpages in order to decide their visibility within the search engine results pages, AI crawler bots have a different agenda. They are hungry for content to train their models and improve the speed and quality of their responses.

The problem is, some media brands aren’t willing to feed them.

---

## Our Study

### Methodology

After we learned that popular news sites could be blocking AI crawler bots, we set out to uncover the extent of the problem and understand what this means for us and our clients.

We started by creating a seed list of 72 national, regional and consumer online news sites the Screaming Frog Digital PR team regularly outreaches to and gets covered by.

We then researched the most common crawler bots that companies training AI use to crawl and collect information and made a list of 11 in total to study. Here is the full list:

* GPTBot (OpenAI)
* ChatGPT-User (OpenAI)
* OAI-SearchBot (OpenAI)
* PerplexityBot (Perplexity AI)
* Perplexity-User (Perplexity AI)
* Google-Extended (Google)
* ClaudeBot (Anthropic)
* Anthropic-ai (Anthropic)
* Claude-Web (Anthropic)
* Applebot-Extended (Apple)
* Bingbot (Microsoft)

The [Screaming Frog SEO Spider](https://www.screamingfrog.co.uk/seo-spider/) was used to bulk check whether the various homepages of the selected sites were allowing or blocking the identified AI user agents.

**Data is correct as of June 2025.**

---

## Our Findings

### The Most Blocked AI User Agents by Major News Sites

From the list of 11 common AI crawler bots studied, GPTBot is the most blocked by UK news sites. 58% of the news sites (42 out of 72) block OpenAI’s automated web crawler that’s used to enhance the training datasets for its AI models including GPT. By continuously updating its datasets, GPTBot helps ensure OpenAI’s models remain current with the latest information and trends, including from news articles.

![](https://www.screamingfrog.co.uk/wp-content/uploads/2025/07/news-site-blocking-ai.jpg)

15 sites also block OpenAI’s ChatGPT-user bot and 29 block its OAI-SearchBot, which indexes publicly available web content to provide real-time, citation-backed search results within its SearchGPT product.

In joint second place are anthropic-ai and Applebot-Extended bots – each blocked by 54% of news sites (39 out of 72).

Anthropic is a main competitor to OpenAI’s ChatGPT and Google’s Gemini and boasts that it is building tools with human benefit at their foundation, while scaling them responsibly. Its user agent, anthropic-ai, is an HTTP user agent string used by Anthropic’s web crawlers to collect data from public websites. However, the start-up has been accused of ‘hammering’ websites with its web crawlers, with [businesses reporting disruptive traffic booms](https://www.inc.com/ben-sherry/why-anthropics-web-crawlers-have-been-hammering-websites.html) from bots.

Anthropic’s two other crawler bots – Claude-Web and ClaudeBot – are blocked by 51% of news sites, followed by Perplexity’s bot, blocked by 47%.

---

## The News Sites That Block the Most AI Crawler Bots

Looking at a publisher level, four of the 72 news sites studied block 10 out of the 11 AI crawler bots (91%), allowing only Bingbot access. These are: MailOnline, iNews, Metro and BBC News.

While not all outlets have publicly announced their reasons for doing so, decisions to block AI crawler bots are driven mainly by concerns of copyright infringement and fears over “zero-click searches”, which directly impacts the revenue for these publications. In fact, Mail Online’s director of SEO and editorial e-commerce revealed that click-through rates decrease by as much as [56%](https://pressgazette.co.uk/publishers/digital-journalism/google-ai-overviews-leads-to-dramatic-reduction-in-click-throughs-for-mail-online/#:~:text=So%20the%20impact%20on%20clickthrough,on%20year%20in%20March%202025).) when a Google AI overview appears for a search query.

Other major news outlets, the New York Times and Channel 4 News block 9 out of 11 AI crawler bots (82%). They each allow Perplexity-User and Bingbot to crawl their content.

![](https://www.screamingfrog.co.uk/wp-content/uploads/2025/07/PR-AI_june-least-AI-Table.jpg)

Regional news sites block the most often, blocking on average 8 AI crawler bots each. This is followed by national news sites (5 on average), and then consumer news sites (3 on average). However, regional news sites are owned by a limited number of parent media companies who will have blanket policies on this across their brands’ websites.

---

## The News Sites That Shape AI Search

Now for the good news. Many popular sites, including some nationals, do allow a wide range of AI crawler bots to mine data from their pages.

Our data shows 25% (18 out of 72) news sites allow all AI crawler bots. These include many consumer publications like Hello!, Ideal Home, Ladbible, Timeout and TechRadar, as well as national titles like GB News, LBC, The Scotsman and The Independent.

57% of news sites studied block five or less AI bots, meaning they allow more access than they deny. To see a more extensive list of which of the 72 news sites do and don’t allow different AI crawler bots, [click here](https://docs.google.com/spreadsheets/d/1yjKCfUgOgkguIfmM1UQcAMPtlF99QegszuVrCeJdRLo/edit?usp=sharing).

---

## Discussion

Our findings confirm that a growing number of major news sites are taking steps to limit the use of their content by AI models by blocking their crawler bots, either entirely or selectively. With three quarters of the sites in our study blocking at least one AI crawler bot, with many blocking several, this is an important issue for Digital PRs to understand.

LLM-powered search is only going to become more common, so the discoverability of media coverage by AI tools will increasingly shape how visible brands are in search results, recommendations, and AI-assisted experiences.

If a high-authority publication cites your client, but that site blocks AI crawlers, that brand win is effectively invisible to LLMs. The result? A gap in brand visibility across a growing number of influential search platforms.

Yet, it’s not all doom and gloom. Around one in four news sites (25%) allow all major AI crawlers unrestricted access to their content. These publications remain valuable opportunities for PRs to secure brand mentions that can feed into LLMs’ training and retrieval mechanisms. For now, these sites may offer the best chance of citations appearing in AI-generated responses.

As a result, we’re seeing a split media environment; one where brand mentions exist at the source and are invisible in search.

Digital PRs should look beyond surface-level coverage metrics and start reporting on LLM visibility too. From a strategic standpoint, Digital PR must now serve two audiences: humans and machines. We still need to land relevant, high-quality editorial coverage that influences real people. But for LLMs we must strategically go after news sites that are actively contributing to the AI ecosystem. Balancing both will be essential for a well-rounded brand strategy.

This is a fast-moving space. Media owners are in ongoing negotiations with AI firms, policymakers are being lobbied from both sides, and AI companies continue to refine their tools, policies and partnerships.

As our industry debates and discovers what AI search means for our services and clients, this is an important piece of the puzzle to monitor and understand. With this information, we can strategise for both humans and AI audiences, and shout about our PR wins even louder.

The post [Out of Cite: Why Your PR Wins May Be Missing From AI Search](https://www.screamingfrog.co.uk/blog/pr-wins-may-be-missing-from-ai/) appeared first on [Screaming Frog](https://www.screamingfrog.co.uk).
