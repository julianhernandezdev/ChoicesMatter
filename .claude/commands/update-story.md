Bring an existing story up to date with all current engine features, or rewrite the feature showcase story.

**Argument:**
- A story name or path (e.g. `dead_air`, `stories/dead_air.json`) → **audit-and-update mode**
- `--showcase` → **showcase mode**: rewrite `stories/test_scene_color.json`

---

## Compiled Feature Reference

Use this instead of reading `CLAUDE.md`. All field names, valid values, and constraints are listed here.

**Meta**

| Field | Required | Notes |
|---|---|---|
| `id` | yes | `[A-Za-z0-9_.-]` only |
| `title` | yes | display string |
| `start_node` | yes | must match a node key |
| `version`, `author` | yes | strings |
| `est_time` | no | non-empty string, e.g. `"15–25 min"` |
| `warnings` | no | list of non-empty strings; shows warning screen |
| `auto_visited_flags` | no | bool, default `true`; `false` disables auto `visited_` tracking |

**Node fields**

| Field | Notes |
|---|---|
| `text`, `choices` | required |
| `is_ending` | bool |
| `ending_type` | `"good"` \| `"bad"` \| `"neutral"` |
| `scene` | non-empty string; carries forward to nodes that omit it |
| `choice_number_color` | rich color name or hex; node-level default for choice numbers |
| `insets` | array of inset objects (see below) |
| `overlays` | array of overlay objects (see below) |

**Choice fields**

| Field | Notes |
|---|---|
| `label`, `next` | required; `next` must be a valid node id |
| `requires` | `{"flag": bool\|int\|str\|[str]}` — int = threshold (≥ N), list = membership |
| `sets` | `{"flag": bool\|int\|str\|"+N"\|"-N"}` — applied when choice is taken; delta strings add/subtract from current int (default 0) |
| `color` | rich color; overrides node-level `choice_number_color` for this choice's number |
| `obfuscated` | bool; player sees `[REDACTED ██████]` instead of label |

**Inset fields:** `text` (req), `position` (`"before"`/`"after"`, default `"before"`), `style` (see below), `requires`

**Overlay fields:** `text` (req), `position` (`"before"`/`"after"`, default `"after"`), `style`, `requires`

**Named styles** (user-configurable; these are the committed defaults):

| Key | Color | Prefix | Modifiers | Use |
|---|---|---|---|---|
| `system` | white | — | dim | timestamps, logs, status lines |
| `echo` | blue | `~ ` | dim italic | recurring phrases, callbacks |
| `memory` | magenta | `◈ ` | dim italic | personal memory, internal recall |
| `whisper` | cyan | `✦ ` | dim italic | ambient atmosphere |
| `warning` | yellow | `⚠ ` | bold | urgent callouts |
| `""` | — | — | dim italic | generic aside |

**Flag system:**
- `requires` bool = exact match; int = value ≥ N; str = exact match; `[str]` = value is member of list
- `sets` bool/int/str = direct assign; `"+N"`/`"-N"` string = delta on current int
- `visited_<node_id>` is auto-set `true` on node entry when `auto_visited_flags` is `true` (reserved prefix — don't set manually via `sets` unless `auto_visited_flags: false`)

**Validation (check before writing):**
- All `next` values and `start_node` reference existing node IDs
- `ending_type` ∈ `{good, bad, neutral}` if present
- `position` ∈ `{before, after}` if present
- `requires` values: bool / int / str / non-empty `[str]`; keys must be strings
- `sets` values: bool / int / str / delta string matching `^[+-]\d+$`; keys must be strings
- `est_time`, `scene`, `choice_number_color`, choice `color`: non-empty string if present
- `warnings`: list of non-empty strings if present
- `obfuscated`: boolean if present

---

## Audit-and-Update Mode

1. Resolve the argument to a file path under `stories/`. Read the story in full. Understand:
   - Tone, setting, genre, and emotional register per node
   - Which flags are in use and what they track
   - The full branching structure and all possible paths

2. Audit the story against the feature checklist. For each item, note whether it is present and whether it would *serve* this specific story if absent:

   **Meta:** `est_time` · `warnings`

   **Nodes:** `scene` · `choice_number_color` · `insets` (before) · `insets` (after) · `insets` with `requires` · `overlays` (before) · `overlays` (after) · `overlays` with `requires`

   **Choices:** `color` (per-choice override) · `obfuscated` · `requires`

3. For every absent feature that *would serve the story*, design how to add it. Prioritize narrative fit — a feature that would feel forced should be left out with a note.

   - **`scene`:** Even sparse labels ("The Corridor", "Your Office") ground the reader. Look for natural location shifts.
   - **`choice_number_color`:** Match palette to emotional weight. Horror → red or dim. Safe → green. Uncertain → yellow.
   - **`insets`:** What is happening *around* the prose that the player notices? System logs, overheard fragments, bodily sensations. Marginal annotations.
   - **`overlays`:** What haunts the space *around* the choices? Recurring phrases, intrusive thoughts, environmental sounds. `after` overlays linger as the player decides.
   - **`obfuscated`:** A choice the character makes blindly. Best on pivotal or irreversible choices. One per story is usually enough.
   - **`requires`:** Which choices or elements should only exist if the player has taken a specific path? Reward attentive players with callbacks.
   - **`warnings`:** Read for content themes — death, violence, psychological distress.

4. Write the updated story JSON. Preserve all existing prose and structure exactly — do not rewrite the story's voice or plot. Only add:
   - New fields on existing nodes/choices (`scene`, `color`, insets, overlays, `obfuscated`)
   - Flag gates on existing choices/insets/overlays where they make narrative sense
   - Meta fields that were missing

   If a flag gate requires a new `sets` on an upstream choice, add it — but do not add nodes, reroute `next` values, or alter any existing prose text.

5. Validate the finished JSON against the rules above before writing.

6. Write the updated file back to the same path.

7. Print a summary: for each feature added, name it, the node(s) it was added to, and one sentence on the narrative reason. For any feature deliberately skipped, say why.

---

## Showcase Mode (`--showcase`)

Goal: keep `stories/test_scene_color.json` as a living reference that demonstrates every engine feature at least once.

1. Read `stories/test_scene_color.json`.

2. Read one rich story file (e.g. `stories/dead_air.json`) to calibrate prose register.

3. Rewrite `stories/test_scene_color.json` so that:
   - Every item in the feature checklist above is demonstrated at least once
   - The story is 8–12 nodes, playable top-to-bottom
   - At least one full flag round-trip: a choice that `sets` a flag, an inset and overlay gated on that flag, and a choice gated on that flag
   - All three `ending_type` values appear across possible endings
   - One choice uses `obfuscated: true`
   - `scene` changes at least once mid-story to show carry-forward; at least one node inherits it silently
   - `warnings` is non-empty so the warning screen is exercised
   - Prose is tight and functional — this is a tech demo, not a story; clarity beats atmosphere

4. Validate the finished JSON against the rules above before writing.

5. Write the updated file to `stories/test_scene_color.json`.

6. Print a coverage summary: each checklist item with the node ID where it appears.
