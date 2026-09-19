import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from main import (
    _build_entries,
    _launch_story,
    _load_story_info,
    _parse_args,
    _prompt_name_state,
    _resolve_player_name,
)
from src.gallery import GalleryManager
from src.save import SaveManager, SaveState


def test_load_story_info_valid(valid_story_path: Path) -> None:
    title, sid, node_count, ending_count, est_time, has_warnings, author, version = _load_story_info(valid_story_path)
    assert title == "Test Story"
    assert sid == "test_story"
    assert node_count == 3
    assert ending_count == 1
    assert "min" in est_time
    assert has_warnings is False
    assert author == "Tester"
    assert version == "1.0"


def test_load_story_info_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("not json", encoding="utf-8")
    title, sid, node_count, ending_count, est_time, has_warnings, author, version = _load_story_info(path)
    assert title == "broken"
    assert sid == ""
    assert node_count == 0
    assert has_warnings is False
    assert author == ""
    assert version == ""


def test_load_story_info_with_warnings(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["meta"]["warnings"] = ["Violence"]
    path = tmp_path / "warned.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    *_, has_warnings, _author, _version = _load_story_info(path)
    assert has_warnings is True


def test_build_entries_valid_story(valid_story_path: Path, saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    gm = GalleryManager(saves_dir)
    entries = _build_entries([valid_story_path], {}, sm, gm)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["index"] == 1
    assert entry["label"] == "Test Story"
    assert entry["error"] is False
    assert entry["has_save"] is False
    assert entry["endings_found"] == 0
    assert entry["node_count"] == 3
    assert entry["author"] == "Tester"
    assert entry["version"] == "1.0"


def test_build_entries_error_story(tmp_path: Path, saves_dir: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("bad json", encoding="utf-8")
    errors = {path: "parse error"}
    sm = SaveManager(saves_dir)
    gm = GalleryManager(saves_dir)
    entries = _build_entries([path], errors, sm, gm)
    assert entries[0]["error"] is True
    assert entries[0]["label"] == "bad"


def test_build_entries_with_active_save(valid_story_path: Path, saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    sm.write(SaveState(story_id="test_story", current_node="start"))
    gm = GalleryManager(saves_dir)
    entries = _build_entries([valid_story_path], {}, sm, gm)
    assert entries[0]["has_save"] is True


def test_build_entries_with_gallery_count(valid_story_path: Path, saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    gm = GalleryManager(saves_dir)
    gm.record_ending("test_story", "ending")
    entries = _build_entries([valid_story_path], {}, sm, gm)
    assert entries[0]["endings_found"] == 1


def test_build_entries_multiple_paths(valid_story_path: Path, saves_dir: Path,
                                      tmp_path: Path, sample_story_dict: dict) -> None:
    second_path = tmp_path / "second.json"
    sample_story_dict["meta"]["id"] = "second_story"
    sample_story_dict["meta"]["title"] = "Second Story"
    second_path.write_text(json.dumps(sample_story_dict), encoding="utf-8")

    sm = SaveManager(saves_dir)
    gm = GalleryManager(saves_dir)
    entries = _build_entries([valid_story_path, second_path], {}, sm, gm)
    assert len(entries) == 2
    assert entries[0]["index"] == 1
    assert entries[1]["index"] == 2


def test_parse_args_defaults():
    with patch.object(sys, "argv", ["main.py"]):
        assert _parse_args() == {"enabled": False, "all": False}


def test_parse_args_debug_flag():
    with patch.object(sys, "argv", ["main.py", "--debug"]):
        assert _parse_args() == {"enabled": True, "all": False}


def test_parse_args_debug_and_all():
    with patch.object(sys, "argv", ["main.py", "--debug", "--all"]):
        assert _parse_args() == {"enabled": True, "all": True}


def test_parse_args_all_without_debug_is_ignored():
    with patch.object(sys, "argv", ["main.py", "--all"]):
        assert _parse_args() == {"enabled": False, "all": False}


# ---------------------------------------------------------------------------
# _resolve_player_name
# ---------------------------------------------------------------------------

def test_resolve_player_name_entered_wins():
    assert _resolve_player_name("Casey", "Officer", "Felix") == "Casey"


def test_resolve_player_name_settings_wins_over_story_default():
    assert _resolve_player_name("", "Officer", "Felix") == "Felix"


def test_resolve_player_name_falls_back_to_story_default_when_no_settings_name():
    assert _resolve_player_name("", "Officer", "") == "Officer"


def test_resolve_player_name_none_when_nothing_available():
    assert _resolve_player_name("", "", "") is None


# ---------------------------------------------------------------------------
# _prompt_name_state
# ---------------------------------------------------------------------------

def _name_story(name_default: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(name_prompt="What is your name?", name_default=name_default)


def test_prompt_name_state_returns_typed_name():
    display = MagicMock()
    display.prompt_protagonist_name.return_value = "Casey"
    assert _prompt_name_state(_name_story(), display, "Felix") == {"player_name": "Casey"}
    display.prompt_protagonist_name.assert_called_once_with("What is your name?", prefill="Felix")


def test_prompt_name_state_empty_input_uses_settings_name():
    display = MagicMock()
    display.prompt_protagonist_name.return_value = ""
    assert _prompt_name_state(_name_story("Officer"), display, "Felix") == {"player_name": "Felix"}


def test_prompt_name_state_empty_input_falls_back_to_story_default():
    display = MagicMock()
    display.prompt_protagonist_name.return_value = ""
    assert _prompt_name_state(_name_story("Officer"), display, "") == {"player_name": "Officer"}


def test_prompt_name_state_q_returns_none_without_error_screen():
    display = MagicMock()
    display.prompt_protagonist_name.return_value = None
    assert _prompt_name_state(_name_story(), display, "Felix") is None
    display.show_name_required.assert_not_called()


def test_prompt_name_state_unresolvable_shows_error_and_returns_none():
    display = MagicMock()
    display.prompt_protagonist_name.return_value = ""
    assert _prompt_name_state(_name_story(), display, "") is None
    display.show_name_required.assert_called_once_with()


# ---------------------------------------------------------------------------
# _launch_story wiring
# ---------------------------------------------------------------------------

def test_launch_story_passes_provider_when_story_has_name_prompt(
    tmp_path: Path, saves_dir: Path, sample_story_dict: dict
) -> None:
    sample_story_dict["meta"]["name_prompt"] = "Who are you?"
    path = tmp_path / "named.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    display = MagicMock()
    display.prompt_protagonist_name.return_value = "Casey"

    with patch("main.Engine") as engine_cls, patch("main.load_settings", return_value={"player_name": "Felix"}):
        _launch_story(path, {}, SaveManager(saves_dir), GalleryManager(saves_dir), display)

    kwargs = engine_cls.call_args.kwargs
    assert kwargs["initial_state"] == {"player_name": "Felix"}
    display.prompt_protagonist_name.assert_not_called()  # no up-front prompt any more
    assert kwargs["fresh_run_state"]() == {"player_name": "Casey"}
    display.prompt_protagonist_name.assert_called_once_with("Who are you?", prefill="Felix")


def test_launch_story_passes_no_provider_without_name_prompt(
    valid_story_path: Path, saves_dir: Path
) -> None:
    display = MagicMock()

    with patch("main.Engine") as engine_cls, patch("main.load_settings", return_value={"player_name": "Felix"}):
        _launch_story(valid_story_path, {}, SaveManager(saves_dir), GalleryManager(saves_dir), display)

    kwargs = engine_cls.call_args.kwargs
    assert kwargs["fresh_run_state"] is None
    assert kwargs["initial_state"] == {"player_name": "Felix"}
    display.prompt_protagonist_name.assert_not_called()
