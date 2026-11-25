import json
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import main as main_module
from main import (
    _build_entries,
    _build_progress,
    _build_top_level_entries,
    _collect_chapter_infos,
    _home_row,
    _launch_story,
    _load_story_info,
    _open_entry,
    _parse_args,
    _parse_seed_override,
    _play_chapter,
    _prompt_name_state,
    _resolve_player_name,
    _run_folder_picker,
    _run_saga_home,
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
        engine_cls.return_value.run.return_value = None
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
        engine_cls.return_value.run.return_value = None
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


def _unreadable_files(directory: Path) -> list[Path]:
    """A non-UTF-8 file and a 'file' that cannot be read at all (a directory named *.json)."""
    directory.mkdir(parents=True, exist_ok=True)
    mojibake = directory / "mojibake.json"
    mojibake.write_bytes(b'{"meta": {"id": "cafe"}}' + bytes([0xFF, 0xFE]))
    unreadable = directory / "unreadable.json"
    unreadable.mkdir()
    return [mojibake, unreadable]


def test_collect_chapter_infos_tolerates_undecodable_and_unreadable_files(
    demo_saga: dict[str, Path], tmp_path: Path
) -> None:
    bad = _unreadable_files(tmp_path / "bad")
    infos = _collect_chapter_infos([bad[0], demo_saga["ch1"], bad[1]])
    assert [i.story_id for i in infos] == ["ch1"]  # a file that cannot be read is treated as absent


def test_top_level_picker_refresh_survives_unreadable_files_in_a_folder(
    demo_saga: dict[str, Path], tmp_path: Path, saves_dir: Path
) -> None:
    stories = _stage_stories(tmp_path, demo_saga.values(), folder="horror")
    _unreadable_files(stories / "horror")
    root_paths, folders = StoryLoader.discover_with_folders(stories)
    all_paths = root_paths + [p for paths in folders.values() for p in paths]

    chapters = _collect_chapter_infos(all_paths)
    graph = SagaGraph.build(chapters)
    entries = _build_top_level_entries(
        root_paths, folders, {}, SaveManager(saves_dir), GalleryManager(saves_dir), graph,
        _build_progress(chapters, SaveManager(saves_dir), GalleryManager(saves_dir)), chapters,
    )

    assert [e["type"] for e in entries] == ["folder"]  # ch2a..ch3 are hidden in the saga row's folder
    assert sorted(i.story_id for i in chapters) == ["ch1", "ch2a", "ch2b", "ch3"]
    assert graph.sagas["demo"].problems == ()


def test_main_still_lists_the_good_stories_when_a_folder_holds_unreadable_files(
    demo_saga: dict[str, Path], valid_story_path: Path, tmp_path: Path, saves_dir: Path
) -> None:
    stories = _stage_stories(tmp_path, [valid_story_path])
    horror = stories / "horror"
    horror.mkdir()
    shutil.copy(demo_saga["ch1"], horror / "ch1.json")
    _unreadable_files(horror)

    display, _cls, _engine = _drive_main([], stories, saves_dir, story_select=[None])

    entries = display.show_story_picker.call_args_list[0].args[0]
    assert [(e["type"], e["label"]) for e in entries] == [("story", "Test Story"), ("folder", "horror")]


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


class _FailingSaves(SaveManager):
    """SaveManager whose delete / delete_handoff raise PermissionError for one (operation, chapter)."""

    def __init__(self, saves_dir: Path, op: str, story_id: str) -> None:
        super().__init__(saves_dir)
        self._op = op
        self._story_id = story_id

    def delete(self, story_id: str) -> None:
        if (self._op, story_id) == ("delete", self._story_id):
            raise PermissionError("locked")
        super().delete(story_id)

    def delete_handoff(self, story_id: str) -> None:
        if (self._op, story_id) == ("delete_handoff", self._story_id):
            raise PermissionError("locked")
        super().delete_handoff(story_id)


@pytest.mark.parametrize("op", ["delete", "delete_handoff"])
@pytest.mark.parametrize("failing", ["ch2a", "ch2b"])
def test_provider_erase_is_best_effort_when_a_downstream_delete_fails(
    demo_saga: dict[str, Path], saves_dir: Path, op: str, failing: str
) -> None:
    """An OSError on one downstream file must not abort the run or stop the remaining erasures."""
    sm = _FailingSaves(saves_dir, op, failing)
    for cid in ("ch2a", "ch2b", "ch3"):
        sm.write(SaveState(story_id=cid, current_node="start"))
        sm.write_handoff(HandoffRecord(story_id=cid, from_story="x", state={"k": 1}))
    sm.write_handoff(HandoffRecord(story_id="ch1", from_story="x", state={"player_name": "Own"}))
    display = MagicMock()
    display.prompt_replay_confirm.return_value = True

    seed = _provider(demo_saga["ch1"], _graph(demo_saga.values()), sm, display)()

    assert seed == {"player_name": "Own"}
    for cid in ("ch2a", "ch2b", "ch3"):
        assert sm.save_path(cid).exists() is ((op, cid) == ("delete", failing))
        assert sm.handoff_path(cid).exists() is ((op, cid) == ("delete_handoff", failing))
    assert sm.has_handoff("ch1") is True  # the chapter's own seed is never touched


def test_provider_erase_does_not_swallow_non_oserrors(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    sm.write(SaveState(story_id="ch2a", current_node="start"))
    display = MagicMock()
    display.prompt_replay_confirm.return_value = True

    with patch.object(SaveManager, "delete", side_effect=RuntimeError("bug")):
        with pytest.raises(RuntimeError):
            _provider(demo_saga["ch1"], _graph(demo_saga.values()), sm, display)()


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
        engine_cls.return_value.run.return_value = None
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


def _play_again_at_a_plain_ending(demo_saga: dict[str, Path], saves_dir: Path, confirm: bool):
    """Real Engine: reach ch1's plain ending, and only THEN put progress downstream and press Play again."""
    graph = _graph(demo_saga.values())
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    display = MagicMock()
    display.prompt_choice.return_value = 3  # ch1: go e_a / go e_b / go e_x  ->  the plain dead end
    display.prompt_replay_confirm.return_value = confirm
    answers = iter([True, False])
    asked: list[bool] = []

    def play_again() -> bool:
        if not asked:  # first ending only: downstream progress appears now
            sm.write(SaveState(story_id="ch2a", current_node="start", state={"trust": 3}))
            sm.write_handoff(HandoffRecord(story_id="ch3", from_story="ch2a", state={"trust": 3}))
        asked.append(True)
        return next(answers)

    display.prompt_play_again.side_effect = play_again
    with patch("main.load_settings", return_value={"player_name": "Felix"}):
        _play_chapter(demo_saga["ch1"], {}, sm, gm, display, graph=graph, seed_override=None)
    return display, sm, gm


def test_play_again_with_downstream_progress_confirms_and_erases_it_when_accepted(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    display, sm, gm = _play_again_at_a_plain_ending(demo_saga, saves_dir, confirm=True)

    display.prompt_replay_confirm.assert_called_once_with(["2A — ch2a", "ch3"])
    assert sm.has_save("ch2a") is False
    assert sm.has_handoff("ch3") is False
    starts = [c for c in display.show_node.call_args_list if c.args[1] == ["ch1 begins."]]
    assert len(starts) == 2  # the run restarted
    assert display.prompt_play_again.call_count == 2
    assert gm.get_found("ch1") == {"e_x"}


def test_play_again_with_downstream_progress_leaves_it_alone_when_declined(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    display, sm, _gm = _play_again_at_a_plain_ending(demo_saga, saves_dir, confirm=False)

    display.prompt_replay_confirm.assert_called_once_with(["2A — ch2a", "ch3"])
    assert sm.load("ch2a").state == {"trust": 3}
    assert sm.load_handoff("ch3").state == {"trust": 3}
    starts = [c for c in display.show_node.call_args_list if c.args[1] == ["ch1 begins."]]
    assert len(starts) == 1  # the run did not restart: it returned to the caller
    assert display.prompt_play_again.call_count == 1


# ---------------------------------------------------------------------------
# Saga rows in the picker
# ---------------------------------------------------------------------------

def _picker_state(paths, saves_dir: Path):
    infos = _collect_chapter_infos(list(paths))
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    return SagaGraph.build(infos), _build_progress(infos, sm, gm), sm, gm


def test_build_entries_collapses_a_saga_into_one_row(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    graph, progress, sm, gm = _picker_state(demo_saga.values(), saves_dir)
    entries = _build_entries(list(demo_saga.values()), {}, sm, gm, graph, progress)

    assert len(entries) == 1
    row = entries[0]
    assert (row["type"], row["label"], row["index"]) == ("saga", "Demo Saga", 1)
    assert row["path"] == demo_saga["ch1"]
    assert (row["chapters_reached"], row["chapters_total"]) == (1, 4)
    assert (row["endings_found"], row["endings_total"]) == (0, 7)
    assert row["complete"] is False
    assert row["more_coming"] is False
    assert row["error"] is False
    assert row["has_save"] is False
    assert row["author"] == "Tester"


def test_build_entries_mixes_saga_and_plain_stories(
    valid_story_path: Path, demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    paths = [valid_story_path, *demo_saga.values()]
    graph, progress, sm, gm = _picker_state(paths, saves_dir)
    entries = _build_entries(paths, {}, sm, gm, graph, progress)

    assert [e["index"] for e in entries] == [1, 2]
    assert entries[0]["path"] == valid_story_path
    assert entries[0]["label"] == "Test Story"
    assert entries[1]["type"] == "saga"


def test_saga_row_reflects_progress(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    sm.write(SaveState(story_id="ch2a", current_node="start"))
    sm.write_handoff(HandoffRecord(story_id="ch3", from_story="ch2a"))
    gm.record_ending("ch3", "e_win")
    infos = _collect_chapter_infos(demo_saga.values())
    graph, progress = SagaGraph.build(infos), _build_progress(infos, sm, gm)

    row = _build_entries(list(demo_saga.values()), {}, sm, gm, graph, progress)[0]

    assert row["chapters_reached"] == 3  # ch1 (entry), ch2a (save), ch3 (seed)
    assert row["complete"] is True
    assert row["has_save"] is True
    assert row["endings_found"] == 1


def test_saga_row_is_an_error_row_when_the_graph_has_problems(make_chapter, saves_dir: Path) -> None:
    a = make_chapter("a", {"e": {}}, saga_id="s", saga_title="S")
    b = make_chapter("b", {"e": {}}, saga_id="s")  # nothing chains into either: two entry chapters
    graph, progress, sm, gm = _picker_state([a, b], saves_dir)

    row = _build_entries([a, b], {}, sm, gm, graph, progress)[0]

    assert row["error"] is True
    assert "multiple entry chapters" in row["problems"][0]


def test_saga_with_no_entry_chapter_still_yields_one_error_row(make_chapter, saves_dir: Path) -> None:
    """A cycle leaves the saga without an entry chapter; the row must anchor somewhere anyway."""
    a = make_chapter("a", {"e": {"next_story": "b"}}, saga_id="s", saga_title="S")
    b = make_chapter("b", {"e": {"next_story": "a"}}, saga_id="s")
    graph, progress, sm, gm = _picker_state([a, b], saves_dir)

    entries = _build_entries([a, b], {}, sm, gm, graph, progress)

    assert len(entries) == 1
    assert entries[0]["error"] is True
    assert any("cycle" in problem for problem in entries[0]["problems"])


def test_top_level_entries_count_a_saga_once_and_skip_folders_with_nothing_visible(
    valid_story_path: Path, demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    graph, progress, sm, gm = _picker_state(demo_saga.values(), saves_dir)
    folders = {"sagas": list(demo_saga.values()), "only_hidden": [demo_saga["ch2a"], demo_saga["ch2b"]]}

    entries = _build_top_level_entries([valid_story_path], folders, {}, sm, gm, graph, progress)

    assert [e.get("type") for e in entries] == ["story", "folder"]
    folder = entries[1]
    assert (folder["label"], folder["story_count"], folder["index"]) == ("sagas", 1, 2)


def test_build_entries_error_story_carries_its_path(tmp_path: Path, saves_dir: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("bad json", encoding="utf-8")
    entries = _build_entries([path], {path: "parse error"}, SaveManager(saves_dir), GalleryManager(saves_dir))
    assert entries[0]["path"] == path


def test_a_chapter_that_fails_to_load_is_treated_as_absent(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    """Spec 7.3: the picker refresh must not crash, and the parent's link reads as dangling."""
    demo_saga["ch2a"].write_text("{ not json", encoding="utf-8")
    paths = list(demo_saga.values())
    graph, progress, sm, gm = _picker_state(paths, saves_dir)

    assert "ch2a" not in graph.known_ids
    entries = _build_top_level_entries(paths, {}, {}, sm, gm, graph, progress)

    saga_rows = [e for e in entries if e.get("type") == "saga"]
    assert len(saga_rows) == 1
    assert saga_rows[0]["error"] is False
    assert saga_rows[0]["chapters_total"] == 3
    assert saga_rows[0]["more_coming"] is True
    # The broken file is not a known chapter, so it stays an ordinary (broken) story row.
    assert [e["label"] for e in entries if e.get("type") != "saga"] == ["ch2a"]


def test_a_chapter_that_fails_to_load_does_not_break_the_home_screen(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    demo_saga["ch2a"].write_text("{ not json", encoding="utf-8")
    graph, _progress, sm, gm = _picker_state(demo_saga.values(), saves_dir)
    display = MagicMock()
    display.prompt_saga_select.side_effect = ["back"]

    _run_saga_home(graph.sagas["demo"], graph, {}, sm, gm, display, debug=True)

    _title, rows, more = display.show_saga_home.call_args.args
    assert [r["label"] for r in rows] == ["ch1", "2B — ch2b", "ch3"]
    assert more is False


# ---------------------------------------------------------------------------
# Progress snapshot on odd save data (the picker rebuilds it on every refresh)
# ---------------------------------------------------------------------------

def test_build_progress_survives_null_timestamps_in_saves_and_seeds(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    """A hand-edited "timestamp": null must not crash max() or default_chapter's comparison."""
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    sm.write(SaveState(story_id="ch1", current_node="start"))
    sm.write(SaveState(story_id="ch2a", current_node="start"))
    sm.write_handoff(HandoffRecord(story_id="ch2a", from_story="ch1"))  # save AND seed on one chapter
    sm.write_handoff(HandoffRecord(story_id="ch3", from_story="ch2a"))
    for path in (sm.save_path("ch1"), sm.save_path("ch2a"), sm.handoff_path("ch2a"), sm.handoff_path("ch3")):
        _set_stamp(path, None)
    infos = _collect_chapter_infos(demo_saga.values())

    progress = _build_progress(infos, sm, gm)

    assert set(progress.activity) == {"ch1", "ch2a", "ch3"}
    assert all(isinstance(stamp, str) for stamp in progress.activity.values())
    graph = SagaGraph.build(infos)
    assert graph.default_chapter(graph.sagas["demo"], progress) in {"ch1", "ch2a", "ch3"}


def test_null_timestamp_loses_to_a_real_one(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    sm.write(SaveState(story_id="ch2a", current_node="start"))
    sm.write_handoff(HandoffRecord(story_id="ch2a", from_story="ch1"))
    sm.write_handoff(HandoffRecord(story_id="ch2b", from_story="ch1"))
    _set_stamp(sm.save_path("ch2a"), None)
    _set_stamp(sm.handoff_path("ch2a"), "2026-09-20T10:00:00+00:00")
    _set_stamp(sm.handoff_path("ch2b"), "2026-09-20T11:00:00+00:00")
    infos = _collect_chapter_infos(demo_saga.values())

    progress = _build_progress(infos, sm, gm)

    assert progress.activity["ch2a"] == "2026-09-20T10:00:00+00:00"
    graph = SagaGraph.build(infos)
    assert graph.default_chapter(graph.sagas["demo"], progress) == "ch2b"

    _set_stamp(sm.handoff_path("ch2a"), None)  # now ch2a has nothing real: it must rank below ch2b
    assert graph.default_chapter(graph.sagas["demo"], _build_progress(infos, sm, gm)) == "ch2b"


@pytest.mark.parametrize("body", ['{"endings_found": null}', "[]", "not json"])
def test_build_progress_tolerates_an_odd_gallery_file(
    demo_saga: dict[str, Path], saves_dir: Path, body: str
) -> None:
    (saves_dir / "ch1.gallery.json").write_text(body, encoding="utf-8")
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)

    progress = _build_progress(_collect_chapter_infos(demo_saga.values()), sm, gm)

    assert progress.found["ch1"] == frozenset()


# ---------------------------------------------------------------------------
# Folder picker returns the chosen entry
# ---------------------------------------------------------------------------

def _folder_display(selections, page_size: int = 5) -> MagicMock:
    display = MagicMock()
    display.get_page_size.return_value = page_size
    display.prompt_story_select.side_effect = list(selections)
    return display


def test_folder_picker_returns_the_chosen_entry_not_a_path_by_position(
    valid_story_path: Path, demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    """Row 2 is the plain story; paths[1] is a saga chapter, so positional mapping would pick wrong."""
    paths = [demo_saga["ch2a"], demo_saga["ch1"], demo_saga["ch3"], valid_story_path]
    graph, progress, sm, gm = _picker_state(paths, saves_dir)
    display = _folder_display([2])

    chosen = _run_folder_picker("f", paths, {}, sm, gm, display, graph, progress)

    assert chosen["path"] == valid_story_path
    shown = display.show_story_picker.call_args.args[0]
    assert [(e["index"], e["label"]) for e in shown] == [(1, "Demo Saga"), (2, "Test Story")]


def test_folder_picker_returns_the_saga_entry(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    paths = list(demo_saga.values())
    graph, progress, sm, gm = _picker_state(paths, saves_dir)

    chosen = _run_folder_picker("f", paths, {}, sm, gm, _folder_display([1]), graph, progress)

    assert (chosen["type"], chosen["saga_id"]) == ("saga", "demo")


def test_folder_picker_back_returns_none(valid_story_path: Path, saves_dir: Path) -> None:
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    assert _run_folder_picker("f", [valid_story_path], {}, sm, gm, _folder_display(["back"])) is None


def test_folder_picker_shows_errors_and_keeps_prompting(tmp_path: Path, saves_dir: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("bad json", encoding="utf-8")
    display = _folder_display([1, "back"])
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)

    assert _run_folder_picker("f", [bad], {bad: "boom"}, sm, gm, display) is None

    display.show_picker_error.assert_called_once_with("bad.json", "boom")


def test_folder_picker_shows_saga_problems_and_keeps_prompting(make_chapter, saves_dir: Path) -> None:
    a = make_chapter("a", {"e": {}}, saga_id="s", saga_title="S")
    b = make_chapter("b", {"e": {}}, saga_id="s")
    graph, progress, sm, gm = _picker_state([a, b], saves_dir)
    display = _folder_display([1, "back"])

    assert _run_folder_picker("f", [a, b], {}, sm, gm, display, graph, progress) is None

    label, message = display.show_picker_error.call_args.args
    assert label == "S"
    assert "multiple entry chapters" in message


def test_folder_picker_pages_index_into_the_full_entry_list(
    valid_story_path: Path, demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    paths = [demo_saga["ch1"], demo_saga["ch2a"], valid_story_path]  # saga row, then the plain story
    graph, progress, sm, gm = _picker_state(paths, saves_dir)
    display = _folder_display(["next_page", 1], page_size=1)

    chosen = _run_folder_picker("f", paths, {}, sm, gm, display, graph, progress)

    assert chosen["path"] == valid_story_path
    assert display.show_story_picker.call_args.kwargs["page"] == 1


# ---------------------------------------------------------------------------
# Saga home screen
# ---------------------------------------------------------------------------

def test_home_row_states(demo_saga: dict[str, Path]) -> None:
    from src.saga import SagaProgress
    infos = {i.story_id: i for i in _collect_chapter_infos(demo_saga.values())}
    progress = SagaProgress(
        saves=frozenset({"ch1"}), seeds=frozenset({"ch2a"}),
        found={"ch2b": frozenset({"e_go"})},
    )
    assert _home_row(infos["ch1"], progress)["state"] == "active"
    assert _home_row(infos["ch2a"], progress)["state"] == "ready"
    finished = _home_row(infos["ch2b"], progress)
    assert (finished["state"], finished["endings_found"], finished["endings_total"]) == ("finished", 1, 1)
    assert _home_row(infos["ch3"], progress)["state"] == "new"
    assert _home_row(infos["ch2a"], progress)["label"] == "2A — ch2a"


def test_run_saga_home_lists_reached_chapters_and_plays_the_selection(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    graph, _progress, sm, gm = _picker_state(demo_saga.values(), saves_dir)
    display = MagicMock()
    display.prompt_saga_select.side_effect = [1, "back"]

    with patch("main._play_chapter") as play:
        _run_saga_home(graph.sagas["demo"], graph, {}, sm, gm, display)

    saga_title, rows, more = display.show_saga_home.call_args.args
    assert saga_title == "Demo Saga"
    assert [r["label"] for r in rows] == ["ch1"]
    assert more is True
    play.assert_called_once()
    assert play.call_args.args[0] == demo_saga["ch1"]


def test_run_saga_home_preselects_the_most_recent_active_chapter(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    sm.write(SaveState(story_id="ch2a", current_node="start"))
    graph = SagaGraph.build(_collect_chapter_infos(demo_saga.values()))
    display = MagicMock()
    display.prompt_saga_select.side_effect = ["back"]

    _run_saga_home(graph.sagas["demo"], graph, {}, sm, gm, display)

    assert display.prompt_saga_select.call_args.args == (2, 2)  # two rows, default is row 2


def test_run_saga_home_debug_lists_every_chapter(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    graph, _progress, sm, gm = _picker_state(demo_saga.values(), saves_dir)
    display = MagicMock()
    display.prompt_saga_select.side_effect = ["back"]

    _run_saga_home(graph.sagas["demo"], graph, {}, sm, gm, display, debug=True)

    _title, rows, more = display.show_saga_home.call_args.args
    assert [r["label"] for r in rows] == ["ch1", "2A — ch2a", "2B — ch2b", "ch3"]
    assert more is False


def test_run_saga_home_passes_graph_and_seed_override_to_play_chapter(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    graph, _progress, sm, gm = _picker_state(demo_saga.values(), saves_dir)
    display = MagicMock()
    display.prompt_saga_select.side_effect = [1, "back"]
    override = {"trust": 9}

    with patch("main._play_chapter") as play:
        _run_saga_home(graph.sagas["demo"], graph, {}, sm, gm, display, seed_override=override)

    assert play.call_args.kwargs == {"graph": graph, "seed_override": override}


def test_run_saga_home_rebuilds_progress_after_each_play(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    graph, _progress, sm, gm = _picker_state(demo_saga.values(), saves_dir)
    display = MagicMock()
    display.prompt_saga_select.side_effect = [1, "back"]

    def play(*_args, **_kwargs) -> None:  # playing ch1 chains a seed into ch2a
        sm.write_handoff(HandoffRecord(story_id="ch2a", from_story="ch1"))

    with patch("main._play_chapter", side_effect=play):
        _run_saga_home(graph.sagas["demo"], graph, {}, sm, gm, display)

    first, second = display.show_saga_home.call_args_list
    assert [r["label"] for r in first.args[1]] == ["ch1"]
    assert [(r["label"], r["state"]) for r in second.args[1]] == [("ch1", "new"), ("2A — ch2a", "ready")]


# ---------------------------------------------------------------------------
# Entry dispatch
# ---------------------------------------------------------------------------

def test_open_entry_shows_saga_problems(saves_dir: Path) -> None:
    display = MagicMock()
    entry = {"type": "saga", "saga_id": "s", "label": "S", "error": True, "problems": ["p1", "p2"]}
    _open_entry(entry, SagaGraph.build([]), {}, SaveManager(saves_dir), GalleryManager(saves_dir), display,
                debug=False, seed_override=None)
    display.show_picker_error.assert_called_once_with("S", "p1; p2")


def test_open_entry_plays_a_plain_story(valid_story_path: Path, saves_dir: Path) -> None:
    entry = {"type": "story", "path": valid_story_path, "label": "Test Story", "error": False}
    with patch("main._play_chapter") as play:
        _open_entry(entry, SagaGraph.build([]), {}, SaveManager(saves_dir), GalleryManager(saves_dir),
                    MagicMock(), debug=False, seed_override=None)
    assert play.call_args.args[0] == valid_story_path


def test_open_entry_passes_graph_and_seed_override_for_a_plain_story(
    valid_story_path: Path, saves_dir: Path
) -> None:
    graph, override = SagaGraph.build([]), {"k": 1}
    entry = {"type": "story", "path": valid_story_path, "label": "Test Story", "error": False}
    with patch("main._play_chapter") as play:
        _open_entry(entry, graph, {}, SaveManager(saves_dir), GalleryManager(saves_dir),
                    MagicMock(), debug=True, seed_override=override)
    assert play.call_args.kwargs == {"graph": graph, "seed_override": override}


def test_open_entry_opens_the_home_screen_for_a_saga(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    graph, _progress, sm, gm = _picker_state(demo_saga.values(), saves_dir)
    entry = {"type": "saga", "saga_id": "demo", "label": "Demo Saga", "error": False}
    with patch("main._run_saga_home") as home:
        _open_entry(entry, graph, {}, sm, gm, MagicMock(), debug=True, seed_override={"a": 1})
    assert home.call_args.args[0] is graph.sagas["demo"]
    assert home.call_args.kwargs == {"debug": True, "seed_override": {"a": 1}}


def test_open_entry_on_an_errored_plain_story_reports_via_the_launch_path(tmp_path: Path, saves_dir: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("bad json", encoding="utf-8")
    display = MagicMock()
    entry = {"path": bad, "label": "bad", "error": True}

    _open_entry(entry, SagaGraph.build([]), {bad: "boom"}, SaveManager(saves_dir), GalleryManager(saves_dir),
                display, debug=False, seed_override=None)

    display.show_picker_error.assert_called_once_with("bad.json", "boom")


# ---------------------------------------------------------------------------
# main(): the whole picker -> home -> launch path
# ---------------------------------------------------------------------------

def _stage_stories(tmp_path: Path, paths, folder: str | None = None) -> Path:
    """Copy story files into a fresh stories/ tree (optionally inside a subfolder)."""
    root = tmp_path / "stories"
    target = root / folder if folder else root
    target.mkdir(parents=True)
    for path in paths:
        shutil.copy(path, target / path.name)
    return root


def _drive_main(argv, stories_dir: Path, saves_dir: Path, *, story_select, saga_select=(), replay_confirm=True):
    display = MagicMock()
    display.get_page_size.return_value = 5
    display.prompt_story_select.side_effect = list(story_select)
    display.prompt_saga_select.side_effect = list(saga_select)
    display.prompt_replay_confirm.return_value = replay_confirm
    with patch.object(sys, "argv", ["main.py", *argv]), \
         patch.object(main_module, "STORIES_DIR", stories_dir), \
         patch.object(main_module, "SAVES_DIR", saves_dir), \
         patch("main.Display", return_value=display) as display_cls, \
         patch("main.load_settings", return_value={"player_name": "Felix"}), \
         patch("main.Engine") as engine_cls:
        engine_cls.return_value.run.return_value = None
        main_module.main()
    return display, display_cls, engine_cls


def test_main_bad_seed_errors_out_before_any_screen_is_drawn(tmp_path: Path, saves_dir: Path) -> None:
    stories = _stage_stories(tmp_path, [])
    for argv in (["--seed", "trust=3"], ["--debug", "--seed", "oops"]):  # needs --debug / no '='
        display = MagicMock()
        with patch.object(sys, "argv", ["main.py", *argv]), \
             patch.object(main_module, "STORIES_DIR", stories), \
             patch.object(main_module, "SAVES_DIR", saves_dir), \
             patch("main.Display", return_value=display) as display_cls:
            with pytest.raises(SystemExit):
                main_module.main()
        display_cls.assert_not_called()
        display.show_title_screen.assert_not_called()
        display.clear_screen.assert_not_called()


def test_main_saga_home_honours_a_persisted_seed(demo_saga: dict[str, Path], tmp_path: Path, saves_dir: Path) -> None:
    """A dropped graph= would give the chapter no saga provider, so the seed would never be read."""
    SaveManager(saves_dir).write_handoff(
        HandoffRecord(story_id="ch2a", from_story="ch1", state={"trust": 3, "player_name": "Ash"})
    )
    stories = _stage_stories(tmp_path, demo_saga.values())

    display, _cls, engine_cls = _drive_main(
        [], stories, saves_dir, story_select=[1, None], saga_select=[2, "back"]
    )

    assert display.show_story_picker.call_args_list[0].args[0][0]["type"] == "saga"
    assert engine_cls.call_args.args[0].id == "ch2a"
    kwargs = engine_cls.call_args.kwargs
    assert kwargs["known_chapter_ids"]
    assert kwargs["fresh_run_state"]() == {"trust": 3, "player_name": "Ash"}


def test_main_saga_inside_a_folder_honours_a_persisted_seed(
    demo_saga: dict[str, Path], tmp_path: Path, saves_dir: Path
) -> None:
    SaveManager(saves_dir).write_handoff(
        HandoffRecord(story_id="ch2a", from_story="ch1", state={"trust": 3, "player_name": "Ash"})
    )
    stories = _stage_stories(tmp_path, demo_saga.values(), folder="sagas")

    display, _cls, engine_cls = _drive_main(
        [], stories, saves_dir, story_select=[1, 1, None], saga_select=[2, "back"]
    )

    assert engine_cls.call_args.args[0].id == "ch2a"
    assert engine_cls.call_args.kwargs["fresh_run_state"]() == {"trust": 3, "player_name": "Ash"}


def test_main_saga_home_shows_the_replay_confirm(demo_saga: dict[str, Path], tmp_path: Path, saves_dir: Path) -> None:
    sm = SaveManager(saves_dir)
    sm.write_handoff(HandoffRecord(story_id="ch2a", from_story="ch1", state={"trust": 3}))
    stories = _stage_stories(tmp_path, demo_saga.values())

    display, _cls, engine_cls = _drive_main(
        [], stories, saves_dir, story_select=[1, None], saga_select=[1, "back"], replay_confirm=False
    )

    assert engine_cls.call_args.args[0].id == "ch1"
    assert engine_cls.call_args.kwargs["fresh_run_state"]() is None  # declined
    display.prompt_replay_confirm.assert_called_with(["2A — ch2a"])
    assert sm.load_handoff("ch2a").state == {"trust": 3}  # nothing erased


def test_main_debug_seed_override_reaches_a_cold_started_chapter(
    demo_saga: dict[str, Path], tmp_path: Path, saves_dir: Path
) -> None:
    stories = _stage_stories(tmp_path, demo_saga.values())

    display, _cls, engine_cls = _drive_main(
        ["--debug", "--seed", "trust=9"], stories, saves_dir,
        story_select=[1, None], saga_select=[3, "back"],  # debug lists all four; row 3 is 2B, never reached
    )

    assert engine_cls.call_args.args[0].id == "ch2b"
    assert engine_cls.call_args.kwargs["fresh_run_state"]() == {"player_name": "Felix", "trust": 9}
    _title, rows, _more = display.show_saga_home.call_args.args
    assert len(rows) == 4


def test_main_launches_the_selected_plain_story_not_a_chapter_by_list_position(
    valid_story_path: Path, demo_saga: dict[str, Path], tmp_path: Path, saves_dir: Path
) -> None:
    """Rows are [saga, Test Story]; root_paths sort as ch1, ch2a, ..., test_story, so row 2 by
    position would launch ch2a."""
    stories = _stage_stories(tmp_path, [valid_story_path, *demo_saga.values()])

    _display, _cls, engine_cls = _drive_main([], stories, saves_dir, story_select=[2, None])

    assert engine_cls.call_args.args[0].id == "test_story"
    assert engine_cls.call_args.kwargs["fresh_run_state"] is None


def test_saga_entries_and_home_rows_render_through_the_real_display(
    demo_saga: dict[str, Path], saves_dir: Path, capsys
) -> None:
    """The dicts main.py builds must carry every key Display reads (no MagicMock in the way)."""
    from src.display import Display

    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    sm.write(SaveState(story_id="ch2a", current_node="start"))
    infos = _collect_chapter_infos(demo_saga.values())
    graph, progress = SagaGraph.build(infos), _build_progress(infos, sm, gm)
    display = Display()

    display.show_story_picker(_build_entries(list(demo_saga.values()), {}, sm, gm, graph, progress))
    saga = graph.sagas["demo"]
    listed = graph.reached(saga, progress)
    display.show_saga_home(
        saga.title, [_home_row(graph.chapter(cid), progress) for cid in listed], len(listed) < len(saga.chapters)
    )

    out = capsys.readouterr().out
    assert "Demo Saga" in out and "SAGA" in out and "RESUME" in out
    assert "2/4 chapters" in out
    assert "2A" in out and "more to discover" in out


# ---------------------------------------------------------------------------
# Duplicate meta.id chapter files (the loser is not a chapter the graph knows)
# ---------------------------------------------------------------------------

def _copy_chapter(src: Path, name: str, **meta) -> Path:
    """Copy a chapter file under a new file name, optionally overriding meta fields."""
    data = json.loads(src.read_text(encoding="utf-8"))
    data["meta"].update(meta)
    dest = src.with_name(name)
    dest.write_text(json.dumps(data), encoding="utf-8")
    return dest


def _dup_state(paths, saves_dir: Path):
    infos = _collect_chapter_infos(list(paths))  # full list: duplicates are NOT deduped here
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    return infos, SagaGraph.build(infos), _build_progress(infos, sm, gm), sm, gm


def test_a_duplicate_of_a_chapter_in_a_known_saga_is_hidden_and_the_saga_row_carries_the_error(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    dup = _copy_chapter(demo_saga["ch2a"], "ch2a_copy.json", title="Chapter Two Copy")
    paths = [*demo_saga.values(), dup]
    infos, graph, progress, sm, gm = _dup_state(paths, saves_dir)

    entries = _build_entries(paths, {}, sm, gm, graph, progress, infos)

    assert len(entries) == 1
    assert entries[0]["type"] == "saga"
    assert entries[0]["error"] is True
    assert any("duplicate story id 'ch2a'" in problem for problem in entries[0]["problems"])
    assert all(e["path"] != dup for e in entries)


def test_a_hidden_duplicate_stays_hidden_in_a_different_folder(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    dup = _copy_chapter(demo_saga["ch2a"], "ch2a_copy.json")
    paths = [*demo_saga.values(), dup]
    infos, graph, progress, sm, gm = _dup_state(paths, saves_dir)
    folders = {"sagas": list(demo_saga.values()), "extras": [dup]}

    entries = _build_top_level_entries([], folders, {}, sm, gm, graph, progress, infos)

    assert [(e["type"], e["label"]) for e in entries] == [("folder", "sagas")]
    assert entries[0]["story_count"] == 1


def test_folder_picker_hides_a_duplicate_of_a_known_chapter(demo_saga: dict[str, Path], saves_dir: Path) -> None:
    dup = _copy_chapter(demo_saga["ch2a"], "ch2a_copy.json")
    paths = [*demo_saga.values(), dup]
    infos, graph, progress, sm, gm = _dup_state(paths, saves_dir)
    display = _folder_display(["back"])

    _run_folder_picker("f", paths, {}, sm, gm, display, graph, progress, infos)

    shown = display.show_story_picker.call_args.args[0]
    assert [(e["label"], e["error"]) for e in shown] == [("Demo Saga", True)]


def test_a_duplicate_whose_saga_is_not_in_the_graph_becomes_an_error_row(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    """The copy declares its own saga_id, so SagaGraph drops it and that saga never forms."""
    dup = _copy_chapter(demo_saga["ch2a"], "ch2a_copy.json", saga_id="solo", title="Chapter Two Copy")
    paths = [*demo_saga.values(), dup]
    infos, graph, progress, sm, gm = _dup_state(paths, saves_dir)
    assert "solo" not in graph.sagas

    entries = _build_entries(paths, {}, sm, gm, graph, progress, infos)

    assert [e["index"] for e in entries] == [1, 2]
    saga_row, dup_row = entries
    assert saga_row["type"] == "saga" and saga_row["error"] is True
    assert dup_row["path"] == dup
    assert dup_row["error"] is True
    assert dup_row.get("type") != "story"
    assert "duplicate story id 'ch2a'" in dup_row["message"]


def test_opening_an_orphan_duplicate_reports_the_error_and_never_launches(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    dup = _copy_chapter(demo_saga["ch2a"], "ch2a_copy.json", saga_id="solo")
    paths = [*demo_saga.values(), dup]
    infos, graph, progress, sm, gm = _dup_state(paths, saves_dir)
    dup_row = _build_entries(paths, {}, sm, gm, graph, progress, infos)[1]
    display = MagicMock()

    with patch("main._play_chapter") as play, patch("main._launch_story") as launch:
        _open_entry(dup_row, graph, {}, sm, gm, display, debug=False, seed_override=None)

    play.assert_not_called()
    launch.assert_not_called()
    name, message = display.show_picker_error.call_args.args
    assert name == "ch2a_copy.json"
    assert "duplicate story id 'ch2a'" in message


def test_folder_picker_reports_an_orphan_duplicate_without_returning_it(
    demo_saga: dict[str, Path], saves_dir: Path
) -> None:
    dup = _copy_chapter(demo_saga["ch2a"], "ch2a_copy.json", saga_id="solo")
    paths = [*demo_saga.values(), dup]
    infos, graph, progress, sm, gm = _dup_state(paths, saves_dir)
    display = _folder_display([2, "back"])

    assert _run_folder_picker("f", paths, {}, sm, gm, display, graph, progress, infos) is None

    name, message = display.show_picker_error.call_args.args
    assert name == "ch2a_copy.json"
    assert "duplicate story id 'ch2a'" in message


def test_plain_stories_are_unaffected_by_the_duplicate_check(
    valid_story_path: Path, saves_dir: Path
) -> None:
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    infos = _collect_chapter_infos([valid_story_path])
    graph = SagaGraph.build(infos)

    with_graph = _build_entries([valid_story_path], {}, sm, gm, graph, _build_progress(infos, sm, gm), infos)

    assert with_graph == _build_entries([valid_story_path], {}, sm, gm)
    assert with_graph[0]["type"] == "story" and with_graph[0]["error"] is False


def test_main_never_lets_an_orphan_duplicate_reach_the_saga_provider(
    demo_saga: dict[str, Path], tmp_path: Path, saves_dir: Path
) -> None:
    sm = SaveManager(saves_dir)
    sm.write(SaveState(story_id="ch2a", current_node="start"))
    sm.write_handoff(HandoffRecord(story_id="ch3", from_story="ch2a", state={"trust": 3}))
    dup = _copy_chapter(demo_saga["ch2a"], "ch2a_copy.json", saga_id="solo", title="Chapter Two Copy")
    stories = _stage_stories(tmp_path, [*demo_saga.values(), dup])

    display, _cls, engine_cls = _drive_main([], stories, saves_dir, story_select=[2, None])

    rows = display.show_story_picker.call_args_list[0].args[0]
    assert [(r["error"], r.get("type")) for r in rows] == [(True, "saga"), (True, None)]
    engine_cls.assert_not_called()
    display.prompt_replay_confirm.assert_not_called()
    assert display.show_picker_error.call_args.args[0] == "ch2a_copy.json"
    assert sm.has_save("ch2a") and sm.has_handoff("ch3")  # nothing erased


def test_main_hides_a_known_saga_duplicate_and_the_saga_gate_still_blocks_play(
    demo_saga: dict[str, Path], tmp_path: Path, saves_dir: Path
) -> None:
    dup = _copy_chapter(demo_saga["ch2a"], "ch2a_copy.json", title="Chapter Two Copy")
    stories = _stage_stories(tmp_path, [*demo_saga.values(), dup], folder="sagas")

    display, _cls, engine_cls = _drive_main(
        [], stories, saves_dir, story_select=[1, 1, "back", None]  # folder, saga row, back, quit
    )

    folder_rows = display.show_story_picker.call_args_list[1].args[0]
    assert [(r["label"], r["error"]) for r in folder_rows] == [("Demo Saga", True)]
    engine_cls.assert_not_called()
    label, message = display.show_picker_error.call_args.args
    assert label == "Demo Saga" and "duplicate story id 'ch2a'" in message


def test_game_finds_its_stories_when_launched_from_another_folder(tmp_path: Path) -> None:
    """Start the real game from an unrelated folder, the way a shortcut or `python path/to/main.py` does.

    It used to look for "stories" in whatever folder the terminal was in: the player got
    "No stories found" and two empty folders were left behind in a place they never asked for.
    """
    import os
    import subprocess

    elsewhere = tmp_path / "somewhere_else"
    elsewhere.mkdir()
    main_py = Path(main_module.__file__).resolve()

    result = subprocess.run(
        [sys.executable, str(main_py)],
        cwd=elsewhere,
        input="q\n",  # quit at the story picker
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "Select a Story" in result.stdout
    assert "No Stories Loaded" not in result.stdout
    assert list(elsewhere.iterdir()) == []  # nothing left behind


def test_story_and_save_folders_sit_next_to_main_py() -> None:
    app_dir = Path(main_module.__file__).resolve().parent
    assert main_module.STORIES_DIR == app_dir / "stories"
    assert main_module.SAVES_DIR == app_dir / "saves"
