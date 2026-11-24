"""Tests for the five-chapter saga "The Census of the Dead" (stories/sagas/25_census_*)."""
import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

from main import _collect_chapter_infos, _play_chapter
from scripts.validate_story import validate_file, validate_sagas
from src.gallery import GalleryManager
from src.saga import SagaGraph
from src.save import SaveManager

SAGAS = Path(__file__).resolve().parents[1] / "stories" / "sagas"
FILES = {
    "1": SAGAS / "25_census_ch1_bureau.json",
    "2": SAGAS / "25_census_ch2_regional_office.json",
    "3": SAGAS / "25_census_ch3_village.json",
    "4": SAGAS / "25_census_ch4_the_report.json",
    "5": SAGAS / "25_census_ch5_archive_1989.json",
}
IDS = {
    "1": "cotd_1_bureau",
    "2": "cotd_2_regional_office",
    "3": "cotd_3_village",
    "4": "cotd_4_the_report",
    "5": "cotd_5_archive_1989",
}
EXPORTS = [
    "drift", "opened_letters", "went_home", "kept_ledger",
    "asked_why", "looked_away", "signed_figure", "filed_true",
]
BOOLS = [name for name in EXPORTS if name != "drift"]
BANNED = re.compile(r"famine|holodomor|starv|death toll", re.IGNORECASE)
ALLOWED_TOKENS = {"player_name", "pause", "corrupt"}
MAX_PROMPTS = 500


def load(chapter: str) -> dict:
    return json.loads(FILES[chapter].read_text(encoding="utf-8"))


def all_text(chapter: str) -> list[str]:
    """Every string the player can read in a chapter: node text, labels, insets, overlays, warnings."""
    data = load(chapter)
    out = list(data["meta"].get("warnings", []))
    for node in data["nodes"].values():
        out.append(node["text"])
        out += [c["label"] for c in node["choices"]]
        out += [i["text"] for i in node.get("insets", [])]
        out += [o["text"] for o in node.get("overlays", [])]
    return out


def play(picks: list[str], start: str = "1", seed: dict | None = None, saves: Path | None = None):
    """Run the saga from chapter `start`, choosing at each prompt the choice whose `next` is the
    next id in `picks` (first choice once picks run out). Returns (SaveManager, GalleryManager, display)."""
    assert saves is not None
    graph = SagaGraph.build(_collect_chapter_infos(FILES.values()))
    sm, gm = SaveManager(saves), GalleryManager(saves)
    display = MagicMock()
    queue = list(picks)
    calls = {"n": 0}

    def choose(choices):
        calls["n"] += 1
        assert calls["n"] < MAX_PROMPTS, "runaway playthrough"
        if not queue:
            return 1
        want = queue.pop(0)
        targets = [c.next for c in choices]
        assert want in targets, f"{want!r} not offered; choices were {targets}"
        return targets.index(want) + 1

    display.prompt_choice.side_effect = choose
    display.prompt_protagonist_name.return_value = "Casey"
    display.prompt_chapter_transition.return_value = "continue"
    display.prompt_play_again.return_value = False
    with patch("main.load_settings", return_value={"player_name": "Felix"}):
        _play_chapter(FILES[start], {}, sm, gm, display, graph=graph, seed_override=seed)
    assert not queue, f"unused picks: {queue}"
    return sm, gm, display


def test_every_file_is_valid_on_its_own() -> None:
    for path in FILES.values():
        assert validate_file(path) == ([], []), path.name


def test_five_chapters_validate_clean_together() -> None:
    assert validate_sagas(list(FILES.values())) == ([], [])


def test_graph_is_a_line_ending_in_a_hub() -> None:
    graph = SagaGraph.build(_collect_chapter_infos(FILES.values()))
    saga = graph.sagas["census_of_the_dead"]
    assert saga.title == "The Census of the Dead"
    assert saga.entry == IDS["1"]
    assert saga.problems == ()
    assert list(saga.chapters) == [IDS[k] for k in "12345"]


def test_banned_words_never_appear() -> None:
    for key in FILES:
        for line in all_text(key):
            assert not BANNED.search(line), (key, line)


def test_no_bare_placeholders() -> None:
    for key in FILES:
        for line in all_text(key):
            for token in re.findall(r"\{(\w+)\}", line):
                assert token in ALLOWED_TOKENS, (key, token, line)


def test_every_chapter_has_warnings() -> None:
    for key in FILES:
        warnings = load(key)["meta"].get("warnings")
        assert isinstance(warnings, list) and warnings, key


# --- helpers for structural chapter tests ---------------------------------


def choices_to(chapter: str, target: str) -> list[dict]:
    """Every choice in a chapter whose `next` is `target`."""
    return [c for n in load(chapter)["nodes"].values() for c in n["choices"] if c["next"] == target]


def endings_chaining_to(chapter: str, next_story: str) -> list[dict]:
    return [n for n in load(chapter)["nodes"].values() if n.get("next_story") == next_story]


ALL_FALSE = {name: False for name in BOOLS}


# --- chapter 1: the bureau -------------------------------------------------


def test_ch1_initialises_every_flag_on_the_only_path() -> None:
    data = load("1")
    start = data["nodes"][data["meta"]["start_node"]]
    assert len(start["choices"]) == 1
    assert start["choices"][0]["sets"] == {"drift": 0, **ALL_FALSE}


def test_ch1_drawer_open_sets_opened_letters_and_shut_does_not() -> None:
    opened = choices_to("1", "drawer_open")
    shut = choices_to("1", "drawer_shut")
    assert opened and all(c["sets"] == {"opened_letters": True} for c in opened)
    assert shut and all("opened_letters" not in c.get("sets", {}) for c in shut)


def test_ch1_exports_all_eight_into_chapter_2() -> None:
    ends = endings_chaining_to("1", IDS["2"])
    assert ends and all(n["exports"] == EXPORTS and n["is_ending"] for n in ends)


def test_ch1_has_name_prompt_and_saga_title() -> None:
    meta = load("1")["meta"]
    assert meta["id"] == IDS["1"] and meta["saga_id"] == "census_of_the_dead"
    assert meta["saga_title"] == "The Census of the Dead"
    assert meta["name_prompt"] and meta["name_default"]


def test_ch1_offers_no_question() -> None:
    labels = [c["label"] for n in load("1")["nodes"].values() for c in n["choices"]]
    assert not [l for l in labels if re.search(r"\bwhy\b", l, re.IGNORECASE)]


# --- chapter 2: the regional office ----------------------------------------


def test_ch2_keep_ledger_sets_flag_and_leave_does_not() -> None:
    keep, leave = choices_to("2", "keep_ledger"), choices_to("2", "leave_ledger")
    assert keep and all(c["sets"] == {"kept_ledger": True} for c in keep)
    assert leave and all("kept_ledger" not in c.get("sets", {}) for c in leave)


def test_ch2_each_reconcile_adds_one_drift_and_nothing_else_does() -> None:
    for target in ("reconcile_a", "reconcile_b"):
        found = choices_to("2", target)
        assert found and all(c["sets"] == {"drift": "+1"} for c in found), target
    drifting = [
        c["next"] for n in load("2")["nodes"].values() for c in n["choices"] if "drift" in c.get("sets", {})
    ]
    assert set(drifting) == {"reconcile_a", "reconcile_b"}


def test_ch2_ask_why_waits_for_the_first_wrong_number() -> None:
    found = choices_to("2", "ask_why")
    assert found and all(c["requires"] == {"drift": 1} for c in found)
    assert all(c["sets"] == {"asked_why": True} for c in found)


def test_ch2_exports_all_eight_into_chapter_3() -> None:
    ends = endings_chaining_to("2", IDS["3"])
    assert ends and all(n["exports"] == EXPORTS and n["is_ending"] for n in ends)


def test_ch2_has_no_saga_title() -> None:
    meta = load("2")["meta"]
    assert meta["id"] == IDS["2"] and "saga_title" not in meta
