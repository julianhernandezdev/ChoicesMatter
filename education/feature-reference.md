# Engine Feature Reference

All 20 engine features in one place — each illustrated by a numbered example story and documented with its code path through the engine. Read sequentially for a guided tour, or jump to a section via the table below.

## Quick Lookup

| # | Feature | Story file | Summary |
|---|---|---|---|
| 01 | Minimal Story | `stories/examples/01_minimal_story.json` | Minimum viable story: two nodes, one choice, one ending |
| 02 | Branching Endings | `stories/examples/02_branching_endings.json` | Three ending types (`good`, `bad`, `neutral`) and their display colors |
| 03 | Scene Carry-Forward | `stories/examples/03_scene_carry_forward.json` | Location labels that persist across nodes until overridden |
| 04 | Boolean Flags | `stories/examples/04_boolean_flags.json` | Write a boolean with `sets`; gate a choice on it with `requires` |
| 05 | Integer Flags | `stories/examples/05_integer_flags.json` | Accumulate an integer with delta strings; check a threshold |
| 06 | String Flags | `stories/examples/06_string_flags.json` | Store a string; check it with exact-match or list-membership |
| 07 | Auto-Visited Flags | `stories/examples/07_auto_visited_flags.json` | Opt out of automatic `visited_` tracking; manage revisit state manually |
| 08 | Insets | `stories/examples/08_insets.json` | Styled text blocks inside the story panel, before or after prose |
| 09 | Overlays | `stories/examples/09_overlays.json` | Flavour text outside the panel, wrapped around the choice list |
| 10 | Named Styles | `stories/examples/10_named_styles.json` | Full set of named style keys for insets and overlays |
| 11 | Choice Colors | `stories/examples/11_choice_colors.json` | Override choice number color per-choice or at node level |
| 12 | Obfuscated Choices | `stories/examples/12_obfuscated_choices.json` | Hide a choice label behind `[REDACTED]` while keeping it selectable |
| 13 | Hub Structure | `stories/examples/13_hub_structure.json` | Revisitable hub; exit unlocks only after visiting all branches |
| 14 | Parallel Knowledge Routes | `stories/examples/14_parallel_knowledge_routes.json` | Two paths converge on one node; state determines how it renders |
| 15 | Soft Failure | `stories/examples/15_soft_failure.json` | A gated choice completely invisible until its condition is met |
| 16 | Stateful Endings | `stories/examples/16_stateful_endings.json` | Multiple paths to one ending node with conditional content per path |
| 17 | Delayed Consequences | `stories/examples/17_delayed_consequences.json` | A flag set early that only surfaces several nodes later |
| 18 | Multi-Condition Gating | `stories/examples/18_multi_condition_gating.json` | One choice gated on two simultaneous conditions (AND + OR) |
| 19 | Conditional Inline Text | `stories/examples/19_conditional_inline_text.json` | Flag-conditional spans in text fields, resolved at runtime |
| 20 | Pause Token | `stories/examples/20_pause_token.json` | Inject a configurable delay mid-stream during typewriter playback |
| 21 | Variable Text Substitution | `stories/examples/21_variable_text_substitution.json` | `{key}` placeholders replaced at runtime with flag values; missing keys preserved intact |
| 22 | Protagonist Name Prompt | `stories/examples/22_protagonist_name_prompt.json` | `meta.name_prompt` triggers a pre-game name input; `{player_name}` available in all text fields |

---

## 01 — Minimal Story

**Story:** `stories/examples/01_minimal_story.json`
**Feature:** The minimum viable story — two nodes, one choice, one ending.

### What the story does

Two nodes. `start` has one choice that leads to `end`. `end` has `is_ending: true` and an empty `choices` array. Nothing else.

### Engine code path

**Loading** — `StoryLoader.load()` in `src/story.py` reads the JSON, validates `meta` fields via `_required_string()`, then iterates `nodes`. For each node it calls `_parse_choices()`, which validates every choice has a `label` and `next`. After parsing all nodes, it does a second pass to verify every `choice.next` references an existing node ID. If anything is missing, `StoryValidationError` is raised immediately.

**Starting** — `Engine.__init__()` (`src/engine.py:13`) sets `self._current_node = story.start_node`, `self._history = []`, and `self._state = {}`. The engine does not touch the save manager yet.

**`Engine.run()` loop** (`src/engine.py:34`) — On each iteration:
1. `self.story.get_node(self._current_node)` fetches the current `Node` dataclass.
2. `visible = [c for c in node.choices if self._check_requires(c.requires)]` — with no `requires`, all choices pass and `visible` equals the full list.
3. The ending check: `if node.is_ending or not visible` — `is_ending: true` short-circuits here. An empty `choices` array also triggers it (the `not visible` branch).
4. `display.show_ending(node.text, node.ending_type, overlays=[])` renders the ending panel.
5. `gallery_manager.record_ending()` persists the found ending; `save_manager.delete()` removes the active save.
6. `display.prompt_play_again()` — Y resets via `_reset()` and continues the loop; N returns from `run()`.

**Why `not visible` also triggers ending** — The engine treats a node with zero visible choices as an implicit ending regardless of `is_ending`. This means `is_ending: true` is only needed to set `ending_type`; an empty `choices` array is sufficient to stop the loop.

### Key references

| Symbol | Location |
|---|---|
| `StoryLoader.load()` | `src/story.py:102` |
| `StoryLoader._parse_choices()` | `src/story.py:277` |
| `Engine.run()` loop | `src/engine.py:34` |
| Ending check | `src/engine.py:53` |
| `Display.show_ending()` | `src/display.py:193` |

---

## 02 — Branching Endings

**Story:** `stories/examples/02_branching_endings.json`
**Feature:** Three `ending_type` values — `good`, `bad`, `neutral` — and how the engine maps them to display colors.

### What the story does

One fork node with three choices, each leading directly to a different ending node. The only difference between the endings is `ending_type`.

### Engine code path

**Validation** — `StoryLoader.load()` checks `ending_type` against `_ENDING_TYPES = {"good", "bad", "neutral"}` (`src/story.py:14`). Any other value raises `StoryValidationError`. The default when `ending_type` is omitted is `"neutral"` (`src/story.py:154`).

**At the ending node** — `Engine.run()` hits `node.is_ending` and calls:

```python
self.display.show_ending(node.text, node.ending_type, overlays=before + after)
```

**`Display.show_ending()`** (`src/display.py:193`) maps `ending_type` to a Rich color string via `_ENDING_COLORS`:

```python
_ENDING_COLORS = {
    "good":    "bright_green",
    "bad":     "bright_red",
    "neutral": "bright_yellow",
}
color = _ENDING_COLORS.get(ending_type, "bright_yellow")
```

The fallback `"bright_yellow"` means an unknown type renders as neutral — but this can't happen in practice because validation already rejected it.

The `color` string is used for both the panel's `border_style` and the title label (`— GOOD ENDING —`), so panel border and header change together.

### Key references

| Symbol | Location |
|---|---|
| `_ENDING_TYPES` constant | `src/story.py:14` |
| `ending_type` default | `src/story.py:154` |
| `_ENDING_COLORS` map | `src/display.py:37` |
| `Display.show_ending()` | `src/display.py:193` |

---

## 03 — Scene Carry-Forward

**Story:** `stories/examples/03_scene_carry_forward.json`
**Feature:** The `scene` field sets a location label that persists across nodes until overridden.

### What the story does

`room_a` sets `"scene": "The Library"`. `room_b` has no `scene` key — it inherits. `garden` sets `"scene": "The Garden"`, replacing the inherited value. `end` inherits from whoever reached it last.

### Engine code path

`Engine.__init__()` initializes `self._current_scene: str | None = None`.

At the top of every `Engine.run()` iteration:

```python
node = self.story.get_node(self._current_node)
if node.scene:
    self._current_scene = node.scene
```

`Node.scene` is `None` by default (when the JSON key is absent). The `if node.scene` guard only updates `_current_scene` when a non-None value is present, so nodes without a `scene` key leave the accumulated value unchanged.

`self._current_scene` is then passed to `display.show_node(..., current_scene=self._current_scene)`.

**`Display.show_node()`** (`src/display.py:146`) — when `current_scene` is truthy:

```python
if current_scene:
    self.console.print(Rule(f"[dim]{current_scene}[/dim]", style="dim"))
```

A dim Rule line is printed above the story panel.

**`Engine._reset()`** (`src/engine.py:130`) clears `self._current_scene = None`, so scene state does not carry between playthroughs.

**Validation** — `StoryLoader.load()` checks that `scene`, if present, is a non-empty string after stripping whitespace (`src/story.py:161`).

### Key references

| Symbol | Location |
|---|---|
| `_current_scene` init | `src/engine.py:28` |
| Scene update in loop | `src/engine.py:40` |
| `_reset()` clears scene | `src/engine.py:134` |
| `Display.show_node()` scene rule | `src/display.py:155` |
| `scene` validation | `src/story.py:160` |

---

## 04 — Boolean Flags

**Story:** `stories/examples/04_boolean_flags.json`
**Feature:** Writing a boolean to state with `sets` and gating a choice on it with `requires`.

### What the story does

Picking up the key sets `has_key: true`. The "Unlock it" choice at the chest requires `has_key: true` — it is hidden entirely if the flag is absent or false.

### Engine code path

**`Engine._state`** (`src/engine.py:27`) is a plain dict (`dict[str, bool | int | str]`) that accumulates all flag writes for the current run. It starts empty.

**Writing a flag — `Engine._apply_sets()`** (`src/engine.py:93`):

```python
def _apply_sets(self, sets: dict) -> None:
    for key, value in sets.items():
        if isinstance(value, str) and _DELTA_RE.fullmatch(value):
            # delta string — handled for integers, see example 05
            ...
        else:
            self._state[key] = value  # direct assignment for bool/int/str
```

`sets: { "has_key": true }` is parsed by `StoryLoader._parse_sets()` as Python `True` (JSON `true` → Python `bool`). `_apply_sets()` stores it directly: `self._state["has_key"] = True`.

`_apply_sets()` is called at the start of `Engine._advance()`, before the node changes (`src/engine.py:116`).

**Checking a flag — `Engine._check_requires()`** (`src/engine.py:75`):

```python
if isinstance(condition, bool):
    if current != condition:
        return False
```

For `requires: { "has_key": true }`, `condition` is `True`. `current = self._state.get("has_key")` — if the flag was never set, `current` is `None`, which `!= True`, so the check fails and the choice is hidden.

**Where hiding happens** — `Engine.run()` builds the `visible` list before rendering:

```python
visible = [c for c in node.choices if self._check_requires(c.requires)]
```

Choices that fail `_check_requires()` are excluded from `visible` entirely. `display.show_choices(visible, ...)` only receives the filtered list — the engine never passes hidden choices to the display layer.

### Key references

| Symbol | Location |
|---|---|
| `_state` field | `src/engine.py:27` |
| `_apply_sets()` | `src/engine.py:93` |
| `_check_requires()` bool branch | `src/engine.py:78` |
| `visible` list filtering | `src/engine.py:43` |
| `_advance()` applies sets | `src/engine.py:116` |

---

## 05 — Integer Flags

**Story:** `stories/examples/05_integer_flags.json`
**Feature:** Accumulating an integer with delta strings (`"+1"`) and checking a threshold with `requires`.

### What the story does

Each "Take a token" choice applies `sets: { "tokens": "+1" }`. The gate requires `tokens: 3`, meaning the player needs to collect at least three. There is no cap — the engine accumulates indefinitely.

### Engine code path

**Delta string detection** — `StoryLoader._parse_sets()` stores `"+1"` as the Python string `"+1"`. The string is legal because it matches the `_DELTA_RE = re.compile(r"^[+-]\d+$")` pattern (`src/story.py:16`). Strings starting with `+` or `-` that do NOT match this pattern are rejected at load time.

**`Engine._apply_sets()` delta branch** (`src/engine.py:95`):

```python
if isinstance(value, str) and _DELTA_RE.fullmatch(value):
    delta = int(value)                          # "+1" → 1
    current = self._state.get(key, 0)
    self._state[key] = (
        current if isinstance(current, int) and not isinstance(current, bool) else 0
    ) + delta
```

`self._state.get("tokens", 0)` returns 0 on first access. The `isinstance(current, bool)` guard exists because Python `bool` is a subclass of `int` — without it, `True + 1 = 2` would be silently accepted. If `current` is a bool, the guard resets to 0 before adding the delta.

**`Engine._check_requires()` integer branch** (`src/engine.py:81`):

```python
elif isinstance(condition, int):
    val = current if isinstance(current, int) and not isinstance(current, bool) else 0
    if val < condition:
        return False
```

`requires: { "tokens": 3 }` — `condition` is `3`. The check is `val < 3`, so the choice is hidden until `tokens` reaches 3 or more. This is a **threshold**, not an exact match — `tokens = 5` still passes.

**No upper bound in the engine** — The engine does not enforce a maximum. The story is responsible for hiding the "+1" choices once they are no longer meaningful, or accepting that the counter can exceed the threshold.

### Key references

| Symbol | Location |
|---|---|
| `_DELTA_RE` pattern | `src/engine.py:10`, `src/story.py:16` |
| `_parse_sets()` delta validation | `src/story.py:417` |
| `_apply_sets()` delta branch | `src/engine.py:95` |
| `_check_requires()` int threshold | `src/engine.py:81` |

---

## 06 — String Flags

**Story:** `stories/examples/06_string_flags.json`
**Feature:** Storing a string value in state and checking it with exact-match and list-membership `requires`.

### What the story does

The player picks a faction — Red, Blue, or None. `sets: { "faction": "red" }` stores the string. The checkpoint node demonstrates two `requires` variants: exact string match and list membership (OR semantics).

### Engine code path

**Writing — `Engine._apply_sets()`** (`src/engine.py:99`):

For non-delta strings, the direct assignment path runs: `self._state["faction"] = "red"`. Plain strings that happen to start with `+` or `-` but don't match `_DELTA_RE` are rejected at load time by `StoryLoader._parse_sets()`, so the engine never sees an ambiguous case.

**Checking — `Engine._check_requires()` string branch** (`src/engine.py:85`):

```python
elif isinstance(condition, str):
    if current != condition:
        return False
```

`requires: { "faction": "red" }` — exact equality. `"blue" != "red"` → hidden.

**List membership branch** (`src/engine.py:88`):

```python
elif isinstance(condition, list):
    if current not in condition:
        return False
```

`requires: { "faction": ["red", "blue"] }` — `current not in ["red", "blue"]` fails for `"none"`, passes for either faction. This is OR semantics: any member of the list satisfies the condition.

**Validation** — `StoryLoader._parse_requires()` (`src/story.py:374`) ensures list values are non-empty and contain only strings. An empty list `[]` is rejected — it would be an unsatisfiable condition.

**Type precedence in `_check_requires()`** — The conditions are checked as `isinstance(condition, bool)` first, then `int`, then `str`, then `list`. JSON `true`/`false` land as Python `bool`, and since `bool` is a subclass of `int`, the `bool` check must come first to prevent `True` being treated as the integer `1`.

### Key references

| Symbol | Location |
|---|---|
| `_apply_sets()` string assignment | `src/engine.py:99` |
| `_check_requires()` string branch | `src/engine.py:85` |
| `_check_requires()` list branch | `src/engine.py:88` |
| `_parse_requires()` list validation | `src/story.py:391` |

---

## 07 — Auto-Visited Flags

**Story:** `stories/examples/07_auto_visited_flags.json`
**Feature:** Opting out of automatic `visited_` flag tracking and managing revisit state manually.

### What the story does

`meta.auto_visited_flags` is `false`. No `visited_*` flags are written automatically. The story uses explicit `sets: { "saw_left": true }` on the choice that enters the left door, then gates the exit with `requires: { "saw_left": true }`.

### Engine code path

**Default behavior (examples 01–06, 08–18)** — `Engine._advance()` (`src/engine.py:119`):

```python
if self.story.auto_visited_flags:
    self._state[f"visited_{self._current_node}"] = True
```

After every navigation, the engine writes `visited_<node_id> = True` into `_state`. This is how example 13 (hub structure) gates the exit without any explicit `sets`.

**Opt-out** — Setting `"auto_visited_flags": false` in `meta` causes `StoryLoader.load()` to set `Story.auto_visited_flags = False` (`src/story.py:228`). The `if self.story.auto_visited_flags` guard in `_advance()` then skips the write entirely.

**Reserved prefix** — When `auto_visited_flags` is `true` (the default), `StoryLoader.load()` validates that no choice's `sets` dict contains a key starting with `"visited_"`:

```python
if auto_visited_flags:
    for node_id, node in nodes.items():
        for choice in node.choices:
            for key in choice.sets:
                if key.startswith("visited_"):
                    raise StoryValidationError(...)
```

This prevents a story author from manually writing `visited_` flags while auto-tracking is on, which would cause confusing overwrites. Setting `auto_visited_flags: false` lifts this restriction entirely and leaves flag management to the story.

**Why you'd opt out** — Auto-visited flags fire on every entry, including re-entries. For a looping structure where you need to distinguish "entered for the first time" from "entered again," auto flags don't help — you need a choice-level `sets` that fires once. Story 07 demonstrates this with `saw_left`.

### Key references

| Symbol | Location |
|---|---|
| `auto_visited_flags` field on `Story` | `src/story.py:73` |
| `auto_visited_flags` parsing | `src/story.py:221` |
| Reserved prefix validation | `src/story.py:230` |
| `visited_` write in `_advance()` | `src/engine.py:119` |

---

## 08 — Insets

**Story:** `stories/examples/08_insets.json`
**Feature:** Styled text blocks inside the story panel, positioned before or after the prose, with optional flag gating.

### What the story does

The first node has two insets: one `"before"` with `style: "system"` and one `"after"` with `style: "memory"`. The second node has a conditional inset (`requires: { "read_note": true }`) that only appears after the player has passed through the first node.

### Engine code path

**Data model** — `Inset` is a dataclass in `src/story.py:40`:

```python
@dataclass
class Inset:
    text: str
    position: str = "before"   # "before" | "after" relative to node text
    style: str = ""             # named style key; "" = dim italic default
    requires: dict = field(default_factory=dict)
```

Parsed by `StoryLoader._parse_insets()` (`src/story.py:347`). Position defaults to `"before"` and must be `"before"` or `"after"`.

**Filtering in `Engine.run()`** (`src/engine.py:49`):

```python
visible_insets = [i for i in node.insets if self._check_requires(i.requires)]
before_insets = [i for i in visible_insets if i.position == "before"]
after_insets  = [i for i in visible_insets if i.position == "after"]
```

Insets with unmet `requires` are excluded before splitting into before/after lists. The two lists are passed to `display.show_node()`.

**Rendering — `Display._node_panel()`** (`src/display.py:246`):

```python
parts: list = []
for inset in (before_insets or []):
    parts.append(self._inset_renderable(inset))
    parts.append(Rule(style="dim white"))   # separator rule
parts.append(Text(text))                   # main prose
for inset in (after_insets or []):
    parts.append(Rule(style="dim white"))   # separator rule
    parts.append(self._inset_renderable(inset))
content = Group(*parts) if len(parts) > 1 else Text(text)
```

Each inset gets a dim `Rule` separator on the side facing the prose — before-insets get a rule after them, after-insets get a rule before them. If there are no insets, `content` is just `Text(text)` with no `Group` overhead.

**`Display._inset_renderable()`** (`src/display.py:280`) — when `inset.style` is non-empty, it calls `_style_cfg()` to resolve the config for that named style (see example 10). When `inset.style == ""`, it falls back to `style="dim italic"` with no prefix.

**Insets on ending nodes** — `Engine.run()` computes `before_insets` and `after_insets` but only passes them to `display.show_node()` for non-ending nodes. On ending nodes, `display.show_ending()` is called instead, which accepts `overlays` but not insets. **Insets on an ending node are silently dropped.** Use `overlays` to attach conditional content to ending nodes.

### Key references

| Symbol | Location |
|---|---|
| `Inset` dataclass | `src/story.py:40` |
| `_parse_insets()` | `src/story.py:347` |
| Inset filtering in `Engine.run()` | `src/engine.py:49` |
| `Display._node_panel()` | `src/display.py:246` |
| `Display._inset_renderable()` | `src/display.py:280` |

---

## 09 — Overlays

**Story:** `stories/examples/09_overlays.json`
**Feature:** Flavour text that renders outside the story panel, wrapped around the choice list, with optional flag gating.

### What the story does

The `scene` node has two overlays: a conditional `"before"` whisper (only shown if `suspicious` is set) and an unconditional `"after"` echo. The player sets `suspicious` by choosing "Investigate" on the first node.

### Engine code path

**Data model** — `Overlay` is a dataclass in `src/story.py:33`:

```python
@dataclass
class Overlay:
    text: str
    requires: dict = field(default_factory=dict)
    position: str = "after"   # "before" | "after"
    style: str = ""           # named style key
```

Default position is `"after"` (unlike insets which default to `"before"`). Parsed by `StoryLoader._parse_overlays()` (`src/story.py:319`).

**Filtering in `Engine.run()`** (`src/engine.py:45`):

```python
visible_overlays = [o for o in node.overlays if self._check_requires(o.requires)]
before = [o for o in visible_overlays if o.position == "before"]
after  = [o for o in visible_overlays if o.position == "after"]
```

**Rendering — `Display.show_choices()`** (`src/display.py:165`):

```python
for overlay in (before_overlays or []):
    self._render_overlay(overlay)
    if stagger:
        time.sleep(stagger)
# ... choices printed here ...
for overlay in (after_overlays or []):
    self._render_overlay(overlay)
    if stagger:
        time.sleep(stagger)
```

Before-overlays print above the numbered choices; after-overlays print below. When typewriter mode is active, each overlay also staggers in at 60ms intervals alongside the choices.

**`Display._render_overlay()`** (`src/display.py:272`) resolves the style via `_style_cfg()` (see example 10), builds a Rich style string from `color` and modifier flags (`bold`, `italic`, etc.), then prints `prefix + overlay.text` with that style.

**Overlays on ending nodes** — `Engine.run()` passes `overlays=before + after` to `display.show_ending()` when an ending is reached. `Display.show_ending()` (`src/display.py:193`) renders all overlays before the ending panel:

```python
for overlay in (overlays or []):
    self._render_overlay(overlay)
```

This is different from non-ending nodes where overlays split around the choice list. On ending nodes, all overlays — regardless of `position` — appear before the panel.

### Overlay vs. inset

| | Insets | Overlays |
|---|---|---|
| Location | Inside the story panel | Outside the panel |
| Default position | `"before"` | `"after"` |
| Separated by | Dim rule | Nothing |
| On ending nodes | **Silently dropped** | Rendered before the panel |

### Key references

| Symbol | Location |
|---|---|
| `Overlay` dataclass | `src/story.py:33` |
| `_parse_overlays()` | `src/story.py:319` |
| Overlay filtering in `Engine.run()` | `src/engine.py:45` |
| `Display.show_choices()` overlay rendering | `src/display.py:176` |
| `Display.show_ending()` overlay rendering | `src/display.py:201` |
| `Display._render_overlay()` | `src/display.py:272` |

---

## 10 — Named Styles

**Story:** `stories/examples/10_named_styles.json`
**Feature:** The full set of named style keys for insets and overlays, and how the engine resolves them to visual properties.

### What the story does

One node with six insets and two overlays demonstrating every style variant: `system`, `memory`, `warning`, `echo`, `whisper` (via unnamed default), and `""` (empty string).

### Engine code path

**`Display._style_cfg()`** (`src/display.py:264`):

```python
def _style_cfg(self, style_name: str) -> dict:
    if style_name:
        named = self._cfg.get("styles", {}).get(style_name)
        if named:
            return named
    return self._cfg["overlay"]
```

Named styles are looked up from the loaded `settings.json` config under the `"styles"` key. If the name is empty or not found, the method falls back to the default `"overlay"` config block. This means all rendering properties — `color`, `prefix`, `bold`, `italic`, etc. — come from the config, not hardcoded values.

**`Display._render_overlay()`** (`src/display.py:272`):

```python
cfg = self._style_cfg(overlay.style)
parts = [m for m in _MODIFIERS if cfg.get(m)]
color = cfg.get("color", "cyan")
style = f"{' '.join(parts)} {color}".strip()
prefix = cfg.get("prefix", "✦ ")
self.console.print(f"  {prefix}{overlay.text}", style=style)
```

`_MODIFIERS = ("bold", "dim", "italic", "underline", "strike")` — any truthy value in the config for these keys is included in the Rich style string.

**`Display._inset_renderable()`** (`src/display.py:280`):

```python
if inset.style:
    cfg = self._style_cfg(inset.style)
    # ... build style from cfg ...
else:
    style = "dim italic"
    prefix = ""
```

When `style == ""` (empty string), the `if inset.style:` guard is `False`, so the empty-string case gets a hardcoded `"dim italic"` fallback with no prefix — distinct from any named style lookup.

**Why style `""` and no style key are identical** — Both map to `style=""` in the `Inset` dataclass default. The `_inset_renderable()` fallback treats both the same: `dim italic`, no prefix.

**Config-driven** — Adding or changing a named style requires only editing `settings.json`, not any Python code. The engine is style-agnostic; it routes the name through `_style_cfg()` and applies whatever the config returns.

### Style reference (defaults)

| Style name | Prefix | Color | Modifiers |
|---|---|---|---|
| `""` (empty) | none | — | dim italic |
| `"system"` | none | dim | — |
| `"memory"` | `◈ ` | magenta | italic |
| `"warning"` | `⚠ ` | yellow | bold |
| `"echo"` | `~ ` | blue | italic |
| `"whisper"` (default overlay) | `✦ ` | cyan | italic |

### Key references

| Symbol | Location |
|---|---|
| `_MODIFIERS` | `src/display.py:43` |
| `Display._style_cfg()` | `src/display.py:264` |
| `Display._render_overlay()` | `src/display.py:272` |
| `Display._inset_renderable()` | `src/display.py:280` |
| Config loading | `src/config.py` |

---

## 11 — Choice Colors

**Story:** `stories/examples/11_choice_colors.json`
**Feature:** Overriding the number color on individual choices and at the node level.

### What the story does

`default_colors` demonstrates per-choice `color` overrides against the default cyan. `node_level_color` sets `choice_number_color: "yellow"` as a node-level fallback and shows a per-choice `"magenta"` override on top of it.

### Engine code path

**Data model** — `Choice.color` is `str | None` (`src/story.py:28`). `Node.choice_number_color` is also `str | None` (`src/story.py:57`). Both default to `None` when absent from JSON.

**Validation** — `StoryLoader._parse_choices()` checks that `color`, if present, is a non-empty string (`src/story.py:297`). `StoryLoader.load()` does the same for `choice_number_color` (`src/story.py:173`). Neither validates that the value is a valid Rich color name — that responsibility is left to the display layer at render time.

**Resolution in `Display.show_choices()`** (`src/display.py:180`):

```python
for i, choice in enumerate(choices, start=1):
    num_color = choice.color or choice_number_color or "cyan"
    ...
    self.console.print(f"  [bold {num_color}]{i}.[/bold {num_color}] {label}")
```

Priority chain: `choice.color` → node's `choice_number_color` → `"cyan"`.

`choice_number_color` is passed from the engine to `display.show_choices()` at the call site in `Engine.run()`:

```python
self.display.show_choices(visible, before, after, node.choice_number_color)
```

The engine does not interpret the color string — it passes it through unchanged. The color string is embedded directly into Rich markup, so any valid Rich color name or hex value works.

**Only the number is colored** — The choice label text always renders in the default terminal color. Only the number prefix (`1.`, `2.`, etc.) is affected.

### Key references

| Symbol | Location |
|---|---|
| `Choice.color` field | `src/story.py:28` |
| `Node.choice_number_color` field | `src/story.py:57` |
| `color` validation in `_parse_choices()` | `src/story.py:293` |
| `choice_number_color` validation | `src/story.py:169` |
| `show_choices()` call with color | `src/engine.py:64` |
| Color resolution in `Display.show_choices()` | `src/display.py:181` |

---

## 12 — Obfuscated Choices

**Story:** `stories/examples/12_obfuscated_choices.json`
**Feature:** Hiding a choice's label behind `[REDACTED]` while keeping it selectable.

### What the story does

Three choices. The middle one has `"obfuscated": true`. The player sees a redacted placeholder instead of the real label text and can still select it by number — but never learns what the label said.

### Engine code path

**Data model** — `Choice.obfuscated: bool = False` (`src/story.py:29`). Parsed by `StoryLoader._parse_choices()` (`src/story.py:301`), which validates the value is exactly `true` or `false` (not a truthy string).

**Rendering in `Display.show_choices()`** (`src/display.py:182`):

```python
label = "[dim]████ ██████ ████ ████████[/dim]" if choice.obfuscated else choice.label
self.console.print(f"  [bold {num_color}]{i}.[/bold {num_color}] {label}")
```

When `obfuscated` is `True`, the label is replaced with a fixed block-character string rendered dim. The number prefix is printed normally — the choice is fully selectable.

**The real label is never exposed** — The display layer never prints `choice.label` for an obfuscated choice. No engine state records what the label said. A player who selects the obfuscated option is navigated to `choice.next` exactly as if they had selected any other choice.

**Obfuscated choices still participate in filtering** — `_check_requires()` evaluates `choice.requires` normally for obfuscated choices. An obfuscated choice with an unmet `requires` is excluded from `visible` entirely — the player never sees a redacted slot for it. This allows obfuscated choices to be conditionally visible.

**No engine logic changes for obfuscated choices** — The obfuscated flag is purely presentational. `_advance()`, `_apply_sets()`, and the rest of the engine treat the choice identically to any other.

### Key references

| Symbol | Location |
|---|---|
| `Choice.obfuscated` field | `src/story.py:29` |
| `obfuscated` parsing and validation | `src/story.py:301` |
| Label substitution in `Display.show_choices()` | `src/display.py:182` |

---

## 13 — Hub Structure

**Story:** `stories/examples/13_hub_structure.json`
**Feature:** A revisitable hub node where an exit unlocks only after the player has visited all branches — using auto-generated `visited_` flags.

### What the story does

`hub` has three choices: Room A, Room B, and an exit requiring `visited_room_a: true` AND `visited_room_b: true`. Rooms loop back to the hub. No explicit `sets` anywhere — the engine tracks visits automatically.

### Engine code path

**Auto-visited flag write** — Every time the player navigates to a node, `Engine._advance()` fires (`src/engine.py:115`):

```python
def _advance(self, choice: Choice) -> None:
    self._apply_sets(choice.sets)
    self._history.append(self._current_node)
    self._current_node = choice.next
    if self.story.auto_visited_flags:
        self._state[f"visited_{self._current_node}"] = True
    ...
```

After `self._current_node` is updated to the new node, the flag `visited_<new_node_id>` is set to `True`. So entering `room_a` writes `self._state["visited_room_a"] = True`.

**Multi-key AND gating** — The exit choice has:

```json
"requires": { "visited_room_a": true, "visited_room_b": true }
```

`Engine._check_requires()` iterates all key-condition pairs and returns `False` on the first failure. Both conditions must be satisfied simultaneously — this is AND semantics. There is no OR at the `requires` dict level; OR within a single key requires the list-value syntax (see example 06).

**Revisit behavior** — The hub is entered on game start via `_resolve_start()`, which sets the initial node without going through `_advance()`, so `visited_hub` is never written. Returning to the hub via a room's "Return" choice does go through `_advance()`, which writes `visited_hub = True` on the second visit — but this doesn't matter for this story since nothing requires it.

**Save on every advance** — Each time the player navigates (including between hub and rooms), `_advance()` writes a save file via `save_manager.write()`. The hub structure generates many saves. This is intentional — save-on-advance means no progress is lost.

### Key references

| Symbol | Location |
|---|---|
| `visited_` write in `_advance()` | `src/engine.py:119` |
| Multi-key AND in `_check_requires()` | `src/engine.py:75` |
| `auto_visited_flags` guard | `src/engine.py:119` |
| `_resolve_start()` — does not write visited_ | `src/engine.py:102` |

---

## 14 — Parallel Knowledge Routes

**Story:** `stories/examples/14_parallel_knowledge_routes.json`
**Feature:** Two different paths converging on the same node, with state determining how that node renders.

### What the story does

`fork` has two choices. Both set `source` to a different string value, then both route to `next: "converge"`. At `converge`, two conditional insets each require a specific value of `source` — only one can be visible at a time.

### Engine code path

**No engine mechanism for convergence** — The engine navigates purely by node ID. When a choice has `"next": "converge"`, the engine sets `self._current_node = "converge"` and enters the loop iteration for that node. It does not care how many other choices also point to `"converge"`. Convergent nodes require no special JSON syntax and no engine support beyond normal navigation.

**State carries across the convergence** — `_advance()` applies `choice.sets` before changing `self._current_node`. So by the time the engine renders `converge`, `self._state["source"]` is already set to whichever value the player's route wrote.

**Conditional rendering at the convergent node** — `Engine.run()` filters insets before displaying:

```python
visible_insets = [i for i in node.insets if self._check_requires(i.requires)]
```

At `converge`, two insets exist — each requires a different value of `source`. Only one passes `_check_requires()`. The display receives a list of exactly one inset; it has no knowledge that another existed.

**The graph vs. tree distinction** — CLAUDE.md notes stories are "a tree by authoring convention, not engine enforcement." Convergent nodes like this one create a directed graph. The engine's node-ID-based navigation handles graphs natively — there is no tree enforcement.

**Validation still runs** — `StoryLoader` validates that every `choice.next` references an existing node. A choice pointing to `"converge"` is valid as long as `"converge"` exists in `nodes`. Multiple choices pointing to the same target are not flagged.

### Key references

| Symbol | Location |
|---|---|
| `_advance()` sets state before navigating | `src/engine.py:116` |
| Inset filtering in `Engine.run()` | `src/engine.py:49` |
| Cross-reference validation | `src/story.py:189` |

---

## 15 — Soft Failure

**Story:** `stories/examples/15_soft_failure.json`
**Feature:** A gated choice that is completely invisible until its condition is met — the player is never told it exists.

### What the story does

The `vault` node has three choices: enter the combination (requires `has_combination`), search the office, or force it. The "Enter the combination" choice is invisible until the player finds the sticky note in `office` and sets the flag. The player who goes straight to "Force it" never sees that a better option existed.

### Engine code path

**Hard hide, not grayout** — The engine has no concept of a grayed-out or disabled choice. `_check_requires()` returns `True` or `False`. Choices that return `False` are excluded from `visible` before the display layer sees them:

```python
visible = [c for c in node.choices if self._check_requires(c.requires)]
```

`Display.show_choices(visible, ...)` only receives the filtered list. It prints choices `1.`, `2.`, `3.` for whatever is in that list — there is no placeholder for the hidden choice, no gap in the numbering, and no message indicating something is missing.

**Renumbering** — Because `visible` is rebuilt each render, choice numbers shift when a flag changes. Before finding the combination: the vault shows choices `1.` (search) and `2.` (force). After: it shows `1.` (enter combination), `2.` (search), `3.` (force). The order follows the JSON order of choices; `requires` filtering does not reorder, only removes.

**State persists across nodes** — The player navigates `vault → office → vault` by having choices `next: "office"` and `next: "vault"`. `_advance()` writes and persists state on each navigation. When the player returns to `vault`, `self._state["has_combination"]` is still `True`, so the gated choice now passes.

**Design implication** — Because hidden choices are completely invisible, the player cannot distinguish "this choice requires something I haven't done" from "this choice doesn't exist in this story." This is a deliberate design choice: the soft failure pattern creates natural puzzle solving without ever communicating that a puzzle exists.

### Key references

| Symbol | Location |
|---|---|
| `visible` list filtering | `src/engine.py:43` |
| `_check_requires()` | `src/engine.py:75` |
| Display receives only filtered choices | `src/engine.py:64` |

---

## 16 — Stateful Endings

**Story:** `stories/examples/16_stateful_endings.json`
**Feature:** Multiple paths converging on one ending node, with conditional content reflecting how the player arrived.

### What the story does

`start` has three choices, each setting `path` to a different string, all routing to `"next": "end"`. The `end` node is an ending with three conditional insets, each requiring a different value of `path`.

### Engine code path

**Convergent ending** — Works identically to the convergent non-ending node in example 14. The engine navigates to `"end"` by node ID; state already contains the `path` flag.

**The inset drop** — `Engine.run()` computes `before_insets` and `after_insets` unconditionally, but on ending nodes it calls `display.show_ending()` instead of `display.show_node()`. `show_ending()` does not accept insets:

```python
if node.is_ending or not visible:
    self.display.show_ending(node.text, node.ending_type, overlays=before + after)
```

The `before_insets` and `after_insets` variables are computed and then **not used**. The conditional insets in this example story do not actually render in the CLI engine.

**To get conditional content on an ending node, use overlays** — `show_ending()` renders all overlays before the ending panel:

```python
for overlay in (overlays or []):
    self._render_overlay(overlay)
```

The corrected version of this story would use `overlays` with `position: "before"` instead of `insets`. The engine merges all visible overlays (regardless of their `position` value) and passes them as a single flat list.

**Why the example uses insets despite the drop** — The story demonstrates the design pattern (convergent ending with per-path content), but insets were chosen instead of overlays. The story works as a conceptual example, but a dev implementing this pattern should use overlays on ending nodes.

### Key references

| Symbol | Location |
|---|---|
| Ending check bypasses insets | `src/engine.py:53` |
| `show_ending()` receives overlays, not insets | `src/engine.py:54` |
| `Display.show_ending()` overlay rendering | `src/display.py:201` |
| Correct pattern: overlays on ending nodes | See example 09 |

---

## 17 — Delayed Consequences

**Story:** `stories/examples/17_delayed_consequences.json`
**Feature:** A flag set early in a story that only becomes relevant several nodes later, with no reference to it in between.

### What the story does

`act1` sets `lied: true` if the player lies. `act2` makes no reference to `lied`. `act3` has a conditional inset and a conditional choice both gated on `lied: true`. The consequence of a choice in act 1 only surfaces in act 3.

### Engine code path

**State lifetime** — `Engine._state` is a plain dict that lives for the entire run. It is initialized to `{}` at `Engine.__init__()` and only cleared by `Engine._reset()` (which fires on play-again or new game). Nothing in the engine evicts or expires flags. A flag set in act 1 is readable in act 3, act 30, or the final ending node — wherever the story checks it.

**`act2` is a pass-through** — `act2` has no `insets`, no `overlays`, and its single choice has no `requires` or `sets`. The engine renders it normally and calls `_advance()`, which writes `visited_act3 = True` but leaves `lied` untouched. State accumulates; it never retracts.

**Combined gating at `act3`** — Two different element types are gated on the same flag simultaneously:

- Inset: `{ "text": "They remember your lie.", "requires": { "lied": true }, "position": "before", "style": "warning" }`
- Choice: `{ "label": "Face the consequences", "next": "end_bad", "requires": { "lied": true } }`

Both go through `_check_requires()` independently. The engine filters insets at `src/engine.py:49` and choices at `src/engine.py:43` — the same method is called on both, making the behavior consistent: an unset or false `lied` hides both the inset and the "Face the consequences" choice.

**The player who told the truth** — `lied` is never set, so `self._state.get("lied")` returns `None`. `_check_requires()` for `requires: { "lied": true }` sees `None != True` and returns `False`. The inset is absent; the bad-ending choice is absent; the only visible choice is "Walk away clean." The structure of act 3 differs completely based on a decision made in act 1, with nothing in act 2 telegraphing the divergence.

### Key references

| Symbol | Location |
|---|---|
| `_state` lifetime | `src/engine.py:27`, `src/engine.py:131` |
| `_check_requires()` missing-key returns `None` | `src/engine.py:77` |
| Inset filtering | `src/engine.py:49` |
| Choice filtering | `src/engine.py:43` |

---

## 18 — Multi-Condition Gating

**Story:** `stories/examples/18_multi_condition_gating.json`
**Feature:** A single choice gated on two simultaneous conditions — boolean AND integer/string — plus list-membership as OR within one condition.

### What the story does

The "Open the door" choice requires `{ "has_key": true, "clearance": ["red", "blue"] }` — both a boolean flag AND a string-as-list-member check. The player must satisfy both independently. The start node loops on itself so the player can acquire prerequisites in any order.

### Engine code path

**`_check_requires()` iterates all pairs** (`src/engine.py:75`):

```python
def _check_requires(self, requires: dict) -> bool:
    for key, condition in requires.items():
        current = self._state.get(key)
        if isinstance(condition, bool):
            if current != condition: return False
        elif isinstance(condition, int):
            ...
        elif isinstance(condition, str):
            if current != condition: return False
        elif isinstance(condition, list):
            if current not in condition: return False
    return True
```

For `{ "has_key": true, "clearance": ["red", "blue"] }`:
1. `key="has_key"`, `condition=True` → bool branch. If `_state["has_key"]` is not `True`, return `False`.
2. `key="clearance"`, `condition=["red", "blue"]` → list branch. If `_state["clearance"]` is not in the list, return `False`.
3. Both passed → return `True`.

**AND is the only dict-level semantic** — Multiple keys in a single `requires` dict are always AND. There is no OR at the dict level. To express "A or B," either use a list value (for a single flag with multiple acceptable values) or create two separate choices with different `requires`.

**OR via list** — `["red", "blue"]` means "current value of `clearance` must be a member of this list." The check is `current not in condition` using Python's `in` operator. This handles OR within a single flag's acceptable values.

**The self-looping start node** — `start` has choices that all set `next: "start"`. This means the player can return to the same node repeatedly, accumulating flags across visits. The engine supports this natively — `_advance()` sets `visited_start = True` on each visit but that flag is never checked in this story.

**Validation of list values** — `StoryLoader._parse_requires()` (`src/story.py:391`) checks that list values are non-empty and contain only strings. An empty list would make the condition unsatisfiable and is rejected at load time.

### Key references

| Symbol | Location |
|---|---|
| `_check_requires()` full implementation | `src/engine.py:75` |
| List-value validation in `_parse_requires()` | `src/story.py:391` |
| Multi-key AND iteration | `src/engine.py:76` |
| List-membership branch | `src/engine.py:88` |

---

## 19 — Conditional Inline Text

**Story:** `stories/examples/19_conditional_inline_text.json`
**Feature:** Flag-conditional spans embedded directly in text fields — node text, insets, and overlays — resolved at runtime without branching to a separate node.

### What the story does

Two choices on the intro node lead to the same `lobby` node: one sets `is_staff: true`, the other does not. The lobby node uses `{is_staff?...|...}` spans in its main text, an inset, and an overlay — producing different prose for staff vs visitors, all within a single node.

### Syntax

```
{flag?shown when true|shown when false}
```

The `|false branch` is optional. When omitted and the condition is false, the span collapses to an empty string — the inset in this story uses that form:

```json
{ "text": "{is_staff?STAFF ACCESS GRANTED}", "style": "system", "position": "before" }
```

If `is_staff` is false or missing, nothing renders in its place.

### Truthiness

| State value | Resolves to |
|---|---|
| `true` | true branch |
| `false` | false branch |
| integer ≥ 1 | true branch |
| integer 0 | false branch |
| non-empty string | true branch |
| empty string `""` | false branch |
| flag missing from state | false branch |

Flag names must match `\w+` (letters, digits, underscores). Flags with hyphens or dots in their names cannot be referenced in inline syntax.

### Engine code path

**Module-level regex** (`src/engine.py`):

```python
_INLINE_RE = re.compile(r"\{(\w+)\?([^|{}]*?)(?:\|([^{}]*?))?\}")
```

Requires `?` in the pattern, so `{player_name}` (no `?`) is left intact.

**Resolver** (`src/engine.py`):

```python
@staticmethod
def _resolve_inline(text: str, state: dict) -> str:
    def _replace(m: re.Match) -> str:
        true_b = m.group(2)
        false_b = m.group(3) or ""
        return true_b if state.get(m.group(1)) else false_b
    return _INLINE_RE.sub(_replace, text)
```

Uses Python truthiness: `True`, non-zero int, and non-empty string are truthy. A missing flag evaluates as falsy.

**Called in `Engine.run()`** after visibility filtering, before display calls:

```python
node_text     = self._resolve_inline(node.text, self._state)
before_insets = [dataclasses.replace(i, text=self._resolve_inline(i.text, self._state)) for i in before_insets]
after_insets  = [dataclasses.replace(i, text=self._resolve_inline(i.text, self._state)) for i in after_insets]
before        = [dataclasses.replace(o, text=self._resolve_inline(o.text, self._state)) for o in before]
after         = [dataclasses.replace(o, text=self._resolve_inline(o.text, self._state)) for o in after]
```

Original `Node`, `Inset`, and `Overlay` objects are never mutated — `dataclasses.replace()` creates copies with resolved text.

### Coexistence with Variable Text Substitution

Variable Text Substitution (example 21) uses `{key}` — no `?`. The conditional regex will not match those patterns. Variable substitution runs first; conditional inline runs second. This means substituted values can appear inside conditional branches — e.g. `{known?Hello, {player_name}!|Hello, stranger!}` resolves correctly.

### Key references

| Symbol | Location |
|---|---|
| `_INLINE_RE` | `src/engine.py` |
| `Engine._resolve_inline()` | `src/engine.py` |
| Resolve block in `Engine.run()` | `src/engine.py`, after visibility filtering |
| Unit tests | `tests/test_engine.py`, section "Conditional inline text: _resolve_inline unit tests" |
| Integration tests | `tests/test_engine.py`, section "Conditional inline text: integration tests" |

---

## 20 — Pause Token

**Story:** `stories/examples/20_pause_token.json`
**Feature:** `{pause}` embedded in node or ending `text` injects a configurable delay mid-stream during typewriter playback. Stripped silently in non-typewriter mode.

### What the story does

A radio story with three endings. The `signal` node demonstrates `{pause}` mid-sentence — the typewriter halts for 500 ms between the static description and the voice cutting through. Two endings (`ending_respond`, `ending_leave`) each carry a `{pause}` of their own, showing the token works in ending text too.

### Syntax

```
"text": "You adjust the frequency.{pause}A voice cuts through."
```

`{pause}` can appear anywhere in a `text` field — mid-sentence, after punctuation, multiple times. It has no effect in insets or overlays.

### Behaviour

| Mode | Effect |
|---|---|
| Typewriter on | Halts character streaming for `typewriter.pause_ms` milliseconds (default 500) |
| Typewriter off | Token stripped silently — rendered text contains no `{pause}` |
| Player presses a key during pause | Skips immediately to full clean text (token stripped) |

### Configuration

```json
{
  "typewriter": {
    "pause_ms": 500
  }
}
```

`pause_ms` lives under `typewriter` in `settings.json`. It is not exposed in the in-game settings screen — authors or players edit `settings.json` directly.

### Engine code path

`{pause}` is a display-layer token only. `Engine._resolve_inline()` does not match it — its regex requires `?` after the key name, so `{pause}` passes through unchanged.

**`_strip_pause_tokens`** (`src/display.py`):

```python
def _strip_pause_tokens(text: str) -> str:
    return text.replace("{pause}", "")
```

**`_typewrite`** (`src/display.py`) — simplified:

```python
pause_s = self._cfg.get("typewriter", {}).get("pause_ms", 500) / 1000
clean_text = _strip_pause_tokens(text)
segments = text.split("{pause}")
for seg_idx, segment in enumerate(segments):
    for char in segment:
        # ... stream character, check for keypress ...
    if seg_idx < len(segments) - 1:
        if _key_pending():
            live.update(make_panel(clean_text))  # skip shows clean text
            return
        time.sleep(pause_s)
```

**Non-typewriter paths** in `show_node` and `show_ending`:

```python
self.console.print(make(_strip_pause_tokens(node_text)))
```

### Key references

| Symbol | Location |
|---|---|
| `_strip_pause_tokens()` | `src/display.py` |
| `_typewrite()` | `src/display.py` |
| `"pause_ms"` default | `src/config.py`, `_DEFAULTS["typewriter"]` |
| Unit tests | `tests/test_display.py`, section `_strip_pause_tokens` and `_typewrite: {pause} token` |

---

## 21 — Variable Text Substitution

**Story:** `stories/examples/21_variable_text_substitution.json`
**Feature:** `{key}` placeholders in any text field replaced at runtime with the current value of that flag.

### What the story does

The player picks a route (Northern, Southern, or Eastern). All three choices converge on `assigned`. `{route}` is substituted into the node text, an inset header, an overlay, and both ending texts — three different stories from one node.

### Syntax

```
"text": "You sign for the {route} assignment."
```

`{key}` without `?` is variable substitution. `{flag?true|false}` with `?` is conditional inline text (example 19). The two syntaxes coexist without interference.

### Behaviour

| Condition | Result |
|---|---|
| Key present in state | Replaced with `str(value)` |
| Key present, value is `""` | Replaced with empty string |
| Key absent from state | Placeholder left intact |

### Engine code path

**`_SUBST_RE`** (`src/engine.py:13`): `re.compile(r"\{(\w+)\}")` — matches any `{word}` without `?`.

**`Engine._substitute_vars()`** (`src/engine.py`):

```python
@staticmethod
def _substitute_vars(text: str, state: dict) -> str:
    def _replace(m: re.Match) -> str:
        val = state.get(m.group(1))
        return str(val) if val is not None else m.group(0)
    return _SUBST_RE.sub(_replace, text)
```

Missing key → `m.group(0)` (original placeholder preserved). Present key → `str(val)`.

**`_pt` closure in `Engine.run()`** — chains substitution before inline resolution:

```python
def _pt(text: str) -> str:
    return self._resolve_inline(self._substitute_vars(text, self._state), self._state)
```

Applied to node text, all insets, and all overlays via `dataclasses.replace()` copies.

### Key references

| Symbol | Location |
|---|---|
| `_SUBST_RE` | `src/engine.py:13` |
| `Engine._substitute_vars()` | `src/engine.py` |
| `_pt` closure in `Engine.run()` | `src/engine.py`, after visibility filtering |
| `substituteVars` (JS) | `web/engine.js` |
| Unit tests | `tests/test_engine.py`, section "Variable text substitution" |
| JS unit tests | `tests/test_web_engine.py`, section "substituteVars" |

---

## 22 — Protagonist Name Prompt

**Story:** `stories/examples/22_protagonist_name_prompt.json`
**Feature:** `meta.name_prompt` triggers a pre-game name input screen. The name is stored as the reserved `player_name` flag and available via `{player_name}` in all text fields.

### What the story does

The innkeeper greets the player by name on the first node. The room inset shows their name on the reservation. The key is engraved with it. Both endings reference the name — one in prose, one as a standalone overlay before the ending panel.

### Meta fields

```json
{
  "meta": {
    "name_prompt": "What is your name?",
    "name_default": "the stranger"
  }
}
```

`name_prompt` triggers the feature. `name_default` is the fallback when the player submits empty input and no settings name is available. `name_default` requires `name_prompt` to also be set.

### Launch flow

Fires after content warnings, before the first node. Skipped on save resume — the saved `player_name` is used directly. The input is pre-filled with the settings `player_name` value (default `"Felix"`).

**Fallback priority:** entered name → `meta.name_default` → settings name → reject (show error).

### Using `{player_name}` without `name_prompt`

`player_name` is always seeded from settings before the engine starts, regardless of whether the story declares `name_prompt`. A story using `{player_name}` with no prompt will show the player's globally saved name automatically.

### Engine code path

`main.py` `_launch_story()` reads `settings_name` and builds `initial_state = {"player_name": settings_name}` unconditionally. If `story.name_prompt` is set and no save exists, it fires the prompt and overwrites `initial_state["player_name"]` with the entered name.

`Engine.__init__` stores `initial_state` and seeds `_state` from it in both `_resolve_start()` (new game) and `_reset()` (play-again). `player_name` is present from the first node of every run.

### Key references

| Symbol | Location |
|---|---|
| `Story.name_prompt` / `name_default` | `src/story.py:74–75` |
| `StoryLoader` validation | `src/story.py:243–280` |
| `_launch_story()` wiring | `main.py` |
| `Engine.__init__` `initial_state` param | `src/engine.py:23` |
| `Display.prompt_protagonist_name()` | `src/display.py` |
| `renderNamePrompt()` / `renderAccessibleNamePrompt()` | `web/app.js` |
| Unit tests | `tests/test_story.py`, `tests/test_engine.py`, `tests/test_display.py` |
| JS parity tests | `tests/test_web_engine.py` |
