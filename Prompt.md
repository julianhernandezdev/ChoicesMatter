# Choices Matter — Story Authoring Reference

Use this document as a system prompt or context block to write valid story JSON files for the Choices Matter engine. No other project knowledge required.

---

## §1 — What this is

Choices Matter is a Python CLI text adventure engine (with a JS web player in parity). All story content lives in `.json` files — no code changes are needed to add a story. The player reads prose and picks a numbered choice; the engine branches to the next node based on that choice and the current flag state. Stories can track inventory, relationships, and visited paths through a persistent flag dict that accumulates across the run.

---

## §2 — File structure

Two top-level keys: `meta` (story metadata) and `nodes` (a dict of all scenes keyed by node ID).

```json
{
  "meta": {
    "id": "my_story",
    "title": "My Story",
    "version": "1.0",
    "author": "Author Name",
    "start_node": "intro"
  },
  "nodes": {
    "intro": {
      "text": "You stand at a crossroads.",
      "choices": [
        { "label": "Go left.", "next": "left_path" },
        { "label": "Go right.", "next": "right_path" }
      ]
    },
    "left_path": {
      "text": "The road bends into shadow.",
      "is_ending": true,
      "ending_type": "neutral",
      "choices": []
    },
    "right_path": {
      "text": "The road opens onto a field.",
      "is_ending": true,
      "ending_type": "good",
      "choices": []
    }
  }
}
```

---

## §3 — Meta fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `id` | Yes | string | Save file key. Must match `[A-Za-z0-9_.-]` only. |
| `title` | Yes | string | Display title shown in the story picker. |
| `version` | Yes | string | Story version (e.g. `"1.0"`). |
| `author` | Yes | string | Author name. |
| `start_node` | Yes | string | Must match a key in `nodes`. |
| `est_time` | No | string | e.g. `"15–25 min"`. Auto-computed from word count if omitted. |
| `warnings` | No | list of strings | Shows a warning screen before launch. e.g. `["Contains depictions of grief"]`. |
| `auto_visited_flags` | No | bool | Default `true`. Set `false` to disable automatic `visited_<node_id>` tracking. |
| `name_prompt` | No | string | If set, prompts the player for a name before the first node. Stored as `player_name` in state. Use `{player_name}` in any text field. |
| `name_default` | No | string | Fallback name if player submits empty. Requires `name_prompt`. |

---

## §4 — Node fields

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Main prose shown to the player. Supports inline tokens (see §9). |
| `choices` | Yes | Array of choice objects. Empty array triggers ending detection (no `is_ending` needed). |
| `is_ending` | No | `true` marks the node as terminal. Triggers ending screen. |
| `ending_type` | No | `good`, `bad`, or `neutral`. Controls ending panel colour (green / red / yellow). |
| `scene` | No | Location label shown as a dim header above the panel. Carries forward to subsequent nodes until overridden. Only write when location changes. |
| `choice_number_color` | No | `rich` colour name or hex (e.g. `"bright_red"`, `"#ffaa00"`). Default fallback for choice number prefixes on this node. |
| `insets` | No | Array of inset objects. Rendered inside the story panel. |
| `overlays` | No | Array of overlay objects. Rendered outside the panel, around the choice list. |

---

## §5 — Choice fields

| Field | Required | Notes |
|---|---|---|
| `label` | Yes | Text shown to the player. Does not support `{key}` substitution or `{flag?…}` conditional syntax. |
| `next` | Yes | Node ID to navigate to. Must exist in `nodes`. |
| `requires` | No | `{"flag": value}` — hides this choice if the condition is not met. |
| `sets` | No | `{"flag": value}` — applies to player state when this choice is taken. |
| `color` | No | Overrides `choice_number_color` (or default `cyan`) for this choice's number prefix. |
| `obfuscated` | No | `true` renders the label as `[REDACTED ██████]`. Player can still select it; real label never shown. |

**`requires` value types:**

| Value type | Condition |
|---|---|
| `true` / `false` | Exact boolean match |
| integer (e.g. `3`) | Current value ≥ 3 (threshold) |
| string (e.g. `"red"`) | Exact string match |
| list of strings (e.g. `["red","blue"]`) | Current value is a member of the list |

**`sets` value types:** `true`/`false`, integer, string, or a delta string like `"+1"` or `"-2"` (adds/subtracts from the current int value; missing key defaults to 0).

---

## §6 — Inset fields

Insets render **inside** the story panel, separated from main text by a dim rule line. Use them for things the character is *perceiving inside the scene* — data on a screen, a letter they're reading, a physical sensation.

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Content of the inset. Supports inline tokens. |
| `position` | No | `"before"` (default) or `"after"` the main text. |
| `style` | No | Named style key (see §8). `""` renders as dim italic with no prefix. |
| `requires` | No | Same format as choice `requires`. Hides inset if condition not met. |

---

## §7 — Overlay fields

Overlays render **outside** the panel, wrapping the choice list. `before` appears above the choices; `after` appears below. On ending nodes, all overlays appear before the ending panel. Use overlays for *atmosphere surrounding the decision* — the gap between knowing and choosing.

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Content of the overlay. Supports inline tokens. |
| `position` | No | `"before"` or `"after"` (default). |
| `style` | No | Named style key (see §8). `""` uses the default overlay style (dim italic, cyan, prefix `✦ `). |
| `requires` | No | Same format as choice `requires`. Hides overlay if condition not met. |

---

## §8 — Named styles

| Style key | Color | Prefix | Modifiers | Intended use |
|---|---|---|---|---|
| `"system"` | white | *(none)* | dim | Data readouts, interface text, log entries |
| `"echo"` | blue | `~ ` | dim, italic | Repetition of earlier words; haunting callbacks |
| `"warning"` | yellow | `⚠ ` | bold | In-world alerts, urgent notices |
| `"memory"` | magenta | `◈ ` | dim, italic | Recalled experience, intrusive thought |
| `"whisper"` | cyan | `✦ ` | dim, italic | Atmosphere, unspoken implication |
| `""` | *(default)* | *(none)* | dim, italic | Generic aside; inherits overlay defaults |

---

## §9 — The flag system

Flags are named values (`bool | int | str`) that persist for the run and are saved between sessions. Three uses:

- **`choice.requires`** — hides the choice if the condition is not met
- **`choice.sets`** — applies flags to state when the choice is taken
- **`overlay.requires` / `inset.requires`** — shows the element only when the condition is met

**Worked example** — a flag set two nodes earlier reveals a callback overlay later:

```json
"choices": [
  { "label": "Stay on the line.", "next": "engage", "sets": { "engaged": true } }
]
```

```json
"overlays": [
  {
    "text": "Nora. The private name. Nobody called her that.",
    "requires": { "engaged": true },
    "style": "memory"
  }
]
```

**Visited flags:** When `auto_visited_flags` is `true` (the default), the engine automatically sets `visited_<node_id>: true` every time a node is entered. Use these in `requires` to detect revisits. Do not set them manually via `sets`.

**Inline conditional text:** Embed `{flag?shown if true|shown if false}` in any text field. The false branch is optional; omitting it collapses to nothing when the flag is unset.

**Variable substitution:** Embed `{key}` to insert `str(state[key])` at runtime. Missing keys leave the placeholder intact. Runs before conditional resolution. `{player_name}` is the standard token for the protagonist's name.

**Inline corruption:** Embed `{corrupt}…{/corrupt}` to mark a span for glitch rendering. Optional params: `{corrupt:0.8}` (intensity 0–1), `{corrupt:random}` (mode), `{corrupt:0.8:random}` (both — intensity first). Corruption is stripped in accessible mode.

---

## §10 — Scene carry-forward

`scene` is a non-empty string that appears as a dim Rule header above the story panel. Once set on a node, it carries forward to all subsequent nodes automatically — you only need to set it again when the location changes. Never set `scene` on every node; set it only on the first node of each new location.

```json
"intro": { "scene": "WKTR 91.4 — Studio B", ... }
```

---

## §11 — Validation rules

The engine validates before launch and raises errors — stories that fail validation show as `-ERROR` in the picker.

- Every `next` value and `start_node` must reference an existing node ID
- `id` must match `[A-Za-z0-9_.-]` only
- `ending_type` must be `good`, `bad`, or `neutral`
- `position` must be `"before"` or `"after"`
- `requires` keys must be strings; values must be `bool`, `int`, `str`, or a non-empty `list` of strings
- `sets` keys must be strings; values must be `bool`, `int`, `str`, or a delta string matching `^[+-]\d+$`
- `warnings` if present: list of non-empty strings
- `scene`, `choice_number_color`, choice `color`: non-empty string if present
- `obfuscated`: boolean if present
- `est_time`: non-empty string if present
- Do not set `visited_<node_id>` via `sets` unless `meta.auto_visited_flags` is `false`
- Inline corruption: `{corrupt}` must have a matching `{/corrupt}`; spans cannot be nested; intensity param must be float 0–1; mode must be `consistent` or `random`; intensity must come before mode when both are present

---

## §12 — Authoring guidance

**Insets vs overlays.** Insets are inside the scene — the character is reading data on a screen, feeling a physical sensation, absorbing information in the moment. Overlays are outside the scene — atmosphere surrounding the decision, the gap between knowing and choosing. A log entry (`system` inset) is what the character reads; a haunting callback (`echo` overlay below the choices) is what the reader feels. The rule of thumb: if the character would be aware of it, it's an inset. If only the reader is aware of it, it's an overlay.

**`requires` on choices vs on overlays/insets.** Use choice `requires` to hide options that would be incoherent given the player's path — a choice that assumes knowledge the player doesn't have. Use overlay and inset `requires` to reward players who took a specific path with a callback — seeing an earlier detail reflected later creates the sense that the story is paying attention.

**`obfuscated`.** Use for choices where the character acts without fully understanding what they're choosing — irreversible decisions, things only named in retrospect. The player experiences the uncertainty alongside the character. One per story is usually enough; more erodes the effect.

**Color.** Use choice number color to signal emotional register, not decoration: red for danger, green for safety or escape, yellow for uncertainty. Consistency within a node matters more than variety — a node with three choices all in yellow reads as "all of these feel wrong." A node mixing red and green signals a genuine moral split.

**Endings.** `ending_type` controls panel color: `good` is green, `bad` is red, `neutral` is yellow. An empty `choices` array triggers ending detection without `is_ending: true`. Multiple endings are fine; the gallery tracks which the player has found.

---

## §13 — Complete working example

```json
{
  "meta": {
    "id": "the_lighthouse",
    "title": "The Lighthouse",
    "version": "1.0",
    "author": "Example Author",
    "start_node": "arrival",
    "est_time": "5–8 min",
    "warnings": ["References to isolation and loss"]
  },
  "nodes": {
    "arrival": {
      "scene": "The Causeway — Low Tide",
      "text": "The lighthouse is dark when you arrive. You expected that. You did not expect the door to be open.",
      "choices": [
        { "label": "Go inside.", "next": "ground_floor", "sets": { "entered": true } },
        { "label": "Wait outside until dawn.", "next": "ending_dawn" }
      ]
    },
    "ground_floor": {
      "insets": [
        { "text": "LIGHTHOUSE LOG — LAST ENTRY: 14 DAYS AGO", "style": "system", "position": "before" }
      ],
      "text": "The ground floor is unchanged since the last keeper. A logbook sits open on the desk. The last entry trails off mid-sentence.\n\nSomething has been moved recently — the chair, perhaps. The dust pattern doesn't match.",
      "overlays": [
        { "text": "The door was open.", "style": "echo", "position": "after" }
      ],
      "choices": [
        { "label": "Read the logbook.", "next": "logbook", "sets": { "read_log": true } },
        { "label": "Climb to the lamp room.", "next": "lamp_room" }
      ]
    },
    "logbook": {
      "text": "The final entry reads: *We saw it again last night. The light we made, reflected back from somewhere it shouldn't be. I don't think the sea is where we thought it was.*\n\nThe rest of the page is blank.",
      "choices": [
        { "label": "Climb to the lamp room.", "next": "lamp_room" }
      ]
    },
    "lamp_room": {
      "scene": "The Lamp Room — Top of the Tower",
      "insets": [
        {
          "text": "LOGBOOK NOTE: The reflection came from the north window.",
          "style": "memory",
          "requires": { "read_log": true },
          "position": "before"
        }
      ],
      "text": "The lamp is cold. Through the north window, far out at sea, you can see a light. Steady. Rhythmic. Identical to the one above you — if it were lit.\n\nThere is no lighthouse in that direction. There never has been.",
      "overlays": [
        { "text": "The light we made, reflected back.", "style": "echo", "requires": { "read_log": true }, "position": "before" },
        { "text": "What does it want?", "style": "whisper", "position": "after" }
      ],
      "choices": [
        { "label": "Activate the lamp. Answer it.", "next": "ending_answer", "color": "bright_red", "obfuscated": true },
        { "label": "Leave. Don't look back.", "next": "ending_leave", "color": "green" }
      ]
    },
    "ending_answer": {
      "text": "You activate the lamp.\n\nFor a moment, two lights face each other across the water. Then the distant one goes dark.\n\nSo does yours.",
      "is_ending": true,
      "ending_type": "bad",
      "choices": []
    },
    "ending_leave": {
      "text": "You walk back along the causeway without looking at the water.\n\nYou don't know what was out there. You know you made the right choice.",
      "is_ending": true,
      "ending_type": "good",
      "choices": []
    },
    "ending_dawn": {
      "text": "You wait. Dawn comes. The light out at sea — you notice it only now, as the sun rises — winks out.\n\nThe door swings shut on its own. You never go inside.",
      "is_ending": true,
      "ending_type": "neutral",
      "choices": []
    }
  }
}
```

**What this demonstrates:**

- **`read_log` flag** — set when the player reads the logbook; gates a `memory` inset and an `echo` overlay in the lamp room. Players who read it get a callback; those who didn't skip straight to the lamp without context.
- **`system` inset** — the log date as an in-world data display, `position: "before"` so it precedes the prose.
- **`echo` overlay** — "The door was open" repeating after the player chose to enter; below the choices, where it haunts the decision just made.
- **`scene` carry-forward** — set on `arrival` and `lamp_room` only; `ground_floor` and `logbook` inherit "The Causeway — Low Tide" and switch cleanly when the player climbs.
- **`obfuscated` choice** — "Activate the lamp" is the bad ending; the player makes the choice without knowing its name.
- **Three `ending_type` values** — one of each, all demonstrated.

---

## §14 — Quick reference card

| Field | Lives in | One-line note |
|---|---|---|
| `est_time` | `meta` | Optional display string; auto-computed if omitted |
| `warnings` | `meta` | List of strings shown before launch |
| `auto_visited_flags` | `meta` | Default true; set false to suppress `visited_*` auto-tracking |
| `name_prompt` | `meta` | Triggers pre-game name prompt; stores as `player_name` |
| `name_default` | `meta` | Per-story fallback name; requires `name_prompt` |
| `is_ending` | node | Marks terminal node; triggers ending screen |
| `ending_type` | node | `good`/`bad`/`neutral` — panel colour green/red/yellow |
| `scene` | node | Location header; carries forward until overridden |
| `choice_number_color` | node | Node-level fallback for choice number prefix colour |
| `insets` | node | Inside-panel styled text blocks |
| `overlays` | node | Outside-panel text around the choice list |
| `requires` | choice / inset / overlay | Hides element if flag condition not met |
| `sets` | choice | Applies flags to state when taken |
| `color` | choice | Per-choice number prefix colour; overrides node default |
| `obfuscated` | choice | `true` renders label as `[REDACTED ██████]` |
| `position` | inset / overlay | `before` or `after`; default `before` (inset) / `after` (overlay) |
| `style` | inset / overlay | Named style key; `""` = dim italic, no prefix |
| `{flag?true\|false}` | any `text` | Inline conditional; false branch optional |
| `{key}` | any `text` | Variable substitution; missing key left intact |
| `{player_name}` | any `text` | Standard token for protagonist name |
| `{pause}` | node/ending `text` | Typewriter delay; stripped in non-typewriter mode |
| `{corrupt:i:m}…{/corrupt}` | any `text` | Glitch span; intensity 0–1, mode consistent/random |
