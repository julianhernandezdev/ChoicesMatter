<p align="center">
  <img src="assets/banner.png" alt="Choices Matter" width="100%">
</p>

# Choices Matter

**Every choice leaves a mark. Every ending remembers.**

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

The engine discovers all `.json` files in `/stories/`, presents a numbered picker with node count, endings found, and estimated read time, and runs whichever story you select. Stories with an active save show a `● RESUME` badge. Progress autosaves after every choice. Saves are per-story and deleted automatically when you reach an ending.

At the picker prompt:
- **Number** — select a story
- **Q** — quit
- **C** — clear all save data and ending progress (with confirmation)
- **T** — toggle typewriter mode on/off for the session
- **S** — open settings (typewriter speed and punctuation pauses; writes to `settings.json`)

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
    "start_node": "intro",
    "est_time": "15–25 min"
  }
}
```

`id` is used as the save file key. `start_node` must match a key in `nodes`. `est_time` is optional — if omitted, the engine auto-computes it from word count. If supplied, it's shown as-is in the story picker.

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

### Insets

Nodes can have `insets` — styled lines rendered **inside** the story panel, above or below the main text, separated by a dim rule. Use them for timestamps, log entries, documents, or any in-world text that belongs inside the scene rather than around it:

```json
"intro": {
  "insets": [
    { "text": "Platform 3  —  23:58", "position": "before", "style": "system" }
  ],
  "text": "You've missed the last train...",
  "choices": [...]
}
```

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Line of text shown inside the panel |
| `position` | No | `"before"` (default) or `"after"` the main text |
| `style` | No | Named style key — see below; `""` renders as dim italic |
| `requires` | No | Same flag dict as choices — hides inset if not matched |

### Conditional Overlays

Nodes can have `overlays` — flavour lines that appear conditionally before or after the choice list, based on what the player knows:

```json
"use_key": {
  "text": "The key fits. The lock turns.",
  "overlays": [
    {
      "text": "Harrow's words surface: 'The guard has a weakness for silver.'",
      "requires": { "logbook_read": true },
      "position": "before",
      "style": "echo"
    }
  ],
  "choices": [...]
}
```

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Whispered line of text |
| `position` | No | `"before"` (above choices) or `"after"` (below choices, default) |
| `style` | No | Named style key — see below; `""` uses the default overlay style |
| `requires` | No | Same flag system as choices; omit to show unconditionally |

Multiple overlays can stack; `before` and `after` accumulate independently. On ending nodes, all overlays appear before the ending panel.

## Named Styles

Both overlays and insets accept a `style` field. The built-in named styles are:

| Name | Color | Look | Prefix | Use for |
|---|---|---|---|---|
| `whisper` | cyan | dim italic | `✦ ` | Quiet asides, intimate atmosphere |
| `echo` | blue | dim italic | `~ ` | Distant voices, remembered words, intrusive thoughts |
| `warning` | yellow | bold | `⚠ ` | Danger signals, urgent realisations |
| `memory` | magenta | dim italic | `◈ ` | Flashbacks, implanted memories, recollections |
| `system` | white | dim | _(none)_ | Timestamps, logs, documents, clinical text |

### Customizing Styles

Copy `settings.example.json` to `settings.json` (gitignored, per-user). Override any built-in style or add your own:

```json
{
  "styles": {
    "warning": { "color": "red" },
    "classified": { "color": "green", "dim": true, "italic": false, "bold": false, "underline": false, "strike": false, "prefix": "[REDACTED] " }
  },
  "overlay": {
    "color": "cyan",
    "dim": true,
    "italic": true,
    "prefix": "✦ "
  }
}
```

`overlay` sets the default style for overlays with no `style` key. Missing or malformed `settings.json` silently falls back to built-in defaults.

## Typewriter Mode

Enable character-by-character text streaming in `settings.json`:

```json
{
  "typewriter": {
    "enabled": true,
    "delay_ms": 35,
    "punctuation_pauses": {
      ".": 550,
      "!": 250,
      "?": 350,
      "…": 700,
      "—": 600
    }
  }
}
```

- `delay_ms` — base delay per character in milliseconds
- `punctuation_pauses` — extra pause (ms) after specific characters; set any to `0` to remove it
- Press any key mid-animation to skip to the full text
- After prose finishes, choices stagger in at 60ms each after a short breath
- Toggle on/off at the story picker with **T** without editing `settings.json`

## Adding a Story

Drop any `.json` file into `/stories/`. No code changes needed. Malformed stories show as `-ERROR` in the picker and can be selected to see the validation message.

## Project Structure

```
main.py              Entry point — story picker, wires components
engine.py            Game loop, navigation, save triggers, ending detection
story.py             Data models (Story, Node, Choice, Overlay, Inset), loader, validation
save.py              Persistent save state — read/write/delete per story
gallery.py           Ending gallery — tracks found endings across runs
display.py           All rich rendering — nothing else imports rich
config.py            Loads settings.json, merges with defaults

/stories             Drop .json story files here — auto-discovered at startup
/saves               Auto-generated — one .save.json + one .gallery.json per story
settings.example.json  Committed template (typewriter, overlay, named styles)
```

## Running Tests

```bash
pytest
```

## Contributing

Suggestions, bug reports, and code contributions are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full guide.

The short version:
- **Feature idea** → open a GitHub Issue with the `suggestion` label, or PR [`SUGGESTIONS.md`](SUGGESTIONS.md) directly using the template at the bottom of that file
- **Bug** → open a GitHub Issue with steps to reproduce
- **Code PR** → check that the feature is accepted in `SUGGESTIONS.md` first, include tests, keep it focused
