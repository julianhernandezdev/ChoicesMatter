from pathlib import Path

import pytest

from gallery import GalleryManager


def test_get_count_zero_when_no_file(saves_dir: Path) -> None:
    gm = GalleryManager(saves_dir)
    assert gm.get_count("my_story") == 0


def test_record_ending_increments_count(saves_dir: Path) -> None:
    gm = GalleryManager(saves_dir)
    gm.record_ending("my_story", "good_end")
    assert gm.get_count("my_story") == 1


def test_record_same_ending_twice_counts_once(saves_dir: Path) -> None:
    gm = GalleryManager(saves_dir)
    gm.record_ending("my_story", "good_end")
    gm.record_ending("my_story", "good_end")
    assert gm.get_count("my_story") == 1


def test_record_multiple_endings(saves_dir: Path) -> None:
    gm = GalleryManager(saves_dir)
    gm.record_ending("my_story", "good_end")
    gm.record_ending("my_story", "bad_end")
    assert gm.get_count("my_story") == 2


def test_get_found_returns_set(saves_dir: Path) -> None:
    gm = GalleryManager(saves_dir)
    gm.record_ending("my_story", "good_end")
    gm.record_ending("my_story", "bad_end")
    assert gm.get_found("my_story") == {"good_end", "bad_end"}


def test_galleries_are_per_story(saves_dir: Path) -> None:
    gm = GalleryManager(saves_dir)
    gm.record_ending("story_a", "end_1")
    assert gm.get_count("story_b") == 0


def test_clear_all_removes_all_galleries(saves_dir: Path) -> None:
    gm = GalleryManager(saves_dir)
    gm.record_ending("story_a", "end_1")
    gm.record_ending("story_b", "end_1")
    gm.clear_all()
    assert gm.get_count("story_a") == 0
    assert gm.get_count("story_b") == 0


def test_clear_all_leaves_save_files_intact(saves_dir: Path) -> None:
    gm = GalleryManager(saves_dir)
    gm.record_ending("my_story", "good_end")
    # create a fake .save.json file
    (saves_dir / "my_story.save.json").write_text("{}", encoding="utf-8")
    gm.clear_all()
    assert (saves_dir / "my_story.save.json").exists()


def test_unsafe_story_id_raises(saves_dir: Path) -> None:
    gm = GalleryManager(saves_dir)
    with pytest.raises(ValueError):
        gm.record_ending("../escape", "end")
    with pytest.raises(ValueError):
        gm.get_found("bad/id")


def test_corrupted_gallery_file_returns_empty(saves_dir: Path) -> None:
    gm = GalleryManager(saves_dir)
    (saves_dir / "my_story.gallery.json").write_text("not json", encoding="utf-8")
    assert gm.get_found("my_story") == set()
    assert gm.get_count("my_story") == 0
