# 19 — Conditional Inline Text

**Story:** `stories/examples/19_conditional_inline_text.json`
**Feature:** Flag-conditional spans embedded directly in text fields — node text, insets, and overlays — resolved at runtime without branching to a separate node.

## What the story does

Two choices on the intro node lead to the same `lobby` node: one sets `is_staff: true`, the other does not. The lobby node uses `{is_staff?...|...}` spans in its main text, an inset, and an overlay — producing different prose for staff vs visitors, all within a single node.

## Syntax

```
{flag?shown when true|shown when false}
```

The `|false branch` is optional. When omitted and the condition is false, the span collapses to an empty string — the inset in this story uses that form:

```json
{ "text": "{is_staff?STAFF ACCESS GRANTED}", "style": "system", "position": "before" }
```

If `is_staff` is false or missing, nothing renders in its place.

## Truthiness

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

## Engine code path

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

## Coexistence with Variable Text Substitution

Variable Text Substitution (future feature) uses `{key}` — no `?`. The conditional regex will not match those patterns. When both features are active, variable substitution runs first; conditional inline runs second.

## Key references

| Symbol | Location |
|---|---|
| `_INLINE_RE` | `src/engine.py` |
| `Engine._resolve_inline()` | `src/engine.py` |
| Resolve block in `Engine.run()` | `src/engine.py`, after visibility filtering |
| Unit tests | `tests/test_engine.py`, section "Conditional inline text: _resolve_inline unit tests" |
| Integration tests | `tests/test_engine.py`, section "Conditional inline text: integration tests" |
