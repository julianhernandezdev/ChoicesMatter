import json
from pathlib import Path

import pytest

from validate_story import reachable_nodes, validate_file
from story import StoryLoader


# ---------------------------------------------------------------------------
# reachable_nodes
# ---------------------------------------------------------------------------

def test_reachable_nodes_includes_all_connected(valid_story_path: Path) -> None:
    story = StoryLoader.load(valid_story_path)
    result = reachable_nodes(story)
    assert result == {"start", "middle", "ending"}


def test_reachable_nodes_excludes_orphan(tmp_path: Path) -> None:
    data = {
        "meta": {
            "id": "orphan_test",
            "title": "Orphan Test",
            "version": "1.0",
            "author": "Tester",
            "start_node": "start",
        },
        "nodes": {
            "start": {
                "text": "Begin.",
                "choices": [{"label": "End", "next": "ending"}],
            },
            "ending": {"text": "Done.", "choices": [], "is_ending": True},
            "orphan": {"text": "Nobody reaches me.", "choices": []},
        },
    }
    path = tmp_path / "orphan.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    story = StoryLoader.load(path)
    result = reachable_nodes(story)
    assert "orphan" not in result
    assert "start" in result
    assert "ending" in result


# ---------------------------------------------------------------------------
# validate_file
# ---------------------------------------------------------------------------

def test_clean_story_no_issues(valid_story_path: Path) -> None:
    warnings, errors = validate_file(valid_story_path)
    assert warnings == []
    assert errors == []


def test_unreachable_node_is_warned(tmp_path: Path) -> None:
    data = {
        "meta": {
            "id": "unreachable_test",
            "title": "Unreachable",
            "version": "1.0",
            "author": "Tester",
            "start_node": "start",
        },
        "nodes": {
            "start": {
                "text": "Begin.",
                "choices": [{"label": "End", "next": "ending"}],
            },
            "ending": {"text": "Done.", "choices": [], "is_ending": True},
            "ghost": {"text": "Unreachable node.", "choices": [], "is_ending": True},
        },
    }
    path = tmp_path / "unreachable.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    warnings, errors = validate_file(path)
    assert any("ghost" in w for w in warnings)
    assert errors == []


def test_dead_end_node_is_error(tmp_path: Path) -> None:
    data = {
        "meta": {
            "id": "dead_end_test",
            "title": "Dead End",
            "version": "1.0",
            "author": "Tester",
            "start_node": "start",
        },
        "nodes": {
            "start": {
                "text": "Begin.",
                "choices": [{"label": "Go", "next": "dead"}],
            },
            "dead": {
                "text": "Stuck.",
                "choices": [],
                # is_ending deliberately omitted — this is the error case
            },
        },
    }
    path = tmp_path / "dead_end.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    warnings, errors = validate_file(path)
    assert any("dead" in e for e in errors)
    assert warnings == []


def test_is_ending_true_empty_choices_not_error(tmp_path: Path) -> None:
    data = {
        "meta": {
            "id": "proper_ending",
            "title": "Proper Ending",
            "version": "1.0",
            "author": "Tester",
            "start_node": "start",
        },
        "nodes": {
            "start": {
                "text": "Begin.",
                "choices": [{"label": "End", "next": "fin"}],
            },
            "fin": {
                "text": "The end.",
                "choices": [],
                "is_ending": True,
                "ending_type": "good",
            },
        },
    }
    path = tmp_path / "proper.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    warnings, errors = validate_file(path)
    assert warnings == []
    assert errors == []


def test_story_load_error_reported_as_error(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not valid json", encoding="utf-8")
    warnings, errors = validate_file(path)
    assert warnings == []
    assert len(errors) == 1
    assert "broken.json" in errors[0]


def test_validate_file_missing_node_field_is_error(tmp_path: Path) -> None:
    data = {
        "meta": {
            "id": "bad_story",
            "title": "Bad Story",
            "version": "1.0",
            "author": "Tester",
            "start_node": "start",
        },
        "nodes": {
            "start": {
                # text field missing — StoryLoader will raise StoryValidationError
                "choices": [],
                "is_ending": True,
            },
        },
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    warnings, errors = validate_file(path)
    assert len(errors) == 1
    assert warnings == []


def test_validate_file_multiple_issues(tmp_path: Path) -> None:
    data = {
        "meta": {
            "id": "multi_issue",
            "title": "Multi Issue",
            "version": "1.0",
            "author": "Tester",
            "start_node": "start",
        },
        "nodes": {
            "start": {
                "text": "Begin.",
                "choices": [{"label": "Go", "next": "dead"}],
            },
            "dead": {
                "text": "Stuck — no is_ending.",
                "choices": [],
            },
            "ghost": {
                "text": "Unreachable.",
                "choices": [],
                "is_ending": True,
            },
        },
    }
    path = tmp_path / "multi.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    warnings, errors = validate_file(path)
    assert any("ghost" in w for w in warnings)
    assert any("dead" in e for e in errors)
