# 07 — Auto-Visited Flags

**Story:** `stories/examples/07_auto_visited_flags.json`
**Feature:** Opting out of automatic `visited_` flag tracking and managing revisit state manually.

## What the story does

`meta.auto_visited_flags` is `false`. No `visited_*` flags are written automatically. The story uses explicit `sets: { "saw_left": true }` on the choice that enters the left door, then gates the exit with `requires: { "saw_left": true }`.

## Engine code path

**Default behavior (examples 01–06, 08–18)** — `Engine._advance()` (`src/engine.py:119`):

```python
if self.story.auto_visited_flags:
    self._state[f"visited_{self._current_node}"] = True
```

After every navigation, the engine writes `visited_<node_id> = True` into `_state`. This is how example 13 (hub structure) gates the exit without any explicit `sets`.

**Opt-out** — Setting `"auto_visited_flags": false` in `meta` causes `StoryLoader.load()` to set `Story.auto_visited_flags = False` (`src/story.py:228`). The `if self.story.auto_visited_flags` guard in `_advance()` then skips the write entirely.

**Reserved prefix** — When `auto_visited_flags` is `true` (the default), `StoryLoader.load()` validates that no choice's `sets` dict contains a key starting with `"visited_"`:

```python
if auto_visited_flags:
    for node_id, node in nodes.items():
        for choice in node.choices:
            for key in choice.sets:
                if key.startswith("visited_"):
                    raise StoryValidationError(...)
```

This prevents a story author from manually writing `visited_` flags while auto-tracking is on, which would cause confusing overwrites. Setting `auto_visited_flags: false` lifts this restriction entirely and leaves flag management to the story.

**Why you'd opt out** — Auto-visited flags fire on every entry, including re-entries. For a looping structure where you need to distinguish "entered for the first time" from "entered again," auto flags don't help — you need a choice-level `sets` that fires once. Story 07 demonstrates this with `saw_left`.

## Key references

| Symbol | Location |
|---|---|
| `auto_visited_flags` field on `Story` | `src/story.py:73` |
| `auto_visited_flags` parsing | `src/story.py:221` |
| Reserved prefix validation | `src/story.py:230` |
| `visited_` write in `_advance()` | `src/engine.py:119` |
