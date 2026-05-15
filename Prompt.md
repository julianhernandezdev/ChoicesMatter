# Choices Matter — Story Author Reference

You are writing a story for **Choices Matter**, a Python CLI text adventure engine. All story content lives in `.json` files. The player reads prose scenes and selects numbered choices; the engine navigates a tree of nodes based on those choices and accumulated flag state. No code changes are needed — drop a `.json` file into `stories/` and it is playable immediately.

---

## File structure

Every story file has exactly two top-level keys:

```json
{
  "meta": { ... },
  "nodes": {
    "node_id": { ... },
    "another_node": { ... }
  }
}
```

`meta` holds story-level metadata. `nodes` is a flat object where each key is an author-defined node ID and each value is a node object. The engine starts at the node named by `meta.start_node` and follows `choice.next` values to navigate.

---

## Meta fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `id` | Yes | string | Unique identifier. Must match `[A-Za-z0-9_.-]` only. Used as the save file key. |
| `title` | Yes | string | Display title shown in the story picker. |
| `version` | Yes | string | Author-defined version string, e.g. `"1.0"`. |
| `author` | Yes | string | Author name. |
| `start_node` | Yes | string | Must exactly match a key in `nodes`. |
| `est_time` | No | string | Estimated read time, e.g. `"5–8 min"`. If omitted, auto-computed from word count. Must be non-empty if present. |
| `warnings` | No | string[] | Content warnings shown before the story launches. Each entry must be a non-empty string. |

---

## Node fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `text` | Yes | string | Main prose shown in the story panel. |
| `choices` | Yes | array | Array of choice objects. An **empty array `[]` is treated as an ending**. |
| `insets` | No | array | Inset objects rendered inside the story panel (see below). |
| `overlays` | No | array | Overlay objects rendered around the choice list (see below). |
| `is_ending` | No | boolean | Marks this as a terminal node. |
| `ending_type` | No | string | `"good"`, `"bad"`, or `"neutral"`. Controls ending panel color (green / red / yellow). |
| `scene` | No | string | Location label shown as a dim header above the panel. Carries forward until changed. Must be non-empty if present. |
| `choice_number_color` | No | string | `rich` color name or hex (e.g. `"bright_red"`, `"#ffaa00"`). Default number-prefix color for all choices on this node. Must be non-empty if present. |

---

## Choice fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `label` | Yes | string | Text shown to the player. |
| `next` | Yes | string | Node ID to navigate to. Must exist in `nodes`. |
| `requires` | No | object | `{"flag_name": true/false}`. Choice is hidden if the condition is not met. |
| `sets` | No | object | `{"flag_name": true/false}`. Applied to player flag state when this choice is taken. |
| `color` | No | string | `rich` color name or hex. Overrides `choice_number_color` for this choice's number prefix only. Must be non-empty if present. |
| `obfuscated` | No | boolean | If `true`, renders the label as dim `[REDACTED ██████]`. Player can still select it; the real label is never shown. |

---

## Inset fields

Insets render **inside** the story panel, separated from main text by a dim rule line. `"before"` insets appear above the main text; `"after"` insets appear below it.

| Field | Required | Type | Notes |
|---|---|---|---|
| `text` | Yes | string | Line rendered inside the panel. Do not include the style prefix — the renderer adds it. |
| `position` | No | string | `"before"` (default) or `"after"`. |
| `style` | No | string | Named style key (see Named styles). `""` renders as dim italic with no prefix. |
| `requires` | No | object | Same flag dict format as choices. Inset is hidden if condition not met. |

---

## Overlay fields

Overlays render **outside** the story panel, around the choice list. `"before"` overlays appear above the choices; `"after"` overlays appear below them. On ending nodes, all overlays appear before the ending panel.

| Field | Required | Type | Notes |
|---|---|---|---|
| `text` | Yes | string | The overlay line. Do not include the style prefix — the renderer adds it. |
| `position` | No | string | `"before"` or `"after"` (default). |
| `style` | No | string | Named style key. `""` uses the default overlay style (cyan dim italic). |
| `requires` | No | object | Same flag dict format. Hidden if condition not met. |

---

## Named styles

These are the committed defaults (user-configurable via `settings.json`). Styles apply to both insets and overlays.

| Key | Color | Prefix | Modifiers | Intended use |
|---|---|---|---|---|
| `system` | white | (none) | dim | Timestamps, logs, status lines, diegetic data the character reads |
| `echo` | blue | `~ ` | dim, italic | Recurring phrases, callbacks, things that resurface unbidden |
| `memory` | magenta | `◈ ` | dim, italic | Personal memory, internal recall, what the character already knows |
| `whisper` | cyan | `✦ ` | dim, italic | Ambient atmosphere, the unnamed feeling in the room |
| `warning` | yellow | `⚠ ` | bold | Urgent callouts, danger signals |
| `""` | — | (none) | dim, italic | Generic aside; no semantic category needed |

Any unrecognised style key falls back to the default overlay config (cyan dim italic, `✦ ` prefix).

---

## The flag system

Flags are boolean values in a dict that persist for the duration of a run and are saved with the save file. They accumulate — flags are never automatically cleared mid-run.

**Three uses:**
- `choice.sets` — applies the flag when the choice is taken
- `choice.requires` — hides the choice entirely if the flag condition is not met
- `inset.requires` / `overlay.requires` — hides the element if the condition is not met

Flag dicts must have **string keys** and **boolean values**: `{"flag_name": true}` or `{"flag_name": false}`.

**Example — flag set and consumed:**
```json
"choice_pick_up": {
  "label": "Pick up the key",
  "next": "hallway",
  "sets": { "has_key": true }
},
"choice_use_key": {
  "label": "Unlock the drawer",
  "next": "drawer_open",
  "requires": { "has_key": true }
}
```
A choice with `requires: {"has_key": false}` would appear only for players who did *not* pick up the key.

---

## Scene carry-forward

`scene` is displayed as a dim rule header above the story panel. Once set on a node, it carries forward silently to all subsequent nodes until a new `scene` value is set. You only need to add `scene` when the location changes.

```json
"node_a": { "scene": "The Archive Room", ... },
"node_b": { ... },
"node_c": { "scene": "The Roof", ... }
```
`node_b` inherits `"The Archive Room"` without any explicit field.

---

## Validation rules

The engine validates the entire story at load time. Any violation prevents the story from running with a clear error message.

- `meta.id` must match `[A-Za-z0-9_.-]` only
- All required `meta` fields (`id`, `title`, `version`, `author`, `start_node`) must be present and non-empty strings
- `meta.start_node` must exist as a key in `nodes`
- Every `choice.next` must reference an existing node ID in `nodes`
- Every node must have a `text` field (string) and a `choices` field (array)
- `ending_type` must be `"good"`, `"bad"`, or `"neutral"` if present
- Overlay `position` must be `"before"` or `"after"` if present
- Flag dicts (`requires`, `sets`) must have string keys and boolean values — no other types
- `est_time` must be a non-empty string if present
- `warnings` must be a list of non-empty strings if present
- `scene` must be a non-empty string if present
- `choice_number_color` must be a non-empty string if present
- `choice.color` must be a non-empty string if present
- `choice.obfuscated` must be a boolean if present

---

## Authoring guidance

**Insets vs overlays.** Insets belong *inside* the scene — they are things the character perceives directly: a timestamp on a screen, a log entry they are reading, a physical sensation they notice. Overlays belong *outside* — they are the atmosphere that surrounds the act of deciding: a phrase that resurfaces, the weight of what the character knows as they face their choices, the feeling in the gap between knowing and acting. If the content is something the character *encounters*, it is an inset. If it is something the reader *feels while deciding*, it is an overlay.

**`requires` on choices vs elements.** Use `choice.requires` to hide options that would be narratively incoherent given prior decisions — a choice to "use the key" should not appear if the player never found one. Use `overlay.requires` and `inset.requires` to reward players who took a specific path: a callback line that recontextualises what came before, a detail that only lands with the right prior knowledge. The distinction is between *gating access* (choices) and *deepening resonance* (elements).

**`obfuscated`.** Reserve this for choices where the character acts without fully understanding what they are doing — decisions that can only be named in retrospect, actions taken from impulse or compulsion. The mechanic loses power through repetition. One per story is usually the right limit. The player can still select the redacted choice; the engine treats it identically to a visible one.

**Color.** Use `choice_number_color` and per-choice `color` to signal emotional register, not decoration. Red for danger, green for safety, yellow for uncertainty, dim white for resignation. Consistency within a node matters more than variety across the story. A node where all choices are `"bright_red"` except one that is `"dim white"` signals something; a node where every choice is a different color signals nothing.

**Endings.** A story needs at least one ending node. `ending_type` controls panel color: `"good"` (bright green), `"bad"` (bright red), `"neutral"` (bright yellow). The gallery system tracks which ending node IDs the player has reached across playthroughs — use distinct node IDs for each ending. An empty `choices` array triggers ending detection automatically; `is_ending: true` is redundant but acceptable for clarity.

---

## Complete working example

```json
{
  "meta": {
    "id": "the_night_inventory",
    "title": "The Night Inventory",
    "version": "1.0",
    "author": "Example Author",
    "start_node": "arrival",
    "est_time": "3–5 min",
    "warnings": ["mild dread"]
  },
  "nodes": {
    "arrival": {
      "scene": "Archive Room, 11:00 PM",
      "insets": [
        { "text": "INVENTORY RUN 4  —  INITIATED 23:00", "position": "before", "style": "system" }
      ],
      "text": "The archive room smells of old paper and wet stone. Your clipboard says fourteen items. You have counted thirteen twice.\n\nOn the shelf at the end of the row: a small wooden box. Not on the manifest.",
      "choice_number_color": "yellow",
      "choices": [
        { "label": "Read the manifest more carefully", "next": "read_manifest", "sets": { "checked_manifest": true } },
        { "label": "Go straight to the box", "next": "the_box" }
      ]
    },

    "read_manifest": {
      "text": "The manifest was compiled in 1987. Item fourteen is listed under a column header that appears nowhere else: HOLD — DO NOT LOG.\n\nThe entry has been redacted. Someone pressed hard enough that the pen went through to the page below.",
      "choices": [
        { "label": "Go to the box", "next": "the_box" }
      ]
    },

    "the_box": {
      "scene": "End of Row 7",
      "insets": [
        {
          "text": "The manifest said: HOLD — DO NOT LOG.",
          "position": "before",
          "style": "memory",
          "requires": { "checked_manifest": true }
        }
      ],
      "text": "The box is unlocked. Inside: a single index card with an address written on it in handwriting that is not yours.\n\nYour handwriting.",
      "overlays": [
        { "text": "You have been here before.", "position": "after", "style": "echo" }
      ],
      "choice_number_color": "bright_red",
      "choices": [
        { "label": "Log it and report to your supervisor", "next": "ending_report" },
        { "label": "Put it back. Finish the inventory. Say nothing.", "next": "ending_silence" },
        { "label": "Take the address", "next": "ending_follow", "obfuscated": true }
      ]
    },

    "ending_report": {
      "text": "Your supervisor arrives at 11:40. She looks at the box for a long time.\n\n'We have been waiting for someone to find this,' she says. 'It has been here since before the building was an archive.'\n\nShe does not explain what it was before. She files your report. She thanks you by your full name, which she has never used.",
      "choices": [],
      "is_ending": true,
      "ending_type": "neutral"
    },

    "ending_silence": {
      "insets": [
        { "text": "INVENTORY RUN 4  —  COMPLETED 23:47  —  ITEMS LOGGED: 13", "position": "after", "style": "system" }
      ],
      "text": "You put the box back. You log thirteen items. The discrepancy you attribute to a transcription error in 1987.\n\nThe drive home is quiet. You check your hands at a red light. They have stopped shaking.",
      "choices": [],
      "is_ending": true,
      "ending_type": "good"
    },

    "ending_follow": {
      "text": "You know the street. You have driven past it hundreds of times without stopping.\n\nYou have never asked yourself why.",
      "choices": [],
      "is_ending": true,
      "ending_type": "bad"
    }
  }
}
```

**Walkthrough:**
- `arrival` — sets `scene`, uses a `"before"` system inset, sets `choice_number_color` to yellow, and a choice that `sets` the flag `checked_manifest`.
- `read_manifest` — minimal pass-through node; one passage, one forward choice.
- `the_box` — `scene` changes to signal a location shift. The `"before"` memory inset is gated on `checked_manifest` — only players who read the manifest see the callback. An `"after"` echo overlay lingers below the choices. `choice_number_color` shifts to `"bright_red"` for the critical decision point. One choice is `obfuscated`.
- Endings — `ending_silence` uses an `"after"` system inset to close the log. Three `ending_type` values covered: `"neutral"`, `"good"`, `"bad"`.

---

## Quick reference card

| Field | Lives on | Default | One-line note |
|---|---|---|---|
| `est_time` | meta | (auto) | Override auto-computed read time |
| `warnings` | meta | (none) | String list; triggers a warning screen before launch |
| `scene` | node | (inherited) | Location label; carries forward until changed |
| `choice_number_color` | node | `"cyan"` | Default number-prefix color for all choices on this node |
| `insets` | node | (none) | Annotated lines inside the story panel |
| `overlays` | node | (none) | Atmospheric lines around the choice list |
| `is_ending` | node | false | Explicitly mark terminal node (empty `choices` also works) |
| `ending_type` | node | (none) | `"good"`/`"bad"`/`"neutral"` — panel color |
| `requires` | choice / inset / overlay | (none) | Hide element if flag condition is unmet |
| `sets` | choice | (none) | Apply flag to player state when this choice is taken |
| `color` | choice | (node default) | Per-choice number-prefix color override |
| `obfuscated` | choice | false | Render label as `[REDACTED ██████]` |
| `position` | inset / overlay | `"before"` / `"after"` | Inset default is `"before"`; overlay default is `"after"` |
| `style` | inset / overlay | (default overlay) | Named style key; `""` for dim italic with no prefix |
