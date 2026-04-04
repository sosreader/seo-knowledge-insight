# January 2026 Baseline monthly digest
- **發佈日期**: 2026-03-02
- **作者**: web.dev
- **來源 URL**: https://web.dev/blog/baseline-digest-jan-2026?hl=en
- **來源類型**: article
- **來源集合**: web-dev
---
Published: March 2, 2026

Welcome to the January 2026 edition of the Baseline digest. Each month, we
highlight the web platform features that have reached new milestones in
[Baseline](/baseline), helping you understand what tools are ready to use in
your projects today.

January was an exciting start to the year, with several significant APIs and CSS
units moving into the Newly available category, along with a major layout
improvement becoming Widely available.

## Baseline Newly available features

The following web features became Baseline Newly available in January 2026.

### Active view transition

The
[`:active-view-transition` CSS pseudo-class](https://developer.mozilla.org/docs/Web/CSS/Reference/Selectors/:active-view-transition)
is now Baseline Newly available. This selector allows developers to target and
style the root element of a document specifically while a view transition is in
progress. This is particularly useful for applying global styles or adjustments
that should only exist during the transition period, such as changing the
background color of the transition overlay or adjusting the z-index of specific
layers to ensure a smooth visual flow.

### JavaScript modules in service workers

[Service workers now support JavaScript modules](https://developer.mozilla.org/docs/Web/API/ServiceWorkerContainer/register#module)
across all major browser engines. By setting the `type: 'module'` option when
calling `navigator.serviceWorker.register()`, you can use standard `import` and
`export` statements within your service worker script. This brings service
workers in line with modern JavaScript development practices, allowing for
better code organization, easier dependency management, and the ability to share
code between the main thread and the background worker.

### Navigation API

[The Navigation API](https://developer.mozilla.org/docs/Web/API/Navigation_API)
provides a modern, purpose-built alternative to the legacy History API,
specifically designed for the needs of single-page applications (SPAs). It
offers a centralized way to initiate, intercept, and manage all types of
navigation actions, including those triggered by the browser's back and forward
buttons. With events like `Maps`, developers can implement smoother client-side
routing with less boilerplate code. For a deeper dive into how this changes the
way we build for the web, check out our dedicated blog post: [Modern client-side
routing: the Navigation API](/blog/baseline-navigation-api).

### `rcap` CSS unit

[The `rcap` unit](https://developer.mozilla.org/docs/Web/CSS/Reference/Values/length#rcap)
is a root-font-relative length unit equal to the "cap height" (the nominal
height of capital letters) of the root element's font. This allows for precise
typographic layouts that scale relative to the primary typeface used on the
site, rather than just the font size.

### `rch` CSS unit

Similar to the `ch` unit but relative to the root element, the
[`rch` unit](https://developer.mozilla.org/docs/Web/CSS/Reference/Values/length#rch)
represents the width—or more specifically, the advance measure—of the "0" (zero)
glyph in the root element's font. It is ideal for creating layouts that depend
on character width, such as a container that should precisely fit a specific
number of characters in the root font.

### `rex` CSS unit

[The `rex` unit](https://developer.mozilla.org/docs/Web/CSS/Reference/Values/length#rex)
is
the root-relative version of `ex`, equal to the x-height of the root element's
font. This unit is particularly useful for vertical alignment and sizing
elements relative to the height of lowercase letters in your document's primary
typography.

### `ric` CSS unit

[The `ric` unit](https://developer.mozilla.org/docs/Web/CSS/Reference/Values/length#ric) is
the root-relative counterpart to the `ic` unit. It is equal to the "ideographic"
advance measure (typically the width or height of a CJK ideograph) of the root
element's font. This is a vital tool for developers building internationalized
layouts, particularly those using Chinese, Japanese, or Korean scripts.

## Baseline Widely available features

The following web features became Baseline Widely available in January 2026.

### Two value CSS `display` property

The
[multi-keyword syntax for the `display` property](https://developer.mozilla.org/docs/Web/CSS/Guides/Display/Multi-keyword_syntax)
is now Baseline Widely available. This update lets you explicitly define
both the "outer" and "inner" display types of a box. For example, instead of the
precomposed `inline-flex`, you can use `display: inline flex`. This clarifies
whether an element participates in block or inline flow (the outer type) and how
its children are laid out (the inner type, like `flex` or `grid`). This change
makes the CSS layout engine more logical and consistent for developers.

### The `animation-composition` CSS property

[The `animation-composition` property](https://developer.mozilla.org/docs/Web/CSS/Reference/Properties/animation-composition)
defines how multiple animations should interact when they affect the same
property simultaneously. You can choose between `replace`, `add`, or
`accumulate`, giving you precise control over how complex, layered animations
are calculated.

### Array by copy

JavaScript now includes
[methods that let you transform arrays](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Array/toReversed)
without mutating the original data. Methods like `toReversed()`, `toSorted()`,
and `toSpliced()` return a new, modified copy of the array, promoting a more
functional and safer programming style.

## Help us improve

As usual, let us know if we missed anything Baseline-related, and we'll make
sure it gets captured in a future edition! If you have any questions or want to
provide feedback on Baseline, you can file an issue in our
[issue tracker](https://github.com/web-platform-dx/web-features/issues).
