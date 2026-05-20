"""
Unit tests for web/engine.js — run via Node.js subprocess.
Each test mirrors the equivalent Python test in test_engine.py so the two
engines stay behaviourally in sync.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(script: str) -> str:
    """Execute an ES-module snippet via Node stdin and return stdout."""
    result = subprocess.run(
        ["node", "--input-type=module"],
        input=script.encode(),
        capture_output=True,
        cwd=ROOT,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr.decode()
    return result.stdout.decode().strip()


def _ri(text: str, state: dict) -> str:
    """Call resolveInline(text, state) in JS and return the result string."""
    script = f"""
import {{ resolveInline }} from './web/engine.js';
console.log(resolveInline({json.dumps(text)}, {json.dumps(state)}));
"""
    return _run(script)


# ---------------------------------------------------------------------------
# resolveInline — branch selection
# ---------------------------------------------------------------------------

def test_resolve_inline_true_branch() -> None:
    assert _ri("{flag?yes|no}", {"flag": True}) == "yes"


def test_resolve_inline_false_branch() -> None:
    assert _ri("{flag?yes|no}", {"flag": False}) == "no"


def test_resolve_inline_missing_flag_returns_false_branch() -> None:
    assert _ri("{flag?yes|no}", {}) == "no"


def test_resolve_inline_no_false_branch_when_true() -> None:
    assert _ri("{flag?shown}", {"flag": True}) == "shown"


def test_resolve_inline_no_false_branch_collapses_when_false() -> None:
    assert _ri("{flag?shown}", {"flag": False}) == ""


def test_resolve_inline_no_false_branch_collapses_when_missing() -> None:
    assert _ri("{flag?shown}", {}) == ""


def test_resolve_inline_multiple_spans() -> None:
    assert _ri("{a?hello|goodbye}, {b?world|earth}.", {"a": True, "b": False}) == "hello, earth."


# ---------------------------------------------------------------------------
# resolveInline — variable substitution placeholders left intact
# ---------------------------------------------------------------------------

def test_resolve_inline_plain_brace_left_intact() -> None:
    assert _ri("{player_name} arrives.", {"player_name": "Mira"}) == "{player_name} arrives."


# ---------------------------------------------------------------------------
# resolveInline — integer and string truthiness
# ---------------------------------------------------------------------------

def test_resolve_inline_int_truthy() -> None:
    assert _ri("{score?pass|fail}", {"score": 5}) == "pass"


def test_resolve_inline_int_zero_falsy() -> None:
    assert _ri("{score?pass|fail}", {"score": 0}) == "fail"


def test_resolve_inline_string_truthy() -> None:
    assert _ri("{mood?happy|sad}", {"mood": "red"}) == "happy"


def test_resolve_inline_empty_string_falsy() -> None:
    assert _ri("{mood?happy|sad}", {"mood": ""}) == "sad"


# ---------------------------------------------------------------------------
# currentView — inline resolution applied to all four text fields
# ---------------------------------------------------------------------------

def test_current_view_resolves_node_text() -> None:
    script = """
import { createRun, currentView } from './web/engine.js';
const story = {
  meta: { id: 's', start_node: 'n', auto_visited_flags: false },
  nodes: { n: { text: '{f?hello|bye}', choices: [] } }
};
const run = createRun({ story });
run.state = { f: true };
const view = currentView(run);
console.log(view.node.text);
"""
    assert _run(script) == "hello"


def test_current_view_resolves_inset_text() -> None:
    script = """
import { createRun, currentView } from './web/engine.js';
const story = {
  meta: { id: 's', start_node: 'n', auto_visited_flags: false },
  nodes: {
    n: {
      text: 'prose',
      choices: [],
      insets: [{ text: '{f?staff|guest}', position: 'before' }]
    }
  }
};
const run = createRun({ story });
run.state = { f: true };
const view = currentView(run);
console.log(view.insets.before[0].text);
"""
    assert _run(script) == "staff"


def test_current_view_resolves_overlay_text() -> None:
    script = """
import { createRun, currentView } from './web/engine.js';
const story = {
  meta: { id: 's', start_node: 'n', auto_visited_flags: false },
  nodes: {
    n: {
      text: 'prose',
      choices: [],
      overlays: [{ text: '{f?whisper|silence}', position: 'after' }]
    }
  }
};
const run = createRun({ story });
run.state = { f: false };
const view = currentView(run);
console.log(view.overlays.after[0].text);
"""
    assert _run(script) == "silence"


def test_current_view_does_not_mutate_story_node() -> None:
    script = """
import { createRun, currentView } from './web/engine.js';
const story = {
  meta: { id: 's', start_node: 'n', auto_visited_flags: false },
  nodes: { n: { text: '{f?yes|no}', choices: [] } }
};
const run = createRun({ story });
run.state = { f: true };
currentView(run);
console.log(story.nodes.n.text);
"""
    assert _run(script) == "{f?yes|no}"
