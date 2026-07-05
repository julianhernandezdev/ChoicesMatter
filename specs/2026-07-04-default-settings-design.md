# Default Settings & Section Registry — Design Spec

**Date:** 2026-07-04  
**Status:** Approved — pending implementation plan  
**Platforms:** Python CLI (`src/display.py`, `src/config.py`) + Web (`web/app.js`, `web/typewriter.js`)

---

## Problem

There is no way to reset settings to their defaults. Settings screens are also fully hardcoded — adding a new section requires touching rendering, input handling, and reset logic independently on both platforms. This spec introduces a "Reset to Defaults" feature backed by a lightweight section registry that standardizes how settings sections are defined and consumed.

---

## Goals

1. "Reset to Defaults" on every settings screen (main + sub-screens).
2. All settings screen logic (rendering, input, reset) derives from a single `SETTINGS_SECTIONS` data structure per platform.
3. Adding a new section = one new registry entry. Reset checkbox, rendering, and sub-screen navigation pick it up automatically.

---

## Non-Goals (deferred)

- **Full plugin surface** — contributor API docs, key-collision validation, schema versioning. Deferred to a future milestone after section registry is stable.
- **Key input rebinding** — named key constants are a precursor; a "Keybindings" settings section is future work.

---

## Section Registry

### Structure

Each entry in `SETTINGS_SECTIONS` (JS array in `app.js`; Python list of dicts in `display.py`):

```
{
  id:                     str   — unique slug ("typewriter", "corruption", …)
  label:                  str   — display name ("Typewriter", "Corruption", …)
  preserveOnGlobalReset:  bool  — if true: excluded from reset checkbox list; values silently preserved
  hasSubscreen:           bool  — if true: renders as a single "→" nav row on the main screen
  defaults:               dict  — default values for this section's keys only
  rows:                   list  — row descriptors (see Row Descriptor below)
}
```

### Row Descriptor

Same shape already used by `SETTINGS_ROWS` in the web:

```
{
  key:        str   — dot-path into settings draft ("typewriter.enabled", "corruption.intensity")
  label:      str   — display name
  type:       str   — "boolean" | "number" | "float" | "text" | "cycle" | "speed_presets" | "a11y"
  unit:       str?  — optional unit suffix ("ms", "×")
  values:     list? — for "cycle" type: ordered list of valid values
  range:      tuple? — for "number"/"float": (min, max)
  subsection: str?  — optional visual sub-header rendered above this row on the main screen
}
```

### Sections

| id | label | preserveOnGlobalReset | hasSubscreen |
|---|---|---|---|
| `typewriter` | Typewriter | false | **true** |
| `display` | Display | false | false |
| `corruption` | Corruption | false | **true** |
| `player` | Player | **true** | false |
| `accessibility` | Accessibility | **true** | **true** |

**Preserved sections** (`player`, `accessibility`) are never listed in the reset checkbox UI. Their values are silently kept on global reset; a feedback line confirms this to the user.

---

## Main Settings Screen

Renders by iterating `SETTINGS_SECTIONS` in order. Rows are auto-numbered sequentially across all sections.

- `hasSubscreen: false` sections — all rows rendered inline.
- `hasSubscreen: true` sections — rendered as a single nav row with a `→` indicator. Section rows are not shown inline.

```
Settings

  Typewriter
  1.  →

  Display
  2.  Stories per page   5

  Corruption
  3.  →

  Player
  4.  Player name        Felix

  Accessibility
  5.  →

  Enter a number to edit · S save · X discard · R reset
```

**Web:** `SETTINGS_ROWS` becomes a derived constant — `SETTINGS_SECTIONS.flatMap(s => s.rows)` — so existing rendering code that reads `SETTINGS_ROWS` is unchanged for inline sections.

**Python CLI:** `show_settings_screen` iterates the registry instead of hardcoding rows. The existing `_settings_corruption` method is replaced by a generic `_section_subscreen(section)`.

---

## Sub-screens

Every `hasSubscreen: true` section gets a dedicated sub-screen rendered generically by:

- **Web:** `renderSectionSubscreen(section)`
- **Python CLI:** `_section_subscreen(section)`

Both read from `section.rows` and `section.defaults`. No section-specific rendering code is needed.

### Sub-screen nav keys

| Key | Action |
|---|---|
| `S` | Save draft → return to main settings screen |
| `X` | Discard changes to this section only → return to main settings screen (rest of draft intact) |
| `M` | Save draft → return to main menu (story picker / library) |
| `Q` | Discard all changes → return to main menu |
| `R` | Reset this section to defaults (with confirmation) |

Footer hint shown on every sub-screen:
```
S save · X back · M save+home · Q discard+home · R reset section
```

---

## Reset Flow

### Global reset — main settings screen `R`

1. Show checkbox selector listing all sections where `preserveOnGlobalReset: false`.
2. All checkboxes start unchecked.
3. User types a section number + Enter to toggle its checkbox. Supports multi-digit numbers (scales beyond 9 sections).
4. `Y` + Enter to confirm. `X` to cancel.
5. Selecting nothing and pressing `Y` is a no-op — show "Nothing selected."
6. On confirm: for each checked section, apply `section.defaults` to the draft.
7. Feedback shown on the main settings screen:

```
Reset: Typewriter, Display. Player name and accessible mode were preserved.
```

8. Draft is modified but not yet saved — user still presses `S` or `M` to persist.

```
Reset to Defaults

Select sections to reset:

  1. [ ] Typewriter
  2. [ ] Corruption
  3. [ ] Display

  Number + Enter to toggle · Y to confirm · X to cancel
```

### Section reset — sub-screen `R`

1. Show inline confirmation prompt:
   ```
   Reset Typewriter to defaults? (Y to confirm, any other key to cancel)
   ```
2. On `Y`: apply `section.defaults` to the relevant keys in the draft.
3. Feedback line: `"Typewriter reset to defaults."`
4. Stay on the sub-screen — user reviews the reset values, then navigates with S/X/M/Q.

---

## Preserved-field feedback

When a global reset is applied (at least one section checked), always append the preservation note to the feedback line if `player_name` or `accessible_mode` differs from defaults:

> "Player name and accessible mode were preserved."

If both are already at their defaults, omit the note — it adds noise without value.

---

## Web — Accessible Mode

`renderAccessibleSettings()` mirrors the terminal changes:

- Sub-screen sections render as a button row (`→`) instead of inline settings.
- Sub-screen views rendered by `renderAccessibleSectionSubscreen(section)`.
- Reset button added to the accessible settings `r-nav`: "Reset to defaults".
- Sub-screen accessible views gain: Save, Back, Save & Home, Discard & Home, Reset section buttons.

---

## Future Work

- **Full plugin surface:** contributor API, section key-collision validation, schema versioning.
- **Keybinding settings section:** standardize nav key definitions as named constants, then expose a "Controls" section where users can remap them.
