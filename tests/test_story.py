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


def test_node_overlays_default_to_empty(valid_story_path: Path) -> None:
    story = StoryLoader.load(valid_story_path)
    assert story.nodes["start"].overlays == []


def test_overlay_fields_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["overlays"] = [
        {"text": "You sense something.", "requires": {"flag": True}, "position": "before"},
        {"text": "A chill runs through you.", "position": "after"},
    ]
    path = tmp_path / "overlay_story.json"
    path.write_text(__import__("json").dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    overlays = story.nodes["start"].overlays
    assert len(overlays) == 2
    assert overlays[0].text == "You sense something."
    assert overlays[0].requires == {"flag": True}
    assert overlays[0].position == "before"
    assert overlays[1].position == "after"
    assert overlays[1].requires == {}


def test_overlay_position_defaults_to_after(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["overlays"] = [{"text": "Whisper."}]
    path = tmp_path / "pos_default.json"
    path.write_text(__import__("json").dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].overlays[0].position == "after"


def test_choice_parses_requires_and_sets(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["requires"] = {"flag_a": True}
    sample_story_dict["nodes"]["start"]["choices"][0]["sets"] = {"flag_b": True}
    path = tmp_path / "flagged.json"
    path.write_text(__import__("json").dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    choice = story.nodes["start"].choices[0]
    assert choice.requires == {"flag_a": True}
    assert choice.sets == {"flag_b": True}


def test_node_count_and_ending_count(valid_story_path: Path) -> None:
    story = StoryLoader.load(valid_story_path)
    assert story.node_count == 3
    assert story.ending_count == 1


def test_est_time_auto_computed(valid_story_path: Path) -> None:
    story = StoryLoader.load(valid_story_path)
    assert story.est_time.startswith("~")
    assert "min" in story.est_time


def test_est_time_author_override(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["meta"]["est_time"] = "15–25 min"
    path = tmp_path / "timed.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.est_time == "15–25 min"


def test_est_time_invalid_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["meta"]["est_time"] = ""
    path = tmp_path / "bad_time.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="est_time"):
        StoryLoader.load(path)


@pytest.mark.parametrize("bad_story_id", ["../escape", "story/id", "story id", ""])
def test_invalid_story_id_raises(tmp_path: Path, sample_story_dict: dict, bad_story_id: str) -> None:
    sample_story_dict["meta"]["id"] = bad_story_id
    path = tmp_path / "bad_id.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="id"):
        StoryLoader.load(path)


def test_choice_missing_label_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    del sample_story_dict["nodes"]["start"]["choices"][0]["label"]
    path = tmp_path / "missing_choice_label.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="label"):
        StoryLoader.load(path)


def test_choice_requires_invalid_type_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["requires"] = {"flag": {"nested": True}}
    path = tmp_path / "bad_requires.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="requires"):
        StoryLoader.load(path)


def test_overlay_position_must_be_before_or_after(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["overlays"] = [{"text": "Whisper.", "position": "middle"}]
    path = tmp_path / "bad_overlay_position.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="position"):
        StoryLoader.load(path)


# ------------------------------------------------------------------
# Overlay style field
# ------------------------------------------------------------------

def test_overlay_style_defaults_to_empty(valid_story_path: Path, sample_story_dict: dict, tmp_path: Path) -> None:
    sample_story_dict["nodes"]["start"]["overlays"] = [{"text": "Whisper."}]
    path = tmp_path / "no_style.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].overlays[0].style == ""


def test_overlay_style_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["overlays"] = [
        {"text": "A warning.", "style": "warning", "position": "before"},
        {"text": "An echo.", "style": "echo", "position": "after"},
    ]
    path = tmp_path / "styled_overlays.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    overlays = story.nodes["start"].overlays
    assert overlays[0].style == "warning"
    assert overlays[1].style == "echo"


# ------------------------------------------------------------------
# Inset parsing
# ------------------------------------------------------------------

def test_node_insets_default_to_empty(valid_story_path: Path) -> None:
    story = StoryLoader.load(valid_story_path)
    assert story.nodes["start"].insets == []


def test_insets_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["insets"] = [
        {"text": "Location: The Vault", "position": "before", "style": "system"},
        {"text": "A distant memory surfaces.", "position": "after", "style": "memory", "requires": {"saw_vault": True}},
    ]
    path = tmp_path / "inset_story.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    insets = story.nodes["start"].insets
    assert len(insets) == 2
    assert insets[0].text == "Location: The Vault"
    assert insets[0].position == "before"
    assert insets[0].style == "system"
    assert insets[0].requires == {}
    assert insets[1].position == "after"
    assert insets[1].style == "memory"
    assert insets[1].requires == {"saw_vault": True}


def test_inset_position_defaults_to_before(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["insets"] = [{"text": "Ambient note."}]
    path = tmp_path / "inset_default_pos.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].insets[0].position == "before"


def test_inset_style_defaults_to_empty(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["insets"] = [{"text": "No style."}]
    path = tmp_path / "inset_no_style.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].insets[0].style == ""


def test_inset_not_a_list_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["insets"] = "not a list"
    path = tmp_path / "bad_insets.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="insets"):
        StoryLoader.load(path)


def test_inset_invalid_position_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["insets"] = [{"text": "Bad.", "position": "middle"}]
    path = tmp_path / "bad_inset_pos.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="position"):
        StoryLoader.load(path)


def test_inset_missing_text_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["insets"] = [{"position": "before"}]
    path = tmp_path / "bad_inset_text.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="text"):
        StoryLoader.load(path)


# ------------------------------------------------------------------
# Load-level errors
# ------------------------------------------------------------------

def test_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{ not valid json", encoding="utf-8")
    with pytest.raises(StoryValidationError, match="Invalid JSON"):
        StoryLoader.load(path)


def test_root_not_object_raises(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="root must be a JSON object"):
        StoryLoader.load(path)


def test_missing_nodes_block_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    del sample_story_dict["nodes"]
    path = tmp_path / "no_nodes.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="nodes"):
        StoryLoader.load(path)


def test_node_not_object_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"] = "not an object"
    path = tmp_path / "bad_node.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="must be an object"):
        StoryLoader.load(path)


def test_is_ending_not_bool_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["ending"]["is_ending"] = "yes"
    path = tmp_path / "bad_is_ending.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="is_ending"):
        StoryLoader.load(path)


def test_invalid_ending_type_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["ending"]["ending_type"] = "terrible"
    path = tmp_path / "bad_ending_type.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="ending_type"):
        StoryLoader.load(path)


# ------------------------------------------------------------------
# scene and choice_number_color validation
# ------------------------------------------------------------------

def test_scene_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["scene"] = "The Vault"
    path = tmp_path / "scene_story.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].scene == "The Vault"


def test_scene_empty_string_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["scene"] = ""
    path = tmp_path / "bad_scene_empty.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="scene"):
        StoryLoader.load(path)


def test_scene_not_string_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["scene"] = 42
    path = tmp_path / "bad_scene_type.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="scene"):
        StoryLoader.load(path)


def test_choice_number_color_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choice_number_color"] = "bright_red"
    path = tmp_path / "cnc_story.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].choice_number_color == "bright_red"


def test_choice_number_color_empty_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choice_number_color"] = ""
    path = tmp_path / "bad_cnc.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="choice_number_color"):
        StoryLoader.load(path)


# ------------------------------------------------------------------
# warnings validation
# ------------------------------------------------------------------

def test_warnings_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["meta"]["warnings"] = ["Violence", "Horror"]
    path = tmp_path / "warned_story.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.warnings == ["Violence", "Horror"]


def test_warnings_not_list_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["meta"]["warnings"] = "a single string"
    path = tmp_path / "bad_warnings.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="warnings"):
        StoryLoader.load(path)


def test_warnings_empty_string_item_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["meta"]["warnings"] = [""]
    path = tmp_path / "bad_warnings_empty.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="warnings"):
        StoryLoader.load(path)


# ------------------------------------------------------------------
# choices / choice field validation
# ------------------------------------------------------------------

def test_choices_not_list_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"] = "not a list"
    path = tmp_path / "choices_not_list.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="choices"):
        StoryLoader.load(path)


def test_choice_not_object_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"] = ["not an object"]
    path = tmp_path / "choice_not_object.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="must be an object"):
        StoryLoader.load(path)


def test_choice_color_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["color"] = "bright_red"
    path = tmp_path / "color_story.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].choices[0].color == "bright_red"


def test_choice_color_empty_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["color"] = ""
    path = tmp_path / "bad_color.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="color"):
        StoryLoader.load(path)


def test_choice_obfuscated_not_bool_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["obfuscated"] = "yes"
    path = tmp_path / "bad_obfuscated.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="obfuscated"):
        StoryLoader.load(path)


# ------------------------------------------------------------------
# overlays / insets element validation
# ------------------------------------------------------------------

def test_overlays_not_list_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["overlays"] = "not a list"
    path = tmp_path / "overlays_not_list.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="overlays"):
        StoryLoader.load(path)


def test_overlay_not_object_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["overlays"] = ["not an object"]
    path = tmp_path / "overlay_not_object.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="must be an object"):
        StoryLoader.load(path)


def test_inset_not_object_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["insets"] = ["not an object"]
    path = tmp_path / "inset_not_object.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="must be an object"):
        StoryLoader.load(path)


# ------------------------------------------------------------------
# _parse_flags: requires/sets not a dict
# ------------------------------------------------------------------

def test_choice_requires_not_dict_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["requires"] = ["flag_a"]
    path = tmp_path / "requires_not_dict.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="requires"):
        StoryLoader.load(path)


# ------------------------------------------------------------------
# auto_visited_flags
# ------------------------------------------------------------------

def test_auto_visited_flags_defaults_true(valid_story_path: Path) -> None:
    story = StoryLoader.load(valid_story_path)
    assert story.auto_visited_flags is True


def test_auto_visited_flags_false_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["meta"]["auto_visited_flags"] = False
    path = tmp_path / "no_visited.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.auto_visited_flags is False


def test_auto_visited_flags_non_bool_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["meta"]["auto_visited_flags"] = "yes"
    path = tmp_path / "bad_avf.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="auto_visited_flags"):
        StoryLoader.load(path)


def test_visited_prefix_in_sets_raises_when_auto_on(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["sets"] = {"visited_middle": True}
    path = tmp_path / "visited_sets.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="visited_"):
        StoryLoader.load(path)


def test_visited_prefix_in_sets_allowed_when_auto_off(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["meta"]["auto_visited_flags"] = False
    sample_story_dict["nodes"]["start"]["choices"][0]["sets"] = {"visited_middle": True}
    path = tmp_path / "visited_sets_opt_out.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].choices[0].sets == {"visited_middle": True}


def test_visited_prefix_in_requires_is_allowed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["requires"] = {"visited_intro": True}
    path = tmp_path / "visited_requires.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].choices[0].requires == {"visited_intro": True}


# ------------------------------------------------------------------
# Non-boolean state: _parse_requires
# ------------------------------------------------------------------

def test_requires_int_threshold_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["requires"] = {"trust": 3}
    path = tmp_path / "int_requires.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].choices[0].requires == {"trust": 3}


def test_requires_string_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["requires"] = {"allegiance": "red"}
    path = tmp_path / "str_requires.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].choices[0].requires == {"allegiance": "red"}


def test_requires_list_of_strings_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["requires"] = {"allegiance": ["red", "blue"]}
    path = tmp_path / "list_requires.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].choices[0].requires == {"allegiance": ["red", "blue"]}


def test_requires_empty_list_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["requires"] = {"allegiance": []}
    path = tmp_path / "empty_list_requires.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="requires"):
        StoryLoader.load(path)


def test_requires_list_with_non_string_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["requires"] = {"allegiance": ["red", 5]}
    path = tmp_path / "bad_list_requires.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="requires"):
        StoryLoader.load(path)


def test_requires_invalid_type_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["requires"] = {"trust": {"gte": 3}}
    path = tmp_path / "bad_type_requires.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="requires"):
        StoryLoader.load(path)


# ------------------------------------------------------------------
# Non-boolean state: _parse_sets
# ------------------------------------------------------------------

def test_sets_int_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["sets"] = {"trust": 5}
    path = tmp_path / "int_sets.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].choices[0].sets == {"trust": 5}


def test_sets_string_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["sets"] = {"allegiance": "red"}
    path = tmp_path / "str_sets.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].choices[0].sets == {"allegiance": "red"}


def test_sets_delta_plus_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["sets"] = {"trust": "+1"}
    path = tmp_path / "delta_plus_sets.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].choices[0].sets == {"trust": "+1"}


def test_sets_delta_minus_parsed(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["sets"] = {"trust": "-2"}
    path = tmp_path / "delta_minus_sets.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    story = StoryLoader.load(path)
    assert story.nodes["start"].choices[0].sets == {"trust": "-2"}


def test_sets_malformed_delta_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["sets"] = {"trust": "+abc"}
    path = tmp_path / "bad_delta_sets.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="delta"):
        StoryLoader.load(path)


def test_sets_invalid_type_raises(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["nodes"]["start"]["choices"][0]["sets"] = {"trust": [1, 2]}
    path = tmp_path / "bad_type_sets.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    with pytest.raises(StoryValidationError, match="sets"):
        StoryLoader.load(path)
