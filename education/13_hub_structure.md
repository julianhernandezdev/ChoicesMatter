# 13 — Hub Structure

**Story:** `stories/examples/13_hub_structure.json`
**Feature:** A revisitable hub node where an exit unlocks only after the player has visited all branches — using auto-generated `visited_` flags.

## What the story does

`hub` has three choices: Room A, Room B, and an exit requiring `visited_room_a: true` AND `visited_room_b: true`. Rooms loop back to the hub. No explicit `sets` anywhere — the engine tracks visits automatically.

## Engine code path

**Auto-visited flag write** — Every time the player navigates to a node, `Engine._advance()` fires (`src/engine.py:115`):

```python
def _advance(self, choice: Choice) -> None:
    self._apply_sets(choice.sets)
    self._history.append(self._current_node)
    self._current_node = choice.next
    if self.story.auto_visited_flags:
        self._state[f"visited_{self._current_node}"] = True
    ...
```

After `self._current_node` is updated to the new node, the flag `visited_<new_node_id>` is set to `True`. So entering `room_a` writes `self._state["visited_room_a"] = True`.

**Multi-key AND gating** — The exit choice has:

```json
"requires": { "visited_room_a": true, "visited_room_b": true }
```

`Engine._check_requires()` iterates all key-condition pairs and returns `False` on the first failure. Both conditions must be satisfied simultaneously — this is AND semantics. There is no OR at the `requires` dict level; OR within a single key requires the list-value syntax (see example 06).

**Revisit behavior** — The hub is entered on game start via `_resolve_start()`, which sets the initial node without going through `_advance()`, so `visited_hub` is never written. Returning to the hub via a room's "Return" choice does go through `_advance()`, which writes `visited_hub = True` on the second visit — but this doesn't matter for this story since nothing requires it.

**Save on every advance** — Each time the player navigates (including between hub and rooms), `_advance()` writes a save file via `save_manager.write()`. The hub structure generates many saves. This is intentional — save-on-advance means no progress is lost.

## Key references

| Symbol | Location |
|---|---|
| `visited_` write in `_advance()` | `src/engine.py:119` |
| Multi-key AND in `_check_requires()` | `src/engine.py:75` |
| `auto_visited_flags` guard | `src/engine.py:119` |
| `_resolve_start()` — does not write visited_ | `src/engine.py:102` |
