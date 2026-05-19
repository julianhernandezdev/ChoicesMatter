# 10 — Named Styles

**Story:** `stories/examples/10_named_styles.json`
**Feature:** The full set of named style keys for insets and overlays, and how the engine resolves them to visual properties.

## What the story does

One node with six insets and two overlays demonstrating every style variant: `system`, `memory`, `warning`, `echo`, `whisper` (via unnamed default), and `""` (empty string).

## Engine code path

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

## Style reference (defaults)

| Style name | Prefix | Color | Modifiers |
|---|---|---|---|
| `""` (empty) | none | — | dim italic |
| `"system"` | none | dim | — |
| `"memory"` | `◈ ` | magenta | italic |
| `"warning"` | `⚠ ` | yellow | bold |
| `"echo"` | `~ ` | blue | italic |
| `"whisper"` (default overlay) | `✦ ` | cyan | italic |

## Key references

| Symbol | Location |
|---|---|
| `_MODIFIERS` | `src/display.py:43` |
| `Display._style_cfg()` | `src/display.py:264` |
| `Display._render_overlay()` | `src/display.py:272` |
| `Display._inset_renderable()` | `src/display.py:280` |
| Config loading | `src/config.py` |
