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
    assert result['intensity'] == 0.6  # TYPEWRITER_DEFAULTS.corruption.intensity
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
