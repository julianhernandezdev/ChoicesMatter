# 14 — Parallel Knowledge Routes

**Story:** `stories/examples/14_parallel_knowledge_routes.json`
**Feature:** Two different paths converging on the same node, with state determining how that node renders.

## What the story does

`fork` has two choices. Both set `source` to a different string value, then both route to `next: "converge"`. At `converge`, two conditional insets each require a specific value of `source` — only one can be visible at a time.

## Engine code path

**No engine mechanism for convergence** — The engine navigates purely by node ID. When a choice has `"next": "converge"`, the engine sets `self._current_node = "converge"` and enters the loop iteration for that node. It does not care how many other choices also point to `"converge"`. Convergent nodes require no special JSON syntax and no engine support beyond normal navigation.

**State carries across the convergence** — `_advance()` applies `choice.sets` before changing `self._current_node`. So by the time the engine renders `converge`, `self._state["source"]` is already set to whichever value the player's route wrote.

**Conditional rendering at the convergent node** — `Engine.run()` filters insets before displaying:

```python
visible_insets = [i for i in node.insets if self._check_requires(i.requires)]
```

At `converge`, two insets exist — each requires a different value of `source`. Only one passes `_check_requires()`. The display receives a list of exactly one inset; it has no knowledge that another existed.

**The graph vs. tree distinction** — CLAUDE.md notes stories are "a tree by authoring convention, not engine enforcement." Convergent nodes like this one create a directed graph. The engine's node-ID-based navigation handles graphs natively — there is no tree enforcement.

**Validation still runs** — `StoryLoader` validates that every `choice.next` references an existing node. A choice pointing to `"converge"` is valid as long as `"converge"` exists in `nodes`. Multiple choices pointing to the same target are not flagged.

## Key references

| Symbol | Location |
|---|---|
| `_advance()` sets state before navigating | `src/engine.py:116` |
| Inset filtering in `Engine.run()` | `src/engine.py:49` |
| Cross-reference validation | `src/story.py:189` |
