# Architecture

What the system is shaped like and why. CLAUDE.md has the tactical detail (exact fields, exact method signatures) and changes with every feature; this file has the durable shape and changes rarely. If the two ever disagree, CLAUDE.md is more likely to be current — fix this file to match.

---

## System Overview

Choices Matter is a data-driven text-adventure engine with two independent runtime implementations of the same interpreter, reading the same story format:

```
                    stories/*.json  (data — no code)
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
      Python CLI engine         JS web engine
      (src/, main.py)           (web/engine.js, web/app.js)
      reference implementation  reference implementation
              │                       │
              ▼                       ▼
        terminal (rich)        browser (2 render modes:
                                terminal-style / reader/accessible)
```

Both are "reference implementations." The stated end goal (see CLAUDE.md's v1.0 definition) is a **third** runtime — a GDScript/Godot port — once the story format and engine semantics are stable enough to bind to. Every architectural choice below is implicitly evaluated against "does this stay portable to a third runtime," not just "does this work in Python and JS."

---

## Core Architectural Principles

These are the load-bearing decisions. Each is documented in full in the internal decision log; this is the index of *why the codebase is shaped like this* in one place.

1. **Content is data, never code.** All story content lives in `.json` under `/stories/`. The engine is a generic interpreter with zero domain knowledge of any specific story. Adding a story is a file drop, never a code change.
2. **One coordinator, one passive renderer.** `Engine` is the only module that owns game state and drives the loop. `Display` (Python) / the render functions (JS) never make decisions — they render what they're given and report input back. This split means the entire rendering layer (`rich` in Python, DOM in JS) could be swapped without touching game logic.
3. **Fail fast, at load time, never mid-game.** `StoryLoader` validates the full structural and type contract of a story before the engine ever sees it. A malformed story is a load-time error with a clear message, not a runtime crash three choices in.
4. **Dual-runtime parity is a tested invariant, not a hope.** Every engine-level feature added to Python must be ported to JS. `tests/test_web_engine.py` shells out to Node to exercise `web/engine.js` directly and asserts it against the same scenarios as the Python tests. Divergence between the two engines is treated as a bug, full stop — see RISKS.md.
5. **Settings/config as a single declarative registry, not hardcoded rendering.** `SETTINGS_SECTIONS` (mirrored in `src/config.py` and `web/app.js`) is the one source of truth for what settings exist, how they render, and how they reset. Adding a setting is a registry entry, not new rendering code in N places.
6. **Accessibility is a parallel first-class path, not a conditional layer.** The web player's reader/accessible mode is a fully separate set of `renderAccessible*()` functions dispatched at the top of each renderer, not `if` branches threaded through one renderer. See the Accessible Mode section of CLAUDE.md for the full priority chain and dispatch pattern.

---

## Module Map (Python CLI)

```
main.py
  └── StoryLoader (src/story.py)             loads + validates JSON
  └── Display (src/display.py)               all terminal rendering (only module that imports rich)
  └── Engine (src/engine.py)                  the coordinator
        └── Story (src/story.py)             data model, node resolver
        └── SaveManager (src/save.py)        read/write save state
        └── GalleryManager (src/gallery.py)  record + persist found endings
        └── corruption (src/corruption.py)   resolves {corrupt} spans → TextSegments
        └── Display (src/display.py)         render calls only
```

`src/config.py` is imported only by `src/display.py` (settings drive rendering, nothing else needs them).

## Module Map (JS Web)

```
index.html
  └── web/app.js         rendering, screen state, folder nav, settings UI, mode dispatch
        └── web/engine.js       pure game logic (no DOM) — mirrors src/engine.py + src/story.py
        └── web/storage.js      localStorage save/gallery (mirrors src/save.py + src/gallery.py)
        └── web/typewriter.js   character animation + corruption scramble/resolve rendering
        └── web/style.css       terminal theme + reader-mode theme (both, dispatched by class)
```

There is no build step. `index.html` loads `web/app.js` as an ES module; the browser resolves the rest via native `import`.

---

## Data Flow

1. **Discovery** — `StoryLoader.discover()` (Python) / manifest read (JS, from `web/stories.json`, kept in sync by `scripts/sync_stories.py`) walks `/stories/` and lists available stories.
2. **Load + validate** — a selected story's JSON is parsed into typed models (`Story`, `Node`, `Choice`, `Overlay`, `Inset`) and validated against the full rule set in CLAUDE.md's Validation Rules section. Any failure raises `StoryValidationError` with enough detail to fix the JSON — lazily, only on selection, never blocking the picker for unrelated stories.
3. **Run loop** — `Engine` resolves the current node (fresh start or resumed save), filters choices/overlays/insets by `requires` against `_state`, renders via `Display`, applies `choice.sets` on advance, autosaves every advance, and detects ending nodes to trigger the ending screen + save deletion.
4. **Text resolution pipeline** (applies to node/inset/overlay text, in order): variable substitution (`{key}`) → inline conditionals (`{flag?a|b}`) → corruption span resolution (`{corrupt}…{/corrupt}`) → typewriter/pause token handling at render time. Each stage is a separate, independently testable pass — see the internal decision log (2026-07-03, 2026-07-04) for why the ordering is fixed.
5. **Persistence** — one active save per story (`saves/<story_id>.save.json`, or localStorage equivalent in the browser), deleted on ending/new-game/reset. A separate gallery file survives save deletion and accumulates found endings across runs.

---

## External Interfaces / Boundaries

| Boundary | Format | Notes |
|---|---|---|
| Story content | `.json` under `/stories/` | The only content-authoring surface. See CLAUDE.md for the full schema. |
| Python save state | `saves/<story_id>.save.json` | One slot per story. |
| Python ending gallery | `saves/<story_id>.gallery.json` | Survives save deletion. |
| Web save/gallery | `localStorage` | Mirrors the same two concerns via `web/storage.js`. |
| Per-user settings | `settings.json` (gitignored) / `localStorage` (web) | Deep-merged over hardcoded defaults; `settings.example.json` is the committed template. |
| Web story manifest | `web/stories.json` | Generated by `scripts/sync_stories.py`; must be committed after any story add/move. |
| External network | Google Fonts (`@import` in `web/style.css`, Newsreader for reader mode) | The only external network dependency in the entire project. See Dependencies.md. |

---

## Reusable Pattern (Template Candidate)

This section exists because this project's shape may get reused as a starting skeleton for future projects — see the project's `MEMORY.md` note on this. The domain-specific pieces (stories, nodes, choices) are not what's reusable; the *pattern* is:

- **Data-driven core + one owning coordinator + one passive renderer**, with the renderer's library (here, `rich`) isolated to a single importing module so it can be swapped without touching logic.
- **Dual-runtime parity enforced by tests**, when a project genuinely needs to run the same logic in two environments (here: terminal + browser) rather than accepting drift.
- **Fail-fast validation at the content/config boundary**, so malformed input is a clear load-time error, never a confusing mid-run crash.
- **A declarative settings/config registry** as the single source of truth for anything with more than a couple of user-configurable knobs, instead of hardcoding each one into N rendering call sites.
- **A `docs/projectmanagement/` knowledge base** (this directory) — Architecture, Decisions, Dependencies, Glossary, Postmortems, Risks, Runbook, Process, plus Backlog/Board/Changelog/Roadmap — structured enough to lift wholesale into a new project's own `docs/projectmanagement/` on day one.

When starting a new project from this skeleton: keep the coordinator/renderer split and the fail-fast validation from day one — they're cheap early and expensive to retrofit. Defer the dual-runtime parity requirement until (if) a second runtime is actually needed; building it speculatively for one runtime is pure overhead.
