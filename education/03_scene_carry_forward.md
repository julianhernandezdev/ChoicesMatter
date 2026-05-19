# 03 — Scene Carry-Forward

**Story:** `stories/examples/03_scene_carry_forward.json`
**Feature:** The `scene` field sets a location label that persists across nodes until overridden.

## What the story does

`room_a` sets `"scene": "The Library"`. `room_b` has no `scene` key — it inherits. `garden` sets `"scene": "The Garden"`, replacing the inherited value. `end` inherits from whoever reached it last.

## Engine code path

`Engine.__init__()` initializes `self._current_scene: str | None = None`.

At the top of every `Engine.run()` iteration:

```python
node = self.story.get_node(self._current_node)
if node.scene:
    self._current_scene = node.scene
```

`Node.scene` is `None` by default (when the JSON key is absent). The `if node.scene` guard only updates `_current_scene` when a non-None value is present, so nodes without a `scene` key leave the accumulated value unchanged.

`self._current_scene` is then passed to `display.show_node(..., current_scene=self._current_scene)`.

**`Display.show_node()`** (`src/display.py:146`) — when `current_scene` is truthy:

```python
if current_scene:
    self.console.print(Rule(f"[dim]{current_scene}[/dim]", style="dim"))
```

A dim Rule line is printed above the story panel.

**`Engine._reset()`** (`src/engine.py:130`) clears `self._current_scene = None`, so scene state does not carry between playthroughs.

**Validation** — `StoryLoader.load()` checks that `scene`, if present, is a non-empty string after stripping whitespace (`src/story.py:161`).

## Key references

| Symbol | Location |
|---|---|
| `_current_scene` init | `src/engine.py:28` |
| Scene update in loop | `src/engine.py:40` |
| `_reset()` clears scene | `src/engine.py:134` |
| `Display.show_node()` scene rule | `src/display.py:155` |
| `scene` validation | `src/story.py:160` |
