# Default Settings & Section Registry — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a `SETTINGS_SECTIONS` registry on both platforms that drives settings rendering, sub-screen navigation, and a "Reset to Defaults" feature with a checkbox selector.

**Architecture:** A `SETTINGS_SECTIONS` constant (Python: `src/config.py`; Web: `web/app.js`) defines every settings section — its rows, defaults, and flags. The settings screen derives its display from the registry; sub-screens are rendered generically from section row descriptors; reset logic iterates selected sections and applies their defaults to the draft. The Python CLI and Web implementations are independent after their respective registry tasks and can be worked in parallel.

**Tech Stack:** Python 3.x + rich (CLI), vanilla ES-module JS (Web), pytest (Python tests), Node.js subprocess (Web tests).

## Global Constraints

- Python: all new public symbols in `src/config.py` are lowercase with underscores. New Display methods are underscore-prefixed (private convention).
- Web: all new JS in `web/app.js`; no new files. Use `var` (not `let`/`const`) consistent with the existing codebase.
- Sub-screen nav keys exactly: `S` save+back-to-settings, `X` discard-section+back-to-settings, `M` save+main-menu, `Q` discard-all+main-menu, `R` reset-section.
- Main settings screen: `R` opens checkbox reset selector. `S` save+main-menu, `X` discard+main-menu (unchanged from current).
- Preservation note "Player name and accessible mode will always be preserved." shown upfront in checkbox selector, not in post-reset feedback.
- Post-reset feedback: "Reset: Typewriter, Display." — section names only, no preservation note.
- `player_name` and `accessible_mode` are never in the reset checkbox list (`preserveOnGlobalReset: true`).
- Resettable sections (checkbox list): Typewriter, Corruption, Display.
- All reset operations modify the draft only — user must press S or M to persist.
- Python CLI: `_settings_corruption` is deleted and replaced by the generic `_section_subscreen`. The old helpers `_settings_edit_pause`, `_settings_edit_page_size`, `_settings_edit_player_name` are also deleted (replaced by generic `_edit_row`). `_settings_edit_speed` is kept.
- Web: `SETTINGS_ROWS` becomes a derived constant (computed from `SETTINGS_SECTIONS`). The hardcoded array is deleted.
- Run tests with: `python -m pytest tests/ -x -q` (Python), `node --input-type=module` via subprocess (Web).

---

## File Map

| File | Change |
|---|---|
| `src/config.py` | Add `SETTINGS_SECTIONS`, `_get_draft_value`, `_set_draft_value`, `apply_section_defaults` |
| `src/display.py` | Rewrite `show_settings_screen`; add `_format_row_value`, `_edit_row`, `_section_subscreen`, `_show_reset_selector`; delete `_settings_corruption`, `_settings_edit_pause`, `_settings_edit_page_size`, `_settings_edit_player_name` |
| `web/app.js` | Replace hardcoded `SETTINGS_ROWS` with `SETTINGS_SECTIONS` + derived rows; add `renderSectionSubscreen`, `renderAccessibleSectionSubscreen`, `renderResetSelector`, `applyDefaults`; extend `handleSubmit`, `startSettingsEdit`, `promptPrefix` |
| `tests/test_config.py` | Add tests for new helpers and registry |
| `tests/test_display.py` | Add tests for new display helpers |
| `tests/test_web_settings.py` | New file — Node.js subprocess tests for web settings registry and applyDefaults |

---

### Task 1: Python — SETTINGS_SECTIONS registry + helpers in `config.py`

**Files:**
- Modify: `src/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `SETTINGS_SECTIONS: list[dict]`, `_get_draft_value(draft, key)`, `_set_draft_value(draft, key, value)`, `apply_section_defaults(draft, section)`

---

- [ ] **Step 1: Write failing tests for `_get_draft_value` and `_set_draft_value`**

Add to `tests/test_config.py`:

```python
from src.config import _get_draft_value, _set_draft_value, apply_section_defaults, SETTINGS_SECTIONS

def test_get_draft_value_top_level():
    draft = {"player_name": "Alice"}
    assert _get_draft_value(draft, "player_name") == "Alice"

def test_get_draft_value_nested():
    draft = {"typewriter": {"enabled": True, "delay_ms": 35}}
    assert _get_draft_value(draft, "typewriter.enabled") is True
    assert _get_draft_value(draft, "typewriter.delay_ms") == 35

def test_get_draft_value_punctuation_pause():
    draft = {"typewriter": {"punctuation_pauses": {".": 550, "!": 250}}}
    assert _get_draft_value(draft, "typewriter.punctuation_pauses..") == 550
    assert _get_draft_value(draft, "typewriter.punctuation_pauses.!") == 250

def test_get_draft_value_corruption():
    draft = {"corruption": {"enabled": True, "intensity": 0.8}}
    assert _get_draft_value(draft, "corruption.enabled") is True
    assert _get_draft_value(draft, "corruption.intensity") == 0.8

def test_get_draft_value_picker():
    draft = {"picker": {"page_size": 10}}
    assert _get_draft_value(draft, "picker.page_size") == 10

def test_set_draft_value_top_level():
    draft = {"player_name": "Felix"}
    _set_draft_value(draft, "player_name", "Alice")
    assert draft["player_name"] == "Alice"

def test_set_draft_value_nested():
    draft = {"typewriter": {"enabled": False}}
    _set_draft_value(draft, "typewriter.enabled", True)
    assert draft["typewriter"]["enabled"] is True

def test_set_draft_value_punctuation_pause():
    draft = {"typewriter": {"punctuation_pauses": {".": 550}}}
    _set_draft_value(draft, "typewriter.punctuation_pauses..", 300)
    assert draft["typewriter"]["punctuation_pauses"]["."] == 300

def test_set_draft_value_corruption():
    draft = {"corruption": {"intensity": 1.0}}
    _set_draft_value(draft, "corruption.intensity", 0.5)
    assert draft["corruption"]["intensity"] == 0.5
```

- [ ] **Step 2: Run tests — verify they fail**

```
python -m pytest tests/test_config.py -k "get_draft_value or set_draft_value" -v
```
Expected: `ImportError` or `NameError` — functions not yet defined.

- [ ] **Step 3: Write failing tests for `apply_section_defaults` and `SETTINGS_SECTIONS`**

Add to `tests/test_config.py`:

```python
def test_apply_section_defaults_typewriter():
    draft = {"typewriter": {"enabled": False, "delay_ms": 999}}
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "typewriter")
    apply_section_defaults(draft, section)
    assert draft["typewriter"]["enabled"] is True
    assert draft["typewriter"]["delay_ms"] == 35

def test_apply_section_defaults_corruption():
    draft = {"corruption": {"intensity": 0.1, "animate": False}}
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    apply_section_defaults(draft, section)
    assert draft["corruption"]["intensity"] == 1.0
    assert draft["corruption"]["animate"] is True

def test_apply_section_defaults_display():
    draft = {"picker": {"page_size": 20}}
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "display")
    apply_section_defaults(draft, section)
    assert draft["picker"]["page_size"] == 5

def test_apply_section_defaults_preserves_other_keys():
    draft = {"typewriter": {"enabled": False}, "player_name": "Zara"}
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "typewriter")
    apply_section_defaults(draft, section)
    assert draft["player_name"] == "Zara"  # untouched

def test_settings_sections_ids():
    ids = [s["id"] for s in SETTINGS_SECTIONS]
    assert "typewriter" in ids
    assert "display" in ids
    assert "corruption" in ids
    assert "player" in ids

def test_settings_sections_preserve_flags():
    by_id = {s["id"]: s for s in SETTINGS_SECTIONS}
    assert by_id["typewriter"]["preserve_on_global_reset"] is False
    assert by_id["corruption"]["preserve_on_global_reset"] is False
    assert by_id["display"]["preserve_on_global_reset"] is False
    assert by_id["player"]["preserve_on_global_reset"] is True

def test_settings_sections_subscreen_flags():
    by_id = {s["id"]: s for s in SETTINGS_SECTIONS}
    assert by_id["typewriter"]["has_subscreen"] is True
    assert by_id["corruption"]["has_subscreen"] is True
    assert by_id["display"]["has_subscreen"] is False
    assert by_id["player"]["has_subscreen"] is False

def test_settings_sections_all_have_rows():
    for section in SETTINGS_SECTIONS:
        assert len(section["rows"]) > 0, f"Section '{section['id']}' has no rows"

def test_settings_sections_rows_have_required_fields():
    for section in SETTINGS_SECTIONS:
        for row in section["rows"]:
            assert "key" in row
            assert "label" in row
            assert "type" in row
```

- [ ] **Step 4: Run tests — verify they fail**

```
python -m pytest tests/test_config.py -k "apply_section_defaults or settings_sections" -v
```
Expected: `ImportError` — symbols not yet defined.

- [ ] **Step 5: Implement helpers and `SETTINGS_SECTIONS` in `src/config.py`**

Add after the `_DEFAULTS` block (before `save_settings`):

```python
def _get_draft_value(draft: dict, key: str):
    if key.startswith("typewriter.punctuation_pauses."):
        char = key[len("typewriter.punctuation_pauses."):]
        return draft.get("typewriter", {}).get("punctuation_pauses", {}).get(char)
    if key.startswith("typewriter."):
        return draft.get("typewriter", {}).get(key[len("typewriter."):])
    if key.startswith("picker."):
        return draft.get("picker", {}).get(key[len("picker."):])
    if key.startswith("corruption."):
        return draft.get("corruption", {}).get(key[len("corruption."):])
    return draft.get(key)


def _set_draft_value(draft: dict, key: str, value) -> None:
    if key.startswith("typewriter.punctuation_pauses."):
        char = key[len("typewriter.punctuation_pauses."):]
        draft.setdefault("typewriter", {}).setdefault("punctuation_pauses", {})[char] = value
    elif key.startswith("typewriter."):
        draft.setdefault("typewriter", {})[key[len("typewriter."):]] = value
    elif key.startswith("picker."):
        draft.setdefault("picker", {})[key[len("picker."):]] = value
    elif key.startswith("corruption."):
        draft.setdefault("corruption", {})[key[len("corruption."):]] = value
    else:
        draft[key] = value


def apply_section_defaults(draft: dict, section: dict) -> None:
    for key in section["config_keys"]:
        draft[key] = _deep_copy(_DEFAULTS[key])


SETTINGS_SECTIONS: list[dict] = [
    {
        "id": "typewriter",
        "label": "Typewriter",
        "preserve_on_global_reset": False,
        "has_subscreen": True,
        "config_keys": ["typewriter"],
        "rows": [
            {"key": "typewriter.enabled",                     "label": "Enabled",           "type": "boolean"},
            {"key": "typewriter.delay_ms",                    "label": "Speed",             "type": "speed_presets", "unit": "ms"},
            {"key": "typewriter.punctuation_pauses..",        "label": "Pause after  .",    "type": "number",  "unit": "ms", "range": (0, 2000)},
            {"key": "typewriter.punctuation_pauses.!",        "label": "Pause after  !",    "type": "number",  "unit": "ms", "range": (0, 2000)},
            {"key": "typewriter.punctuation_pauses.?",        "label": "Pause after  ?",    "type": "number",  "unit": "ms", "range": (0, 2000)},
            {"key": "typewriter.punctuation_pauses.…",   "label": "Pause after  …", "type": "number", "unit": "ms", "range": (0, 2000)},
            {"key": "typewriter.punctuation_pauses.—",   "label": "Pause after  —", "type": "number", "unit": "ms", "range": (0, 2000)},
        ],
    },
    {
        "id": "display",
        "label": "Display",
        "preserve_on_global_reset": False,
        "has_subscreen": False,
        "config_keys": ["picker"],
        "rows": [
            {"key": "picker.page_size", "label": "Stories per page", "type": "number", "unit": "", "range": (1, 50)},
        ],
    },
    {
        "id": "corruption",
        "label": "Corruption",
        "preserve_on_global_reset": False,
        "has_subscreen": True,
        "config_keys": ["corruption"],
        "rows": [
            {"key": "corruption.enabled",           "label": "Enabled",         "type": "boolean"},
            {"key": "corruption.intensity",         "label": "Intensity",       "type": "float",  "unit": "×", "range": (0.0, 1.0)},
            {"key": "corruption.mode",              "label": "Mode",            "type": "cycle",  "values": ["consistent", "random"]},
            {"key": "corruption.charset",           "label": "Character set",   "type": "cycle",  "values": ["blocks", "symbols", "diacritics", "custom"]},
            {"key": "corruption.custom_chars",      "label": "Custom chars",    "type": "custom_chars"},
            {"key": "corruption.animate",           "label": "Animate",         "type": "boolean"},
            {"key": "corruption.scramble_frames",   "label": "Scramble frames", "type": "number", "unit": "",   "range": (1, 50)},
            {"key": "corruption.scramble_delay_ms", "label": "Scramble delay",  "type": "number", "unit": "ms", "range": (0, 1000)},
        ],
    },
    {
        "id": "player",
        "label": "Player",
        "preserve_on_global_reset": True,
        "has_subscreen": False,
        "config_keys": ["player_name"],
        "rows": [
            {"key": "player_name", "label": "Player name", "type": "text"},
        ],
    },
]
```

- [ ] **Step 6: Run all new tests — verify they pass**

```
python -m pytest tests/test_config.py -k "get_draft or set_draft or apply_section or settings_sections" -v
```
Expected: all pass.

- [ ] **Step 7: Run full test suite — verify no regressions**

```
python -m pytest tests/ -x -q
```
Expected: all existing tests still pass.

- [ ] **Step 8: Commit**

```
git add src/config.py tests/test_config.py
git commit -m "feat(config): add SETTINGS_SECTIONS registry and draft value helpers"
```

---

### Task 2: Python — Refactor `show_settings_screen`

**Files:**
- Modify: `src/display.py`
- Test: `tests/test_display.py`

**Interfaces:**
- Consumes: `SETTINGS_SECTIONS`, `_get_draft_value`, `_set_draft_value` from `src/config.py`
- Produces: `_format_row_value(row, val) -> str`, `_edit_row(draft, row)` (both private methods on `Display`)

---

- [ ] **Step 1: Write failing tests for `_format_row_value`**

Add to `tests/test_display.py`:

```python
from src.config import SETTINGS_SECTIONS

def test_format_row_value_boolean_true(display):
    row = {"type": "boolean"}
    result = display._format_row_value(row, True)
    assert "on" in result

def test_format_row_value_boolean_false(display):
    row = {"type": "boolean"}
    result = display._format_row_value(row, False)
    assert "off" in result

def test_format_row_value_number_with_unit(display):
    row = {"type": "number", "unit": "ms"}
    result = display._format_row_value(row, 35)
    assert "35" in result
    assert "ms" in result

def test_format_row_value_number_no_unit(display):
    row = {"type": "number", "unit": ""}
    result = display._format_row_value(row, 5)
    assert "5" in result

def test_format_row_value_cycle(display):
    row = {"type": "cycle", "values": ["consistent", "random"]}
    result = display._format_row_value(row, "consistent")
    assert "consistent" in result

def test_format_row_value_text(display):
    row = {"type": "text"}
    result = display._format_row_value(row, "Felix")
    assert "Felix" in result
```

- [ ] **Step 2: Run tests — verify they fail**

```
python -m pytest tests/test_display.py -k "format_row_value" -v
```
Expected: `AttributeError` — method not yet defined.

- [ ] **Step 3: Add `_format_row_value` and `_edit_row` to `Display` in `src/display.py`**

Add these two methods inside the `Display` class (place near the existing `_settings_edit_speed`):

```python
def _format_row_value(self, row: dict, val) -> str:
    t = row.get("type", "")
    if t == "boolean":
        return "[green]on[/green]" if val else "[dim]off[/dim]"
    if t in ("number", "speed_presets"):
        unit = row.get("unit", "")
        suffix = f" {unit}" if unit else ""
        return f"[bold]{val}{suffix}[/bold]"
    if t == "float":
        unit = row.get("unit", "")
        suffix = f" {unit}" if unit else ""
        return f"[bold]{val:.1f}{suffix}[/bold]"
    if t in ("cycle", "text", "custom_chars"):
        return f"[bold]{val}[/bold]"
    return str(val) if val is not None else ""

def _edit_row(self, draft: dict, row: dict) -> None:
    from .config import _get_draft_value, _set_draft_value
    key = row["key"]
    val = _get_draft_value(draft, key)
    t = row.get("type", "")

    if t == "boolean":
        _set_draft_value(draft, key, not val)

    elif t == "speed_presets":
        self._settings_edit_speed(draft.setdefault("typewriter", {}))

    elif t == "number":
        lo, hi = row.get("range", (0, 9999))
        unit = row.get("unit", "value")
        while True:
            v = self.console.input(f"  Enter {unit or 'value'} ({lo}–{hi}, or Enter to keep): ").strip()
            if v == "":
                break
            if v.isdigit() and lo <= int(v) <= hi:
                _set_draft_value(draft, key, int(v))
                break
            self.console.print(f"  [red]Enter a number between {lo} and {hi}.[/red]")

    elif t == "float":
        lo, hi = row.get("range", (0.0, 1.0))
        while True:
            v = self.console.input(f"  Enter value ({lo}–{hi}, or Enter to keep): ").strip()
            if v == "":
                break
            try:
                fv = float(v)
                if lo <= fv <= hi:
                    _set_draft_value(draft, key, fv)
                    break
            except ValueError:
                pass
            self.console.print(f"  [red]Enter a number between {lo} and {hi}.[/red]")

    elif t == "text":
        v = self.console.input("  Enter value (or Enter to keep): ").strip()
        if v:
            _set_draft_value(draft, key, v)

    elif t == "cycle":
        values = row.get("values", [])
        idx = values.index(val) if val in values else 0
        _set_draft_value(draft, key, values[(idx + 1) % len(values)])
```

- [ ] **Step 4: Run format_row_value tests — verify they pass**

```
python -m pytest tests/test_display.py -k "format_row_value" -v
```
Expected: all pass.

- [ ] **Step 5: Rewrite `show_settings_screen` to iterate `SETTINGS_SECTIONS`**

Replace the entire `show_settings_screen` method in `src/display.py`. The new version builds a `row_map` from section registry:

```python
def show_settings_screen(self) -> None:
    from .config import SETTINGS_SECTIONS, _get_draft_value, save_settings
    import copy
    draft = copy.deepcopy(self._cfg)
    reset_feedback = ""

    while True:
        self.clear_screen()
        self.console.print()
        self.console.print(Rule("[bold cyan]Settings[/bold cyan]"))
        self.console.print()

        row_num = 0
        row_map: dict[int, tuple[dict, dict | None]] = {}

        for section in SETTINGS_SECTIONS:
            if section["has_subscreen"]:
                row_num += 1
                row_map[row_num] = (section, None)
                self.console.print(f"  [cyan]{row_num}.[/cyan]  {section['label']:<18} →")
            else:
                for row in section["rows"]:
                    row_num += 1
                    row_map[row_num] = (section, row)
                    val = _get_draft_value(draft, row["key"])
                    display = self._format_row_value(row, val)
                    self.console.print(f"  [cyan]{row_num}.[/cyan]  {row['label']:<18} {display}")

        self.console.print()
        self.console.print("  [dim]Enter a number to edit · [green]S[/green] save · [red]X[/red] discard · [yellow]R[/yellow] reset[/dim]")
        if reset_feedback:
            self.console.print(f"  [dim green]✓ {reset_feedback}[/dim green]")
            reset_feedback = ""

        raw = self.console.input("  › ").strip().lower()

        if raw == "s":
            save_settings(draft)
            self.console.print("\n  [dim green]✓ Saved. Changes take effect next launch.[/dim green]")
            self.console.input("\n  [dim]Press Enter to return.[/dim] ")
            return
        if raw == "x":
            return
        if raw == "r":
            reset_feedback = self._show_reset_selector(draft)
            continue
        if raw.isdigit():
            n = int(raw)
            if n in row_map:
                section, row = row_map[n]
                if row is None:
                    result = self._section_subscreen(section, draft)
                    if result == "save_exit":
                        save_settings(draft)
                        return
                    if result == "discard_exit":
                        return
                else:
                    self._edit_row(draft, row)
```

- [ ] **Step 6: Remove the four now-replaced methods**

Delete these methods from `src/display.py`:
- `_settings_edit_pause`
- `_settings_edit_page_size`
- `_settings_edit_player_name`
- `_settings_corruption`

(Keep `_settings_edit_speed` — it is still called via `_edit_row` for `speed_presets` type.)

- [ ] **Step 7: Run full test suite — verify no regressions**

```
python -m pytest tests/ -x -q
```
Expected: all pass.

- [ ] **Step 8: Commit**

```
git add src/display.py tests/test_display.py
git commit -m "feat(display): refactor show_settings_screen from registry; add _edit_row, _format_row_value"
```

---

### Task 3: Python — Generic `_section_subscreen`

**Files:**
- Modify: `src/display.py`
- Test: `tests/test_display.py`

**Interfaces:**
- Consumes: `SETTINGS_SECTIONS`, `_get_draft_value`, `_set_draft_value`, `apply_section_defaults` from `src/config.py`
- Produces: `_section_subscreen(section: dict, draft: dict) -> str` — returns `"back"`, `"save_exit"`, or `"discard_exit"`

---

- [ ] **Step 1: Write failing tests for `_section_subscreen`**

Add to `tests/test_display.py`:

```python
import copy
from src.config import SETTINGS_SECTIONS, _get_draft_value

def _make_draft():
    from src.config import load_settings
    return load_settings()

def test_section_subscreen_x_returns_back(display):
    display.console.input = MagicMock(side_effect=["x"])
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    draft = _make_draft()
    result = display._section_subscreen(section, draft)
    assert result == "back"

def test_section_subscreen_m_returns_save_exit(display):
    display.console.input = MagicMock(side_effect=["m"])
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    draft = _make_draft()
    result = display._section_subscreen(section, draft)
    assert result == "save_exit"

def test_section_subscreen_q_returns_discard_exit(display):
    display.console.input = MagicMock(side_effect=["q"])
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    draft = _make_draft()
    result = display._section_subscreen(section, draft)
    assert result == "discard_exit"

def test_section_subscreen_r_resets_section(display):
    display.console.input = MagicMock(side_effect=["r", "y", "x"])
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    draft = _make_draft()
    draft["corruption"]["intensity"] = 0.1
    display._section_subscreen(section, draft)
    assert draft["corruption"]["intensity"] == 1.0

def test_section_subscreen_r_cancel_no_change(display):
    display.console.input = MagicMock(side_effect=["r", "n", "x"])
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    draft = _make_draft()
    draft["corruption"]["intensity"] = 0.1
    display._section_subscreen(section, draft)
    assert draft["corruption"]["intensity"] == 0.1
```

- [ ] **Step 2: Run tests — verify they fail**

```
python -m pytest tests/test_display.py -k "section_subscreen" -v
```
Expected: `AttributeError` — method not yet defined.

- [ ] **Step 3: Implement `_section_subscreen` in `src/display.py`**

Add the method inside the `Display` class:

```python
def _section_subscreen(self, section: dict, draft: dict) -> str:
    """
    Generic section sub-screen.
    Returns: "back" | "save_exit" | "discard_exit"
    """
    from .config import _get_draft_value, _set_draft_value, apply_section_defaults, save_settings
    import copy

    while True:
        self.clear_screen()
        self.console.print()
        self.console.print(Rule(f"[bold cyan]Settings — {section['label']}[/bold cyan]"))
        self.console.print()

        charset = _get_draft_value(draft, "corruption.charset") if section["id"] == "corruption" else None

        for i, row in enumerate(section["rows"], start=1):
            val = _get_draft_value(draft, row["key"])
            display_val = self._format_row_value(row, val)
            if row["type"] == "custom_chars" and charset != "custom":
                self.console.print(f"  [dim][cyan]{i}.[/cyan]  {row['label']:<18} {display_val}[/dim]")
            else:
                self.console.print(f"  [cyan]{i}.[/cyan]  {row['label']:<18} {display_val}")

        self.console.print()
        self.console.print(
            "  [dim][green]S[/green] save · [red]X[/red] back · [blue]M[/blue] save+home · "
            "[yellow]Q[/yellow] discard+home · [yellow]R[/yellow] reset section[/dim]"
        )
        raw = self.console.input("  › ").strip().lower()

        if raw == "s":
            save_settings(draft)
            self._cfg = copy.deepcopy(draft)
            self.console.print("\n  [dim green]✓ Saved. Changes take effect next launch.[/dim green]")
            self.console.input("\n  [dim]Press Enter to return.[/dim] ")
            return "back"
        if raw == "x":
            return "back"
        if raw == "m":
            save_settings(draft)
            self._cfg = copy.deepcopy(draft)
            return "save_exit"
        if raw == "q":
            return "discard_exit"
        if raw == "r":
            confirm = self.console.input(
                f"  Reset {section['label']} to defaults? ([green]Y[/green] to confirm, any other key to cancel): "
            ).strip().lower()
            if confirm in ("y", "yes"):
                apply_section_defaults(draft, section)
                self.console.print(f"  [dim green]✓ {section['label']} reset to defaults.[/dim green]")
            continue
        if raw.isdigit():
            n = int(raw)
            if 1 <= n <= len(section["rows"]):
                row = section["rows"][n - 1]
                if row["type"] == "custom_chars":
                    if charset != "custom":
                        self.console.print("  [dim]Set character set to 'custom' first.[/dim]")
                        continue
                    v = self.console.input("  Enter custom characters (or Enter to keep): ").strip()
                    if v:
                        _set_draft_value(draft, row["key"], v)
                else:
                    self._edit_row(draft, row)
```

- [ ] **Step 4: Run section_subscreen tests — verify they pass**

```
python -m pytest tests/test_display.py -k "section_subscreen" -v
```
Expected: all pass.

- [ ] **Step 5: Run full test suite**

```
python -m pytest tests/ -x -q
```
Expected: all pass.

- [ ] **Step 6: Commit**

```
git add src/display.py tests/test_display.py
git commit -m "feat(display): add generic _section_subscreen with S/X/M/Q/R nav"
```

---

### Task 4: Python — `_show_reset_selector` and main screen R key

**Files:**
- Modify: `src/display.py`
- Test: `tests/test_display.py`

**Interfaces:**
- Consumes: `SETTINGS_SECTIONS`, `apply_section_defaults` from `src/config.py`
- Produces: `_show_reset_selector(draft: dict) -> str` — returns feedback string or `""` if cancelled

---

- [ ] **Step 1: Write failing tests**

Add to `tests/test_display.py`:

```python
def test_show_reset_selector_cancel_returns_empty(display):
    display.console.input = MagicMock(side_effect=["x"])
    draft = _make_draft()
    result = display._show_reset_selector(draft)
    assert result == ""

def test_show_reset_selector_nothing_checked_is_noop(display):
    # Y with no checkboxes checked — returns empty, no changes
    display.console.input = MagicMock(side_effect=["y", "x"])
    draft = _make_draft()
    original_tw = copy.deepcopy(draft.get("typewriter", {}))
    result = display._show_reset_selector(draft)
    # first Y does nothing (nothing selected), then x exits
    assert result == ""
    assert draft.get("typewriter") == original_tw

def test_show_reset_selector_resets_selected_section(display):
    # Toggle typewriter (1), then confirm (y)
    display.console.input = MagicMock(side_effect=["1", "y"])
    draft = _make_draft()
    draft["typewriter"]["enabled"] = False
    draft["typewriter"]["delay_ms"] = 999
    result = display._show_reset_selector(draft)
    assert draft["typewriter"]["enabled"] is True
    assert draft["typewriter"]["delay_ms"] == 35
    assert "Typewriter" in result

def test_show_reset_selector_preserves_unchecked_section(display):
    # Toggle typewriter (1) only, confirm (y) — corruption unchanged
    display.console.input = MagicMock(side_effect=["1", "y"])
    draft = _make_draft()
    draft["corruption"]["intensity"] = 0.2
    display._show_reset_selector(draft)
    assert draft["corruption"]["intensity"] == 0.2  # untouched

def test_show_reset_selector_feedback_lists_section_names(display):
    display.console.input = MagicMock(side_effect=["1", "2", "y"])
    draft = _make_draft()
    result = display._show_reset_selector(draft)
    assert "Typewriter" in result
    assert "Corruption" in result
```

- [ ] **Step 2: Run tests — verify they fail**

```
python -m pytest tests/test_display.py -k "show_reset_selector" -v
```
Expected: `AttributeError` — method not yet defined.

- [ ] **Step 3: Implement `_show_reset_selector` in `src/display.py`**

```python
def _show_reset_selector(self, draft: dict) -> str:
    """
    Show checkbox selector for resetting settings sections.
    Returns feedback message (e.g. "Reset: Typewriter.") or "" if cancelled.
    """
    from .config import SETTINGS_SECTIONS, apply_section_defaults
    resettable = [s for s in SETTINGS_SECTIONS if not s["preserve_on_global_reset"]]
    checked = [False] * len(resettable)

    while True:
        self.clear_screen()
        self.console.print()
        self.console.print(Rule("[bold cyan]Reset to Defaults[/bold cyan]"))
        self.console.print()
        self.console.print("  [dim]Note: Player name and accessible mode will always be preserved.[/dim]")
        self.console.print()
        self.console.print("  Select sections to reset:")
        self.console.print()
        for i, section in enumerate(resettable, start=1):
            mark = "[bold green]✓[/bold green]" if checked[i - 1] else " "
            self.console.print(f"  {i}. [{mark}] {section['label']}")
        self.console.print()
        self.console.print("  [dim]Number + Enter to toggle · [green]Y[/green] confirm · [red]X[/red] cancel[/dim]")
        raw = self.console.input("  › ").strip().lower()

        if raw == "x":
            return ""
        if raw == "y":
            selected = [resettable[i] for i, c in enumerate(checked) if c]
            if not selected:
                self.console.print("  [dim]Nothing selected.[/dim]")
                self.console.input("  [dim]Press Enter to continue.[/dim] ")
                continue
            for section in selected:
                apply_section_defaults(draft, section)
            return "Reset: " + ", ".join(s["label"] for s in selected) + "."
        if raw.isdigit():
            n = int(raw)
            if 1 <= n <= len(resettable):
                checked[n - 1] = not checked[n - 1]
```

- [ ] **Step 4: Run all new tests — verify they pass**

```
python -m pytest tests/test_display.py -k "show_reset_selector" -v
```
Expected: all pass.

- [ ] **Step 5: Run full test suite**

```
python -m pytest tests/ -x -q
```
Expected: all pass.

- [ ] **Step 6: Commit**

```
git add src/display.py tests/test_display.py
git commit -m "feat(display): add _show_reset_selector with checkbox UI and R key on main settings"
```

---

### Task 5: Web — `SETTINGS_SECTIONS` + derived `SETTINGS_ROWS` + `applyDefaults`

**Files:**
- Modify: `web/app.js`
- Create: `tests/test_web_settings.py`

**Interfaces:**
- Produces: `SETTINGS_SECTIONS` (array), derived `SETTINGS_ROWS` (array), `applyDefaults(draft, section)`

---

- [ ] **Step 1: Create `tests/test_web_settings.py` with failing tests**

```python
"""Tests for web/app.js settings registry and applyDefaults — run via Node.js."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(script: str) -> str:
    result = subprocess.run(
        ["node", "--input-type=module"],
        input=script.encode(),
        capture_output=True,
        cwd=ROOT,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr.decode()
    return result.stdout.decode().strip()


# Inline helpers used across tests (avoids DOM import issues with app.js)
_SETUP = """
import { TYPEWRITER_DEFAULTS } from './web/typewriter.js';

var SETTINGS_SECTIONS = [
  { id: 'typewriter', label: 'Typewriter', preserveOnGlobalReset: false, hasSubscreen: true,
    defaultKeys: ['enabled', 'delay_ms', 'pauses', 'pause_ms'],
    rows: [
      { key: 'enabled', label: 'Enabled', type: 'boolean' },
      { key: 'delay_ms', label: 'Speed', type: 'number', unit: 'ms' },
    ] },
  { id: 'display', label: 'Display', preserveOnGlobalReset: false, hasSubscreen: false,
    defaultKeys: ['page_size'],
    rows: [{ key: 'page_size', label: 'Stories per page', type: 'number', unit: '' }] },
  { id: 'corruption', label: 'Corruption', preserveOnGlobalReset: false, hasSubscreen: true,
    defaultKeys: ['corruption'],
    rows: [{ key: 'corruption.enabled', label: 'Enabled', type: 'boolean' }] },
  { id: 'player', label: 'Player', preserveOnGlobalReset: true, hasSubscreen: false,
    defaultKeys: ['player_name'],
    rows: [{ key: 'player_name', label: 'Player name', type: 'text' }] },
  { id: 'accessibility', label: 'Accessibility', preserveOnGlobalReset: true, hasSubscreen: true,
    defaultKeys: ['accessible_mode'],
    rows: [{ key: 'accessible_mode', label: 'Accessible mode', type: 'a11y' }] },
];

function applyDefaults(draft, section) {
  section.defaultKeys.forEach(function(key) {
    if (key === 'pauses') {
      draft.pauses = Object.assign({}, TYPEWRITER_DEFAULTS.pauses);
    } else if (key === 'corruption') {
      draft.corruption = Object.assign({}, TYPEWRITER_DEFAULTS.corruption);
    } else {
      draft[key] = TYPEWRITER_DEFAULTS[key];
    }
  });
}
"""


def test_settings_sections_ids():
    out = _run(_SETUP + """
var ids = SETTINGS_SECTIONS.map(function(s) { return s.id; });
console.log(JSON.stringify(ids));
""")
    ids = json.loads(out)
    assert 'typewriter' in ids
    assert 'corruption' in ids
    assert 'display' in ids
    assert 'player' in ids
    assert 'accessibility' in ids


def test_preserve_on_global_reset_flags():
    out = _run(_SETUP + """
var result = {};
SETTINGS_SECTIONS.forEach(function(s) { result[s.id] = s.preserveOnGlobalReset; });
console.log(JSON.stringify(result));
""")
    flags = json.loads(out)
    assert flags['typewriter'] is False
    assert flags['corruption'] is False
    assert flags['display'] is False
    assert flags['player'] is True
    assert flags['accessibility'] is True


def test_apply_defaults_typewriter():
    out = _run(_SETUP + """
var draft = { enabled: false, delay_ms: 999, pauses: {}, pause_ms: 0,
              page_size: 5, player_name: 'Felix',
              corruption: { enabled: true, charset: 'blocks', intensity: 1.0,
                            animate: true, scramble_frames: 5, scramble_delay_ms: 50 } };
var section = SETTINGS_SECTIONS.find(function(s) { return s.id === 'typewriter'; });
applyDefaults(draft, section);
console.log(JSON.stringify({ enabled: draft.enabled, delay_ms: draft.delay_ms }));
""")
    result = json.loads(out)
    assert result['enabled'] is True
    assert result['delay_ms'] == 20  # TYPEWRITER_DEFAULTS.delay_ms


def test_apply_defaults_corruption():
    out = _run(_SETUP + """
var draft = { enabled: true, delay_ms: 20, pauses: {}, pause_ms: 500,
              page_size: 5, player_name: 'Felix',
              corruption: { enabled: false, intensity: 0.1, animate: false,
                            charset: 'custom', scramble_frames: 1, scramble_delay_ms: 0 } };
var section = SETTINGS_SECTIONS.find(function(s) { return s.id === 'corruption'; });
applyDefaults(draft, section);
console.log(JSON.stringify(draft.corruption));
""")
    result = json.loads(out)
    assert result['enabled'] is True
    assert result['intensity'] == 1.0
    assert result['animate'] is True


def test_apply_defaults_does_not_touch_player_name():
    out = _run(_SETUP + """
var draft = { enabled: false, delay_ms: 999, pauses: {}, pause_ms: 0,
              page_size: 5, player_name: 'Zara',
              corruption: { enabled: true, charset: 'blocks', intensity: 1.0,
                            animate: true, scramble_frames: 5, scramble_delay_ms: 50 } };
var section = SETTINGS_SECTIONS.find(function(s) { return s.id === 'typewriter'; });
applyDefaults(draft, section);
console.log(draft.player_name);
""")
    assert out == 'Zara'
```

- [ ] **Step 2: Run tests — verify they fail**

```
python -m pytest tests/test_web_settings.py -v
```
Expected: `AssertionError` (Node can't find the inlined functions yet — the test exercises the inlined definitions in `_SETUP`, but confirms the logic is correct before putting it in app.js).

Actually these tests inline the logic so they should pass immediately. Run them and confirm they do pass before touching app.js — this validates the design:

```
python -m pytest tests/test_web_settings.py -v
```
Expected: all pass (they test the inlined reference implementation).

- [ ] **Step 3: Add `SETTINGS_SECTIONS` to `web/app.js`**

In `web/app.js`, replace the entire `var SETTINGS_ROWS = [...]` block (lines 206–224) with:

```js
var SETTINGS_SECTIONS = [
  {
    id: 'typewriter', label: 'Typewriter',
    preserveOnGlobalReset: false, hasSubscreen: true,
    defaultKeys: ['enabled', 'delay_ms', 'pauses', 'pause_ms'],
    rows: [
      { key: 'enabled',   label: 'Enabled',        type: 'boolean',                             subsection: 'Typewriter' },
      { key: 'delay_ms',  label: 'Speed',           type: 'number',  unit: 'ms',                subsection: null },
      { key: 'pauses..',  label: 'Pause after  .', type: 'number',  unit: 'ms',                subsection: null },
      { key: 'pauses.!',  label: 'Pause after  !', type: 'number',  unit: 'ms',                subsection: null },
      { key: 'pauses.?',  label: 'Pause after  ?', type: 'number',  unit: 'ms',                subsection: null },
      { key: 'pauses.…', label: 'Pause after  …', type: 'number', unit: 'ms',        subsection: null },
      { key: 'pauses.—', label: 'Pause after  —', type: 'number', unit: 'ms',        subsection: null },
    ],
  },
  {
    id: 'display', label: 'Display',
    preserveOnGlobalReset: false, hasSubscreen: false,
    defaultKeys: ['page_size'],
    rows: [
      { key: 'page_size', label: 'Stories per page', type: 'number', unit: '', subsection: 'Display' },
    ],
  },
  {
    id: 'corruption', label: 'Corruption',
    preserveOnGlobalReset: false, hasSubscreen: true,
    defaultKeys: ['corruption'],
    rows: [
      { key: 'corruption.enabled',           label: 'Enabled',         type: 'boolean',                                              subsection: 'Corruption' },
      { key: 'corruption.intensity',         label: 'Intensity',       type: 'float',   unit: '×',                             subsection: null },
      { key: 'corruption.mode',              label: 'Mode',            type: 'cycle',   values: ['consistent', 'random'],            subsection: null },
      { key: 'corruption.charset',           label: 'Character set',   type: 'cycle',   values: ['blocks', 'symbols', 'diacritics', 'custom'], subsection: null },
      { key: 'corruption.animate',           label: 'Animate',         type: 'boolean',                                             subsection: null },
      { key: 'corruption.scramble_frames',   label: 'Scramble frames', type: 'number',  unit: '',                                   subsection: null },
      { key: 'corruption.scramble_delay_ms', label: 'Scramble delay',  type: 'number',  unit: 'ms',                                 subsection: null },
    ],
  },
  {
    id: 'player', label: 'Player',
    preserveOnGlobalReset: true, hasSubscreen: false,
    defaultKeys: ['player_name'],
    rows: [
      { key: 'player_name', label: 'Player name', type: 'text', subsection: 'Player' },
    ],
  },
  {
    id: 'accessibility', label: 'Accessibility',
    preserveOnGlobalReset: true, hasSubscreen: true,
    defaultKeys: ['accessible_mode'],
    rows: [
      { key: 'accessible_mode', label: 'Accessible mode', type: 'a11y', subsection: 'Accessibility' },
    ],
  },
];

var SETTINGS_ROWS = SETTINGS_SECTIONS.reduce(function(acc, section) {
  if (section.hasSubscreen) {
    acc.push({
      key: '__nav__' + section.id,
      label: section.label,
      type: 'nav',
      section: section.label,
      _section: section,
    });
  } else {
    section.rows.forEach(function(row, i) {
      acc.push(Object.assign({}, row, { section: i === 0 ? (row.subsection || section.label) : null }));
    });
  }
  return acc;
}, []);

function applyDefaults(draft, section) {
  section.defaultKeys.forEach(function(key) {
    if (key === 'pauses') {
      draft.pauses = Object.assign({}, TYPEWRITER_DEFAULTS.pauses);
    } else if (key === 'corruption') {
      draft.corruption = Object.assign({}, TYPEWRITER_DEFAULTS.corruption);
    } else {
      draft[key] = TYPEWRITER_DEFAULTS[key];
    }
  });
}
```

- [ ] **Step 4: Update `renderSettings` to handle `nav` row type**

In `renderSettings`, find the display value assignment block (around line 661) and add a case for `nav`:

```js
} else if (row.type === 'nav') {
  display = '→';
```

Place this before the final `else` that handles `unit`.

- [ ] **Step 5: Update `startSettingsEdit` to navigate on `nav` rows**

In `startSettingsEdit` (around line 1288), add at the top of the function body:

```js
if (row.type === 'nav') {
  renderSectionSubscreen(row._section);
  return;
}
```

Place this before the existing `if (row.key === 'delay_ms') { renderSpeedPresets(); return; }` line.

- [ ] **Step 6: Run web settings tests against the new app.js code**

The `test_web_settings.py` tests inline their own definitions, so they still pass. Optionally open the browser and verify the settings screen shows nav rows for Typewriter, Corruption, and Accessibility, and inline rows for Display and Player.

- [ ] **Step 7: Run full Python test suite**

```
python -m pytest tests/ -x -q
```
Expected: all pass (no Python breakage from JS changes).

- [ ] **Step 8: Commit**

```
git add web/app.js tests/test_web_settings.py
git commit -m "feat(web): add SETTINGS_SECTIONS registry, derive SETTINGS_ROWS, add applyDefaults"
```

---

### Task 6: Web — `renderSectionSubscreen` (terminal + accessible)

**Files:**
- Modify: `web/app.js`

**Interfaces:**
- Consumes: `SETTINGS_SECTIONS`, `applyDefaults`, `getSettingValue`, `setSettingValue`, `renderSettings`, `renderLibrary`, `renderSpeedPresets`, `saveTypewriterSettings`, `loadTypewriterSettings`
- Produces: `renderSectionSubscreen(section)`, `renderAccessibleSectionSubscreen(section)`; module vars `currentSectionScreen`, `sectionDraftSnapshot`, `sectionEditRow`

---

- [ ] **Step 1: Add module-level variables near the top of `web/app.js`** (after existing var declarations around line 34):

```js
var currentSectionScreen = null;
var sectionDraftSnapshot = null;
var sectionEditRow = null;
var speedPresetsReturn = null;
```

- [ ] **Step 2: Add `renderSectionSubscreen` to `web/app.js`** (after `renderSpeedPresets`):

```js
function renderSectionSubscreen(section) {
  if (isAccessibleMode()) { renderAccessibleSectionSubscreen(section); return; }
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  currentScreen = 'settings-section';
  currentSectionScreen = section;
  sectionEditRow = null;

  // Snapshot this section's keys so X can restore them
  sectionDraftSnapshot = {};
  section.defaultKeys.forEach(function(key) {
    var val = settingsDraft[key];
    if (val !== null && typeof val === 'object') {
      sectionDraftSnapshot[key] = Object.assign({}, val);
    } else {
      sectionDraftSnapshot[key] = val;
    }
  });

  setPageTitle('Settings – ' + section.label);

  var rows = '';
  section.rows.forEach(function(row, i) {
    var val = getSettingValue(settingsDraft, row.key);
    var display;
    if (row.type === 'boolean') {
      display = val ? 'on' : 'off';
    } else if (row.type === 'a11y') {
      display = val === null || val === undefined ? 'auto' : val ? 'on' : 'off';
    } else if (row.type === 'cycle') {
      display = val;
    } else {
      display = String(val != null ? val : '') + (row.unit ? ' ' + row.unit : '');
    }
    rows += '<div class="terminal-settings-row" data-action="section-row" data-row="' + i + '">' +
      '<span class="setting-num">' + (i + 1) + '.</span>' +
      '<span class="setting-name">' + escapeHtml(row.label) + '</span>' +
      '<span class="setting-value" id="section-val-' + i + '">' + escapeHtml(String(display)) + '</span>' +
      '</div>';
  });

  app.innerHTML =
    '<div class="terminal-screen">' +
    renderRule('Settings – ' + section.label, 'green') +
    '<div class="terminal-list">' + rows + '</div>' +
    '<div class="terminal-footer">' +
    '<div class="footer-hint">Enter a number to edit &middot; ' +
    '<span class="key-fwd">S</span> save &middot; ' +
    '<span class="key-back">X</span> back &middot; ' +
    '<span class="key-fwd">M</span> save+home &middot; ' +
    '<span class="key-back">Q</span> discard+home &middot; ' +
    '<span class="key-fwd">R</span> reset section</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">⌨ Tap to type</button>' +
    '</div></div>';
  updatePrompt();
}
```

- [ ] **Step 3: Wire click handler for section rows**

In the `app.addEventListener('click', ...)` block (around line 1454), add a new case after `'settings-row'`:

```js
} else if (action === 'section-row') {
  startSectionRowEdit(Number(button.dataset.row));
```

- [ ] **Step 4: Add `startSectionRowEdit`, `confirmSectionRowEdit`, `cancelSectionRowEdit`**

Add after `cancelSettingsEdit`:

```js
function startSectionRowEdit(rowIndex) {
  if (!currentSectionScreen) return;
  var row = currentSectionScreen.rows[rowIndex];
  if (!row) return;
  var val = getSettingValue(settingsDraft, row.key);

  if (row.key === 'delay_ms') {
    speedPresetsReturn = function() { renderSectionSubscreen(currentSectionScreen); };
    renderSpeedPresets();
    return;
  }
  if (row.type === 'boolean') {
    setSettingValue(settingsDraft, row.key, !val);
    renderSectionSubscreen(currentSectionScreen);
    return;
  }
  if (row.type === 'a11y') {
    var cur = settingsDraft.accessible_mode;
    settingsDraft.accessible_mode = cur === null ? true : cur === true ? false : null;
    renderSectionSubscreen(currentSectionScreen);
    return;
  }
  if (row.type === 'cycle') {
    var cycleIdx = row.values ? row.values.indexOf(val) : -1;
    setSettingValue(settingsDraft, row.key, row.values[(cycleIdx < 0 ? 0 : cycleIdx + 1) % row.values.length]);
    renderSectionSubscreen(currentSectionScreen);
    return;
  }
  if (isAccessibleMode() && (row.type === 'number' || row.type === 'float' || row.type === 'text')) {
    var entered = window.prompt(row.label + ':', String(val || ''));
    if (entered !== null) {
      if (row.type === 'text') {
        if (entered.trim() !== '') setSettingValue(settingsDraft, row.key, entered.trim());
      } else if (row.type === 'float') {
        var fnum = parseFloat(entered);
        if (!isNaN(fnum) && fnum >= 0 && fnum <= 1) setSettingValue(settingsDraft, row.key, fnum);
      } else {
        var num = parseInt(entered, 10);
        if (!isNaN(num) && num >= 0) setSettingValue(settingsDraft, row.key, num);
      }
    }
    renderSectionSubscreen(currentSectionScreen);
    return;
  }
  // Inline edit (desktop)
  sectionEditRow = rowIndex;
  var valEl = document.getElementById('section-val-' + rowIndex);
  if (!valEl) return;
  if (window.matchMedia('(pointer: coarse)').matches) {
    valEl.innerHTML = '<span class="setting-editing">(editing&hellip;)</span>';
    pendingInput = String(val);
    mobileCapture.value = String(val);
    var hintEl = document.querySelector('.footer-hint');
    if (hintEl) hintEl.innerHTML = 'Enter to confirm &middot; <span class="key-back">Esc</span> to cancel.';
    updatePrompt();
    mobileCapture.focus();
  } else {
    valEl.innerHTML = '<input class="setting-input" id="section-edit-input" type="text" value="' + escapeHtml(String(val)) + '" autocomplete="off">';
    var input = document.getElementById('section-edit-input');
    if (input) { input.focus(); input.select(); }
  }
}

function confirmSectionRowEdit() {
  if (sectionEditRow === null || !currentSectionScreen) return;
  var row = currentSectionScreen.rows[sectionEditRow];
  if (!row) return;
  var inlineInput = document.getElementById('section-edit-input');
  var valueStr = inlineInput ? inlineInput.value : pendingInput.trim();
  if (row.type === 'text') {
    if (valueStr.trim() !== '') setSettingValue(settingsDraft, row.key, valueStr.trim());
  } else if (row.type === 'float') {
    var fnum = parseFloat(valueStr);
    if (!isNaN(fnum) && fnum >= 0 && fnum <= 1) setSettingValue(settingsDraft, row.key, fnum);
  } else {
    var num = parseInt(valueStr, 10);
    if (!isNaN(num) && num >= 0) setSettingValue(settingsDraft, row.key, num);
  }
  sectionEditRow = null;
  pendingInput = '';
  renderSectionSubscreen(currentSectionScreen);
}

function cancelSectionRowEdit() {
  sectionEditRow = null;
  pendingInput = '';
  renderSectionSubscreen(currentSectionScreen);
}
```

- [ ] **Step 5: Update `renderSpeedPresets` exit path to respect `speedPresetsReturn`**

In `renderSpeedPresets`, find the two places that call `renderSettings()` after a preset is picked (in the click handler and in `handleSubmit` for `'settings-speed'`). Both should be changed to:

```js
if (speedPresetsReturn) { var fn = speedPresetsReturn; speedPresetsReturn = null; fn(); }
else renderSettings();
```

Apply this to both: the `SPEED_PRESETS` click handler in `renderSpeedPresets`, and the `sp >= 1` branch in `handleSubmit` `'settings-speed'` case.

- [ ] **Step 6: Add `renderAccessibleSectionSubscreen`** (after `renderAccessibleSpeedPresets`):

```js
function renderAccessibleSectionSubscreen(section) {
  pendingInput = '';
  currentScreen = 'settings-section';
  currentSectionScreen = section;
  document.body.classList.add('reader-mode');
  setPageTitle('Settings – ' + section.label);

  sectionDraftSnapshot = {};
  section.defaultKeys.forEach(function(key) {
    var val = settingsDraft[key];
    sectionDraftSnapshot[key] = (val !== null && typeof val === 'object') ? Object.assign({}, val) : val;
  });

  var rowsHtml = section.rows.map(function(row, i) {
    var val = getSettingValue(settingsDraft, row.key);
    var display;
    if (row.type === 'boolean') display = val ? 'On' : 'Off';
    else if (row.type === 'a11y') display = val === null || val === undefined ? 'Auto' : val ? 'On' : 'Off';
    else if (row.type === 'cycle') display = val;
    else display = String(val != null ? val : '') + (row.unit ? ' ' + row.unit : '');
    return '<div role="listitem" class="r-setting-row" tabindex="0" data-section-row-index="' + i + '"' +
      ' aria-label="' + escapeHtml(row.label) + ', currently ' + escapeHtml(String(display)) + '">' +
      '<span class="r-setting-num">' + (i + 1) + '.</span>' +
      '<span class="r-setting-label">' + escapeHtml(row.label) + '</span>' +
      '<span class="r-setting-value">' + escapeHtml(String(display)) + '</span>' +
      '</div>';
  }).join('');

  app.innerHTML =
    '<main class="reader-screen">' +
    '<h1 class="r-page-title">Settings – ' + escapeHtml(section.label) + '</h1>' +
    '<p class="r-page-sub">Press Enter on a row to edit its value.</p>' +
    '<div class="r-settings" role="list" aria-label="' + escapeHtml(section.label) + ' settings">' + rowsHtml + '</div>' +
    '<div class="r-nav">' +
    '<button class="r-btn primary r-section-save-btn">Save</button>' +
    '<button class="r-btn ghost r-section-back-btn">&#8592; Back to settings</button>' +
    '<button class="r-btn ghost r-section-save-home-btn">Save &amp; Home</button>' +
    '<button class="r-btn ghost r-section-discard-home-btn">Discard &amp; Home</button>' +
    '<button class="r-btn ghost r-section-reset-btn">Reset section to defaults</button>' +
    '</div>' +
    '</main>';

  app.querySelectorAll('[data-section-row-index]').forEach(function(row) {
    row.addEventListener('click', function() { startSectionRowEdit(Number(row.dataset.sectionRowIndex)); });
    row.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); startSectionRowEdit(Number(row.dataset.sectionRowIndex)); }
    });
  });
  app.querySelector('.r-section-save-btn').addEventListener('click', function() {
    saveTypewriterSettings(settingsDraft); renderSettings();
  });
  app.querySelector('.r-section-back-btn').addEventListener('click', function() {
    Object.assign(settingsDraft, sectionDraftSnapshot); renderSettings();
  });
  app.querySelector('.r-section-save-home-btn').addEventListener('click', function() {
    saveTypewriterSettings(settingsDraft); settingsDraft = null; renderLibrary();
  });
  app.querySelector('.r-section-discard-home-btn').addEventListener('click', function() {
    settingsDraft = null; renderLibrary();
  });
  app.querySelector('.r-section-reset-btn').addEventListener('click', function() {
    if (confirm('Reset ' + section.label + ' to defaults?')) {
      applyDefaults(settingsDraft, section);
      renderAccessibleSectionSubscreen(section);
    }
  });

  var first = app.querySelector('[data-section-row-index]');
  if (first) first.focus();
}
```

- [ ] **Step 7: Run full test suite**

```
python -m pytest tests/ -x -q
```
Expected: all pass.

- [ ] **Step 8: Commit**

```
git add web/app.js
git commit -m "feat(web): add renderSectionSubscreen, renderAccessibleSectionSubscreen, section row edit helpers"
```

---

### Task 7: Web — Sub-screen input dispatch

**Files:**
- Modify: `web/app.js`

**Interfaces:**
- Consumes: `currentSectionScreen`, `sectionEditRow`, `renderSectionSubscreen`, `renderSettings`, `renderLibrary`, `saveTypewriterSettings`, `confirmSectionRowEdit`, `cancelSectionRowEdit`, `applyDefaults`

---

- [ ] **Step 1: Add `'settings-section'` to `promptPrefix`**

In `promptPrefix` (around line 255), add before the final `return '&gt; '`:

```js
if (currentScreen === 'settings-section' && sectionEditRow !== null) {
  var srow = currentSectionScreen ? currentSectionScreen.rows[sectionEditRow] : null;
  return 'Edit ' + (srow ? srow.label : 'value') + ': ';
}
if (currentScreen === 'settings-section') return '&gt; ';
if (currentScreen === 'settings-reset')   return '&gt; ';
```

- [ ] **Step 2: Add `'settings-section'` case to `handleSubmit`**

In `handleSubmit`, after the `'settings-speed'` block (after line 1552), add:

```js
} else if (currentScreen === 'settings-section') {
  if (input === 's') {
    saveTypewriterSettings(settingsDraft);
    renderSettings();
    return;
  }
  if (input === 'x') {
    Object.assign(settingsDraft, sectionDraftSnapshot);
    renderSettings();
    return;
  }
  if (input === 'm') {
    saveTypewriterSettings(settingsDraft);
    settingsDraft = null;
    renderLibrary();
    return;
  }
  if (input === 'q') {
    settingsDraft = null;
    renderLibrary();
    return;
  }
  if (input === 'r') {
    renderSectionResetConfirm();
    return;
  }
  var sn = parseInt(input, 10);
  if (sn >= 1 && currentSectionScreen && sn <= currentSectionScreen.rows.length) {
    startSectionRowEdit(sn - 1);
  }
```

- [ ] **Step 3: Add `renderSectionResetConfirm`**

Add after `renderSectionSubscreen`:

```js
function renderSectionResetConfirm() {
  if (!currentSectionScreen) return;
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  currentScreen = 'settings-section-reset';
  setPageTitle('Settings – ' + currentSectionScreen.label);
  app.innerHTML =
    '<div class="terminal-screen">' +
    renderRule('Reset ' + currentSectionScreen.label + ' to Defaults', 'green') +
    '<div class="terminal-list">' +
    '<div class="terminal-settings-row">' +
    '<span class="setting-name">Reset ' + escapeHtml(currentSectionScreen.label) + ' settings to defaults?</span>' +
    '</div></div>' +
    '<div class="terminal-footer">' +
    '<div class="footer-hint"><span class="key-fwd">Y</span> confirm &middot; <span class="key-back">any other key</span> cancel</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">⌨ Tap to type</button>' +
    '</div></div>';
  updatePrompt();
}
```

Add a case for `'settings-section-reset'` in `handleSubmit` (after the `'settings-section'` block):

```js
} else if (currentScreen === 'settings-section-reset') {
  if (input === 'y') {
    applyDefaults(settingsDraft, currentSectionScreen);
  }
  renderSectionSubscreen(currentSectionScreen);
```

- [ ] **Step 4: Handle Enter/Escape in keydown handler for section edit**

In the `keydown` event listener (around line 1555), find the `settings` row-edit block:

```js
if (currentScreen === 'settings' && settingsEditRow !== null) {
  if (keyUp === 'ENTER')  { confirmSettingsEdit(); return; }
  if (keyUp === 'ESCAPE') { cancelSettingsEdit();  return; }
  return;
}
```

Add the equivalent for section screens immediately after:

```js
if (currentScreen === 'settings-section' && sectionEditRow !== null) {
  if (keyUp === 'ENTER')  { confirmSectionRowEdit(); return; }
  if (keyUp === 'ESCAPE') { cancelSectionRowEdit();  return; }
  return;
}
```

- [ ] **Step 5: Handle mobile capture for section edit**

In `mobileCapture.addEventListener('input', ...)` (around line 1636), add a case before the default `pendingInput = mobileCapture.value` fallthrough:

```js
if (currentScreen === 'settings-section' && sectionEditRow !== null) {
  var sInline = document.getElementById('section-edit-input');
  if (sInline) {
    sInline.value = mobileCapture.value;
  } else {
    pendingInput = mobileCapture.value;
    updatePrompt();
  }
  return;
}
```

In `mobileCapture.addEventListener('keydown', ...)` (around line 1651), add before the outer Enter handler:

```js
if (currentScreen === 'settings-section' && sectionEditRow !== null) {
  if (e.key === 'Enter') {
    e.preventDefault();
    mobileCapture.value = '';
    confirmSectionRowEdit();
    setTimeout(function() { mobileCapture.focus(); }, 0);
  } else if (e.key === 'Escape') {
    e.preventDefault();
    mobileCapture.value = '';
    cancelSectionRowEdit();
    setTimeout(function() { mobileCapture.focus(); }, 0);
  }
  return;
}
```

- [ ] **Step 6: Run full test suite**

```
python -m pytest tests/ -x -q
```
Expected: all pass.

- [ ] **Step 7: Commit**

```
git add web/app.js
git commit -m "feat(web): wire section subscreen input dispatch — S/X/M/Q/R/number keys"
```

---

### Task 8: Web — `renderResetSelector` and main settings screen R key

**Files:**
- Modify: `web/app.js`

**Interfaces:**
- Consumes: `SETTINGS_SECTIONS`, `applyDefaults`, `renderSettings`, module var `resetChecked`

---

- [ ] **Step 1: Add module-level `resetChecked` variable** (near the other module vars added in Task 6):

```js
var resetChecked = {};
var resetFeedback = '';
```

- [ ] **Step 2: Add `renderResetSelector` and `renderResetSelectorView`** (after `renderSectionResetConfirm`):

```js
function renderResetSelector() {
  if (isAccessibleMode()) { renderAccessibleResetSelector(); return; }
  document.body.classList.remove('reader-mode');
  pendingInput = '';
  currentScreen = 'settings-reset';
  resetChecked = {};
  setPageTitle('Settings – Reset');
  renderResetSelectorView();
}

function renderResetSelectorView() {
  var resettable = SETTINGS_SECTIONS.filter(function(s) { return !s.preserveOnGlobalReset; });
  var rows = resettable.map(function(section, i) {
    var checked = !!resetChecked[section.id];
    var mark = checked ? '<span class="key-fwd">✓</span>' : ' ';
    return '<div class="terminal-settings-row" data-action="reset-toggle" data-index="' + i + '">' +
      '<span class="setting-num">' + (i + 1) + '.</span>' +
      '<span class="setting-name">[' + mark + '] ' + escapeHtml(section.label) + '</span>' +
      '</div>';
  }).join('');

  app.innerHTML =
    '<div class="terminal-screen">' +
    renderRule('Reset to Defaults', 'green') +
    '<div class="terminal-hint" style="padding:0 1em 0.5em;opacity:0.6">Note: Player name and accessible mode will always be preserved.</div>' +
    '<div class="terminal-list">' + rows + '</div>' +
    '<div class="terminal-footer">' +
    '<div class="footer-hint">Number + Enter to toggle &middot; <span class="key-fwd">Y</span> confirm &middot; <span class="key-back">X</span> cancel</div>' +
    '<div class="terminal-prompt-line"></div>' +
    '<button class="mobile-keyboard-btn" data-action="show-keyboard" aria-label="Open keyboard">⌨ Tap to type</button>' +
    '</div></div>';
  updatePrompt();
}

function renderAccessibleResetSelector() {
  pendingInput = '';
  currentScreen = 'settings-reset';
  resetChecked = {};
  document.body.classList.add('reader-mode');
  setPageTitle('Settings – Reset to Defaults');

  var resettable = SETTINGS_SECTIONS.filter(function(s) { return !s.preserveOnGlobalReset; });
  var itemsHtml = resettable.map(function(section, i) {
    return '<li><button class="r-btn ghost r-reset-section-btn" data-index="' + i + '"' +
      ' aria-pressed="false">' + escapeHtml(section.label) + '</button></li>';
  }).join('');

  app.innerHTML =
    '<main class="reader-screen">' +
    '<h1 class="r-page-title">Reset to Defaults</h1>' +
    '<p class="r-page-sub">Note: Player name and accessible mode will always be preserved.</p>' +
    '<ul class="r-presets">' + itemsHtml + '</ul>' +
    '<div class="r-nav">' +
    '<button class="r-btn primary r-reset-confirm-btn">Reset selected</button>' +
    '<button class="r-btn ghost r-reset-cancel-btn">Cancel</button>' +
    '</div>' +
    '</main>';

  app.querySelectorAll('.r-reset-section-btn').forEach(function(btn, i) {
    btn.addEventListener('click', function() {
      var sid = resettable[i].id;
      var checked = !!resetChecked[sid];
      resetChecked[sid] = !checked;
      btn.setAttribute('aria-pressed', String(!checked));
      btn.classList.toggle('r-btn-active', !checked);
    });
  });
  app.querySelector('.r-reset-confirm-btn').addEventListener('click', function() {
    var selected = resettable.filter(function(s) { return !!resetChecked[s.id]; });
    if (selected.length === 0) { alert('Nothing selected.'); return; }
    selected.forEach(function(s) { applyDefaults(settingsDraft, s); });
    resetFeedback = 'Reset: ' + selected.map(function(s) { return s.label; }).join(', ') + '.';
    renderSettings();
  });
  app.querySelector('.r-reset-cancel-btn').addEventListener('click', renderSettings);

  var first = app.querySelector('.r-reset-section-btn');
  if (first) first.focus();
}
```

- [ ] **Step 3: Add `'settings-reset'` case to `handleSubmit`** (after the `'settings-section-reset'` block):

```js
} else if (currentScreen === 'settings-reset') {
  var resettable = SETTINGS_SECTIONS.filter(function(s) { return !s.preserveOnGlobalReset; });
  if (input === 'x') { renderSettings(); return; }
  if (input === 'y') {
    var selected = resettable.filter(function(s) { return !!resetChecked[s.id]; });
    if (selected.length === 0) {
      renderResetSelectorView();
      return;
    }
    selected.forEach(function(s) { applyDefaults(settingsDraft, s); });
    resetFeedback = 'Reset: ' + selected.map(function(s) { return s.label; }).join(', ') + '.';
    renderSettings();
    return;
  }
  var rn = parseInt(input, 10);
  if (rn >= 1 && rn <= resettable.length) {
    var sid = resettable[rn - 1].id;
    resetChecked[sid] = !resetChecked[sid];
    renderResetSelectorView();
  }
```

- [ ] **Step 4: Wire `data-action="reset-toggle"` in the click handler**

In `app.addEventListener('click', ...)`, add after the `'section-row'` case:

```js
} else if (action === 'reset-toggle') {
  var rtIdx = Number(button.dataset.index);
  var resettableList = SETTINGS_SECTIONS.filter(function(s) { return !s.preserveOnGlobalReset; });
  if (rtIdx >= 0 && rtIdx < resettableList.length) {
    var rtSid = resettableList[rtIdx].id;
    resetChecked[rtSid] = !resetChecked[rtSid];
    renderResetSelectorView();
  }
```

- [ ] **Step 5: Add R key to main settings screen and show `resetFeedback`**

In `handleSubmit`, in the `'settings'` block (around line 1526), add the R case and feedback:

```js
} else if (currentScreen === 'settings') {
  if (input === 'x') { renderLibrary(); return; }
  if (input === 's') { saveTypewriterSettings(settingsDraft); renderLibrary(); return; }
  if (input === 'r') { renderResetSelector(); return; }
  var ns = parseInt(input, 10);
  if (ns >= 1 && ns <= SETTINGS_ROWS.length) startSettingsEdit(ns - 1);
```

- [ ] **Step 6: Show `resetFeedback` in `renderSettings`**

In `renderSettings`, update the footer hint to include `R` and show feedback if set. Find the `footer-hint` div string and update it:

```js
'<div class="footer-hint">Enter a number to edit &middot; <span class="key-fwd">S</span> save &middot; <span class="key-back">X</span> discard &middot; <span class="key-fwd">R</span> reset. Press Enter to confirm.' +
(resetFeedback ? '<div class="reset-feedback" style="color:#6af;margin-top:4px">✓ ' + escapeHtml(resetFeedback) + '</div>' : '') + '</div>' +
```

Then immediately after building `app.innerHTML` in `renderSettings`, clear the feedback:

```js
resetFeedback = '';
updatePrompt();
```

- [ ] **Step 7: Run full test suite**

```
python -m pytest tests/ -x -q
```
Expected: all pass.

- [ ] **Step 8: Commit**

```
git add web/app.js
git commit -m "feat(web): add renderResetSelector, R key on settings screen, checkbox reset flow"
```

---

## Self-Review Checklist

### Spec coverage

| Spec requirement | Task |
|---|---|
| `SETTINGS_SECTIONS` registry (id, label, preserveOnGlobalReset, hasSubscreen, defaults, rows) | T1 (Python), T5 (Web) |
| Row descriptor (key, label, type, unit, values, range) | T1, T5 |
| Sections: typewriter/display/corruption/player + accessibility (web only) | T1, T5 |
| Main screen iterates registry, auto-numbers rows | T2 (Python), T5/T6 (Web) |
| hasSubscreen sections render as `→` nav row | T2, T6 |
| Generic `_section_subscreen` / `renderSectionSubscreen` | T3, T6 |
| Sub-screen nav: S/X/M/Q/R | T3, T7 |
| X discard section only, rest of draft intact | T3 (snapshot), T7 |
| Preservation note upfront in checkbox selector | T4, T8 |
| Checkbox multi-digit + Enter to toggle | T4, T8 |
| Y with nothing selected = no-op | T4, T8 |
| Post-reset feedback: section names only | T4, T8 |
| Accessible mode: section sub-screens with buttons | T6 (`renderAccessibleSectionSubscreen`) |
| Accessible mode: reset selector with buttons | T8 (`renderAccessibleResetSelector`) |
| `_settings_corruption` deleted | T2 |
| Old Python helpers (`_settings_edit_pause/page_size/player_name`) deleted | T2 |
| `SETTINGS_ROWS` derived from `SETTINGS_SECTIONS` | T5 |
| `applyDefaults` helper | T5 |
| Speed presets return path respects sub-screen origin | T6 (`speedPresetsReturn`) |

### Placeholder scan

No TBDs, TODOs, or incomplete steps found.

### Type consistency

- `_section_subscreen` returns `"back"` | `"save_exit"` | `"discard_exit"` — consumed in `show_settings_screen` Task 2 step 5. ✓
- `_show_reset_selector` returns `str` — consumed in `show_settings_screen` as `reset_feedback`. ✓
- `apply_section_defaults(draft, section)` — called in T3 and T4 with `section` from `SETTINGS_SECTIONS`. ✓
- `applyDefaults(draft, section)` (web) — called in T7 and T8 with `section` from `SETTINGS_SECTIONS`. ✓
- `sectionDraftSnapshot` set in T6, consumed in T7 (`Object.assign(settingsDraft, sectionDraftSnapshot)`). ✓
- `resetFeedback` set in T8 step 3/4, consumed in T8 step 6 in `renderSettings`. ✓
- `speedPresetsReturn` set in T6, consumed in T6 step 5 exit path. ✓
