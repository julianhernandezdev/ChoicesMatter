# Screen Reader Testing Guide

Automated tools (axe-core, Lighthouse) catch approximately 30% of WCAG issues.
The remaining 70% require a human navigating with a screen reader. This guide
provides step-by-step test scripts for NVDA (Windows) and VoiceOver (macOS/iOS).

---

## Setup

### NVDA (Windows)

1. Download from https://www.nvaccess.org/download/ (free, open-source).
2. Install and launch. NVDA starts speaking immediately.
3. Open **Firefox** (NVDA + Firefox is the most widely tested combination for web apps).
4. NVDA starts in **Browse Mode**: arrow keys read content sequentially, `Tab` jumps between interactive elements (buttons, links, inputs).
5. Press `Insert+Space` to toggle **Forms Mode** (required for interacting with fields). For a web app driven entirely by `<button>` elements, NVDA automatically switches to Forms Mode when a button receives focus — no manual toggle needed.
6. Useful shortcuts:
   - `Insert+F7` — Elements List (lists all headings, links, and buttons on the page)
   - `Insert+T` — Read page title
   - `Insert+Down Arrow` — Read from cursor position
   - `Ctrl` — Stop speech

### VoiceOver (macOS)

1. Enable with `Cmd+F5` (or System Settings → Accessibility → VoiceOver).
2. Use **Safari** (VoiceOver + Safari is the most widely tested combination on macOS).
3. The `VO` key chord is `Ctrl+Option`. All VoiceOver commands use this prefix.
4. Key commands:
   - `VO+Right` / `VO+Left` — Next / previous element
   - `Tab` — Next focusable element (buttons, links, inputs)
   - `VO+Space` or `Space` — Activate a focused button
   - `VO+U` — Open the **Rotor** (navigate by headings, buttons, links — equivalent to NVDA Elements List)
   - `VO+A` — Read from current position

### VoiceOver (iOS)

1. Enable in Settings → Accessibility → VoiceOver.
2. Swipe right to move to the next element; double-tap to activate.
3. Three-finger swipe to scroll.
4. Use Safari.

### Testing URL

- **Production:** `https://julianhernandezdev.github.io/ChoicesMatter/`
- **Local:** `http://localhost` (or whichever port your local server uses)

### Activating Accessible Mode

Accessible (reader) mode can be activated by any of the following:

- **OS Reduce Motion:** macOS → System Settings → Accessibility → Display → enable "Reduce Motion". Windows → Settings → Ease of Access → Display → turn off "Show animations in Windows".
- **OS High Contrast:** Windows → Settings → Ease of Access → High Contrast → turn on a theme. macOS → System Settings → Accessibility → Display → enable "Increase Contrast".
- **Settings screen:** In the app, open Settings (row 9 at the story picker) → set `accessible_mode` to `true` → Save.
- **Keyboard shortcut:** Press `A` at the library/story picker screen.

Confirm accessible mode is active: the page should render in a clean document layout with no box-drawing characters, and the page title bar should show "Library — Choices Matter".

---

## Library Screen — Reader Mode

The library screen lists all available stories as buttons.

1. **Load the page** with accessible mode active (see Setup above).
   - **Expected:** Screen reader announces the page title: "Library — Choices Matter". The `<main>` region with `aria-live="polite"` is present; the SR may announce "main" or the region label on entry.

2. **Press `Tab`** to move to the first story button.
   - **Expected (NVDA):** "The [Story Title]. [est time]. [N/Y endings]. Button."
   - **Expected (VoiceOver):** "[Story Title]. [est time]. [N/Y endings]. Button."
   - The full `aria-label` includes title, estimated reading time, and ending count — all announced as a single unit.

3. **Press `Insert+F7`** (NVDA) or open the VoiceOver Rotor (`VO+U`) and navigate to Buttons.
   - **Expected:** Every story in the library appears as a named button. No button should be labelled simply "button" or be unnamed.

4. **Tab through the full list** to confirm all story buttons are reachable and none are skipped.
   - **Expected:** Tab order matches the visual order of stories. Focus indicator (outline) is visible on each button.

5. **Press `Enter` or `Space`** on any story button.
   - **Expected:** The screen transitions (immediately if no save/warnings; otherwise to Resume Prompt or Warnings). The SR announces the new screen's page title without a full page reload.

6. **Navigate back to library** using the "Back to library" button (if shown after a transition).
   - **Expected:** Focus returns to a sensible position on the library screen — either the first story button or the previously selected story button.

---

## Folder Screen — Reader Mode

Shown when the story library contains stories grouped into subfolders.

1. **Tab to the first folder button.**
   - **Expected (NVDA):** "[Folder Name]. Button." (or similar, depending on the `aria-label` set on the folder button)
   - **Expected (VoiceOver):** "[Folder Name]. Button."

2. **Tab through the folder list** to confirm all folders are reachable.
   - **Expected:** Each folder is a distinct, named button. Tab order matches visual order.

3. **Press `Enter` or `Space`** on a folder button.
   - **Expected:** The screen transitions to show the stories inside that folder. Page title updates to "[Folder Name] — Choices Matter". SR announces the title change. Focus moves to the first story button inside the folder.

4. **Tab through the stories** within the folder.
   - **Expected:** Story buttons inside the folder are announced with the same format as the Library screen (title, est time, endings).

5. **Tab to "Back to library"** and press `Enter`.
   - **Expected:** Returns to the top-level library. Focus moves to the first interactive element on the library screen.

---

## Resume Prompt Screen — Reader Mode

Shown when a save file exists for the selected story.

1. **Select a story that has an active save.** (Start a story, make a choice, then return to the library and select the same story again.)
   - **Expected:** Resume Prompt screen loads. Page title updates to "Resume — Choices Matter". SR announces the title.

2. **Tab to the "Continue" button.**
   - **Expected (NVDA):** "Continue. Button."
   - **Expected (VoiceOver):** "Continue. Button."
   - The button should be the first focusable element after the screen loads (focus should have moved here automatically).

3. **Tab to the "New Game" button.**
   - **Expected (NVDA):** "New Game. Button."
   - **Expected (VoiceOver):** "New Game. Button."

4. **Press `Enter` on "Continue".**
   - **Expected:** Game screen loads, resuming at the saved node. Page title updates. Focus moves to the first choice button.

5. **Repeat steps 1–3, then press `Enter` on "New Game".**
   - **Expected:** Game starts fresh from the beginning. The saved state is cleared. Focus moves to the first choice button of the opening node.

---

## Warnings Screen — Reader Mode

Shown before stories that have declared content warnings.

1. **Select a story with content warnings** (a story whose JSON `meta.warnings` list is non-empty).
   - **Expected:** Warnings screen loads. Page title updates to "Content Warning — Choices Matter". SR announces the title.

2. **Navigate with arrow keys or `VO+Right`** to read the warning text.
   - **Expected:** Warning strings are read as body text. No warning is skipped or hidden from the SR.

3. **Tab to the "I understand, continue" button.**
   - **Expected (NVDA):** "I understand, continue. Button."
   - **Expected (VoiceOver):** "I understand, continue. Button."
   - This button should be the first focusable element (focus moved here on screen load).

4. **Tab to the "Go back" button.**
   - **Expected (NVDA):** "Go back. Button."
   - **Expected (VoiceOver):** "Go back. Button."
   - Tab order must be: "I understand, continue" → "Go back" (not reversed).

5. **Press `Enter` on "I understand, continue".**
   - **Expected:** Proceeds to Resume Prompt (if save exists) or Game screen. SR announces new page title.

6. **Press `Enter` on "Go back".**
   - **Expected:** Returns to the library screen. SR announces "Library — Choices Matter".

---

## Game Screen — Reader Mode

The main play screen showing story prose and choices.

1. **Start or resume a story** so the Game screen is visible.
   - **Expected:** Page title updates to "[Story Title] — Choices Matter". SR announces the title on load.

2. **Navigate the prose with arrow keys** (NVDA Browse Mode) or `VO+Right` (VoiceOver).
   - **Expected:** The story prose inside the `<article>` element is read sequentially. Every sentence and paragraph is reachable without Tab. No box-drawing characters or raw escape sequences are present.

3. **Check insets** (notes/system messages, if the node has any).
   - **Expected:** The `<aside>` element containing insets is announced with an accessible label (e.g., "Notes" or "Supplementary information"). Inset text is readable via arrow key navigation.

4. **Press `Tab`** to move to the first choice button.
   - **Expected (NVDA):** "Choice 1: [choice label]. Button."
   - **Expected (VoiceOver):** "Choice 1: [choice label]. Button."
   - The `aria-label` attribute provides this announcement even if the visible text differs.

5. **Tab through remaining choice buttons.**
   - **Expected:** Each subsequent choice is announced as "Choice N: [label]. Button." Tab order matches the visual order of choices (1, 2, 3, ...). No choice is skipped.

6. **Press `Enter` or `Space`** on a choice button.
   - **Expected:** New node loads. SR announces the updated page title (if changed). Focus moves automatically to the first choice button of the new node — the SR announces "Choice 1: [new label]. Button." without the user needing to Tab.

7. **Verify no choice button is unlabelled.** Use `Insert+F7` (NVDA) or the VoiceOver Rotor to list all buttons and confirm each has a descriptive name beginning with "Choice N:".

---

## Ending Screen — Reader Mode

Shown when the player reaches a terminal node (story ending).

1. **Play through a story to an ending.**
   - **Expected:** Ending screen loads. Page title updates to "[Story Title] — Choices Matter". SR announces the title.

2. **Navigate with arrow keys or `VO+Right`** to read the ending content.
   - **Expected:** The ending type label (e.g., "Good ending", "Bad ending", or "Neutral ending") is announced before or alongside the ending prose. No choice buttons are present — the SR should not announce any "Choice N:" buttons on this screen.

3. **Tab to the "Play again" button.**
   - **Expected (NVDA):** "Play again. Button."
   - **Expected (VoiceOver):** "Play again. Button."
   - This should be the first or only interactive element on the screen (focus moved here on load, or to "Back to library").

4. **Tab to the "Back to library" button.**
   - **Expected (NVDA):** "Back to library. Button."
   - **Expected (VoiceOver):** "Back to library. Button."

5. **Press `Enter` on "Play again".**
   - **Expected:** Game restarts from the beginning of the story. Focus moves to first choice button.

6. **Press `Enter` on "Back to library".**
   - **Expected:** Library screen loads. SR announces "Library — Choices Matter".

---

## Settings Screen — Reader Mode

The settings/configuration screen.

1. **Open the Settings screen** (from the library, Tab to the Settings button and press `Enter`; or use row 9 at the story picker).
   - **Expected:** Page title updates to "Settings — Choices Matter". SR announces the title. Focus moves to the first interactive element in the settings form.

2. **Tab through each settings row.**
   - **Expected:** Each row is announced with the setting name and its current value. For example: "Accessible mode. Off. Button." or "Delay (ms). 20. Edit text." Tab order matches the visual order of settings from top to bottom.

3. **Check that the current value of each setting is readable without activating the control.** Use arrow keys to read surrounding text.
   - **Expected:** The setting label and current value are both present in the DOM as readable text, not just as placeholder or tooltip text.

4. **Tab to the Speed Presets button** (at or near the end of the settings list).
   - **Expected (NVDA):** "Speed Presets. Button." (or similar label)
   - **Expected (VoiceOver):** "Speed Presets. Button."

5. **Press `Enter` on the Speed Presets button.**
   - **Expected:** Transitions to the Speed Presets screen. SR announces the new page title.

6. **Tab to the "Save" button and press `Enter`.**
   - **Expected:** Settings are saved. SR announces confirmation feedback (if any) or returns to the library. No silent failure.

---

## Speed Presets Screen — Reader Mode

Preset configuration options for typewriter speed.

1. **Navigate to the Speed Presets screen** from Settings (see Settings Screen step 4–5).
   - **Expected:** Page title updates to "Speed Presets — Choices Matter". SR announces the title. Focus moves to the first preset button.

2. **Tab to the currently active preset button.**
   - **Expected (NVDA):** "[Preset Name]. Button. Pressed." — NVDA announces "pressed" for `aria-pressed="true"`.
   - **Expected (VoiceOver):** "[Preset Name]. Selected. Button." — VoiceOver announces the pressed state differently but the meaning is equivalent.

3. **Tab to an inactive preset button.**
   - **Expected (NVDA):** "[Preset Name]. Button." — no "pressed" announcement (because `aria-pressed="false"`).
   - **Expected (VoiceOver):** "[Preset Name]. Button." — VoiceOver may announce "not selected" depending on version.

4. **Tab through all preset buttons** to confirm each is reachable and named.
   - **Expected:** All presets appear in the Elements List / Rotor. None are unnamed. Tab order matches visual order.

5. **Press `Enter` or `Space`** on an inactive preset.
   - **Expected:** The selected preset becomes active (`aria-pressed="true"`). The previously active preset's `aria-pressed` changes to `"false"`. SR announces the new state of the activated button. The screen may automatically return to the Settings screen after selection.

6. **Confirm the selection is reflected in Settings.** Return to the Settings screen and check the relevant speed values.
   - **Expected:** Delay and speed values have updated to match the chosen preset. SR reads the new values when tabbing through settings rows.

---

## Common Failure Patterns

| Symptom | Cause | Fix |
|---|---|---|
| SR announces "group" with no label | Missing `aria-label` on `<nav>` or `<aside>` | Add `aria-label` attribute |
| SR reads out ASCII art or box-drawing characters | `makeRule()` or `renderRule()` used in accessible renderer | Accessible renderers must never call these functions |
| Focus disappears after screen change | `focus()` not called after `app.innerHTML` replacement | Add `if (first) first.focus()` at end of each accessible renderer |
| SR announces "button" with no label | `<button>` has no text content and no `aria-label` | Add visible text or `aria-label` |
| SR reads wrong `aria-label` | `escapeHtml()` not used in `aria-label` attribute value | Always use `escapeHtml()` for attribute interpolation |
| Tab order jumps unexpectedly | DOM order does not match visual order | Fix HTML source order; never use `tabindex > 0` |
| SR reads "image" for emoji | Emoji in button label without `aria-hidden` wrapper | Wrap decorative emoji in `<span aria-hidden="true">` |
| Page title not updated | `setPageTitle()` not called in renderer | Call `setPageTitle()` as first side-effect in every renderer |
| Choice buttons not reachable by Tab | Buttons inside a non-interactive container | Ensure choices are direct children of the app or a focusable container |
