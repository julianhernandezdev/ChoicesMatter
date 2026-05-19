# 11 — Choice Colors

**Story:** `stories/examples/11_choice_colors.json`
**Feature:** Overriding the number color on individual choices and at the node level.

## What the story does

`default_colors` demonstrates per-choice `color` overrides against the default cyan. `node_level_color` sets `choice_number_color: "yellow"` as a node-level fallback and shows a per-choice `"magenta"` override on top of it.

## Engine code path

**Data model** — `Choice.color` is `str | None` (`src/story.py:28`). `Node.choice_number_color` is also `str | None` (`src/story.py:57`). Both default to `None` when absent from JSON.

**Validation** — `StoryLoader._parse_choices()` checks that `color`, if present, is a non-empty string (`src/story.py:297`). `StoryLoader.load()` does the same for `choice_number_color` (`src/story.py:173`). Neither validates that the value is a valid Rich color name — that responsibility is left to the display layer at render time.

**Resolution in `Display.show_choices()`** (`src/display.py:180`):

```python
for i, choice in enumerate(choices, start=1):
    num_color = choice.color or choice_number_color or "cyan"
    ...
    self.console.print(f"  [bold {num_color}]{i}.[/bold {num_color}] {label}")
```

Priority chain: `choice.color` → node's `choice_number_color` → `"cyan"`.

`choice_number_color` is passed from the engine to `display.show_choices()` at the call site in `Engine.run()`:

```python
self.display.show_choices(visible, before, after, node.choice_number_color)
```

The engine does not interpret the color string — it passes it through unchanged. The color string is embedded directly into Rich markup, so any valid Rich color name or hex value works.

**Only the number is colored** — The choice label text always renders in the default terminal color. Only the number prefix (`1.`, `2.`, etc.) is affected.

## Key references

| Symbol | Location |
|---|---|
| `Choice.color` field | `src/story.py:28` |
| `Node.choice_number_color` field | `src/story.py:57` |
| `color` validation in `_parse_choices()` | `src/story.py:293` |
| `choice_number_color` validation | `src/story.py:169` |
| `show_choices()` call with color | `src/engine.py:64` |
| Color resolution in `Display.show_choices()` | `src/display.py:181` |
