# 16 — Stateful Endings

**Story:** `stories/examples/16_stateful_endings.json`
**Feature:** Multiple paths converging on one ending node, with conditional content reflecting how the player arrived.

## What the story does

`start` has three choices, each setting `path` to a different string, all routing to `"next": "end"`. The `end` node is an ending with three conditional insets, each requiring a different value of `path`.

## Engine code path

**Convergent ending** — Works identically to the convergent non-ending node in example 14. The engine navigates to `"end"` by node ID; state already contains the `path` flag.

**The inset drop** — `Engine.run()` computes `before_insets` and `after_insets` unconditionally, but on ending nodes it calls `display.show_ending()` instead of `display.show_node()`. `show_ending()` does not accept insets:

```python
if node.is_ending or not visible:
    self.display.show_ending(node.text, node.ending_type, overlays=before + after)
```

The `before_insets` and `after_insets` variables are computed and then **not used**. The conditional insets in this example story do not actually render in the CLI engine.

**To get conditional content on an ending node, use overlays** — `show_ending()` renders all overlays before the ending panel:

```python
for overlay in (overlays or []):
    self._render_overlay(overlay)
```

The corrected version of this story would use `overlays` with `position: "before"` instead of `insets`. The engine merges all visible overlays (regardless of their `position` value) and passes them as a single flat list.

**Why the example uses insets despite the drop** — The story demonstrates the design pattern (convergent ending with per-path content), but insets were chosen instead of overlays. The story works as a conceptual example, but a dev implementing this pattern should use overlays on ending nodes.

## Key references

| Symbol | Location |
|---|---|
| Ending check bypasses insets | `src/engine.py:53` |
| `show_ending()` receives overlays, not insets | `src/engine.py:54` |
| `Display.show_ending()` overlay rendering | `src/display.py:201` |
| Correct pattern: overlays on ending nodes | See example 09 |
