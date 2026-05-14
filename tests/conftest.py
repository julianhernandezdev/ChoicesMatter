import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_story_dict() -> dict:
    return {
        "meta": {
            "id": "test_story",
            "title": "Test Story",
            "version": "1.0",
            "author": "Tester",
            "start_node": "start",
        },
        "nodes": {
            "start": {
                "text": "You begin here.",
                "choices": [
                    {"label": "Go forward", "next": "middle"},
                ],
            },
            "middle": {
                "text": "You are in the middle.",
                "choices": [
                    {"label": "Reach the end", "next": "ending"},
                ],
            },
            "ending": {
                "text": "You have escaped.",
                "choices": [],
                "is_ending": True,
                "ending_type": "good",
            },
        },
    }


@pytest.fixture
def valid_story_path(tmp_path: Path, sample_story_dict: dict) -> Path:
    path = tmp_path / "test_story.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    return path


@pytest.fixture
def saves_dir(tmp_path: Path) -> Path:
    d = tmp_path / "saves"
    d.mkdir()
    return d
