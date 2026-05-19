# 17 — Delayed Consequences

**Story:** `stories/examples/17_delayed_consequences.json`
**Feature:** A flag set early in a story that only becomes relevant several nodes later, with no reference to it in between.

## What the story does

`act1` sets `lied: true` if the player lies. `act2` makes no reference to `lied`. `act3` has a conditional inset and a conditional choice both gated on `lied: true`. The consequence of a choice in act 1 only surfaces in act 3.

## Engine code path

**State lifetime** — `Engine._state` is a plain dict that lives for the entire run. It is initialized to `{}` at `Engine.__init__()` and only cleared by `Engine._reset()` (which fires on play-again or new game). Nothing in the engine evicts or expires flags. A flag set in act 1 is readable in act 3, act 30, or the final ending node — wherever the story checks it.

**`act2` is a pass-through** — `act2` has no `insets`, no `overlays`, and its single choice has no `requires` or `sets`. The engine renders it normally and calls `_advance()`, which writes `visited_act3 = True` but leaves `lied` untouched. State accumulates; it never retracts.

**Combined gating at `act3`** — Two different element types are gated on the same flag simultaneously:

- Inset: `{ "text": "They remember your lie.", "requires": { "lied": true }, "position": "before", "style": "warning" }`
- Choice: `{ "label": "Face the consequences", "next": "end_bad", "requires": { "lied": true } }`

Both go through `_check_requires()` independently. The engine filters insets at `src/engine.py:49` and choices at `src/engine.py:43` — the same method is called on both, making the behavior consistent: an unset or false `lied` hides both the inset and the "Face the consequences" choice.

**The player who told the truth** — `lied` is never set, so `self._state.get("lied")` returns `None`. `_check_requires()` for `requires: { "lied": true }` sees `None != True` and returns `False`. The inset is absent; the bad-ending choice is absent; the only visible choice is "Walk away clean." The structure of act 3 differs completely based on a decision made in act 1, with nothing in act 2 telegraphing the divergence.

## Key references

| Symbol | Location |
|---|---|
| `_state` lifetime | `src/engine.py:27`, `src/engine.py:131` |
| `_check_requires()` missing-key returns `None` | `src/engine.py:77` |
| Inset filtering | `src/engine.py:49` |
| Choice filtering | `src/engine.py:43` |
