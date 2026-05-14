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
| `engine.py` | Game loop, navigation, save triggers, ending detection |
| `story.py` | Data models (`Story`, `Node`, `Choice`), JSON loader, validation |
| `save.py` | Persistent save state — read/write/delete per story |
| `display.py` | All `rich` rendering — nothing else imports `rich` |

```
/stories    Drop .json story files here — auto-discovered at startup
/saves      Auto-generated at runtime — one .save.json per story
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

## Story JSON Format

Stories have two top-level keys: `meta` and `nodes`.

**`meta`** — `id` is the save file key; `start_node` must match a key in `nodes`.

```json
{
  "id": "your_story_id",
  "title": "Display Title",
  "version": "1.0",
  "author": "Name",
  "start_node": "intro"
}
```

**`nodes`** — each keyed by node ID:

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Scene description shown to the player |
| `choices` | Yes | Array of `{ "label": "...", "next": "node_id" }` |
| `is_ending` | No | Marks terminal node — triggers ending screen |
| `ending_type` | No | `good`, `bad`, or `neutral` — controls ending panel color |

An empty `choices` array is treated as an ending even without `is_ending: true`.

## Validation Rules

`StoryLoader` validates before the engine starts. It raises on:
- Missing `meta` fields
- `start_node` not present in `nodes`
- Any node missing `text` or `choices`
- Any choice referencing a nonexistent node ID

Fail fast at load with a clear error — never mid-game.

## Save System

- **Location:** `/saves/<story_id>.save.json`
- **Written:** on every node advance (autosave)
- **Deleted:** when an ending is reached, on New Game, or on play-again reset
- **Structure:** `story_id`, `current_node`, `history` (breadcrumb, reserved for future features), `timestamp`

## Display Layer

All `rich` calls are isolated in `display.py`. Named methods: `show_title_screen`, `show_node`, `show_choices`, `show_ending`, `show_save_indicator`, `prompt_story_select`, `prompt_continue_or_new`, `prompt_choice`, `prompt_play_again`.

Ending color map: `good` → bright green, `bad` → bright red, `neutral` → bright yellow.

Invalid input is caught and re-prompted in `display.py` — `Engine` never sees bad input.

## Key Design Constraints

- `rich` is imported **only** in `display.py`. If rendering changes, no other module is affected.
- Stories are a **tree** (not a graph) by authoring convention, not engine enforcement — the engine already navigates by node ID, so convergent nodes just need `next` to point to the same ID.
- One save slot per story — avoids slot-management UI.
- Save is deleted on ending — a save at an ending node would require distinguishing "just reached" from "resuming at", adding edge cases for no benefit.

## Adding a Story

Drop a `.json` file into `/stories/`. No code changes needed.

## Planned Extension Points

- **Inventory/flags:** Add `state: {}` to `SaveState`; add `requires`/`sets` fields to `Choice` JSON; `Engine` checks `requires` before showing a choice and applies `sets` after advancing.
- **Story validator CLI:** `python validate_story.py stories/your_story.json` — all validation logic already lives in `story.py`.
- **Multiple save slots:** Change `SaveManager` to accept a slot index; save path becomes `<story_id>.<slot>.save.json`.
