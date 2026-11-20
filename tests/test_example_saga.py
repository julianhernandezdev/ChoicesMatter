from pathlib import Path
from unittest.mock import MagicMock, patch

from main import _collect_chapter_infos, _play_chapter
from scripts.validate_story import validate_file, validate_sagas
from src.gallery import GalleryManager
from src.saga import SagaGraph
from src.save import SaveManager

SAGAS = Path(__file__).resolve().parents[1] / "stories" / "sagas"
FILES = {
    "ch1": SAGAS / "24_saga_ch1_the_bridge.json",
    "ch2a": SAGAS / "24_saga_ch2a_the_far_bank.json",
    "ch2b": SAGAS / "24_saga_ch2b_the_skiff.json",
    "ch3": SAGAS / "24_saga_ch3_the_last_ferry.json",
}


def test_every_file_is_valid_on_its_own() -> None:
    for path in FILES.values():
        assert validate_file(path) == ([], []), path.name


def test_the_four_chapters_validate_clean_together() -> None:
    assert validate_sagas(list(FILES.values())) == ([], [])


def test_the_graph_is_a_clean_branch_and_converge() -> None:
    graph = SagaGraph.build(_collect_chapter_infos(FILES.values()))
    saga = graph.sagas["saga_demo"]
    assert saga.title == "The Last Ferry"
    assert saga.entry == "saga_demo_ch1"
    assert saga.problems == ()
    assert list(saga.chapters) == ["saga_demo_ch1", "saga_demo_ch2a", "saga_demo_ch2b", "saga_demo_ch3"]
    assert graph.descendants("saga_demo_ch1") == frozenset(
        {"saga_demo_ch2a", "saga_demo_ch2b", "saga_demo_ch3"}
    )


def _run(saves_dir: Path, choices: list[int]):
    graph = SagaGraph.build(_collect_chapter_infos(FILES.values()))
    sm, gm = SaveManager(saves_dir), GalleryManager(saves_dir)
    display = MagicMock()
    display.prompt_choice.side_effect = choices
    display.prompt_protagonist_name.return_value = "Casey"
    display.prompt_chapter_transition.return_value = "continue"
    display.prompt_play_again.return_value = False
    with patch("main.load_settings", return_value={"player_name": "Felix"}):
        _play_chapter(FILES["ch1"], {}, sm, gm, display, graph=graph, seed_override=None)
    return sm, gm, display


def test_bridge_path_reaches_the_saga_end(saves_dir: Path) -> None:
    sm, gm, display = _run(saves_dir, [1, 1, 1, 1])  # bridge, help, lantern path, ring the bell

    assert gm.get_found("saga_demo_ch1") == {"e_left"}
    assert gm.get_found("saga_demo_ch2a") == {"e_go"}
    assert gm.get_found("saga_demo_ch3") == {"e_win"}
    assert sm.load_handoff("saga_demo_ch3").state == {"trust": 3, "player_name": "Casey"}
    assert display.prompt_protagonist_name.call_count == 1  # ch2a's name_prompt is skipped by the seed
    display.show_chapter_transition.assert_called_once()
    assert any("still sways" in str(c.args[1]) for c in display.show_node.call_args_list)  # carried visited_bridge


def test_skiff_path_without_trust_hides_the_bell(saves_dir: Path) -> None:
    sm, gm, display = _run(saves_dir, [2, 1, 2, 1])  # hut, take skiff, drift, walk back

    assert gm.get_found("saga_demo_ch3") == {"e_lose"}
    final_choices = display.show_choices.call_args_list[-1].args[0]
    assert [c.label for c in final_choices] == ["Walk back into the dark"]
    assert sm.load_handoff("saga_demo_ch3").state == {"trust": 1, "player_name": "Casey"}
