"""A damaged save or endings file must never stop the game opening or a story starting.

The game writes straight over the old file, so a power cut or a full disk can leave one
that is empty or stops half way. These tests hand the game files like that.
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from main import _build_entries
from src.engine import Engine
from src.gallery import GalleryManager
from src.save import SaveManager
from src.story import StoryLoader

DAMAGED_GALLERIES = [
    pytest.param(b"[]", id="a list instead of a record"),
    pytest.param(b"null", id="null"),
    pytest.param(b'{"endings_found": null}', id="endings_found is null"),
    pytest.param(b"\xff\xfe\x00\x00", id="not text at all"),
]

DAMAGED_SAVES = [
    pytest.param(b"", id="0 bytes"),
    pytest.param(b'{\n  "story_id": "test_story",\n  "current_no', id="cut off half way"),
    pytest.param(b"\x00" * 64, id="all zero bytes"),
    pytest.param(b"\xff\xfe\x00\x00", id="not text at all"),
    pytest.param(b'{"story_id": "test_story"}', id="no current_node"),
    pytest.param(b"[]", id="a list instead of a record"),
    pytest.param(b"null", id="null"),
]


# ---------------------------------------------------------------------------
# Endings gallery
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("body", DAMAGED_GALLERIES)
def test_damaged_gallery_counts_as_no_endings_found(saves_dir: Path, body: bytes) -> None:
    (saves_dir / "test_story.gallery.json").write_bytes(body)
    gm = GalleryManager(saves_dir)

    assert gm.get_found("test_story") == set()
    assert gm.get_count("test_story") == 0


@pytest.mark.parametrize("body", DAMAGED_GALLERIES)
def test_story_picker_still_lists_a_story_with_a_damaged_gallery(
    valid_story_path: Path, saves_dir: Path, body: bytes
) -> None:
    (saves_dir / "test_story.gallery.json").write_bytes(body)

    entries = _build_entries([valid_story_path], {}, SaveManager(saves_dir), GalleryManager(saves_dir))

    assert entries[0]["label"] == "Test Story"
    assert entries[0]["error"] is False
    assert entries[0]["endings_found"] == 0


def test_damaged_gallery_is_only_replaced_when_a_new_ending_is_found(saves_dir: Path) -> None:
    path = saves_dir / "test_story.gallery.json"
    path.write_bytes(b"[]")
    gm = GalleryManager(saves_dir)

    gm.get_found("test_story")
    assert path.read_bytes() == b"[]"  # looking at it does not throw the player's file away

    gm.record_ending("test_story", "ending")
    assert gm.get_found("test_story") == {"ending"}


# ---------------------------------------------------------------------------
# Active save
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("body", DAMAGED_SAVES)
def test_damaged_save_counts_as_no_save(saves_dir: Path, body: bytes) -> None:
    sm = SaveManager(saves_dir)
    sm.save_path("test_story").write_bytes(body)

    assert sm.load("test_story") is None


@pytest.mark.parametrize("body", DAMAGED_SAVES)
def test_story_starts_fresh_when_its_save_is_damaged(
    valid_story_path: Path, saves_dir: Path, body: bytes
) -> None:
    sm = SaveManager(saves_dir)
    sm.save_path("test_story").write_bytes(body)
    display = MagicMock()
    display.prompt_choice.return_value = None  # the player reads the first page and quits

    Engine(StoryLoader.load(valid_story_path), sm, display, GalleryManager(saves_dir)).run()

    display.prompt_continue_or_new.assert_not_called()  # there is nothing to continue
    display.show_node.assert_called_once_with("Test Story", ["You begin here."], [], [], None)
    assert sm.save_path("test_story").read_bytes() == body  # starting does not delete the bad file


def test_first_move_after_a_damaged_save_writes_a_good_one(valid_story_path: Path, saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    sm.save_path("test_story").write_bytes(b"")
    display = MagicMock()
    display.prompt_choice.side_effect = [1, None]  # make one choice, then quit

    Engine(StoryLoader.load(valid_story_path), sm, display, GalleryManager(saves_dir)).run()

    assert sm.load("test_story").current_node == "middle"


# ---------------------------------------------------------------------------
# A file that is there but will not open
# ---------------------------------------------------------------------------

def test_a_file_that_will_not_open_counts_as_missing(saves_dir: Path) -> None:
    # A folder wearing the file's name is the cheap way to get "it exists but you cannot read it".
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    sm.save_path("test_story").mkdir()
    (saves_dir / "test_story.gallery.json").mkdir()

    assert sm.load("test_story") is None
    assert gm.get_found("test_story") == set()
