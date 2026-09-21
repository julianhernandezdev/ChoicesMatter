import json
from pathlib import Path

import pytest

from scripts.validate_story import main, reachable_nodes, validate_file, validate_sagas
from src.story import StoryLoader


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


# ---------------------------------------------------------------------------
# Cross-file saga checks
# ---------------------------------------------------------------------------

def test_demo_saga_validates_clean(demo_saga: dict[str, Path]) -> None:
    assert validate_sagas(list(demo_saga.values())) == ([], [])


def test_plain_stories_have_no_saga_findings(valid_story_path: Path) -> None:
    assert validate_sagas([valid_story_path]) == ([], [])


def test_lone_chapter_gets_one_warning_and_no_errors(demo_saga: dict[str, Path]) -> None:
    warnings, errors = validate_sagas([demo_saga["ch1"]])
    assert errors == []
    assert len(warnings) == 1
    assert "pass sibling chapters together" in warnings[0]


def test_dangling_next_story_warns_and_strict_makes_it_an_error(demo_saga: dict[str, Path]) -> None:
    paths = [demo_saga["ch1"], demo_saga["ch2a"], demo_saga["ch2b"]]  # ch3 is missing

    warnings, errors = validate_sagas(paths)
    assert errors == []
    assert len([w for w in warnings if "matches no chapter" in w]) == 2

    strict_warnings, strict_errors = validate_sagas(paths, strict=True)
    assert len([e for e in strict_errors if "matches no chapter" in e]) == 2
    assert not any("matches no chapter" in w for w in strict_warnings)


def test_cycle_is_an_error(make_chapter) -> None:
    x1 = make_chapter("x1", {"e": {"next_story": "x2"}}, saga_id="cyc", saga_title="C")
    x2 = make_chapter("x2", {"e": {"next_story": "x1"}}, saga_id="cyc")
    _warnings, errors = validate_sagas([x1, x2])
    assert any("cycle" in e for e in errors)


def test_two_entry_chapters_is_an_error(make_chapter) -> None:
    a = make_chapter("a", {"e": {}}, saga_id="s", saga_title="S")
    b = make_chapter("b", {"e": {}}, saga_id="s")
    _warnings, errors = validate_sagas([a, b])
    assert any("multiple entry chapters" in e for e in errors)


def test_saga_title_on_a_non_entry_chapter_is_an_error(make_chapter) -> None:
    a = make_chapter("a", {"e": {"next_story": "b"}}, saga_id="s", saga_title="S")
    b = make_chapter("b", {"e": {}}, saga_id="s", saga_title="Also S")
    _warnings, errors = validate_sagas([a, b])
    assert any("not the entry chapter" in e for e in errors)


def test_visited_export_colliding_with_a_target_node_is_an_error(make_chapter) -> None:
    # Every make_chapter chapter has a node named 'start', so exporting visited_start collides.
    a = make_chapter(
        "a", {"e": {"next_story": "b", "exports": ["visited_start"]}}, saga_id="v", saga_title="V"
    )
    b = make_chapter("b", {"e": {}}, saga_id="v")
    _warnings, errors = validate_sagas([a, b])
    assert any("has its own node 'start'" in e for e in errors)


def test_export_that_nothing_sets_warns(make_chapter) -> None:
    a = make_chapter("a", {"e": {"next_story": "b", "exports": ["ghost"]}}, saga_id="g", saga_title="G")
    b = make_chapter("b", {"e": {}}, saga_id="g")
    warnings, errors = validate_sagas([a, b])
    assert errors == []
    assert any("exports 'ghost'" in w for w in warnings)


def test_export_seeded_by_a_parent_does_not_warn(make_chapter) -> None:
    a = make_chapter(
        "a", {"e": {"next_story": "b", "exports": ["trust"]}}, saga_id="g", saga_title="G",
        choice_sets={"e": {"trust": 1}},
    )
    b = make_chapter("b", {"e": {"next_story": "c", "exports": ["trust"]}}, saga_id="g")
    c = make_chapter("c", {"e": {"saga_end": True}}, saga_id="g")
    warnings, errors = validate_sagas([a, b, c])
    assert errors == []
    assert not any("exports 'trust'" in w for w in warnings)


def test_needed_flag_that_nothing_provides_warns(make_chapter) -> None:
    a = make_chapter("a", {"e": {"next_story": "b"}}, saga_id="m", saga_title="M")
    b = make_chapter(
        "b", {"e": {"saga_end": True}}, saga_id="m", choice_requires={"e": {"never_provided": True}}
    )
    warnings, errors = validate_sagas([a, b])
    assert errors == []
    assert any("needs flag 'never_provided'" in w for w in warnings)


def test_needed_flag_provided_by_a_parent_export_does_not_warn(make_chapter) -> None:
    a = make_chapter(
        "a", {"e": {"next_story": "b", "exports": ["key"]}}, saga_id="m", saga_title="M",
        choice_sets={"e": {"key": True}},
    )
    b = make_chapter(
        "b", {"e": {"saga_end": True}}, saga_id="m", choice_requires={"e": {"key": True}}
    )
    warnings, _errors = validate_sagas([a, b])
    assert not any("needs flag" in w for w in warnings)


def test_false_conditions_are_not_needed_flags(make_chapter) -> None:
    a = make_chapter("a", {"e": {"next_story": "b"}}, saga_id="m", saga_title="M")
    b = make_chapter(
        "b", {"e": {"saga_end": True}}, saga_id="m", choice_requires={"e": {"unset_flag": False}}
    )
    warnings, _errors = validate_sagas([a, b])
    assert not any("needs flag" in w for w in warnings)


def test_chapter_with_no_chaining_or_saga_end_warns(make_chapter) -> None:
    a = make_chapter("a", {"e": {"next_story": "b"}}, saga_id="n", saga_title="N")
    b = make_chapter("b", {"e": {}}, saga_id="n")
    warnings, _errors = validate_sagas([a, b])
    assert any("chapter 'b' has no chaining or saga_end ending" in w for w in warnings)


# ---------------------------------------------------------------------------
# Needed-flag details (list / integer conditions, inline spans, exemptions)
# ---------------------------------------------------------------------------

def _needs_flag_pair(make_chapter, requires: dict, *, b_text: str | None = None) -> list[Path]:
    a = make_chapter("a", {"e": {"next_story": "b"}}, saga_id="m", saga_title="M")
    b = make_chapter("b", {"e": {"saga_end": True}}, saga_id="m", choice_requires={"e": requires})
    if b_text is not None:
        data = json.loads(b.read_text(encoding="utf-8"))
        data["nodes"]["start"]["text"] = b_text
        b.write_text(json.dumps(data), encoding="utf-8")
    return [a, b]


def test_list_condition_counts_as_a_needed_flag(make_chapter) -> None:
    warnings, _errors = validate_sagas(_needs_flag_pair(make_chapter, {"mood": ["red", "blue"]}))
    assert any("needs flag 'mood'" in w for w in warnings)


def test_positive_integer_condition_counts_as_a_needed_flag(make_chapter) -> None:
    warnings, _errors = validate_sagas(_needs_flag_pair(make_chapter, {"trust": 2}))
    assert any("needs flag 'trust'" in w for w in warnings)


def test_non_positive_integer_condition_is_not_a_needed_flag(make_chapter) -> None:
    warnings, _errors = validate_sagas(_needs_flag_pair(make_chapter, {"trust": 0}))
    assert not any("needs flag" in w for w in warnings)


def test_inline_conditional_counts_as_a_needed_flag(make_chapter) -> None:
    paths = _needs_flag_pair(make_chapter, {}, b_text="You {met_her?greet her|walk past}.")
    warnings, _errors = validate_sagas(paths)
    assert any("needs flag 'met_her'" in w for w in warnings)


def test_flag_set_by_the_chapter_itself_is_provided(make_chapter) -> None:
    a = make_chapter("a", {"e": {"next_story": "b"}}, saga_id="m", saga_title="M")
    b = make_chapter(
        "b", {"e1": {"saga_end": True}, "e2": {}}, saga_id="m",
        choice_sets={"e2": {"counter": "+1"}}, choice_requires={"e1": {"counter": 1}},
    )
    warnings, _errors = validate_sagas([a, b])
    assert not any("needs flag" in w for w in warnings)


def test_visited_and_player_name_flags_are_exempt(make_chapter) -> None:
    paths = _needs_flag_pair(
        make_chapter, {"visited_start": True}, b_text="Hi {player_name?{player_name}|you}."
    )
    warnings, _errors = validate_sagas(paths)
    assert not any("needs flag" in w for w in warnings)


# ---------------------------------------------------------------------------
# Lone chapter: only the single WARN, nothing else about the saga
# ---------------------------------------------------------------------------

def test_lone_chapter_skips_dangling_flag_and_title_checks(make_chapter) -> None:
    lone = make_chapter(
        "lone", {"e": {"next_story": "elsewhere", "exports": ["ghost"]}}, saga_id="l",
        choice_requires={"e": {"needed": True}},
    )  # dangling link, unset export, unmet flag, and no saga_title
    warnings, errors = validate_sagas([lone], strict=True)
    assert errors == []
    assert len(warnings) == 1
    assert "pass sibling chapters together" in warnings[0]


# ---------------------------------------------------------------------------
# Duplicate meta.id among saga chapters is always an ERROR, reported once
# ---------------------------------------------------------------------------

def _duplicate_pair(make_chapter, tmp_path: Path, story_id: str, first_kw: dict, second_kw: dict):
    """Two files that both declare meta.id == story_id (make_chapter names files by id)."""
    first = make_chapter(story_id, {"e": {}}, **first_kw).rename(tmp_path / f"{story_id}_first.json")
    second = make_chapter(story_id, {"e": {}}, **second_kw).rename(
        tmp_path / f"{story_id}_second.json"
    )
    return first, second


def test_duplicate_id_inside_a_multi_chapter_saga_is_reported_once(
    make_chapter, tmp_path: Path
) -> None:
    a = make_chapter("a", {"e": {"next_story": "b"}}, saga_id="s", saga_title="S")
    b1, b2 = _duplicate_pair(make_chapter, tmp_path, "b", {"saga_id": "s"}, {"saga_id": "s"})

    _warnings, errors = validate_sagas([a, b1, b2])

    dup_errors = [e for e in errors if "duplicate" in e]
    assert len(dup_errors) == 1
    assert "'b'" in dup_errors[0]
    assert "b_first.json" in dup_errors[0] and "b_second.json" in dup_errors[0]


def test_duplicate_id_across_two_single_chapter_sagas_is_reported_once(
    make_chapter, tmp_path: Path
) -> None:
    # Each saga would otherwise hold just this chapter; SagaGraph drops the second file.
    x1, x2 = _duplicate_pair(
        make_chapter, tmp_path, "dup", {"saga_id": "s1", "saga_title": "One"}, {"saga_id": "s2"}
    )

    _warnings, errors = validate_sagas([x1, x2])

    dup_errors = [e for e in errors if "duplicate" in e]
    assert len(dup_errors) == 1
    assert "'dup'" in dup_errors[0]
    assert "dup_first.json" in dup_errors[0] and "dup_second.json" in dup_errors[0]


def test_duplicate_id_in_a_vanished_saga_is_reported_once(make_chapter, tmp_path: Path) -> None:
    # The dropped duplicate is the only chapter of saga 's2', so 's2' is absent from the graph.
    a = make_chapter("a", {"e": {"next_story": "shared"}}, saga_id="s1", saga_title="One")
    s1, s2 = _duplicate_pair(make_chapter, tmp_path, "shared", {"saga_id": "s1"}, {"saga_id": "s2"})

    _warnings, errors = validate_sagas([a, s1, s2])

    assert len([e for e in errors if "duplicate" in e]) == 1


def test_each_duplicated_id_gets_its_own_error(make_chapter, tmp_path: Path) -> None:
    p1, p2 = _duplicate_pair(
        make_chapter, tmp_path, "p", {"saga_id": "sp", "saga_title": "P"}, {"saga_id": "sp"}
    )
    q1, q2 = _duplicate_pair(
        make_chapter, tmp_path, "q", {"saga_id": "sq", "saga_title": "Q"}, {"saga_id": "sq"}
    )

    _warnings, errors = validate_sagas([p1, p2, q1, q2])

    dup_errors = [e for e in errors if "duplicate" in e]
    assert len(dup_errors) == 2
    assert any("'p'" in e for e in dup_errors) and any("'q'" in e for e in dup_errors)


def test_the_same_file_passed_twice_is_not_a_duplicate(demo_saga: dict[str, Path]) -> None:
    paths = [*demo_saga.values(), demo_saga["ch1"]]
    assert validate_sagas(paths) == ([], [])


def test_main_exits_1_on_a_duplicate_id_and_prints_it_once(
    make_chapter, tmp_path: Path, capsys
) -> None:
    x1, x2 = _duplicate_pair(
        make_chapter, tmp_path, "dup", {"saga_id": "s1", "saga_title": "One"}, {"saga_id": "s2"}
    )
    assert main([str(x1), str(x2)]) == 1
    out = capsys.readouterr().out
    assert out.count("ERROR") == 1
    assert "duplicate" in out


# ---------------------------------------------------------------------------
# main() flags and exit codes
# ---------------------------------------------------------------------------

def test_main_strict_flag_controls_the_exit_code(demo_saga: dict[str, Path]) -> None:
    paths = [str(demo_saga[key]) for key in ("ch1", "ch2a", "ch2b")]  # ch3 missing: dangling links
    assert main(paths) == 0
    assert main([*paths, "--strict"]) == 1


def test_main_with_only_the_strict_flag_is_a_usage_error() -> None:
    assert main(["--strict"]) == 2
    assert main([]) == 2


def test_main_reports_a_clean_saga(demo_saga: dict[str, Path], capsys) -> None:
    assert main([str(p) for p in demo_saga.values()]) == 0
    assert "All files OK" in capsys.readouterr().out


def test_main_lone_chapter_warning_never_fails_the_run(demo_saga: dict[str, Path], capsys) -> None:
    assert main([str(demo_saga["ch1"]), "--strict"]) == 0
    assert "pass sibling chapters together" in capsys.readouterr().out


def test_main_still_flags_a_dead_end_in_a_non_saga_story(tmp_path: Path) -> None:
    data = {
        "meta": {"id": "plain", "title": "P", "version": "1", "author": "T", "start_node": "start"},
        "nodes": {
            "start": {"text": "x", "choices": [{"label": "go", "next": "stuck"}]},
            "stuck": {"text": "y", "choices": []},
        },
    }
    path = tmp_path / "plain.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert main([str(path)]) == 1
