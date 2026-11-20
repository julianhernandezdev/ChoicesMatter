# Runbook

Operational procedures for common tasks.

---

## Add a Story

1. Create a `.json` file following the story format (reference: CLAUDE.md or GameConcept.md)
2. Drop it into `/stories/` or a subfolder (e.g. `stories/horror/`)
3. Run `python main.py` — the story appears in the picker automatically
4. Validate schema and reachability:
   ```bash
   python scripts/validate_story.py stories/your_story.json
   ```
5. If publishing to the web player, sync the manifest and commit:
   ```bash
   python scripts/sync_stories.py
   git add web/stories.json && git commit -m "chore: sync web story manifest"
   ```

---

## Validate a Story

Single file:
```bash
python scripts/validate_story.py stories/your_story.json
```

Multiple files:
```bash
python scripts/validate_story.py stories/**/*.json
```

Exit codes: `0` = clean, `1` = errors found, `2` = no arguments passed.

Checks: schema correctness, `start_node` reachability, dead-end non-ending nodes.

---

## Sync the Web Story Manifest

Run after adding, removing, renaming, or moving stories that should appear in the web player. Skips CLI-only folders (see `SKIP_DIRS` in the script) by default.

```bash
python scripts/sync_stories.py
```

Writes `web/stories.json`. Commit the result:
```bash
git add web/stories.json && git commit -m "chore: sync web story manifest"
```

---

## Run Tests

```bash
pytest
```

This includes JS engine parity checks — `tests/test_web_engine.py` shells out to `node --input-type=module` per assertion to exercise `web/engine.js` directly, so no separate JS test command is needed. Requires Node.js on `PATH`.

`tests/test_web.py` (Playwright) runs against the **deployed** GitHub Pages site, not your checkout, so it can neither confirm nor break on local changes, and 13 of its tests currently fail on `main`. For a fast local run use `pytest --ignore=tests/test_web.py` (about 5 s). To check a local web change in a browser, serve the repo root — `python -m http.server 8766`, then open `http://localhost:8766/index.html` (`index.html` is at the root, not in `web/`) — and drive it with Playwright; stop the server afterwards.

---

## Debug a Story (Author Mode)

CLI — show non-`visited_` flags below choices:
```bash
python main.py --debug
```

CLI — show all flags including `visited_*`:
```bash
python main.py --all
```

Web player — press `-` to cycle: off → author flags → all flags.

---

## Deploy the Web Player

Deploys automatically via GitHub Actions on push to `main`. No manual steps needed.

Live at: https://julianhernandezdev.github.io/ChoicesMatter/

---

## Clear Save Data

From the story picker: press `C`, then confirm with `Y`. Clears all `.save.json` and `.gallery.json` files.

Or manually:
```bash
# Clear active saves only
rm saves/*.save.json

# Clear gallery too
rm saves/*.gallery.json
```

---

## Run the Settings Screen

From the story picker: press `S`. Covers typewriter toggle, speed presets, and punctuation pause values. Writes `settings.json` on confirm.

---

## Toggle Typewriter (Session-only)

From the story picker: press `T`. Toggles typewriter on/off for the current session without writing to `settings.json`.

---

## Run the Skill-Token Audit

Measures whether the exploration-tooling guidance in CLAUDE.md (semble-first, no redundant re-reads) is actually changing agent tool-use behavior over time, by scanning this project's own Claude Code transcript history.

```bash
python scripts/audit_skill_tokens.py
```

Read-only against `~/.claude/projects/<project-slug>/` — the only file it ever writes is its own baseline snapshot.

- **First run:** prints a full report and saves a baseline to `docs/projectmanagement/skill-token-baseline.json`.
- **Subsequent runs:** prints the same report plus a delta against that saved baseline (Read:semble call ratio, Read's share of exploration-tool tokens, fruitless Grep/Glob rate, true-duplicate Read count).

To audit a different project's transcripts:
```bash
python scripts/audit_skill_tokens.py --transcripts-dir path/to/transcripts
```

See the internal decision log (2026-07-09 — durable guidance belongs in CLAUDE.md, not a vendored plugin) and POSTMORTEMS.md for why this script exists.
