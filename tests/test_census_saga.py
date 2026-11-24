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


# --- chapter 3: the village ------------------------------------------------


def test_ch3_go_home_sets_went_home_and_avoid_does_not() -> None:
    go, avoid = choices_to("3", "go_home"), choices_to("3", "avoid_home")
    assert go and all(c["sets"] == {"went_home": True} for c in go)
    assert avoid and all("went_home" not in c.get("sets", {}) for c in avoid)


def test_ch3_look_away_sets_looked_away() -> None:
    found = choices_to("3", "look_away")
    assert found and all(c["sets"] == {"looked_away": True} for c in found)


def test_ch3_ask_why_needs_drift_and_sets_asked_why() -> None:
    found = choices_to("3", "ask_why")
    assert found and all(c["requires"] == {"drift": 1} and c["sets"] == {"asked_why": True} for c in found)


def test_ch3_three_reconcile_nodes_each_add_one_drift_and_nothing_else_does() -> None:
    targets = set()
    for node in load("3")["nodes"].values():
        for c in node["choices"]:
            if "drift" in c.get("sets", {}):
                assert c["sets"] == {"drift": "+1"} and c["next"].startswith("reconcile_"), c
                targets.add(c["next"])
    assert len(targets) >= 3


def test_ch3_ledger_insets_are_additive_drift_tiers() -> None:
    tiers = set()
    for node in load("3")["nodes"].values():
        for inset in node.get("insets", []):
            req = inset.get("requires", {})
            if "drift" in req:
                assert req["drift"] >= 1, inset  # never a tier-0 inset
                if inset["style"] == "system":
                    tiers.add(req["drift"])
    assert {1, 3, 5} <= tiers


def test_ch3_exports_all_eight_into_chapter_4() -> None:
    ends = endings_chaining_to("3", IDS["4"])
    assert ends and all(n["exports"] == EXPORTS and n["is_ending"] for n in ends)


def test_ch3_never_requires_an_unset_flag_to_be_false() -> None:
    # a cold start has no flags, and `requires {flag: false}` fails for a missing key
    for node in load("3")["nodes"].values():
        for c in node["choices"]:
            assert False not in c.get("requires", {}).values(), c


# --- chapter 4: the report -------------------------------------------------


def test_ch4_sign_sets_exactly_signed_figure() -> None:
    found = choices_to("4", "e_sign")
    assert found and all(c["sets"] == {"signed_figure": True, "filed_true": False} for c in found)


def test_ch4_file_true_sets_exactly_filed_true() -> None:
    found = choices_to("4", "e_file_true")
    assert found and all(c["sets"] == {"filed_true": True, "signed_figure": False} for c in found)


def test_ch4_ledger_option_depends_on_kept_ledger() -> None:
    found = choices_to("4", "attach_ledger")
    assert found and all(c["requires"] == {"kept_ledger": True} for c in found)


def test_ch4_both_endings_export_all_eight_into_chapter_5() -> None:
    ends = endings_chaining_to("4", IDS["5"])
    assert {k for k, n in load("4")["nodes"].items() if n.get("next_story") == IDS["5"]} == {"e_sign", "e_file_true"}
    assert all(n["exports"] == EXPORTS and n["is_ending"] for n in ends)


def test_ch4_never_sets_drift_and_never_requires_an_unset_flag_to_be_false() -> None:
    for node in load("4")["nodes"].values():
        for c in node["choices"]:
            assert "drift" not in c.get("sets", {}), c
            assert False not in c.get("requires", {}).values(), c


# --- chapter 5: the archive, 1989 ------------------------------------------

HUB = "files"
ENDINGS = {
    "e_stands", "e_wrong", "e_honest", "e_colleague",
    "e_name_letters", "e_name_home", "e_name_late", "e_unread",
}
NAME_LINE = re.compile(r"danylenko, hanna opanasivna", re.IGNORECASE)
FATE_WORDS = re.compile(r"\b(died|dead|death|buried|grave|corpses?|bod(?:y|ies))\b", re.IGNORECASE)


def meets(requires: dict, state: dict) -> bool:
    """Mirror of Engine._check_requires for bool and int conditions."""
    for key, want in requires.items():
        have = state.get(key)
        if isinstance(want, bool):
            if have != want:
                return False
        elif isinstance(want, int):
            val = have if isinstance(have, int) and not isinstance(have, bool) else 0
            if val < want:
                return False
    return True


def hub_targets(state: dict) -> set[str]:
    return {c["next"] for c in load("5")["nodes"][HUB]["choices"] if meets(c.get("requires", {}), state)}


def profile(**flags) -> dict:
    return {**ALL_FALSE, "drift": 0, **flags}


def test_ch5_hub_choices_by_profile() -> None:
    complicit = profile(signed_figure=True, looked_away=True)
    asker = profile(filed_true=True, opened_letters=True, went_home=True, kept_ledger=True)
    signed_but_asked = profile(signed_figure=True, kept_ledger=True)
    assert hub_targets(complicit) == {"e_stands", "e_name_late", "e_unread"}
    assert hub_targets(asker) == {"e_honest", "e_colleague", "e_name_letters", "e_name_home", "e_unread"}
    assert hub_targets(signed_but_asked) == {"e_wrong", "e_colleague", "e_name_late", "e_unread"}


def test_ch5_hub_is_never_empty_even_with_no_flags_at_all() -> None:
    assert "e_unread" in hub_targets({})


def test_ch5_every_ending_is_a_plain_saga_end() -> None:
    nodes = load("5")["nodes"]
    assert {k for k, n in nodes.items() if n.get("is_ending")} == ENDINGS
    for key in ENDINGS:
        node = nodes[key]
        assert node["saga_end"] is True and node["ending_type"] == "neutral", key
        assert not {"next_story", "exports", "chapter_transition"} & node.keys(), key


def test_ch5_opens_in_1989_in_the_players_name() -> None:
    data = load("5")
    opening = data["nodes"][data["meta"]["start_node"]]["text"]
    assert "{player_name}" in opening and "1989" in opening


def test_ch5_every_file_carries_the_name_line_except_the_unread_one() -> None:
    nodes = load("5")["nodes"]
    for key in ENDINGS - {"e_unread"}:
        assert NAME_LINE.search(nodes[key]["text"]), key
    assert not NAME_LINE.search(nodes["e_unread"]["text"])


def test_no_chapter_states_a_fate() -> None:
    for key in FILES:
        data = load(key)
        for node in data["nodes"].values():
            texts = [node["text"]] + [i["text"] for i in node.get("insets", [])] + [o["text"] for o in node.get("overlays", [])]
            for line in texts:
                assert not FATE_WORDS.search(line), (key, line)
