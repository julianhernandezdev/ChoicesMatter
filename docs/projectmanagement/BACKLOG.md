# Backlog

Items waiting to be scheduled. Promoted to PIPELINE.md when picked up.

---

## High Priority

### Godot v1.0 Critical Path
Five items required before v1.0 (Godot library readiness). Ship in order — each builds on the last or adds a format-breaking change that must be stable before v1.0.

1. **Chapters / Sagas** — branching saga model: `meta.saga_id` / `saga_title` / `chapter_label`; ending-node `next_story` + explicit `exports` (original flag names) + `chapter_transition` + `saga_end`; persistent chapter-entry seed; saga home screen with destructive replay. **Plan 1 (CLI) implemented on `feat/chapters-cli` (2026-09-21); awaiting merge.** Supersedes RFC 0001's model (decision log 2026-09-20); spec `docs/superpowers/specs/2026-09-20-chapters-saga-design.md`. **Next: Plan 2 (web parity, `feat/chapters-web`).** The former open question is settled in `main.py` (`_saga_fresh_run_state`): one composed provider per saga chapter — confirm replay → resolve the seed (entry seed, else name prompt / settings name, plus a cold-start `--seed` overlay) → erase downstream progress last.
2. **Cross-Story Persistent State** — `global.*` flag namespace backed by `saves/global.json`
3. **Asset Association Layer** — optional `node.assets` field for host engines (Godot, etc.); CLI/web ignore it
4. **Signal / Event API Design** — spec doc only (`godot-signal-api.md`); no implementation
5. **GDScript Engine** — Godot 4 plugin in new repo `ChoicesMatter-Godot`; the actual v1.0 deliverable

Full plans are in the internal roadmap's `v1.0 Critical Path` section (not tracked in this repo).

---

## Medium Priority

### Story Graph Visualizer
CLI tool: reads story JSON, outputs a Mermaid graph of the full node tree with node types, flag edges, and ending colours.

### Extract Settings Screen from Display
Move settings UI out of `Display` into `src/settings_screen.py` — reduces Display to pure rendering + prompting. **Note:** The Default Settings & Section Registry feature refactors `show_settings_screen` significantly; extract after that ships to avoid double-churn.

### Settings Plugin Surface
Deferred non-goal from the Default Settings & Section Registry spec (`specs/2026-07-04-default-settings-design.md`). Now that `SETTINGS_SECTIONS` is stable on both platforms, define the contributor-facing API for adding a new section: docs for the registry shape, key-collision validation (a new section reusing an existing dot-path key), and schema versioning so old `settings.json` files migrate cleanly as sections change shape. **Note:** do after Extract Settings Screen from Display ships — the registry's new home in `src/settings_screen.py` is where the contributor API should live.

### Keybinding Settings Section (Controls)
Deferred future work from the same spec. Sub-screen nav keys (S/X/M/Q/R) are hardcoded per-screen on both platforms. Standardize them as named constants first, then expose a "Controls" settings section for remapping. Precursor to the plugin surface item above — do the constants pass before designing the rebinding UI.

### Extract Typewriter Logic from Display
Move `_typewrite()` and helpers into `src/typewriter.py` — independently testable. **Note:** `_typewrite()` grew further with the Corruption Resolve Effect's decay/cascade animation phases (2026-07-06) — the case for extraction is stronger now than when this item was first written.

### Web: run tests/test_web.py against the local checkout
`tests/test_web.py`'s `BASE_URL` is the deployed GitHub Pages site, so it cannot catch a local regression before it ships, and 13 of its 35 tests already fail on `main` because the tests are stale relative to features added after they were written (diagnosed 2026-09-19): (1) 11 gameplay/debug tests time out because their "open first folder, pick story 1" helper lands on the protagonist **name prompt** (*Ash and Receipts*, first in `ChoicesMatterGPT/`, has `name_prompt`), a screen the helper does not handle — it only handles the content-warning and resume screens; fix by pressing Enter to accept the prefilled name (or picking a story without `name_prompt`). (2) 2 `TestSettings` tests assert the `Enabled` / `Speed` rows on the top-level Settings screen, but since the Section Registry (2026-07-05) those rows live in the Typewriter subscreen; fix by opening it first. Serve the repo root locally (`python -m http.server`; `index.html` is at the root, not in `web/`) from a pytest fixture, point `BASE_URL` at it, then fix or update the stale assertions. Related: `tests/test_web_settings.py` keeps an inline copy of the web settings registry because `web/app.js` cannot be imported in Node, so the copy can drift from `app.js`.

### De-duplicate the web corruption renderer
`_effectiveIntensity` / `_corruptString` in `web/app.js` (~l.126-177) and `_twEffectiveIntensity` / `_twCorruptStringRaw` in `web/typewriter.js` (~l.83-142) are near-copies. They have already drifted once: only the Python side had the `intensity <= 0` guard until the 2026-09-19 clamp parity fix, which patched both copies through shared helpers in `web/engine.js` rather than merging them. Merge the bodies into one shared module. This touches the seeded-corruption parity path (`_textSeed` / LCG selection), so it needs its own spec, with the existing cross-engine seed tests as the safety net.

### CLAUDE.md: audit the Save / Validation / Flag sections against the code
The 2026-09-19 drift sync audited only the Module table, Dependency Flow and Display Layer, and added `tests/test_docs_drift.py` for those. The Save System, Validation Rules, Flag System and Story JSON Format sections have not been checked against the code. Extend the drift guard wherever a mechanical check is possible.

### Themes
Named color scheme presets (`default`, `noir`, `amber`, `paper`) in `settings.json`.

### Tap/Click-to-Skip Typewriter Setting
Web: touch/click no longer skips the typewriter animation (only keyboard input does — the global click-to-skip listener in `web/app.js` was removed so mobile taps stop accidentally snapping prose to full text). Add a settings toggle (e.g. under the typewriter or accessibility section) letting users opt back into tap/click-to-skip for those who prefer the old behavior. Pairs naturally with the Keybinding Settings Section item below if input remapping gets its own section.

---

## Lower Priority / Longer-term

### Achievements
Authored unlock conditions tracked across runs in `saves/achievements.json`. **RFC 0002 accepted 2026-09-19; sequenced after v1.0** (not on the Godot Critical Path — start only once v1.0 is declared). Design is closed; see the RFC and the internal roadmap.

### Choice Graph / Replay
Full-story map, unlocked after all endings found.

### Web Export (single-file)
Generate a self-contained HTML from a story JSON — no server needed.

---

## Icebox

- Split Display into GameDisplay / PickerDisplay
- Skip Already-Seen Prose (typewriter skip on revisit — data already in save state)
- Cross-Story Persistent State (`saves/global.json`, `global.*` flag namespace)
- Random outcomes (weighted `next` arrays)
- Timed choices (countdown before auto-select)
- Story packaging (zip story + assets)
- Notion Wiki (game design bible, 12 pages)
