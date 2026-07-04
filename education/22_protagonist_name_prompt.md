# 22 — Protagonist Name Prompt

**Story:** `stories/examples/22_protagonist_name_prompt.json`
**Feature:** An optional pre-game name input screen. The player's name is stored as the reserved `player_name` flag and available as `{player_name}` throughout the story via Variable Text Substitution.

## What the story does

The story declares `name_prompt` and `name_default` in its `meta`. Before the first node loads, the player is asked for their name. That name is then woven into every node: the innkeeper greets them by name, the room inset shows their name on the reservation, the key is engraved with it, and both endings use it — including one ending where the name appears as a standalone overlay text before the ending panel.

## Meta fields

```json
{
  "meta": {
    "name_prompt": "What is your name?",
    "name_default": "the stranger"
  }
}
```

| Field | Required | Notes |
|---|---|---|
| `name_prompt` | No | Non-empty string. Triggers the name prompt screen. The string is shown as the prompt label. |
| `name_default` | No | Non-empty string. Used when the player submits empty input and no settings name is available. Requires `name_prompt` to also be set. |

## Launch flow

The prompt fires **after content warnings and before the first node**, only for new games. On save resume, `player_name` is already in the saved state — the prompt is skipped and the saved name is used directly.

### Fallback priority chain

| Condition | `player_name` value used |
|---|---|
| Player submits a non-empty name | Entered name |
| Player submits empty + story has `name_default` | `meta.name_default` |
| Player submits empty + no story default + settings name is non-empty | Settings `player_name` value |
| Player submits empty + no fallback available | Prompt rejected; error shown; return to picker |
| Player presses Q | Return to picker; story not launched |

The input is pre-filled with the settings `player_name` value (default `"Felix"`). Because the default is a non-empty string, the rejection path is only reached if the player has actively cleared their saved name in Settings.

## `{player_name}` in story text

`{player_name}` is a standard Variable Text Substitution placeholder (see example 21). No special syntax — it resolves the same way as any other `{key}`.

```json
"text": "The innkeeper calls you {player_name}."
```

Works in: node text, insets, overlays. Does **not** work in choice `label` fields — those are excluded from VTS.

## Using `{player_name}` without `name_prompt`

`player_name` is always seeded from settings before the engine starts, even for stories that don't declare `name_prompt`. A story can use `{player_name}` with no prompt — the player's globally saved name (default `"Felix"`) appears automatically.

## Engine code path

**`initial_state` seeding in `main.py`**:

```python
settings_name = load_settings().get("player_name", "Felix")
initial_state: dict[str, bool | int | str] = {"player_name": settings_name}

if story.name_prompt and not save_manager.has_save(story.id):
    name = display.prompt_protagonist_name(story.name_prompt, prefill=settings_name)
    if name is None:
        return                          # Q → back to picker
    if not name:
        name = story.name_default or settings_name or ""
        if not name:
            display.show_name_required()
            return
    initial_state = {"player_name": name}

Engine(story, save_manager, display, gallery_manager, initial_state=initial_state).run()
```

**`Engine.__init__` `initial_state` parameter** (`src/engine.py:23`):

```python
def __init__(self, ..., initial_state: dict[str, bool | int | str] | None = None) -> None:
    self._initial_state = dict(initial_state) if initial_state else {}
```

**`_resolve_start()` and `_reset()`** — both seed `_state` from `_initial_state`:

```python
self._state = dict(self._initial_state)
```

This means `player_name` is present from the very first node, and survives play-again resets without re-prompting.

**`Story.name_prompt` / `Story.name_default`** (`src/story.py:74–75`) — parsed by `StoryLoader.load()`. Validation rules:
- `name_prompt` if present: must be a non-empty string
- `name_default` if present: must be a non-empty string AND `name_prompt` must also be set

## Display layer

`Display.prompt_protagonist_name(prompt_text, prefill)` renders the prompt label (from `meta.name_prompt`) and a pre-filled text input. Returns the entered string (including empty string) or `None` on Q.

The web player has `renderNamePrompt()` and `renderAccessibleNamePrompt()` in `web/app.js`. The accessible renderer adds `reader-mode` class and focuses the input immediately after rendering (no `startTypewriter` call).

## Settings

`Settings → Player name` (row 9 in both CLI and web settings screens) stores a persistent default under the top-level `"player_name"` key in `settings.json`. This is the first **client variable** — a player-provided value that persists across all stories.

## Key references

| Symbol | Location |
|---|---|
| `Story.name_prompt` / `name_default` fields | `src/story.py:74–75` |
| Validation in `StoryLoader.load()` | `src/story.py:243–280` |
| `_launch_story()` wiring | `main.py` |
| `Engine.__init__` `initial_state` param | `src/engine.py:23` |
| `_resolve_start()` / `_reset()` seeding | `src/engine.py` |
| `Display.prompt_protagonist_name()` | `src/display.py` |
| `renderNamePrompt()` / `renderAccessibleNamePrompt()` | `web/app.js` |
| `player_name` in `TYPEWRITER_DEFAULTS` | `web/typewriter.js` |
| `createRun` `initialState` param | `web/engine.js` |
| Unit tests | `tests/test_story.py`, `tests/test_config.py`, `tests/test_engine.py`, `tests/test_display.py` |
| JS parity tests | `tests/test_web_engine.py` |
