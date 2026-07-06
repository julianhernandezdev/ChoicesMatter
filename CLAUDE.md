# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Choices Matter** is a Python CLI text adventure engine. Stories are fully data-driven — all content lives in `.json` files under `/stories/`. The engine discovers and runs them; no story content belongs in code.

**v1.0 goal: Godot library readiness.** The Python CLI and JS web player are reference implementations. v1.0 ships when the story format and engine semantics are stable enough for a GDScript port (`ChoicesMatter-Godot`). Until then, versioning is 0.x. Format-breaking features (Chapters, Cross-Story Persistent State, Asset Association Layer) must ship and stabilise before v1.0 is declared. Design decisions should favour format stability and clean API surfaces over convenience features.

## Running the Game

```bash
python main.py
```

## Module Responsibilities

| File | Role |
|---|---|
| `main.py` | Entry point — story picker, wires together all components |
| `src/engine.py` | Game loop, navigation, flag state, save triggers, ending detection; accepts `initial_state` dict to seed state before game loop and on "play again" resets |
| `src/story.py` | Data models (`Story`, `Node`, `Choice`, `Overlay`, `Inset`), JSON loader, validation |
| `src/save.py` | Persistent save state — read/write/delete per story |
| `src/gallery.py` | Ending gallery — tracks found endings per story across runs |
| `src/display.py` | All `rich` rendering — nothing else imports `rich` |
| `src/config.py` | Loads and saves `settings.json`, deep-merges with hardcoded defaults |

```
/src                 Python CLI engine package (imported as src.X from main.py and tests/)
/web                 Browser-based web player — app.js (rendering/UI), engine.js (pure game logic), typewriter.js, storage.js, style.css
/stories             Story JSON files — auto-discovered at startup; organized into subfolders:
                       examples/         (01–20: one file per engine feature)
                       horror/
                       showcase/         (including showcase/sci-fi/)
                       ChoicesMatterGPT/ (GPT-authored stories)
/tests               Test suite — pytest for Python; node tests/test_web_engine.js for JS engine parity
/education           Feature guide docs — one .md per example story + feature-reference.md master index
/accessibility       WCAG docs: implementation guide, screen reader test scripts, renderer authoring checklist
/scripts             Developer tools (sync_stories.py, validate_story.py)
/saves               Auto-generated at runtime — one .save.json + one .gallery.json per story
settings.json        Gitignored, per-user visual style overrides
settings.example.json  Committed template
```

## Dependency Flow

`Engine` is the only coordinator. `Display` is purely passive.

```
main.py
  └── StoryLoader (src/story.py)             loads + validates JSON
  └── Display (src/display.py)               all terminal rendering
  └── Engine (src/engine.py)
        └── Story (src/story.py)             data model, node resolver
        └── SaveManager (src/save.py)        read/write save state
        └── GalleryManager (src/gallery.py)  record + persist found endings
        └── Display (src/display.py)         render calls only
```

`src/config.py` is imported only by `src/display.py`.

## Story JSON Format

Stories have two top-level keys: `meta` and `nodes`.

**`meta`** — `id` is the save file key; `start_node` must match a key in `nodes`. `est_time` is optional; if omitted the engine auto-computes it from word count. `warnings` is optional; if present, a warning screen is shown before the story launches. `auto_visited_flags` defaults to `true`; set to `false` to disable automatic `visited_` flag tracking.

| Field | Required | Notes |
|---|---|---|
| `id` | Yes | Save file key |
| `title` | Yes | Display title |
| `version` | Yes | Version string |
| `author` | Yes | Author name |
| `start_node` | Yes | Must match a key in `nodes` |
| `est_time` | No | Optional; if omitted the engine auto-computes it from word count |
| `warnings` | No | Optional; if present, a warning screen is shown before the story launches |
| `auto_visited_flags` | No | Defaults to `true`; set to `false` to disable automatic `visited_` flag tracking |
| `name_prompt` | No | Non-empty string. Triggers a protagonist name prompt after content warnings and before the first node. Prompt is skipped on save resume. |
| `name_default` | No | Non-empty string. Fallback name used when the player submits empty and no saved `player_name` exists. Requires `name_prompt` to also be set. |

```json
{
  "id": "your_story_id",
  "title": "Display Title",
  "version": "1.0",
  "author": "Name",
  "start_node": "intro",
  "est_time": "15–25 min"
}
```

**`nodes`** — each keyed by node ID:

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Scene description shown to the player |
| `choices` | Yes | Array of choice objects (see below) |
| `insets` | No | Array of inset objects — styled text inside the story panel |
| `overlays` | No | Array of overlay objects — flavour text around the choice list |
| `is_ending` | No | Marks terminal node — triggers ending screen |
| `ending_type` | No | `good`, `bad`, or `neutral` — controls ending panel color |
| `scene` | No | Location label displayed as a dim Rule header above the story panel; once set, carries forward to nodes without a `scene` key |
| `choice_number_color` | No | `rich` color name or hex (e.g. `bright_red`, `#ffaa00`) — node-level fallback for choice number prefixes; overridden per-choice by `choice.color` |
| `corruption` | No | `float` 0–1 or `{ "intensity": float, "mode": "consistent"\|"random", "resolve_style": "decay"\|"cascade" }` — baseline corruption for all text on this node; provides defaults for inline `{corrupt}` spans that omit params |

An empty `choices` array is treated as an ending even without `is_ending: true`.

**Conditional Inline Text**

Any `text` field (node text, inset text, overlay text) may embed conditional spans:

```
{flag?shown when true|shown when false}
```

The `|false branch` is optional — omitting it collapses the span to an empty string when the condition is false. Spans are resolved at runtime against the current flag state.

Flag names in inline spans must match `\w+` (letters, digits, underscores). Flags with hyphens or dots in their names cannot be referenced by inline syntax.

| Condition | Resolves to |
|---|---|
| Flag is `true` | true branch |
| Flag is `false` | false branch |
| Flag missing from state | false branch |
| Integer ≥ 1 | true branch |
| Integer 0 | false branch |
| Non-empty string | true branch |
| Empty string `""` | false branch |

`{key}` patterns without `?` are handled by Variable Text Substitution (see below), which runs before inline resolution. A substituted value may appear inside a conditional branch — this is intentional and the recommended way to personalise branching text.

Example: `"text": "You address {knows_name?the guard by name|the stranger}."`

Inset with no false branch (collapses when unset): `{ "text": "{is_staff?STAFF ACCESS GRANTED}", "style": "system" }`

**Variable Text Substitution**

Any `text` field may embed `{key}` placeholders that are replaced at runtime with the string representation of the named flag's current value:

```
"text": "Hello, {player_name}. You have {coins} coins."
```

| Condition | Result |
|---|---|
| Key present in state | Replaced with `str(value)` — booleans become `True`/`False` (Python) or `true`/`false` (JS) |
| Key present, value is `""` | Placeholder replaced with empty string — `{name}` disappears from the rendered text |
| Key absent from state | Placeholder left intact — `{player_name}` stays in the rendered text |

Substitution runs **before** conditional inline resolution. This means a substituted value can appear inside a conditional branch:

```
"text": "{known?Hello, {player_name}!|Hello, stranger!}"
```

`{player_name}` is the standard token for the player's protagonist name. It is populated automatically from `settings.json` (default: `"Felix"`) or overridden per-story via `meta.name_prompt`.

**Reserved flag names:** do not use `pause` as a flag name — it collides with the `{pause}` typewriter delay token, which is also a `{key}` pattern. Do not use `player_name` as a flag name set by `choice.sets` — it is reserved for the protagonist name prompt feature and the engine's `initial_state`. The tokens `{corrupt}` and `{/corrupt}` are reserved corruption span delimiters; `corrupt` alone (without the closing brace syntax) is not a reserved flag name and can be used freely as a flag key.

**Choice object:**

| Field | Required | Notes |
|---|---|---|
| `label` | Yes | Text shown to the player — does not support `{key}` substitution or `{flag?…}` conditional inline syntax |
| `next` | Yes | Node ID to navigate to |
| `requires` | No | `{ "flag": true/false }` — hides choice if not matched |
| `sets` | No | `{ "flag": true/false }` — applies to player state on advance |
| `color` | No | `rich` color name or hex — overrides the node-level `choice_number_color` (or default `cyan`) for this choice's number prefix |
| `obfuscated` | No | If `true`, renders the label as dim `[REDACTED ██████]` — player can still select it; the real label is never shown |

**Inset object:**

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Line rendered inside the story panel |
| `position` | No | `"before"` (default) or `"after"` the main text |
| `style` | No | Named style key (`system`, `memory`, etc.); `""` renders as dim italic |
| `requires` | No | Same flag dict as choices — hides inset if not matched |

Insets are separated from the main text by a dim rule line inside the panel.

**Overlay object:**

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Whispered line of text |
| `position` | No | `"before"` or `"after"` (default: `"after"`) |
| `style` | No | Named style key; `""` uses the default overlay config |
| `requires` | No | Same flag dict as choices — hides overlay if not matched |

Overlays render around the choice list: `before` above the choices, `after` below. On ending nodes, all overlays appear before the ending panel.

## Flag System

`Engine` maintains a `_state: dict[str, bool | int | str]` across the run.

- `choice.requires` — checked before presenting choices; unmet choices are hidden entirely
- `choice.sets` — applied to `_state` when a choice is taken (via `_apply_sets`)
- `visited_<node_id>` — automatically set to `true` every time a node is entered via `_advance`; use in `requires` to detect revisits. The `visited_` prefix is reserved — manually setting it via `choice.sets` raises a validation error unless `meta.auto_visited_flags` is `false`.
- `overlay.requires` / `inset.requires` — same check; unmet elements are filtered before rendering

**State value types and evaluation:**

| `sets` value | Effect |
|---|---|
| `true` / `false` | Boolean assignment |
| integer (e.g. `5`) | Absolute integer assignment |
| string (e.g. `"red"`) | String assignment |
| delta string (e.g. `"+1"`, `"-2"`) | Adds/subtracts from current int value; missing key defaults to 0 |

| `requires` value | Condition |
|---|---|
| `true` / `false` | Exact boolean match |
| integer (e.g. `3`) | Current value ≥ 3 (threshold) |
| string (e.g. `"red"`) | Exact string match |
| list of strings (e.g. `["red","blue"]`) | Current value is a member of the list |

Flags accumulate within a run and are persisted in the save file. `_reset()` clears them.

## Validation Rules

`StoryLoader` validates before the engine starts. It raises `StoryValidationError` on:
- Missing or non-string `meta` fields
- `start_node` not present in `nodes`
- Any node missing `text` or `choices`
- Any choice referencing a nonexistent node ID
- `story_id` containing characters outside `[A-Za-z0-9_.-]` (path traversal guard)
- `ending_type` not one of `good`, `bad`, `neutral`
- Overlay `position` not `before` or `after`
- `requires` dict: non-string keys, or values not in `{bool, int, str, list[str]}`; list values must be non-empty and contain only strings
- `sets` dict: non-string keys, or values not in `{bool, int, str}`; delta strings must match `^[+-]\d+$`
- `est_time` present but not a non-empty string
- `warnings` present but not a list of non-empty strings
- `scene` present but not a non-empty string
- `choice_number_color` present but not a non-empty string
- Choice `color` present but not a non-empty string
- Choice `obfuscated` present but not a boolean
- `name_prompt` present but not a non-empty string
- `name_default` present without `name_prompt` also being set
- `name_default` present but not a non-empty string
- `corruption` (node field): float not in `[0.0, 1.0]`; dict containing unknown keys (only `intensity`, `mode`, and `resolve_style` are allowed); dict `intensity` not a float in `[0.0, 1.0]`; dict `mode` not `"consistent"` or `"random"`; dict `resolve_style` not `"decay"` or `"cascade"`; any other type
- `{corrupt}` inline span: unclosed `{corrupt}` open tag; stray `{/corrupt}` without matching open; nested `{corrupt}` spans; intensity param not parseable as float in `[0.0, 1.0]`; mode param not `"consistent"` or `"random"`

Fail fast at load with a clear error — never mid-game. In `main.py`, validation is lazy (on selection, not startup) — broken stories show as `-ERROR` and can still be selected to display the error message.

## Save System

**Active save** (`/saves/<story_id>.save.json`):
- **Written:** on every node advance (autosave)
- **Deleted:** when an ending is reached, on New Game, or on play-again reset
- **Structure:** `story_id`, `current_node`, `history` (breadcrumb), `state` (flag dict), `timestamp`

**Ending gallery** (`/saves/<story_id>.gallery.json`):
- **Written:** each time an ending node is reached — accumulates found ending node IDs
- **Survives** active save deletion — persists across playthroughs
- **Cleared:** only via "C → clear all save data" at the story picker, or `GalleryManager.clear_all()`
- **Structure:** `story_id`, `endings_found` (sorted list of node IDs)
- **Displayed:** story picker shows `X/Y endings` (or `X/?` for single-ending stories)

## Display Layer

All `rich` calls are isolated in `display.py`. Named methods:

| Method | Signature |
|---|---|
| `show_title_screen()` | — |
| `clear_screen()` | — |
| `show_node(story_title, node_text, before_insets, after_insets, current_scene=None)` | Story panel; renders dim Rule above panel when `current_scene` is set |
| `show_choices(choices, before_overlays, after_overlays, choice_number_color=None)` | Overlays wrap the choice list; staggers when typewriter is on; number color resolved as `choice.color → choice_number_color → "cyan"` |
| `show_ending(node_text, ending_type, overlays)` | Overlays appear before the ending panel |
| `show_save_indicator()` | — |
| `show_content_warnings(title, warnings)` | Warning panel before story launch; returns True (proceed) / False (back) |
| `show_story_picker(entries)` | — |
| `show_no_stories()` | — |
| `show_picker_error(name, message)` | — |
| `show_clear_complete()` | — |
| `toggle_typewriter()` | Flips `typewriter.enabled` in-memory; prints new state |
| `show_settings_screen()` | Typewriter settings screen — edits a draft copy of config, writes to `settings.json` via `config.save_settings()` on confirm; changes take effect next launch |
| `prompt_story_select(count)` | Returns 1-based int, `None` (quit), `"clear"`, `"toggle_typewriter"`, or `"settings"` |
| `prompt_continue_or_new()` | Returns True (continue) / False (new) |
| `prompt_clear_confirm()` | Returns True/False |
| `prompt_choice(choices)` | Returns 1-based int or None (Q to menu) |
| `prompt_play_again()` | Returns True/False |

Ending color map: `good` → bright green, `bad` → bright red, `neutral` → bright yellow.

Invalid input is caught and re-prompted in `display.py` — `Engine` never sees bad input.

## Accessible Mode

The web viewer supports two rendering modes: **terminal mode** (default, existing behaviour) and **reader mode** (light paper theme, semantic HTML, button-driven). The decision of which mode to use is made by `isAccessibleMode()` in `web/app.js` — call it before rendering, not once at boot.

### Priority chain

Three layers evaluated in order. Lower layers only apply when the layer above returns no value:

| Priority | Source | Variable / API |
| --- | --- | --- |
| 1 (highest) | Session toggle | `sessionAccessible` (module var in `app.js`, never written to disk) |
| 2 | Saved preference | `loadTypewriterSettings().accessible_mode` from localStorage |
| 3 (lowest) | Auto-detect | `matchMedia('(prefers-reduced-motion: reduce)').matches` OR `matchMedia('(prefers-contrast: more)').matches` |

```js
function isAccessibleMode() {
  if (sessionAccessible !== null) return sessionAccessible;
  var saved = loadTypewriterSettings().accessible_mode;
  if (saved !== null && saved !== undefined) return saved;
  return matchMedia('(prefers-reduced-motion: reduce)').matches ||
         matchMedia('(prefers-contrast: more)').matches;
}
```

### `accessible_mode` in web localStorage

| Value | Meaning |
|---|---|
| `null` (default) | Auto-detect — check OS media queries |
| `true` | Always reader mode — auto-detect bypassed |
| `false` | Always terminal mode — auto-detect bypassed |

### Toggle surfaces

- **A key** — at the library screen only (terminal mode), sets `sessionAccessible = !isAccessibleMode()`. Session-only; does not write to disk.
- **"Accessible mode" button** — on the accessible library screen, calls `toggleAccessibleMode()`. Same effect.
- **Settings screen row 9** — cycles `null → true → false → null`. Writes to localStorage on Save.

### Dispatch pattern

One line at the top of each terminal renderer:

```js
function renderGame() {
  if (isAccessibleMode()) { renderAccessibleGame(); return; }
  document.body.classList.remove('reader-mode');
  // ... existing terminal code
}
```

Each accessible renderer adds `document.body.classList.add('reader-mode')`. Each terminal renderer removes it.

Naming convention: `render<ScreenName>()` = terminal renderer, `renderAccessible<ScreenName>()` = accessible renderer.

The eight accessible renderers (all in `web/app.js`):

- `renderAccessiblePicker()`
- `renderAccessibleFolder()`
- `renderAccessibleResume()`
- `renderAccessibleWarnings()`
- `renderAccessibleGame()`
- `renderAccessibleEnding()`
- `renderAccessibleSettings()`
- `renderAccessibleSpeedPresets()`

### Focus management rule

Every accessible renderer must call `focus()` on the first meaningful interactive element **immediately after setting `app.innerHTML`**. Without this, focus lands on `<body>` and screen reader users must re-navigate from the top of the page on every screen transition.

```js
app.innerHTML = html;
var first = app.querySelector('.r-choice-btn');
if (first) first.focus();
```

### Typewriter prohibition

Never call `startTypewriter()` from any accessible renderer. Prose appears fully rendered immediately. This is consistent with `prefers-reduced-motion` intent and eliminates animation flicker for users who triggered reader mode via the OS motion setting.

### `debugMode` across mode switches

`debugMode` persists when switching between terminal and reader mode. It only resets in `renderLibrary()`. In reader mode, the Debug button in `r-nav` cycles `false → "author" → "all" → false` and re-renders.

## Typewriter Effect

When `typewriter.enabled` is true, `show_node` and `show_ending` stream the main prose character by character via `rich.live.Live`. Insets appear instantly. Any keypress skips to the full text.

After prose finishes, `show_choices` waits 250ms then reveals each line (overlays and choices) at 60ms intervals.

Per-character extra pauses are configurable in `settings.json`:

```json
{
  "typewriter": {
    "enabled": false,
    "delay_ms": 20,
    "pause_ms": 500,
    "punctuation_pauses": {
      ".": 150,
      "!": 150,
      "?": 150,
      "…": 200,
      "—": 100
    }
  },
  "corruption": {
    "enabled": true,
    "intensity": 0.6,
    "intensity_multiplier": 1.0,
    "mode": "consistent",
    "charset": "blocks",
    "custom_chars": "█▓▒░",
    "animate": true,
    "scramble_frames": 85,
    "scramble_delay_ms": 40,
    "resolve_frames": null,
    "resolve_delay_ms": null,
    "cascade_stagger_ms": null
  }
}
```

**Inline Pause Token**

Authors may embed `{pause}` anywhere in node or ending `text` to inject an intentional delay mid-stream during typewriter playback:

```
"text": "You reach for the handle.{pause}The door swings open."
```

The pause duration is `typewriter.pause_ms` (default 500 ms). In non-typewriter mode the token is stripped silently. `{pause}` has no effect in inset or overlay text.

`T` at the story picker toggles the effect for the current session. `settings.json` controls the permanent default.

**Corruption Spans**

Authors wrap phrases in `{corrupt}…{/corrupt}` to mark them for glitch rendering. Optional params control intensity and mode for that span:

| Syntax | Effect |
|---|---|
| `{corrupt}text{/corrupt}` | Inherits node-level and global settings defaults |
| `{corrupt:0.8}text{/corrupt}` | Sets intensity (0.0–1.0) for this span |
| `{corrupt:random}text{/corrupt}` | Sets mode for this span (`consistent` or `random`) |
| `{corrupt:0.8:random}text{/corrupt}` | Sets both — intensity first, then mode |
| `{corrupt:0.8:random:decay}text{/corrupt}` | Sets intensity, mode, and resolve style — span types in corrupted, then settles into clean text via a shrinking-intensity decay |
| `{corrupt:0.8:random:cascade}text{/corrupt}` | Same, but characters lock into their clean value one at a time instead of decaying together |

Params are positional and must appear in order (`intensity:mode:resolve_style`) — a value in the wrong slot is not validated against the other params' formats and is rendered as literal text instead of being applied.

Story-defined `intensity`/`mode` (node or span) now fully **override** the global `Intensity Default`/`Mode Default` settings rather than being multiplied with them — the global settings apply only when the story defines neither. `Intensity Multiplier` is a separate, always-applied accessibility control layered on top of whichever value wins (span → node → global default).

Inheritance chain: span param → node `corruption` field → `settings.json` `corruption` defaults. `resolve_style` follows the same chain but has no global-settings fallback — omitting it everywhere simply means the span never enters a resolve phase.

`{corrupt}` spans are not supported in choice `label` fields. Nested spans are forbidden. Every open tag must have a matching close tag — mismatches raise `StoryValidationError` at load time.

In web accessible mode, all corruption is stripped and original text is shown. The CLI `enabled: false` setting has the same effect.

## Key Design Constraints

- `rich` is imported **only** in `display.py`. If rendering changes, no other module is affected.
- Stories are a **tree** (not a graph) by authoring convention, not engine enforcement — the engine navigates by node ID, so convergent nodes just need `next` to point to the same ID.
- One save slot per story — avoids slot-management UI.
- Save is deleted on ending — a save at an ending node would require distinguishing "just reached" from "resuming at", adding edge cases for no benefit.
- `settings.json` is gitignored (per-user). `settings.example.json` is committed as a template.

## Adding a Story

Drop a `.json` file into `/stories/`. No code changes needed.

## Extension Points

- **Story validator CLI:** `python scripts/validate_story.py stories/your_story.json` — validates schema, reachability, and dead-ends. Accepts multiple files: `python scripts/validate_story.py stories/**/*.json`. Exit codes: 0 = clean, 1 = errors found, 2 = no arguments.
- **Multiple save slots:** Change `SaveManager` to accept a slot index; save path becomes `<story_id>.<slot>.save.json`.
- **Graph branching (convergent nodes):** No engine changes needed — just point multiple `next` values at the same node ID.
- **Godot / host engine binding:** The v1.0 deliverable. A GDScript port reads the same `.json` files and emits signals defined in `docs/superpowers/specs/godot-signal-api.md` (not yet written). Format-changing backlog items (Chapters, Cross-Story Persistent State, Asset Association Layer) must ship before the signal API is frozen. Do not introduce new top-level `node` fields or new reserved flag namespaces without considering their GDScript surface.
