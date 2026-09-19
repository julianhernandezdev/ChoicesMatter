"""
Unit tests for web/engine.js — run via Node.js subprocess.
Each test mirrors the equivalent Python test in test_engine.py so the two
engines stay behaviourally in sync.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

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
    assert result[0]["mode"] is None


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


def test_js_resolve_corruption_resolve_style_decay() -> None:
    result = json.loads(_rc("{corrupt:0.8:consistent:decay}text{/corrupt}", None))
    assert result[0]["resolve_style"] == "decay"


def test_js_resolve_corruption_resolve_style_cascade() -> None:
    result = json.loads(_rc("{corrupt:0.8:random:cascade}text{/corrupt}", None))
    assert result[0]["resolve_style"] == "cascade"


def test_js_resolve_corruption_resolve_style_omitted_is_null() -> None:
    result = json.loads(_rc("{corrupt}text{/corrupt}", None))
    assert result[0]["resolve_style"] is None


def test_js_resolve_corruption_resolve_style_alone_skips_intensity_and_mode() -> None:
    result = json.loads(_rc("{corrupt:decay}text{/corrupt}", None))
    assert result[0]["resolve_style"] == "decay"
    assert result[0]["intensity"] is None
    assert result[0]["mode"] is None


def test_js_resolve_corruption_resolve_style_inherits_from_node() -> None:
    result = json.loads(_rc("{corrupt}text{/corrupt}", {"resolve_style": "cascade"}))
    assert result[0]["resolve_style"] == "cascade"


def test_js_resolve_corruption_intensity_is_null_when_unspecified() -> None:
    result = json.loads(_rc("{corrupt}text{/corrupt}", None))
    assert result[0]["intensity"] is None


# ---------------------------------------------------------------------------
# Settings clamping (parity with src/config.py)
# ---------------------------------------------------------------------------

def _js_json(script_body: str):
    """Run an ES-module snippet that console.logs JSON and return the parsed value."""
    return json.loads(_run(script_body))


def _py_key_to_js(py_key: str) -> str:
    if py_key == "picker.page_size":
        return "page_size"
    if py_key.startswith("typewriter.punctuation_pauses."):
        return "pauses." + py_key[len("typewriter.punctuation_pauses."):]
    return py_key


def test_js_setting_ranges_match_python_registry() -> None:
    from src.config import SETTING_RANGES as PY_RANGES
    js = _js_json("""
import { SETTING_RANGES } from './web/engine.js';
console.log(JSON.stringify(SETTING_RANGES));
""")
    expected = {_py_key_to_js(k): list(v) for k, v in PY_RANGES.items()}
    assert js == expected


def test_js_defaults_lie_within_their_ranges() -> None:
    offenders = _js_json("""
import { SETTING_RANGES } from './web/engine.js';
import { TYPEWRITER_DEFAULTS as D } from './web/typewriter.js';
const bad = [];
for (const [key, [lo, hi]] of Object.entries(SETTING_RANGES)) {
  let v;
  if (key === 'page_size') v = D.page_size;
  else if (key.startsWith('pauses.')) v = D.pauses[key.slice('pauses.'.length)];
  else if (key.startsWith('corruption.')) v = D.corruption[key.slice('corruption.'.length)];
  if (v === null || v === undefined) continue;
  if (v < lo || v > hi) bad.push(key + '=' + v);
}
console.log(JSON.stringify(bad));
""")
    assert offenders == []


_TIMING_CASES = [
    {"scramble_frames": 85, "scramble_delay_ms": 40, "resolve_frames": None, "resolve_delay_ms": None, "cascade_stagger_ms": None},
    {"scramble_frames": 0, "scramble_delay_ms": -3, "resolve_frames": None, "resolve_delay_ms": None, "cascade_stagger_ms": None},
    {"scramble_frames": -5, "scramble_delay_ms": 5000, "resolve_frames": None, "resolve_delay_ms": None, "cascade_stagger_ms": None},
    {"scramble_frames": 9999, "scramble_delay_ms": 40, "resolve_frames": 300, "resolve_delay_ms": 5000, "cascade_stagger_ms": -1},
    {"scramble_frames": 10, "scramble_delay_ms": 20, "resolve_frames": 7, "resolve_delay_ms": 0, "cascade_stagger_ms": 15},
]


@pytest.mark.parametrize("cfg", _TIMING_CASES)
def test_js_corruption_timing_matches_python(cfg: dict) -> None:
    from src.config import corruption_timing
    js = _js_json(f"""
import {{ corruptionTiming }} from './web/engine.js';
console.log(JSON.stringify(corruptionTiming({json.dumps(cfg)})));
""")
    py = corruption_timing(cfg)
    assert js == {
        "scrambleFrames": py["scramble_frames"],
        "scrambleDelay": py["scramble_delay_ms"],
        "resolveFrames": py["resolve_frames"],
        "resolveDelay": py["resolve_delay_ms"],
        "cascadeStagger": py["cascade_stagger_ms"],
    }


def test_js_clamp_setting() -> None:
    js = _js_json("""
import { clampSetting } from './web/engine.js';
console.log(JSON.stringify([
  clampSetting('corruption.scramble_frames', 0),
  clampSetting('corruption.scramble_frames', 85),
  clampSetting('corruption.scramble_frames', 9999),
  clampSetting('pauses..', -1),
  clampSetting('page_size', NaN),
  clampSetting('unknown_key', 12345),
]));
""")
    assert js == [1, 85, 200, 0, 1, 9999]


def test_js_corruption_count_guards_non_positive_intensity() -> None:
    js = _js_json("""
import { corruptionCount } from './web/engine.js';
console.log(JSON.stringify([
  corruptionCount(6, -0.5),
  corruptionCount(6, 0),
  corruptionCount(6, NaN),
  corruptionCount(6, 0.5),
  corruptionCount(6, 1),
  corruptionCount(6, 1.5),
  corruptionCount(0, 0.5),
]));
""")
    assert js == [0, 0, 0, 3, 6, 6, 0]


def test_js_commit_setting_value_number_rows_clamp_and_parse_strictly() -> None:
    js = _js_json("""
import { commitSettingValue } from './web/engine.js';
const frames = { key: 'corruption.scramble_frames', type: 'number' };
const page = { key: 'page_size', type: 'number' };
console.log(JSON.stringify([
  commitSettingValue(frames, '12'),
  commitSettingValue(frames, ' 85 '),
  commitSettingValue(frames, '0'),
  commitSettingValue(frames, '9999'),
  commitSettingValue(frames, '12abc'),
  commitSettingValue(frames, ''),
  commitSettingValue(frames, '-3'),
  commitSettingValue(frames, '5.5'),
  commitSettingValue(page, '99'),
]));
""")
    assert js == [
        {"ok": True, "value": 12},
        {"ok": True, "value": 85},
        {"ok": True, "value": 1},
        {"ok": True, "value": 200},
        {"ok": False},
        {"ok": False},
        {"ok": False},
        {"ok": False},
        {"ok": True, "value": 50},
    ]


def test_js_commit_setting_value_float_rows_reject_out_of_range() -> None:
    js = _js_json("""
import { commitSettingValue } from './web/engine.js';
const row = { key: 'corruption.intensity', type: 'float' };
console.log(JSON.stringify([
  commitSettingValue(row, '0.6'),
  commitSettingValue(row, '0'),
  commitSettingValue(row, '1'),
  commitSettingValue(row, '1.5'),
  commitSettingValue(row, '-0.1'),
  commitSettingValue(row, 'abc'),
]));
""")
    assert js == [
        {"ok": True, "value": 0.6},
        {"ok": True, "value": 0},
        {"ok": True, "value": 1},
        {"ok": False},
        {"ok": False},
        {"ok": False},
    ]


def test_js_sanitize_corruption_settings() -> None:
    js = _js_json("""
import { sanitizeCorruptionSettings } from './web/engine.js';
const defaults = {
  enabled: true, charset: 'blocks', intensity: 0.6, intensity_multiplier: 1.0, mode: 'consistent',
  animate: true, scramble_frames: 85, scramble_delay_ms: 40,
  resolve_frames: null, resolve_delay_ms: null, cascade_stagger_ms: null,
};
const stored = {
  intensity_multiplier: -1, scramble_frames: 0, scramble_delay_ms: 'fast',
  resolve_frames: 9999.9, resolve_delay_ms: null, cascade_stagger_ms: 'x',
  custom_chars: 'ab', charset: 'custom',
};
console.log(JSON.stringify(sanitizeCorruptionSettings(stored, defaults)));
""")
    assert js["intensity_multiplier"] == 0            # clamped up to 0, stays a float key
    assert js["scramble_frames"] == 1                 # clamped, integer
    assert js["scramble_delay_ms"] == 40              # wrong type -> default
    assert js["resolve_frames"] == 200                # clamped and truncated
    assert js["resolve_delay_ms"] is None             # nullable "Auto" preserved
    assert js["cascade_stagger_ms"] is None           # wrong type on nullable -> default (null)
    assert js["custom_chars"] == "ab"                 # unknown keys preserved
    assert js["charset"] == "custom"
    assert js["intensity"] == 0.6                     # untouched default


def test_js_sanitize_corruption_settings_handles_missing_or_invalid_stored() -> None:
    js = _js_json("""
import { sanitizeCorruptionSettings } from './web/engine.js';
const defaults = { scramble_frames: 85, resolve_frames: null };
console.log(JSON.stringify([
  sanitizeCorruptionSettings(undefined, defaults),
  sanitizeCorruptionSettings('nope', defaults),
  sanitizeCorruptionSettings({ scramble_frames: null }, defaults),
]));
""")
    assert js == [
        {"scramble_frames": 85, "resolve_frames": None},
        {"scramble_frames": 85, "resolve_frames": None},
        {"scramble_frames": 85, "resolve_frames": None},
    ]


def test_js_sanitize_pauses() -> None:
    js = _js_json("""
import { sanitizePauses } from './web/engine.js';
const defaults = { '.': 550, '!': 250 };
console.log(JSON.stringify([
  sanitizePauses({ '.': 99999, '!': -4, '?': 100 }, defaults),
  sanitizePauses({ '.': 'slow' }, defaults),
  sanitizePauses(null, defaults),
]));
""")
    assert js == [
        {".": 2000, "!": 0, "?": 100},
        {".": 550, "!": 250},
        {".": 550, "!": 250},
    ]
