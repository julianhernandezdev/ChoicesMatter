import dataclasses
import json
from pathlib import Path

import pytest

from src.saga import (
    ChainEdge,
    ChapterInfo,
    SagaGraph,
    SagaProgress,
    chapter_info_from_story,
    chapter_label_text,
    parse_seed_arg,
)
from src.story import StoryLoader

_CASES = json.loads(
    (Path(__file__).parent / "fixtures" / "saga_cases.json").read_text(encoding="utf-8")
)["cases"]


def _chapter(d: dict) -> ChapterInfo:
    return ChapterInfo(
        story_id=d["story_id"],
        path=Path(f"{d['story_id']}.json"),
        title=d["title"],
        saga_id=d["saga_id"],
        saga_title=d.get("saga_title"),
        chapter_label=d.get("chapter_label"),
        edges=tuple(
            ChainEdge(e["node_id"], e["target"], tuple(e.get("exports", [])), e.get("transition", False))
            for e in d.get("edges", [])
        ),
        saga_end_nodes=frozenset(d.get("saga_end_nodes", [])),
        ending_count=d["ending_count"],
    )


def _progress(d: dict) -> SagaProgress:
    return SagaProgress(
        saves=frozenset(d.get("saves", [])),
        seeds=frozenset(d.get("seeds", [])),
        found={k: frozenset(v) for k, v in d.get("found", {}).items()},
        activity=dict(d.get("activity", {})),
    )


@pytest.mark.parametrize("case", _CASES, ids=[c["name"] for c in _CASES])
def test_fixture_case(case: dict) -> None:
    graph = SagaGraph.build([_chapter(c) for c in case["chapters"]])
    progress = _progress(case.get("progress", {}))
    for saga_id, exp in case["expect"].items():
        saga = graph.sagas[saga_id]
        if "title" in exp:
            assert saga.title == exp["title"]
        if "entry" in exp:
            assert saga.entry == exp["entry"]
        if "chapters" in exp:
            assert list(saga.chapters) == exp["chapters"]
        if "problems" in exp:
            assert list(saga.problems) == exp["problems"]
        if "has_dangling" in exp:
            assert saga.has_dangling is exp["has_dangling"]
        if "reached" in exp:
            assert list(graph.reached(saga, progress)) == exp["reached"]
        if "active" in exp:
            assert list(graph.active(saga, progress)) == exp["active"]
        if "complete" in exp:
            assert graph.is_complete(saga, progress) is exp["complete"]
        if "stats" in exp:
            assert dataclasses.asdict(graph.stats(saga, progress)) == exp["stats"]
        if "default_chapter" in exp:
            assert graph.default_chapter(saga, progress) == exp["default_chapter"]
        for story_id, expected in exp.get("descendants", {}).items():
            assert sorted(graph.descendants(story_id)) == expected


def test_chapters_without_saga_id_are_ignored() -> None:
    loose = ChapterInfo("x", Path("x.json"), "X", None, None, None, (), frozenset(), 1)
    graph = SagaGraph.build([loose])
    assert graph.sagas == {}
    assert graph.known_ids == frozenset()


def test_lookup_helpers() -> None:
    graph = SagaGraph.build([_chapter(c) for c in _CASES[0]["chapters"]])
    assert graph.known_ids == frozenset({"a", "b"})
    assert graph.chapter("a").title == "A"
    assert graph.chapter("nope") is None
    assert graph.saga_of("b").saga_id == "s"
    assert graph.saga_of("nope") is None
    assert graph.depth("a") == 0
    assert graph.depth("b") == 1
    assert graph.depth("nope") is None
    assert graph.descendants("nope") == frozenset()
    assert [c.story_id for c in graph.chapters_of(graph.sagas["s"])] == ["a", "b"]


def test_default_chapter_prefers_latest_activity_then_earlier_chapter() -> None:
    graph = SagaGraph.build([_chapter(c) for c in _CASES[1]["chapters"]])
    saga = graph.sagas["s"]
    newer = SagaProgress(saves=frozenset({"b1", "b2"}), activity={"b1": "2026-01-01", "b2": "2026-02-01"})
    assert graph.default_chapter(saga, newer) == "b2"
    tie = SagaProgress(saves=frozenset({"b1", "b2"}), activity={"b1": "2026-01-01", "b2": "2026-01-01"})
    assert graph.default_chapter(saga, tie) == "b1"


def test_descendants_terminates_on_a_cycle() -> None:
    graph = SagaGraph.build([_chapter(c) for c in _CASES[3]["chapters"]])
    assert graph.descendants("a") == frozenset({"b"})


def test_chapter_info_from_story_and_label(demo_saga: dict[str, Path]) -> None:
    info = chapter_info_from_story(StoryLoader.load(demo_saga["ch2a"]))
    assert info.story_id == "ch2a"
    assert info.path == demo_saga["ch2a"]
    assert info.saga_id == "demo"
    assert info.chapter_label == "2A"
    assert info.edges == (ChainEdge("e_go", "ch3", ("trust",), True),)
    assert info.next_targets == frozenset({"ch3"})
    assert info.ending_count == 1
    assert chapter_label_text(info) == "2A — ch2a"
    ch3 = chapter_info_from_story(StoryLoader.load(demo_saga["ch3"]))
    assert ch3.saga_end_nodes == frozenset({"e_win"})
    assert chapter_label_text(ch3) == "ch3"


def test_demo_saga_builds_a_clean_graph(demo_saga: dict[str, Path]) -> None:
    infos = [chapter_info_from_story(StoryLoader.load(p)) for p in demo_saga.values()]
    graph = SagaGraph.build(infos)
    saga = graph.sagas["demo"]
    assert saga.entry == "ch1"
    assert saga.title == "Demo Saga"
    assert saga.problems == ()
    assert list(saga.chapters) == ["ch1", "ch2a", "ch2b", "ch3"]


# ---------------------------------------------------------------------------
# parse_seed_arg
# ---------------------------------------------------------------------------

def test_parse_seed_arg_types() -> None:
    assert parse_seed_arg("trust=4,key_taken=true,gone=FALSE,mood=calm,delta=-2") == {
        "trust": 4, "key_taken": True, "gone": False, "mood": "calm", "delta": -2,
    }


def test_parse_seed_arg_keeps_equals_in_value() -> None:
    assert parse_seed_arg("note=a=b") == {"note": "a=b"}


@pytest.mark.parametrize("bad", ["", "novalue", "=3", "a=1,,b=2", "a=1,"])
def test_parse_seed_arg_rejects_malformed(bad: str) -> None:
    with pytest.raises(ValueError):
        parse_seed_arg(bad)
