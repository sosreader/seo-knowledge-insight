# Navigation API - a better way to navigate, is now Baseline Newly Available
- **發佈日期**: 2026-02-17
- **作者**: web.dev
- **來源 URL**: https://web.dev/blog/baseline-navigation-api?hl=en
- **來源類型**: article
- **來源集合**: web-dev
---
Published: Feb 17, 2026

For over a decade, we've relied on `window.history` to build [Single Page Applications (SPAs)](https://en.wikipedia.org/wiki/Single-page_application), and for over a decade, we've complained about it. The reason? It was never really designed for SPAs. To provide a seamless experience, SPAs must mimic standard multi-page navigation by manually tapping into the browser's history to support the back and forward buttons.

The [History API](https://developer.mozilla.org/docs/Web/API/History_API) alleviated some of these pain points, but not without its own shortcomings, like being unable to detect all different types of navigation triggers. Other notable limitations include the inability to read the full history stack, or edit non-current entries. The `popstate` event also behaves inconsistently, and doesn't trigger when `pushState` or `replaceState` are called programmatically.

That era ends now. The [Navigation API](https://developer.mozilla.org/docs/Web/API/Navigation_API) is here, and it's finally becoming Baseline Newly available across all major browsers as of early 2026.

## A side by side comparison

To illustrate the difference, this section compares how we've historically handled client-side routing versus the new, streamlined approach powered by the Navigation API.

### The old way

```
// 1. Function to navigate programmatically
function navigate(path) {
  // Update the URL without a page refresh
  window.history.pushState({ path }, '', path);

  // Manually trigger the UI update
  renderContent(path);
}

// 2. Listener for browser navigation (Back/Forward buttons)
window.addEventListener('popstate', (event) => {
  // event.state contains the object we pushed in navigate()
  const path = event.state?.path || window.location.pathname;
  renderContent(path);
});

// 3. Mock UI renderer
function renderContent(path) {
  console.log(`Rendering UI for: ${path}...`);
}

// Example usage:
// navigate('/dashboard');
```

### How the Navigation API works

```
// 1. One central listener for ALL navigation
// This catches: links, back/forward buttons, AND programmatic calls
navigation.addEventListener('navigate', (event) => {
  const url = new URL(event.destination.url);

  // Intercept the navigation to prevent a full page reload
  event.intercept({
    async handler() {
      // The API handles the URL update; you just handle the UI
      await renderContent(url.pathname);
    }
  });
});

// 2. Mock UI renderer
async function renderContent(path) {
    console.log(`Rendering UI for: ${path}...`);
}

// Example usage:
// navigation.navigate('/dashboard');
```

Building a router with the History API felt like assembling a puzzle, since you had to:

1. Listen for clicks on `<a>` tags globally.
2. Call `preventDefault()` on them.
3. Manually call `history.pushState()`.
4. Manually update your DOM.
5. *Separately* listen for the `popstate` event to handle the back/forward buttons.

If you forgot to handle one edge case, users might accidentally end up at the wrong view, highlighting its fragility.

The Navigation API radically simplifies this. It gives you a single, centralized [NavigateEvent](https://developer.mozilla.org/docs/Web/API/NavigateEvent) for every navigation—whether it's a user clicking a link, submitting a form, hitting the back button, or your code calling `navigation.navigate()`.

The `event.intercept()` function does a lot of the heavy lifting for you:

* **Automatic URL updates:** Handles updating the address bar and the history stack, without the need to call `pushState`.
* **Automatic accessibility:** Handles accessibility primitives like focus management (restoring focus after navigation) automatically.
* **Centralized logic:** Handles the back button and click events in the exact same function.

## Some more use cases

We look at a few more examples in this section to highlight more ways the Navigation API can be leveraged.

### Example: Handling a form submission

The navigate event automatically catches all same-document form submissions and provides a [NavigateEvent.formData](https://developer.mozilla.org/docs/Web/API/NavigateEvent/formData) property to access the data.

This example captures a standard HTML form submission, prevents the page reload, and processes the data asynchronously.

```
// 1. One central listener handles links AND forms
navigation.addEventListener('navigate', (event) => {
  // Only handle form POST submissions in this block
  if (event.formData && event.canIntercept) {
    event.intercept({
      async handler() {
        const data = event.formData;
        console.log(`Submitting form data...`);

        const username = data.get('username');

        // Perform your async API call
        postFormData(data);

        // Update UI without a page refresh
        renderSuccessMessage(username);
      }
    });
  }
});

// 2. Standard HTML form (No JS 'onsubmit' needed!)
// <form action="/login" method="POST">
//   <input name="username" type="text" required />
//   <button type="submit">Login</button>
// </form>
```

### Example: Handling async scrolling

In the Navigation API, `event.scroll()` gives you manual control over when the browser restores scroll position during a navigation.

By default, the browser tries to restore scroll position as soon as `event.intercept()` is called. However, in modern SPAs, the content often isn't ready yet (you might be waiting for an API response). If the browser scrolls before the content is rendered, it will land in the wrong place or stay at the top.

Imagine a user clicks the back button to return to a long list of items. We will need to fetch those items before the page is long enough to go to the end.

```
navigation.addEventListener('navigate', (event) => {
  if (!event.canIntercept) return;

  event.intercept({
    // Tells the browser: "I will handle the scroll timing manually"
    scroll: 'manual',

    async handler() {
      // 1. Fetch data and render it
      const data = await fetchListData();
      renderItems(data);

      // 2. Now that the items are in the DOM and the page has height,
      //    we can move the scrollbar to the saved position (for back/forward)
      //    or to the top (for new navigations).
      event.scroll();
    }
  });
});
```

### Example: Enabling view transitions

The [Navigation API](https://developer.mozilla.org/docs/Web/API/Navigation_API) and [View Transitions API](https://developer.mozilla.org/docs/Web/API/View_Transition_API) are designed to work together to create seamless, "app-like" transitions in SPAs.

While intercepting a navigation event, we can wrap the DOM updates in a [document.startViewTransition()](https://developer.mozilla.org/docs/Web/API/Document/startViewTransition). This tells the browser to capture a snapshot of the "old" state, perform the required DOM changes, and then animate to the "new" state. This can allow us to support app-like transitions!

```
navigation.addEventListener('navigate', (event) => {
  if (!event.canIntercept) return;

  const url = new URL(event.destination.url);

  event.intercept({
    async handler() {
      // 1. Fetch the new content first (optional but recommended)
      const content = await fetchNewPageContent(url.pathname);

      // 2. Start the view transition
      document.startViewTransition(() => {
        // 3. Update the DOM inside the callback
        // The browser snapshots the old UI before this and the new UI after
        document.getElementById('app').innerHTML = content;
      });
    }
  });
});
```

## In summary

As seen with the preceding examples, the Navigation API fixes deep architectural issues with navigating SPAs, a long-standing pain point among many web developers. It is built-in, safe, and handles edge cases robustly.

As of early 2026, with support landing in Safari and Firefox, the Navigation API is ready for prime time. It's the router we always wanted—simple, powerful, and built for the modern web.
