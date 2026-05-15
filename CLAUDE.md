# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Choices Matter** is a Python CLI text adventure engine. Stories are fully data-driven — all content lives in `.json` files under `/stories/`. The engine discovers and runs them; no story content belongs in code.

## Running the Game

```bash
python main.py
```

## Module Responsibilities

| File | Role |
|---|---|
| `main.py` | Entry point — story picker, wires together all components |
| `engine.py` | Game loop, navigation, flag state, save triggers, ending detection |
| `story.py` | Data models (`Story`, `Node`, `Choice`, `Overlay`, `Inset`), JSON loader, validation |
| `save.py` | Persistent save state — read/write/delete per story |
| `gallery.py` | Ending gallery — tracks found endings per story across runs |
| `display.py` | All `rich` rendering — nothing else imports `rich` |
| `config.py` | Loads and saves `settings.json`, deep-merges with hardcoded defaults |

```
/stories             Drop .json story files here — auto-discovered at startup
/saves               Auto-generated at runtime — one .save.json + one .gallery.json per story
settings.json        Gitignored, per-user visual style overrides
settings.example.json  Committed template
```

## Dependency Flow

`Engine` is the only coordinator. `Display` is purely passive.

```
main.py
  └── StoryLoader (story.py)             loads + validates JSON
  └── Display (display.py)               all terminal rendering
  └── Engine (engine.py)
        └── Story (story.py)             data model, node resolver
        └── SaveManager (save.py)        read/write save state
        └── GalleryManager (gallery.py)  record + persist found endings
        └── Display (display.py)         render calls only
```

`config.py` is imported only by `display.py`.

## Story JSON Format

Stories have two top-level keys: `meta` and `nodes`.

**`meta`** — `id` is the save file key; `start_node` must match a key in `nodes`. `est_time` is optional; if omitted the engine auto-computes it from word count. `warnings` is optional; if present, a warning screen is shown before the story launches. `auto_visited_flags` defaults to `true`; set to `false` to disable automatic `visited_` flag tracking.

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

An empty `choices` array is treated as an ending even without `is_ending: true`.

**Choice object:**

| Field | Required | Notes |
|---|---|---|
| `label` | Yes | Text shown to the player |
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

`Engine` maintains a `_state: dict[str, bool]` across the run.

- `choice.requires` — checked before presenting choices; unmet choices are hidden entirely
- `choice.sets` — applied to `_state` when a choice is taken (in `_advance`)
- `visited_<node_id>` — automatically set to `true` every time a node is entered via `_advance`; use in `requires` to detect revisits. The `visited_` prefix is reserved — manually setting it via `choice.sets` raises a validation error unless `meta.auto_visited_flags` is `false`.
- `overlay.requires` — same check; unmet overlays are not passed to `display.show_choices`

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
- Flag dicts (`requires`, `sets`) mapping non-string keys or non-boolean values
- `est_time` present but not a non-empty string
- `warnings` present but not a list of non-empty strings
- `scene` present but not a non-empty string
- `choice_number_color` present but not a non-empty string
- Choice `color` present but not a non-empty string
- Choice `obfuscated` present but not a boolean

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

## Typewriter Effect

When `typewriter.enabled` is true, `show_node` and `show_ending` stream the main prose character by character via `rich.live.Live`. Insets appear instantly. Any keypress skips to the full text.

After prose finishes, `show_choices` waits 250ms then reveals each line (overlays and choices) at 60ms intervals.

Per-character extra pauses are configurable in `settings.json`:

```json
{
  "typewriter": {
    "enabled": false,
    "delay_ms": 20,
    "punctuation_pauses": {
      ".": 150,
      "!": 150,
      "?": 150,
      "…": 200,
      "—": 100
    }
  }
}
```

`T` at the story picker toggles the effect for the current session. `settings.json` controls the permanent default.

## Key Design Constraints

- `rich` is imported **only** in `display.py`. If rendering changes, no other module is affected.
- Stories are a **tree** (not a graph) by authoring convention, not engine enforcement — the engine navigates by node ID, so convergent nodes just need `next` to point to the same ID.
- One save slot per story — avoids slot-management UI.
- Save is deleted on ending — a save at an ending node would require distinguishing "just reached" from "resuming at", adding edge cases for no benefit.
- `settings.json` is gitignored (per-user). `settings.example.json` is committed as a template.

## Adding a Story

Drop a `.json` file into `/stories/`. No code changes needed.

## Extension Points

- **Story validator CLI:** `python validate_story.py stories/your_story.json` — all validation logic already lives in `story.py`.
- **Multiple save slots:** Change `SaveManager` to accept a slot index; save path becomes `<story_id>.<slot>.save.json`.
- **Graph branching (convergent nodes):** No engine changes needed — just point multiple `next` values at the same node ID.
