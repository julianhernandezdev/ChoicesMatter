# Risks

Active risks and open uncertainties. Resolved risks are kept for record.

---

## Open

### `web/app.js` is a large monolithic file
**Risk:** The file has grown to several thousand lines covering all rendering, settings, state, and game orchestration. Navigation and review are difficult; adding new screens increases the file further.
**Mitigation:** `web/engine.js` was extracted for pure game logic. Further breakup (display modules per screen) is acknowledged tech debt, planned post-redesign.
**Impact:** Medium — slows feature development; not a correctness risk.

### No automated E2E tests for the web player in CI
**Risk:** The Playwright tests (`tests/test_web.py`) run against the deployed GitHub Pages site (`BASE_URL`), not the local checkout, so they cannot catch a regression before it ships; 13 of its 35 tests already fail on `main` (checked 2026-09-19: 11 selector timeouts, 2 assertions expecting the pre-sections Settings layout). Regressions in web rendering, focus management, or accessible mode won't be caught automatically before they reach production.
**Mitigation:** JS engine tests in `tests/test_web_engine.py` verify parity for specific scenarios. UI regressions require human testing. Since 2026-09-19, logic that needs tests (settings clamping) is written as pure helpers in `web/engine.js` so the Node harness covers it, and UI behavior is checked with a localhost Playwright run (serve the repo root; `index.html` is not in `web/`). See BACKLOG for pointing `test_web.py` at a local server.
**Impact:** Medium — accessible mode and visual regressions are most at risk. Confirmed concretely by the Corruption Resolve Effect work (2026-07-06): `web/app.js`/`web/typewriter.js` cannot be executed via the Node-subprocess test harness (browser-only globals at module scope), so their new decay/cascade animation logic is only covered by text-presence assertions plus manual Playwright verification — a real logic bug there (the JS `intensity_multiplier` double-application, caught only by task review reading the code) would not have been caught by the automated suite.

### Story manifest (`web/stories.json`) is manually synced
**Risk:** New stories added to `stories/` won't appear in the web player until `scripts/sync_stories.py` is run and the result committed. Easy to forget.
**Mitigation:** `scripts/sync_stories.py` exists and is documented. Step must be done consciously.
**Impact:** Low — doesn't break anything; stories just don't appear in the web player.

### Python/JS engine parity drift
**Risk:** The two-engine model requires every engine feature added to the Python CLI to be manually ported to `web/engine.js`. Conformance fixtures catch divergence, but only for scenarios explicitly covered — a new feature's JS port can be subtly wrong without a test catching it.
**Mitigation:** JS parity tests in `tests/test_web_engine.py` are the source of truth. New engine features must add JS test coverage before the port is considered complete. Cross-language parity tests now also compare the settings range table and the corruption timing function against the Python implementations (2026-09-19).
**Impact:** Medium — divergence would produce different game outcomes between CLI and web player for the same story + input.

### Duplicated corruption renderer in `web/app.js` and `web/typewriter.js`
**Risk:** `_effectiveIntensity` / `_corruptString` (`app.js`) and `_twEffectiveIntensity` / `_twCorruptStringRaw` (`typewriter.js`) are near-copies. They have already drifted once (only Python had the `intensity <= 0` guard until 2026-09-19), so a fix to one can silently miss the other.
**Mitigation:** Shared helpers (`corruptionCount`, `corruptionTiming`, `clampSetting`) live in `web/engine.js` and both copies call them; the bodies are still duplicated. Merging them is a BACKLOG item.
**Impact:** Low–Medium — a divergence changes how corruption looks between the static and animated paths, not game outcomes.

### Story format must be stable before Godot binding
**Risk:** The v1.0 backlog includes format-breaking items (Chapters, Cross-Story Persistent State, Asset Association Layer) that add new top-level schema fields. If any ship post-v1.0, they break existing Godot plugins that have already been built against the frozen format.
**Mitigation:** All three format-breaking features are in the v1.0 Critical Path section of the internal roadmap and must ship before the Signal API is frozen and the GDScript engine is written. Versioning discipline (no v1.0 tag until the path is clear) is the primary guard.
**Impact:** High — a format change post-v1.0 forces a major version bump on the Godot plugin and breaks story authoring assumptions.
**Update 2026-09-20:** The Chapters design is now the largest freeze item: `meta.saga_id`, `saga_title`, `chapter_label` and ending-node `next_story`, `exports`, `chapter_transition`, `saga_end` (decision log 2026-09-20). None of it is implemented yet.

### Chapters scope growth can stall the Critical Path again
**Risk:** Chapters started as the RFC's 9-step outline and is now a saga home screen, destructive replay, persistent entry seeds, debug unlock with a seed argument, cross-file validation and two web renderers per screen. The 2026-09-19 retro found zero Critical Path commits in four months because easier work won every session; a feature this size can recreate that stall by never reaching a first mergeable slice.
**Mitigation:** Spec first, then two sequential plans (decision log 2026-09-20). Plan 1 (format, Python, CLI) ships and merges on its own before web parity starts, and Chapters stays ordered ahead of everything else on BOARD.md.
**Impact:** High — Chapters gates the Signal API and the GDScript engine, so a stall here delays v1.0.

### Local-only design docs are invisible to worktrees and other branches
**Risk:** Specs, plans and RFCs are local-only (untracked), so they exist only in the main checkout. A git worktree or a fresh clone will not have them, and the July Chapters spec survived only on an unmerged remote branch, where it was missed until 2026-09-20 (POSTMORTEMS 2026-09-20).
**Mitigation:** Implement in the main checkout rather than a worktree (chosen 2026-09-20), and run the PROCESS.md prior-art check (`git log --all`) before starting a spec.
**Impact:** Medium — a missed or unreachable design doc costs a redesign or a stalled implementation session, not a correctness bug.

### No validator check for insets on ending nodes
**Risk:** Authors can place insets on ending nodes and they will be silently dropped (see POSTMORTEMS.md). The validator doesn't warn.
**Mitigation:** Known after the 2026-05 postmortem. Manual awareness is the current mitigation.
**Impact:** Low — content loss is silent, not a crash; affects new stories if the authoring convention isn't followed.

---

## Resolved

### Vendored plugin cache edits silently reverted by update *(resolved 2026-07-09)*
Behavior-changing edits made directly to the `superpowers` plugin's cached skill files (2026-05-21) were silently overwritten by a later plugin update, with no error or notification — the guidance was effectively absent for ~7 weeks before an unrelated audit caught it. Redone via this project's own git-tracked `CLAUDE.md` instead, paired with a rerunnable audit script (`scripts/audit_skill_tokens.py`) so future drift is checkable rather than assumed. See the internal decision log and POSTMORTEMS.md (2026-07-09).

### `--dim` contrast below WCAG AA *(resolved 2026-05)*
The terminal mode `--dim` CSS variable was #4a5870 (2.4:1 contrast — below AA threshold). Fixed to #6a7e99 (4.6:1) as part of the accessible mode work.

### Ending node insets dropped silently *(resolved 2026-05-21)*
Four public stories had insets on ending nodes that were silently discarded at runtime. Fixed by converting to overlays in all affected stories. See POSTMORTEMS.md.

### Pygame spike blocking web player *(resolved 2025)*
A native renderer spike was consuming research time without clear payoff. Abandoned in favour of the web player, which covered the same use case. See POSTMORTEMS.md.
