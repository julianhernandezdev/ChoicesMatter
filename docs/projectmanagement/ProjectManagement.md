# ProjectManagement.md
## Choices Matter — Epics, Stories & Tasks

---

### Epic 1: Project Setup
**Goal:** Repository scaffolding, dependencies, and project documentation.

#### Story 1.1: Initialize Project Structure
- [x] Task: Create `/stories/` directory
- [x] Task: Create `/saves/` directory with `.gitkeep`
- [x] Task: Write `.gitignore` (Python standard + project docs + saves/ + settings.json)
- [x] Task: Write `requirements.txt` (`rich`, `pytest`)

#### Story 1.2: Project Documentation
- [x] Task: Write `ProjectManagement.md` (this file)
- [x] Task: Write `ProjectChecklist.md`
- [x] Task: Write `CLAUDE.md`
- [x] Task: Write `README.md`

---

### Epic 2: Story Data Layer (`src/story.py`)
**Goal:** Data models, JSON loader, and validation.

#### Story 2.1: Data Models
- [x] Task: Implement `Choice` dataclass (`label`, `next`, `requires`, `sets`)
- [x] Task: Implement `Overlay` dataclass (`text`, `requires`, `position`)
- [x] Task: Implement `Node` dataclass (`text`, `choices`, `overlays`, `is_ending`, `ending_type`)
- [x] Task: Implement `Story` dataclass (`id`, `title`, `version`, `author`, `start_node`, `nodes`, `source_path`)
- [x] Task: Implement `StoryValidationError(Exception)`

#### Story 2.2: StoryLoader
- [x] Task: Implement `StoryLoader.discover(stories_dir: Path) -> list[Path]`
- [x] Task: Implement `StoryLoader.load(path: Path) -> Story`
  - Parse JSON, validate meta fields present
  - Validate `start_node` exists in `nodes`
  - Validate each node has `text` and `choices`
  - Validate each choice `next` references an existing node
  - Parse `overlays` from each node (text, requires, position — defaults to "after")

---

### Epic 3: Save System (`src/save.py`)
**Goal:** Persistent save state per story (one slot per story, keyed by `story_id`).

#### Story 3.1: SaveState Model
- [x] Task: Implement `SaveState` dataclass (`story_id`, `current_node`, `history`, `state`, `timestamp`)
- [x] Task: Implement `SaveState.to_dict() -> dict`
- [x] Task: Implement `SaveState.from_dict(data: dict) -> SaveState` (classmethod)

#### Story 3.2: SaveManager
- [x] Task: Implement `SaveManager.__init__(saves_dir: Path)` — creates dir if missing
- [x] Task: Implement `SaveManager.save_path(story_id: str) -> Path`
- [x] Task: Implement `SaveManager.has_save(story_id: str) -> bool`
- [x] Task: Implement `SaveManager.load(story_id: str) -> SaveState | None`
- [x] Task: Implement `SaveManager.write(state: SaveState) -> None` — stamps timestamp
- [x] Task: Implement `SaveManager.delete(story_id: str) -> None` — silent if no file

---

### Epic 4: Display Layer (`src/display.py`)
**Goal:** All `rich` rendering. Zero game logic. Nothing else imports `rich`.

#### Story 4.1: Setup
- [x] Task: Implement `Display.__init__()` — initialize `rich.Console`, load settings via `config.py`

#### Story 4.2: Story Picker
- [x] Task: Implement `Display.show_title_screen()` — branded panel on launch
- [x] Task: Implement `Display.show_story_picker(entries: list[dict]) -> None` — numbered list + `-ERROR` markers + `Q. Quit`
- [x] Task: Implement `Display.show_no_stories()` — "No stories loaded" message
- [x] Task: Implement `Display.show_picker_error(name: str, message: str) -> None` — inline error for bad story

#### Story 4.3: In-Game Rendering
- [x] Task: Implement `Display.show_node(story_title, node_text)` — story panel only
- [x] Task: Implement `Display.show_choices(choices, before_overlays, after_overlays)` — overlays wrap choice list
- [x] Task: Implement `Display.show_ending(node_text, ending_type, overlays)` — overlays before ending panel
- [x] Task: Implement `Display.show_save_indicator()` — subtle "✓ Progress saved." line
- [x] Task: Implement `Display._render_overlay(text)` — style from config

#### Story 4.4: Input Prompts
- [x] Task: Implement `Display.prompt_story_select(count: int) -> int | None` — `None` = quit
- [x] Task: Implement `Display.prompt_continue_or_new() -> bool` — `True` = continue
- [x] Task: Implement `Display.prompt_choice(choices: list) -> int` — validated 1-based index, re-prompts on bad input
- [x] Task: Implement `Display.prompt_play_again() -> bool`

---

### Epic 5: Game Engine (`src/engine.py`)
**Goal:** Game loop. Coordinates story/save/display. No rendering, no I/O — delegates everything.

#### Story 5.1: Engine Setup
- [x] Task: Implement `Engine.__init__(story, save_manager, display)` — `_state`, `_history`, `_current_node`
- [x] Task: Implement `Engine._resolve_start()` — load save or fresh start

#### Story 5.2: Game Loop
- [x] Task: Implement `Engine.run()` — main loop with flag filtering; separate code paths for ending vs non-ending
- [x] Task: Implement `Engine._advance(choice)` — apply `sets`, append history, autosave, show indicator
- [x] Task: Implement `Engine._reset()` — clear `_state`, `_history`, reset node, delete save
- [x] Task: Implement `Engine._flag_check(requires: dict) -> bool` — reusable for choices and overlays

#### Story 5.3: Ending Handling
- [x] Task: Detect ending node (or empty visible choices) in `run()`
- [x] Task: Pass filtered overlays to `show_ending`; delete save
- [x] Task: Handle play-again: `True` → `_reset()` + continue loop; `False` → return

---

### Epic 6: Entry Point (`main.py`)
**Goal:** Outer story-picker loop. Glues all components together.

#### Story 6.1: Story Picker Loop
- [x] Task: Implement `main()` — outer `while True` loop
- [x] Task: Call `StoryLoader.discover()`, build picker entries
- [x] Task: On selection: call `StoryLoader.load()`, catch `StoryValidationError`, mark `-ERROR`, stay in picker
- [x] Task: On valid selection: instantiate `Engine`, call `engine.run()`
- [x] Task: On `Q`: clean exit

#### Story 6.2: Edge Cases
- [x] Task: Empty `/stories/` directory → `display.show_no_stories()` + exit
- [x] Task: `/stories/` directory doesn't exist → create it, show no-stories message

---

### Epic 7: Settings / Config (`src/config.py`)
**Goal:** Per-user visual style for overlays. Gitignored `settings.json`, committed `settings.example.json`.

- [x] Task: Implement `config.py` — loads `settings.json`, deep-merges with hardcoded defaults
- [x] Task: Write `settings.example.json` — committed template with all options documented
- [x] Task: Add `settings.json` to `.gitignore`
- [x] Task: Expand style options: `color`, `dim`, `italic`, `bold`, `underline`, `strike`, `prefix`

---

### Epic 8: Stories
**Goal:** Three complete stories demonstrating all engine features.

- [x] Task: `stories/the_locked_room.json` — v1.2; logbook flag gates watch mechanic; 3 overlays
- [x] Task: `stories/the_last_train.json` — v1.1; Mira call gates escape route; 2 overlays
- [x] Task: `stories/watcher_in_the_light.json` — horror; multiple flags; 7 overlays across 6 nodes; 3 endings
- [x] Task: `examplestory.json` (root) — shareable copy of The Last Train with overlays

---

### Epic 9: Tests
**Goal:** pytest coverage for all layers.

#### Story 9.1: Fixtures (`tests/conftest.py`)
- [x] Task: `saves_dir` fixture — empty `tmp_path / "saves"`

#### Story 9.2: StoryLoader Tests (`tests/test_story.py`)
- [x] Task: Valid story loads with all fields correct
- [x] Task: Missing meta field → `StoryValidationError`
- [x] Task: `start_node` not in `nodes` → `StoryValidationError`
- [x] Task: Node missing `text` → `StoryValidationError`
- [x] Task: Node missing `choices` → `StoryValidationError`
- [x] Task: Choice `next` references nonexistent node → `StoryValidationError`
- [x] Task: `discover()` returns only `.json` files, ignores others
- [x] Task: `Overlay` fields parsed correctly (text, requires, position)
- [x] Task: `position` defaults to `"after"` when omitted
- [x] Task: Node with no `overlays` key → empty list

#### Story 9.3: SaveManager Tests (`tests/test_save.py`)
- [x] Task: `has_save()` → `False` when no file exists
- [x] Task: `write()` then `has_save()` → `True`
- [x] Task: `write()` then `load()` round-trips all fields including `state`
- [x] Task: `delete()` removes the save file
- [x] Task: `delete()` is silent when no file exists
- [x] Task: `load()` → `None` when no file exists

#### Story 9.4: Config Tests (`tests/test_config.py`)
- [x] Task: Default settings returned when file missing
- [x] Task: Valid `settings.json` merges over defaults (partial override works)
- [x] Task: Malformed JSON falls back to defaults

#### Story 9.5: Engine Tests (`tests/test_engine.py`)
- [x] Task: Advance moves to next node
- [x] Task: Autosave called on advance
- [x] Task: Ending deletes save
- [x] Task: Play-again True → resets to start
- [x] Task: Play-again False → run() returns
- [x] Task: Unmet `requires` hides choice from `show_choices`
- [x] Task: Met `requires` shows choice in `show_choices`
- [x] Task: `sets` applies flag after advance (flag end reachable)
- [x] Task: State saved and restored from save file (flag-gated choice reachable after reload)
- [x] Task: Overlay with unmet `requires` not passed to `show_choices`
- [x] Task: Overlay with met `requires` passed to `show_choices` after_overlays
- [x] Task: Before and after overlays split correctly into separate args
- [x] Task: `_reset()` clears flag state between play-throughs

---

### Epic 18: WCAG 2.1 Level AA Accessible Mode (Web Player)
**Goal:** Reader mode alongside terminal mode, auto-detected from OS accessibility preferences. 26 WCAG 2.1 AA criteria addressed across the web viewer.

#### Story 18.1: Terminal Mode Hardening
- [x] Task: Fix `--dim` contrast (#4a5870 → #6a7e99, 2.4:1 → 4.6:1) in `web/style.css`
- [x] Task: Add `@media (prefers-reduced-motion)` cursor animation guard in `web/style.css`
- [x] Task: Skip typewriter animation on `prefers-reduced-motion` — early return in `startTypewriter()` in `web/typewriter.js`
- [x] Task: Add `setPageTitle()` helper and call it in all 8 terminal renderers in `web/app.js`
- [x] Task: Add `aria-label="Open keyboard"` to all `.mobile-keyboard-btn` elements in `web/app.js`

#### Story 18.2: Mode Detection System
- [x] Task: Add `accessible_mode: null` to `TYPEWRITER_DEFAULTS` and `loadTypewriterSettings()` in `web/typewriter.js`
- [x] Task: Add `sessionAccessible` module var, `isAccessibleMode()`, `toggleAccessibleMode()` in `web/app.js`
- [x] Task: Wire A key toggle at library screen; `if (isAccessibleMode()) return` in keydown handler

#### Story 18.3: Settings Expansion
- [x] Task: Expand `SETTINGS_ROWS` to 9 rows with section headings and accessible_mode row in `web/app.js`
- [x] Task: Add accessible_mode display, cycling, and settingsDraft handling to `renderSettings()`

#### Story 18.4: Reader Mode CSS
- [x] Task: Add Google Fonts `@import` for Newsreader at line 1 of `web/style.css`
- [x] Task: Add full `body.reader-mode` light paper theme with `--r-*` custom properties and 3px double-ring focus indicator

#### Story 18.5: Accessible Renderers
- [x] Task: Implement `renderAccessiblePicker()` with dispatch from `renderPicker()` and focus management
- [x] Task: Implement `renderAccessibleFolder()`, `renderAccessibleResume()`, `renderAccessibleWarnings()`
- [x] Task: Implement `renderAccessibleGame()` with semantic HTML, insets, overlays, choices, debug panel, focus management
- [x] Task: Implement `renderAccessibleEnding()` with ending type label and focus management
- [x] Task: Implement `renderAccessibleSettings()` and `renderAccessibleSpeedPresets()`

#### Story 18.6: Config & Documentation
- [x] Task: Add `"accessible_mode": null` to `settings.example.json`
- [x] Task: Add Accessible Mode section to `CLAUDE.md` (priority chain, dispatch pattern, renderer list, focus management rule)
- [x] Task: Create `accessibility/wcag-implementation.md` — 26-criterion WCAG 2.1 AA implementation guide
- [x] Task: Create `accessibility/screen-reader-testing.md` — NVDA/VoiceOver test scripts for all 8 screens
- [x] Task: Create `accessibility/accessible-renderer-patterns.md` — eight-step checklist and reference tables for new accessible renderer authoring
