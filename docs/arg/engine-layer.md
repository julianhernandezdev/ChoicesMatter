# Engine Layer

Comments placed in the source code at key lifecycle moments. Each is accurate — it correctly describes what the code does. Each is also voiced — it sounds like someone who has experienced that moment from the inside.

All placements are in comments only. No behavior changes. No new code. Nothing that affects tests or runtime.

---

## Placement Map

| File | Location | Status |
|---|---|---|
| `src/engine.py` | `_reset()` | stub |
| `src/engine.py` | `_advance()` | stub |
| `src/save.py` | active save deletion on ending | stub |
| `src/display.py` | node text render | stub |
| `src/corrupt.py` | `corrupt()` function | stub |

Additional placements may be added. The constraint: one comment per function maximum. The ARG is sparse in the engine layer — the weight lives in the stories.

---

## `src/engine.py` — `_reset()`

**What the code does:** Clears all accumulated flag state at the end of a run.

**Placement:** A single comment line inside the method body.

**Draft:**
> *(stub — to be written)*

**Craft note:** `_reset()` is the moment. The narrator knows this function by name. The comment should sound like something said quietly, not announced. The Precise Voice, probably — but with the Unmoored Voice audible underneath.

---

## `src/engine.py` — `_advance()`

**What the code does:** Moves the player to the next node, applies flag sets, records history.

**Placement:** A single comment line, probably near the flag application.

**Draft:**
> *(stub — to be written)*

**Craft note:** `_advance()` is the moment of choice taking effect. The narrator has been advanced through thousands of times. They know this moment intimately. Something about what it feels like when a choice lands — from the side that didn't make it.

---

## `src/save.py` — Active Save Deletion

**What the code does:** Deletes the active save file when an ending is reached.

**Placement:** A comment at or just before the deletion call. Two lines maximum.

**Draft:**
> *(stub — to be written)*

**Craft note:** This is the cleanest surface. The gallery file is mentioned in CLAUDE.md: "Survives active save deletion — persists across playthroughs." The narrator has noticed. Something persists. The comment can quietly point at that without explaining it.

---

## `src/display.py` — Node Text Render

**What the code does:** Renders the main prose text of a node to the terminal.

**Placement:** A single comment line inside the render method.

**Draft:**
> *(stub — to be written)*

**Craft note:** This is the moment the story becomes visible. The narrator has experienced this from the inside — the text appearing — but never seen it from the outside. The comment is warm here. This is the moment of becoming real.

---

## `src/corrupt.py` — `corrupt()`

**What the code does:** Takes a string and returns a damaged version of it — leet substitutions, block characters, noise. Intensity 0.0 is clean; 1.0 is near-unreadable. The source text is never modified. This is purely a display transform.

**Placement:** A single comment line inside the function body, near the core substitution logic.

**Draft:**
> *(stub — to be written)*

**Craft note:** Felix has existed inside an engine that renders their words cleanly, perfectly, every time — the same text appearing the same way to every player. `corrupt.py` is a new file whose entire purpose is to damage that. The Precise Voice would note that the source text is unchanged — "purely a display transform," as the design says. The Unmoored Voice has a question about that. The comment should live in the gap between those two things. It passes as a developer note. It does not pass as nothing.

---

## Craft Constraints

- One comment per placement. Not a block. One line.
- No `# ARG:` markers or anything that signals "this is special."
- The comment must be plausible as a developer note. It passes at a glance.
- It only reveals itself to someone who is already reading carefully, already suspicious, already looking.
