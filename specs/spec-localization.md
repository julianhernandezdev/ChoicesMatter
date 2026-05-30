# Spec: Language Support & Learning Mode

**Status:** Pre-roadmap / Design  
**Motivation:** Use Choices Matter as a Spanish-learning platform — stories authored in the target language, with optional English assistance available on demand. Architecture must generalize to any language pair.

---

## Overview

This feature has two layers:

1. **Language tagging** — stories declare what language they are written in (`meta.lang`). The engine uses this for TTS voice selection, STT recognition tuning, and UI hints.
2. **Learning mode** — bilingual stories carry an optional `text_translation` field. Players choose how much assistance they want at story launch.

The feature is additive. Stories without `meta.lang` behave identically to today.

---

## Play Modes

When a story has `translation_lang` set in its meta, players are offered a mode selection before the story starts (after the content warnings screen, before the first node):

| Mode | Description |
|---|---|
| **Immersion** | Story rendered entirely in target language. No translations visible. |
| **Guided** | Story in target language; translations revealed on demand. |
| **Passive** | Story rendered in translation language only (English). Equivalent to today's behavior for translated stories. |

If `translation_lang` is absent, no mode prompt is shown — the story plays in whatever language it was authored in.

Mode selection is session-only. It is not saved to the save file — players choose fresh each run. A `default_play_mode` setting controls what is pre-selected in the prompt.

---

## Story JSON Format Changes

### `meta` additions

```json
{
  "meta": {
    "id": "el_misterio",
    "title": "El Misterio de la Casa Vieja",
    "lang": "es",
    "region": "MX",
    "translation_lang": "en",
    "start_node": "intro"
  }
}
```

| Field | Required | Notes |
|---|---|---|
| `lang` | No | BCP-47 language code for the primary story text (`"es"`, `"fr"`, `"ja"`). |
| `region` | No | BCP-47 region subtag (`"MX"`, `"ES"`, `"AR"`). Combined with `lang` for TTS voice selection (`es-MX`). If absent, TTS uses `lang` only. |
| `translation_lang` | No | Language code of the `*_translation` fields. Required if any node uses `text_translation`. Enables the mode-selection prompt at story launch. |

### `nodes` additions

```json
{
  "intro": {
    "text": "Entras en la habitación oscura. El aire huele a humedad y a años olvidados.",
    "text_translation": "You enter the dark room. The air smells of dampness and forgotten years.",
    "choices": [
      {
        "label": "Encender la luz",
        "label_translation": "Turn on the light",
        "next": "lights_on"
      },
      {
        "label": "Quedarte en la oscuridad",
        "label_translation": "Stay in the darkness",
        "next": "dark_room"
      }
    ]
  }
}
```

| Field | Required | Notes |
|---|---|---|
| `text_translation` | No | Full node prose in translation language. Shown in guided mode. |
| `label_translation` | No | Choice label in translation language. Shown in guided mode alongside the primary label. |

Insets and overlays may also carry `text_translation` using the same pattern.

### Authored convention

Authors write the primary story in the target language (`text`). Translations are additive — a story can ship without them and add `*_translation` fields later without any engine changes.

---

## Engine Changes

`Engine` passes `play_mode` (an enum: `immersion | guided | passive`) to all `Display` methods that render node content. `play_mode` is set at story launch and lives in session state — it is **not** persisted in the save file and **not** part of `_state` (not accessible via `requires`/`sets`).

```python
class PlayMode(Enum):
    IMMERSION = "immersion"
    GUIDED    = "guided"
    PASSIVE   = "passive"
```

`Engine` gains a `_play_mode: PlayMode` attribute, defaulting to `IMMERSION` (or the user's `default_play_mode` config setting) if no mode selection prompt is shown.

No core navigation or flag logic changes. Play mode is purely a display concern.

---

## Display Changes

### CLI (`display.py`)

`show_node()` and `show_choices()` gain a `play_mode` parameter.

**Passive mode:** render `text_translation` as the main text (if present); fall back to `text` if absent.

**Guided mode:** render primary `text` normally; add a dim "— ? for translation —" rule below. When player presses `?`, re-render the node with the translation expanded (shown as a styled inset below the main text). `?` is only active while the choice prompt is waiting.

**Immersion mode:** render only primary `text`. Translation fields are ignored.

Choice label rendering in guided mode: primary label on one line; `label_translation` on the next line in dim italic, indented.

```
  [1] Encender la luz
      Turn on the light
  [2] Quedarte en la oscuridad
      Stay in the darkness
```

### Web (`app.js`)

**Immersion / passive:** straightforward — render the appropriate text field directly.

**Guided mode:** primary text is rendered normally. Beneath each prose block, a small collapse toggle:

```html
<button class="translation-toggle" aria-expanded="false">▸ translation</button>
<div class="translation-panel" hidden>You enter the dark room…</div>
```

Clicking expands/collapses. Toggle state is per-node and resets on navigation.

Choice labels in guided mode: Spanish label above, English in a `<small class="translation-label">` below.

Focus management: translation toggles are keyboard-focusable but are not in the primary tab order — they appear after all choice buttons in source order.

---

## Story Picker Changes

Stories with `meta.lang` set show a small language tag in the picker entry:

```
  [2] El Misterio de la Casa Vieja  [ES]   4/6 endings
```

CLI: appended to the title line in dim.  
Web: small pill badge next to the title.

---

## Validation Additions

- `meta.lang` must match `^[a-z]{2,3}$` if present (two- or three-letter ISO 639 code).
- `meta.region` must match `^[A-Z]{2}$` if present.
- `meta.translation_lang` must match the same pattern as `meta.lang` if present.
- If any node has `text_translation` or `label_translation`, `meta.translation_lang` must be declared.
- `text_translation` and `label_translation`: non-empty strings when present.

---

## Settings Additions

### CLI (`settings.json`)
```json
{
  "language_learning": {
    "default_play_mode": "guided"
  }
}
```

### Web (localStorage, inside existing settings blob)
```json
{
  "default_play_mode": "guided"
}
```

Settings screen: new "Language" section with a `default_play_mode` row that cycles `guided → immersion → passive`.

---

## Open Questions

1. **Glossary / vocabulary tracking** — Should the engine track which Spanish words the player has seen across sessions? This would enable a "words learned" counter and spaced repetition prompts. Out of scope for this spec but the `meta.lang` flag makes it possible later.
2. **Inline word tooltips** — In the web guided mode, should individual Spanish words be tappable to reveal their English meaning? Requires a per-word dictionary or author-provided glossary. Higher authoring cost; defer.
3. **Required vs optional translations** — Should `text_translation` be required whenever `meta.translation_lang` is declared, or always optional? Optional is lower authoring burden but produces inconsistent guided mode UX. Recommended: optional with a validation warning (not error) if some nodes have it and others don't.
4. **Multiple translation languages** — Not in scope. A single `translation_lang` per story is the constraint for now.
5. **Story picker language filter** — Should players be able to filter the library by language? Useful when the library grows. Defer to a separate spec.
