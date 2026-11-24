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
