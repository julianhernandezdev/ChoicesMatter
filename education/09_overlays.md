# 09 — Overlays

**Story:** `stories/examples/09_overlays.json`
**Feature:** Flavour text that renders outside the story panel, wrapped around the choice list, with optional flag gating.

## What the story does

The `scene` node has two overlays: a conditional `"before"` whisper (only shown if `suspicious` is set) and an unconditional `"after"` echo. The player sets `suspicious` by choosing "Investigate" on the first node.

## Engine code path

**Data model** — `Overlay` is a dataclass in `src/story.py:33`:

```python
@dataclass
class Overlay:
    text: str
    requires: dict = field(default_factory=dict)
    position: str = "after"   # "before" | "after"
    style: str = ""           # named style key
```

Default position is `"after"` (unlike insets which default to `"before"`). Parsed by `StoryLoader._parse_overlays()` (`src/story.py:319`).

**Filtering in `Engine.run()`** (`src/engine.py:45`):

```python
visible_overlays = [o for o in node.overlays if self._check_requires(o.requires)]
before = [o for o in visible_overlays if o.position == "before"]
after  = [o for o in visible_overlays if o.position == "after"]
```

**Rendering — `Display.show_choices()`** (`src/display.py:165`):

```python
for overlay in (before_overlays or []):
    self._render_overlay(overlay)
    if stagger:
        time.sleep(stagger)
# ... choices printed here ...
for overlay in (after_overlays or []):
    self._render_overlay(overlay)
    if stagger:
        time.sleep(stagger)
```

Before-overlays print above the numbered choices; after-overlays print below. When typewriter mode is active, each overlay also staggers in at 60ms intervals alongside the choices.

**`Display._render_overlay()`** (`src/display.py:272`) resolves the style via `_style_cfg()` (see example 10), builds a Rich style string from `color` and modifier flags (`bold`, `italic`, etc.), then prints `prefix + overlay.text` with that style.

**Overlays on ending nodes** — `Engine.run()` passes `overlays=before + after` to `display.show_ending()` when an ending is reached. `Display.show_ending()` (`src/display.py:193`) renders all overlays before the ending panel:

```python
for overlay in (overlays or []):
    self._render_overlay(overlay)
```

This is different from non-ending nodes where overlays split around the choice list. On ending nodes, all overlays — regardless of `position` — appear before the panel.

## Overlay vs. inset

| | Insets | Overlays |
|---|---|---|
| Location | Inside the story panel | Outside the panel |
| Default position | `"before"` | `"after"` |
| Separated by | Dim rule | Nothing |
| On ending nodes | **Silently dropped** | Rendered before the panel |

## Key references

| Symbol | Location |
|---|---|
| `Overlay` dataclass | `src/story.py:33` |
| `_parse_overlays()` | `src/story.py:319` |
| Overlay filtering in `Engine.run()` | `src/engine.py:45` |
| `Display.show_choices()` overlay rendering | `src/display.py:176` |
| `Display.show_ending()` overlay rendering | `src/display.py:201` |
| `Display._render_overlay()` | `src/display.py:272` |
