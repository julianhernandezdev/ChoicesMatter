from pathlib import Path

import pytest

from save import SaveManager, SaveState


def test_has_save_false_when_missing(saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    assert sm.has_save("test_story") is False


def test_write_then_has_save_true(saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    sm.write(SaveState(story_id="test_story", current_node="middle"))
    assert sm.has_save("test_story") is True


def test_write_then_load_roundtrip(saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    original = SaveState(
        story_id="test_story",
        current_node="middle",
        history=["start"],
    )
    sm.write(original)
    loaded = sm.load("test_story")
    assert loaded is not None
    assert loaded.story_id == original.story_id
    assert loaded.current_node == original.current_node
    assert loaded.history == original.history
    assert loaded.timestamp != ""


def test_load_returns_none_when_missing(saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    assert sm.load("test_story") is None


def test_delete_removes_save(saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    sm.write(SaveState(story_id="test_story", current_node="start"))
    sm.delete("test_story")
    assert sm.has_save("test_story") is False


def test_delete_silent_when_missing(saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    sm.delete("nonexistent")  # must not raise


def test_save_path_format(saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    assert sm.save_path("my_story") == saves_dir / "my_story.save.json"


@pytest.mark.parametrize("bad_story_id", ["../escape", "a/b", "", "story id"])
def test_save_path_rejects_unsafe_story_ids(saves_dir: Path, bad_story_id: str) -> None:
    sm = SaveManager(saves_dir)
    with pytest.raises(ValueError, match="story_id"):
        sm.save_path(bad_story_id)
