# 01 — Minimal Story

**Story:** `stories/examples/01_minimal_story.json`
**Feature:** The minimum viable story — two nodes, one choice, one ending.

## What the story does

Two nodes. `start` has one choice that leads to `end`. `end` has `is_ending: true` and an empty `choices` array. Nothing else.

## Engine code path

**Loading** — `StoryLoader.load()` in `src/story.py` reads the JSON, validates `meta` fields via `_required_string()`, then iterates `nodes`. For each node it calls `_parse_choices()`, which validates every choice has a `label` and `next`. After parsing all nodes, it does a second pass to verify every `choice.next` references an existing node ID. If anything is missing, `StoryValidationError` is raised immediately.

**Starting** — `Engine.__init__()` (`src/engine.py:13`) sets `self._current_node = story.start_node`, `self._history = []`, and `self._state = {}`. The engine does not touch the save manager yet.

**`Engine.run()` loop** (`src/engine.py:34`) — On each iteration:
1. `self.story.get_node(self._current_node)` fetches the current `Node` dataclass.
2. `visible = [c for c in node.choices if self._check_requires(c.requires)]` — with no `requires`, all choices pass and `visible` equals the full list.
3. The ending check: `if node.is_ending or not visible` — `is_ending: true` short-circuits here. An empty `choices` array also triggers it (the `not visible` branch).
4. `display.show_ending(node.text, node.ending_type, overlays=[])` renders the ending panel.
5. `gallery_manager.record_ending()` persists the found ending; `save_manager.delete()` removes the active save.
6. `display.prompt_play_again()` — Y resets via `_reset()` and continues the loop; N returns from `run()`.

**Why `not visible` also triggers ending** — The engine treats a node with zero visible choices as an implicit ending regardless of `is_ending`. This means `is_ending: true` is only needed to set `ending_type`; an empty `choices` array is sufficient to stop the loop.

## Key references

| Symbol | Location |
|---|---|
| `StoryLoader.load()` | `src/story.py:102` |
| `StoryLoader._parse_choices()` | `src/story.py:277` |
| `Engine.run()` loop | `src/engine.py:34` |
| Ending check | `src/engine.py:53` |
| `Display.show_ending()` | `src/display.py:193` |
