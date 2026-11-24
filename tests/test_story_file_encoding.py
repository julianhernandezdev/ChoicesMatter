"""Story files saved the "wrong" way by ordinary Windows programs.

Two cases. A file saved as "UTF-8 with BOM" (old Notepad's favourite) should just load.
A file saved as something else entirely (Windows-1252, say) should be one broken story
in the list, not the reason the whole game refuses to open.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import main as main_module
from main import _load_story_info
from scripts.validate_story import validate_file
from src.story import StoryLoader, StoryValidationError

BOM = b"\xef\xbb\xbf"


def _accented(sample_story_dict: dict) -> str:
    sample_story_dict["meta"]["title"] = "Café"
    return json.dumps(sample_story_dict, ensure_ascii=False)


@pytest.fixture
def bom_story_path(tmp_path: Path, sample_story_dict: dict) -> Path:
    path = tmp_path / "notepad.json"
    path.write_bytes(BOM + _accented(sample_story_dict).encode("utf-8"))
    return path


@pytest.fixture
def cp1252_story_path(tmp_path: Path, sample_story_dict: dict) -> Path:
    path = tmp_path / "cafe.json"
    path.write_bytes(_accented(sample_story_dict).encode("cp1252"))
    return path


def test_story_saved_with_bom_loads(bom_story_path: Path) -> None:
    story = StoryLoader.load(bom_story_path)
    assert story.id == "test_story"
    assert story.title == "Café"


def test_plain_utf8_story_with_accents_still_loads(tmp_path: Path, sample_story_dict: dict) -> None:
    path = tmp_path / "plain.json"
    path.write_bytes(_accented(sample_story_dict).encode("utf-8"))
    assert StoryLoader.load(path).title == "Café"


def test_story_not_saved_as_utf8_is_an_ordinary_load_error(cp1252_story_path: Path) -> None:
    with pytest.raises(StoryValidationError) as excinfo:
        StoryLoader.load(cp1252_story_path)
    message = str(excinfo.value)
    assert "cafe.json" in message
    assert "UTF-8" in message


def test_story_info_for_a_non_utf8_story_falls_back_like_any_broken_story(cp1252_story_path: Path) -> None:
    title, sid, node_count, *_ = _load_story_info(cp1252_story_path)
    assert title == "cafe"
    assert sid == ""
    assert node_count == 0


def test_game_opens_with_a_non_utf8_story_in_the_folder(
    tmp_path: Path, cp1252_story_path: Path, saves_dir: Path
) -> None:
    """The whole point: one badly saved file must not keep the picker from opening."""
    stories = tmp_path / "stories"
    stories.mkdir()
    cp1252_story_path.rename(stories / "cafe.json")
    display = MagicMock()
    display.get_page_size.return_value = 5
    display.prompt_story_select.side_effect = [1, None]
    with patch.object(sys, "argv", ["main.py"]), \
         patch.object(main_module, "STORIES_DIR", stories), \
         patch.object(main_module, "SAVES_DIR", saves_dir), \
         patch("main.Display", return_value=display), \
         patch("main.load_settings", return_value={"player_name": "Felix"}), \
         patch("main.Engine") as engine_cls:
        main_module.main()

    engine_cls.assert_not_called()
    name, message = display.show_picker_error.call_args.args
    assert name == "cafe.json"
    assert "UTF-8" in message


def test_validator_accepts_a_story_saved_with_bom(bom_story_path: Path) -> None:
    assert validate_file(bom_story_path) == ([], [])


def test_validator_reports_a_non_utf8_story_instead_of_crashing(cp1252_story_path: Path) -> None:
    warnings, errors = validate_file(cp1252_story_path)
    assert warnings == []
    assert len(errors) == 1
    assert "UTF-8" in errors[0]
