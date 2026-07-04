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
console.log(JSON.stringify(view.node.text));
"""
    assert json.loads(_run(script)) == ["hello"]


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
console.log(JSON.stringify(view.insets.before[0].text));
"""
    assert json.loads(_run(script)) == ["staff"]


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
console.log(JSON.stringify(view.overlays.after[0].text));
"""
    assert json.loads(_run(script)) == ["silence"]


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


# ---------------------------------------------------------------------------
# substituteVars — helper
# ---------------------------------------------------------------------------

def _sv(text: str, state: dict) -> str:
    """Call substituteVars(text, state) in JS and return the result string."""
    script = f"""
import {{ substituteVars }} from './web/engine.js';
console.log(substituteVars({json.dumps(text)}, {json.dumps(state)}));
"""
    return _run(script)


# ---------------------------------------------------------------------------
# substituteVars — unit tests
# ---------------------------------------------------------------------------

def test_substitute_vars_js_replaces_key() -> None:
    assert _sv("Hello, {name}!", {"name": "Mira"}) == "Hello, Mira!"


def test_substitute_vars_js_missing_key_left_intact() -> None:
    assert _sv("Hello, {name}!", {}) == "Hello, {name}!"


def test_substitute_vars_js_int_coerced_to_str() -> None:
    assert _sv("Score: {score}", {"score": 42}) == "Score: 42"


def test_substitute_vars_js_bool_coerced_to_str() -> None:
    # JS true → "true" (lowercase), consistent with String(true)
    assert _sv("Done: {done}", {"done": True}) == "Done: true"


def test_substitute_vars_js_multiple_keys() -> None:
    assert _sv("{a} and {b}", {"a": "one", "b": "two"}) == "one and two"


def test_substitute_vars_js_does_not_touch_conditional_syntax() -> None:
    assert _sv("{flag?yes|no}", {"flag": "yes"}) == "{flag?yes|no}"


def test_substitute_vars_js_leaves_pause_token_intact_when_not_in_state() -> None:
    assert _sv("wait.{pause}go.", {}) == "wait.{pause}go."


def test_substitute_vars_js_no_patterns_unchanged() -> None:
    assert _sv("Plain text.", {"name": "Mira"}) == "Plain text."


# ---------------------------------------------------------------------------
# substituteVars — currentView integration tests
# ---------------------------------------------------------------------------

def _view(story_json: str, state: dict) -> dict:
    """Call currentView(run) in JS and return the parsed result."""
    script = f"""
import {{ createRun, currentView }} from './web/engine.js';
const entry = {{ story: {story_json} }};
const run = createRun(entry);
run.state = {json.dumps(state)};
console.log(JSON.stringify(currentView(run)));
"""
    return json.loads(_run(script))


def test_substitute_vars_js_in_node_text() -> None:
    story = json.dumps({
        "meta": {"id": "t", "title": "T", "version": "1", "author": "T", "start_node": "start"},
        "nodes": {
            "start": {
                "text": "Hello, {player_name}!",
                "choices": [{"label": "Go", "next": "start"}],
            }
        },
    })
    view = _view(story, {"player_name": "Mira"})
    assert view["node"]["text"] == ["Hello, Mira!"]


def test_substitute_vars_js_in_overlay_text() -> None:
    story = json.dumps({
        "meta": {"id": "t", "title": "T", "version": "1", "author": "T", "start_node": "start"},
        "nodes": {
            "start": {
                "text": "A room.",
                "choices": [{"label": "Go", "next": "start"}],
                "overlays": [{"text": "The air feels {mood}.", "position": "after"}],
            }
        },
    })
    view = _view(story, {"mood": "tense"})
    assert view["overlays"]["after"][0]["text"] == ["The air feels tense."]


def test_substitute_vars_js_in_inset_text() -> None:
    story = json.dumps({
        "meta": {"id": "t", "title": "T", "version": "1", "author": "T", "start_node": "start"},
        "nodes": {
            "start": {
                "text": "A door.",
                "choices": [{"label": "Go", "next": "start"}],
                "insets": [{"text": "Rank: {rank}", "position": "before"}],
            }
        },
    })
    view = _view(story, {"rank": "Captain"})
    assert view["insets"]["before"][0]["text"] == ["Rank: Captain"]


def test_substitute_vars_js_before_inline_resolution() -> None:
    # Substitution runs first; then conditional resolves using substituted text
    story = json.dumps({
        "meta": {"id": "t", "title": "T", "version": "1", "author": "T", "start_node": "start"},
        "nodes": {
            "start": {
                "text": "{known?Hello, {player_name}!|Hello, stranger!}",
                "choices": [{"label": "Go", "next": "start"}],
            }
        },
    })
    view = _view(story, {"known": True, "player_name": "Mira"})
    assert view["node"]["text"] == ["Hello, Mira!"]


# ---------------------------------------------------------------------------
# createRun — initialState parameter
# ---------------------------------------------------------------------------

def _create_run_state(story_json: dict, saved=None, initial_state: dict | None = None) -> dict:
    """Call createRun in JS and return the resulting run.state as a Python dict."""
    initial_state_json = json.dumps(initial_state if initial_state is not None else {})
    script = f"""
import {{ createRun }} from './web/engine.js';
const entry = {{ story: {json.dumps(story_json)} }};
const saved = {json.dumps(saved)};
const initialState = {initial_state_json};
const run = createRun(entry, saved, initialState);
console.log(JSON.stringify(run.state));
"""
    return json.loads(_run(script))


_MINIMAL_STORY = {
    "meta": {"id": "t", "title": "T", "version": "1", "author": "A", "start_node": "s"},
    "nodes": {"s": {"text": "x", "choices": []}},
}


def test_create_run_initial_state_seeds_new_game() -> None:
    state = _create_run_state(_MINIMAL_STORY, None, {"player_name": "Felix"})
    assert state["player_name"] == "Felix"


def test_create_run_saved_state_overrides_initial() -> None:
    saved = {"current_node": "s", "history": [], "state": {"player_name": "Zara"}}
    state = _create_run_state(_MINIMAL_STORY, saved, {"player_name": "Felix"})
    assert state["player_name"] == "Zara"


def test_create_run_no_initial_state_backwards_compat() -> None:
    state = _create_run_state(_MINIMAL_STORY, None, {})
    assert "player_name" not in state


def test_load_typewriter_settings_player_name_default() -> None:
    """loadTypewriterSettings() returns player_name: 'Felix' when no localStorage is set."""
    script = """
import { loadTypewriterSettings } from './web/typewriter.js';
// Simulate empty localStorage (Node has no localStorage — function catches and returns defaults)
console.log(loadTypewriterSettings().player_name);
"""
    assert _run(script) == "Felix"


# ---------------------------------------------------------------------------
# resolveCorruption — unit tests
# ---------------------------------------------------------------------------

def _rc(text: str, node_corruption) -> str:
    """Call resolveCorruption(text, nodeCorruption) in JS and JSON.stringify the result."""
    script = f"""
import {{ resolveCorruption }} from './web/engine.js';
const result = resolveCorruption({json.dumps(text)}, {json.dumps(node_corruption)});
console.log(JSON.stringify(result));
"""
    return _run(script)


def test_js_resolve_corruption_no_spans() -> None:
    result = json.loads(_rc("plain text", None))
    assert result == ["plain text"]


def test_js_resolve_corruption_span_object() -> None:
    result = json.loads(_rc("{corrupt}broken{/corrupt}", None))
    assert len(result) == 1
    assert result[0]["text"] == "broken"
    assert result[0]["mode"] == "consistent"


def test_js_resolve_corruption_intensity_override() -> None:
    result = json.loads(_rc("{corrupt:0.7}text{/corrupt}", None))
    assert abs(result[0]["intensity"] - 0.7) < 0.001


def test_js_resolve_corruption_mode_override() -> None:
    result = json.loads(_rc("{corrupt:random}text{/corrupt}", None))
    assert result[0]["mode"] == "random"


def test_js_resolve_corruption_node_level_float() -> None:
    result = json.loads(_rc("{corrupt}text{/corrupt}", 0.4))
    assert abs(result[0]["intensity"] - 0.4) < 0.001


def test_js_resolve_corruption_mixed_segments() -> None:
    result = json.loads(_rc("before {corrupt}bad{/corrupt} after", None))
    assert len(result) == 3
    assert result[0] == "before "
    assert result[1]["text"] == "bad"
    assert result[2] == " after"


def test_js_resolve_corruption_seed_matches_python() -> None:
    """Seed formula must produce identical values in Python and JS."""
    from src.corruption import _text_seed
    py_seed = _text_seed("glitch", 0)
    script = f"""
import {{ resolveCorruption }} from './web/engine.js';
const result = resolveCorruption('{{corrupt}}glitch{{/corrupt}}', null);
console.log(result[0].seed);
"""
    js_seed = int(_run(script))
    assert py_seed == js_seed


def test_js_current_view_chains_corruption() -> None:
    story = {
        "meta": {"start_node": "start"},
        "nodes": {
            "start": {
                "text": "Hello {corrupt}world{/corrupt}.",
                "choices": [{"label": "Go", "next": "end", "requires": {}, "sets": {}}],
                "overlays": [], "insets": [],
            },
            "end": {
                "text": "Done.", "choices": [],
                "is_ending": True, "overlays": [], "insets": [],
            },
        },
    }
    script = f"""
import {{ createRun, currentView }} from './web/engine.js';
const entry = {{ story: {json.dumps(story)} }};
const run = createRun(entry);
const view = currentView(run);
console.log(JSON.stringify(view.node.text));
"""
    result = json.loads(_run(script))
    # result is TextSegments: ["Hello ", {{text:"world",...}}, "."]
    assert isinstance(result, list)
    assert result[0] == "Hello "
    assert result[1]["text"] == "world"
    assert result[2] == "."
