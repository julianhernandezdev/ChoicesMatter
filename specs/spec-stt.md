# Spec: Speech-to-Text Choice Selection

**Status:** Pre-roadmap / Design  
**Motivation:** Let players select choices by speaking — particularly valuable for Spanish learning (forces oral practice in the target language) and accessibility (hands-free navigation). Player must say the choice, not just a number, to get the full language-learning benefit.

---

## Overview

The player speaks; the engine matches their speech to a visible choice and navigates to it. This transforms choice selection from a reading exercise into a speaking exercise.

**Platform scope for MVP:** Web only. The Web Speech Recognition API is available in Chromium-based browsers (Chrome, Edge, Brave) and Safari 14.1+. CLI STT requires heavy native dependencies (`PyAudio` + a recognition model); deferred to a future spec.

---

## Recognition Strategy

Three possible matching approaches, ordered by simplicity:

### Mode A: Number words only
Player says "one", "uno", "two", "dos" → selects choice 1, 2.

- Simplest implementation, lowest error rate.
- Zero language learning value: saying "uno" is not the same as reading and speaking a full Spanish sentence.
- Good accessibility fallback; not a satisfying language learning mechanism.

### Mode B: Label matching only
Player speaks the text of a choice label (or a close approximation).

- High language learning value: player must read and produce the target-language phrase.
- Higher error rate: names, punctuation, and accents all affect recognition confidence.
- Requires fuzzy matching.

### Mode C: Hybrid (recommended)
Try number word matching first (fast path). If the transcript doesn't match any number word, attempt label matching.

- Preserves accessibility (players who just want to navigate quickly use numbers).
- Rewards language practice (players who speak the Spanish label correctly get matched).
- Label matching only fires when no number match is found — avoids false positives.

---

## Number Word Table

Applied in hybrid mode before label matching. Both English and Spanish accepted regardless of story language — players who are still learning shouldn't be penalized for falling back to English numbers.

```js
const NUMBER_WORDS = {
  // English ordinals and cardinals
  'one': 1, 'first': 1, '1': 1,
  'two': 2, 'second': 2, '2': 2,
  'three': 3, 'third': 3, '3': 3,
  'four': 4, 'fourth': 4, '4': 4,
  // Spanish
  'uno': 1, 'primero': 1, 'primera': 1,
  'dos': 2, 'segundo': 2, 'segunda': 2,
  'tres': 3, 'tercero': 3, 'tercera': 3,
  'cuatro': 4, 'cuarto': 4, 'cuarta': 4,
};
```

Matching: tokenize transcript, check if any token is in `NUMBER_WORDS`. Multiple number tokens → ambiguous → fall through to label matching.

---

## Label Matching Algorithm

1. **Normalize** both transcript and each choice label: lowercase, strip punctuation, remove accents (NFD normalize → strip combining marks), trim whitespace.
2. **Tokenize** into word arrays.
3. **Score** each choice: Jaccard similarity between transcript word set and label word set.
   - `score = |intersection| / |union|`
4. **Select** the choice with the highest score, if `score ≥ 0.3` (threshold TBD via testing).
5. If max score < 0.3: no match.

Example:
- Label: `"Encender la luz"` → words: `["encender", "la", "luz"]`
- Transcript: `"enciendo la luz"` → words: `["enciendo", "la", "luz"]`
- Intersection: `{"la", "luz"}` (2), Union: 4 → Jaccard 0.5 → matches (≥ 0.3)

Partial credit: "la luz" alone → intersection 2, union 4 → 0.5. This is intentional — learners who produce a partial but recognizable phrase get credit.

Confidence from the recognition API also factors in: if `SpeechRecognitionResult.confidence < 0.6`, the match is treated as low-confidence regardless of Jaccard score (see UX flow below).

---

## Recognition Language

The speech recognition API is pointed at the story's language:

```js
recognition.lang = meta.lang + (meta.region ? '-' + meta.region : '');
// e.g., 'es-MX' for a story with lang: 'es', region: 'MX'
```

This is the key language-learning mechanic: the engine is listening for Spanish. The player must produce intelligible Spanish for the label match to fire. English number words still work because they are short, unambiguous phonemes that get through cross-language recognition reliably.

If `meta.lang` is absent, recognition language falls back to `navigator.language`.

---

## Interaction Model (Web)

### Activation: Hold-to-speak (default)

1. Player sees choices on screen.
2. A mic button (or `V` key hold) activates recognition.
3. While active: pulsing mic indicator with "Escuchando..." / "Listening..." overlay replaces the input hint.
4. On release (key or button): recognition finalizes.
5. Outcome (see below).

`V` key is used rather than `Space` to avoid conflict with page scroll. On mobile, the mic button is the primary activation method.

### Activation: Toggle mode (accessible mode default)

Single tap activates. Tap again (or silence detection after 3s) stops. Recommended for mobile and for accessible mode where hold-to-speak is awkward with screen readers.

### Outcomes

| Condition | Response |
|---|---|
| Number word matched | Navigate immediately. No confirmation needed. |
| Label matched, confidence ≥ 0.6 | Highlight matched choice, show transcript. Auto-navigate after 1.5s delay (player can press any key to cancel and try again). |
| Label matched, confidence < 0.6 | Highlight matched choice, show transcript, show "¿Quisiste decir [label]?" prompt. Player confirms with `Enter` / taps choice. |
| No match | Show transcript, show "No entendí — intenta de nuevo" hint. Player tries again or uses keyboard. |
| Empty / silence | Dismiss listener. No state change. |
| API error / permission denied | Show one-time error message. Fall back silently to keyboard-only. |

### Transcript display

Transcript is shown in small muted text below the choice list immediately after recognition finalizes:

```
Escuché: "encender la luz"
```

This has secondary language learning value: the player sees what the system heard, which reveals their pronunciation accuracy.

---

## UX Components

### Mic button

Positioned alongside the choice input hint in terminal mode, as a `<button>` element:

```html
<button id="mic-btn" class="mic-button" aria-label="Speak your choice">🎤</button>
```

Hidden entirely (not just disabled) when `voice_input` is false or when the API is unavailable. Avoids prompting for microphone permission passively.

### Accessible mode (`r-nav` integration)

In accessible mode, the mic button appears in the `r-nav` bar alongside existing nav buttons. Toggle mode is default. After recognition resolves, focus moves to the matched choice `<button>` (if confident) or stays on the `r-nav` mic button (if low-confidence, for retry).

### Listening indicator

A minimal overlay inside the story panel (does not replace the choice list):

```html
<div class="stt-status">
  <span class="mic-pulse">●</span> Escuchando...
</div>
```

Pulse animation is CSS-only and respects `prefers-reduced-motion` (static dot if reduced motion is set).

---

## Privacy

- Microphone is only activated on an explicit user gesture (hold key or tap button).
- No audio is stored. Recognition is processed entirely by the browser's native API — audio never leaves the device (Web Speech API in Chrome uses Google's servers for recognition; this is browser behavior, not engine behavior, and should be disclosed in settings).
- `voice_input` defaults to `false`. The browser mic permission prompt is never shown until the player explicitly enables voice input in settings and activates the mic button.
- The engine does not log, store, or transmit transcripts.

---

## Settings (web localStorage)

Added to existing settings blob:

```json
{
  "voice_input": false,
  "voice_input_mode": "hold",
  "voice_input_number_only": false
}
```

| Key | Values | Notes |
|---|---|---|
| `voice_input` | `false` / `true` | Master toggle. Default `false`. |
| `voice_input_mode` | `"hold"` / `"toggle"` | Hold-to-speak or tap-to-toggle. Default `"hold"`. |
| `voice_input_number_only` | `false` / `true` | Skip label matching; only number words accepted. For users who want hands-free navigation without the language learning mechanic. |

Settings screen: new **Voice Input** section in the Audio group (alongside TTS if TTS is implemented).

Rows:
- Voice input: Off / Hold / Toggle (three-state cycle)
- Mode: Numbers only / Label matching (visible only when voice input is on)

---

## Story JSON additions (optional)

Stories may opt into strict speech-only mode for specific choices:

```json
{
  "label": "Encender la luz",
  "label_translation": "Turn on the light",
  "speech_required": true,
  "next": "lights_on"
}
```

`speech_required: true` hides this choice from the keyboard number list and requires speech to select it. Useful for high-stakes learning moments ("you must say this aloud"). Not in scope for MVP — document as a future drama-pass enhancement.

---

## Validation additions (for `speech_required` when implemented)

- `choice.speech_required` must be boolean when present.
- `speech_required: true` is a validation warning (not error) if `meta.lang` is not set — the mechanic has no meaning without a target language.

---

## Open Questions

1. **CLI STT** — `whisper.cpp` (via `llama.cpp` or directly) runs locally with no API key and decent Spanish recognition. Packaging is non-trivial (~150 MB model), but feasible as an optional dependency. Worth a prototype before dismissing.
2. **"Repeat after me" mode** — TTS reads a choice label aloud; player repeats it; STT confirms they said it. A pronunciation drill mechanic. High language learning value, low navigation utility. Could be a distinct mode (`drill_mode: true` in story meta) rather than part of standard choice selection.
3. **Jaccard threshold (0.3)** — needs empirical testing with real Spanish learners. Accented vowels, articles (el/la/los/las), and gender agreement variations may require a lower threshold or a more forgiving normalization step.
4. **Chrome / Web Speech API cloud dependency** — Chrome sends audio to Google servers for recognition. Some users may prefer a local option. `whisper.js` (WebAssembly port of OpenAI Whisper) runs entirely in-browser at reasonable latency. Consider for a privacy-hardened pass.
5. **Transcript logging for vocabulary review** — Recording what the player said (normalized transcript only, no audio) across a session could power a "your pronunciation attempts" review screen. Would require player consent and a clear data-handling statement.
6. **Confidence threshold (0.6)** — same as item 3. Lower confidence values may be appropriate for learners who are producing accented or partial Spanish — the fuzzy matching already handles partial; the confidence gate may be too strict.
