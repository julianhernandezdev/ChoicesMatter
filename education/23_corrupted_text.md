# 23 — Corrupted Text

**Story:** `stories/examples/23_corrupted_text.json`
**Feature:** `{corrupt}…{/corrupt}` inline spans mark text for glitch rendering — characters are replaced with noise from a configurable charset, leaving punctuation and spaces intact. Authors control intensity and mode per-span; a node-level `corruption` field sets a baseline; `settings.json` multiplies the global effect and controls the typewriter scramble-settle animation.

## What the story does

An abandoned signal station. A node-level baseline `"corruption": 0.3` gives the station logs a low-level persistent glitch. Inline spans mark the most damaged passages at higher intensity. The ending nodes use `{corrupt:random}` for an unstable, flickering feel distinct from the deterministic glitch of mid-game prose.

## Quick start

Add `{corrupt}…{/corrupt}` to any `text` field:

```json
{
  "text": "The readout says: {corrupt}SIGNAL LOST{/corrupt}. Nothing else.",
  "choices": [{ "label": "Check the logs", "next": "logs" }]
}
```

At the default global intensity (`1.0`), every non-punctuation letter in `SIGNAL LOST` is replaced with a block character. Spaces are never corrupted. Punctuation is never corrupted.

## Syntax

All four span forms work in node `text`, inset `text`, and overlay `text`:

| Syntax | Effect |
|---|---|
| `{corrupt}text{/corrupt}` | Inherits node-level baseline and global settings defaults |
| `{corrupt:0.8}text{/corrupt}` | Sets intensity (0.0–1.0) for this span; mode inherited |
| `{corrupt:random}text{/corrupt}` | Sets mode for this span; intensity inherited |
| `{corrupt:0.8:random}text{/corrupt}` | Sets both intensity and mode explicitly |

**Parameter order:** intensity first, then mode. `{corrupt:0.8:random}` is valid; `{corrupt:random:0.8}` is not validated and renders as literal text in the output (the player sees `{corrupt:random:0.8}` and `{/corrupt}` as visible characters). Use the correct order `{corrupt:0.8:random}` instead.

A span with `{corrupt:0.0}…{/corrupt}` renders completely clean. This is valid and can be used to shelter a phrase from a node-level baseline.

## Inheritance chain

Three levels supply values for any unspecified param:

```
inline span param → node-level corruption field → global settings defaults
```

Resolved author intensity is then multiplied by the player's global intensity multiplier:

```
effective_intensity = min(author_intensity × cfg["corruption"]["intensity"], 1.0)
```

### Three-level example

```json
{
  "corruption": { "intensity": 0.3, "mode": "random" },
  "text": "Static on the line. {corrupt:0.9}CRITICAL FAILURE{/corrupt} confirmed. {corrupt:consistent}Sector 4 offline.{/corrupt}"
}
```

With default global settings (`intensity: 1.0`, `mode: "consistent"`):

| Span | Effective intensity | Effective mode | Source |
|---|---|---|---|
| `CRITICAL FAILURE` | `0.9 × 1.0 = 0.9` | `random` | span overrides node |
| `Sector 4 offline.` | `0.3 × 1.0 = 0.3` | `consistent` | span overrides node |

The surrounding prose (`"Static on the line."`, `"confirmed."`) is plain text — the node-level `corruption` field does NOT corrupt text outside of spans. It provides defaults for spans that do not specify their own params.

## Mode comparison: consistent vs random

| Mode | Behaviour | When to use |
|---|---|---|
| `consistent` | Same input text always produces the same corrupted output — glyphs are fixed across all renders and all runs | Permanent damage, encoded noise, deliberate redaction. Reliable for insets re-rendered on every node visit. |
| `random` | Corruption re-rolls on each render — different glyphs every time | Live unstable signal, flickering interference, active jamming. |

In typewriter mode, `consistent` shows the scramble animation and then settles to the same final glyphs every time. `random` settles to a freshly sampled set on each render.

## Character sets

Four charsets are available, controlled globally in `settings.json`:

| Key | Characters | Character |
|---|---|---|
| `blocks` (default) | `█ ▓ ▒ ░` | Block fill — dense digital noise |
| `symbols` | `# @ ! ? & * ~` | Printable ASCII — lighter, typographic glitch |
| `diacritics` | `̈ ̊ ̃ ̂ ̄` | Unicode combining marks — stack visually on source characters |
| `custom` | Player-defined (`custom_chars`) | Any characters the player configures |

**`diacritics` warning:** Combining Unicode marks overlay the preceding character rather than replacing it, creating visually striking effects. However, `diacritics` is the most screen-reader-hostile charset — combining characters either cause literal pronunciation of each combining code point or are silently dropped by assistive technology, producing unpredictable audio output. Avoid this charset for narratively important text. The in-game settings screen labels it `diacritics (⚠ screen reader unfriendly)`.

## Typewriter behaviour

When `typewriter.enabled` is true and `corruption.animate` is true, each `{corrupt}` span goes through two phases:

**Phase 1 — Scramble** (`scramble_frames` frames at `scramble_delay_ms` each): The span renders as a fully random noise block — different characters every frame, updating the `Live` panel in place. Any keypress skips directly to Phase 2.

**Phase 2 — Settle** (character by character at `typewriter.delay_ms`): The final corrupted form of the span streams character by character, exactly like normal typewriter prose. Any keypress skips to the end of the span.

Plain text segments before and after the span stream normally. The existing skip-on-keypress behaviour extends to all phases: any keypress during scramble or settle skips to the fully assembled final text.

When `corruption.animate` is false or typewriter is off: spans render statically — corruption is applied once and the assembled text is displayed immediately.

## Accessibility

**Web player (accessible mode):** All `renderAccessible*()` renderers call `_assembleText(segments)` with `enabled: false`. Corruption is stripped entirely — the clean original text is passed to the DOM. The scramble animation never runs. Screen readers hear the intended words without interference from noise characters.

**Python CLI:** No automatic accessible mode exists. The player's escape hatch is `settings.json → "corruption" → "enabled": false`, which gives clean text everywhere and strips all `{corrupt}` spans. This is available in the in-game Settings → Corruption sub-screen.

**When to use `{obfuscated}` instead:** `{obfuscated}` on a choice renders a fixed `[REDACTED ██████]` placeholder regardless of any corruption settings — it is always consistent and not affected by the `enabled` toggle. Use `{obfuscated}` when the player should not know what an option is. Use `{corrupt}` when the text is readable-but-damaged and the player can partially make out the underlying words at lower intensities.

## Interaction with `{pause}`

Both tokens work in the same `text` field:

```json
"text": "You see the message: {corrupt:0.8}TRANSMISSION ERROR{/corrupt}.{pause}Then silence."
```

Processing order in the engine pipeline:
1. Variable substitution (`{key}` → value)
2. Conditional inline resolution (`{flag?…}` → branch)
3. Corruption span resolution (`{corrupt}…{/corrupt}` → `TextSegments`)
4. `{pause}` is handled by the display layer inside plain string segments during typewriter streaming

`{pause}` only fires in plain string segments. It has no effect inside a `{corrupt}` span. Place `{pause}` tokens in the plain text portions of your prose, not between corruption tags.

## Restrictions

- `{corrupt}` spans are **not** supported in choice `label` fields. Choice labels are excluded from all inline token processing — the same restriction that applies to Variable Text Substitution and conditional inline text.
- Nested `{corrupt}` spans are forbidden — `{corrupt}{corrupt}…{/corrupt}{/corrupt}` raises a `StoryValidationError` at load time.
- Every `{corrupt…}` open tag must have a matching `{/corrupt}` close tag. An unclosed span or a stray `{/corrupt}` raises a validation error at story load time.

## Settings reference

All eight keys live under `"corruption"` in `settings.json`:

```json
{
  "corruption": {
    "enabled": true,
    "intensity": 1.0,
    "mode": "consistent",
    "charset": "blocks",
    "custom_chars": "█▓▒░",
    "animate": true,
    "scramble_frames": 8,
    "scramble_delay_ms": 60
  }
}
```

| Key | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Master toggle — `false` renders clean text everywhere, strips all `{corrupt}` spans |
| `intensity` | float 0–1 | `1.0` | Global multiplier applied to every span's resolved author intensity |
| `mode` | string | `"consistent"` | Fallback mode when neither span nor node specifies one |
| `charset` | string | `"blocks"` | Active character set — `"blocks"`, `"symbols"`, `"diacritics"`, or `"custom"` |
| `custom_chars` | string | `"█▓▒░"` | Character pool used only when `charset` is `"custom"` |
| `animate` | bool | `true` | Scramble-settle animation in typewriter mode; `false` renders statically |
| `scramble_frames` | int | `8` | Number of scramble frames before the span settles to its final corrupted form |
| `scramble_delay_ms` | int | `60` | Milliseconds between scramble frames |

Access these in the CLI via **Settings → 10. Corruption →** from the story picker. The sub-screen exposes all eight keys. The `custom_chars` row is dimmed and non-interactive unless `charset` is `"custom"`.

## Complete worked example

A node with a `0.4` node-level baseline and two inline span overrides:

```json
{
  "id": "broadcast_room",
  "text": "The room hums. {corrupt:0.9:random}EMERGENCY BROADCAST IN PROGRESS{/corrupt}\n\nYou read the ticker: {corrupt:0.5}Channel 7 reports no signal from the northern grid.{/corrupt}\n\nA handwritten note says: 'Do not adjust your set.'",
  "corruption": 0.4,
  "choices": [
    { "label": "Try to boost the signal", "next": "boost" },
    { "label": "Read the operator log", "next": "log" }
  ]
}
```

With default global settings (`intensity: 1.0`, `charset: "blocks"`, `mode: "consistent"`):

| Segment | Source | Effective intensity | Effective mode |
|---|---|---|---|
| `"The room hums."` | Plain text | — | no corruption |
| `EMERGENCY BROADCAST IN PROGRESS` | `{corrupt:0.9:random}` | `0.9 × 1.0 = 0.9` | `random` |
| `Channel 7 reports no signal…` | `{corrupt:0.5}` | `0.5 × 1.0 = 0.5` | `consistent` (node default) |
| `"A handwritten note says: 'Do not adjust your set.'"` | Plain text | — | no corruption |

**Rendered output (static, blocks charset, representative):**

```
The room hums. ██E█G█N█Y █R█A█C█S█ I█ P█O█R█S█

You read the ticker: Ch█nn█l 7 r█p█rt█ no █i█n█l from the n█rt██rn gr█d.

A handwritten note says: 'Do not adjust your set.'
```

The heading changes on every render (random mode). The ticker is identical on every render (consistent mode). The note is always clean.

## Engine code path

**`src/corruption.py`** — core module:
- `CHARSETS` — the four built-in character pools
- `CorruptedSpan` — frozen dataclass (`text`, `intensity`, `mode`, `seed`)
- `TextSegments = list[str | CorruptedSpan]`
- `_text_seed(text, index)` — stable polynomial hash for consistent-mode seeds; deterministic across processes and platforms
- `_lcg_select(n_total, n_select, seed)` — seeded Fisher-Yates position selection for consistent mode; same constants shared with the JS port
- `corrupt_string(text, intensity, mode, seed, charset)` — applies corruption to one string
- `resolve_corruption(text, node_corruption)` — parses all `{corrupt}…{/corrupt}` spans, applies inheritance chain, returns `TextSegments`

**`_pt()` closure in `Engine.run()`** (`src/engine.py`) chains corruption as step 3:

```
_substitute_vars(text, state)           # step 1 — {key} → value
→ _resolve_inline(result, state)        # step 2 — {flag?…} → branch
→ resolve_corruption(result, node_corruption)  # step 3 — {corrupt}…{/corrupt} → TextSegments
```

The engine passes `node.corruption` to `resolve_corruption` but does NOT apply the global multiplier — that happens in the display layer where config is available.

**`src/display.py`** — `_assemble_text(segments, charset, cfg_corruption)` converts `TextSegments` to a final string. For each `CorruptedSpan`, it calls `corrupt_string` with intensity clamped to `min(span.intensity × cfg["corruption"]["intensity"], 1.0)`. All render paths — `show_node`, `show_ending`, `_render_overlay`, `_inset_renderable` — call `_assemble_text` before constructing `Text` or `Panel` objects.

**JS parity** — `web/engine.js` exports `resolveCorruption()` with identical span parsing, inheritance chain, and seed formula (same LCG constants as Python). `web/app.js` has `_assembleText()` and `_corruptString()`. `web/typewriter.js` `startTypewriter()` accepts `TextSegments` and runs the scramble-settle animation for each span. All accessible renderers call `_assembleText` with `enabled: false`.

## Key references

| Symbol | Location |
|---|---|
| `CHARSETS`, `CorruptedSpan`, `TextSegments` | `src/corruption.py` |
| `resolve_corruption()` | `src/corruption.py` |
| `corrupt_string()` | `src/corruption.py` |
| `_text_seed()` / `_lcg_select()` | `src/corruption.py` |
| `_pt()` chaining corruption as step 3 | `src/engine.py` |
| `_assemble_text()` | `src/display.py` |
| `resolveCorruption()` (JS) | `web/engine.js` |
| `_assembleText()` / `_corruptString()` (JS) | `web/app.js` |
| `startTypewriter` with `TextSegments` (JS) | `web/typewriter.js` |
| `"corruption"` defaults | `src/config.py`, `_DEFAULTS["corruption"]` |
| `Node.corruption` field | `src/story.py` |
| `_parse_corruption()` validation | `src/story.py` |
| `_validate_corruption_spans()` | `src/story.py` |
| Unit tests | `tests/test_corruption.py`, `tests/test_story.py`, `tests/test_display.py`, `tests/test_engine.py` |
| JS parity tests | `tests/test_web_engine.js` |
