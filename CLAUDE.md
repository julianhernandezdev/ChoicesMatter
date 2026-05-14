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
| `story.py` | Data models (`Story`, `Node`, `Choice`, `Overlay`), JSON loader, validation |
| `save.py` | Persistent save state — read/write/delete per story |
| `display.py` | All `rich` rendering — nothing else imports `rich` |
| `config.py` | Loads `settings.json`, deep-merges with hardcoded defaults |

```
/stories             Drop .json story files here — auto-discovered at startup
/saves               Auto-generated at runtime — one .save.json per story
settings.json        Gitignored, per-user visual style overrides
settings.example.json  Committed template
```

## Dependency Flow

`Engine` is the only coordinator. `Display` is purely passive.

```
main.py
  └── StoryLoader (story.py)      loads + validates JSON
  └── Display (display.py)        all terminal rendering
  └── Engine (engine.py)
        └── Story (story.py)      data model, node resolver
        └── SaveManager (save.py) read/write save state
        └── Display (display.py)  render calls only
```

`config.py` is imported only by `display.py`.

## Story JSON Format

Stories have two top-level keys: `meta` and `nodes`.

**`meta`** — `id` is the save file key; `start_node` must match a key in `nodes`. `est_time` is optional; if omitted the engine auto-computes it from word count.

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
| `overlays` | No | Array of overlay objects (see below) |
| `is_ending` | No | Marks terminal node — triggers ending screen |
| `ending_type` | No | `good`, `bad`, or `neutral` — controls ending panel color |

An empty `choices` array is treated as an ending even without `is_ending: true`.

**Choice object:**

| Field | Required | Notes |
|---|---|---|
| `label` | Yes | Text shown to the player |
| `next` | Yes | Node ID to navigate to |
| `requires` | No | `{ "flag": true/false }` — hides choice if not matched |
| `sets` | No | `{ "flag": true/false }` — applies to player state on advance |

**Overlay object:**

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Whispered line of text |
| `position` | No | `"before"` or `"after"` (default: `"after"`) |
| `requires` | No | Same flag dict as choices — hides overlay if not matched |

Overlays render around the choice list: `before` above the choices, `after` below. On ending nodes, all overlays appear before the ending panel.

## Flag System

`Engine` maintains a `_state: dict[str, bool]` across the run.

- `choice.requires` — checked before presenting choices; unmet choices are hidden entirely
- `choice.sets` — applied to `_state` when a choice is taken (in `_advance`)
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

Fail fast at load with a clear error — never mid-game. In `main.py`, validation is lazy (on selection, not startup) — broken stories show as `-ERROR` and can still be selected to display the error message.

## Save System

- **Location:** `/saves/<story_id>.save.json`
- **Written:** on every node advance (autosave)
- **Deleted:** when an ending is reached, on New Game, or on play-again reset
- **Structure:** `story_id`, `current_node`, `history` (breadcrumb), `state` (flag dict), `timestamp`

## Display Layer

All `rich` calls are isolated in `display.py`. Named methods:

| Method | Signature |
|---|---|
| `show_title_screen()` | — |
| `show_node(story_title, node_text)` | Story panel only — no overlay params |
| `show_choices(choices, before_overlays, after_overlays)` | Overlays wrap the choice list |
| `show_ending(node_text, ending_type, overlays)` | Overlays appear before the ending panel |
| `show_save_indicator()` | — |
| `show_story_picker(entries)` | — |
| `show_no_stories()` | — |
| `show_picker_error(name, message)` | — |
| `prompt_story_select(count)` | Returns 1-based int or None (quit) |
| `prompt_continue_or_new()` | Returns True (continue) / False (new) |
| `prompt_choice(choices)` | Returns 1-based int |
| `prompt_play_again()` | Returns True/False |

Ending color map: `good` → bright green, `bad` → bright red, `neutral` → bright yellow.

Invalid input is caught and re-prompted in `display.py` — `Engine` never sees bad input.

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
