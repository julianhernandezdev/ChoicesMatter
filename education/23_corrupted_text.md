# 23 — Corrupted Text

**Story:** `stories/examples/23_corrupted_text.json`
**Feature:** `{corrupt}…{/corrupt}` inline spans mark text for glitch rendering — characters are replaced with noise from a configurable charset, leaving punctuation and spaces intact. Authors control intensity, mode, and an optional resolve style per-span; a node-level `corruption` field sets a baseline; `settings.json` provides global fallback defaults, an always-applied intensity multiplier, and controls the typewriter scramble/resolve animation timing.

## What the story does

An abandoned signal station. A node-level baseline `"corruption": 0.3` gives the station logs a low-level persistent glitch. Inline spans mark the most damaged passages at higher intensity. The ending nodes use `{corrupt:random}` for an unstable, flickering feel distinct from the deterministic glitch of mid-game prose.

Two spans demonstrate the resolve effect. The console's boot-up warning banner uses `decay` — the diagnostic overlay stabilizes into legible text as the terminal finishes waking from cold storage, the glitch shrinking away on its own. The recovered log's `CHEN:` line uses `cascade` — the recovery algorithm decoding the buried transmission ("IT RESPONDED") character by character, like a cipher breaking under brute force. The two `——` redaction spans (shutdown authorisation, reason) are deliberately left without a resolve style: they're permanently unknown, and punctuation like `—` is never corrupted in the first place, so there'd be nothing visible to resolve.

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

All span forms work in node `text`, inset `text`, and overlay `text`:

| Syntax | Effect |
|---|---|
| `{corrupt}text{/corrupt}` | Inherits node-level baseline and global settings defaults |
| `{corrupt:0.8}text{/corrupt}` | Sets intensity (0.0–1.0) for this span; mode inherited |
| `{corrupt:random}text{/corrupt}` | Sets mode for this span; intensity inherited |
| `{corrupt:0.8:random}text{/corrupt}` | Sets both intensity and mode explicitly |
| `{corrupt:0.8:random:decay}text{/corrupt}` | Sets intensity, mode, and resolve style — the span types in corrupted, then settles into its clean text |
| `{corrupt:0.8:random:cascade}text{/corrupt}` | Same, but the clean text is revealed one character at a time instead of decaying together |

**Parameter order:** intensity, then mode, then resolve style — always in that order. `{corrupt:0.8:random}` and `{corrupt:0.8:random:cascade}` are valid; putting `decay`/`cascade` before `mode` or `intensity` (e.g. `{corrupt:decay:0.8:random}`) is not validated and renders as literal text in the output (the player sees the raw `{corrupt:...}` and `{/corrupt}` markers as visible characters). The same rule already applied to putting `mode` before `intensity` — it now extends to the 4th param. Use the correct order `{corrupt:0.8:random:decay}` instead.

A span with `{corrupt:0.0}…{/corrupt}` renders completely clean. This is valid and can be used to shelter a phrase from a node-level baseline.

## Inheritance chain

Three levels supply values for any unspecified param:

```
inline span param → node-level corruption field → global settings defaults
```

A story-defined value at any level (span or node) fully **overrides** the global `Intensity Default`/`Mode Default` settings — it does not multiply with them. The global settings only apply when the story defines neither. Player-controlled `Intensity Multiplier` is layered on top of whichever value wins, always:

```
resolved_intensity = author_intensity if author_intensity is not None else cfg["corruption"]["intensity"]
effective_intensity = min(resolved_intensity × cfg["corruption"]["intensity_multiplier"], 1.0)
```

`resolve_style` follows the same span → node chain but has no global-settings fallback level — there is no `settings.json` default resolve style. Omitting it everywhere simply means the span never enters a resolve phase; it stays corrupted (or animates via scramble-only, if `animate` is on) for the rest of the render.

### Three-level example

```json
{
  "corruption": { "intensity": 0.3, "mode": "random" },
  "text": "Static on the line. {corrupt:0.9}CRITICAL FAILURE{/corrupt} confirmed. {corrupt:consistent}Sector 4 offline.{/corrupt}"
}
```

With default global settings (`intensity: 1.0`, `intensity_multiplier: 1.0`, `mode: "consistent"`):

| Span | Effective intensity | Effective mode | Source |
|---|---|---|---|
| `CRITICAL FAILURE` | `0.9 × 1.0 = 0.9` | `random` | span overrides node |
| `Sector 4 offline.` | `0.3 × 1.0 = 0.3` | `consistent` | span overrides node |

The surrounding prose (`"Static on the line."`, `"confirmed."`) is plain text — the node-level `corruption` field does NOT corrupt text outside of spans. It provides defaults for spans that do not specify their own params.

## Resolve effect

A `{corrupt}` span normally stays corrupted for the rest of its render once the scramble animation finishes. Adding a `resolve_style` — the optional 4th positional param, or a `"resolve_style"` key on the node `corruption` field — gives the span a second phase where it visibly settles back into its original clean text instead of staying garbled.

Narratively, the two styles read very differently:

- **`decay`** — the whole span decays back to normal together, like a corrupted memory slowly clarifying or a bad signal stabilizing. Intensity shrinks frame by frame until nothing is left corrupted.
- **`cascade`** — characters lock into their correct value one at a time, in mode-dependent order, like a redacted word being decrypted character-by-character or a cipher breaking under brute force.

Both styles start exactly like a normal span: scramble in (if `animate` is on), then a resolve phase begins automatically — no player input is needed to trigger it. Any keypress during either phase (scramble or resolve) skips straight to the fully clean text, never to the corrupted form.

**Worked example — decay:**

```json
{
  "text": "{corrupt:0.9:consistent:decay}The signal clears.{/corrupt}",
  "choices": [{ "label": "Next", "next": "cascade_test" }]
}
```

The span types in heavily corrupted (intensity `0.9`), then the corrupted glyphs shrink away together until the panel reads "The signal clears." in plain text.

**Worked example — cascade:**

```json
{
  "text": "{corrupt:0.9:random:cascade}TRANSMISSION DECODING{/corrupt}",
  "choices": [{ "label": "Finish", "next": "end" }]
}
```

The span types in heavily corrupted, then individual characters — `T`, `N`, `M`, `S`, `I`, `D`, and so on, in a shuffled order determined by the mode/seed — lock into their clean values one at a time until the full phrase "TRANSMISSION DECODING" is legible.

Resolve timing is controlled by three settings (all fall back to the scramble timing when left `null`): `resolve_frames` (decay's frame count, defaults to `scramble_frames`), `resolve_delay_ms` (decay's per-frame delay, defaults to `scramble_delay_ms`), and `cascade_stagger_ms` (delay between each character locking in during cascade, defaults to `scramble_delay_ms`).

In web accessible mode and with `corruption.enabled: false`, resolve-styled spans behave exactly like any other span: corruption is stripped entirely and the clean text renders immediately, with no animation.

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

When `typewriter.enabled` is true and `corruption.animate` is true, each `{corrupt}` span goes through two phases (three if it has a `resolve_style` — see [Resolve effect](#resolve-effect) above):

**Phase 1 — Scramble** (`scramble_frames` frames at `scramble_delay_ms` each): The span renders as a fully random noise block — different characters every frame, updating the `Live` panel in place. Any keypress skips directly to Phase 2 (or straight to the clean text, for a resolve-styled span).

**Phase 2 — Settle** (character by character at `typewriter.delay_ms`): The final corrupted form of the span streams character by character, exactly like normal typewriter prose. Any keypress skips to the end of the span (or to the clean text, for a resolve-styled span).

Plain text segments before and after the span stream normally. The existing skip-on-keypress behaviour extends to all phases, including the optional resolve phase: any keypress at any point during a span's animation skips straight to the fully assembled final text — a resolve-styled span's "final text" is always its clean form, never its corrupted form.

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
- A `resolve_style` param (span or node `corruption.resolve_style`) that isn't `"decay"` or `"cascade"` raises a `StoryValidationError` at load time.

## Settings reference

Twelve keys live under `"corruption"` in `settings.json`:

```json
{
  "corruption": {
    "enabled": true,
    "intensity": 0.6,
    "intensity_multiplier": 1.0,
    "mode": "consistent",
    "charset": "blocks",
    "custom_chars": "█▓▒░",
    "animate": true,
    "scramble_frames": 85,
    "scramble_delay_ms": 40,
    "resolve_frames": null,
    "resolve_delay_ms": null,
    "cascade_stagger_ms": null
  }
}
```

| Key | Type | Default | Meaning |
|---|---|---|---|
| `enabled` | bool | `true` | Master toggle — `false` renders clean text everywhere, strips all `{corrupt}` spans |
| `intensity` | float 0–1 | `0.6` | (Labelled **Intensity Default** in-game) Fallback intensity used only when neither span nor node specifies one — a story-defined intensity fully overrides this rather than multiplying with it |
| `intensity_multiplier` | float 0–1 | `1.0` | (Labelled **Intensity Multiplier** in-game) Always-applied accessibility scalar layered on top of whichever intensity wins (span → node → `intensity` default) |
| `mode` | string | `"consistent"` | (Labelled **Mode Default** in-game) Fallback mode when neither span nor node specifies one — same override-or-default behaviour as `intensity` |
| `charset` | string | `"blocks"` | Active character set — `"blocks"`, `"symbols"`, `"diacritics"`, or `"custom"` |
| `custom_chars` | string | `"█▓▒░"` | Character pool used only when `charset` is `"custom"` |
| `animate` | bool | `true` | Scramble-settle animation in typewriter mode; `false` renders statically |
| `scramble_frames` | int | `85` | Number of scramble frames before the span settles to its final corrupted form |
| `scramble_delay_ms` | int | `40` | Milliseconds between scramble frames |
| `resolve_frames` | int or `null` | `null` | Number of frames for a `decay` resolve; falls back to `scramble_frames` when `null` |
| `resolve_delay_ms` | int or `null` | `null` | Milliseconds between decay frames; falls back to `scramble_delay_ms` when `null` |
| `cascade_stagger_ms` | int or `null` | `null` | Milliseconds between each character locking in during a `cascade` resolve; falls back to `scramble_delay_ms` when `null` |

Access these in the CLI via **Settings → 10. Corruption →** from the story picker. The sub-screen exposes all twelve keys, showing `Auto` for any of the three resolve-timing keys left `null`. The `custom_chars` row is dimmed and non-interactive unless `charset` is `"custom"`.

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

With default global settings (`intensity_multiplier: 1.0`, `charset: "blocks"`, `mode: "consistent"`) — note `intensity`/`mode` defaults are irrelevant here since every span or its node already supplies its own value:

| Segment | Source | Effective intensity (`author × intensity_multiplier`) | Effective mode |
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
- `CorruptedSpan` — frozen dataclass (`text`, `intensity`, `mode`, `seed`, `resolve_style`)
- `TextSegments = list[str | CorruptedSpan]`
- `_text_seed(text, index)` — stable polynomial hash for consistent-mode seeds; deterministic across processes and platforms
- `_lcg_select(n_total, n_select, seed)` — seeded Fisher-Yates position selection for consistent mode; same constants shared with the JS port
- `corrupt_string(text, intensity, mode, seed, charset)` — applies corruption to one string
- `resolve_corruption(text, node_corruption)` — parses all `{corrupt}…{/corrupt}` spans, applies inheritance chain (including `resolve_style`), returns `TextSegments`
- `effective_mode(span_mode, cfg_corruption)` — resolves a span's mode: span value if set, else `cfg["corruption"]["mode"]`
- `effective_intensity(span_intensity, cfg_corruption)` — resolves a span's intensity (span value if set, else `cfg["corruption"]["intensity"]`), then applies `cfg["corruption"]["intensity_multiplier"]`, clamped to `1.0`
- `cascade_reveal_order(positions, mode, seed)` — given the already-corrupted character positions in a span, returns them shuffled into the order a `cascade` resolve should lock them back to clean

**`_pt()` closure in `Engine.run()`** (`src/engine.py`) chains corruption as step 3:

```
_substitute_vars(text, state)           # step 1 — {key} → value
→ _resolve_inline(result, state)        # step 2 — {flag?…} → branch
→ resolve_corruption(result, node_corruption)  # step 3 — {corrupt}…{/corrupt} → TextSegments
```

The engine passes `node.corruption` to `resolve_corruption` but does NOT resolve global-settings fallback or the intensity multiplier — that happens in the display layer via `effective_mode`/`effective_intensity`, where config is available.

**`src/display.py`** — `_assemble_text(segments, charset, cfg_corruption)` converts `TextSegments` to a final string. For each `CorruptedSpan`, it calls `effective_intensity`/`effective_mode` to resolve the span → node → global-default → multiplier chain, then `corrupt_string` with the result. Resolve-styled spans additionally bypass corruption entirely once their resolve phase completes — the render-time text is the clean original, not a corrupted string with intensity `0`. All render paths — `show_node`, `show_ending`, `_render_overlay`, `_inset_renderable` — call `_assemble_text` before constructing `Text` or `Panel` objects. The typewriter's decay/cascade animation phases live in the `_typewrite()` helper, which reads `resolve_frames`/`resolve_delay_ms`/`cascade_stagger_ms` (falling back to the scramble settings) and calls `cascade_reveal_order()` for cascade spans.

**JS parity** — `web/engine.js` exports `resolveCorruption()` with identical span parsing, inheritance chain, and seed formula (same LCG constants as Python), plus `resolve_style` parsing. `web/app.js` has `_assembleText()`, `_corruptString()`, and mirrors `effective_mode()`/`effective_intensity()`. `web/typewriter.js` `startTypewriter()` accepts `TextSegments` and runs the scramble animation plus, for resolve-styled spans, the decay/cascade resolve phase (mirroring `cascade_reveal_order()` for cascade). All accessible renderers call `_assembleText` with `enabled: false`.

## Key references

| Symbol | Location |
|---|---|
| `CHARSETS`, `CorruptedSpan`, `TextSegments` | `src/corruption.py` |
| `resolve_corruption()` | `src/corruption.py` |
| `corrupt_string()` | `src/corruption.py` |
| `effective_mode()` / `effective_intensity()` | `src/corruption.py` |
| `cascade_reveal_order()` | `src/corruption.py` |
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
