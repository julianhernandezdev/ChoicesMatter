# Dependencies

Everything this project relies on outside its own code, and why. Update when a dependency is added, removed, upgraded with behavior implications, or a version floor changes.

---

## Python (CLI engine)

| Dependency | Declared in | Purpose | Pinning |
|---|---|---|---|
| `rich` | `requirements.txt` | All terminal rendering — panels, styled text, `Live` for the typewriter effect. Isolated entirely to `src/display.py`; see Architecture.md principle 2. | Unpinned (no version pin in `requirements.txt`) |
| `pytest` | `requirements.txt` | Test runner for the full Python suite, including the JS-parity tests (see below). | Unpinned |

No other third-party Python packages. Standard library only for everything else, including `scripts/audit_skill_tokens.py` (explicitly stdlib-only by design — see the internal decision log 2026-07-09).

**Interpreter:** developed against Python 3.14. No documented minimum version floor; `from __future__ import annotations` is used throughout, which requires 3.7+. If a floor is ever decided, record it here and in `pytest.ini`/CI config.

---

## JavaScript (Web player)

**Zero npm dependencies.** `web/` is vanilla JS (ES modules), HTML, and CSS — no bundler, no build step, no `package.json`. `index.html` loads `web/app.js` directly as a module; the browser resolves the rest via native `import`.

This is a deliberate simplicity choice, not an oversight — see Architecture.md. Introducing any JS dependency (a framework, a bundler) would be a significant architectural shift and should get a decision-log entry, not a quiet `npm install`.

---

## Dev / Test Tooling

| Tool | Purpose | Required for |
|---|---|---|
| Node.js | `tests/test_web_engine.py` shells out to `node --input-type=module` per assertion to exercise `web/engine.js` directly, so Python's `pytest` run exercises JS logic too. Must be on `PATH`. | Running the full test suite (`pytest`) |
| `git` | Version control. | Everything |
| A local HTTP server (any) | The web player is static files; opening `index.html` via `file://` breaks ES module imports (CORS). Any static server (`python -m http.server`, etc.) works for local dev. | Local web player testing |

No linter, formatter, or type-checker is currently configured for either Python or JS. (Worth a RISKS.md entry if this becomes a pain point — not yet.)

---

## External Network Dependencies

| Dependency | Where | Purpose | Failure mode if unavailable |
|---|---|---|---|
| Google Fonts (`fonts.googleapis.com`) | `@import` at the top of `web/style.css` | Loads the Newsreader font for reader/accessible mode. | Reader mode falls back to the browser's default serif — a graceful degradation, not a breakage. This is the **only** external network dependency in the entire project. |
| GitHub Pages | Hosts the deployed web player at `https://julianhernandezdev.github.io/ChoicesMatter/` | Static hosting for `index.html` + `web/`. | N/A for local dev; affects only the public deploy. **Note:** RUNBOOK.md describes this as deploying "automatically via GitHub Actions on push to main," but no `.github/workflows/` directory exists in this repo as of 2026-07-09 — the deploy is most likely configured via GitHub Pages' built-in branch-based deploy (repo Settings → Pages), not an Actions workflow file. Flagged here rather than silently corrected in RUNBOOK.md since the actual Pages configuration isn't visible from the local checkout — verify in the repo's GitHub Settings before relying on that line. |

No database, no backend service, no API keys, no third-party SDKs anywhere in the project.

---

## Story Content

Not a "dependency" in the software sense, but the story JSON files under `/stories/` are the one thing every part of the system depends on being well-formed — `StoryLoader` / the JS equivalent validate them at load time (see Architecture.md Data Flow). `scripts/validate_story.py` is the standalone tool for checking this outside of running the game; see RUNBOOK.md.
