Generate or update `Prompt.md` — a self-contained reference document for giving to other LLMs so they can write stories for this engine without access to the codebase.

**Goal:** `Prompt.md` must be usable as a drop-in system prompt or context block. Complete enough that an LLM with no other project knowledge can produce a valid, well-crafted story JSON file. Target length: under ~3000 tokens. Precision over warmth — tables beat prose where structure is involved.

---

**Steps:**

1. Read `settings.example.json` to get the named style defaults (colors, prefixes, modifiers for `system`, `echo`, `memory`, `whisper`, `warning`).

2. Read one rich story file — `stories/dead_air.json` — to extract short verbatim snippets that demonstrate inset and overlay authoring style. Pull 2–3 lines max; quality beats quantity.

3. Write `Prompt.md` to the project root with these 14 sections in order. All sections are required.

---

**Section content specs** — write each section exactly as described:

**§1 — What this is**
One paragraph: Python CLI text adventure engine, all story content in JSON files, player reads prose and picks numbered choices, stories branch on choices and flag state, no code changes to add a story.

**§2 — File structure**
Two top-level keys: `meta` and `nodes`. Show a minimal 2-node skeleton JSON block. One sentence explaining each key.

**§3 — Meta fields**
Table: field | required | type | notes. Cover:
- `id` — yes — string — must match `[A-Za-z0-9_.-]`; used as save file key
- `title`, `version`, `author` — yes — string
- `start_node` — yes — string — must match a key in `nodes`
- `est_time` — no — string — e.g. `"15–25 min"`; auto-computed from word count if omitted
- `warnings` — no — list of strings — shows warning screen before launch
- `auto_visited_flags` — no — bool — default `true`; set `false` to disable auto `visited_` tracking

**§4 — Node fields**
Table: field | required | notes. Cover `text`, `choices`, `is_ending`, `ending_type` (good/bad/neutral), `scene`, `choice_number_color`, `insets`, `overlays`. Note: empty `choices` array triggers ending even without `is_ending: true`.

**§5 — Choice fields**
Table: `label`, `next`, `requires`, `sets`, `color`, `obfuscated`. For `requires`: show the flag dict format and explain bool/int (threshold ≥)/str (exact)/list[str] (membership). For `sets`: show delta string format (`"+1"`, `"-2"`). For `color`: explain it overrides `choice_number_color`. For `obfuscated`: player sees `[REDACTED ██████]`.

**§6 — Inset fields**
Table: `text`, `position` (before/after, default before), `style`, `requires`. One sentence: insets render inside the story panel, separated by a dim rule. Before insets appear above main text; after below.

**§7 — Overlay fields**
Table: `text`, `position` (before/after, default after), `style`, `requires`. One sentence: overlays render outside the panel, around the choice list. `before` above choices, `after` below. On ending nodes, all overlays appear before the ending panel.

**§8 — Named styles**
Table: style key | color | prefix | modifiers | intended use. Use the values from `settings.example.json`. Include `""` (empty string) → dim italic, no prefix, generic aside.

**§9 — The flag system**
Three uses: `choice.requires` (hides choice if condition unmet), `choice.sets` (applies flag when choice is taken), `overlay.requires` / `inset.requires` (hides element if unmet). Flags persist for the run and are saved. Give one worked example: a choice that sets a flag two nodes earlier, an inset gated on that flag later.

**§10 — Scene carry-forward**
`scene` is a string shown as a dim header above the panel. Once set, it carries to all subsequent nodes until a new `scene` is set. Only write `scene` when the location changes.

**§11 — Validation rules**
Bullet list of every must-pass constraint, phrased as "must" statements:
- Every `next` value and `start_node` must reference an existing node ID
- `story_id` must match `[A-Za-z0-9_.-]`
- `ending_type` must be `good`, `bad`, or `neutral`
- `position` must be `before` or `after`
- `requires` values must be bool / int / str / non-empty list of strings; keys must be strings
- `sets` values must be bool / int / str / delta string matching `^[+-]\d+$`; keys must be strings
- `warnings` if present: list of non-empty strings
- `scene`, `choice_number_color`, choice `color`: non-empty string if present
- `obfuscated`: boolean if present
- `est_time`: non-empty string if present
- Do not set `visited_*` via `sets` unless `auto_visited_flags` is `false`

**§12 — Authoring guidance**
Prose paragraphs (not bullets):
- Insets vs overlays: insets are *inside* the scene (data the character reads, sensations they feel); overlays are *outside* (atmosphere surrounding the decision, the gap between knowing and choosing).
- `requires` on choices vs overlays/insets: use choice `requires` to hide options that would be incoherent; use overlay/inset `requires` to reward players who took a specific path with a callback.
- `obfuscated`: on choices where the character acts without fully understanding — irreversible decisions, things named only in retrospect. One per story is usually enough.
- Color: signal emotional register, not decoration. Red = danger, green = safety, yellow = uncertainty, dim/white = resignation. Consistency within a node matters more than variety.
- Endings: good/bad/neutral controls panel color (green/red/yellow). Empty `choices` triggers ending detection.

**§13 — Complete working example**
A full, valid, short story JSON (5–7 nodes) demonstrating: at least one flag set and used as a `requires`, one inset, one overlay, one `scene` label, one `ending_type`. Original prose. Clean JSON, no comment keys. After the code block, a prose walkthrough explaining what each section demonstrates.

**§14 — Quick reference card**
Single compact table: field name | lives in | one-line note. Every optional field, all in one place.

---

4. After writing `Prompt.md`, print one line per section confirming it was populated. Flag any fact that couldn't be sourced (e.g. a style missing from `settings.example.json`).
