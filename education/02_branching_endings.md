# 02 — Branching Endings

**Story:** `stories/examples/02_branching_endings.json`
**Feature:** Three `ending_type` values — `good`, `bad`, `neutral` — and how the engine maps them to display colors.

## What the story does

One fork node with three choices, each leading directly to a different ending node. The only difference between the endings is `ending_type`.

## Engine code path

**Validation** — `StoryLoader.load()` checks `ending_type` against `_ENDING_TYPES = {"good", "bad", "neutral"}` (`src/story.py:14`). Any other value raises `StoryValidationError`. The default when `ending_type` is omitted is `"neutral"` (`src/story.py:154`).

**At the ending node** — `Engine.run()` hits `node.is_ending` and calls:

```python
self.display.show_ending(node.text, node.ending_type, overlays=before + after)
```

**`Display.show_ending()`** (`src/display.py:193`) maps `ending_type` to a Rich color string via `_ENDING_COLORS`:

```python
_ENDING_COLORS = {
    "good":    "bright_green",
    "bad":     "bright_red",
    "neutral": "bright_yellow",
}
color = _ENDING_COLORS.get(ending_type, "bright_yellow")
```

The fallback `"bright_yellow"` means an unknown type renders as neutral — but this can't happen in practice because validation already rejected it.

The `color` string is used for both the panel's `border_style` and the title label (`— GOOD ENDING —`), so panel border and header change together.

## Key references

| Symbol | Location |
|---|---|
| `_ENDING_TYPES` constant | `src/story.py:14` |
| `ending_type` default | `src/story.py:154` |
| `_ENDING_COLORS` map | `src/display.py:37` |
| `Display.show_ending()` | `src/display.py:193` |
