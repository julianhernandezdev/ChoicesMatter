# Choices Matter

```text
   ___ _          _              __  __      _   _
  / __| |_  ___(_)__ ___ ___  |  \/  |__ _| |_| |_ ___ _ _
 | (__| ' \/ _ \ / _/ -_|_-< | |\/| / _` | _| _/ -_) '_|
  \___|_||_\___/_\__\___/__/ |_|  |_\__,_|\__|\_\_\___|_|
```

*every choice leaves a mark*

A Python CLI text adventure engine. Stories are fully data-driven — all content lives in `.json` files under `/stories/`. Drop a file in, launch the engine, play.

## Requirements

- Python 3.12+
- `rich` (terminal rendering)
- `pytest` (tests only)

```bash
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

The engine discovers all `.json` files in `/stories/`, presents a numbered picker, and runs whichever story you select. Progress autosaves after every choice. Saves are per-story and deleted automatically when you reach an ending.

## Writing a Story

Stories are JSON files with two top-level keys: `meta` and `nodes`.

### `meta`

```json
{
  "meta": {
    "id": "your_story_id",
    "title": "Display Title",
    "version": "1.0",
    "author": "Your Name",
    "start_node": "intro"
  }
}
```

`id` is used as the save file key. `start_node` must match a key in `nodes`.

### Nodes

Each node is a keyed object:

```json
"intro": {
  "text": "You wake up in a dim room.",
  "choices": [
    { "label": "Try the door", "next": "try_door" },
    { "label": "Search the desk", "next": "search_desk" }
  ]
}
```

**Ending nodes** — use `is_ending: true` and set `ending_type` to `good`, `bad`, or `neutral`:

```json
"escaped": {
  "text": "You slip out into the night. You made it.",
  "choices": [],
  "is_ending": true,
  "ending_type": "good"
}
```

An empty `choices` array is always treated as an ending, even without `is_ending: true`.

### Conditional Choices (Flags)

Choices support `requires` and `sets` to gate content on boolean flags the player has accumulated:

```json
"choices": [
  {
    "label": "Take the key",
    "next": "use_key",
    "sets": { "has_key": true }
  },
  {
    "label": "Use the silver watch",
    "next": "bribed_escape",
    "requires": { "logbook_read": true }
  }
]
```

- `sets` — applies flags to the player's state when this choice is taken
- `requires` — hides the choice entirely if the player doesn't have the matching flags

Flags accumulate across the run and are persisted in the save file.

### Conditional Overlays

Nodes can have `overlays` — whispered lines of text that appear conditionally before or after the choice list, based on what the player knows:

```json
"use_key": {
  "text": "The key fits. The lock turns.",
  "overlays": [
    {
      "text": "Harrow's words surface: 'The guard has a weakness for silver.'",
      "requires": { "logbook_read": true },
      "position": "before"
    }
  ],
  "choices": [...]
}
```

- `position: "before"` — appears above the choice list (prior knowledge framing the decision)
- `position: "after"` — appears below the choice list (a dawning realization)
- `requires` — same flag system as choices; omit to show unconditionally
- Multiple overlays can stack; `before` and `after` accumulate independently

On ending nodes, all overlays appear before the ending panel.

## Customizing Overlay Style

Copy `settings.example.json` to `settings.json` (gitignored, per-user) and edit:

```json
{
  "overlay": {
    "color": "cyan",
    "dim": true,
    "italic": true,
    "bold": false,
    "underline": false,
    "strike": false,
    "prefix": "✦ "
  }
}
```

Missing or malformed `settings.json` silently falls back to the defaults above.

## Adding a Story

Drop any `.json` file into `/stories/`. No code changes needed. Malformed stories show as `-ERROR` in the picker and can be selected to see the validation message.

## Project Structure

```
main.py              Entry point — story picker, wires components
engine.py            Game loop, navigation, save triggers, ending detection
story.py             Data models (Story, Node, Choice, Overlay), loader, validation
save.py              Persistent save state — read/write/delete per story
display.py           All rich rendering — nothing else imports rich
config.py            Loads settings.json, merges with defaults

/stories             Drop .json story files here — auto-discovered at startup
/saves               Auto-generated — one .save.json per story
settings.example.json  Committed overlay style template
```

## Running Tests

```bash
pytest
```
