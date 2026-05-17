import json
from pathlib import Path

import pytest

from main import _build_entries, _load_story_info
from src.gallery import GalleryManager
from src.save import SaveManager, SaveState


def test_load_story_info_valid(valid_story_path: Path) -> None:
    title, sid, node_count, ending_count, est_time, has_warnings = _load_story_info(valid_story_path)
    assert title == "Test Story"
    assert sid == "test_story"
    assert node_count == 3
    assert ending_count == 1
    assert "min" in est_time
    assert has_warnings is False


def test_load_story_info_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("not json", encoding="utf-8")
    title, sid, node_count, ending_count, est_time, has_warnings = _load_story_info(path)
    assert title == "broken"
    assert sid == ""
    assert node_count == 0
    assert has_warnings is False


def test_load_story_info_with_warnings(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["meta"]["warnings"] = ["Violence"]
    path = tmp_path / "warned.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    *_, has_warnings = _load_story_info(path)
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


import sys
from unittest.mock import patch


def test_parse_args_defaults():
    with patch.object(sys, "argv", ["main.py"]):
        from main import _parse_args
        assert _parse_args() == {"enabled": False, "all": False}


def test_parse_args_debug_flag():
    with patch.object(sys, "argv", ["main.py", "--debug"]):
        from main import _parse_args
        assert _parse_args() == {"enabled": True, "all": False}


def test_parse_args_debug_and_all():
    with patch.object(sys, "argv", ["main.py", "--debug", "--all"]):
        from main import _parse_args
        assert _parse_args() == {"enabled": True, "all": True}


def test_parse_args_all_without_debug_is_ignored():
    with patch.object(sys, "argv", ["main.py", "--all"]):
        from main import _parse_args
        assert _parse_args() == {"enabled": False, "all": False}
