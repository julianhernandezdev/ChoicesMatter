import json
from pathlib import Path

import pytest

from story import StoryLoader, StoryValidationError


def test_valid_story_loads(valid_story_path: Path, sample_story_dict: dict) -> None:
    story = StoryLoader.load(valid_story_path)
    assert story.id == "test_story"
    assert story.title == "Test Story"
    assert story.start_node == "start"
    assert set(story.nodes.keys()) == {"start", "middle", "ending"}
    assert story.nodes["ending"].is_ending is True
    assert story.nodes["ending"].ending_type == "good"
    assert story.nodes["start"].choices[0].label == "Go forward"
    assert story.nodes["start"].choices[0].next == "middle"


def test_missing_meta_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"nodes": {}}), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="meta"):
        StoryLoader.load(path)


@pytest.mark.parametrize("missing_field", ["id", "title", "version", "author", "start_node"])
def test_missing_meta_field_raises(tmp_path: Path, sample_story_dict: dict, missing_field: str) -> None:
    del sample_story_dict["meta"][missing_field]
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match=missing_field):
        StoryLoader.load(path)


def test_bad_start_node_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["meta"]["start_node"] = "nonexistent"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="start_node"):
        StoryLoader.load(path)


def test_node_missing_text_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    del sample_story_dict["nodes"]["middle"]["text"]
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="text"):
        StoryLoader.load(path)


def test_node_missing_choices_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    del sample_story_dict["nodes"]["middle"]["choices"]
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="choices"):
        StoryLoader.load(path)


def test_choice_bad_next_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["next"] = "nowhere"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="nowhere"):
        StoryLoader.load(path)


def test_discover_returns_only_json(tmp_path: Path, valid_story_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("ignore me")
    (tmp_path / "other.md").write_text("also ignore")
    results = StoryLoader.discover(tmp_path)
    assert all(p.suffix == ".json" for p in results)
    assert valid_story_path in results


def test_discover_empty_dir(tmp_path: Path) -> None:
    empty = tmp_path / "stories"
    empty.mkdir()
    assert StoryLoader.discover(empty) == []


def test_discover_missing_dir(tmp_path: Path) -> None:
    assert StoryLoader.discover(tmp_path / "nonexistent") == []


def test_choice_defaults_have_empty_requires_and_sets(valid_story_path: Path) -> None:
    story = StoryLoader.load(valid_story_path)
    choice = story.nodes["start"].choices[0]
    assert choice.requires == {}
    assert choice.sets == {}


def test_choice_parses_requires_and_sets(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["requires"] = {"flag_a": True}
    sample_story_dict["nodes"]["start"]["choices"][0]["sets"] = {"flag_b": True}
    path = tmp_path / "flagged.json"
    path.write_text(__import__("json").dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    choice = story.nodes["start"].choices[0]
    assert choice.requires == {"flag_a": True}
    assert choice.sets == {"flag_b": True}
