"""Tests for the page-level keydown handler in web/app.js, run via Node.js.

Ctrl and Cmd combos (reload, find, zoom) belong to the browser. The game must
not type them into the prompt or block them. AltGr characters must still type.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

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


# app.js needs a real page to load, so it cannot be imported in Node.
# Instead the real handler is cut out of the file and run against a few stand-ins
# for the things it touches. No copy of the logic lives in this test.
_HARNESS = """
import { readFileSync } from 'node:fs';
const src = readFileSync('./web/app.js', 'utf8');
const marker = "document.addEventListener('keydown', ";
const open = src.indexOf(marker + 'function(e) {') + marker.length;
if (open < marker.length) throw new Error('page keydown handler not found in web/app.js');
const handlerSource = src.slice(open, src.indexOf('\\n});', open) + 2);

const scenario = SCENARIO;
var mobileCapture = {};
var currentScreen = scenario.screen;
var pendingInput = '';
var settingsEditRow = null, sectionEditRow = null;
var debugMode = false;
var skipped = false;
function isAccessibleMode() { return false; }
function isTwAnimating() { return scenario.animating; }
function skipTypewriter() { skipped = true; }
function updatePrompt() {}
function renderGame() {}

const handler = eval('(' + handlerSource + ')');
const event = Object.assign({
  key: '', ctrlKey: false, metaKey: false, altKey: false, shiftKey: false,
  modifierStates: [], target: {}, defaultPrevented: false,
  preventDefault() { this.defaultPrevented = true; },
  getModifierState(name) { return this.modifierStates.includes(name); },
}, scenario.event);
handler(event);
console.log(JSON.stringify({ typed: pendingInput, prevented: event.defaultPrevented, skipped, debugMode }));
"""


def _press(event: dict, screen: str = "game", animating: bool = False) -> dict:
    scenario = {"event": event, "screen": screen, "animating": animating}
    return json.loads(_run(_HARNESS.replace("SCENARIO", json.dumps(scenario))))


@pytest.mark.parametrize(
    "event",
    [
        {"key": "r", "ctrlKey": True},   # reload
        {"key": "f", "ctrlKey": True},   # find in page
        {"key": "l", "ctrlKey": True},   # address bar
        {"key": "r", "metaKey": True},   # reload on a Mac
        {"key": "+", "ctrlKey": True},   # zoom in
        {"key": "-", "ctrlKey": True},   # zoom out
    ],
)
def test_browser_shortcuts_are_left_to_the_browser(event: dict) -> None:
    result = _press(event)
    assert result == {"typed": "", "prevented": False, "skipped": False, "debugMode": False}


def test_browser_shortcut_while_text_is_typing_out_is_left_alone() -> None:
    result = _press({"key": "r", "ctrlKey": True}, animating=True)
    assert result == {"typed": "", "prevented": False, "skipped": False, "debugMode": False}


@pytest.mark.parametrize("char", ["@", "{"])
def test_altgr_characters_are_still_typed(char: str) -> None:
    """Windows reports AltGr as Ctrl plus Alt. Those keys are typing, not shortcuts."""
    event = {"key": char, "ctrlKey": True, "altKey": True, "modifierStates": ["AltGraph"]}
    result = _press(event, screen="name-prompt")
    assert result["typed"] == char
    assert result["prevented"] is True


@pytest.mark.parametrize("event", [{"key": "r"}, {"key": "R", "shiftKey": True}])
def test_plain_keys_are_still_typed(event: dict) -> None:
    result = _press(event)
    assert result["typed"] == event["key"]
    assert result["prevented"] is True


def test_plain_minus_still_toggles_debug_in_game() -> None:
    result = _press({"key": "-"})
    assert result["debugMode"] == "author"
    assert result["typed"] == ""
