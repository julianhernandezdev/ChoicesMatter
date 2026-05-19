# 05 — Integer Flags

**Story:** `stories/examples/05_integer_flags.json`
**Feature:** Accumulating an integer with delta strings (`"+1"`) and checking a threshold with `requires`.

## What the story does

Each "Take a token" choice applies `sets: { "tokens": "+1" }`. The gate requires `tokens: 3`, meaning the player needs to collect at least three. There is no cap — the engine accumulates indefinitely.

## Engine code path

**Delta string detection** — `StoryLoader._parse_sets()` stores `"+1"` as the Python string `"+1"`. The string is legal because it matches the `_DELTA_RE = re.compile(r"^[+-]\d+$")` pattern (`src/story.py:16`). Strings starting with `+` or `-` that do NOT match this pattern are rejected at load time.

**`Engine._apply_sets()` delta branch** (`src/engine.py:95`):

```python
if isinstance(value, str) and _DELTA_RE.fullmatch(value):
    delta = int(value)                          # "+1" → 1
    current = self._state.get(key, 0)
    self._state[key] = (
        current if isinstance(current, int) and not isinstance(current, bool) else 0
    ) + delta
```

`self._state.get("tokens", 0)` returns 0 on first access. The `isinstance(current, bool)` guard exists because Python `bool` is a subclass of `int` — without it, `True + 1 = 2` would be silently accepted. If `current` is a bool, the guard resets to 0 before adding the delta.

**`Engine._check_requires()` integer branch** (`src/engine.py:81`):

```python
elif isinstance(condition, int):
    val = current if isinstance(current, int) and not isinstance(current, bool) else 0
    if val < condition:
        return False
```

`requires: { "tokens": 3 }` — `condition` is `3`. The check is `val < 3`, so the choice is hidden until `tokens` reaches 3 or more. This is a **threshold**, not an exact match — `tokens = 5` still passes.

**No upper bound in the engine** — The engine does not enforce a maximum. The story is responsible for hiding the "+1" choices once they are no longer meaningful, or accepting that the counter can exceed the threshold.

## Key references

| Symbol | Location |
|---|---|
| `_DELTA_RE` pattern | `src/engine.py:10`, `src/story.py:16` |
| `_parse_sets()` delta validation | `src/story.py:417` |
| `_apply_sets()` delta branch | `src/engine.py:95` |
| `_check_requires()` int threshold | `src/engine.py:81` |
