# Spec: Chapters (Multi-File Stories)

**Status:** Pre-roadmap / Design
**Motivation:** Enable serialised episodic fiction — an ending in one story hands off into another, carrying flag state across the boundary — without requiring one giant story file. This is one of three format-breaking features (`CLAUDE.md`: Chapters, Cross-Story Persistent State, Asset Association Layer) that must ship and stabilise before v1.0.

---

## Overview

**Scope:** this spec covers Chapters only — sequential/branching chaining between discrete story files that together form a *saga*. It deliberately does not cover Cross-Story Persistent State (e.g. achievement-style unlocks spanning unrelated, non-chained stories); that stays a separate future spec, though the two may eventually share infrastructure.

A story opts into a saga by declaring `meta.saga_id`. An ending node in that story may declare `next_story`, pointing at another story's `meta.id`. Reaching that ending hands the player off into the next chapter, carrying (a scoped copy of) the outgoing story's flag state forward. Because `next_story` lives on the ending node rather than at the story-meta level, different endings in the same chapter can route to different next chapters — branching sagas, not just linear ones.

The feature is additive: a story without `meta.saga_id` behaves identically to today.

---

## Story JSON Format Changes

### `meta` additions

```json
{
  "meta": {
    "id": "midnight_convoy_ch2",
    "title": "Midnight Convoy — Chapter 2: The Long Silence",
    "saga_id": "midnight_convoy",
    "saga_index": 2,
    "start_node": "intro"
  }
}
```

| Field | Required | Notes |
|---|---|---|
| `saga_id` | No | Groups stories into a saga. Any non-empty string. Requires `saga_index` to also be present. |
| `saga_index` | No | 1-based position within the saga. Requires `saga_id` to also be present. Across all discovered chapters sharing a `saga_id`, indices must be contiguous `1..N` with no gaps or duplicates. |
| `saga_title` | Conditional | The saga's display name, used by the picker's grouped entry. **Required** when `saga_index == 1`. **Must be absent** on any chapter where `saga_index != 1` — the saga has exactly one authoritative title, declared once, to avoid drift between chapters. |

### Ending node additions

`next_story` and `chapter_transition` are node-level fields, alongside the existing `is_ending`/`ending_type`:

```json
{
  "convoy_falls": {
    "text": "The convoy scatters into the dark, and with it, any hope of a quiet ending.",
    "choices": [],
    "is_ending": true,
    "ending_type": "bad",
    "next_story": "midnight_convoy_ch2",
    "chapter_transition": false
  }
}
```

| Field | Required | Notes |
|---|---|---|
| `next_story` | No | Target chapter's `meta.id`. Only valid on a node that is an ending (`is_ending: true`, or an implicit ending via empty `choices`). |
| `chapter_transition` | No | Boolean. Only valid alongside `next_story`. Defaults to `false`. See **Ending-Node Behavior** below. |

### Authored convention

Chapters of a saga are typically authored together under a shared directory, e.g. `stories/sagas/midnight_convoy/chapter_1.json`, `chapter_2.json`, etc. This is a convention, not an engine requirement — saga membership is determined purely by matching `meta.saga_id`, independent of file location, mirroring how the existing subfolder picker is a display concern layered over flat discovery.

---

## Flag Carryover

When a chapter hands off to the next via `next_story`, the entire outgoing `_state` dict — including engine-managed `visited_<node_id>` flags — is copied into the next chapter's `initial_state`, with every key prefixed `<outgoing_story_id>_`:

```
Chapter 1 (id: midnight_convoy_ch1) ends with _state = {"trust": 4, "visited_intro": true}
  ↓
Chapter 2's initial_state seeded with:
  {"midnight_convoy_ch1_trust": 4, "midnight_convoy_ch1_visited_intro": true}
```

The next chapter's own flags start otherwise clean — no merging beyond the prefixed import. Authors reference carried-forward state in `requires` using the full prefixed key (e.g. `"requires": {"midnight_convoy_ch1_trust": 3}`), which means a downstream chapter necessarily hardcodes the upstream chapter's `story_id`. This coupling is accepted as inherent to chained chapters — they are meant to be authored and read together.

`player_name` carries forward like any other flag (as `<story_id>_player_name`), but is inert in practice: the receiving chapter resolves its own `player_name` independently through the existing settings/`name_prompt` priority chain, regardless of the prefixed copy sitting alongside it in state.

---

## Engine Changes

### New module: `src/saga.py` — `SagaManager`

Mirrors the shape of `SaveManager`/`GalleryManager`. Persists `saves/<saga_id>.saga.json`:

```json
{
  "saga_id": "midnight_convoy",
  "current_chapter": "midnight_convoy_ch2",
  "carried_state": { "midnight_convoy_ch1_trust": 4, "...": "..." },
  "chapters_completed": ["midnight_convoy_ch1"],
  "timestamp": "2026-07-22T18:04:00Z"
}
```

`Engine` gains `SagaManager` as a fourth collaborator alongside `SaveManager`/`GalleryManager`, written to on every chapter hand-off.

### Hand-off sequence

When the current node is an ending with `next_story` set:

1. Apply existing ending-reached bookkeeping regardless of `chapter_transition`: log the ending to *this chapter's* gallery, delete *this chapter's* active save.
2. If `chapter_transition` is `false` (default): render the ending screen as today, then proceed to step 3.
   If `chapter_transition` is `true`: skip the ending screen entirely.
3. Build the prefixed carryover dict from outgoing `_state` (see **Flag Carryover**).
4. Update `saga.json`: merge the prefixed dict into `carried_state`, append the outgoing `story_id` to `chapters_completed`, set `current_chapter` to `next_story`'s id, persist.
5. Load the next chapter via `StoryLoader`, construct its `Engine` with `initial_state = carried_state`, resume the game loop.

### Standalone play

A chapter remains independently selectable and playable outside its saga context — e.g. a player jumping straight to chapter 2 from the picker before ever starting chapter 1. In that case no `saga.json` exists yet (or exists but doesn't have that chapter as `current_chapter`), and the chapter simply starts with an empty `initial_state`, identical to how any non-saga story starts today. This is the expected degrade path, not an error condition.

---

## Story Picker Changes

### Grouping and badge

Story discovery groups entries sharing `meta.saga_id` into a single picker row, keyed by `saga_id`, titled by `saga_title`. The row carries a `[SAGA]` badge next to the title, and its stats line shows chapter progress instead of an endings count:

```
[3] Midnight Convoy [SAGA]                Chapter 2/3
    by Choices Matter · v1.0
[4] A Standalone Story                     2/5 endings
    by Choices Matter · v1.0
```

Ungrouped stories (no `saga_id`) render exactly as they do today.

### Solo / orphan saga

If saga discovery finds only one chapter for a given `saga_id` (the rest not yet written, or simply not present in `/stories/`), the stats line cannot honestly claim `Chapter 1/1` — that reads as "complete, one chapter total." Instead it renders a distinct label, still fully playable:

```
[3] Midnight Convoy [SAGA]              Chapter 1 · more chapters coming
    by Choices Matter · v1.0
```

### Drill-down chapter list

Selecting a saga's collapsed row opens a sub-screen listing every known chapter, reusing the existing subfolder drill-down pattern:

```
Midnight Convoy
[1] Chapter 1: The Break-In         ✓ 3/5 endings
[2] Chapter 2: The Long Silence      ▶ current · 0/4 endings
[3] Chapter 3: ???                   🔒 locked
[B] Back
```

- `✓` completed chapters (behind `current_chapter`) are selectable — see **Rollback** below.
- `▶` marks `current_chapter`; selecting it runs the ordinary Continue-or-New flow, same as any story.
- `🔒` locked chapters (`saga_index` beyond `current_chapter`'s) are shown, dimmed, and not selectable — visible so the player knows the saga continues, without letting them jump ahead.

### Rollback (replaying an earlier chapter)

Selecting a completed chapter behind `current_chapter` prompts a confirmation, reusing the existing `prompt_clear_confirm()`-style Y/N pattern:

```
Replaying Chapter 1 will erase progress in Chapter 2 onward.
Continue?  [Y/N]
```

On confirmation:

- Delete the active save for every chapter with `saga_index` greater than the replayed chapter's.
- Truncate `chapters_completed` in `saga.json` to only entries before that index.
- Reset `current_chapter` to the replayed chapter.
- Strip any `carried_state` keys prefixed by a chapter at or beyond that index.
- The replayed chapter itself runs ordinary New Game — its own save was already deleted the moment it was originally finished (endings always delete the active save).

**Per-chapter galleries are never touched by rollback.** Endings already found in chapters 2+ remain marked "found" even after those chapters' saves are erased — consistent with the existing invariant that galleries survive save deletion and are cleared only via the explicit "clear all save data" flow.

---

## Validation Additions

### `StoryLoader` (per-file, schema-level)

- `saga_id` present without `saga_index` (or vice versa) → error.
- `saga_id`/`saga_title` present but not non-empty strings → error.
- `saga_index` present but not a positive integer → error.
- `saga_title` present when `saga_index != 1` → error.
- `saga_title` absent when `saga_index == 1` → error.
- `next_story` present but not a non-empty string → error.
- `next_story` present on a node that is not an ending (no `is_ending: true` and non-empty `choices`) → error.
- `chapter_transition` present without `next_story` → error.
- `chapter_transition` present but not a boolean → error.

### `scripts/validate_story.py` (cross-file, WARN tier unless noted)

The validator only reasons over the files passed to it in a given invocation — it cannot see the rest of `/stories/`. After per-file validation, stories sharing a `saga_id` among the *validated set* are grouped for these checks:

- Group size 1 → `WARN`: `saga_id 'X': no sibling chapter among validated files (this one declares saga_index=N) — pass sibling chapters together to check saga-wide consistency`. Never affects exit code — the story is fully playable on its own.
- Group size > 1: `saga_index` values must be contiguous `1..N` with no gaps/duplicates → `ERROR` if violated.
- `next_story` must resolve to a discoverable `meta.id` among the validated set → `ERROR` if not found (same severity as a broken `choice.next`).

---

## Open Questions

1. **Independent saga reset.** Should a player be able to reset saga progress (`saga.json`) without also clearing each chapter's own save/gallery data, via the existing "clear all save data" flow — or does clearing a saga always cascade to clearing every chapter in it?
2. **End-of-saga summary.** Once `chapters_completed` covers the whole saga, should there be a dedicated summary/credits screen distinct from the final chapter's own ending screen?
3. **`name_prompt` on hand-off.** If a downstream chapter declares its own `meta.name_prompt`, should it be skipped automatically on saga hand-off (the player already named themselves earlier in the saga), the same way it's already skipped on ordinary save resume? Currently unspecified — defaults to prompting again unless resolved here.
4. **Locked-chapter dimmed state.** This introduces the engine's first "visible but unselectable" list item; no existing pattern (choices are only ever shown-or-hidden via `requires`). Worth deciding whether this dimmed-item pattern should be generalized for future reuse, or kept saga-specific.
