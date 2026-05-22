# Accessible Renderer Patterns

Reference guide for adding a new screen to reader mode in `web/app.js`.
Read this before writing any new `renderAccessible*()` function.

## Eight-Step Checklist for a New Accessible Renderer

1. **Create `renderAccessible<ScreenName>()`** in `web/app.js`, after the existing
   accessible renderer family (search for `renderAccessibleSpeedPresets` to find the insertion point).

2. **Add the dispatch line** at the top of the existing terminal renderer:
   ```js
   function renderMyScreen() {
     if (isAccessibleMode()) { renderAccessibleMyScreen(); return; }
     document.body.classList.remove('reader-mode');
     // ... existing terminal code unchanged below
   }
   ```

3. **Set `currentScreen`** to the correct string value before building HTML.
   Use the same string the terminal renderer uses — page navigation handlers branch on this value.

4. **Call `document.body.classList.add('reader-mode')`** as the first side-effect in the function.

5. **Call `setPageTitle()`** with the correct parts (see existing renderers for examples).

6. **Build HTML using semantic elements** — see the element table below. Never use
   `makeRule()`, `renderRule()`, or any ASCII box-drawing in accessible renderers.

7. **Set `app.innerHTML`** to the built HTML string.

8. **Call `focus()`** on the first interactive element immediately after:
   ```js
   app.innerHTML = html;
   var first = app.querySelector('.r-choice-btn'); // or whatever the first button is
   if (first) first.focus();
   ```
   **This step is mandatory.** Omitting it causes focus to land on `<body>`. Screen reader
   users will hear nothing and must navigate from the top of the page — a WCAG 2.4.3
   (Focus Order) failure.

**Prohibitions (never do these in accessible renderers):**
- Never call `startTypewriter()` — prose must appear instantly
- Never render `.terminal-prompt-line` — no keyboard buffer
- Never render `.terminal-cursor` — no blinking cursor
- Never use `pendingInput` for navigation — all interaction is button-driven

## Element Substitution Table

| Terminal pattern | Accessible equivalent | WCAG criterion |
|---|---|---|
| `<div data-action="...">` clickable area | `<button>` | 4.1.2, 2.1.1 |
| `<div class="terminal-list-item">` for stories | `<button class="r-story-btn" aria-label="full description">` | 2.5.3, 4.1.2 |
| `<div class="terminal-panel">` for prose | `<article class="r-panel" aria-label="Story: [title]">` | 1.3.1 |
| `<span class="terminal-inset">` | `<p role="note" class="r-inset" aria-label="[KindLabel]: [text]">` inside `<aside aria-label="Notes">`; the visual kind label is `<span class="r-inset-kind" aria-hidden="true">` | 1.3.1 |
| `<div class="terminal-choices">` | `<nav aria-label="Story choices"><ul class="r-choices">` | 1.3.1, 2.4.6 |
| Choice `<div>` | `<li><button class="r-choice-btn" aria-label="Choice N: [text]">` for normal choices; colored choices append a suffix: `bright_red` → `. Risky.`, `green` → `. Safe.` | 4.1.2 |
| `<span class="terminal-overlay">` | `<p class="r-overlay">` (outside the `<article>`) | 1.3.2 |
| Section heading | `<h1>` (page title), `<h2>` (section title) | 2.4.6 |
| Prompt line | **Not rendered** in reader mode | 2.1.4 |
| ASCII rule `────` | `<hr>` or `<p class="r-settings-section">` (CSS handles styling) | 1.3.1 |
| `pendingInput` buffer | **Not used** in reader mode | 2.1.4 |
| `mobileCapture` input | **Not rendered** in reader mode — touch uses native buttons | 2.1.1 |

## ARIA Live Region Usage

`<main id="app" aria-live="polite">` is set in `index.html` and is present for
the lifetime of the page. It may provide supplemental announcements for some screen
readers when `app.innerHTML` is replaced — but it is unreliable for wholesale
`innerHTML` replacement (live regions are designed for incremental updates).

**The authoritative mechanism for announcing new screen content is focus management
(Step 8 in the checklist).** When focus moves to the first interactive element of the
new screen, screen readers announce the element and its context. Do not rely on
`aria-live` as the primary mechanism for screen transitions.

**Do not add additional `aria-live` regions** unless you are announcing a status
that changes within a screen (not a full screen replacement). If you do:
- Use `role="status"` for non-urgent updates (e.g. "Saved")
- Use `role="alert"` only for errors that require immediate attention
- Never use `aria-live="assertive"` on a container that changes frequently — it interrupts
  whatever the screen reader is currently speaking

## Focus Management in Depth

After every `app.innerHTML = html` call in an accessible renderer, focus moves to
`<body>` (browser default when the focused element is removed from DOM). The user's
screen reader will then be positioned at the top of the document, unaware that a
new screen has loaded.

The fix is a single `.focus()` call:
```js
app.innerHTML = html;
var first = app.querySelector('.r-choice-btn'); // adjust selector for each screen
if (first) first.focus();
```

**Which element receives focus on each screen:**

| Screen | Focused element | Selector |
|---|---|---|
| Library | First story button | `.r-story-btn` |
| Folder | First story button in folder | `.r-story-btn` |
| Resume prompt | Continue button | `.r-continue-btn` |
| Warnings | Proceed button | `.r-proceed-btn` |
| Game | First choice button | `.r-choice-btn` |
| Ending | Play again button | `.r-play-again-btn` |
| Settings | First settings row | `[data-row-index]` (class is `r-setting-row`) |
| Speed presets | Active preset button | `.r-preset-btn[aria-pressed="true"]`, fallback `.r-preset-btn` |

The `if (first)` guard is required — do not assume the element exists. A game
node with zero choices is an ending and should have been dispatched to `renderAccessibleEnding()`
before reaching `renderAccessibleGame()`, but defensive code prevents focus errors.
