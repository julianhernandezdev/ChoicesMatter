# 06 — String Flags

**Story:** `stories/examples/06_string_flags.json`
**Feature:** Storing a string value in state and checking it with exact-match and list-membership `requires`.

## What the story does

The player picks a faction — Red, Blue, or None. `sets: { "faction": "red" }` stores the string. The checkpoint node demonstrates two `requires` variants: exact string match and list membership (OR semantics).

## Engine code path

**Writing — `Engine._apply_sets()`** (`src/engine.py:99`):

For non-delta strings, the direct assignment path runs: `self._state["faction"] = "red"`. Plain strings that happen to start with `+` or `-` but don't match `_DELTA_RE` are rejected at load time by `StoryLoader._parse_sets()`, so the engine never sees an ambiguous case.

**Checking — `Engine._check_requires()` string branch** (`src/engine.py:85`):

```python
elif isinstance(condition, str):
    if current != condition:
        return False
```

`requires: { "faction": "red" }` — exact equality. `"blue" != "red"` → hidden.

**List membership branch** (`src/engine.py:88`):

```python
elif isinstance(condition, list):
    if current not in condition:
        return False
```

`requires: { "faction": ["red", "blue"] }` — `current not in ["red", "blue"]` fails for `"none"`, passes for either faction. This is OR semantics: any member of the list satisfies the condition.

**Validation** — `StoryLoader._parse_requires()` (`src/story.py:374`) ensures list values are non-empty and contain only strings. An empty list `[]` is rejected — it would be an unsatisfiable condition.

**Type precedence in `_check_requires()`** — The conditions are checked as `isinstance(condition, bool)` first, then `int`, then `str`, then `list`. JSON `true`/`false` land as Python `bool`, and since `bool` is a subclass of `int`, the `bool` check must come first to prevent `True` being treated as the integer `1`.

## Key references

| Symbol | Location |
|---|---|
| `_apply_sets()` string assignment | `src/engine.py:99` |
| `_check_requires()` string branch | `src/engine.py:85` |
| `_check_requires()` list branch | `src/engine.py:88` |
| `_parse_requires()` list validation | `src/story.py:391` |
