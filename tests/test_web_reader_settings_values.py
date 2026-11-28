"""Reader mode: the main Settings screen must not print the word 'undefined'.

web/app.js needs a browser, so it cannot be imported in Node as it is. These tests
cut the real settings table and the real renderAccessibleSettings function out of
the file and run them in Node with a pretend page.
"""
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


def _between(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin:source.index(end, begin) + len(end)]


def _function(source: str, name: str) -> str:
    return _between(source, f"function {name}(", "\n}\n")


def _reader_settings_rows() -> list[dict]:
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    script = "\n".join([
        "import { TYPEWRITER_DEFAULTS } from './web/typewriter.js';",
        # A pretend page: just enough for the function to draw into.
        "var app = { innerHTML: '', querySelectorAll: function() { return []; },",
        "  querySelector: function() { return { addEventListener: function() {}, focus: function() {} }; } };",
        "var document = { body: { classList: { add: function() {} } } };",
        "var currentSectionScreen, sectionDraftSnapshot, pendingInput, currentScreen, settingsEditRow;",
        "var settingsDraft = null;",
        "function setPageTitle() {}",
        "function renderLibrary() {}",
        "function isAccessibleMode() { return true; }",
        "function loadTypewriterSettings() { return JSON.parse(JSON.stringify(TYPEWRITER_DEFAULTS)); }",
        _between(app, "var SETTINGS_SECTIONS = [", "\n];"),
        _between(app, "var SETTINGS_ROWS = ", "\n}, []);"),
        _function(app, "escapeHtml"),
        _function(app, "getSettingValue"),
        _function(app, "renderAccessibleSettings"),
        "renderAccessibleSettings('');",
        "var rows = [];",
        "var pattern = /data-row-index=\"\\d+\" aria-label=\"([^\"]*)\"><span class=\"r-setting-num\">\\d+\\.<\\/span>"
        "<span class=\"r-setting-label\">(.*?)<\\/span>"
        "<span class=\"r-setting-value\">(.*?)<\\/span>/g;",
        "var match;",
        "while ((match = pattern.exec(app.innerHTML))) rows.push({ aria: match[1], label: match[2], value: match[3] });",
        "console.log(JSON.stringify(rows));",
    ])
    return json.loads(_run(script))


def test_reader_settings_shows_all_five_rows():
    labels = [row["label"] for row in _reader_settings_rows()]
    assert labels == ["Typewriter", "Stories per page", "Corruption", "Player name Default", "Accessibility"]


def test_reader_settings_never_shows_the_word_undefined():
    for row in _reader_settings_rows():
        assert "undefined" not in row["value"], row
        assert "undefined" not in row["aria"], row


def test_reader_settings_section_rows_show_the_same_arrow_as_the_terminal_screen():
    values = {row["label"]: row["value"] for row in _reader_settings_rows()}
    # The terminal-style settings screen shows this arrow on the rows that open another screen.
    assert values["Typewriter"] == "→"
    assert values["Corruption"] == "→"
    assert values["Accessibility"] == "→"
