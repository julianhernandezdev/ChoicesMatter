"""Tests for clearAllProgress in web/storage.js, run via Node.js.

"C to clear saves" in the browser should clear what the terminal game clears
(saves and ending galleries) and leave the player's settings alone.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SETTINGS_KEY = "choices-matter:typewriter-settings"


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


# Node has no browser storage, so the tests bring a small stand-in.
# Stored items are plain properties, which is what Object.keys() lists in a real browser too.
_FAKE_STORAGE = """
class FakeStorage {
  getItem(key) { return Object.prototype.hasOwnProperty.call(this, key) ? this[key] : null; }
  setItem(key, value) { this[key] = String(value); }
  removeItem(key) { delete this[key]; }
}
Object.defineProperty(globalThis, 'localStorage', { value: new FakeStorage(), configurable: true, writable: true });
"""


def _keys_after_clear(stored: dict[str, str]) -> list[str]:
    script = f"""
{_FAKE_STORAGE}
const {{ clearAllProgress }} = await import('./web/storage.js');
for (const [key, value] of Object.entries({json.dumps(stored)})) localStorage.setItem(key, value);
clearAllProgress();
console.log(JSON.stringify(Object.keys(localStorage).sort()));
"""
    return json.loads(_run(script))


def test_clear_all_progress_keeps_settings() -> None:
    remaining = _keys_after_clear({
        SETTINGS_KEY: '{"page_size": 8}',
        "choices-matter:save:the_last_train": "{}",
        "choices-matter:gallery:the_last_train": "{}",
    })
    assert remaining == [SETTINGS_KEY]


def test_clear_all_progress_removes_saves_and_galleries_of_every_story() -> None:
    remaining = _keys_after_clear({
        "choices-matter:save:the_last_train": "{}",
        "choices-matter:gallery:the_last_train": "{}",
        "choices-matter:save:awaiting_response": "{}",
        "choices-matter:gallery:awaiting_response": "{}",
        "some-other-site-key": "keep me",
    })
    assert remaining == ["some-other-site-key"]


def test_saved_settings_still_load_after_clearing_saves() -> None:
    """Written and read back through the real settings code, with a real save and ending in between."""
    script = f"""
{_FAKE_STORAGE}
const {{ loadTypewriterSettings, saveTypewriterSettings }} = await import('./web/typewriter.js');
const {{ writeSave, recordEnding, loadSave, loadGallery, clearAllProgress }} = await import('./web/storage.js');
const settings = loadTypewriterSettings();
settings.page_size = 8;
settings.player_name = 'Albert';
saveTypewriterSettings(settings);
const story = {{ meta: {{ id: 'the_last_train' }} }};
writeSave(story, {{ nodeId: 'start', history: [], state: {{}} }});
recordEnding(story, 'ending_walk_away');
clearAllProgress();
const after = loadTypewriterSettings();
console.log(JSON.stringify({{
  page_size: after.page_size,
  player_name: after.player_name,
  save: loadSave('the_last_train'),
  endings: loadGallery('the_last_train').endings_found,
}}));
"""
    assert json.loads(_run(script)) == {
        "page_size": 8,
        "player_name": "Albert",
        "save": None,
        "endings": [],
    }
