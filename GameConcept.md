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
engine.py     Game loop. Navigation. Flag state. Save triggers. Ending detection.
story.py      Data models. JSON loader. Validation.
save.py       Persistent save state. Read/write/delete.
display.py    All Rich rendering. Nothing else knows about Rich.
config.py     Loads settings.json. Merges with hardcoded defaults.
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

`Engine` is the only component that coordinates the others. `Display` is purely passive — it renders what it's given and prompts for input. It has no opinions about story state. `config.py` is imported only by `display.py`.

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

Each node is a keyed object:

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Scene description shown to the player |
| `choices` | Yes | Array of choice objects |
| `overlays` | No | Array of overlay objects |
| `is_ending` | No | Marks node as terminal. Triggers ending screen |
| `ending_type` | No | `good`, `bad`, or `neutral`. Controls ending panel color |

**Terminal node rule:** `choices: []` with `is_ending: true`. The engine also treats an empty choices array as an ending even without the flag, as a fallback.

### Choice Object

```json
{ "label": "Use the silver watch", "next": "bribed_escape", "requires": { "logbook_read": true } }
```

| Field | Required | Notes |
|---|---|---|
| `label` | Yes | Text shown to the player |
| `next` | Yes | Node ID to navigate to |
| `requires` | No | Flag conditions — choice is hidden if not met |
| `sets` | No | Flags to apply to player state on advance |

### Overlay Object

```json
{ "text": "Harrow's words surface in your mind.", "requires": { "logbook_read": true }, "position": "before" }
```

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Whispered line displayed to the player |
| `position` | No | `"before"` or `"after"` (default: `"after"`) |
| `requires` | No | Same flag system as choices — hidden if not met |

Overlays appear around the choice list, not the story prose: `before` above, `after` below. On ending nodes, overlays appear before the ending panel.

### Full Node Example

```json
"use_key": {
  "text": "The key fits. The lock turns with a satisfying click. You ease the door open — and walk straight into the guard.",
  "overlays": [
    {
      "text": "Harrow's entry surfaces: 'The night guard has a weakness for silver.'",
      "requires": { "logbook_read": true },
      "position": "before"
    }
  ],
  "choices": [
    { "label": "Try to push past him", "next": "caught" },
    {
      "label": "Produce the silver watch. His grip loosens.",
      "next": "bribed_escape",
      "requires": { "logbook_read": true }
    }
  ]
}
```

---

## The Flag System

`Engine` maintains a `_state: dict[str, bool]` across the run. Flags accumulate as the player makes choices and are cleared on reset or new game.

**`requires`** — a dict of `{ "flag": true/false }` conditions checked against current state. All conditions must match. Used on both `Choice` and `Overlay` objects. Unmet → hidden from the player entirely.

**`sets`** — a dict applied to `_state` when a choice is taken. Applied before advancing to the next node.

This means flags affect:
- **What you can do** — choices only appear if their `requires` are met
- **What you notice** — overlays only appear if their `requires` are met

A player who found the logbook and a player who didn't see a different world at the same node.

---

## The Overlay System

Overlays are whispered lines of text attached to nodes. They are conditional on the flag system and positional relative to the choice list.

**`"before"` overlays** — appear above the choices. Used for prior knowledge framing the decision: the player *remembers* something relevant as they consider their options.

**`"after"` overlays** — appear below the choices. Used for dawning realizations: something *occurs* to the player after reading the choices.

Multiple overlays can match and stack. Before and after pools accumulate independently. Overlays with unmet `requires` are filtered by `Engine` before being passed to `Display` — `Display` only receives the text strings, never the conditions.

---

## Game Loop (Engine)

```
1. Load story JSON (validate on load, fail fast with clear errors)
2. Check for existing save
   → If found: prompt Continue or New Game
   → If new: start at meta.start_node with empty flag state
3. LOOP:
   a. Get current node
   b. Filter choices by requires (flag check)
   c. Filter overlays by requires, split into before/after lists
   d. If ending node (or no visible choices):
      → show_ending(text, type, overlays)
      → delete save
      → prompt play again: True → _reset() + continue; False → return
   e. show_node(title, text)
   f. show_choices(visible, before_overlays, after_overlays)
   g. prompt_choice(visible) — re-prompts on invalid input
   h. Apply choice.sets to flag state
   i. Advance to choice.next
   j. Autosave (current_node + history + flag state)
4. On play again → reset node, history, flag state; delete save
```

Invalid input is caught in `display.py` and re-prompted inline. The engine never sees bad input.

---

## Save System

One save slot per story, keyed by `story_id`.

**Save file location:** `/saves/<story_id>.save.json`

**Save file structure:**

```json
{
  "story_id": "the_locked_room",
  "current_node": "use_key",
  "history": ["intro", "search_desk", "read_logbook"],
  "state": { "logbook_read": true },
  "timestamp": "2026-05-13T14:32:00"
}
```

`history` is a breadcrumb trail of visited nodes — not currently used in-game, but preserved for future features.

`state` is the player's full flag dictionary, persisted so that a restored save has the same conditional options as the original run.

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
| `show_node(title, text)` | Story text in a Panel, titled with story name |
| `show_choices(choices, before, after)` | Overlays + numbered choice list + overlays |
| `show_ending(text, type, overlays)` | Overlays + full-width ending panel (color by type) |
| `show_save_indicator()` | Subtle "✓ Progress saved." line |
| `show_story_picker(entries)` | Numbered story picker with -ERROR markers |
| `show_no_stories()` | "No stories found" message |
| `show_picker_error(name, message)` | Inline load error for a selected story |
| `prompt_story_select(count)` | Returns 1-based index or None (quit) |
| `prompt_continue_or_new()` | Save detected → C to continue or N for new |
| `prompt_choice(choices)` | Validated choice input, re-prompts on bad input |
| `prompt_play_again()` | Y/N after an ending |

**Ending color map:**

| Type | Color |
|---|---|
| `good` | Bright Green |
| `bad` | Bright Red |
| `neutral` | Bright Yellow |

### Overlay Style

Overlay visual style is controlled by `settings.json` (gitignored, per-user). The committed `settings.example.json` serves as the template. `config.py` deep-merges user settings over hardcoded defaults, so partial overrides work. Missing or malformed `settings.json` silently falls back to defaults.

Configurable: `color`, `dim`, `italic`, `bold`, `underline`, `strike`, `prefix`.

---

## Validation

`StoryLoader` validates the JSON before the engine ever starts. Errors are raised with explicit messages:

- Missing meta fields
- `start_node` not present in `nodes`
- Any node missing `text` or `choices`
- Any choice referencing a node that doesn't exist

In `main.py`, validation is **lazy** (on story selection, not startup). Broken stories appear as `-ERROR` in the picker and can be selected to display the error — they don't block other stories from loading.

---

## Design Decisions

### Why pure tree (no graph)?
Simplest model that covers the core "choices matter" experience. Convergent nodes are supported by the engine (just point multiple `next` values at the same ID) — the tree constraint is authoring convention, not code.

### Why one save slot per story?
Avoids slot management UI entirely. Covers 90% of the use case. Multiple slots can be layered in later.

### Why delete save on ending?
An ending means the run is complete. Keeping a save at an ending node would require the engine to distinguish "just reached" from "resuming at" — edge cases for no real benefit.

### Why validate on selection, not startup?
Authors iterate on stories while the engine is running. Eager validation at startup would require a restart to pick up fixes. Lazy validation means a fixed story becomes immediately selectable on the next pick.

### Why isolate Rich in `display.py`?
If the rendering library changes (or a GUI layer is added), nothing in `engine.py`, `story.py`, or `save.py` needs to change. The engine only calls named display methods — it doesn't know what those methods do internally.

### Why are overlays around the choices, not the story prose?
The player reads the scene text, then considers options. Overlays model *what occurs to the player in that moment of decision* — the knowledge that surfaces as they look at their choices, or the realization that follows. Placing them inside the prose panel would blur the line between narration and meta-awareness.

### Why filter overlays in Engine, not Display?
`Display` is purely passive — it renders what it's given. Flag logic belongs in `Engine`, which owns `_state`. This means `Display.show_choices` only receives plain text strings, never conditions or flag dicts.

---

## Extending This

### Add a new story
Drop a `.json` file into `/stories/`. No code changes needed.

### Story validator CLI
```bash
python validate_story.py stories/your_story.json
```
Would call `StoryLoader.load()` and report the result. All validation logic already lives in `story.py`.

### Multiple save slots
Change `SaveManager` to accept a slot index. Add a slot picker to `Display`. Save path becomes `<story_id>.<slot>.save.json`.

### Graph branching (convergent nodes)
No engine changes needed. Just write JSON that points multiple nodes to the same `next` target.
