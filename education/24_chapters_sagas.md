# 24 — Chapters and Sagas

**Stories:** `stories/sagas/24_saga_ch1_the_bridge.json`, `24_saga_ch2a_the_far_bank.json`, `24_saga_ch2b_the_skiff.json`, `24_saga_ch3_the_last_ferry.json`
**Feature:** A story ending can chain into another story file. Chapters that share a `saga_id` form a saga: one picker row, a saga home screen listing the chapters you have reached, and only the flags an ending exports carry over. The CLI runs sagas today; the web player does not yet.

## What the saga does

*The Last Ferry* is four short chapters. Chapter one ends three ways: help a stranger across the bridge (chains to **2A**), take the ferryman's skiff (chains to **2B**), or push past the stranger and fall (a plain dead end). Both middle chapters chain into the finale, so the graph branches and converges. In the finale you can only ring the bell if you carried enough `trust`.

```
ch1 ──e_left──▶ 2A ──(transition)──▶ ch3 ──e_win  (saga_end)
    ──e_right─▶ 2B ──────────────────▶     ──e_lose (plain)
    ──e_fall  (plain)
```

The trust arithmetic, if you want to check the finale:

| Route | `trust` entering ch3 |
|---|---|
| Cross the rope bridge → Help them across (`+2`) → 2A → any choice (`+1`) | 3 |
| Knock at the hut → Take the skiff (`+1`) → 2B → Row hard (`+1`) | 2 |
| Knock at the hut → Take the skiff (`+1`) → 2B → Drift | 1 |

Chapter three's bell choice requires `trust: 2`, so it is hidden after "Drift". Chapter one's third ending (`e_fall`) is an ordinary dead end: no `next_story`, no `saga_end`.

## Meta fields

| Field | Notes |
|---|---|
| `saga_id` | Same on every chapter |
| `saga_title` | Only on the first chapter (the one nothing chains into) once the saga has two or more chapters |
| `chapter_label` | Optional short label (`"2A"`) shown before the title on the saga home screen |

## Ending-node fields

| Field | Notes |
|---|---|
| `next_story` | The next chapter's `meta.id` |
| `exports` | Exact flag names to carry over, same names. `visited_<node>` allowed. No `*`; never `player_name` |
| `chapter_transition` | `true` = the node plays as a normal scene plus one keypress, then the next chapter starts |
| `saga_end` | `true` marks the finale; can't be combined with the fields above |

An ending with none of these is a plain dead end. A `next_story` that matches no installed chapter is a *dangling* link: the ending shows "To be continued" and does not chain.

## How state carries

Only the flags in `exports` (if they are set) plus `player_name` reach the next chapter. Chapter one exports `trust` and `visited_bridge` to 2A, so 2A can write `{visited_bridge?The bridge still sways behind you.|You did not come by the bridge.}` and gate its "Call out to the stranger you helped" choice with `"requires": {"trust": 2}`.

The carried state is stored as a **chapter-entry seed** (`saves/<chapter_id>.handoff.json`) written the moment the ending is reached, so quitting at the `[C]ontinue / play [A]gain / [M]enu` prompt loses nothing. It stays until a parent chapter chains in again, so "New game" on chapter two later still starts with your chapter-one choices. A chapter that starts from a seed skips its own `name_prompt` (2A and 2B both declare one, and never show it when reached from chapter one).

If you export `visited_bridge`, the next chapter must not have its own node called `bridge`, or the carried flag would look like a real visit. The validator checks this.

## What the player sees

- One `[SAGA]` row in the picker (`● RESUME` while any chapter has an active save): `X/Y chapters · X/Y endings`, `✓ Complete` after a `saga_end`, `· more chapters coming` while a `next_story` points at a chapter that isn't installed yet.
- Selecting it opens the saga home screen: the chapters reached so far (each marked `▶` in progress, `●` ready to start, `✓` finished, `·` new), plus a `…more to discover` line while others remain. Enter picks the default chapter, the one you played most recently.
- At a chaining ending: the ending screen, then `[C]ontinue / play [A]gain / [M]enu`. A `chapter_transition` node skips that prompt: the scene plays and one keypress moves you on (2A's `e_go` does this). The finale prints "End of saga".
- Restarting a chapter that has later chapters in progress prints `Restarting this chapter will erase your progress in: <titles>.` and asks `Continue? [Y/N]`, then erases that later progress. Ending galleries are never touched.

## Testing a late chapter

`python main.py --debug --seed trust=2` lists every chapter of the saga on the saga home screen, including ones you have not reached. A chapter with no seed starts cold; `--seed` supplies the flags an earlier chapter would have exported (values `true`/`false`, integers, or text). `--seed` requires `--debug`, applies to cold starts only, and is never saved.

## Validating

```bash
python scripts/validate_story.py stories/sagas/24_saga_*.json
python scripts/validate_story.py --strict stories/sagas/24_saga_*.json
```

Validate all of a saga's files together. The checks cover duplicate ids, cycles, several entry chapters, `saga_title` placement, exports nothing sets, flags a chapter needs that no earlier chapter provides, and (with `--strict`, which promotes only this to an error) a `next_story` that matches no file. Given a single chapter of a saga, the validator warns you to pass its siblings too and skips the checks that need them.

## Code path

| What | Where |
|---|---|
| Fields and per-file validation | `src/story.py` |
| Seed file | `src/save.py` (`HandoffRecord`) |
| Graph, progress, `--seed` parser | `src/saga.py` |
| Ending kinds, seed write, `ChainResult` | `src/engine.py` |
| Picker rows, saga home screen, replay, chain loop | `main.py` |
| Screens and prompts | `src/display.py` |
| Cross-file checks | `scripts/validate_story.py` |
