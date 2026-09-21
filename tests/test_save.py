from pathlib import Path

import pytest

from src.save import HandoffRecord, SaveManager, SaveState


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


def test_clear_all_removes_saves(saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    sm.write(SaveState(story_id="story_a", current_node="x"))
    sm.write(SaveState(story_id="story_b", current_node="y"))
    sm.clear_all()
    assert not sm.has_save("story_a")
    assert not sm.has_save("story_b")


def test_clear_all_empty_dir_no_error(saves_dir: Path) -> None:
    SaveManager(saves_dir).clear_all()  # must not raise


@pytest.mark.parametrize("bad_story_id", ["../escape", "a/b", "", "story id"])
def test_save_path_rejects_unsafe_story_ids(saves_dir: Path, bad_story_id: str) -> None:
    sm = SaveManager(saves_dir)
    with pytest.raises(ValueError, match="story_id"):
        sm.save_path(bad_story_id)


def test_handoff_roundtrip(saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    sm.write_handoff(HandoffRecord(story_id="ch2", from_story="ch1", state={"trust": 3, "player_name": "Casey"}))
    loaded = sm.load_handoff("ch2")
    assert loaded is not None
    assert loaded.story_id == "ch2"
    assert loaded.from_story == "ch1"
    assert loaded.state == {"trust": 3, "player_name": "Casey"}
    assert loaded.timestamp != ""
    assert sm.has_handoff("ch2") is True
    assert (saves_dir / "ch2.handoff.json").exists()


def test_handoff_missing_is_none(saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    assert sm.load_handoff("ch2") is None
    assert sm.has_handoff("ch2") is False


@pytest.mark.parametrize("content", ["not json", "[]", '{"story_id": "ch2"}', '{"story_id": "ch2", "from_story": "a", "state": 5}'])
def test_corrupt_handoff_is_treated_as_absent(saves_dir: Path, content: str) -> None:
    (saves_dir / "ch2.handoff.json").write_text(content, encoding="utf-8")
    sm = SaveManager(saves_dir)
    assert sm.load_handoff("ch2") is None
    assert sm.has_handoff("ch2") is False


def test_delete_handoff(saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    sm.write_handoff(HandoffRecord(story_id="ch2", from_story="ch1"))
    sm.delete_handoff("ch2")
    assert sm.has_handoff("ch2") is False
    sm.delete_handoff("ch2")  # silent when already gone


def test_handoff_path_rejects_unsafe_ids(saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    with pytest.raises(ValueError):
        sm.handoff_path("../evil")


def test_clear_all_removes_handoffs_and_saves(saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    sm.write(SaveState(story_id="ch1", current_node="start"))
    sm.write_handoff(HandoffRecord(story_id="ch2", from_story="ch1"))
    sm.clear_all()
    assert sm.has_save("ch1") is False
    assert sm.has_handoff("ch2") is False
