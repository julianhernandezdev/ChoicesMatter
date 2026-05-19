<p align="center">
  <img src="assets/banner.png" alt="Choices Matter" width="100%">
</p>

# Choices Matter

**Every choice leaves a mark. Every ending remembers.**

A Python CLI text adventure engine with a browser play mode. Stories are fully data-driven — all content lives in `.json` files under `/stories/`. Drop a file in, launch the engine, play.

## Play in Browser
<p align="center">
  <a href="https://julianhernandezdev.github.io/ChoicesMatter/"><strong>Play Now</strong></a>
</p>

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

> **Need help?** [ChoicesMatterGPT](https://chatgpt.com/g/g-6a07ba3fe91881918378538ca6cbfe8f-choicesmattergpt) is a custom GPT trained on this format — describe your story and it generates valid JSON.

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

`id` is used as the save file key. `start_node` must match a key in `nodes`. `est_time` is optional — if omitted, the engine auto-computes it from word count. If supplied, it's shown as-is in the story picker. `warnings` is optional — a list of strings shown in a yellow warning panel before launch; affected stories are marked `[!]` in the picker. `auto_visited_flags` defaults to `true` — see the Flags section below.

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

Choices support `requires` and `sets` to gate and track state. State values can be **booleans**, **integers**, or **strings**.

**`sets`** — applies values to the player's state when this choice is taken:

```json
{ "sets": { "has_key": true } }           // boolean flag
{ "sets": { "trust": 3 } }                // absolute integer
{ "sets": { "trust": "+1" } }             // delta — adds 1 (unset key defaults to 0)
{ "sets": { "trust": "-2" } }             // delta — subtracts 2
{ "sets": { "faction": "red" } }          // string assignment
```

**`requires`** — hides the choice entirely if conditions are not met:

```json
{ "requires": { "has_key": true } }                    // boolean exact match
{ "requires": { "trust": 3 } }                         // integer threshold (trust ≥ 3)
{ "requires": { "faction": "red" } }                   // string exact match
{ "requires": { "faction": ["red", "blue"] } }         // string membership (any of)
```

Multiple conditions in one `requires` dict are ANDed — all must pass for the choice to appear.

State accumulates across the run and is persisted in the save file.

**Auto-visited flags:** The engine automatically sets `visited_<node_id>: true` each time a node is entered. Use these in `requires` to create revisit-aware content with no `sets` boilerplate:

```json
{
  "label": "You remember this room. Check the panel again.",
  "next": "panel_check",
  "requires": { "visited_generator_room": true }
}
```

The `visited_` prefix is reserved — manually setting it via `sets` raises a validation error. Set `"auto_visited_flags": false` in `meta` to manage the namespace yourself.

### Obfuscated Choices

Choices with `"obfuscated": true` render as `[REDACTED ██████]` in the choice list. The player can still select the option — they just don't know what it is until after. Use it for irreversible decisions or choices the character makes without fully understanding what they're doing:

```json
{ "label": "Pull the lever", "next": "consequences", "obfuscated": true }
```

### Choice Number Color

Two-level color system for choice number prefixes. Set `"choice_number_color"` on a node as a fallback for all its choices, then override per-choice with `"color"`:

```json
"platform_7": {
  "choice_number_color": "bright_red",
  "choices": [
    { "label": "Run.", "next": "escape", "color": "green" },
    { "label": "Stay.", "next": "caught" }
  ]
}
```

Use color to signal emotional register, not decoration. `"bright_red"` for danger, `"green"` for safety, `"yellow"` for uncertainty. Both accept any `rich` color name or hex (e.g. `"#ffaa00"`).

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

### Conditional Inline Text

Write conditional spans directly inside any `text` field — node text, inset text, or overlay text — without branching to a separate node:

```
{flag?shown when true|shown when false}
```

The false branch is optional; omitting it collapses to nothing when the flag is unset:

```json
"lobby": {
  "text": "The receptionist {is_staff?gives you a professional nod.|watches you carefully.}",
  "insets": [
    { "text": "{is_staff?STAFF ACCESS GRANTED}", "position": "before", "style": "system" }
  ],
  "choices": [...]
}
```

Truthiness mirrors the flag system: `true`, integer ≥ 1, and non-empty strings resolve to the true branch; `false`, `0`, `""`, and missing flags resolve to the false branch. Flag names must match `\w+` (letters, digits, underscores).

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

Stories can be organised into subfolders inside `/stories/`. The picker shows each subfolder as a named folder entry with a story count; selecting it drills into a sub-screen. Root stories always appear alongside folders.

## Validating a Story

```bash
python scripts/validate_story.py stories/your_story.json
```

Checks schema (via the engine's own loader), reachability (BFS from `start_node`), and dead-ends (reachable nodes with empty `choices` and no `is_ending`). Accepts multiple files:

```bash
python scripts/validate_story.py stories/horror/*.json stories/sci-fi/*.json
```

Output: `WARN` for unreachable nodes, `ERROR` for dead-ends and schema failures. Exit codes: `0` = clean, `1` = errors found, `2` = no arguments.

## Project Structure

```
main.py                    Entry point — story picker, wires components
src/engine.py              Game loop, navigation, save triggers, ending detection
src/story.py               Data models (Story, Node, Choice, Overlay, Inset), loader, validation
src/save.py                Persistent save state — read/write/delete per story
src/gallery.py             Ending gallery — tracks found endings across runs
src/display.py             All rich rendering — nothing else imports rich
src/config.py              Loads settings.json, merges with defaults
scripts/validate_story.py  Story validator — schema, reachability, dead-end detection
scripts/sync_stories.py    Regenerates web/stories.json manifest from stories/
index.html                 GitHub Pages entrypoint for browser play
web/app.js                 Browser play mode — rendering, screen state, UI logic
web/engine.js              Browser engine — pure game logic (no DOM)
web/storage.js             Browser storage — save/gallery via localStorage
web/typewriter.js          Browser typewriter — animation and settings
web/style.css              Browser play mode styling
web/stories.json           Static manifest of bundled stories (auto-generated)

/stories             Drop .json story files here — auto-discovered at startup (subfolders supported)
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
