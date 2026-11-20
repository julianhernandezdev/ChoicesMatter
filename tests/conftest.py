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


@pytest.fixture
def make_chapter(tmp_path: Path):
    """Factory: write a small chapter file into tmp_path and return its path.

    `endings` maps an ending node id to extra node fields (next_story, exports, ...).
    Each ending is reached from `start` by one choice; `choice_sets` / `choice_requires`
    map an ending id to the `sets` / `requires` dict on that choice.
    """

    def _make(
        story_id: str,
        endings: dict,
        *,
        saga_id: str | None = "demo",
        saga_title: str | None = None,
        chapter_label: str | None = None,
        title: str | None = None,
        name_prompt: str | None = None,
        choice_sets: dict | None = None,
        choice_requires: dict | None = None,
    ) -> Path:
        meta = {
            "id": story_id,
            "title": title or story_id,
            "version": "1.0",
            "author": "Tester",
            "start_node": "start",
        }
        if saga_id:
            meta["saga_id"] = saga_id
        if saga_title:
            meta["saga_title"] = saga_title
        if chapter_label:
            meta["chapter_label"] = chapter_label
        if name_prompt:
            meta["name_prompt"] = name_prompt
        nodes: dict = {"start": {"text": f"{story_id} begins.", "choices": []}}
        for end_id, fields in endings.items():
            choice = {"label": f"go {end_id}", "next": end_id}
            if choice_sets and end_id in choice_sets:
                choice["sets"] = choice_sets[end_id]
            if choice_requires and end_id in choice_requires:
                choice["requires"] = choice_requires[end_id]
            nodes["start"]["choices"].append(choice)
            nodes[end_id] = {"text": f"{end_id} text.", "choices": [], "is_ending": True, **fields}
        path = tmp_path / f"{story_id}.json"
        path.write_text(json.dumps({"meta": meta, "nodes": nodes}), encoding="utf-8")
        return path

    return _make


@pytest.fixture
def demo_saga(make_chapter) -> dict[str, Path]:
    """ch1 -> (ch2a | ch2b) -> ch3, with a plain dead end in ch1 and a saga_end in ch3."""
    return {
        "ch1": make_chapter(
            "ch1",
            {
                "e_a": {"next_story": "ch2a", "exports": ["trust"]},
                "e_b": {"next_story": "ch2b", "exports": ["trust"]},
                "e_x": {},
            },
            saga_title="Demo Saga",
            choice_sets={"e_a": {"trust": 3}, "e_b": {"trust": 1}},
        ),
        "ch2a": make_chapter(
            "ch2a",
            {"e_go": {"next_story": "ch3", "exports": ["trust"], "chapter_transition": True}},
            chapter_label="2A",
        ),
        "ch2b": make_chapter(
            "ch2b",
            {"e_go": {"next_story": "ch3", "exports": ["trust"]}},
            chapter_label="2B",
        ),
        "ch3": make_chapter("ch3", {"e_win": {"saga_end": True}, "e_lose": {}}),
    }
