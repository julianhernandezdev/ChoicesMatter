# Conformance Suite

Language-neutral test vectors that define what a Choices Matter engine must do.
Each case says: given this input, the engine must produce this output. The
Python CLI engine and the web engine both run every case, and a port (for
example GDScript) is correct when it passes the same files.

When an engine and a vector disagree, the vector wins. To change engine
behaviour, change the vector first.

## Running

```bash
pytest tests/test_conformance.py
```

This runs each case twice: against `src/engine.py`, and against
`web/engine.js` through Node (`tests/conformance_runner.mjs`).

## File format

```json
{
  "suite": "requires",
  "format": 1,
  "description": "what function this suite pins",
  "cases": [
    { "id": "bool-int-one-vs-true",
      "state": {"k": 1}, "requires": {"k": true},
      "expect": false,
      "why": "Strict typing: the integer 1 is not the boolean true." }
  ]
}
```

- `id` is unique within the file and stable; refer to it in bug reports.
- `why` is required. It is the one-line rule the case demonstrates.
- `format` is the vector file format version, not the story format version.
- Results are compared as canonical JSON, so types are strict: `1` and `true`
  are different, and so are `2` and `"2"`.

## Suites

| File | Function | Input | `expect` |
|---|---|---|---|
| `requires.json` | Is a choice, inset or overlay visible? | `state`, `requires` | boolean |
| `sets.json` | Apply a choice's `sets` | `state`, `sets` | the full resulting state |

## The rules these suites pin

**Integer value of a flag.** A flag's integer value is the flag itself if it
holds an integer, otherwise 0. Missing flags, booleans and strings all count
as 0. Thresholds and deltas both use this one rule.

**`requires`** (all conditions must hold):

| Condition | Holds when |
|---|---|
| `true` / `false` | State holds exactly that boolean. A missing flag satisfies neither |
| integer N | The flag's integer value is >= N |
| string | State holds exactly that string (case-sensitive) |
| list of strings | State holds a string that is in the list |

**`sets`** (each key independent):

| Value | Effect |
|---|---|
| string matching `[+-][0-9]+` | Delta: integer value of the flag plus the signed number |
| anything else (boolean, integer, other string) | Assigned as-is, replacing value and type |

## Notes for porters

- Booleans are not integers. In languages where `true == 1` (Python) or where
  JSON numbers all parse as floats (Godot's `JSON`), check types explicitly.
- Integers in vectors stay within +/- 2^53 so every host can represent them.
- A `sets` string that starts with `+` or `-` but is not a valid delta is
  rejected when the story loads, so it never reaches `apply_sets`.

## Adding a suite

1. Add `conformance/<name>.json` in the format above.
2. Add `<name>` to `PY_SUITES` in `tests/test_conformance.py` and to `SUITES`
   in `tests/conformance_runner.mjs`. A test fails if a file has no runner.

Planned: `text` (variable substitution and conditional inline text),
`corruption` (span parsing and seeds), `validation` (accept or reject a story
fragment), and `runs` (a whole story plus a choice sequence).
