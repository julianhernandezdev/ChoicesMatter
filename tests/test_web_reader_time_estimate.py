"""Reader mode: the time shown in the game header must be the story's own estimate.

web/app.js needs a browser, so it cannot be imported in Node as it is. These tests
cut the real estimateTime and renderAccessibleGame functions out of the file and
run them in Node with a pretend page.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_WITH_ESTIMATE = {
    "meta": {"id": "long_one", "title": "Long One", "start_node": "a", "est_time": "25–35 min"},
    "nodes": {
        "a": {"text": "You wait.", "choices": [{"label": "Keep waiting", "next": "b"}]},
        "b": {"text": "It ends.", "is_ending": True, "ending_type": "good"},
    },
}

# No est_time, so the player has to work one out from the word count.
_WITHOUT_ESTIMATE = {
    "meta": {"id": "short_one", "title": "Short One", "start_node": "a"},
    "nodes": _WITH_ESTIMATE["nodes"],
}


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


def _function(source: str, name: str) -> str:
    begin = source.index(f"function {name}(")
    end = "\n}\n"
    return source[begin:source.index(end, begin) + len(end)]


def _header_and_library_time(story: dict) -> dict:
    """Return the time in the reader game header, and the time the library shows."""
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    script = "\n".join([
        "import { createRun, currentView } from './web/engine.js';",
        # A pretend page: just enough for the function to draw into.
        "var app = { innerHTML: '', querySelectorAll: function() { return []; },",
        "  querySelector: function() { return { addEventListener: function() {}, focus: function() {} }; } };",
        "var document = { body: { classList: { add: function() {} } } };",
        "var pendingInput, currentScreen, lastSaved;",
        "var debugMode = false;",
        "function setPageTitle() {}",
        "function renderLibrary() {}",
        "function renderAccessibleEnding() {}",
        _function(app, "escapeHtml"),
        _function(app, "_assembleText"),
        _function(app, "nodeList"),
        _function(app, "estimateTime"),
        _function(app, "storyTitle"),
        _function(app, "renderAccessibleGame"),
        "var story = " + json.dumps(story) + ";",
        "var currentRun = createRun({ path: 'stories/test.json', story: story });",
        "renderAccessibleGame();",
        "var match = /<span class=\"r-time\">(.*?)<\\/span>/.exec(app.innerHTML);",
        # The library screens print estimateTime(story) as it is.
        "console.log(JSON.stringify({ header: match && match[1], library: estimateTime(story) }));",
    ])
    return json.loads(_run(script))


def test_reader_header_shows_the_estimate_the_author_wrote():
    assert _header_and_library_time(_WITH_ESTIMATE)["header"] == "25–35 min"


def test_reader_header_shows_the_same_estimate_as_the_library():
    for story in (_WITH_ESTIMATE, _WITHOUT_ESTIMATE):
        times = _header_and_library_time(story)
        assert times["header"] == times["library"], story["meta"]["id"]


def test_reader_header_has_one_tilde_at_most():
    header = _header_and_library_time(_WITHOUT_ESTIMATE)["header"]
    assert header == "~5 min"
    assert header.count("~") == 1
