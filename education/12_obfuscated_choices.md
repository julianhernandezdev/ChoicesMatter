# 12 — Obfuscated Choices

**Story:** `stories/examples/12_obfuscated_choices.json`
**Feature:** Hiding a choice's label behind `[REDACTED]` while keeping it selectable.

## What the story does

Three choices. The middle one has `"obfuscated": true`. The player sees a redacted placeholder instead of the real label text and can still select it by number — but never learns what the label said.

## Engine code path

**Data model** — `Choice.obfuscated: bool = False` (`src/story.py:29`). Parsed by `StoryLoader._parse_choices()` (`src/story.py:301`), which validates the value is exactly `true` or `false` (not a truthy string).

**Rendering in `Display.show_choices()`** (`src/display.py:182`):

```python
label = "[dim]████ ██████ ████ ████████[/dim]" if choice.obfuscated else choice.label
self.console.print(f"  [bold {num_color}]{i}.[/bold {num_color}] {label}")
```

When `obfuscated` is `True`, the label is replaced with a fixed block-character string rendered dim. The number prefix is printed normally — the choice is fully selectable.

**The real label is never exposed** — The display layer never prints `choice.label` for an obfuscated choice. No engine state records what the label said. A player who selects the obfuscated option is navigated to `choice.next` exactly as if they had selected any other choice.

**Obfuscated choices still participate in filtering** — `_check_requires()` evaluates `choice.requires` normally for obfuscated choices. An obfuscated choice with an unmet `requires` is excluded from `visible` entirely — the player never sees a redacted slot for it. This allows obfuscated choices to be conditionally visible.

**No engine logic changes for obfuscated choices** — The obfuscated flag is purely presentational. `_advance()`, `_apply_sets()`, and the rest of the engine treat the choice identically to any other.

## Key references

| Symbol | Location |
|---|---|
| `Choice.obfuscated` field | `src/story.py:29` |
| `obfuscated` parsing and validation | `src/story.py:301` |
| Label substitution in `Display.show_choices()` | `src/display.py:182` |
