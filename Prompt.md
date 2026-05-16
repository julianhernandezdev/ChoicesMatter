# Choices Matter — Story Authoring Reference

Use this document as a complete reference for writing story JSON files for the Choices Matter engine. No other project knowledge is required.

---

## 1. What this is

Choices Matter is a Python CLI text adventure engine. All story content lives in `.json` files in the `/stories/` directory. The player reads prose and selects numbered choices. Stories branch based on choices and accumulated flag state. No code changes are needed — drop a `.json` file in `/stories/` and the engine discovers it automatically.

---

## 2. File structure

```json
{
  "meta": { ... },
  "nodes": {
    "node_id": { ... },
    "another_node": { ... }
  }
}
```

`meta` holds story-level metadata. `nodes` is a flat dictionary of node objects keyed by unique string IDs. The engine starts at the node named in `meta.start_node`.

---

## 3. Meta fields

| Field | Required | Type | Notes |
|---|---|---|---|
| `id` | Yes | string | Save file key. Must match `[A-Za-z0-9_.-]` only — no spaces or slashes. |
| `title` | Yes | string | Display name shown in the story picker. |
| `version` | Yes | string | Author-defined version string (e.g. `"1.0"`). |
| `author` | Yes | string | Author name. |
| `start_node` | Yes | string | Must exactly match a key in `nodes`. |
| `est_time` | No | string | Read time shown in picker (e.g. `"5–10 min"`). Auto-computed from word count if omitted. Must be non-empty if provided. |
| `warnings` | No | string[] | Content warning strings displayed before launch. Each must be non-empty. |
| `auto_visited_flags` | No | boolean | Default `true`. Engine auto-sets `visited_<node_id>: true` on every navigation. Set to `false` to manage the `visited_` namespace manually. |

---

## 4. Node fields

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Main prose shown in the story panel. |
| `choices` | Yes | Array of choice objects. An empty array triggers ending detection even without `is_ending: true`. |
| `insets` | No | Array of inset objects rendered inside the story panel. |
| `overlays` | No | Array of overlay objects rendered around the choice list. |
| `is_ending` | No | Boolean. If `true`, triggers the ending screen. |
| `ending_type` | No | `"good"`, `"bad"`, or `"neutral"`. Controls ending panel color. Defaults to `"neutral"`. |
| `scene` | No | Location label shown as a dim header above the panel. Carries forward to subsequent nodes until a new `scene` overrides it. Non-empty string if provided. |
| `choice_number_color` | No | `rich` color name or hex (e.g. `"bright_red"`, `"#ffaa00"`). Node-level fallback for choice number prefix color. Non-empty string if provided. |

---

## 5. Choice fields

| Field | Required | Notes |
|---|---|---|
| `label` | Yes | Text shown to the player. |
| `next` | Yes | Node ID to navigate to. Must exist in `nodes`. |
| `requires` | No | Flag conditions — choice hidden unless all match. `bool` = exact; `int` = threshold (≥); `str` = exact; `list[str]` = membership. |
| `sets` | No | Applied to state when choice is taken. `bool`/`int`/`str` = direct assignment; `"+N"`/`"-N"` strings = integer delta (unset key defaults to 0). Keys must not start with `visited_` unless `meta.auto_visited_flags` is `false`. |
| `color` | No | Overrides node-level `choice_number_color` for this choice's number prefix. Non-empty string if provided. |
| `obfuscated` | No | Boolean. If `true`, the label is replaced with `[REDACTED ██████]` in the choice list. The player can still select it; the real label is never shown. |

---

## 6. Inset fields

Insets render inside the story panel, separated from the main text by a dim rule line. `"before"` insets appear above the prose; `"after"` insets appear below.

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Line of text rendered inside the panel. |
| `position` | No | `"before"` (default) or `"after"` the main prose. |
| `style` | No | Named style key — see Section 8. `""` renders dim italic with no prefix. |
| `requires` | No | Same flag dict as choices. Hides the inset if conditions are not met. |

---

## 7. Overlay fields

Overlays render outside the story panel. `"before"` overlays appear above the choice list; `"after"` overlays appear below it. On ending nodes, all overlays appear before the ending panel regardless of `position`.

| Field | Required | Notes |
|---|---|---|
| `text` | Yes | Line of text. |
| `position` | No | `"before"` or `"after"` (default). |
| `style` | No | Named style key — see Section 8. `""` uses the default overlay config (cyan, dim italic). |
| `requires` | No | Same flag dict as choices. Hides the overlay if conditions are not met. |

---

## 8. Named styles

Built-in style keys for `style` fields on insets and overlays. User-configurable via `settings.json`; these are the committed defaults.

| Key | Color | Dim | Italic | Bold | Prefix | Intended use |
|---|---|---|---|---|---|---|
| `"system"` | white | yes | no | no | _(none)_ | Timestamps, logs, status lines, diegetic data |
| `"echo"` | blue | yes | yes | no | `~ ` | Recurring phrases, callbacks, things that resurface |
| `"memory"` | magenta | yes | yes | no | `◈ ` | Personal memory, internal recall, what the character knows |
| `"whisper"` | cyan | yes | yes | no | `✦ ` | Ambient atmosphere, the unnamed feeling in the room |
| `"warning"` | yellow | no | no | yes | `⚠ ` | Urgent callouts, danger signals, alerts |
| `""` | _(default)_ | yes | yes | no | _(none)_ | Generic aside; no semantic label needed |

---

## 9. The flag system

The engine maintains a `state` dictionary of `string → bool | int | str` values across the run. State accumulates and is persisted in the save file. It is cleared on new game.

**Three uses:**
- **`choice.sets`** — applies values when a choice is taken
- **`choice.requires`** / **`inset.requires`** / **`overlay.requires`** — hides the element unless all conditions match

**`sets` value types:**

| Value | Effect |
|---|---|
| `true` / `false` | Boolean assignment |
| integer (e.g. `5`) | Absolute integer assignment |
| `"+N"` / `"-N"` (e.g. `"+1"`) | Integer delta — adds/subtracts from current value; unset key defaults to 0 |
| string (e.g. `"red"`) | String assignment |

**`requires` evaluation:**

| Value | Condition |
|---|---|
| `true` / `false` | Exact boolean match |
| integer (e.g. `3`) | Current value ≥ 3 |
| string (e.g. `"red"`) | Exact string match |
| `["red", "blue"]` | Current value is any member of the list |

**Auto-visited flags:** When `meta.auto_visited_flags` is `true` (the default), the engine automatically sets `visited_<node_id>: true` each time a node is entered. Use in `requires` to detect revisits — no `sets` boilerplate needed. `visited_` is reserved; manually setting it raises a validation error unless `meta.auto_visited_flags` is `false`.

**Worked example** — boolean flag, integer counter, and threshold require:

```json
"gate": {
  "text": "The contact studies you.",
  "choices": [
    { "label": "Help them", "next": "helped", "sets": {"trust": "+2", "aided": true} },
    { "label": "Decline", "next": "helped" }
  ]
},
"helped": {
  "text": "They nod.",
  "choices": [
    { "label": "Ask the question", "next": "secret", "requires": {"trust": 2} },
    { "label": "Leave",            "next": "exit" }
  ],
  "insets": [
    {
      "text": "You helped them. They remember.",
      "requires": {"aided": true},
      "position": "before",
      "style": "memory"
    }
  ]
}
```

---

## 10. Scene carry-forward

`scene` is a string label displayed as a dim rule header above the story panel. Set it once when a location is established; it carries forward silently to all subsequent nodes until a new `scene` key overrides it. Only set `scene` when the location changes.

```json
"basement":    { "scene": "The Basement", "text": "...", "choices": [...] },
"boiler_room": {                           "text": "...", "choices": [...] }
```

`boiler_room` displays `"The Basement"` automatically. No duplication needed.

---

## 11. Validation rules

The engine validates at load time and raises a hard error on any violation:

- `meta.id` must only contain letters, numbers, dots, underscores, and hyphens (`[A-Za-z0-9_.-]`)
- All required `meta` fields (`id`, `title`, `version`, `author`, `start_node`) must be present and non-empty strings
- `meta.start_node` must match a key in `nodes`
- `meta.est_time`, if present, must be a non-empty string
- `meta.warnings`, if present, must be a list of non-empty strings
- `meta.auto_visited_flags`, if present, must be `true` or `false` (not a string)
- Every node must have a `text` field (non-empty string) and a `choices` field (array)
- Every `next` value in every choice must reference a node ID that exists in `nodes`
- `ending_type` must be one of `"good"`, `"bad"`, `"neutral"`
- `is_ending`, if present, must be `true` or `false`
- `overlay.position` and `inset.position` must be `"before"` or `"after"`
- `requires` values must be `bool`, `int`, `str`, or a non-empty `list[str]`; keys must be strings
- `sets` values must be `bool`, `int`, or `str`; delta strings (`"+1"`, `"-3"`) must match `^[+-]\d+$`
- `choice.sets` keys must not start with `visited_` unless `meta.auto_visited_flags` is `false`
- `scene`, `choice_number_color`, and `choice.color` must be non-empty strings if provided
- `choice.obfuscated`, if present, must be `true` or `false`

---

## 12. Authoring guidance

**Insets vs overlays.** Insets belong inside the scene: data the character is directly perceiving — a clock on the wall, a line from a document they're reading, a system log. Overlays belong outside the scene: the feeling in the gap between knowing and deciding. They haunt the space around the choices. Use insets to anchor the player in physical reality; use overlays to create the emotional register in which a choice is made.

**`requires` on choices vs on insets and overlays.** Use `choice.requires` to hide an option that would be narratively incoherent — a player cannot use a code they were never given, cannot confront someone they haven't met. Use `inset.requires` or `overlay.requires` to reward players who took a specific path with a callback or a deeper layer of context. Gated choices gate agency; gated insets and overlays gate depth.

**`obfuscated`.** Use on choices where the character acts without fully understanding what they're choosing — an irreversible decision, something named only in retrospect, a door that should feel dangerous to open. The player sees `[REDACTED ██████]` and can still select it. One per story is usually enough. Overuse cheapens the effect.

**Color.** `choice_number_color` and per-choice `color` signal emotional register, not decoration. Danger → `"bright_red"`. Safety → `"green"`. Uncertainty → `"yellow"`. Resignation or ambiguity → `"white"` or dim. Consistency within a node matters more than variety across nodes.

**Endings.** `ending_type` controls the ending panel color: `"good"` → green, `"bad"` → red, `"neutral"` → yellow. A story needs at least one reachable ending. An empty `choices` array triggers ending detection even without `is_ending: true`. The gallery tracks each ending node ID found across playthroughs.

---

## 13. Complete working example

```json
{
  "meta": {
    "id": "cold_signal",
    "title": "Cold Signal",
    "version": "1.0",
    "author": "Example Author",
    "start_node": "watch_station",
    "warnings": ["Psychological horror"]
  },
  "nodes": {
    "watch_station": {
      "scene": "Array Station Theta — Night Watch",
      "choice_number_color": "yellow",
      "insets": [
        { "text": "THETA-7  —  04:17  —  ALL SYSTEMS NOMINAL", "position": "before", "style": "system" }
      ],
      "text": "Six hours on the night watch. Nothing comes through the deep channel. Nothing ever does.\n\nThen the waveform changes.",
      "choices": [
        { "label": "Log the anomaly and analyze it", "next": "analyze", "sets": {"anomaly_logged": true} },
        { "label": "Flag it to command without touching the controls", "next": "reported" }
      ]
    },
    "analyze": {
      "choice_number_color": "yellow",
      "insets": [
        { "text": "SIGNAL ORIGIN: UNRESOLVED  —  STRUCTURE: NON-RANDOM  —  REPEATING: YES", "position": "after", "style": "system" }
      ],
      "text": "The signal is structured. Not noise. Not a satellite echo. Something arranged these pulses with intent.",
      "overlays": [
        { "text": "Non-random. Repeating. Structured.", "position": "after", "style": "echo" },
        {
          "text": "You logged it before you understood it. That distinction matters now.",
          "requires": {"anomaly_logged": true},
          "position": "before",
          "style": "memory"
        }
      ],
      "choices": [
        { "label": "Run the full pattern decode.", "next": "decode" },
        { "label": "File it to command and lock the channel.", "next": "reported", "color": "green" }
      ]
    },
    "decode": {
      "choice_number_color": "bright_red",
      "insets": [
        { "text": "DECODE COMPLETE  —  PATTERN: RECURSIVE  —  ORIGIN: DEEP FIELD", "position": "before", "style": "system" },
        { "text": "SECONDARY LAYER DETECTED  —  THIS SIGNAL IS LISTENING BACK", "position": "after", "style": "warning" }
      ],
      "text": "The pattern is self-referencing — it contains a model of you receiving it. The signal is not broadcasting. It is asking.\n\nYou have thirty seconds before it times out.",
      "overlays": [
        { "text": "It knows you're here.", "position": "after", "style": "whisper" }
      ],
      "choices": [
        { "label": "Answer it.", "next": "responded", "color": "bright_red", "obfuscated": true },
        { "label": "Terminate the session and file the full decode.", "next": "reported", "color": "green" }
      ]
    },
    "responded": {
      "insets": [
        { "text": "OUTGOING TRANSMISSION  —  04:31  —  DURATION: 00:00:08", "position": "before", "style": "system" }
      ],
      "text": "You transmit.\n\nThe waveform stops.\n\nFor four seconds, the channel is completely silent.\n\nThen it answers.",
      "choices": [],
      "is_ending": true,
      "ending_type": "bad"
    },
    "reported": {
      "scene": "Array Station Theta — Dawn",
      "text": "You file the anomaly report, flag the recording, and lock the channel.\n\nBy morning, three other stations have logged the same signal.\n\nYou don't find out what it was. That starts to feel like the right outcome.",
      "insets": [
        { "text": "ANOMALY REPORT FILED  —  CASE TRANSFERRED  —  CHANNEL LOCKED", "position": "after", "style": "system" }
      ],
      "choices": [],
      "is_ending": true,
      "ending_type": "good"
    }
  }
}
```

**Walkthrough:**

- `watch_station` establishes the `scene` (carries into `analyze`), uses `choice_number_color: "yellow"` for the uncertain register, and places a `"system"` before-inset as a status timestamp.
- "Log the anomaly" uses `sets` to record `anomaly_logged: true`.
- `analyze` has an `"echo"` after-overlay for atmosphere and a `"memory"` before-overlay gated on `anomaly_logged` — only players who logged the signal see the callback.
- `decode` uses two insets (before `"system"`, after `"warning"`), a `"whisper"` after-overlay, and an `obfuscated` choice — the player sees `[REDACTED ██████]` for "Answer it."
- `responded` is a bad ending; `reported` is a good ending with a `scene` override showing time has passed.
- `est_time` is omitted — the engine auto-computes it from word count.

---

## 14. Quick reference card

| Field | Lives on | Notes |
|---|---|---|
| `scene` | node | Location header; carries forward until overridden |
| `choice_number_color` | node | Node-level fallback for choice number prefix color |
| `insets` | node | Styled lines inside the story panel |
| `overlays` | node | Styled lines around the choice list |
| `is_ending` | node | Triggers ending screen; empty `choices` does the same |
| `ending_type` | node | `"good"` / `"bad"` / `"neutral"` — ending panel color |
| `requires` | choice / inset / overlay | Show only when all conditions match: bool=exact, int=threshold(≥), str=exact, list[str]=membership |
| `sets` | choice | Apply state when taken: bool/int/str=direct, `"+N"`/`"-N"`=delta |
| `color` | choice | Per-choice number prefix color override |
| `obfuscated` | choice | Replace label with `[REDACTED ██████]` |
| `position` | inset / overlay | `"before"` or `"after"` relative to prose / choice list |
| `style` | inset / overlay | Named style key; `""` for dim italic, no prefix |
| `est_time` | meta | Read time string; auto-computed if omitted |
| `warnings` | meta | Content warning strings shown before launch |
| `auto_visited_flags` | meta | Default `true`; set to `false` to manage `visited_` manually |
