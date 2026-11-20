# Postmortems

Significant wrong turns, failed approaches, and design reversals worth remembering. Small bugs don't belong here — only things that consumed meaningful effort or reveal a systemic blind spot.

---

## 2026-09-20 — RFC 0001 was accepted without reconciling an existing Chapters design spec

**What happened:** RFC 0001 (drafted 2026-06-08, accepted 2026-09-19) and a separate design spec, `specs/spec-chapters.md` (commit `a28587e`, 2026-07-22, on `origin/claude/next-work-priorities-ussf5j`), described incompatible Chapters models: `chained_from` vs `saga_id`/`saga_index`, explicit exports vs prefixed full-state carryover, hidden chapters vs a saga home screen. Neither document referenced the other. The spec was never merged to `main`, and `docs/` is gitignored, so semantic search over the checkout never surfaced it; it was found the next day with `git log --all --grep=chapter`. Reconciling the two took a design review (decision log 2026-09-20) that reversed several of the RFC's accepted decisions.

**Why it went unnoticed:** Design docs live in gitignored paths or on unmerged branches, and the 2026-09-19 RFC triage looked at the working tree only. No code had been written against either design, so nothing was wasted beyond the acceptance itself.

**Fix:** A new spec supersedes both; RFC 0001 is marked superseded in part and flips to `Superseded` when the spec is written.

**Lesson:** Before accepting an RFC or starting a spec, search every branch and remote for prior design work on the same feature (`git log --all -i --grep=<feature>`), not just the working tree. Design work that exists only on a branch is invisible to every other search tool.

---

## 2026-07-06 — The same "recompute instead of derive from actual state" bug appeared three times in one feature

**What happened:** The Corruption Resolve Effect's `cascade` animation needs to know which character positions are currently corrupted so it can reveal them one at a time. The first design (`cascade_reveal_order(text, intensity, mode, seed)`) recomputed that position set from scratch — the same inputs `corrupt_string()` uses to originally corrupt the text, but a second, independent call. For `mode="consistent"` this happens to agree (same seeded algorithm, same inputs, same output). For `mode="random"`, it doesn't: two independent calls to the shared, unseeded random module draw different subsets, so the reveal order desyncs from what's actually on screen. This exact bug pattern showed up three separate times: once in the Python cascade implementation (caught in task review, fixed by changing `cascade_reveal_order`'s signature to accept the actual corrupted positions instead of recomputing them); pre-emptively avoided in the JS cascade mirror once the Python fix existed as a reference; and then a *variant* of the same root cause appeared in the JS decay handler — `_twCorruptString` conflated "resolve intensity/mode against settings" with "render corrupted text," so calling it a second time (to re-render a scaled-down intensity) silently re-applied the `intensity_multiplier` a second time.

**Why it went unnoticed at design time:** The bug is invisible in the common case. `mode="consistent"` (the default) never exposes it, and default `intensity_multiplier: 1.0` makes the double-multiply a no-op. It only becomes visible when the feature is used in exactly the way it's meant to be flexible for (`mode="random"`, or a player-configured `intensity_multiplier` — an accessibility setting this same feature added). Task-level reviews caught each instance because they specifically hand-traced the "does this independently-computed value agree with what's actually rendered" question rather than only checking the code against its own stated spec.

**Fix:** `cascade_reveal_order` (Python) changed signature to take explicit `positions: list[int]` (derived by the caller by diffing the actual rendered corrupted string against the clean text) rather than `(text, intensity, mode, seed)`. `web/typewriter.js` mirrors this. `_twCorruptString` was split into `_twCorruptStringRaw` (no internal resolution, takes already-resolved values) plus a thin resolving wrapper, so a caller that already has a resolved intensity never re-triggers resolution.

**Lesson:** Whenever a value is "resolved" (against config, against random state, against anything with hidden state) and then that SAME logical value needs to be used again later — in a different function, a different animation frame, or a different engine — derive it from the first resolution's actual output, don't recompute it from the original inputs. This applies doubly across this project's two-engine (Python/JS) architecture and doubly again across any two-phase pipeline (parse-time vs. render-time). When reviewing code that "recomputes" something instead of "reusing" it, ask explicitly whether the recomputation is provably identical to the original — for anything involving `mode="random"`/unseeded randomness, it usually isn't.

---

## 2026-05-21 (discovered 2026-07-09) — Edits to a vendored plugin cache were silently reverted by an update

**What happened:** To get subagents to prefer `mcp__semble__search` over `Read`/`Grep`/`Glob` for exploration, the `superpowers` plugin's cached skill files (`brainstorming/SKILL.md` Step 1, `systematic-debugging/SKILL.md` Phase 2 Step 1) were edited directly, adding a semble-first instruction. It was verified working at the time via a manual before/after check (0 semble calls → 5 semble calls). A note was made explicitly flagging the fragility: "local plugin cache only — not forked, edits will be lost on plugin update." Roughly seven weeks later, a token-usage audit (`scripts/audit_skill_tokens.py`, built for an unrelated reason) grepped all 34 skill files in `superpowers` plugin v6.1.1 and found **zero** mentions of semble anywhere. The May edits were gone — silently overwritten by a plugin update sometime in the intervening window, with no error, warning, or changelog entry surfaced to the user. Across 161 real transcripts spanning that window (30 sessions + 131 subagent dispatches), semble was called only 3 times total vs. 1,140+ Read calls — consistent with the guidance having been absent for nearly the entire period it was assumed to be active.

**Why it went unnoticed:** The fix worked and was verified at the moment it was made — there was no reason to re-check it later, and nothing about a routine plugin update surfaces "a file you customized was just overwritten." The risk was correctly identified and written down at the time, but nothing was in place to actually catch the regression when it happened; the note sat unactioned until an unrelated audit incidentally re-checked the same files.

**Fix:** Redone via a different mechanism entirely — see the internal decision log (2026-07-09). Guidance now lives in this repo's own `CLAUDE.md` (git-tracked, immune to plugin updates) instead of the vendored plugin cache, paired with a rerunnable audit script so "did the guidance actually change behavior" has a checkable answer instead of a one-time verification that silently goes stale.

**Lesson:** Editing a vendored/cached third-party file to configure behavior is fragile even when it works today — "not forked, will be lost on update" is a live risk, not a documentation footnote, and it will not announce itself when it fires. Two mitigations, both applied here: (1) put durable configuration in a project-owned, git-tracked file instead of a vendored cache whenever the option exists; (2) if a fix depends on state you don't own, make its verification rerunnable (a script, a test) rather than a one-time manual check, so drift gets caught by later routine use instead of by accident.

---

## 2026-07-05 — Web section subscreen snapshot rebuilt on every re-render

**What happened:** The `renderSectionSubscreen` and `renderAccessibleSectionSubscreen` functions took a snapshot of the section's draft keys unconditionally on every call. Because every in-subscreen edit re-invokes the renderer, the snapshot always reflected post-edit state — making the X (discard section) key a no-op. Additionally, `currentSectionScreen` was never reset to `null` on exit, so re-entering the same section skipped the snapshot entirely, leaving it stale from the prior visit.

**Why it went unnoticed:** Individual task reviewers only saw their task's diff. The snapshot guard (`if (currentSectionScreen !== section)`) was correct for intra-subscreen re-renders but couldn't be evaluated correctly without seeing both the render and the exit paths together — a cross-task seam the whole-branch reviewer caught.

**Fix:** Two changes: (1) guard the snapshot block so it only runs when transitioning into a new section (`if (currentSectionScreen !== section)`); (2) reset `currentSectionScreen = null` and `sectionDraftSnapshot = null` at the top of `renderSettings()` and `renderAccessibleSettings()` so every fresh entry re-snapshots. Committed across `f3a0100` and `62d67f0`.

**Lesson:** Snapshot/restore correctness spans two sites — where the snapshot is taken and where the owning screen is exited — and can't be fully verified from a single task diff. The final whole-branch review is the right gate for this class of bug.

---

## 2026-05-21 — Ending node insets dropped silently

**What happened:** Four of nine public stories had insets on ending nodes. The engine silently discarded them — `show_ending()` only accepts overlays, not insets. No error, no warning.

**Why it went unnoticed:** The story format allows insets anywhere syntactically. The validator doesn't check inset placement against node type. The bug only manifests at runtime, and ending screens are easy to miss during authoring when iterating on prose.

**Affected stories:** The Last Train, ash_and_receipts, and two others confirmed at discovery.

**Fix:** Converted insets to overlays in all four affected stories (overlays are supported on ending nodes). Committed 2026-05-21.

**Lesson:** Insets are not valid on ending nodes. The correct pattern is overlays. The validator should warn — or error — when insets appear on an ending node. That check is not yet implemented.

---

## 2025 — Pygame/Pyglet native renderer spike (abandoned)

**What happened:** A spike was started to investigate replacing `src/display.py`'s `rich`/terminal rendering with a proper windowed renderer using Pygame or Pyglet.

**Why it was abandoned:** The web player (GitHub Pages, `index.html` + `web/`) was built instead and already covers the "play without a terminal" use case for players who can't or won't run Python. A native windowed renderer would duplicate that effort without adding meaningful reach.

**Lesson:** The web player was the right call. Any future "native app" requirement should be evaluated against the web player's coverage first. The two-engine model (Python CLI + JS web) is the settled architecture.
