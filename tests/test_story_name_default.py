"""A story's own default name must be used when the player has not picked a name.

"Felix" is the name the settings hand out when nobody chose one. It used to beat every
story's default, so "Marlowe", "Officer" and friends never showed up. Both players are
covered here: the terminal one (main.py) and the browser one (web/engine.js, web/app.js).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from main import _launch_story, _prompt_name_state, _resolve_player_name
from src.config import load_settings
from src.gallery import GalleryManager
from src.save import SaveManager

ROOT = Path(__file__).resolve().parents[1]


def _name_story(name_default: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(name_prompt="What is your name?", name_default=name_default)


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


def _web_name(entered: str, name_default: str | None, saved_name: str) -> object:
    """Call resolvePlayerName in web/engine.js with 'Felix' as the built-in name."""
    script = f"""
import {{ resolvePlayerName }} from './web/engine.js';
console.log(JSON.stringify(resolvePlayerName(
  {json.dumps(entered)}, {json.dumps(name_default)}, {json.dumps(saved_name)}, 'Felix')));
"""
    return json.loads(_run(script))


# ---------------------------------------------------------------------------
# Terminal player: _resolve_player_name
# ---------------------------------------------------------------------------

def test_blank_entry_uses_story_default_when_only_the_built_in_name_exists() -> None:
    assert _resolve_player_name("", "Officer", "Felix") == "Officer"


def test_blank_entry_keeps_a_name_the_player_saved() -> None:
    assert _resolve_player_name("", "Officer", "Zara") == "Zara"


def test_blank_entry_falls_back_to_built_in_name_when_story_has_no_default() -> None:
    assert _resolve_player_name("", "", "Felix") == "Felix"


def test_typing_the_built_in_name_still_wins_over_the_story_default() -> None:
    assert _resolve_player_name("Felix", "Officer", "Felix") == "Felix"


# ---------------------------------------------------------------------------
# Terminal player: the prompt itself
# ---------------------------------------------------------------------------

def test_prompt_blank_entry_gives_story_default_and_says_so_in_the_hint() -> None:
    display = MagicMock()
    display.prompt_protagonist_name.return_value = ""
    assert _prompt_name_state(_name_story("Officer"), display, "Felix") == {"player_name": "Officer"}
    # The hint in brackets is a promise about what Enter does, so it has to name the same name.
    display.prompt_protagonist_name.assert_called_once_with("What is your name?", prefill="Officer")


def test_prompt_hint_shows_the_saved_name_when_the_player_has_one() -> None:
    display = MagicMock()
    display.prompt_protagonist_name.return_value = ""
    assert _prompt_name_state(_name_story("Officer"), display, "Zara") == {"player_name": "Zara"}
    display.prompt_protagonist_name.assert_called_once_with("What is your name?", prefill="Zara")


def test_launch_with_no_settings_file_uses_the_story_default(
    tmp_path: Path, saves_dir: Path, sample_story_dict: dict
) -> None:
    sample_story_dict["meta"]["name_prompt"] = "Who are you?"
    sample_story_dict["meta"]["name_default"] = "Marlowe"
    path = tmp_path / "named.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    display = MagicMock()
    display.prompt_protagonist_name.return_value = ""  # the player just presses Enter
    no_settings = load_settings(tmp_path / "no_settings.json")  # what a fresh install gets

    with patch("main.Engine") as engine_cls, patch("main.load_settings", return_value=no_settings):
        engine_cls.return_value.run.return_value = None
        _launch_story(path, {}, SaveManager(saves_dir), GalleryManager(saves_dir), display)

    assert engine_cls.call_args.kwargs["fresh_run_state"]() == {"player_name": "Marlowe"}


# ---------------------------------------------------------------------------
# Browser player: same rule, run through Node
# ---------------------------------------------------------------------------

def test_web_blank_entry_uses_story_default_when_only_the_built_in_name_exists() -> None:
    assert _web_name("", "Officer", "Felix") == "Officer"


def test_web_blank_entry_keeps_a_name_the_player_saved() -> None:
    assert _web_name("", "Officer", "Zara") == "Zara"


def test_web_blank_entry_falls_back_to_built_in_name_when_story_has_no_default() -> None:
    assert _web_name("", None, "Felix") == "Felix"


def test_web_typed_name_wins_and_nothing_at_all_gives_null() -> None:
    assert _web_name("Felix", "Officer", "Felix") == "Felix"
    assert _web_name("", None, "") is None


def test_web_app_gives_story_default_with_empty_browser_storage() -> None:
    """app.js needs a real page to load, so lift its _resolvePlayerName out and run that text
    against the real settings loader. Node has no localStorage, which is a fresh browser."""
    script = """
import { readFileSync } from 'node:fs';
import * as engine from './web/engine.js';
import { loadTypewriterSettings, TYPEWRITER_DEFAULTS } from './web/typewriter.js';
const src = readFileSync('./web/app.js', 'utf8');
const body = src.match(/function _resolvePlayerName\\(entered, meta\\) \\{[\\s\\S]*?\\r?\\n\\}/)[0];
const resolve = new Function(
  'loadTypewriterSettings', 'TYPEWRITER_DEFAULTS', 'resolvePlayerName',
  body + '\\nreturn _resolvePlayerName;'
)(loadTypewriterSettings, TYPEWRITER_DEFAULTS, engine.resolvePlayerName);
console.log(resolve('', { name_prompt: 'Who are you?', name_default: 'Marlowe' }));
"""
    assert _run(script) == "Marlowe"
