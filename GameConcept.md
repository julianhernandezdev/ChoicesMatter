# GameConcept.md
## Choices Matter — CLI Text Adventure Engine

---

## What This Is

A Python-based CLI text adventure engine where stories are fully data-driven. No story content lives in code. Authors write `.json` files and drop them into `/stories/` — the engine handles everything else.

The design goal was a clean separation between **engine logic**, **story content**, and **presentation**. Each layer can change without touching the others.

---

## Architecture

```
main.py       Entry point. Story picker.
engine.py     Game loop. Navigation. Save triggers. Ending detection.
story.py      Data models. JSON loader. Validation.
save.py       Persistent save state. Read/write/delete.
display.py    All Rich rendering. Nothing else knows about Rich.
```

```
/stories      Drop .json files here. Auto-discovered at startup.
/saves        Auto-generated. One save file per story.
```

### Dependency Flow

```
main.py
  └── StoryLoader (story.py)     loads + validates JSON
  └── Display (display.py)       all terminal rendering
  └── Engine (engine.py)
        └── Story (story.py)     data model, node resolver
        └── SaveManager (save.py) read/write save state
        └── Display (display.py) render calls only
```

`Engine` is the only component that coordinates the others. `Display` is purely passive — it renders what it's given and prompts for input. It has no opinions about story state.

---

## The Story Format

Stories are JSON files with two top-level keys: `meta` and `nodes`.

### `meta`

```json
{
  "id": "your_story_id",
  "title": "Display Title",
  "version": "1.0",
  "author": "Name",
  "start_node": "intro"
}
```

`id` is used as the save file key. `start_node` tells the engine where to begin.

### `nodes`

Each node is a keyed object with:

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Scene description shown to the player |
| `choices` | Yes | Array of `{ "label": "...", "next": "node_id" }` pairs |
| `is_ending` | No | Marks node as terminal. Triggers ending screen |
| `ending_type` | No | `good`, `bad`, or `neutral`. Controls ending panel color |

**Terminal node rule:** `choices: []` with `is_ending: true`. The engine also treats an empty choices array as an ending even without the flag, as a fallback.

### Example Node

```json
"intro": {
  "text": "You wake up in a dim room.",
  "choices": [
    { "label": "Try the door", "next": "try_door" },
    { "label": "Search the desk", "next": "search_desk" }
  ]
}
```

### Example Ending Node

```json
"ending_escape": {
  "text": "You slip out into the night. You made it.",
  "choices": [],
  "is_ending": true,
  "ending_type": "good"
}
```

---

## Game Loop (Engine)

```
1. Load story JSON (validate on load, fail fast with clear errors)
2. Check for existing save
   → If found: prompt Continue or New Game
   → If new: start at meta.start_node
3. LOOP:
   a. Render current node text
   b. If ending node → show ending screen, delete save, prompt play again
   c. Render numbered choices
   d. Get valid input (re-prompts on bad input, no crashes)
   e. Advance to next node
   f. Autosave
4. On play again → reset to start, clear save
```

Invalid input is caught in `display.py` and re-prompted inline. The engine never sees bad input.

---

## Save System

One save slot per story, keyed by `story_id`.

**Save file location:** `/saves/<story_id>.save.json`

**Save file structure:**

```json
{
  "story_id": "sample_story",
  "current_node": "search_desk",
  "history": ["intro", "try_door"],
  "timestamp": "2026-05-13T14:32:00"
}
```

`history` is a breadcrumb trail of visited nodes. Not currently used in-game, but preserved for future features (recap, map, hints).

**Save lifecycle:**
- Written on every node advance (autosave)
- Deleted when an ending is reached
- Deleted when player chooses New Game
- Deleted on play-again reset

---

## Display Layer

All `rich` calls are isolated in `display.py`. Nothing else imports `rich`.

| Method | What it renders |
|---|---|
| `show_title_screen()` | Branded title panel on launch |
| `show_node()` | Story text in a `Panel`, titled with story name |
| `show_choices()` | Numbered, color-coded choice list |
| `show_ending()` | Full-width ending panel, color by `ending_type` |
| `show_save_indicator()` | Subtle "✓ Progress saved." line |
| `prompt_story_select()` | Numbered story picker |
| `prompt_continue_or_new()` | Save detected → continue or restart |
| `prompt_choice()` | Validated choice input |
| `prompt_play_again()` | y/n after an ending |

**Ending color map:**

| Type | Color |
|---|---|
| `good` | Bright Green |
| `bad` | Bright Red |
| `neutral` | Bright Yellow |

---

## Validation

`StoryLoader` validates the JSON before the engine ever starts. Errors are raised with explicit messages:

- Missing meta fields
- `start_node` not present in `nodes`
- Any node missing `text` or `choices`
- Any choice referencing a node that doesn't exist

This means a malformed story file fails immediately at load, not mid-game.

---

## Design Decisions

### Why pure tree (no graph)?
Simplest model that covers the core "choices matter" experience. A graph model (nodes that converge or revisit) adds state complexity without adding authoring value at this stage.

### Why one save slot per story?
Avoids slot management UI entirely. Covers 90% of the use case. Multiple slots can be layered in later if needed.

### Why delete save on ending?
An ending means the run is complete. Keeping a save at an ending node would require the engine to distinguish "just reached" from "resuming at" an ending, which adds edge case handling for no real benefit. Cleaner to wipe and prompt replay.

### Why validate on load, not at authoring time?
The engine is the only runtime enforcer. A separate validator script could be added later. For now, fast-fail at startup with a clear error message is sufficient.

### Why isolate Rich in `display.py`?
If the rendering library changes (or a GUI layer is added), nothing in `engine.py`, `story.py`, or `save.py` needs to change. The engine only calls named display methods — it doesn't know what those methods do internally.

---

## Extending This

### Add a new story
Drop a `.json` file into `/stories/`. No code changes needed.

### Add inventory / flags
Add a `state: {}` dict to `SaveState`. Add `requires` and `sets` fields to `Choice` in the JSON schema. `Engine` checks `requires` before showing a choice and applies `sets` after advancing.

### Multiple save slots
Change `SaveManager` to accept a slot index. Add a slot picker to `Display`. `save_path` becomes `<story_id>.<slot>.save.json`.

### Graph branching (nodes that converge)
No changes needed to the engine — it already navigates by node ID. The tree constraint is in the story JSON authoring convention, not the code. Just write JSON that points multiple nodes to the same `next` target.

### A story validator CLI
```bash
python validate_story.py stories/your_story.json
```
Would just call `StoryLoader.load()` and report the result. All validation logic already lives in `story.py`.