# Board

Current sprint snapshot. Update when work starts or finishes.

---

## In Progress

| Item | Notes |
|---|---|

_Last shipped 2026-09-19: fresh-run name prompt (CLI), settings clamp parity, CLAUDE.md drift sync._

---

## Up Next

| Item | Notes |
|---|---|
| Extract Settings Screen from Display | `show_settings_screen` + helpers into `src/settings_screen.py`; explicitly flagged "do after Default Settings ships" in BACKLOG.md |

---

## Done (Recent)

| Item | Date |
|---|---|
| **Chapters / Sagas** (Godot v1.0 Critical Path #1) — Plan 1 (CLI) implemented on `feat/chapters-cli`; awaiting merge; Plan 2 (web parity, `feat/chapters-web`) next. Saga picker row + home screen, chapter-entry seeds, `chapter_transition` / `saga_end`, destructive replay with confirmation, `--debug` unlock and `--seed`, cross-file validation with `--strict`, four-chapter example saga in `stories/sagas/` | 2026-09-21 |
| CLI: protagonist name prompt now asked at every fresh run (first launch, New game at the resume prompt, play again) via a new `Engine` `fresh_run_state` provider — web already did this; the CLI silently reused the first name. Verified with a real-`Display` scripted run (fails on the old code, passes on the new) | 2026-09-19 |
| Settings clamp parity — JS settings are now range-checked at edit time (the Corruption subscreen previously clamped nothing) and on load; shipped default `scramble_frames` 85 was outside its own 1–50 range, so frames ranges widened to 1–200; Python `clamp_setting`/`corruption_timing` + JS helpers in `web/engine.js`, with cross-language parity tests. Verified in a localhost browser run | 2026-09-19 |
| CLAUDE.md drift sync — Dependency Flow and Display Layer table corrected against `display.py`; `tests/test_docs_drift.py` fails when a public `Display` method or `src/*.py` module is not documented | 2026-09-19 |
| Story Picker: restyled footer hints in `prompt_story_select()` — dropped redundant pagination shorthand, reordered lines (primary "enter a number" hint now closest to input), colored hotkeys/pagination keys by semantic weight to match settings-screen convention, matched folder-browsing footer to root picker | 2026-07-08 |
| Content: added `resolve_style` (decay/cascade) to 8 selected `{corrupt}` spans across 5 published stories, narratively fitted per moment | 2026-07-06 |
| Corruption Resolve Effect — `resolve_style` param (decay/cascade) on `{corrupt}` spans, decay/cascade typewriter animation (CLI + Web); fixed pre-existing `Mode Default` settings-wiring bug; split `Intensity` into `Intensity Default` (override-or-default) + new `Intensity Multiplier` (always-applied accessibility scalar) to preserve global corruption-dampening; `Player name` relabeled `Player name Default`. 13-task subagent-driven implementation, 2 fix cycles (cascade reveal desync under `mode=random`; JS decay double-applying `intensity_multiplier`), whole-branch review approved | 2026-07-06 |
| Web: touch/click no longer skips typewriter — removed the global `document` click-to-skip listener in `web/app.js`; keyboard skip untouched. Verified live via Playwright (mid-animation click leaves partial text intact; keydown still skips). Backlog item added for a settings toggle to opt back into tap/click-to-skip | 2026-07-05 |
| Restored *The Locked Room* (v1.3) and *The Watcher in the Light* (v1.1) to `stories/horror/` — excluded 2026-05 for graphic content, that call no longer applies; `web/stories.json` re-synced | 2026-07-05 |
| Story Picker: author/version byline row (`by {author} · v{version}`) below the title/stats line; author names truncate at 20 chars with `...` | 2026-07-05 |
| Story metadata cleanup: normalized `meta.author` repo-wide from 8 distinct strings down to 3 (`Choices Matter`, `ChoicesMatterGPT`, `Fable`); moved *Awaiting Response* to `stories/` root and *The Cartographer's Confession* to `stories/horror/`; re-synced `web/stories.json` | 2026-07-05 |
| *The One-Eyed Guest* (`stories/the_one_eyed_guest.json`) — Nordic folk-horror one-shot; three guest-right tests over one night, inside/outside staging split, diegetic vocabulary-glossing insets, obfuscated final choice, 3 endings. First story authored end-to-end by a Claude Fable 5 subagent from a brainstormed spec | 2026-07-05 |
| Default Settings & Section Registry — `SETTINGS_SECTIONS` registry on both platforms; registry-driven settings rendering, generic section sub-screens (S/X/M/Q/R nav), Reset to Defaults with checkbox selector; `player_name` and `accessible_mode` preserved on global reset | 2026-07-05 |
| *The Last Customer Support Representative* v1.2 — full engine feature pass: name_prompt, {player_name} ×7, corruption gradient (5 zones), 10 conditional inline prose moments, variable text substitution (inset collapse) | 2026-07-04 |
| Chore: tune corruption defaults — intensity 0.6, 85 scramble frames, 40 ms delay | 2026-07 |
| Fix: CLI corruption settings persistence (`_settings_corruption` S key now actually saves; values no longer reset on settings re-entry) | 2026-07 |
| Fix: CLI charset cycling crash — empty rich markup `[]`/`[/]` when cycling to "custom"; replaced with conditional print | 2026-07 |
| Add: web player Corruption settings section — 7 rows, `cycle`/`float` types, `animate` default true, `settingsDraft` now includes corruption | 2026-07 |
| Add: root `CHANGELOG.md` (moved from gitignored `docs/`); fix README "Full changelog" link | 2026-07 |
| *Awaiting Response* (ChoicesMatterGPT) — deep-space relay horror showcasing corrupted text, name prompt, consistent/random modes, node baseline, obfuscated choice, 5 endings | 2026-07 |
| README, `feature-reference.md`, and `Prompt.md` updated for v0.11.0 — corrupted text section, feature table, §23 reference entry, GPT authoring prompt | 2026-07 |
| Corrupted Text Rendering (CLI + Web) — inline `{corrupt}` spans, node baseline, TextSegments pipeline, scramble-settle typewriter, accessibility fallback, settings sub-screen | 2026-07 |
| Protagonist Name Prompt — `{player_name}` token, name prompt screen, player name setting (CLI + Web) | 2026-07 |
| Variable Text Substitution — `{key}` in any text field, Python + JS engines | 2026-07 |
| Add 3 ChoicesMatterGPT stories (ash_and_receipts, lantern_rounds, moonlitdoor) | 2026-05 |
| Add The Vulture Corridor v2.1 demo (`stories/horror/`) | 2026-05 |
| Story subfolder reorganisation (`showcase/`, `horror/`, `ChoicesMatterGPT/`) | 2026-05 |
| `education/feature-reference.md` — master index for all 23 example stories | 2026-05 |
| Fix: remove empty `warnings` field from ash_and_receipts | 2026-05 |
| `{pause}` inline delay token in typewriter (CLI + Web) | 2026-05 |
| WCAG 2.1 Level AA accessible mode (web player) | 2026-05 |
| Ending node inset bug — converted insets to overlays in 4 stories | 2026-05 |
| Inline conditional text `{flag?true|false}` (CLI + Web) | 2026-05 |
| Mobile capture flow for settings edits (web) | 2026-05 |
| The Cartographer's Confession enhancements (insight threshold, visited_ overlay) | 2026-05 |
| Customer Support story (ORLA profile insets, list requires, compliance gate) | 2026-05 |
