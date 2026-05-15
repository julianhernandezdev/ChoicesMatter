Generate or update `Prompt.md` — a self-contained reference document for giving to other LLMs so they can write stories for this engine without access to the codebase.

**Goal:** `Prompt.md` must be usable as a drop-in system prompt or context block. It should be complete enough that an LLM with no other project knowledge can produce a valid, well-crafted story JSON file.

---

**Steps:**

1. Read `CLAUDE.md` in full. This is the authoritative engine spec — extract every field, rule, and constraint from it.

2. Read `settings.example.json`. This defines the named styles (`system`, `echo`, `memory`, `whisper`, `warning`) — document each with its visual meaning (color, prefix character, dim/italic/bold).

3. Read two stories that demonstrate a wide range of features. Good choices: `stories/dead_air.json` (insets, paired before/after, echo/memory/system styles, flag `sets`) and `stories/the_locked_room.json` (overlays with `requires`, flag system). Extract short verbatim snippets to use as examples in the document.

4. Write `Prompt.md` to the project root. Structure it as follows — every section is required:

   **Section 1 — What this is**
   One short paragraph: a Python CLI text adventure engine where all story content lives in JSON files. The player reads prose and picks numbered choices. Stories branch based on choices and flag state. No code changes needed to add a story.

   **Section 2 — File structure**
   Show the two top-level keys (`meta`, `nodes`) with a minimal skeleton and a brief prose explanation.

   **Section 3 — Meta fields**
   A table: field name | required | type | notes. Cover `id`, `title`, `version`, `author`, `start_node`, `est_time`, `warnings`. Include validation constraints (e.g. `id` must match `[A-Za-z0-9_.-]`).

   **Section 4 — Node fields**
   A table for the node object. Cover `text`, `choices`, `insets`, `overlays`, `is_ending`, `ending_type`, `scene`, `choice_number_color`. Note that an empty `choices` array is treated as an ending.

   **Section 5 — Choice fields**
   A table: `label`, `next`, `requires`, `sets`, `color`, `obfuscated`. For `requires` and `sets`: describe the flag dict format (`{"flag_name": true/false}`). For `color`: explain it overrides the node-level `choice_number_color`. For `obfuscated`: explain what the player sees.

   **Section 6 — Inset fields**
   A table: `text`, `position`, `style`, `requires`. Explain that insets render inside the story panel, separated by a dim rule. Before insets appear above the main text; after insets appear below.

   **Section 7 — Overlay fields**
   A table: `text`, `position`, `style`, `requires`. Explain that overlays render outside the story panel, around the choice list (`before` above choices, `after` below). On ending nodes, all overlays appear before the ending panel.

   **Section 8 — Named styles**
   A table for the five built-in styles. Columns: style key | color | prefix | modifiers | intended use.
   - `system` — white, dim, no prefix — timestamps, logs, status lines, diegetic data
   - `echo` — blue, dim italic, `~ ` prefix — recurring phrases, callbacks, things that resurface
   - `memory` — magenta, dim italic, `◈ ` prefix — personal memory, internal recall, what the character knows
   - `whisper` — cyan, dim italic, `✦ ` prefix — ambient atmosphere, the unnamed feeling in the room
   - `warning` — yellow, bold, `⚠ ` prefix — urgent callouts, danger signals
   - `""` (empty string) — dim italic, no prefix — generic aside, no semantic label needed
   Note: styles are user-configurable via `settings.json`; these are the committed defaults.

   **Section 9 — The flag system**
   Explain the three uses: `choice.requires` (hides a choice if flag not set), `choice.sets` (applies flag when choice is taken), `overlay.requires` / `inset.requires` (hides element if flag not set). Flags are booleans, persist across the run, and are saved with the save file. Give a brief worked example showing a flag set on one choice and used as a `requires` on an inset two nodes later.

   **Section 10 — Scene carry-forward**
   Explain that `scene` is a string label shown as a dim header above the story panel. Once set on a node, it carries forward silently to all subsequent nodes until a new `scene` is set. Authors only need to add `scene` when the location changes.

   **Section 11 — Validation rules**
   A bullet list of every constraint the engine enforces at load time. Copy from CLAUDE.md's Validation Rules section but phrase each rule as a "must" statement (e.g. "Every `next` value must reference a node ID that exists in `nodes`"). This is the most important section for preventing broken files.

   **Section 12 — Authoring guidance**
   Prose paragraphs (not bullets) covering:
   - When to use `insets` vs `overlays`: insets belong *inside* the scene (data the character can read, sensations they feel); overlays belong *outside* (atmosphere that surrounds the decision, the feeling in the gap between knowing and choosing).
   - When to use `requires` on overlays/insets vs on choices: use choice `requires` to hide options that would be incoherent given prior decisions; use overlay/inset `requires` to reward players who took a specific path with a callback or deeper context.
   - When to use `obfuscated`: on choices where the character acts without fully understanding what they're doing — irreversible decisions, things named only in retrospect. Overuse cheapens the mechanic; one per story is usually enough.
   - `choice_number_color` and per-choice `color`: use color to signal emotional register, not decoration. Red for danger, green for safety, yellow for uncertainty, dim/white for resignation. Consistency within a node matters more than variety.
   - Ending design: good/bad/neutral controls panel color (green/red/yellow). A story needs at least one ending; the `endings_found` gallery tracks them. Empty `choices` array triggers ending detection even without `is_ending: true`.

   **Section 13 — Complete working example**
   A full, valid, short story JSON (5–7 nodes, at least one flag, one inset, one overlay, one scene label, one ending). Use original prose — do not copy from existing stories. Include inline comments in the example using `//` notation *above* the relevant line (since JSON doesn't support comments, note at the top that these are explanatory and must be removed from real files). Actually — JSON does not support comments, so instead use a two-column annotated layout: show the JSON on the left as a fenced code block and a numbered annotation list below it that references specific lines by key name. Or simply write clean, commented JSON using `"_comment"` keys that explain the intent, with a note that `_comment` keys are ignored by the engine. Actually — do NOT use `_comment` keys because the engine doesn't strip them and they would pollute the data model. Just write clean JSON and add a prose walkthrough below the code block explaining what each section demonstrates.

   **Section 14 — Quick reference card**
   A single compact table of every optional field, where it lives, and a one-line note. This is the cheat sheet for experienced authors who just need to remember a field name.

5. After writing `Prompt.md`, print a brief summary listing each section and confirming it was populated, plus any information that couldn't be fully sourced (e.g. if a style wasn't found in the example files).

---

**Tone and length guidance for Prompt.md:**
- Write for an LLM reader, not a human reader. Precision beats warmth. Tables beat prose where structure is involved.
- Each section should be complete but not padded. If a rule has no exceptions, state it once and move on.
- The document should be usable as a system prompt — keep the total length under ~3000 tokens if possible, without sacrificing any required field or rule.
- Do not reference the project codebase, file paths outside the story author's concern, or internal Python module names.
