import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from main import (
    _build_entries,
    _build_progress,
    _collect_chapter_infos,
    _launch_story,
    _load_story_info,
    _parse_args,
    _parse_seed_override,
    _play_chapter,
    _prompt_name_state,
    _resolve_player_name,
    _saga_fresh_run_state,
)
from src.engine import ChainResult
from src.gallery import GalleryManager
from src.saga import SagaGraph
from src.save import HandoffRecord, SaveManager, SaveState
from src.story import StoryLoader


def test_load_story_info_valid(valid_story_path: Path) -> None:
    title, sid, node_count, ending_count, est_time, has_warnings, author, version = _load_story_info(valid_story_path)
    assert title == "Test Story"
    assert sid == "test_story"
    assert node_count == 3
    assert ending_count == 1
    assert "min" in est_time
    assert has_warnings is False
    assert author == "Tester"
    assert version == "1.0"


def test_load_story_info_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("not json", encoding="utf-8")
    title, sid, node_count, ending_count, est_time, has_warnings, author, version = _load_story_info(path)
    assert title == "broken"
    assert sid == ""
    assert node_count == 0
    assert has_warnings is False
    assert author == ""
    assert version == ""


def test_load_story_info_with_warnings(tmp_path: Path, sample_story_dict: dict) -> None:
    sample_story_dict["meta"]["warnings"] = ["Violence"]
    path = tmp_path / "warned.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    *_, has_warnings, _author, _version = _load_story_info(path)
    assert has_warnings is True


def test_build_entries_valid_story(valid_story_path: Path, saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    gm = GalleryManager(saves_dir)
    entries = _build_entries([valid_story_path], {}, sm, gm)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["index"] == 1
    assert entry["label"] == "Test Story"
    assert entry["error"] is False
    assert entry["has_save"] is False
    assert entry["endings_found"] == 0
    assert entry["node_count"] == 3
    assert entry["author"] == "Tester"
    assert entry["version"] == "1.0"


def test_build_entries_error_story(tmp_path: Path, saves_dir: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("bad json", encoding="utf-8")
    errors = {path: "parse error"}
    sm = SaveManager(saves_dir)
    gm = GalleryManager(saves_dir)
    entries = _build_entries([path], errors, sm, gm)
    assert entries[0]["error"] is True
    assert entries[0]["label"] == "bad"


def test_build_entries_with_active_save(valid_story_path: Path, saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    sm.write(SaveState(story_id="test_story", current_node="start"))
    gm = GalleryManager(saves_dir)
    entries = _build_entries([valid_story_path], {}, sm, gm)
    assert entries[0]["has_save"] is True


def test_build_entries_with_gallery_count(valid_story_path: Path, saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    gm = GalleryManager(saves_dir)
    gm.record_ending("test_story", "ending")
    entries = _build_entries([valid_story_path], {}, sm, gm)
    assert entries[0]["endings_found"] == 1


def test_build_entries_multiple_paths(valid_story_path: Path, saves_dir: Path,
                                      tmp_path: Path, sample_story_dict: dict) -> None:
    second_path = tmp_path / "second.json"
    sample_story_dict["meta"]["id"] = "second_story"
    sample_story_dict["meta"]["title"] = "Second Story"
    second_path.write_text(json.dumps(sample_story_dict), encoding="utf-8")

    sm = SaveManager(saves_dir)
    gm = GalleryManager(saves_dir)
    entries = _build_entries([valid_story_path, second_path], {}, sm, gm)
    assert len(entries) == 2
    assert entries[0]["index"] == 1
    assert entries[1]["index"] == 2


def test_parse_args_defaults():
    with patch.object(sys, "argv", ["main.py"]):
        assert _parse_args() == {"enabled": False, "all": False}


def test_parse_args_debug_flag():
    with patch.object(sys, "argv", ["main.py", "--debug"]):
        assert _parse_args() == {"enabled": True, "all": False}


def test_parse_args_debug_and_all():
    with patch.object(sys, "argv", ["main.py", "--debug", "--all"]):
        assert _parse_args() == {"enabled": True, "all": True}


def test_parse_args_all_without_debug_is_ignored():
    with patch.object(sys, "argv", ["main.py", "--all"]):
        assert _parse_args() == {"enabled": False, "all": False}


# ---------------------------------------------------------------------------
# _resolve_player_name
# ---------------------------------------------------------------------------

def test_resolve_player_name_entered_wins():
    assert _resolve_player_name("Casey", "Officer", "Felix") == "Casey"


def test_resolve_player_name_settings_wins_over_story_default():
    assert _resolve_player_name("", "Officer", "Felix") == "Felix"


def test_resolve_player_name_falls_back_to_story_default_when_no_settings_name():
    assert _resolve_player_name("", "Officer", "") == "Officer"


def test_resolve_player_name_none_when_nothing_available():
    assert _resolve_player_name("", "", "") is None


# ---------------------------------------------------------------------------
# _prompt_name_state
# ---------------------------------------------------------------------------

def _name_story(name_default: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(name_prompt="What is your name?", name_default=name_default)


def test_prompt_name_state_returns_typed_name():
    display = MagicMock()
    display.prompt_protagonist_name.return_value = "Casey"
    assert _prompt_name_state(_name_story(), display, "Felix") == {"player_name": "Casey"}
    display.prompt_protagonist_name.assert_called_once_with("What is your name?", prefill="Felix")


def test_prompt_name_state_empty_input_uses_settings_name():
    display = MagicMock()
    display.prompt_protagonist_name.return_value = ""
    assert _prompt_name_state(_name_story("Officer"), display, "Felix") == {"player_name": "Felix"}


def test_prompt_name_state_empty_input_falls_back_to_story_default():
    display = MagicMock()
    display.prompt_protagonist_name.return_value = ""
    assert _prompt_name_state(_name_story("Officer"), display, "") == {"player_name": "Officer"}


def test_prompt_name_state_q_returns_none_without_error_screen():
    display = MagicMock()
    display.prompt_protagonist_name.return_value = None
    assert _prompt_name_state(_name_story(), display, "Felix") is None
    display.show_name_required.assert_not_called()


def test_prompt_name_state_unresolvable_shows_error_and_returns_none():
    display = MagicMock()
    display.prompt_protagonist_name.return_value = ""
    assert _prompt_name_state(_name_story(), display, "") is None
    display.show_name_required.assert_called_once_with()


# ---------------------------------------------------------------------------
# _launch_story wiring
# ---------------------------------------------------------------------------

def test_launch_story_passes_provider_when_story_has_name_prompt(
    tmp_path: Path, saves_dir: Path, sample_story_dict: dict
) -> None:
    sample_story_dict["meta"]["name_prompt"] = "Who are you?"
    path = tmp_path / "named.json"
    path.write_text(json.dumps(sample_story_dict), encoding="utf-8")
    display = MagicMock()
    display.prompt_protagonist_name.return_value = "Casey"

    with patch("main.Engine") as engine_cls, patch("main.load_settings", return_value={"player_name": "Felix"}):
        _launch_story(path, {}, SaveManager(saves_dir), GalleryManager(saves_dir), display)

    kwargs = engine_cls.call_args.kwargs
    assert kwargs["initial_state"] == {"player_name": "Felix"}
    display.prompt_protagonist_name.assert_not_called()  # no up-front prompt any more
    assert kwargs["fresh_run_state"]() == {"player_name": "Casey"}
    display.prompt_protagonist_name.assert_called_once_with("Who are you?", prefill="Felix")


def test_launch_story_passes_no_provider_without_name_prompt(
    valid_story_path: Path, saves_dir: Path
) -> None:
    display = MagicMock()

    with patch("main.Engine") as engine_cls, patch("main.load_settings", return_value={"player_name": "Felix"}):
        _launch_story(valid_story_path, {}, SaveManager(saves_dir), GalleryManager(saves_dir), display)

    kwargs = engine_cls.call_args.kwargs
    assert kwargs["fresh_run_state"] is None
    assert kwargs["initial_state"] == {"player_name": "Felix"}
    display.prompt_protagonist_name.assert_not_called()


# ---------------------------------------------------------------------------
# --seed
# ---------------------------------------------------------------------------

def test_parse_seed_override_absent():
    with patch.object(sys, "argv", ["main.py", "--debug"]):
        assert _parse_seed_override() is None


def test_parse_seed_override_parses_values():
    with patch.object(sys, "argv", ["main.py", "--debug", "--seed", "trust=4,ok=true,who=Ash"]):
        assert _parse_seed_override() == {"trust": 4, "ok": True, "who": "Ash"}


def test_parse_seed_override_requires_debug():
    with patch.object(sys, "argv", ["main.py", "--seed", "a=1"]):
        with pytest.raises(SystemExit):
            _parse_seed_override()


def test_parse_seed_override_rejects_malformed_value():
    with patch.object(sys, "argv", ["main.py", "--debug", "--seed", "oops"]):
        with pytest.raises(SystemExit):
            _parse_seed_override()


def test_parse_seed_override_rejects_empty_pair():
    with patch.object(sys, "argv", ["main.py", "--debug", "--seed", "a=1,,b=2"]):
        with pytest.raises(SystemExit):
            _parse_seed_override()


def test_parse_args_is_unchanged_by_seed():
    with patch.object(sys, "argv", ["main.py", "--debug", "--seed", "a=1"]):
        assert _parse_args() == {"enabled": True, "all": False}


# ---------------------------------------------------------------------------
# Chapter discovery and progress
# ---------------------------------------------------------------------------

def _graph(paths) -> SagaGraph:
    return SagaGraph.build(_collect_chapter_infos(list(paths)))


def test_collect_chapter_infos_skips_plain_and_broken_stories(
    valid_story_path: Path, demo_saga: dict[str, Path], tmp_path: Path
) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("not json", encoding="utf-8")
    infos = _collect_chapter_infos([valid_story_path, broken, *demo_saga.values()])
    assert sorted(i.story_id for i in infos) == ["ch1", "ch2a", "ch2b", "ch3"]


def test_build_progress_reads_saves_seeds_galleries(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    sm.write(SaveState(story_id="ch1", current_node="start"))
    sm.write_handoff(HandoffRecord(story_id="ch2a", from_story="ch1", state={"trust": 3}))
    gm.record_ending("ch1", "e_x")

    progress = _build_progress(_collect_chapter_infos(demo_saga.values()), sm, gm)

    assert progress.saves == frozenset({"ch1"})
    assert progress.seeds == frozenset({"ch2a"})
    assert progress.found["ch1"] == frozenset({"e_x"})
    assert progress.found["ch3"] == frozenset()
    assert set(progress.activity) == {"ch1", "ch2a"}


_ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?\+00:00$")


def test_progress_activity_timestamps_share_one_iso_format(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    """activity is compared as a string by SagaGraph.default_chapter, so a save's
    timestamp and a seed's timestamp must be the same ISO-8601 UTC format."""
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    sm.write(SaveState(story_id="ch1", current_node="start"))
    sm.write_handoff(HandoffRecord(story_id="ch2a", from_story="ch1"))

    progress = _build_progress(_collect_chapter_infos(demo_saga.values()), sm, gm)

    for stamp in progress.activity.values():
        assert _ISO_UTC.match(stamp), stamp
        assert datetime.fromisoformat(stamp).utcoffset() == timedelta(0)


def _set_stamp(path: Path, stamp: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["timestamp"] = stamp
    path.write_text(json.dumps(data), encoding="utf-8")


def test_progress_activity_string_order_is_time_order_across_saves_and_seeds(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    graph = _graph(demo_saga.values())
    saga = graph.sagas["demo"]
    sm.write(SaveState(story_id="ch1", current_node="start"))
    sm.write_handoff(HandoffRecord(story_id="ch2a", from_story="ch1"))
    infos = _collect_chapter_infos(demo_saga.values())

    _set_stamp(sm.save_path("ch1"), "2026-09-20T10:00:00.250000+00:00")
    _set_stamp(sm.handoff_path("ch2a"), "2026-09-20T10:00:00.500000+00:00")
    assert graph.default_chapter(saga, _build_progress(infos, sm, gm)) == "ch2a"

    _set_stamp(sm.save_path("ch1"), "2026-09-20T10:00:01+00:00")  # no fractional part
    assert graph.default_chapter(saga, _build_progress(infos, sm, gm)) == "ch1"


def test_build_progress_tolerates_an_unreadable_save(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    sm.save_path("ch1").write_text("{not json", encoding="utf-8")

    progress = _build_progress(_collect_chapter_infos(demo_saga.values()), sm, gm)

    assert progress.saves == frozenset({"ch1"})
    assert progress.activity["ch1"] == ""


# ---------------------------------------------------------------------------
# Composed fresh-run provider
# ---------------------------------------------------------------------------

def _provider(path: Path, graph: SagaGraph, sm: SaveManager, display, seed_override=None):
    story = StoryLoader.load(path)
    return _saga_fresh_run_state(story, graph, sm, display, "Felix", seed_override)


def test_provider_defaults_to_settings_name(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    display = MagicMock()
    provider = _provider(demo_saga["ch1"], _graph(demo_saga.values()), SaveManager(saves_dir), display)
    assert provider() == {"player_name": "Felix"}
    display.prompt_replay_confirm.assert_not_called()


def test_provider_returns_persisted_seed_and_skips_name_prompt(make_chapter, saves_dir: Path) -> None:
    n1 = make_chapter("n1", {"e": {"next_story": "n2"}}, saga_id="n", saga_title="N", name_prompt="Who?")
    n2 = make_chapter("n2", {"e": {}}, saga_id="n", name_prompt="Who?")
    sm = SaveManager(saves_dir)
    sm.write_handoff(HandoffRecord(story_id="n2", from_story="n1", state={"trust": 3, "player_name": "Casey"}))
    display = MagicMock()

    assert _provider(n2, _graph([n1, n2]), sm, display)() == {"trust": 3, "player_name": "Casey"}
    display.prompt_protagonist_name.assert_not_called()


def test_provider_runs_the_name_prompt_for_an_unseeded_chapter(make_chapter, saves_dir: Path) -> None:
    n1 = make_chapter("n1", {"e": {"next_story": "n2"}}, saga_id="n", saga_title="N", name_prompt="Who?")
    n2 = make_chapter("n2", {"e": {}}, saga_id="n")
    display = MagicMock()
    display.prompt_protagonist_name.return_value = "Ash"

    assert _provider(n1, _graph([n1, n2]), SaveManager(saves_dir), display)() == {"player_name": "Ash"}


def test_provider_declined_confirm_aborts_and_touches_nothing(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    sm.write(SaveState(story_id="ch2a", current_node="start", state={"trust": 2}))
    sm.write_handoff(HandoffRecord(story_id="ch3", from_story="ch2a", state={"trust": 2}))
    sm.write_handoff(HandoffRecord(story_id="ch1", from_story="x", state={"player_name": "Own"}))
    display = MagicMock()
    display.prompt_replay_confirm.return_value = False

    assert _provider(demo_saga["ch1"], _graph(demo_saga.values()), sm, display)() is None

    display.prompt_replay_confirm.assert_called_once_with(["2A — ch2a", "ch3"])
    display.prompt_protagonist_name.assert_not_called()
    assert sm.has_save("ch2a") is True
    assert sm.load("ch2a").state == {"trust": 2}
    assert sm.load_handoff("ch3").state == {"trust": 2}
    assert sm.load_handoff("ch1").state == {"player_name": "Own"}


def test_provider_confirmed_erases_downstream_but_keeps_own_seed(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    sm.write(SaveState(story_id="ch2a", current_node="start"))
    sm.write_handoff(HandoffRecord(story_id="ch3", from_story="ch2a"))
    sm.write_handoff(HandoffRecord(story_id="ch1", from_story="x", state={"player_name": "Own"}))
    gm.record_ending("ch2a", "e_go")
    gm.record_ending("ch3", "e_win")
    display = MagicMock()
    display.prompt_replay_confirm.return_value = True

    assert _provider(demo_saga["ch1"], _graph(demo_saga.values()), sm, display)() == {"player_name": "Own"}

    assert sm.has_save("ch2a") is False
    assert sm.has_handoff("ch3") is False
    assert sm.has_handoff("ch1") is True
    assert gm.get_found("ch2a") == {"e_go"}  # galleries are never touched
    assert gm.get_found("ch3") == {"e_win"}


def test_provider_does_not_touch_sibling_or_upstream_chapters(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    """Restarting ch2a erases only ch3; the sibling ch2b and the parent ch1 are not downstream."""
    sm = SaveManager(saves_dir)
    sm.write(SaveState(story_id="ch1", current_node="start"))
    sm.write(SaveState(story_id="ch2b", current_node="start"))
    sm.write_handoff(HandoffRecord(story_id="ch3", from_story="ch2a"))
    display = MagicMock()
    display.prompt_replay_confirm.return_value = True

    _provider(demo_saga["ch2a"], _graph(demo_saga.values()), sm, display)()

    display.prompt_replay_confirm.assert_called_once_with(["ch3"])
    assert sm.has_save("ch1") is True
    assert sm.has_save("ch2b") is True
    assert sm.has_handoff("ch3") is False


def _three_chain(make_chapter) -> tuple[Path, Path, Path]:
    p1 = make_chapter("p1", {"e": {"next_story": "p2"}}, saga_id="p", saga_title="P", name_prompt="Who?")
    p2 = make_chapter("p2", {"e": {"next_story": "p3"}}, saga_id="p")
    p3 = make_chapter("p3", {"e": {}}, saga_id="p")
    return p1, p2, p3


def test_provider_name_prompt_abort_erases_nothing(make_chapter, saves_dir: Path) -> None:
    p1, p2, p3 = _three_chain(make_chapter)
    sm = SaveManager(saves_dir)
    sm.write(SaveState(story_id="p2", current_node="start", state={"k": 1}))
    sm.write_handoff(HandoffRecord(story_id="p3", from_story="p2", state={"k": 2}))
    display = MagicMock()
    display.prompt_replay_confirm.return_value = True
    display.prompt_protagonist_name.return_value = None  # player pressed Q

    assert _provider(p1, _graph([p1, p2, p3]), sm, display)() is None

    display.prompt_replay_confirm.assert_called_once_with(["p2", "p3"])
    # confirm said yes, but nothing is erased until a seed exists
    assert sm.load("p2").state == {"k": 1}
    assert sm.load_handoff("p3").state == {"k": 2}


def test_provider_unresolvable_name_aborts_and_erases_nothing(make_chapter, saves_dir: Path) -> None:
    p1, p2, p3 = _three_chain(make_chapter)
    sm = SaveManager(saves_dir)
    sm.write(SaveState(story_id="p2", current_node="start"))
    sm.write_handoff(HandoffRecord(story_id="p3", from_story="p2"))
    display = MagicMock()
    display.prompt_replay_confirm.return_value = True
    display.prompt_protagonist_name.return_value = ""  # submitted empty; no settings/default name

    provider = _saga_fresh_run_state(StoryLoader.load(p1), _graph([p1, p2, p3]), sm, display, "", None)

    assert provider() is None
    display.show_name_required.assert_called_once_with()
    assert sm.has_save("p2") is True
    assert sm.has_handoff("p3") is True


def test_provider_erases_only_after_the_name_prompt_has_returned(make_chapter, saves_dir: Path) -> None:
    """Pins erase-LAST: at the moment the name prompt runs, the downstream progress is still on disk."""
    p1, p2, p3 = _three_chain(make_chapter)
    sm = SaveManager(saves_dir)
    sm.write(SaveState(story_id="p2", current_node="start", state={"k": 1}))
    sm.write_handoff(HandoffRecord(story_id="p3", from_story="p2", state={"k": 2}))
    display = MagicMock()
    display.prompt_replay_confirm.return_value = True
    observed: dict = {}

    def prompt(text, prefill=""):
        observed["save"] = sm.has_save("p2")
        observed["seed"] = sm.load_handoff("p3")
        return "Ash"

    display.prompt_protagonist_name.side_effect = prompt

    assert _provider(p1, _graph([p1, p2, p3]), sm, display)() == {"player_name": "Ash"}

    assert observed["save"] is True
    assert observed["seed"] is not None and observed["seed"].state == {"k": 2}
    assert sm.has_save("p2") is False  # ...and it is gone once the provider has returned
    assert sm.has_handoff("p3") is False


class _RecordingSaves(SaveManager):
    """SaveManager that logs every mutation and every read of the given chapter's own seed."""

    def __init__(self, saves_dir: Path, log: list) -> None:
        super().__init__(saves_dir)
        self.log = log

    def load_handoff(self, story_id: str):
        self.log.append(("load_handoff", story_id))
        return super().load_handoff(story_id)

    def delete(self, story_id: str) -> None:
        self.log.append(("delete", story_id))
        super().delete(story_id)

    def delete_handoff(self, story_id: str) -> None:
        self.log.append(("delete_handoff", story_id))
        super().delete_handoff(story_id)


def _ops(log: list, *kinds: str) -> list:
    return [entry for entry in log if entry[0] in kinds]


def test_provider_operation_order_is_confirm_then_seed_then_erase_with_a_seeded_chapter(
    make_chapter, saves_dir: Path
) -> None:
    p1, p2, p3 = _three_chain(make_chapter)
    log: list = []
    sm = _RecordingSaves(saves_dir, log)
    sm.write(SaveState(story_id="p2", current_node="start"))
    sm.write_handoff(HandoffRecord(story_id="p3", from_story="p2"))
    sm.write_handoff(HandoffRecord(story_id="p1", from_story="x", state={"player_name": "Own"}))
    display = MagicMock()
    display.prompt_replay_confirm.side_effect = lambda titles: log.append(("confirm", None)) or True

    _provider(p1, _graph([p1, p2, p3]), sm, display)()

    confirm_at = log.index(("confirm", None))
    own_seed_at = max(i for i, e in enumerate(log) if e == ("load_handoff", "p1"))
    first_erase_at = min(i for i, e in enumerate(log) if e[0] in ("delete", "delete_handoff"))
    assert confirm_at < own_seed_at < first_erase_at
    assert ("delete_handoff", "p1") not in log  # the chapter's own seed is never erased
    assert ("delete", "p1") not in log
    assert sorted(_ops(log, "delete", "delete_handoff")) == [
        ("delete", "p2"), ("delete", "p3"), ("delete_handoff", "p2"), ("delete_handoff", "p3"),
    ]


def test_provider_operation_order_is_confirm_then_name_prompt_then_erase(
    make_chapter, saves_dir: Path
) -> None:
    p1, p2, p3 = _three_chain(make_chapter)
    log: list = []
    sm = _RecordingSaves(saves_dir, log)
    sm.write(SaveState(story_id="p2", current_node="start"))
    display = MagicMock()
    display.prompt_replay_confirm.side_effect = lambda titles: log.append(("confirm", None)) or True
    display.prompt_protagonist_name.side_effect = lambda *a, **k: log.append(("name", None)) or "Ash"

    _provider(p1, _graph([p1, p2, p3]), sm, display)()

    first_erase_at = min(i for i, e in enumerate(log) if e[0] in ("delete", "delete_handoff"))
    assert log.index(("confirm", None)) < log.index(("name", None)) < first_erase_at


def test_provider_seed_override_applies_to_cold_starts_only(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    graph = _graph(demo_saga.values())
    display = MagicMock()

    cold = _provider(demo_saga["ch1"], graph, sm, display, seed_override={"trust": 9})()
    assert cold == {"player_name": "Felix", "trust": 9}

    sm.write_handoff(HandoffRecord(story_id="ch2a", from_story="ch1", state={"trust": 1, "player_name": "Casey"}))
    seeded = _provider(demo_saga["ch2a"], graph, sm, display, seed_override={"trust": 9})()
    assert seeded == {"trust": 1, "player_name": "Casey"}
    assert sm.load_handoff("ch2a").state == {"trust": 1, "player_name": "Casey"}  # never persisted


def test_provider_seed_override_is_never_persisted(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    _provider(demo_saga["ch1"], _graph(demo_saga.values()), sm, MagicMock(), seed_override={"trust": 9})()
    assert list(saves_dir.iterdir()) == []


def test_provider_seed_override_overlays_the_name_prompt_result(make_chapter, saves_dir: Path) -> None:
    n1 = make_chapter("n1", {"e": {"next_story": "n2"}}, saga_id="n", saga_title="N", name_prompt="Who?")
    n2 = make_chapter("n2", {"e": {}}, saga_id="n")
    display = MagicMock()
    display.prompt_protagonist_name.return_value = "Ash"

    result = _provider(n1, _graph([n1, n2]), SaveManager(saves_dir), display, seed_override={"trust": 2})()

    assert result == {"player_name": "Ash", "trust": 2}


# ---------------------------------------------------------------------------
# _launch_story / _play_chapter
# ---------------------------------------------------------------------------

def test_launch_story_wires_the_saga_provider_and_returns_the_chain_result(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    graph = _graph(demo_saga.values())
    chain = ChainResult(next_story="ch2a", from_story="ch1")

    with patch("main.Engine") as engine_cls, patch("main.load_settings", return_value={"player_name": "Felix"}):
        engine_cls.return_value.run.return_value = chain
        result = _launch_story(
            demo_saga["ch1"], {}, SaveManager(saves_dir), GalleryManager(saves_dir), MagicMock(), graph=graph
        )

    assert result == chain
    kwargs = engine_cls.call_args.kwargs
    assert kwargs["known_chapter_ids"] == graph.known_ids
    assert kwargs["fresh_run_state"]() == {"player_name": "Felix"}


def test_launch_story_returns_none_when_engine_returns_none(valid_story_path: Path, saves_dir: Path) -> None:
    with patch("main.Engine") as engine_cls, patch("main.load_settings", return_value={"player_name": "Felix"}):
        engine_cls.return_value.run.return_value = None
        assert _launch_story(
            valid_story_path, {}, SaveManager(saves_dir), GalleryManager(saves_dir), MagicMock()
        ) is None


def test_launch_story_without_a_graph_keeps_todays_behaviour_for_a_saga_chapter(
    make_chapter, saves_dir: Path
) -> None:
    """No graph -> no saga provider: a name_prompt chapter gets the plain name-prompt provider."""
    path = make_chapter("solo", {"e": {}}, saga_id="s", saga_title="S", name_prompt="Who?")
    display = MagicMock()
    display.prompt_protagonist_name.return_value = "Ash"

    with patch("main.Engine") as engine_cls, patch("main.load_settings", return_value={"player_name": "Felix"}):
        engine_cls.return_value.run.return_value = None
        _launch_story(path, {}, SaveManager(saves_dir), GalleryManager(saves_dir), display)

    kwargs = engine_cls.call_args.kwargs
    assert kwargs["fresh_run_state"]() == {"player_name": "Ash"}
    display.prompt_replay_confirm.assert_not_called()
    assert not kwargs["known_chapter_ids"]


def test_launch_story_saga_chapter_without_name_prompt_still_gets_a_provider(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    with patch("main.Engine") as engine_cls, patch("main.load_settings", return_value={"player_name": "Felix"}):
        engine_cls.return_value.run.return_value = None
        _launch_story(
            demo_saga["ch3"], {}, SaveManager(saves_dir), GalleryManager(saves_dir), MagicMock(),
            graph=_graph(demo_saga.values()),
        )
    assert engine_cls.call_args.kwargs["fresh_run_state"] is not None


def test_launch_story_shows_content_warnings_and_can_back_out(
    make_chapter, tmp_path: Path, saves_dir: Path
) -> None:
    path = make_chapter("warn", {"e": {}}, saga_id="s", saga_title="S")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["meta"]["warnings"] = ["Spoilers"]
    path.write_text(json.dumps(data), encoding="utf-8")
    display = MagicMock()
    display.show_content_warnings.return_value = False

    with patch("main.Engine") as engine_cls:
        result = _launch_story(
            path, {}, SaveManager(saves_dir), GalleryManager(saves_dir), display,
            graph=_graph([path]),
        )

    assert result is None
    display.show_content_warnings.assert_called_once()
    engine_cls.assert_not_called()


def test_play_chapter_follows_the_chain_until_it_ends(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    graph = _graph(demo_saga.values())
    results = [ChainResult("ch2a", "ch1"), ChainResult("ch3", "ch2a"), None]
    display = MagicMock()
    with patch("main._launch_story", side_effect=results) as launch:
        _play_chapter(
            demo_saga["ch1"], {}, SaveManager(saves_dir), GalleryManager(saves_dir), display,
            graph=graph, seed_override=None,
        )
    assert [c.args[0] for c in launch.call_args_list] == [demo_saga["ch1"], demo_saga["ch2a"], demo_saga["ch3"]]
    assert display.clear_screen.call_count == 2  # once before each chained chapter


def test_play_chapter_passes_graph_and_seed_override_to_every_launch(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    graph = _graph(demo_saga.values())
    override = {"trust": 4}
    with patch("main._launch_story", side_effect=[ChainResult("ch2b", "ch1"), None]) as launch:
        _play_chapter(
            demo_saga["ch1"], {}, SaveManager(saves_dir), GalleryManager(saves_dir), MagicMock(),
            graph=graph, seed_override=override,
        )
    for call in launch.call_args_list:
        assert call.kwargs == {"graph": graph, "seed_override": override}


def test_play_chapter_stops_on_an_unknown_next_story(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    graph = _graph(demo_saga.values())
    with patch("main._launch_story", side_effect=[ChainResult("ghost", "ch1")]) as launch:
        _play_chapter(
            demo_saga["ch1"], {}, SaveManager(saves_dir), GalleryManager(saves_dir), MagicMock(),
            graph=graph, seed_override=None,
        )
    assert launch.call_count == 1


def test_play_chapter_end_to_end_with_the_real_engine(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    graph = _graph(demo_saga.values())
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    display = MagicMock()
    display.prompt_choice.return_value = 1
    display.prompt_chapter_transition.return_value = "continue"
    display.prompt_play_again.return_value = False

    with patch("main.load_settings", return_value={"player_name": "Felix"}):
        _play_chapter(demo_saga["ch1"], {}, sm, gm, display, graph=graph, seed_override=None)

    assert gm.get_found("ch1") == {"e_a"}
    assert gm.get_found("ch2a") == {"e_go"}
    assert gm.get_found("ch3") == {"e_win"}
    assert sm.load_handoff("ch3").state == {"trust": 3, "player_name": "Felix"}
    display.prompt_replay_confirm.assert_not_called()


def test_replaying_the_entry_chapter_declined_leaves_all_progress_on_disk(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    """Whole-path pin: a real Engine restart over a saved chapter, declined at the confirm."""
    graph = _graph(demo_saga.values())
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    sm.write(SaveState(story_id="ch1", current_node="start"))
    sm.write(SaveState(story_id="ch2a", current_node="start", state={"trust": 3}))
    sm.write_handoff(HandoffRecord(story_id="ch3", from_story="ch2a", state={"trust": 3}))
    display = MagicMock()
    display.prompt_continue_or_new.return_value = False  # choose "New game" at the resume prompt
    display.prompt_replay_confirm.return_value = False

    with patch("main.load_settings", return_value={"player_name": "Felix"}):
        _play_chapter(demo_saga["ch1"], {}, sm, gm, display, graph=graph, seed_override=None)

    display.prompt_replay_confirm.assert_called_once_with(["2A — ch2a", "ch3"])
    assert sm.load("ch2a").state == {"trust": 3}
    assert sm.load_handoff("ch3").state == {"trust": 3}
    assert sm.has_save("ch1") is True
