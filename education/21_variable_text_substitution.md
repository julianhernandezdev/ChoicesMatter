# 21 — Variable Text Substitution

**Story:** `stories/examples/21_variable_text_substitution.json`
**Feature:** `{key}` placeholders in any text field replaced at runtime with the current value of that flag.

## What the story does

The player picks a route (Northern, Southern, or Eastern) at the intro node. All three choices lead to the same `assigned` node. `{route}` is then substituted into the node's main text, an inset header, an overlay, and both ending texts — producing different prose from a single node based on the choice made.

## Syntax

```
"text": "You sign for the {route} assignment."
```

`{key}` patterns without `?` are variable substitution. Patterns with `?` (`{flag?true|false}`) are conditional inline text (example 19) — the two syntaxes coexist.

## Behaviour

| Condition | Result |
|---|---|
| Key present in state | Replaced with `str(value)` |
| Key present, value is `""` | Replaced with empty string — placeholder disappears |
| Key absent from state | Placeholder left intact — `{route}` stays in the rendered text |
| `true` / `false` (bool) | Replaced with `"True"` / `"False"` (Python) or `"true"` / `"false"` (JS) |

## Ordering relative to conditional inline

Variable substitution runs **before** conditional inline resolution. This means a substituted value can appear inside a conditional branch:

```json
"text": "{known?Hello, {player_name}!|Hello, stranger!}"
```

`{player_name}` is substituted first; the result (e.g. `"Hello, Felix!"`) is then the true branch of the conditional.

## Reserved names

`{pause}` is matched by the `_SUBST_RE` pattern and would be replaced if a `pause` flag existed in state. Do not use `pause` as a flag name — it collides with the typewriter pause token. `player_name` is reserved for the protagonist name feature (see example 22).

## Engine code path

**Module-level regex** (`src/engine.py:13`):

```python
_SUBST_RE = re.compile(r"\{(\w+)\}")
```

Matches any `{word}` not containing `?`. Because `_INLINE_RE` requires `?`, the two patterns are non-overlapping.

**`Engine._substitute_vars()`** (`src/engine.py`):

```python
@staticmethod
def _substitute_vars(text: str, state: dict) -> str:
    def _replace(m: re.Match) -> str:
        val = state.get(m.group(1))
        return str(val) if val is not None else m.group(0)
    return _SUBST_RE.sub(_replace, text)
```

Missing keys: `state.get(key)` returns `None`, and `m.group(0)` is the original `{key}` string — so the placeholder is returned unchanged. Present keys: `str(val)` is called unconditionally, converting booleans and integers to their string representations.

**`_pt` closure in `Engine.run()`** — chains substitution before inline resolution:

```python
def _pt(text: str) -> str:
    return self._resolve_inline(self._substitute_vars(text, self._state), self._state)

node_text    = _pt(node.text)
before_insets = [dataclasses.replace(i, text=_pt(i.text)) for i in before_insets]
after_insets  = [dataclasses.replace(i, text=_pt(i.text)) for i in after_insets]
before        = [dataclasses.replace(o, text=_pt(o.text)) for o in before]
after         = [dataclasses.replace(o, text=_pt(o.text)) for o in after]
```

`_substitute_vars` runs on the raw text first; `_resolve_inline` then runs on the substituted result. Original `Node`, `Inset`, and `Overlay` objects are never mutated.

**`{pause}` passthrough** — `_substitute_vars` runs before `Display._strip_pause_tokens()`. As long as `pause` is not in state, `_SUBST_RE` matches `{pause}` but returns `m.group(0)` unchanged (key absent → preserve). `{pause}` then reaches the display layer intact for stripping.

## Both engines

The JS web engine implements an equivalent `substituteVars` export in `web/engine.js`. The `currentView()` function chains it identically: substitution then inline resolution. Missing keys preserve the placeholder; present keys call `.toString()`.

## Key references

| Symbol | Location |
|---|---|
| `_SUBST_RE` | `src/engine.py:13` |
| `Engine._substitute_vars()` | `src/engine.py` |
| `_pt` closure in `Engine.run()` | `src/engine.py`, after visibility filtering |
| `substituteVars` (JS) | `web/engine.js` |
| Unit tests | `tests/test_engine.py`, section "Variable text substitution" |
| JS unit tests | `tests/test_web_engine.py`, section "substituteVars" |
