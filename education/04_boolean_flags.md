# 04 — Boolean Flags

**Story:** `stories/examples/04_boolean_flags.json`
**Feature:** Writing a boolean to state with `sets` and gating a choice on it with `requires`.

## What the story does

Picking up the key sets `has_key: true`. The "Unlock it" choice at the chest requires `has_key: true` — it is hidden entirely if the flag is absent or false.

## Engine code path

**`Engine._state`** (`src/engine.py:27`) is a plain dict (`dict[str, bool | int | str]`) that accumulates all flag writes for the current run. It starts empty.

**Writing a flag — `Engine._apply_sets()`** (`src/engine.py:93`):

```python
def _apply_sets(self, sets: dict) -> None:
    for key, value in sets.items():
        if isinstance(value, str) and _DELTA_RE.fullmatch(value):
            # delta string — handled for integers, see example 05
            ...
        else:
            self._state[key] = value  # direct assignment for bool/int/str
```

`sets: { "has_key": true }` is parsed by `StoryLoader._parse_sets()` as Python `True` (JSON `true` → Python `bool`). `_apply_sets()` stores it directly: `self._state["has_key"] = True`.

`_apply_sets()` is called at the start of `Engine._advance()`, before the node changes (`src/engine.py:116`).

**Checking a flag — `Engine._check_requires()`** (`src/engine.py:75`):

```python
if isinstance(condition, bool):
    if current != condition:
        return False
```

For `requires: { "has_key": true }`, `condition` is `True`. `current = self._state.get("has_key")` — if the flag was never set, `current` is `None`, which `!= True`, so the check fails and the choice is hidden.

**Where hiding happens** — `Engine.run()` builds the `visible` list before rendering:

```python
visible = [c for c in node.choices if self._check_requires(c.requires)]
```

Choices that fail `_check_requires()` are excluded from `visible` entirely. `display.show_choices(visible, ...)` only receives the filtered list — the engine never passes hidden choices to the display layer.

## Key references

| Symbol | Location |
|---|---|
| `_state` field | `src/engine.py:27` |
| `_apply_sets()` | `src/engine.py:93` |
| `_check_requires()` bool branch | `src/engine.py:78` |
| `visible` list filtering | `src/engine.py:43` |
| `_advance()` applies sets | `src/engine.py:116` |
