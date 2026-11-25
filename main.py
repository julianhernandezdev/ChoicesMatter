from __future__ import annotations

import argparse
import math
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

from src.display import Display
from src.engine import ChainResult, Engine
from src.gallery import GalleryManager
from src.saga import (
    ChapterInfo,
    Saga,
    SagaGraph,
    SagaProgress,
    chapter_info_from_story,
    chapter_label_text,
    parse_seed_arg,
)
from src.save import SaveManager
from src.config import _DEFAULTS, load_settings
from src.story import Story, StoryLoader, StoryValidationError

# Look next to this file, not wherever the terminal happens to be standing.
# Otherwise launching from another folder finds no stories and leaves empty
# "stories" and "saves" folders behind as a souvenir.
APP_DIR = Path(__file__).resolve().parent
STORIES_DIR = APP_DIR / "stories"
SAVES_DIR = APP_DIR / "saves"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Choices Matter text adventure engine")
    parser.add_argument("--debug", action="store_true", help="Show debug overlay")
    parser.add_argument("--all", action="store_true", help="Include visited_* flags in debug panel")
    parser.add_argument(
        "--seed",
        metavar="K=V,...",
        help="With --debug: seed flags when a chapter is started cold (e.g. trust=3,key=true)",
    )
    return parser


def _parse_args() -> dict:
    args = _build_parser().parse_args()
    return {"enabled": args.debug, "all": args.debug and args.all}


def _parse_seed_override() -> dict[str, bool | int | str] | None:
    parser = _build_parser()
    args = parser.parse_args()
    if args.seed is None:
        return None
    if not args.debug:
        parser.error("--seed requires --debug")
    try:
        return parse_seed_arg(args.seed)
    except ValueError as exc:
        parser.error(f"--seed: {exc}")


def main() -> None:
    STORIES_DIR.mkdir(exist_ok=True)
    SAVES_DIR.mkdir(exist_ok=True)

    # Parse (and reject) launch arguments before any screen is drawn.
    seed_override = _parse_seed_override()
    debug = _parse_args()
    display = Display(debug=debug)
    display.clear_screen()
    display.show_title_screen()

    save_manager = SaveManager(SAVES_DIR)
    gallery_manager = GalleryManager(SAVES_DIR)
    errors: dict[Path, str] = {}

    page = 0
    while True:
        root_paths, folders = StoryLoader.discover_with_folders(STORIES_DIR)

        if not root_paths and not folders:
            display.show_no_stories()
            return

        all_paths = root_paths + [p for paths in folders.values() for p in paths]
        chapters = _collect_chapter_infos(all_paths)
        graph = SagaGraph.build(chapters)
        progress = _build_progress(chapters, save_manager, gallery_manager)

        full_entries = _build_top_level_entries(
            root_paths, folders, errors, save_manager, gallery_manager, graph, progress, chapters
        )
        page_size = display.get_page_size()
        total_entries = len(full_entries)
        total_pages = max(1, math.ceil(total_entries / page_size))
        page = max(0, min(page, total_pages - 1))
        start = page * page_size
        paged = full_entries[start:start + page_size]
        display_entries = [{**e, "index": i + 1} for i, e in enumerate(paged)]

        display.clear_screen()
        display.show_story_picker(display_entries, page=page, total_pages=total_pages)

        selection = display.prompt_story_select(len(display_entries), total_pages=total_pages)
        if selection is None:
            return
        if selection == "prev_page":
            page = max(0, page - 1)
            continue
        if selection == "next_page":
            page = min(total_pages - 1, page + 1)
            continue
        if selection == "first_page":
            page = 0
            continue
        if selection == "toggle_typewriter":
            display.toggle_typewriter()
            continue
        if selection == "settings":
            display.show_settings_screen()
            continue
        if selection == "clear":
            if display.prompt_clear_confirm():
                save_manager.clear_all()
                gallery_manager.clear_all()
                display.show_clear_complete()
            continue

        chosen_entry = full_entries[start + (selection - 1)]

        if chosen_entry.get("type") == "folder":
            chosen_entry = _run_folder_picker(
                chosen_entry["label"], folders[chosen_entry["label"]], errors,
                save_manager, gallery_manager, display, graph, progress, chapters,
            )
            if chosen_entry is None:
                continue

        _open_entry(
            chosen_entry, graph, errors, save_manager, gallery_manager, display,
            debug=debug["enabled"], seed_override=seed_override,
        )


def _run_folder_picker(
    folder_name: str,
    paths: list[Path],
    errors: dict[Path, str],
    save_manager: SaveManager,
    gallery_manager: GalleryManager,
    display: Display,
    graph: SagaGraph | None = None,
    progress: SagaProgress | None = None,
    chapters: Sequence[ChapterInfo] | None = None,
) -> dict | None:
    """Show the contents of a folder. Returns the chosen entry dict, or None (back)."""
    full_entries = _build_entries(paths, errors, save_manager, gallery_manager, graph, progress, chapters)
    page = 0
    while True:
        display.clear_screen()
        page_size = display.get_page_size()
        total_pages = max(1, math.ceil(len(full_entries) / page_size))
        page = max(0, min(page, total_pages - 1))
        start = page * page_size
        paged = full_entries[start:start + page_size]
        display_entries = [{**e, "index": i + 1} for i, e in enumerate(paged)]
        display.show_story_picker(display_entries, title=f"📁 {folder_name}/", page=page, total_pages=total_pages)
        selection = display.prompt_story_select(len(display_entries), has_back=True, total_pages=total_pages)
        if selection is None or selection == "back":
            display.clear_screen()
            return None
        if selection == "prev_page":
            page = max(0, page - 1)
            continue
        if selection == "next_page":
            page = min(total_pages - 1, page + 1)
            continue
        if selection == "first_page":
            page = 0
            continue
        chosen_entry = full_entries[start + (selection - 1)]
        if chosen_entry.get("error"):
            if chosen_entry.get("type") == "saga":
                display.show_picker_error(chosen_entry["label"], "; ".join(chosen_entry["problems"]))
            else:
                display.show_picker_error(
                    chosen_entry["path"].name,
                    chosen_entry.get("message") or errors[chosen_entry["path"]],
                )
            continue
        return chosen_entry


def _resolve_player_name(entered: str, name_default: str, settings_name: str) -> str | None:
    """Pick the protagonist name once the player has answered the name prompt.

    Order: what the player typed, then a name the player saved in Settings,
    then the story's own name_default, then the built-in "Felix".
    """
    if entered:
        return entered
    # Settings always hand back a name, and "Felix" is what you get when nobody
    # picked one. That is not a choice, so it does not get to beat the name the
    # story's author picked. A saved name only counts if it is a different one.
    if settings_name and settings_name != _DEFAULTS["player_name"]:
        return settings_name
    if name_default:
        return name_default
    return settings_name or None


def _prompt_name_state(
    story: Story, display: Display, settings_name: str
) -> dict[str, bool | int | str] | None:
    """Run the protagonist name prompt for a fresh run.

    Returns the seed-state dict, or None when the player backed out (Q) or no
    name could be resolved. In the latter case the player has already been told.
    """
    # The name in brackets is what Enter will give, so it has to be the same name.
    blank_name = _resolve_player_name("", story.name_default or "", settings_name)
    entered = display.prompt_protagonist_name(story.name_prompt or "", prefill=blank_name or "")
    if entered is None:
        return None
    name = _resolve_player_name(entered, story.name_default or "", settings_name)
    if name is None:
        display.show_name_required()
        return None
    return {"player_name": name}


def _collect_chapter_infos(paths: Iterable[Path]) -> list[ChapterInfo]:
    """Load every story and keep the saga chapters. Stories that fail to load are skipped.

    "Fail to load" includes a file that cannot be read or decoded (OSError; UnicodeDecodeError
    is a ValueError): StoryLoader.load only wraps JSON syntax errors, and this runs over every
    story in every folder on each picker refresh, so one bad file must not take the picker down.
    """
    infos: list[ChapterInfo] = []
    for path in paths:
        try:
            story = StoryLoader.load(path)
        except (StoryValidationError, OSError, ValueError):
            continue
        if story.saga_id:
            infos.append(chapter_info_from_story(story))
    return infos


def _stamp(value: object) -> str:
    """Coerce a save/seed timestamp to a string. A hand-edited "timestamp": null comes back
    from from_dict as None, and None cannot be compared with the ISO strings around it."""
    return str(value) if value else ""


def _save_timestamp(save_manager: SaveManager, story_id: str) -> str:
    try:
        save = save_manager.load(story_id)
    except (ValueError, KeyError, TypeError, OSError):
        return ""
    return _stamp(save.timestamp) if save else ""


def _found_endings(gallery_manager: GalleryManager, story_id: str) -> frozenset[str]:
    """Gallery endings for a chapter; a corrupt gallery file counts as nothing found."""
    try:
        return frozenset(gallery_manager.get_found(story_id))
    except (ValueError, TypeError, AttributeError, OSError):
        return frozenset()


def _build_progress(
    chapters: Iterable[ChapterInfo],
    save_manager: SaveManager,
    gallery_manager: GalleryManager,
) -> SagaProgress:
    saves: set[str] = set()
    seeds: set[str] = set()
    found: dict[str, frozenset[str]] = {}
    activity: dict[str, str] = {}
    for info in chapters:
        story_id = info.story_id
        stamps: list[str] = []
        if save_manager.has_save(story_id):
            saves.add(story_id)
            stamps.append(_save_timestamp(save_manager, story_id))
        record = save_manager.load_handoff(story_id)
        if record is not None:
            seeds.add(story_id)
            stamps.append(_stamp(record.timestamp))
        found[story_id] = _found_endings(gallery_manager, story_id)
        if stamps:
            activity[story_id] = max(stamps)
    return SagaProgress(frozenset(saves), frozenset(seeds), found, activity)


def _saga_fresh_run_state(
    story: Story,
    graph: SagaGraph,
    save_manager: SaveManager,
    display: Display,
    settings_name: str,
    seed_override: dict[str, bool | int | str] | None,
) -> Callable[[], dict[str, bool | int | str] | None]:
    """Provider for Engine's fresh_run_state: confirm, resolve the seed, erase last."""

    def provider() -> dict[str, bool | int | str] | None:
        at_risk = [
            cid
            for cid in sorted(graph.descendants(story.id))
            if save_manager.has_save(cid) or save_manager.has_handoff(cid)
        ]
        if at_risk:
            titles = [chapter_label_text(graph.chapter(cid)) for cid in at_risk]
            if not display.prompt_replay_confirm(titles):
                return None

        record = save_manager.load_handoff(story.id)
        if record is not None:
            seed = dict(record.state)
        elif story.name_prompt:
            resolved = _prompt_name_state(story, display, settings_name)
            if resolved is None:
                return None
            seed = resolved
        else:
            seed = {"player_name": settings_name}
        if record is None and seed_override:
            seed.update(seed_override)

        # The only mutation, and only once a seed exists. Best-effort: a file that cannot be
        # deleted (locked, read-only) is left behind rather than aborting the run half-erased;
        # the leftover is harmless and is erased again by the next replay.
        for cid in at_risk:
            for erase in (save_manager.delete, save_manager.delete_handoff):
                try:
                    erase(cid)
                except OSError:
                    pass
        return seed

    return provider


def _launch_story(
    path: Path,
    errors: dict[Path, str],
    save_manager: SaveManager,
    gallery_manager: GalleryManager,
    display: Display,
    *,
    graph: SagaGraph | None = None,
    seed_override: dict[str, bool | int | str] | None = None,
) -> ChainResult | None:
    if path in errors:
        display.show_picker_error(path.name, errors[path])
        return None
    try:
        story = StoryLoader.load(path)
    except StoryValidationError as e:
        errors[path] = str(e)
        display.show_picker_error(path.name, str(e))
        return None
    if story.warnings:
        if not display.show_content_warnings(story.title, story.warnings):
            return None
    settings_name = load_settings().get("player_name", "Felix")
    initial_state: dict[str, bool | int | str] = {"player_name": settings_name}
    known_chapter_ids: Iterable[str] = ()
    if story.saga_id and graph is not None:
        fresh_run_state = _saga_fresh_run_state(
            story, graph, save_manager, display, settings_name, seed_override
        )
        known_chapter_ids = graph.known_ids
    elif story.name_prompt:
        fresh_run_state = lambda: _prompt_name_state(story, display, settings_name)
    else:
        fresh_run_state = None
    result = Engine(
        story, save_manager, display, gallery_manager,
        initial_state=initial_state, fresh_run_state=fresh_run_state,
        known_chapter_ids=known_chapter_ids,
    ).run()
    display.clear_screen()
    return result


def _play_chapter(
    path: Path,
    errors: dict[Path, str],
    save_manager: SaveManager,
    gallery_manager: GalleryManager,
    display: Display,
    *,
    graph: SagaGraph,
    seed_override: dict[str, bool | int | str] | None,
) -> None:
    """Launch a chapter, then keep launching whatever it chains into."""
    result = _launch_story(
        path, errors, save_manager, gallery_manager, display,
        graph=graph, seed_override=seed_override,
    )
    while result is not None:
        info = graph.chapter(result.next_story)
        if info is None:
            return
        display.clear_screen()
        result = _launch_story(
            info.path, errors, save_manager, gallery_manager, display,
            graph=graph, seed_override=seed_override,
        )


def _duplicate_chapters(
    graph: SagaGraph | None, chapters: Sequence[ChapterInfo] | None
) -> dict[Path, tuple[ChapterInfo, ChapterInfo]]:
    """Files the graph rejected because their meta.id was already taken: path -> (loser, winner).

    `chapters` is the full list _collect_chapter_infos returned (it does not dedupe);
    SagaGraph.build keeps the first chapter per story id and drops the rest.
    """
    duplicates: dict[Path, tuple[ChapterInfo, ChapterInfo]] = {}
    if graph is None:
        return duplicates
    for info in chapters or ():
        winner = graph.chapter(info.story_id)
        if winner is not None and winner.path != info.path:
            duplicates[info.path] = (info, winner)
    return duplicates


def _saga_layout(
    graph: SagaGraph | None, chapters: Sequence[ChapterInfo] | None = None
) -> tuple[dict[Path, Saga], set[Path]]:
    """anchors: path -> the saga rendered there; hidden: chapter paths folded into a saga row.

    A duplicate-id file whose saga is in the graph is hidden too: it is a chapter of that
    saga, and the saga's own error row already reports the duplicate. A duplicate whose saga
    is NOT in the graph is left visible so _build_entries can show it as an error row.
    """
    anchors: dict[Path, Saga] = {}
    hidden: set[Path] = set()
    if graph is None:
        return anchors, hidden
    for path, (loser, _winner) in _duplicate_chapters(graph, chapters).items():
        if loser.saga_id in graph.sagas:
            hidden.add(path)
    for saga in graph.sagas.values():
        paths = [info.path for info in graph.chapters_of(saga)]
        anchor = graph.chapter(saga.entry).path if saga.entry else paths[0]
        anchors[anchor] = saga
        hidden.update(p for p in paths if p != anchor)
    return anchors, hidden


def _saga_entry(saga: Saga, graph: SagaGraph, progress: SagaProgress, index: int) -> dict:
    stats = graph.stats(saga, progress)
    anchor = graph.chapter(saga.entry) if saga.entry else graph.chapters_of(saga)[0]
    return {
        "index": index,
        "type": "saga",
        "saga_id": saga.saga_id,
        "path": anchor.path,
        "label": saga.title,
        "error": bool(saga.problems),
        "problems": list(saga.problems),
        "has_save": any(cid in progress.saves for cid in saga.chapters),
        "chapters_reached": stats.chapters_reached,
        "chapters_total": stats.chapters_total,
        "endings_found": stats.endings_found,
        "endings_total": stats.endings_total,
        "complete": graph.is_complete(saga, progress),
        "more_coming": saga.has_dangling,
        "author": anchor.author,
        "version": anchor.version,
    }


def _build_top_level_entries(
    root_paths: list[Path],
    folders: dict[str, list[Path]],
    errors: dict[Path, str],
    save_manager: SaveManager,
    gallery_manager: GalleryManager,
    graph: SagaGraph | None = None,
    progress: SagaProgress | None = None,
    chapters: Sequence[ChapterInfo] | None = None,
) -> list[dict]:
    entries = _build_entries(root_paths, errors, save_manager, gallery_manager, graph, progress, chapters)
    _anchors, hidden = _saga_layout(graph, chapters)
    index = len(entries)
    for name, paths in folders.items():
        visible = sum(1 for p in paths if p not in hidden)
        if visible == 0:
            continue
        index += 1
        entries.append({"index": index, "type": "folder", "label": name, "story_count": visible})
    return entries


def _build_entries(
    paths: list[Path],
    errors: dict[Path, str],
    save_manager: SaveManager,
    gallery_manager: GalleryManager,
    graph: SagaGraph | None = None,
    progress: SagaProgress | None = None,
    chapters: Sequence[ChapterInfo] | None = None,
) -> list[dict]:
    anchors, hidden = _saga_layout(graph, chapters)
    duplicates = _duplicate_chapters(graph, chapters)
    progress = progress or SagaProgress()
    entries: list[dict] = []
    for path in paths:
        if path in hidden:
            continue
        index = len(entries) + 1
        if path in anchors and graph is not None:
            entries.append(_saga_entry(anchors[path], graph, progress, index))
            continue
        if path in duplicates:  # saga-tagged file the graph did not adopt: never playable
            _loser, winner = duplicates[path]
            message = (
                f"duplicate story id '{winner.story_id}': already used by '{winner.path.name}', "
                "so this file is ignored"
            )
            entries.append(
                {"index": index, "label": path.stem, "error": True, "path": path, "message": message}
            )
            continue
        if path in errors:
            entries.append({"index": index, "label": path.stem, "error": True, "path": path})
            continue

        info = _load_story_info(path)
        title, story_id, node_count, ending_count, est_time, has_warnings, author, version = info

        has_save = False
        endings_found = 0
        if story_id:
            try:
                has_save = save_manager.has_save(story_id)
                endings_found = gallery_manager.get_count(story_id)
            except ValueError:
                pass

        entries.append({
            "index": index,
            "type": "story",
            "path": path,
            "label": title,
            "error": False,
            "has_save": has_save,
            "node_count": node_count,
            "ending_count": ending_count,
            "endings_found": endings_found,
            "est_time": est_time,
            "has_warnings": has_warnings,
            "author": author,
            "version": version,
        })
    return entries


def _home_row(info: ChapterInfo, progress: SagaProgress) -> dict:
    story_id = info.story_id
    if story_id in progress.saves:
        state = "active"
    elif story_id in progress.seeds:
        state = "ready"
    elif progress.found.get(story_id):
        state = "finished"
    else:
        state = "new"
    return {
        "label": chapter_label_text(info),
        "state": state,
        "endings_found": len(progress.found.get(story_id, ())),
        "endings_total": info.ending_count,
    }


def _run_saga_home(
    saga: Saga,
    graph: SagaGraph,
    errors: dict[Path, str],
    save_manager: SaveManager,
    gallery_manager: GalleryManager,
    display: Display,
    *,
    debug: bool = False,
    seed_override: dict[str, bool | int | str] | None = None,
) -> None:
    while True:
        infos = graph.chapters_of(saga)
        progress = _build_progress(infos, save_manager, gallery_manager)
        listed = list(saga.chapters) if debug else list(graph.reached(saga, progress))
        rows = [_home_row(graph.chapter(cid), progress) for cid in listed]
        default = graph.default_chapter(saga, progress)
        default_index = listed.index(default) + 1 if default in listed else 1
        display.clear_screen()
        display.show_saga_home(saga.title, rows, len(listed) < len(saga.chapters))
        selection = display.prompt_saga_select(len(rows), default_index)
        if selection == "back":
            display.clear_screen()
            return
        _play_chapter(
            graph.chapter(listed[selection - 1]).path, errors, save_manager, gallery_manager, display,
            graph=graph, seed_override=seed_override,
        )


def _open_entry(
    entry: dict,
    graph: SagaGraph,
    errors: dict[Path, str],
    save_manager: SaveManager,
    gallery_manager: GalleryManager,
    display: Display,
    *,
    debug: bool,
    seed_override: dict[str, bool | int | str] | None,
) -> None:
    if entry.get("type") == "saga":
        if entry.get("error"):
            display.show_picker_error(entry["label"], "; ".join(entry["problems"]))
            return
        _run_saga_home(
            graph.sagas[entry["saga_id"]], graph, errors, save_manager, gallery_manager, display,
            debug=debug, seed_override=seed_override,
        )
        return
    if entry.get("message"):  # a rejected duplicate-id chapter: report it, never launch it
        display.show_picker_error(entry["path"].name, entry["message"])
        return
    _play_chapter(
        entry["path"], errors, save_manager, gallery_manager, display,
        graph=graph, seed_override=seed_override,
    )


def _load_story_info(path: Path) -> tuple[str, str, int, int, str, bool, str, str]:
    try:
        s = StoryLoader.load(path)
        return (s.title, s.id, s.node_count, s.ending_count, s.est_time, bool(s.warnings), s.author, s.version)
    except StoryValidationError:
        return (path.stem, "", 0, 0, "", False, "", "")


def run() -> None:
    """Run the game, and leave quietly when the player wants out."""
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C, or the terminal window got closed on us. Progress is saved after
        # every choice, so there is nothing to rescue. Say goodbye instead of dumping
        # a page of stack trace on someone who only wanted to stop reading.
        print("\n  Goodbye.")


if __name__ == "__main__":
    run()
