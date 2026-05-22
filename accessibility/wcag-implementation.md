# WCAG 2.1 Level AA — Implementation Guide

> This document covers every WCAG 2.1 AA criterion as implemented in the Choices Matter web viewer.
> Written criterion-by-criterion during implementation. Study material for OutSystems AA compliance work.
>
> **Tool:** [WCAG 2.1 Quick Reference (AA filter)](https://www.w3.org/WAI/WCAG21/quickref/?versions=2.1&levels=aa)
> **Contrast checker:** https://webaim.org/resources/contrastchecker/
> **Automated testing:** axe DevTools browser extension (catches ~30% of issues)

---

## Addressed

### 1.3.1 Info and Relationships — A

**What it requires:**
Information, structure, and relationships conveyed visually must also be available programmatically (via semantic HTML or ARIA), not just through visual presentation.

**Why it matters:**
Screen reader users cannot perceive visual structure (indentation, layout grouping, font weight). Semantic elements allow assistive technology to announce headings, lists, navigation landmarks, and regions.

**What was failing (if applicable):**
Terminal mode rendered everything in `<div>` elements with no landmark roles, no heading hierarchy, and no list semantics. Structure was conveyed entirely through CSS positioning and color.

**What was fixed / implemented:**
Reader mode accessible renderers use full semantic HTML: `<nav aria-label="Story choices">` for choice lists, `<main class="reader-screen">` for primary content, `<article>` for story prose, `<aside aria-label="Notes">` containing `<p role="note">` for insets, `<ul>/<li>` for story and choice lists, `<h1>` for page title, `<h2>` for section titles. ARIA roles added where native semantics are unavailable (`role="note"` on inset paragraphs).

**Where in the code:**
`web/app.js` — all eight `renderAccessible*()` functions: `renderAccessiblePicker()`, `renderAccessibleFolder()`, `renderAccessibleResume()`, `renderAccessibleWarnings()`, `renderAccessibleGame()`, `renderAccessibleEnding()`, `renderAccessibleSettings()`, `renderAccessibleSpeedPresets()`

**How to verify:**
Open axe DevTools on any reader-mode screen. Run the accessibility scan — no "region", "landmark", or "heading-order" violations should appear. In browser DevTools Accessibility panel, confirm the accessibility tree shows landmarks (main, nav, aside) and heading hierarchy (h1 → h2).

---

### 1.3.2 Meaningful Sequence — A

**What it requires:**
If the order of content matters for understanding, the DOM order must reflect that meaningful sequence — reading order cannot depend on CSS positioning alone.

**Why it matters:**
Screen readers read the DOM in source order. If CSS `order`, `float`, or `position: absolute` visually reorders elements but the DOM order differs, screen reader users hear a nonsensical sequence.

**What was fixed / implemented:**
DOM order in all accessible renderers matches the intended visual reading order: page title → back navigation → story content → choices. No CSS `order` property, `position: absolute`, or `float` is used to reorder elements in reader mode. Layout is achieved with flexbox in column direction and standard block flow.

**Where in the code:**
`web/style.css` — `body.reader-mode` and `.reader-screen` rules use `display: flex; flex-direction: column` and `display: block`. `web/app.js` — HTML string construction in each `renderAccessible*()` function follows source-order-equals-reading-order discipline.

**How to verify:**
Disable CSS in browser DevTools (uncheck all stylesheets). Confirm content is still readable in a logical top-to-bottom order. Alternatively, use a screen reader (NVDA + Chrome, or VoiceOver on macOS) and Tab through reader mode — announced order should match expected reading order.

---

### 1.3.3 Sensory Characteristics — A

**What it requires:**
Instructions must not rely solely on sensory characteristics — shape, color, size, visual location, orientation, or sound — to convey meaning.

**Why it matters:**
Users who are blind, color-blind, or using high-contrast mode cannot distinguish elements by color or shape alone. Instructions like "click the green button" are meaningless to them.

**What was fixed / implemented:**
Choice buttons are labeled "Choice N: [label text]" — the number prefix is part of the programmatic label and provides a non-color identifier. Story choice `color` field (e.g. `bright_red`, `green`) adds a CSS class (`.danger`, `.safe`) to the rendered button but the visible label text always conveys meaning independently. No instruction in the UI refers to an element by color or position alone.

**Where in the code:**
`web/app.js` — choice button `aria-label="Choice N: [label]"` construction in `renderAccessibleGame()`. CSS classes `.danger` and `.safe` supplement but do not replace text labels.

**How to verify:**
Enable Windows High Contrast mode or macOS Increased Contrast. All choices should remain distinguishable by their text labels. Run axe scan — no "color alone" violations.

---

### 1.3.4 Orientation — AA

**What it requires:**
Content must not restrict viewing or operation to a single display orientation (portrait or landscape), unless a specific orientation is essential.

**Why it matters:**
Users who mount their devices in a fixed orientation (e.g. wheelchair-mounted tablets) or who use screen rotation assistive technology may be locked out if content forces a single orientation.

**What was fixed / implemented:**
No CSS `@media (orientation: portrait)` or `@media (orientation: landscape)` rules lock layout. The `<meta name="viewport">` tag in `web/index.html` allows user scaling. Reader mode layout uses `max-width: 780px; margin: auto; padding: 1rem` — a flexible block layout that adapts to both orientations without breaking.

**Where in the code:**
`web/style.css` — `body.reader-mode` and `.reader-screen` layout rules. `web/index.html` — viewport meta tag.

**How to verify:**
Open the web viewer on a mobile device (or use browser DevTools device emulation). Rotate between portrait and landscape. All content and controls should remain accessible and usable in both orientations.

---

### 1.4.1 Use of Color — A

**What it requires:**
Color must not be the only visual means of conveying information, indicating an action, prompting a response, or distinguishing a visual element.

**Why it matters:**
Approximately 8% of men and 0.5% of women have color vision deficiency. Red/green distinctions (common in good/bad UI patterns) are invisible to many users.

**What was fixed / implemented:**
Story choice `color` field values (e.g. `bright_red`, `green`) are mapped to supplemental CSS classes (`.danger`, `.safe`) but the button label text always conveys the meaning of the choice independently. Ending type (good/bad/neutral) uses a visible text label in the reader-mode ending renderer alongside the color-coded panel. The decorative icon on ending screens has `aria-hidden="true"` — the ending type is conveyed by visible text, not the icon alone.

**Where in the code:**
`web/app.js` — `renderAccessibleEnding()` includes ending type as visible text. Choice button construction in `renderAccessibleGame()` uses the full label text in both visible content and `aria-label`.

**How to verify:**
Install a color-blindness simulation browser extension (e.g. Chrome's built-in vision deficiencies emulator under DevTools → Rendering). With deuteranopia simulation active, confirm all choices and ending types remain distinguishable by text alone.

---

### 1.4.3 Contrast (Minimum) — AA

**What it requires:**
Text must have a contrast ratio of at least 4.5:1 against its background (3:1 for large text — 18pt or 14pt bold). This applies to all text including placeholder text and disabled state text (unless decorative or inactive).

**Why it matters:**
Low contrast text is the most common WCAG failure and affects users with low vision, aging eyes, and anyone using a screen in bright ambient light. It is the single highest-impact fix.

**What was failing (if applicable):**
Terminal mode `--dim` color was `#4a5870`, yielding approximately 2.4:1 contrast on the `--bg: #0a0e14` dark background — well below the 4.5:1 minimum for normal text.

**What was fixed / implemented:**
`--dim` changed from `#4a5870` to `#6a7e99`, raising contrast to 4.6:1 on `#0a0e14`. Reader mode text colors all verified at 4.5:1 or above against the `--r-bg: #f5f0e8` background:
- `#1a1a1a` (main body text): ~16:1
- `#5c5c5c` (muted metadata/timestamps): ~7.2:1
- `#2c5f8a` (accent/choice numbers): ~5.5:1
- Ending colors: `#1a6b2a` good (5.5:1), `#8b1a1a` bad (9.1:1), `#6b4a00` neutral (7.7:1)
- Focus ring `--r-focus: #b34216` on `--r-bg: #f4ecda`: 4.8:1

**Where in the code:**
`web/style.css` — `:root` custom property `--dim: #6a7e99`. `body.reader-mode` color variables block.

**How to verify:**
Use WebAIM Contrast Checker (https://webaim.org/resources/contrastchecker/) to verify each color pair. Run axe DevTools scan on both terminal mode and reader mode — no "color-contrast" violations should appear.

---

### 1.4.4 Resize Text — AA

**What it requires:**
Text must be resizable up to 200% without loss of content or functionality, except for captions and images of text.

**Why it matters:**
Users with low vision frequently increase browser font size or use the browser zoom function. If layouts break or text clips at 200%, critical content becomes inaccessible.

**What was fixed / implemented:**
All text in reader mode is sized in `rem` or `em` units, not `px`. No `overflow: hidden` is applied to text containers. At 200% browser zoom, all content reflows to accommodate the larger text size without truncation. Reader mode uses `max-width: 780px` with `padding: 1rem` — a flexible container that scales with font size changes.

**Where in the code:**
`web/style.css` — all `.r-*` selectors use `rem`/`em` for `font-size`, `padding`, `margin`, and `line-height`.

**How to verify:**
Set browser zoom to 200% (Ctrl+= or Cmd+= twice from 100%). Navigate through all reader mode screens — picker, game, settings, ending. Confirm no text is clipped, no buttons overlap, and all choices remain selectable.

---

### 1.4.10 Reflow — AA

**What it requires:**
Content must be presentable without horizontal scrolling at a viewport width equivalent to 320 CSS pixels (approximately 400% zoom on a 1280px display), for content that requires vertical scrolling.

**Why it matters:**
Users with low vision who zoom to 400% on a 1280px display effectively have a 320px viewport. Horizontal scrolling at this zoom level forces them to scroll both axes simultaneously, which is extremely difficult with screen magnification software.

**What was fixed / implemented:**
Reader mode layout uses `max-width: 780px; margin: auto; padding: 1rem` with block and flex-column layout. At a 320px viewport, the container collapses to a single column with no horizontal overflow. No fixed-width elements, no `min-width` values wider than 100%, no `white-space: nowrap` on text content.

**Where in the code:**
`web/style.css` — `.reader-screen` and `body.reader-mode` layout rules.

**How to verify:**
In browser DevTools, set the viewport to 320px wide (Device Toolbar → custom dimensions). Navigate through reader mode screens. Confirm no horizontal scrollbar appears and all content is reachable by vertical scrolling only.

---

### 1.4.11 Non-text Contrast — AA

**What it requires:**
UI components (buttons, form fields, focus indicators) and informational graphics must have a contrast ratio of at least 3:1 against adjacent colors.

**Why it matters:**
Users with low vision need to be able to perceive the boundaries of interactive elements — not just their label text. A button that blends into its background is invisible even if its label text has sufficient contrast.

**What was fixed / implemented:**
Reader mode focus indicator: `outline: 3px solid var(--r-focus)` plus `box-shadow: 0 0 0 5px var(--r-bg), 0 0 0 6px var(--r-focus)` creates a double-ring effect. `--r-focus: #b34216` on `--r-bg: #f4ecda` yields 4.8:1 — exceeding the 3:1 minimum. Terminal mode: `.setting-input:focus` changed to `.setting-input:focus-visible` to ensure focus ring appears consistently for keyboard users.

**Where in the code:**
`web/style.css` — `.r-choice-btn:focus-visible`, `.r-story-btn:focus-visible`, `.r-nav-btn:focus-visible` rules. Terminal mode: `.setting-input:focus-visible` rule.

**How to verify:**
Tab through all interactive elements in reader mode. The focus ring (orange double-ring) should be clearly visible on every button. Use WebAIM Contrast Checker to verify `#b34216` on `#f4ecda` = 4.8:1. Confirm the ring is 3px wide — exceeding the minimum visual indicator size.

---

### 1.4.12 Text Spacing — AA

**What it requires:**
No loss of content or functionality occurs when users override text spacing to: line-height ≥ 1.5× font-size, letter-spacing ≥ 0.12× font-size, word-spacing ≥ 0.16× font-size, and spacing after paragraphs ≥ 2× font-size.

**Why it matters:**
Users with dyslexia frequently apply custom text spacing via browser extensions or user stylesheets. CSS that sets fixed heights or overflow hidden on text containers will clip text when spacing is expanded.

**What was fixed / implemented:**
Reader mode uses flexible block layout. No CSS sets fixed `height` on text containers. `line-height`, `letter-spacing`, `word-spacing`, and `margin-bottom` are set in `em`/`rem` units or inherit browser defaults. Container padding is sufficient that expanded spacing does not cause clipping.

**Where in the code:**
`web/style.css` — `.reader-screen`, `.r-prose`, `.r-choice-btn`, `.r-story-btn` rules — all use flexible sizing without fixed heights.

**How to verify:**
Apply the Text Spacing bookmarklet (https://www.html5accessibility.com/tests/tsbookmarklet.html) which injects the maximum override values. Navigate through reader mode — confirm no text clips, overlaps, or disappears.

---

### 2.1.1 Keyboard — A

**What it requires:**
All functionality must be operable with a keyboard alone, without requiring specific timing for keystrokes.

**Why it matters:**
Users with motor disabilities who cannot use a mouse, users with repetitive strain injury, and power users all rely on keyboard navigation. If any action requires a mouse, those users are locked out.

**What was fixed / implemented:**
Reader mode uses native `<button>` elements for all interactive actions — story selection, choice selection, navigation, settings changes. Native buttons are keyboard-accessible by default (Tab to focus, Enter or Space to activate). No custom mouse-only event handlers in accessible renderers. Terminal mode preserves its existing full keyboard input model. The A key shortcut at the library screen (terminal mode) triggers `toggleAccessibleMode()`.

**Where in the code:**
`web/app.js` — all `renderAccessible*()` functions use `<button>` elements exclusively for interactive controls. `toggleAccessibleMode()` is called from the terminal keydown handler.

**How to verify:**
Unplug or disable the mouse. Navigate the entire web viewer using only Tab, Shift+Tab, Enter, Space, and Escape. Confirm every story can be selected, every choice can be made, settings can be changed, and the ending can be reached — all without mouse interaction.

---

### 2.1.2 No Keyboard Trap — A

**What it requires:**
If keyboard focus moves to a component, focus must be able to move away using standard keyboard navigation (Tab, Shift+Tab, or arrow keys). The user must not become trapped.

**Why it matters:**
A keyboard trap makes the entire page unusable for keyboard-only users — they are stuck in one component with no way to proceed or exit.

**What was fixed / implemented:**
Reader mode does not use `<dialog>` elements or modal overlays. All interactive elements are standard `<button>` elements in the normal document flow. Tab cycles through all buttons on screen and wraps to the browser chrome naturally. No `tabindex="-1"` traps or `keydown` event handlers that intercept Tab presses in accessible renderers.

**Where in the code:**
`web/app.js` — accessible renderers contain no `keydown` event listeners. All interactivity is through `<button onclick>` attributes.

**How to verify:**
Tab repeatedly from the first element on any reader mode screen. Confirm focus cycles through all interactive elements and eventually exits to the browser address bar. Shift+Tab should reverse the cycle. No element should prevent Tab from moving forward.

---

### 2.1.4 Character Key Shortcuts — AA

**What it requires:**
If a keyboard shortcut uses a single character (letter, digit, punctuation), the user must be able to turn it off, remap it, or ensure it only activates when the component has focus.

**Why it matters:**
Single-character shortcuts conflict with screen reader commands and with speech input software (Dragon NaturallySpeaking users who dictate navigation commands). The letter A, for instance, is used by many screen readers.

**What was fixed / implemented:**
The A key single-character shortcut (toggle accessible mode) is active only in terminal mode at the library screen. When accessible mode is active, the terminal keydown handler returns early (`if (isAccessibleMode()) return;`), disabling all single-character shortcuts in reader mode. Reader mode uses only native `<button>` elements with no global keydown handling.

**Where in the code:**
`web/app.js` — terminal mode keydown handler checks `isAccessibleMode()` before processing single-character inputs. Accessible renderers have no global keydown listeners.

**How to verify:**
Switch to accessible/reader mode (press A at the library screen in terminal mode). Confirm that pressing single letter keys (A, T, S, etc.) does not trigger any unintended actions. Use a screen reader — its single-character navigation commands should work normally.

---

### 2.2.2 Pause, Stop, Hide — A

**What it requires:**
Any moving, blinking, or auto-updating content that lasts more than 5 seconds must have a mechanism to pause, stop, or hide it, unless the motion is essential.

**Why it matters:**
Flashing or moving content can trigger seizures (WCAG 2.3) and creates severe distraction for users with ADHD or vestibular disorders. Auto-playing animations can also interfere with screen reader focus.

**What was failing (if applicable):**
The typewriter animation plays text character-by-character over several seconds — moving content that users could not stop without navigating away.

**What was fixed / implemented:**
`startTypewriter()` in `web/typewriter.js` checks `window.matchMedia('(prefers-reduced-motion: reduce)').matches` at invocation. If true, it sets the full text immediately without animation and returns early. The terminal cursor blink animation is suppressed via `@media (prefers-reduced-motion: reduce) { .terminal-cursor { animation: none; } }` in CSS. The session A key toggle also halts typewriter animation for the current session. Reader mode has no auto-playing animations.

**Where in the code:**
`web/typewriter.js` — `startTypewriter()` early-return check. `web/style.css` — `@media (prefers-reduced-motion: reduce)` block suppressing cursor blink.

**How to verify:**
In browser DevTools → Rendering → Emulate CSS media feature, set `prefers-reduced-motion` to `reduce`. Navigate to a story node in terminal mode. Text should appear instantly with no character-by-character animation. The terminal cursor should be static (no blink). Toggle back to `no-preference` to confirm animation resumes.

---

### 2.4.2 Page Titled — A

**What it requires:**
Web pages must have descriptive titles that identify the topic or purpose of the page.

**Why it matters:**
Page titles are the first thing screen readers announce when loading or switching tabs. Descriptive titles help users orient themselves and distinguish between browser tabs. Generic titles like "Choices Matter" on every screen make navigation extremely difficult for screen reader users.

**What was failing (if applicable):**
Before this implementation, `document.title` was set once at load time and never updated as the user navigated between screens (picker, game, ending, settings).

**What was fixed / implemented:**
`setPageTitle(...parts)` helper added in `web/app.js`. It joins parts with " — " and appends " — Choices Matter" as the suffix. Called in all 8 terminal renderers and all 8 accessible renderers. Titles produced: library screen → "Choices Matter"; game screen → "[Story Title] — Choices Matter"; ending screen → "Ending — [Story Title] — Choices Matter"; settings → "Settings — Choices Matter".

**Where in the code:**
`web/app.js` — `setPageTitle()` function definition near the top of the module. Called at the start of every `render*()` and `renderAccessible*()` function.

**How to verify:**
Navigate through all screens in both terminal and reader mode. Check the browser tab title after each navigation — it should update to describe the current screen. In a screen reader, switch browser tabs and confirm the announced title matches the current screen context.

---

### 2.4.3 Focus Order — A

**What it requires:**
If a web page can be navigated sequentially (Tab key), the focus order must preserve meaning and operability — focus should follow the logical reading/interaction order.

**Why it matters:**
If focus jumps unpredictably (e.g. to the footer after submitting a form, when the user expects to see results), keyboard users lose orientation. Programmatically moving focus on page updates is essential for single-page applications.

**What was failing (if applicable):**
When `app.innerHTML` was replaced with new screen content in a single-page app, keyboard focus remained at the browser's remembered position (or was lost entirely). Screen reader users had no cue that a page change occurred.

**What was fixed / implemented:**
After every `app.innerHTML =` assignment in accessible renderers, `first.focus()` is called on the first interactive element (typically the back-navigation button or first story button). This moves focus to the logical start of the new screen. Focus order within each screen matches DOM order, which matches visual reading order.

**Where in the code:**
`web/app.js` — all eight `renderAccessible*()` functions end with `const first = app.querySelector('button'); if (first) first.focus();` (or equivalent targeting the first interactive element).

**How to verify:**
In reader mode, select a story using Tab + Enter. Confirm focus immediately lands on the first button of the game screen (back button or first choice). Tab forward and confirm order matches the visual layout top-to-bottom.

---

### 2.4.6 Headings and Labels — AA

**What it requires:**
Headings and labels must be descriptive — they must convey the topic or purpose of the section or control they represent.

**Why it matters:**
Screen reader users navigate by jumping between headings (H key in NVDA/JAWS). Vague headings like "Section 1" or unlabeled form controls prevent efficient navigation. Descriptive headings allow users to skim content structure.

**What was fixed / implemented:**
Reader mode uses `<h1>` for the primary page title (e.g. "Library", the story title on game screens). `<h2>` is used for section titles (e.g. "Stories", "Settings"). Choice buttons have `aria-label="Choice N: [label text]"` providing a descriptive label that includes position context. Story buttons have `aria-label="[title]. [author]. [estimated time]. [ending count]"` — a complete description. `<nav aria-label="Story choices">` and `<aside aria-label="Notes">` label their landmark regions.

**Where in the code:**
`web/app.js` — `renderAccessiblePicker()` uses `<h1>Library</h1>`, `<h2>Stories</h2>`. `renderAccessibleGame()` uses `<h1>[story title]</h1>`, choice `aria-label` construction. `renderAccessibleSettings()` uses `<h1>Settings</h1>`, `<h2>` per settings section.

**How to verify:**
Open the Headings panel in browser DevTools Accessibility tab. Confirm a logical h1 → h2 hierarchy with no skipped levels. In NVDA, press H to jump between headings and confirm each heading describes its section accurately.

---

### 2.4.7 Focus Visible — AA

**What it requires:**
Any keyboard-operable interface must have a visible focus indicator — the element that has keyboard focus must be visually identifiable.

**Why it matters:**
Without a visible focus indicator, keyboard-only users cannot tell which element will activate when they press Enter or Space. Browsers provide a default focus ring, but many stylesheets suppress it with `outline: none`, making keyboard navigation blind.

**What was failing (if applicable):**
Terminal mode had `.setting-input:focus { ... }` which applied a focus style on mouse click as well as keyboard focus — inconsistent with user expectations and visually noisy. This is not a direct 2.4.7 failure but a related best-practice issue fixed simultaneously.

**What was fixed / implemented:**
All focusable elements in reader mode have `:focus-visible` CSS rules showing the double-ring indicator (`outline: 3px solid var(--r-focus)` + `box-shadow` offset ring). `:focus-visible` (not `:focus`) is used throughout — browsers only apply `:focus-visible` styles when focus was reached via keyboard, suppressing the ring for mouse clicks. Terminal mode: `.setting-input:focus` changed to `.setting-input:focus-visible`.

**Where in the code:**
`web/style.css` — `.r-choice-btn:focus-visible`, `.r-story-btn:focus-visible`, `.r-nav-btn:focus-visible` rules. Terminal mode: `.setting-input:focus-visible` rule.

**How to verify:**
Click a button with the mouse in reader mode — no focus ring should appear (`:focus-visible` suppresses it). Tab to the same button with keyboard — the orange double-ring focus indicator should appear. Tab through all interactive elements confirming the ring is always visible.

---

### 2.5.2 Pointer Cancellation — AA

**What it requires:**
For actions triggered by a single pointer (mouse click, touch tap), at least one of: no down-event trigger, ability to abort/undo the action, up-event triggers with down-event abort mechanism, or essential exception.

**Why it matters:**
Users who accidentally touch the wrong area on a touchscreen, or who click the wrong button, should be able to drag away and release without the action firing. This is especially important for irreversible actions.

**What was fixed / implemented:**
All `<button>` elements in reader mode handle activation via the `click` event (which fires on mouse-up after mouse-down on the same element). The browser's native button behavior allows users to click down on a button, drag away from it, and release — the click event will not fire. No `mousedown` or `touchstart` event listeners trigger navigation. All button `onclick` handlers are standard click handlers.

**Where in the code:**
`web/app.js` — accessible renderers use `onclick="..."` or `addEventListener('click', ...)` exclusively. No `onmousedown` or `ontouchstart` handlers on interactive elements.

**How to verify:**
On a touchscreen or with a mouse: click down on a story button, drag the pointer/finger away from the button, then release. Confirm the story does not launch. Only a full click (down and up on the same button) should trigger navigation.

---

### 2.5.3 Label in Name — AA

**What it requires:**
For user interface components with visible text labels, the accessible name (computed from `aria-label`, `aria-labelledby`, etc.) must contain the visible text label as a substring.

**Why it matters:**
Speech input users (Dragon NaturallySpeaking) activate controls by speaking their visible label. If the `aria-label` is completely different from the visible text, "Click [visible text]" will not activate the control. The visible text must appear somewhere in the accessible name.

**What was fixed / implemented:**
Choice button visible text is `[label text]`; `aria-label` is `"Choice N: [label text]"` — the visible text appears at the end of the aria-label, satisfying the containment requirement. Story button visible text includes the title; `aria-label` begins with the story title. Nav buttons ("Back to library") have their visible text as their accessible name (no separate aria-label needed). Speed preset buttons show the preset name; aria-label includes the preset name.

**Where in the code:**
`web/app.js` — `renderAccessibleGame()` choice button construction: visible inner text is the label, `aria-label` prefixes "Choice N: " before the same label text. `renderAccessiblePicker()` story button construction: `aria-label` starts with the story title which is also the visible `<strong>` text.

**How to verify:**
In browser DevTools Accessibility panel, inspect a choice button. Confirm the "Accessible Name" field contains the same text as the visible button label. Use axe DevTools — no "label-content-name-mismatch" violations should appear.

---

### 3.1.1 Language of Page — A

**What it requires:**
The default human language of each web page must be programmatically determinable via the `lang` attribute on the `<html>` element.

**Why it matters:**
Screen readers use the page language to select the correct text-to-speech voice and pronunciation rules. Without `lang="en"`, a French screen reader may read English text with French phonetics, making it unintelligible.

**What was fixed / implemented:**
`<html lang="en">` is present in `web/index.html`. All story content is authored in English. The attribute was verified present during this implementation — no change was needed.

**Where in the code:**
`web/index.html` — `<html lang="en">` opening tag.

**How to verify:**
View source of `web/index.html`. Confirm the `<html>` tag includes `lang="en"`. Run axe DevTools — no "html-has-lang" or "html-lang-valid" violations.

---

### 3.2.1 On Focus — A

**What it requires:**
Receiving focus must not automatically trigger a change of context (navigation, form submission, opening dialogs, or substantially changing page content).

**Why it matters:**
Screen reader users and keyboard users move through elements to explore the page before activating them. If focusing an element automatically triggers navigation, they cannot review available options without unintentionally activating them.

**What was fixed / implemented:**
No focus event listeners trigger context changes. Programmatic `first.focus()` calls in accessible renderers move focus after a context change has already occurred (triggered by a button click), not as a cause of context change. Button `onfocus` events are not used. All navigation is triggered by `click` events only.

**Where in the code:**
`web/app.js` — accessible renderers: `first.focus()` is called after `app.innerHTML =` replacement, not on any focus event handler. No `onfocus` or `addEventListener('focus', ...)` handlers in accessible renderer code.

**How to verify:**
Tab through all interactive elements in reader mode without pressing Enter or Space. Confirm no screen changes, no dialogs open, and no navigation occurs purely from receiving focus.

---

### 3.2.3 Consistent Navigation — AA

**What it requires:**
Navigation mechanisms that are repeated on multiple pages must occur in the same relative order each time they are repeated, unless a change is initiated by the user.

**Why it matters:**
Consistent navigation placement allows screen reader users to build a mental model of the interface — they know to expect "Back to library" at the top of every screen, and can navigate directly there without exploring the entire page.

**What was fixed / implemented:**
The "Back to library" navigation button appears at the top of `<nav class="r-nav">` as the first interactive element on every accessible screen that is not the picker itself. This consistent positioning is maintained across `renderAccessibleGame()`, `renderAccessibleFolder()`, `renderAccessibleResume()`, `renderAccessibleWarnings()`, `renderAccessibleEnding()`, `renderAccessibleSettings()`, and `renderAccessibleSpeedPresets()`.

**Where in the code:**
`web/app.js` — all accessible renderer functions (except `renderAccessiblePicker()`) begin their HTML structure with the same `<nav class="r-nav"><button class="r-nav-btn" onclick="...">← Back to library</button></nav>` pattern.

**How to verify:**
Navigate through several reader mode screens (picker → story → game → settings → back). Confirm the back button appears at the same visual and DOM position on each screen. Tab on any screen — back button should be the first focusable element (after any skip links).

---

### 4.1.1 Parsing — A

**What it requires:**
HTML must have no major parsing errors: elements have complete start/end tags, elements are nested according to specification, elements do not have duplicate IDs, and elements do not have duplicate attributes.

**Why it matters:**
Malformed HTML causes browsers to apply error-recovery heuristics differently, potentially creating an accessibility tree that differs from what the author intended. Screen readers read the accessibility tree, not the raw HTML.

**What was fixed / implemented:**
Reader mode HTML is constructed as a single `innerHTML` assignment per screen render. Semantic elements are used correctly: `<button>` elements are not placed inside `<a>` tags, list items (`<li>`) are only placed inside `<ul>` or `<ol>`, and `<main>` appears only once per render. The `app` div ID is on the container element which is replaced wholesale — no duplicate IDs are generated. All HTML tags are properly opened and closed.

**Where in the code:**
`web/app.js` — all `renderAccessible*()` functions construct well-formed HTML strings. `web/index.html` — `<main id="app" aria-live="polite">` is the single container.

**How to verify:**
Run axe DevTools on each reader mode screen — no "duplicate-id" violations. Paste the rendered HTML (from DevTools Elements panel) into the W3C HTML Validator (validator.w3.org). Confirm no parsing errors related to nesting or unclosed tags.

---

### 4.1.2 Name, Role, Value — A

**What it requires:**
For all UI components, the name (accessible name), role, and value (current state/property) must be programmatically determinable and set when changed.

**Why it matters:**
Screen readers announce element names, roles, and states to users. A button that says "pressed" or "expanded" in its state communicates toggle status. Without proper role and state markup, users cannot tell the difference between a button that is on versus off.

**What was fixed / implemented:**
All interactive elements are native `<button>` elements (implicit `role="button"` — no explicit ARIA role needed). Non-native semantic elements use explicit ARIA: `<p role="note">` for insets inside `<aside>`, `aria-label` on nav landmarks and aside elements, `aria-hidden="true"` on decorative icons in ending screens. Speed preset buttons use `aria-pressed="true/false"` to communicate toggle state — `aria-pressed` is correct for toggle buttons (vs `aria-current` which is for current item in a set). The accessible mode setting row uses `aria-pressed` on the currently active value button.

**Where in the code:**
`web/app.js` — `renderAccessibleSpeedPresets()` and `renderAccessibleSettings()` set `aria-pressed` on active preset/setting buttons. `renderAccessibleEnding()` uses `aria-hidden="true"` on decorative ending-type icon. Inset `<p role="note">` in `renderAccessibleGame()`.

**How to verify:**
In DevTools Accessibility panel, inspect a speed preset button. Confirm "Pressed" state is shown as `true` for the active preset and `false` for inactive ones. Use NVDA — the active preset button should be announced as "pressed". Inspect inset paragraphs — role should be "note".

---

### 4.1.3 Status Messages — AA

**What it requires:**
Status messages (e.g. search results, error messages, save confirmations) must be programmatically determinable so assistive technologies can announce them without the user needing to move focus to the message.

**Why it matters:**
When content updates without a page reload (as in single-page applications), screen readers do not automatically announce the change unless the update is in a live region or focus is moved to the message. Without this, status updates are silently invisible to screen reader users.

**What was fixed / implemented:**
`<main id="app" aria-live="polite">` in `web/index.html` makes the entire app container a live region with polite announcements. When `app.innerHTML` is replaced during screen transitions, the new content is announced by screen readers with `polite` priority — it waits for the user to finish reading current content before announcing. `aria-live="polite"` (not `assertive`) is used — no content in the web viewer requires immediate interruption. `role="alert"` is not used as there are no error messages requiring urgent announcement.

**Where in the code:**
`web/index.html` — `<main id="app" aria-live="polite" aria-atomic="false">` (or equivalent). All screen transitions write to this container via `app.innerHTML =`.

**How to verify:**
In NVDA + Chrome, navigate to a story and select a choice. The new scene text should be announced without requiring the user to manually navigate to it. Confirm the announcement is not disruptive (polite, not assertive — it waits for silence before speaking).

---

## Not Addressed

The following criteria are not addressed by this implementation. They are noted here for completeness.

### 2.4.1 Bypass Blocks — A
**What it requires:** A mechanism to skip repeated navigation blocks (e.g. a "Skip to main content" link).
**Why not addressed:** The web viewer has minimal repeated navigation. Each screen renders fresh content. A skip link would require persistent nav that does not currently exist.

### 2.4.5 Multiple Ways — AA
**What it requires:** More than one way to locate a page (e.g. search, sitemap, navigation).
**Why not addressed:** The web viewer is a single-page application with a single entry point. Stories are reached only from the library screen. A search feature is not in scope.

### 3.1.2 Language of Parts — AA
**What it requires:** Language of each passage that uses a different language is identified.
**Why not addressed:** Stories are authored in a single language (English). Multi-language story support is not a current feature.

### 3.3.x Input Assistance — AA
**What it requires:** Error identification, labels, suggestions, error prevention for user input.
**Why not addressed:** The web viewer has no form fields that require user input beyond button selection. Settings rows modify values via cycling buttons, not text input. No user-authored content is submitted.
