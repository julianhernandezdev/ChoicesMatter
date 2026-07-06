# Changelog

All notable changes to Choices Matter, most recent first.

---

## [Unreleased]

### Typewriter Defaults — Engine Parity
- **Fixed** `web/typewriter.js` `TYPEWRITER_DEFAULTS` disagreed with the CLI's real defaults (`src/config.py` `_DEFAULTS`) — web shipped `delay_ms: 20` and flat `100–200ms` punctuation pauses while the CLI used `delay_ms: 35` and `250–700ms` pauses tuned per character. Web now matches exactly: `delay_ms: 35`, `pauses: {".": 550, "!": 250, "?": 350, "…": 700, "—": 600}`
- **Fixed** `settings.example.json` had drifted from `src/config.py` `_DEFAULTS` (`page_size: 10` vs. `5`, `delay_ms: 40` vs. `35`, em-dash pause `800` vs. `600`) — reverted the template back in sync with the actual runtime defaults
- **Changed** `tests/test_web_settings.py::test_apply_defaults_typewriter` — updated hardcoded `delay_ms == 20` assertion to `35`

### Protagonist Name Prompt — Priority Bug Fix
- **Fixed** Blank name-prompt submission resolved the story's `name_default` before the settings-saved `player_name`, in both `main.py` (`_launch_story`) and `web/app.js` (`_resolvePlayerName`) — the opposite of the documented contract ("`name_default` is a fallback for when no saved `player_name` exists"). Since `settings.json` always resolves to at least `"Felix"`, this made `name_default` win unconditionally whenever a story declared one, silently shadowing the player's saved name
- **Added** `_resolve_player_name(entered, name_default, settings_name)` pure helper in `main.py` (mirrors the existing `_resolvePlayerName` shape in `web/app.js`); priority is now typed name > saved settings name > story `name_default`
- **Added** 4 regression tests in `tests/test_main.py` covering all four resolution branches

### Story Picker (Web Player Folder Parity)
- **Fixed** `scripts/sync_stories.py` — root-level stories (no subfolder) previously got a literal `"category": "uncategorized"` in `web/stories.json`, which made the web player bucket them into an `uncategorized/` folder instead of listing them flat like the CLI does. Root stories now get no `category` key at all, matching `StoryLoader.discover_with_folders()`'s root/folder split; `web/app.js`'s existing `entry.category || null` check already routes uncategorized entries to the flat top-level list, so no JS changes were needed
- **Synced** `web/stories.json` — `awaiting_response.json`, `the_last_customer_support_representative.json`, `the_last_train.json`, `the_one_eyed_guest.json` lost their `"uncategorized"` category and now render as flat top-level entries in both terminal and reader mode

### Story Picker
- **Added** Author/version byline row to the story picker — `by {author} · v{version}` printed dim beneath the title/status line, above the nodes/endings/time stats line (`Display.show_story_picker()`, `src/display.py`)
- **Added** `MAX_AUTHOR_LEN` (20) and `_truncate_author()` in `src/display.py` — author names longer than 20 chars truncate with `...` appended
- **Changed** `main.py`: `_load_story_info()` and `_build_entries()` now also return/carry `author` and `version` from `Story` (previously loaded but unused in the picker)
- **Fixed** Web player was missing the byline entirely (terminal mode and reader/accessible mode both) — the CLI-only feature above never got ported. Added `storyByline()` / `truncateAuthor()` helpers in `web/app.js`; wired into `renderPickerEntry()` (terminal, shared by library + folder screens), `renderAccessiblePicker()`, and `renderAccessibleFolder()` (including the `aria-label`)

### Story Metadata Cleanup
- **Normalized** `meta.author` across all 40 public stories to 3 canonical values: `"Choices Matter"` (35 stories), `"ChoicesMatterGPT"` (4 stories, all in `stories/ChoicesMatterGPT/`), and `"Fable"` (*The One-Eyed Guest*, unchanged by request)
- **Moved** `stories/ChoicesMatterGPT/awaiting_response.json` → `stories/awaiting_response.json`
- **Moved** `stories/the_cartographers_confession.json` → `stories/horror/the_cartographers_confession.json`
- **Synced** `web/stories.json` via `scripts/sync_stories.py` to reflect both moves
- **Normalized** `stories/horror/the_locked_room.json` `meta.author` from `"Choices Matter Dev"` to `"Choices Matter"` — missed by the pass above because the story was restored to the repo afterward

### Stories
- **Added** *The One-Eyed Guest* (`stories/the_one_eyed_guest.json`) — Nordic folk-horror one-shot: a homestead keeper faces a one-eyed wanderer's three guest-right tests across a single night; inside/outside staging split after the first test, diegetic vocabulary-glossing insets (`memory`/`warning` styles), `{corrupt}` spans tied to forbidden knowledge landing, an obfuscated final choice with its blindness narrated in-fiction, and three endings (good/neutral/bad). First story authored end-to-end by a Claude Fable 5 subagent from a brainstormed spec
- **Restored** *The Locked Room* (v1.3) and *The Watcher in the Light* (v1.1) to public release (`stories/horror/`) — both were excluded from the 2026-05 general release for graphic content; that call no longer applies and both validate cleanly via `scripts/validate_story.py`
- **Synced** `web/stories.json` — added *The One-Eyed Guest*, *The Locked Room*, and *The Watcher in the Light* via `scripts/sync_stories.py`

### Corruption Resolve Effect
- **Added** `resolve_style` param (`decay`/`cascade`) as the 4th positional param on `{corrupt:intensity:mode:resolve_style}` spans, and as an optional key on the node `corruption` field — an opt-in second typewriter phase that settles a corrupted span into its original clean text
- **Added** `cascade_reveal_order`, `effective_mode`, `effective_intensity` to `src/corruption.py`; mirrored in `web/app.js`/`web/typewriter.js`
- **Fixed** `settings.json`'s `corruption.mode` was documented as a fallback default but was never actually read by `resolve_corruption()` — now wired correctly via render-time resolution in `display.py`/`app.js`/`typewriter.js`
- **Changed** `corruption.intensity` (relabeled **Intensity Default**) no longer multiplies with story-defined intensity — a story-defined value now fully overrides it, matching `mode`'s existing override-or-default behavior. This is a player-visible behavior change, not just a bug fix.
- **Added** `corruption.intensity_multiplier` (relabeled **Intensity Multiplier**) — a new always-applied scalar restoring the global corruption-dampening accessibility control that the Intensity Default change would otherwise have removed
- **Added** `resolve_frames`, `resolve_delay_ms`, `cascade_stagger_ms` settings (fall back to `scramble_frames`/`scramble_delay_ms` when unset)
- **Changed** `player_name` setting relabeled **Player name Default** (label only — no behavior change, `meta.name_prompt` already overrides it)

### Default Settings & Section Registry
- **Added** `SETTINGS_SECTIONS` registry (Python `src/config.py`, web `web/app.js`) as single source of truth for all settings — each entry declares id, label, preserve flag, subscreen flag, config keys, and row descriptors
- **Changed** Settings screen rendering is now fully registry-driven on both platforms; web `SETTINGS_ROWS` is now a derived constant
- **Added** Generic section sub-screens (`_section_subscreen` / `renderSectionSubscreen` / `renderAccessibleSectionSubscreen`) — any `has_subscreen` section rendered from its row descriptors with no section-specific code
- **Added** Sub-screen nav keys: S (save+back), X (discard section+back), M (save+home), Q (discard all+home), R (reset section)
- **Added** `R` on main settings screen — checkbox selector to reset any combination of sections to defaults; `player_name` and `accessible_mode` are always preserved
- **Added** `apply_section_defaults` (Python) / `applyDefaults` (web) — deep-copy section keys from platform defaults
- **Fixed** `mode: "consistent"` added to `TYPEWRITER_DEFAULTS.corruption` in `web/typewriter.js` — corruption reset no longer produces `undefined` mode

---

## [v0.11.0] — 2026-07-04

### Corrupted Text Rendering
- **Added** `{corrupt}…{/corrupt}` inline span syntax in any text field (node prose, insets, overlays) with optional `intensity` (float 0–1) and `mode` (`consistent`/`random`) params — e.g. `{corrupt:0.8:random}text{/corrupt}`
- **Added** `Node.corruption` field (float or `{"intensity": float, "mode": string}`) as a node-level baseline; intensity inheritance chain: inline param → node baseline → global multiplier
- **Added** `CorruptedSpan` frozen dataclass and `TextSegments = list[str | CorruptedSpan]` — engine resolves spans into this annotation model before Display
- **Added** `src/corruption.py` — `resolve_corruption`, `corrupt_string`, `_text_seed`, `CHARSETS` (`blocks`, `symbols`, `diacritics`), stable LCG for consistent-mode position selection
- **Added** `corruption` block to `src/config.py` defaults and `settings.example.json` — 8 keys: `enabled`, `intensity`, `mode`, `charset`, `custom_chars`, `animate`, `scramble_frames`, `scramble_delay_ms`
- **Added** Settings sub-screen item 10 "Corruption →" in CLI settings screen — all 8 keys editable with validation
- **Changed** `_typewrite()` in `src/display.py` — rewrote for `TextSegments`; `CorruptedSpan` objects run scramble-then-settle animation when `animate: true`
- **Added** `resolveCorruption()` export to `web/engine.js` with seed parity to Python (`_textSeed` formula confirmed by cross-engine test)
- **Added** `_corruptString`, `_assembleText` to `web/app.js`; scramble-settle animation in `web/typewriter.js`; all `renderAccessible*()` renderers strip corruption (`enabled: false`)
- **Added** `education/23_corrupted_text.md` — full author feature doc
- **Updated** `CLAUDE.md` — `{corrupt}` span syntax, node field, inheritance chain, validation rules, settings block, reserved tokens note
- **Added** 27 tests in `tests/test_corruption.py`; 17 corruption tests in `tests/test_story.py`; 3 in `tests/test_config.py`; engine + display integration tests; 8 JS parity tests in `tests/test_web_engine.py`

### Stories
- **Added** *Awaiting Response* (`stories/ChoicesMatterGPT/awaiting_response.json`) — deep-space relay horror; player name appears uncorrupted inside a signal that predates the crew; showcases `{corrupt}` spans, node-level baseline, consistent/random modes, name prompt + VTS, system insets, echo overlays, obfuscated choice, and 5 endings
- **Added** `name_prompt` to *Ash and Receipts* (v1.2) — prompt "What's your name, Detective?", default "Marlowe"; `{player_name}` used in the folder-tab reveal and the caught-by-name confrontation
- **Added** `name_prompt` to *Dead Air* (v1.3) — prompt "The overnight host. What's your name?"; caller now speaks the player's name in the Line 3 reveal

### Docs
- **Updated** README — v0.11.0 banner; added `### Corrupted Text` section (syntax, node baseline, charsets, animate, accessible mode note); added corrupted text and typewriter rows to feature table
- **Updated** `education/feature-reference.md` — header updated to 23 features; row 23 added to Quick Lookup table; full §23 Corrupted Text section (story walkthrough, syntax, inheritance chain, Python + JS code path, validation, key references)
- **Rewritten** `Prompt.md` for v0.11 — 14 sections; §9 now covers inline corruption tokens with param table; §14 quick-reference card includes `{corrupt:i:m}…{/corrupt}`
- **Added** Variable Text Substitution, Protagonist Name Prompt, and `{pause}` token sections to README
- **Updated** CLAUDE.md with v1.0 Godot milestone definition and Extension Points entry
- **Added** `v1.0 Critical Path` section to ROADMAP.md (Chapters, Cross-Story State, Asset Layer, Signal API, GDScript Engine)

---

## [v0.10.0] — 2026-07-03

### Protagonist Name Prompt
- **Added** `meta.name_prompt` (string) and `meta.name_default` (string) — optional meta fields that trigger a pre-game name prompt screen
- **Added** `player_name` as a reserved state key — populated from the name prompt (or settings fallback) before the first node; available as `{player_name}` in any text field via VTS
- **Added** `"player_name": "Felix"` to `_DEFAULTS` in `src/config.py` and `settings.example.json`
- **Added** `Engine.__init__` `initial_state` param — seeds `_state` on new game and play-again resets via `_resolve_start()` and `_reset()`
- **Added** `Display.prompt_protagonist_name()` and `Display.show_name_required()` to `src/display.py`
- **Added** Settings row 9 "Player name" to CLI settings screen
- **Added** `renderNamePrompt()` and `renderAccessibleNamePrompt()` to `web/app.js` — terminal and accessible renderers, case-preservation in keydown handlers
- **Added** "Player name" settings row to web settings screen (`SETTINGS_ROWS`, `confirmSettingsEdit`, `startSettingsEdit`)
- **Added** `createRun(entry, saved, initialState)` third param to `web/engine.js`
- **Added** `player_name: "Felix"` to `TYPEWRITER_DEFAULTS` and both return paths of `loadTypewriterSettings()` in `web/typewriter.js`
- **Added** 13 new tests across `test_story.py`, `test_config.py`, `test_engine.py`, `test_display.py`, `test_web_engine.py`

### Variable Text Substitution
- **Added** `{key}` placeholder substitution in all text fields (node text, insets, overlays) — replaced at runtime with `str(state[key])`; missing keys leave placeholder intact
- **Added** `_SUBST_RE` + `_substitute_vars` static method to `src/engine.py`; runs before `_resolve_inline` so substituted values can appear inside `{flag?...}` conditional branches
- **Added** `substituteVars` export to `web/engine.js`; `currentView()` updated to chain substitution before `resolveInline`
- **Added** 8 unit + 4 integration tests in `tests/test_engine.py`; 8 unit + 4 integration tests in `tests/test_web_engine.py`
- **Added** Pre-roadmap design specs for Localization, TTS, and STT (`specs/`)

---

## 2026-05 (post-v0.9.0)

### Accessible Mode — WCAG 2.1 Level AA (Web Player)
- **Added** Reader mode alongside terminal mode — light paper theme (Newsreader font), semantic HTML, button-driven navigation
- **Added** Auto-detection via `prefers-reduced-motion` / `prefers-contrast: more` OS media queries
- **Added** Three-layer priority chain: session toggle → saved preference → auto-detect
- **Added** A key (session-only), Settings row 9 (persistent), accessible library button as toggle surfaces
- **Added** 8 accessible renderers: Picker, Folder, Resume, Warnings, Game, Ending, Settings, SpeedPresets
- **Fixed** `--dim` contrast ratio (#4a5870 → #6a7e99, 2.4:1 → 4.6:1 — AA compliant)
- **Added** `prefers-reduced-motion` cursor animation guard and typewriter skip
- **Added** `setPageTitle()` called in all 16 renderers (terminal + accessible)
- **Added** `accessible_mode: null` to `settings.example.json` and localStorage schema
- **Added** `accessibility/wcag-implementation.md` — 26-criterion WCAG 2.1 AA guide
- **Added** `accessibility/screen-reader-testing.md` — NVDA/VoiceOver test scripts
- **Added** `accessibility/accessible-renderer-patterns.md` — eight-step authoring checklist
- **Fixed** `renderAccessiblePicker` focus deferred to prevent Enter key synthetic click

### Inline Pause Token
- **Added** `{pause}` embed in node/ending `text` — injects mid-stream delay during typewriter playback
- **Added** `typewriter.pause_ms` config key (default 500 ms); stripped silently in non-typewriter mode

### Stories
- **Added** The Vulture Corridor v2.1 demo (`stories/horror/`) — remaster of the original
- **Added** The Moonlit Door (`stories/ChoicesMatterGPT/`)
- **Added** Ash and Receipts (`stories/ChoicesMatterGPT/`)
- **Added** The Lantern Rounds (`stories/ChoicesMatterGPT/`)
- **Added** Inline conditional text, content warnings, and dim italic style to The Last Train
- **Added** Insight threshold and `visited_` overlay to The Cartographer's Confession
- **Added** ORLA profile insets, list `requires`, and compliance gate to Customer Support
- **Fixed** Ending node inset bug — converted silently-dropped insets to overlays in 4 stories
- **Fixed** Remove invalid empty `warnings` field from ash_and_receipts
- **Added** Mobile capture flow for settings edits (touch devices)
- **Added** Story subfolders — `showcase/`, `horror/`, `examples/`, `ChoicesMatterGPT/` under `stories/`

### Docs
- **Added** `education/feature-reference.md` — master index of all 20 engine features with story cross-refs
- **Added** WCAG 2.1 AA compliance badge to README
- **Added** Accessible Mode section to CLAUDE.md
- **Added** AI use disclosure to README and CONTRIBUTING

---

## [v0.9.0] — 2026-05-19

---

## Earlier (Key Milestones)

### Conditional Inline Text
`{flag?shown if true|shown if false}` spans in any text field. False branch optional. Resolved at runtime. (CLI + Web)

### Non-Boolean State
Flag system extended to `bool | int | str`. Delta strings (`"+1"`, `"-2"`). Threshold `requires` (≥), string exact-match, list membership.

### Node Revisit Flags
Auto-set `visited_<node_id>` on every node entry. Reserved prefix; manually setting via `sets` raises validation error.

### Web Player (GitHub Pages)
Full browser-based play mode. Same story format, same flag system. `web/engine.js` mirrors Python engine. Live at https://julianhernandezdev.github.io/ChoicesMatter/

### Debug / Author Mode
`python main.py --debug` (or `--all`). Web player: `-` key cycles modes. Flag-state panel shown below choices.

### Subfolder Directory Navigation
Story picker supports subfolders. Top level shows root stories + named folder entries. Drills into a sub-screen.

### Settings Screen
In-game settings from picker via `S`. Typewriter toggle, speed presets, punctuation pauses. Writes `settings.json`.

### Obfuscated Choices
`"obfuscated": true` renders choice as `[REDACTED ██████]`. Player can still select; real label never shown.

### Content Warnings
`meta.warnings` list shown in yellow panel before launch. `[!]` indicator in picker.

### Scene Context Headers
`"scene"` key on nodes renders dim Rule header; carries forward until overridden.

### Choice Number Colour
Two-level: `choice.color` → node `choice_number_color` → default `cyan`.

### Node Reachability Validator
`scripts/validate_story.py` catches unreachable nodes and dead-end non-endings.

### Insets
Styled text inside the story panel (`before`/`after`, named styles, `requires`).

### WCAG 2.1 Terminal Mode Hardening
`--dim` contrast fix, `prefers-reduced-motion` guard, `aria-label` on keyboard buttons.
