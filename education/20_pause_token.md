# 20 — Pause Token

**Story:** `stories/examples/20_pause_token.json`
**Feature:** `{pause}` embedded in node or ending `text` injects a configurable delay mid-stream during typewriter playback. Stripped silently in non-typewriter mode.

## What the story does

A radio story with three endings. The `signal` node demonstrates `{pause}` mid-sentence — the typewriter halts for 500 ms between the static description and the voice cutting through. Two endings (`ending_respond`, `ending_leave`) each carry a `{pause}` of their own, showing the token works in ending text too.

## Syntax

```
"text": "You adjust the frequency.{pause}A voice cuts through."
```

`{pause}` can appear anywhere in a `text` field — mid-sentence, after punctuation, multiple times. It has no effect in insets or overlays.

## Behaviour

| Mode | Effect |
|---|---|
| Typewriter on | Halts character streaming for `typewriter.pause_ms` milliseconds (default 500) |
| Typewriter off | Token stripped silently — rendered text contains no `{pause}` |
| Player presses a key during pause | Skips immediately to full clean text (token stripped) |

## Configuration

```json
{
  "typewriter": {
    "pause_ms": 500
  }
}
```

`pause_ms` lives under `typewriter` in `settings.json`. It is not exposed in the in-game settings screen — authors or players edit `settings.json` directly.

## Engine code path

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

## Key references

| Symbol | Location |
|---|---|
| `_strip_pause_tokens()` | `src/display.py` |
| `_typewrite()` | `src/display.py` |
| `"pause_ms"` default | `src/config.py`, `_DEFAULTS["typewriter"]` |
| Unit tests | `tests/test_display.py`, section `_strip_pause_tokens` and `_typewrite: {pause} token` |
