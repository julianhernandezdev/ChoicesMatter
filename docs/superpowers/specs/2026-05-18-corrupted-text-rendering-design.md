# Corrupted Text Rendering — Design Spec

**Date:** 2026-05-18
**Scope:** Python CLI (web player follow-on, top priority post-CLI ship)

---

## Goal

Add a `"corrupted"` named style and a `"corrupted": true` field on choices that renders text with digital noise — leet substitutions and block characters. Purely a display effect; the underlying text is never modified.

---

## Aesthetic

Terminal-pure digital noise. Two character pools:

| Pool | Characters | When used |
|---|---|---|
| Leet | `a→4  e→3  i→1  o→0  s→5  t→7  g→9  b→6  l→|` | Low-to-mid intensity |
| Light block | `░  ▒` | Mid intensity |
| Heavy block | `▓  █` | High intensity |

Spaces and punctuation are never corrupted — structure is preserved. As intensity increases, weight shifts from leet substitutions toward block characters.

---

## Scope

| Surface | Supported | Notes |
|---|---|---|
| Insets | Yes | via `"style": "corrupted"` |
| Overlays | Yes | via `"style": "corrupted"` |
| Choice labels | Yes | via `"corrupted": true` on choice |
| Node `text` (prose) | No | Roadmap item |

---

## Corruption Modes

**Dynamic (default):** Corruption re-rolls on every render. Feels like a live unstable signal. Pairs naturally with the stagger effect on overlays and choices.

**Static (opt-in):** Corruption is seeded from the text content — same text always produces the same glyphs. Enables deterministic authorial intent. Activated via `"static": true` in the style config.

Static seeding uses a stable hash: `sum(ord(c) * i for i, c in enumerate(text, 1)) % 2**32`. No external dependency; deterministic across processes.

---

## Story JSON Format

### Insets and overlays — no schema change

Uses the existing named style system:

```json
{
  "text": "Th1s m3ssage is not for you.",
  "style": "corrupted"
}
```

### Choice labels — new `"corrupted"` boolean

```json
{
  "label": "Trust the signal",
  "next": "trust",
  "corrupted": true
}
```

Mirrors `"obfuscated": true` exactly. If both `"obfuscated"` and `"corrupted"` are set on the same choice, `obfuscated` takes precedence — the label is already hidden, corrupting `████ ██████` is meaningless. The display layer handles this by checking `obfuscated` first; no validation error is raised.

---

## Architecture

### New module: `src/corrupt.py`

The corruption transform is algorithmic, not a rendering concern. Isolated in its own module for independent testability and as a reference spec for the future JS port.

**Public interface:**

```python
def corrupt(text: str, intensity: float, static: bool = False) -> str
```

- `intensity`: `0.0` = no change, `1.0` = maximum noise
- `static=True`: seeds `random.Random` from `_text_hash(text)`; same input always produces same output
- `static=False` (default): unseeded `random.Random()`; different result each call
- `_text_hash` is a private helper inside `corrupt.py`

### `src/config.py` — new default style entry

```python
"corrupted": {
    "color":     "dark_orange",
    "dim":       False,
    "italic":    False,
    "bold":      False,
    "underline": False,
    "strike":    False,
    "prefix":    "",
    "intensity": 0.35,
    "static":    False,
},
```

`intensity` and `static` sit alongside standard style fields. The existing `_STYLE_FIELDS` tuple and rendering path ignores them — they are read explicitly by `display.py` when corruption is triggered.

**Trigger mechanism:** `display.py` checks `cfg.get("intensity") is not None` after resolving a style config. Any named style with an `intensity` key activates corruption. This means future named styles can opt into corruption without code changes.

**User override shape** (`settings.json`):

```json
{
  "styles": {
    "corrupted": {
      "intensity": 0.6,
      "static": true
    }
  }
}
```

Deep-merge handles partial overrides cleanly.

### `src/story.py` — `Choice` dataclass

New field added to `Choice`:

```python
corrupted: bool = False
```

Validated in `_parse_choices()` using the same pattern as `obfuscated`: must be `true` or `false`; raises `StoryValidationError` otherwise.

### `src/display.py` — three render paths

**`_inset_renderable`:** After resolving style config, if `intensity` is present, apply `corrupt()` to the text before building the `Text` object. `Text()` takes a plain string — no escaping needed.

**`_render_overlay`:** Same check. The corruption transform is applied first (to a local variable), then: in the non-debug path, the result is passed through `rich.markup.escape()` before interpolation into `console.print()` — the leet table includes `|` which Rich interprets as a style separator. In the debug path, the corrupted text is passed to `Text()` directly (no escaping needed; `Text()` treats content as plain string).

**`show_choices`:** `obfuscated` check runs first. If `choice.corrupted` is true, resolve the `"corrupted"` style config, apply `corrupt()` to the label, and escape the result. In debug mode, append a dim `[corrupted]` tag — consistent with debug tags on insets and overlays.

One new import: `from rich.markup import escape`.

---

## Debug Mode

Corrupted choices show the rendered (noisy) label plus a dim `[corrupted]` tag in debug mode. There is nothing to "reveal" — corruption is display-only — so debug mode does not bypass it.

---

## CLAUDE.md Updates

- Add `corrupted` row to the Choice object table (alongside `obfuscated`)
- Add `corrupted` validation rule to the Validation Rules section
- Note that `"corrupted"` is a built-in named style for insets and overlays

---

## Testing Strategy

**`tests/test_corrupt.py`**
- `intensity=0.0` → output equals input
- `intensity=1.0` → no original alpha characters survive
- Spaces and punctuation → never altered at any intensity
- `static=True`, same text → identical output across multiple calls
- `static=False`, high intensity → output differs across N calls
- Return type is always `str`

**`tests/test_story.py`**
- `"corrupted": true` → `Choice.corrupted == True`
- `"corrupted": false` → `Choice.corrupted == False`
- Absent → defaults to `False`
- `"corrupted": "yes"` / `"corrupted": 1` → `StoryValidationError`

**`tests/test_display.py`**
- Inset with `style="corrupted"` → rendered text differs from source text
- Overlay with `style="corrupted"` → rendered text differs from source text
- Choice with `corrupted=True` → label differs from source
- Choice with `obfuscated=True` and `corrupted=True` → obfuscated wins; renders as `████`
- Debug mode + corrupted choice → `[corrupted]` tag present in output
- `intensity=0.0` in config → text passes through unchanged

**`tests/test_config.py`**
- `load_settings()` includes `styles.corrupted` with `intensity=0.35` and `static=False`
- Partial override deep-merges correctly; unspecified keys retain defaults

---

## Out of Scope (This Iteration)

- Node `text` (prose) corruption — roadmap item
- Per-element intensity override on individual insets/overlays/choices — roadmap item
- Configurable character substitution table — YAGNI; the digital noise aesthetic is a fixed constraint
- Web player implementation — top priority follow-on after CLI ships

---

## ARG Note

`src/corrupt.py` has a placement entry in `docs/arg/engine-layer.md`. The function takes clean text and returns damaged text — Felix's Precise Voice notes that "the source text is unchanged." The Unmoored Voice has a question about that. Comment draft is a stub pending the ARG writing pass.
