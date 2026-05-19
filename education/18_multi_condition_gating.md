# 18 — Multi-Condition Gating

**Story:** `stories/examples/18_multi_condition_gating.json`
**Feature:** A single choice gated on two simultaneous conditions — boolean AND integer/string — plus list-membership as OR within one condition.

## What the story does

The "Open the door" choice requires `{ "has_key": true, "clearance": ["red", "blue"] }` — both a boolean flag AND a string-as-list-member check. The player must satisfy both independently. The start node loops on itself so the player can acquire prerequisites in any order.

## Engine code path

**`_check_requires()` iterates all pairs** (`src/engine.py:75`):

```python
def _check_requires(self, requires: dict) -> bool:
    for key, condition in requires.items():
        current = self._state.get(key)
        if isinstance(condition, bool):
            if current != condition: return False
        elif isinstance(condition, int):
            ...
        elif isinstance(condition, str):
            if current != condition: return False
        elif isinstance(condition, list):
            if current not in condition: return False
    return True
```

For `{ "has_key": true, "clearance": ["red", "blue"] }`:
1. `key="has_key"`, `condition=True` → bool branch. If `_state["has_key"]` is not `True`, return `False`.
2. `key="clearance"`, `condition=["red", "blue"]` → list branch. If `_state["clearance"]` is not in the list, return `False`.
3. Both passed → return `True`.

**AND is the only dict-level semantic** — Multiple keys in a single `requires` dict are always AND. There is no OR at the dict level. To express "A or B," either use a list value (for a single flag with multiple acceptable values) or create two separate choices with different `requires`.

**OR via list** — `["red", "blue"]` means "current value of `clearance` must be a member of this list." The check is `current not in condition` using Python's `in` operator. This handles OR within a single flag's acceptable values.

**The self-looping start node** — `start` has choices that all set `next: "start"`. This means the player can return to the same node repeatedly, accumulating flags across visits. The engine supports this natively — `_advance()` sets `visited_start = True` on each visit but that flag is never checked in this story.

**Validation of list values** — `StoryLoader._parse_requires()` (`src/story.py:391`) checks that list values are non-empty and contain only strings. An empty list would make the condition unsatisfiable and is rejected at load time.

## Key references

| Symbol | Location |
|---|---|
| `_check_requires()` full implementation | `src/engine.py:75` |
| List-value validation in `_parse_requires()` | `src/story.py:391` |
| Multi-key AND iteration | `src/engine.py:76` |
| List-membership branch | `src/engine.py:88` |
