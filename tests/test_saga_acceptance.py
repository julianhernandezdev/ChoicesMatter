"""End-to-end run of the example saga through the real Display with scripted input.

Every save, seed and gallery lives under pytest's tmp_path; the real saves/ folder is never
touched. Unscripted prompts (and answers left over at the end) fail loudly instead of hanging.
"""
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from rich.console import Console
from rich.text import Text

from main import _collect_chapter_infos, _run_saga_home
from src.config import load_settings
from src.display import Display
from src.gallery import GalleryManager
from src.saga import SagaGraph
from src.save import SaveManager

SAGA_DIR = Path(__file__).resolve().parents[1] / "stories" / "sagas"
CHAPTERS = [
    SAGA_DIR / "24_saga_ch1_the_bridge.json",
    SAGA_DIR / "24_saga_ch2a_the_far_bank.json",
    SAGA_DIR / "24_saga_ch2b_the_skiff.json",
    SAGA_DIR / "24_saga_ch3_the_last_ferry.json",
]
CH1, CH2A, CH2B, CH3 = "saga_demo_ch1", "saga_demo_ch2a", "saga_demo_ch2b", "saga_demo_ch3"
ALL_CHAPTERS = (CH1, CH2A, CH2B, CH3)

# Prompt keys: each is matched against the prompt's plain text, exactly as rich renders it.
HOME = "Chapter (1-"                                  # Display.prompt_saga_select
NAME = "Enter name"                                   # Display.prompt_protagonist_name
CHOICE = "Your choice"                                # Display.prompt_choice
CHAIN = "[C]ontinue / play [A]gain / [M]enu"          # Display.prompt_chapter_transition
CONFIRM = "Continue? [Y/N]"                           # Display.prompt_replay_confirm
PANEL_WAIT = "Press Enter to continue"                # Display.show_chapter_transition
AGAIN = "Play again?"                                 # Display.prompt_play_again


class Script:
    """Answer console.input() by matching plain text in the prompt. Fails on anything unscripted."""

    def __init__(self, rules: dict[str, list[str]]) -> None:
        self.rules = {key: list(answers) for key, answers in rules.items()}
        self.log: list[str] = []

    def __call__(self, prompt: str = "", **_kwargs) -> str:
        plain = Text.from_markup(prompt).plain  # what rich itself shows; keeps literal [C]/[Y/N]
        for key, answers in self.rules.items():
            if key in plain:
                assert answers, f"script exhausted for {key!r}; log so far: {self.log}"
                answer = answers.pop(0)
                self.log.append(f"{key!r} -> {answer!r}")
                return answer
        raise AssertionError(f"unscripted prompt: {plain!r}; log so far: {self.log}")

    def assert_consumed(self) -> None:
        leftover = {k: v for k, v in self.rules.items() if v}
        assert not leftover, f"unused answers: {leftover}; log: {self.log}"


def _rig(tmp_path: Path, saves_dir: Path):
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    # Display() reads settings.json through src.display.load_settings; point it at a path that
    # does not exist so the developer's own file (typewriter, corruption, ...) cannot leak in.
    defaults = load_settings(tmp_path / "no_settings.json")
    defaults["typewriter"]["enabled"] = False  # the shipped default is on; the run must not stream
    with patch("src.display.load_settings", return_value=defaults):
        display = Display()
    out = StringIO()
    display.console = Console(file=out, width=100, force_terminal=False)
    graph = SagaGraph.build(_collect_chapter_infos(CHAPTERS))
    return sm, gm, display, out, graph


def _drive(display, graph, sm, gm, rules, **kwargs) -> Script:
    script = Script(rules)
    display.console.input = script
    with patch("main.load_settings", return_value={"player_name": "Felix"}):
        _run_saga_home(graph.sagas["saga_demo"], graph, {}, sm, gm, display, **kwargs)
    script.assert_consumed()
    return script


def _play_bridge_route(display, graph, sm, gm) -> None:
    """Enter the saga, take the default (entry) chapter and play the bridge route to the saga end."""
    _drive(display, graph, sm, gm, {
        HOME: ["", "b"],                          # Enter takes the default (entry), then back
        NAME: ["Casey"],                          # asked once, in chapter one only
        CHOICE: ["1", "1", "1", "1"],             # bridge, help, lantern path, ring the bell
        CHAIN: ["c"],                             # after ch1's e_left; ch2a is a transition, no prompt
        PANEL_WAIT: [""],                         # ch2a's chapter_transition node
        AGAIN: ["n"],                             # after the saga_end ending
    })


def test_bridge_route_chains_transitions_and_ends_the_saga(tmp_path: Path, saves_dir: Path) -> None:
    sm, gm, display, out, graph = _rig(tmp_path, saves_dir)

    _play_bridge_route(display, graph, sm, gm)

    text = out.getvalue()
    assert "more to discover" in text                           # home hid the unreached chapters
    assert "The bridge still sways behind you" in text          # carried visited_bridge
    assert "End of saga" in text
    assert sm.load_handoff(CH2A).state == {"trust": 2, "visited_bridge": True, "player_name": "Casey"}
    assert sm.load_handoff(CH3).state == {"trust": 3, "player_name": "Casey"}
    assert not sm.has_handoff(CH1) and not sm.has_handoff(CH2B)
    assert gm.get_found(CH1) == {"e_left"}
    assert gm.get_found(CH2A) == {"e_go"}
    assert gm.get_found(CH2B) == set()
    assert gm.get_found(CH3) == {"e_win"}
    assert not any(sm.has_save(cid) for cid in ALL_CHAPTERS)


def test_replay_confirm_erase_menu_and_resume_from_home(tmp_path: Path, saves_dir: Path) -> None:
    sm, gm, display, out, graph = _rig(tmp_path, saves_dir)
    _play_bridge_route(display, graph, sm, gm)

    # Phase B: restart chapter one. Declining the confirm erases nothing; accepting erases the
    # downstream seeds (only after the name prompt resolves) and galleries survive. The skiff
    # route then stops at the first chain prompt via Menu, leaving ch2b's seed on disk.
    _drive(display, graph, sm, gm, {
        HOME: ["1", "1", "b"],
        CONFIRM: ["n", "y"],                      # replay confirm: decline, then accept
        NAME: ["Ash"],
        CHOICE: ["2", "1"],                       # hut, take the skiff
        CHAIN: ["m"],                             # menu: the seed stays on disk
    })
    assert not sm.has_handoff(CH2A)
    assert not sm.has_handoff(CH3)
    assert sm.load_handoff(CH2B).state == {"trust": 1, "player_name": "Ash"}
    assert gm.get_found(CH1) == {"e_left", "e_right"}
    assert gm.get_found(CH2A) == {"e_go"}         # galleries are never touched by a replay
    assert gm.get_found(CH3) == {"e_win"}
    assert not any(sm.has_save(cid) for cid in ALL_CHAPTERS)

    # Phase C: back in the saga home, Enter takes the default chapter: the one with the pending
    # seed (ch2b). Its name prompt must not fire (no NAME rule: an unscripted prompt fails), the
    # carried name reaches ch3, and the run finishes the saga.
    mark = len(out.getvalue())
    _drive(display, graph, sm, gm, {
        HOME: ["", "b"],
        CHOICE: ["1", "1"],                       # row hard (+1 trust), then ring the bell
        CHAIN: ["c"],                             # after ch2b's e_go (a plain chain, no panel)
        AGAIN: ["n"],
    })
    resumed = out.getvalue()[mark:]
    ready_line = next(line for line in resumed.splitlines() if "The Skiff" in line)
    assert "●" in ready_line                                    # pending-seed marker on the home screen
    assert "Who crosses the river tonight?" not in resumed      # no name panel in chapter two
    assert "The skiff rocks under you, Ash." in resumed
    assert "The ferry is here, Ash" in resumed
    assert sm.load_handoff(CH3).state == {"trust": 2, "player_name": "Ash"}
    assert sm.load_handoff(CH2B).state == {"trust": 1, "player_name": "Ash"}
    assert gm.get_found(CH2B) == {"e_go"}
    assert gm.get_found(CH3) == {"e_win"}
    assert not sm.has_handoff(CH2A)
    assert not any(sm.has_save(cid) for cid in ALL_CHAPTERS)


def test_declined_confirm_touches_nothing(tmp_path: Path, saves_dir: Path) -> None:
    sm, gm, display, _out, graph = _rig(tmp_path, saves_dir)
    _play_bridge_route(display, graph, sm, gm)
    seeds_before = {cid: sm.load_handoff(cid) for cid in ALL_CHAPTERS}
    gallery_before = {cid: gm.get_found(cid) for cid in ALL_CHAPTERS}

    _drive(display, graph, sm, gm, {HOME: ["1", "b"], CONFIRM: ["n"]})

    assert {cid: sm.load_handoff(cid) for cid in ALL_CHAPTERS} == seeds_before
    assert {cid: gm.get_found(cid) for cid in ALL_CHAPTERS} == gallery_before
    assert not any(sm.has_save(cid) for cid in ALL_CHAPTERS)


def test_debug_cold_start_with_seed_override(tmp_path: Path, saves_dir: Path) -> None:
    sm, gm, display, _out, graph = _rig(tmp_path, saves_dir)
    _drive(
        display, graph, sm, gm,
        {
            HOME: ["4", "b"],                     # debug lists all four chapters; 4 = the finale
            CHOICE: ["1"],                        # ring the bell: visible because --seed gave trust
            AGAIN: ["n"],
        },
        debug=True, seed_override={"trust": 2},
    )
    assert gm.get_found(CH3) == {"e_win"}
    assert gm.get_found(CH1) == set() and gm.get_found(CH2A) == set() and gm.get_found(CH2B) == set()
    assert not any(sm.has_save(cid) for cid in ALL_CHAPTERS)
