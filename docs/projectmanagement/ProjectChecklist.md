# ProjectChecklist.md
## Choices Matter — Build Checklist

---

## Epic 1: Project Setup
- [x] Create `/stories/` directory
- [x] Create `/saves/.gitkeep`
- [x] Write `.gitignore`
- [x] Write `requirements.txt`
- [x] Write `ProjectManagement.md`
- [x] Write `ProjectChecklist.md`
- [x] Write `CLAUDE.md`
- [x] Write `README.md`

---

## Epic 2: Story Data Layer (`src/story.py`)
- [x] `StoryValidationError`
- [x] `Choice` dataclass (`label`, `next`, `requires`, `sets`)
- [x] `Overlay` dataclass (`text`, `requires`, `position`)
- [x] `Node` dataclass (`text`, `choices`, `overlays`, `is_ending`, `ending_type`)
- [x] `Story` dataclass
- [x] `StoryLoader.discover()`
- [x] `StoryLoader.load()` + full validation

---

## Epic 3: Save System (`src/save.py`)
- [x] `SaveState` dataclass (includes `state: dict[str, bool]` for flags)
- [x] `SaveState.to_dict()`
- [x] `SaveState.from_dict()`
- [x] `SaveManager.__init__()`
- [x] `SaveManager.save_path()`
- [x] `SaveManager.has_save()`
- [x] `SaveManager.load()`
- [x] `SaveManager.write()`
- [x] `SaveManager.delete()`

---

## Epic 4: Display Layer (`src/display.py`)
- [x] `Display.__init__()` — loads settings via `config.py`
- [x] `show_title_screen()`
- [x] `show_story_picker()`
- [x] `show_no_stories()`
- [x] `show_picker_error()`
- [x] `show_node(story_title, node_text)` — story panel only
- [x] `show_choices(choices, before_overlays, after_overlays)` — overlays wrap choice list
- [x] `show_ending(node_text, ending_type, overlays)` — overlays before ending panel
- [x] `show_save_indicator()`
- [x] `_render_overlay(text)` — style driven by `config.py`
- [x] `prompt_story_select()`
- [x] `prompt_continue_or_new()`
- [x] `prompt_choice()`
- [x] `prompt_play_again()`

---

## Epic 5: Game Engine (`src/engine.py`)
- [x] `Engine.__init__()` — initializes `_state`, `_history`, `_current_node`
- [x] `Engine._resolve_start()` — saves or fresh start
- [x] `Engine.run()` — main loop with flag filtering and overlay split
- [x] `Engine._advance()` — applies `sets`, autosaves
- [x] `Engine._reset()` — clears state, history, deletes save
- [x] `Engine._flag_check(requires)` — reusable for choices and overlays
- [x] Ending detection + save delete
- [x] Play-again: True → reset + continue
- [x] Play-again: False → return to picker

---

## Epic 6: Entry Point (`main.py`)
- [x] `main()` outer loop
- [x] `StoryLoader.discover()` + build picker entries
- [x] Lazy load on selection + `StoryValidationError` → mark `-ERROR`
- [x] On valid selection → `Engine.run()`
- [x] Q → quit
- [x] Empty `/stories/` → no-stories message + exit
- [x] Missing `/stories/` → create + no-stories message

---

## Epic 7: Settings / Config (`src/config.py`)
- [x] `config.py` — loads `settings.json`, deep-merges with hardcoded defaults
- [x] `settings.example.json` — committed template
- [x] `settings.json` — gitignored (per-user)
- [x] Overlay style options: `color`, `dim`, `italic`, `bold`, `underline`, `strike`, `prefix`

---

## Epic 8: Stories
- [x] `stories/the_locked_room.json` — v1.2, flag-gated watch mechanic, 3 overlays
- [x] `stories/the_last_train.json` — v1.1, flag-gated escape route, 2 overlays
- [x] `stories/watcher_in_the_light.json` — horror, multiple flags, 7 overlays, 3 endings
- [x] `examplestory.json` (root) — shareable copy of The Last Train

---

## Epic 9: Tests
- [x] `tests/conftest.py` — `saves_dir` fixture
- [x] `test_story.py` — valid load, missing fields, bad start_node, bad choice next
- [x] `test_story.py` — Overlay parsed correctly (text, requires, position, defaults)
- [x] `test_story.py` — Node with no overlays → empty list
- [x] `test_save.py` — full SaveManager + SaveState round-trip including `state` field
- [x] `test_config.py` — defaults when file missing, partial override, malformed JSON fallback
- [x] `test_engine.py` — advance, autosave, ending deletes save, play-again reset
- [x] `test_engine.py` — unmet requires hides choice
- [x] `test_engine.py` — met requires shows choice
- [x] `test_engine.py` — sets applies flag after advance
- [x] `test_engine.py` — state saved and restored from save
- [x] `test_engine.py` — overlay with unmet requires not passed to show_choices
- [x] `test_engine.py` — overlay with met requires passed to show_choices
- [x] `test_engine.py` — before/after overlays split correctly
- [x] `test_engine.py` — reset clears flag state between play-throughs

---

## Epic 10: Ending Gallery (`src/gallery.py`)
- [x] `GalleryManager` — reads/writes `saves/<story_id>.gallery.json`
- [x] `record_ending(story_id, node_id)` — accumulates found endings across runs
- [x] Gallery survives save deletion — separate file, cleared only via explicit wipe
- [x] Story picker shows `X/Y endings` (or `X/?` for single-ending stories)
- [x] `test_gallery.py` — round-trip, accumulation, clear

---

## Epic 11: Non-Boolean State
- [x] `_state` widened to `dict[str, bool | int | str]`
- [x] `sets` supports delta strings (`"+1"`, `"-2"`) — missing key defaults to 0
- [x] `requires` supports int threshold (≥), str exact, `list[str]` membership
- [x] `StoryLoader` validates all new types; 17 new tests

---

## Epic 12: Advanced Story Format
- [x] `scene` key on nodes — dim Rule header; carries forward until overridden
- [x] `choice_number_color` on nodes; `color` on choices — two-level fallback to `cyan`
- [x] `obfuscated: true` on choices — renders `[REDACTED ██████]`
- [x] `insets` — styled lines inside the story panel (before/after, named styles, requires)
- [x] `warnings` in meta — yellow panel before launch; `[!]` in picker
- [x] `auto_visited_flags` in meta — auto-sets `visited_<node_id>` on every node enter
- [x] `est_time` in meta — shown in picker; auto-computed from word count if omitted

---

## Epic 13: Scripts & Developer Tools
- [x] `scripts/validate_story.py` — schema, reachability, dead-end detection; multi-file CLI; exit codes 0/1/2
- [x] `scripts/sync_stories.py` — walks stories/, skips examples/ and showcase/, writes web/stories.json
- [x] `tests/test_validate_story.py` — 9 tests

---

## Epic 14: Web Player
- [x] `index.html` — GitHub Pages entrypoint; ES module script tag
- [x] `web/app.js` — rendering, screen state, folder nav, settings UI, typewriter integration
- [x] `web/engine.js` — pure game logic (no DOM); mirrors Python engine
- [x] `web/storage.js` — localStorage save/gallery
- [x] `web/typewriter.js` — character-by-character animation, settings persistence
- [x] `web/style.css` — terminal aesthetic
- [x] `web/stories.json` — static manifest
- [x] `tests/test_web_player_assets.py` — asset presence checks

---

## Epic 15: Subfolder Navigation & Settings Screen
- [x] `StoryLoader.discover_with_folders()` — returns root paths + folder map
- [x] `_build_top_level_entries()` / `_run_folder_picker()` in `main.py`
- [x] `Display.show_settings_screen()` — typewriter speed + pauses; writes `settings.json`
- [x] `Display.show_content_warnings()` — pre-launch warning panel
- [x] `prompt_story_select()` returns `"settings"`, `"clear"`, `"toggle_typewriter"` sentinels

---

## Epic 17: Debug / Author Mode
- [x] `main.py` — `argparse` with `--debug` / `--all`; passes `debug` dict to `Display`
- [x] `src/display.py` — accepts `debug` dict; renders flag panel in `show_choices()`; appends style tags in `show_node()`; panel suppressed on endings, picker, settings
- [x] `web/app.js` — `debugMode` state var, `-` key handler cycling off → author → all; debug rendering in `renderGame()`
- [x] `web/style.css` — `.debug-panel`, `.debug-tag`, `.debug-hint` classes
- [x] `tests/test_display.py` — debug panel rendering, style tag output
- [x] `tests/test_web.py` — Playwright tests for web debug mode (run after deploy)

---

## Epic 16: Package Structure
- [x] `src/` package — all engine modules moved from root; relative imports inside `src/`
- [x] `main.py` uses `from src.X import ...`
- [x] `scripts/` package — `__init__.py`, `validate_story.py`, `sync_stories.py`
- [x] All tests updated to `from src.X import ...` / `from scripts.validate_story import ...`
- [x] `CLAUDE.md` updated with new module paths

---

## Epic 18: WCAG 2.1 Level AA Accessible Mode (Web Player)
- [x] `web/style.css` — `--dim` contrast fix (#4a5870 → #6a7e99); `prefers-reduced-motion` cursor animation guard; full `body.reader-mode` theme (Newsreader font, `--r-*` custom properties, 3px double-ring focus indicator)
- [x] `web/typewriter.js` — `accessible_mode: null` in settings schema; `startTypewriter()` skips animation on `prefers-reduced-motion`
- [x] `web/app.js` — `isAccessibleMode()`, `toggleAccessibleMode()`, `sessionAccessible`; `setPageTitle()` in all 16 renderers; 8 accessible renderers (`renderAccessiblePicker/Folder/Resume/Warnings/Game/Ending/Settings/SpeedPresets`); `SETTINGS_ROWS` expanded to 9 with accessible_mode row
- [x] `settings.example.json` — `"accessible_mode": null` added
- [x] `CLAUDE.md` — Accessible Mode section (priority chain, dispatch pattern, renderer list, focus management rule)
- [x] `accessibility/wcag-implementation.md` — 26-criterion WCAG 2.1 AA implementation guide
- [x] `accessibility/screen-reader-testing.md` — NVDA/VoiceOver test scripts for all 8 screens
- [x] `accessibility/accessible-renderer-patterns.md` — eight-step checklist and reference tables for new accessible renderer authoring
