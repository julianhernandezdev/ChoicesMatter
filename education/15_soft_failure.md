# 15 — Soft Failure

**Story:** `stories/examples/15_soft_failure.json`
**Feature:** A gated choice that is completely invisible until its condition is met — the player is never told it exists.

## What the story does

The `vault` node has three choices: enter the combination (requires `has_combination`), search the office, or force it. The "Enter the combination" choice is invisible until the player finds the sticky note in `office` and sets the flag. The player who goes straight to "Force it" never sees that a better option existed.

## Engine code path

**Hard hide, not grayout** — The engine has no concept of a grayed-out or disabled choice. `_check_requires()` returns `True` or `False`. Choices that return `False` are excluded from `visible` before the display layer sees them:

```python
visible = [c for c in node.choices if self._check_requires(c.requires)]
```

`Display.show_choices(visible, ...)` only receives the filtered list. It prints choices `1.`, `2.`, `3.` for whatever is in that list — there is no placeholder for the hidden choice, no gap in the numbering, and no message indicating something is missing.

**Renumbering** — Because `visible` is rebuilt each render, choice numbers shift when a flag changes. Before finding the combination: the vault shows choices `1.` (search) and `2.` (force). After: it shows `1.` (enter combination), `2.` (search), `3.` (force). The order follows the JSON order of choices; `requires` filtering does not reorder, only removes.

**State persists across nodes** — The player navigates `vault → office → vault` by having choices `next: "office"` and `next: "vault"`. `_advance()` writes and persists state on each navigation. When the player returns to `vault`, `self._state["has_combination"]` is still `True`, so the gated choice now passes.

**Design implication** — Because hidden choices are completely invisible, the player cannot distinguish "this choice requires something I haven't done" from "this choice doesn't exist in this story." This is a deliberate design choice: the soft failure pattern creates natural puzzle solving without ever communicating that a puzzle exists.

## Key references

| Symbol | Location |
|---|---|
| `visible` list filtering | `src/engine.py:43` |
| `_check_requires()` | `src/engine.py:75` |
| Display receives only filtered choices | `src/engine.py:64` |
