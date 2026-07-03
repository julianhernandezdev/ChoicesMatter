# Spec: Text-to-Speech

**Status:** Pre-roadmap / Design  
**Motivation:** Read story prose aloud — primarily useful for language learning (hearing correct Spanish pronunciation) and accessibility (eyes-free play). Two delivery passes: MVP uses built-in platform TTS; drama pass adds per-character voice casting and emotional prosody.

---

## Overview

| Pass | What it delivers |
|---|---|
| **MVP** | Platform TTS reads node text aloud after it appears. Language inherits from `meta.lang`. Typewriter bypassed when TTS is on. Toggle via settings. |
| **Drama** | Per-node voice/emotion hints in story JSON. Author-defined voice cast in meta. Prosody adjustments (rate, pitch, volume) driven by emotion. Optional cloud TTS backend for higher quality. |

Both passes share the same settings schema and module interfaces — drama is additive.

---

## MVP (Pass 1)

### Platform approach

| Platform | Primary | Fallback |
|---|---|---|
| Web | Web Speech API (`speechSynthesis`) — zero install, built into Chrome/Edge/Safari/Firefox | None needed |
| CLI | `pyttsx3` (pure Python, cross-platform, no API key) | OS commands: `say` (macOS), `espeak` / `espeak-ng` (Linux) |

TTS is an optional dependency on CLI. If `pyttsx3` is not installed, `TTSEngine.is_available()` returns `False` and TTS-related settings are hidden. The engine never crashes due to missing TTS.

### Language selection

When a story has `meta.lang` set, TTS uses that language. Combined with `meta.region` when available:
- `lang: "es", region: "MX"` → TTS locale `es-MX`
- `lang: "es"` (no region) → TTS locale `es` (browser/OS picks default regional variant)
- No `meta.lang` → TTS locale falls back to system locale

For Spanish learning specifically: the player hears native-accent Spanish pronunciation automatically, without any configuration.

### Typewriter interaction

When TTS is enabled:
- **Typewriter is bypassed** — text appears instantly, then TTS begins reading.
- Reason: simultaneous character-by-character animation and audio is disorienting.
- If the player has typewriter on and TTS off, typewriter behaves normally.
- If TTS is on, the typewriter setting is effectively suspended for the session (not changed in settings).

### Skip / stop

- **Web:** clicking anywhere on the page, or pressing any key, stops the current utterance. Play continues normally.
- **CLI:** any keypress stops TTS. The existing typewriter skip key (`any key`) is reused.

TTS auto-stops when a choice is submitted (before the next node begins rendering).

### Choices

`read_choices: false` by default. When enabled, TTS reads each choice label (in sequence) after node prose finishes. Useful for eyes-free play. For language learning, hearing the Spanish choice labels read aloud before deciding is high-value — authors should document that enabling this setting enriches the learning experience.

### New module: `src/tts.py` (CLI)

```python
class TTSEngine:
    def speak(self, text: str, lang: str | None = None) -> None:
        """Speak text in a background thread. Returns immediately."""
    def stop(self) -> None:
        """Stop current utterance immediately."""
    def is_available(self) -> bool:
        """Returns False if pyttsx3 is not installed."""
    def wait(self) -> None:
        """Block until current utterance finishes."""
    @property
    def enabled(self) -> bool: ...
```

`Display` receives a `TTSEngine` instance at init (injected by `main.py`). `Display.show_node()` calls `tts.speak(node_text, lang=story.meta.lang)` after rendering. `Display` calls `tts.stop()` before any screen transition.

### New module: `web/tts.js`

```js
export function isTtsAvailable()        // false if speechSynthesis not present
export function isTtsEnabled()          // checks settings
export function ttsSpeak(text, lang)    // speak; cancels any in-progress utterance first
export function ttsStop()               // cancel current utterance
export function isTtsSpeaking()         // true while utterance is active
export function getTtsVoice(lang)       // returns best available SpeechSynthesisVoice for lang
```

`app.js` calls `ttsSpeak()` after setting `innerHTML` for the node screen. Any key handler and choice submission both call `ttsStop()`.

### Settings

**CLI `settings.json`:**
```json
{
  "tts": {
    "enabled": false,
    "rate": 1.0,
    "volume": 1.0,
    "read_choices": false
  }
}
```

**Web localStorage (added to existing settings blob):**
```json
{
  "tts_enabled": false,
  "tts_rate": 1.0,
  "tts_volume": 1.0,
  "tts_read_choices": false
}
```

Rate range: `0.5` (slow) – `2.0` (fast). Default `1.0`. For language learners, a rate around `0.8` is recommended for comprehension — worth calling out in the settings screen.

Settings screen: new **Audio** section between Accessibility and Speed Presets.  
Web rows: TTS on/off toggle, rate slider (or stepped preset: slow / normal / fast), volume, read choices toggle.  
CLI: same fields, same settings screen pattern as existing typewriter rows.

### Key binding

- **Web terminal mode:** `U` key (for "Utter" / audio) toggles TTS on/off for the session. Permanent setting via settings screen.
- **Web accessible mode:** speaker button in `r-nav`.
- **CLI:** no new hotkey for MVP. Toggle via settings screen only (keeps `T` for typewriter, avoids key collision).

---

## Drama Pass (Pass 2)

Drama pass is additive — no MVP fields are modified.

### Story JSON additions

#### Node-level TTS hints

```json
{
  "confrontation": {
    "text": "Elena te mira fijamente. Sus manos tiemblan.",
    "tts": {
      "voice": "elena",
      "emotion": "tense",
      "rate": 0.88
    }
  }
}
```

| Field | Required | Notes |
|---|---|---|
| `voice` | No | Key into `meta.tts_voices`. If absent, uses default narrator voice. |
| `emotion` | No | Prosody preset (see table below). Applied on top of `voice` settings. |
| `rate` | No | Float `0.5–2.0`. Node-level rate override; stacks with voice rate. |

#### Meta-level voice directory

```json
{
  "meta": {
    "tts_voices": {
      "narrator": { "lang": "es-MX", "name": "Paulina", "pitch": 1.0, "rate": 1.0 },
      "elena":    { "lang": "es-MX", "name": "Monica",  "pitch": 1.1, "rate": 0.95 },
      "villain":  { "lang": "es-MX", "name": "Diego",   "pitch": 0.85, "rate": 1.05 }
    }
  }
}
```

`name` is advisory — the engine selects the closest available voice by name. If no voice matches, the language-appropriate default is used. Authors should document that named voices are platform-dependent.

### Emotion → prosody mapping

Resolved engine-side; authors do not set raw prosody values:

| Emotion | Rate multiplier | Pitch | Volume |
|---|---|---|---|
| `neutral` | 1.0 | 1.0 | 1.0 |
| `tense` | 0.85 | 0.95 | 0.9 |
| `urgent` | 1.15 | 1.05 | 1.0 |
| `whisper` | 0.9 | 1.0 | 0.5 |
| `sad` | 0.8 | 0.9 | 0.85 |
| `joyful` | 1.1 | 1.1 | 1.0 |

Multipliers are applied to the voice's base settings (not the global settings). Node-level `rate` overrides the result of this multiplication.

### Inline voice switching

For nodes where multiple characters speak, per-span voice control:

```
"text": "El guardia gruñe: {voice:villain}Nadie pasa.{/voice} Elena susurra: {voice:elena}Sígueme.{/voice}"
```

The engine splits the text on voice tags before passing to TTS. Each segment is spoken sequentially with the appropriate voice settings. In non-TTS mode, the tags are stripped silently (same as `{pause}` behavior).

This is a drama-pass-only feature. MVP TTS ignores `{voice:...}` tags (strips them).

### Cloud TTS backend (optional)

Platform TTS (Web Speech API, pyttsx3) does not support fine-grained prosody or high-quality Spanish voices on all systems. For drama-quality output, a cloud backend is available as a plugin:

- **CLI:** `src/tts_cloud.py` implementing the same `TTSEngine` interface
- **Web:** `web/tts_cloud.js` implementing the same `ttsSpeak` / `ttsStop` interface
- Provider configured in `settings.json`: `"tts_provider": "elevenlabs"` | `"azure"` | `"google"`
- API keys stored in `settings.json` (gitignored) — never in story JSON
- Story meta may declare a preferred provider: `"tts_provider": "elevenlabs"` — treated as a hint, not a requirement. Engine falls back to platform TTS if provider is unconfigured.
- Cloud audio may be cached locally (`/saves/<story_id>/<node_id>.<voice>.mp3`) to avoid re-fetching on revisit.

Cloud TTS is a story-author-level feature, not an engine-level one. Stories that don't declare a provider work identically with platform TTS.

### Validation additions (drama pass)

- `node.tts.voice` must reference a key in `meta.tts_voices` when present.
- `node.tts.emotion` must be in the known set (`neutral`, `tense`, `urgent`, `whisper`, `sad`, `joyful`).
- `node.tts.rate` must be a float between `0.5` and `2.0`.
- `meta.tts_voices[name].lang` must match the same pattern as `meta.lang` when both are present.
- `meta.tts_voices[name].pitch` must be a float between `0.5` and `2.0`.
- `meta.tts_voices[name].rate` must be a float between `0.5` and `2.0`.

---

## Open Questions

1. **TTS + typewriter: concurrent or bypass?** This spec recommends bypass (text appears instantly). Alternative: TTS plays concurrently with typewriter, both finishing at roughly the same time (requires TTS rate to be calibrated to match typewriter delay). Concurrent is more cinematic but significantly harder to implement and synchronize.
2. **Replay button** — Should players be able to replay the last utterance without re-navigating? Especially useful for language learning ("I didn't catch that"). A dedicated `R` key or repeat button after prose finishes.
3. **Slow-mode TTS for learning** — A distinct "comprehension rate" setting (e.g., `0.6`) separate from the general rate, triggered by a separate key or settings toggle. Lets learners hear slow pronunciation on demand without permanently changing playback speed.
4. **Voice selection UI** — Web Speech API exposes available voices by name, which is platform-specific and not portable across OS/browser. Should the settings screen show a voice picker? Requires enumerating `speechSynthesis.getVoices()` and filtering by `lang`. Worth doing for drama pass.
5. **CLI pyttsx3 background threading** — pyttsx3 uses an event loop that conflicts with Python's standard threading model on some platforms. May need a subprocess approach instead. Needs a prototype before finalizing the CLI architecture.
