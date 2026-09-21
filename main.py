from __future__ import annotations

import argparse
import math
from collections.abc import Callable, Iterable
from pathlib import Path

from src.display import Display
from src.engine import ChainResult, Engine
from src.gallery import GalleryManager
from src.saga import (
    ChapterInfo,
    SagaGraph,
    SagaProgress,
    chapter_info_from_story,
    chapter_label_text,
    parse_seed_arg,
)
from src.save import SaveManager
from src.config import load_settings
from src.story import Story, StoryLoader, StoryValidationError

STORIES_DIR = Path("stories")
SAVES_DIR = Path("saves")


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

        full_entries = _build_top_level_entries(root_paths, folders, errors, save_manager, gallery_manager)
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

        full_idx = start + (selection - 1)
        chosen_entry = full_entries[full_idx]

        if chosen_entry.get("type") == "folder":
            folder_name = chosen_entry["label"]
            folder_paths = folders[folder_name]
            chosen_path = _run_folder_picker(
                folder_name, folder_paths, errors, save_manager, gallery_manager, display
            )
            if chosen_path is None:
                continue
        else:
            chosen_path = root_paths[full_idx]

        _launch_story(chosen_path, errors, save_manager, gallery_manager, display)


def _run_folder_picker(
    folder_name: str,
    paths: list[Path],
    errors: dict[Path, str],
    save_manager: SaveManager,
    gallery_manager: GalleryManager,
    display: Display,
) -> Path | None:
    """Show the contents of a folder. Returns chosen Path or None (back)."""
    full_entries = _build_entries(paths, errors, save_manager, gallery_manager)
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
        full_idx = start + (selection - 1)
        chosen_entry = full_entries[full_idx]
        chosen_path = paths[full_idx]
        if chosen_entry.get("error"):
            display.show_picker_error(chosen_path.name, errors[chosen_path])
            continue
        return chosen_path


def _resolve_player_name(entered: str, name_default: str, settings_name: str) -> str | None:
    """Resolve the protagonist name after an empty name-prompt submission.

    Priority: typed name > saved settings player_name > story's name_default.
    The settings name wins over name_default because settings.json always
    resolves to a value (default "Felix") — name_default is a fallback only
    for the case where no saved player_name exists at all.
    """
    if entered:
        return entered
    if settings_name:
        return settings_name
    if name_default:
        return name_default
    return None


def _prompt_name_state(
    story: Story, display: Display, settings_name: str
) -> dict[str, bool | int | str] | None:
    """Run the protagonist name prompt for a fresh run.

    Returns the seed-state dict, or None when the player backed out (Q) or no
    name could be resolved. In the latter case the player has already been told.
    """
    entered = display.prompt_protagonist_name(story.name_prompt or "", prefill=settings_name)
    if entered is None:
        return None
    name = _resolve_player_name(entered, story.name_default or "", settings_name)
    if name is None:
        display.show_name_required()
        return None
    return {"player_name": name}


def _collect_chapter_infos(paths: Iterable[Path]) -> list[ChapterInfo]:
    """Load every story and keep the saga chapters. Stories that fail to load are skipped."""
    infos: list[ChapterInfo] = []
    for path in paths:
        try:
            story = StoryLoader.load(path)
        except StoryValidationError:
            continue
        if story.saga_id:
            infos.append(chapter_info_from_story(story))
    return infos


def _save_timestamp(save_manager: SaveManager, story_id: str) -> str:
    try:
        save = save_manager.load(story_id)
    except (ValueError, KeyError, TypeError, OSError):
        return ""
    return save.timestamp if save else ""


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
            stamps.append(record.timestamp)
        found[story_id] = frozenset(gallery_manager.get_found(story_id))
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

        for cid in at_risk:  # the only mutation, and only once a seed exists
            save_manager.delete(cid)
            save_manager.delete_handoff(cid)
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
    return result if isinstance(result, ChainResult) else None


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


def _build_top_level_entries(
    root_paths: list[Path],
    folders: dict[str, list[Path]],
    errors: dict[Path, str],
    save_manager: SaveManager,
    gallery_manager: GalleryManager,
) -> list[dict]:
    entries = _build_entries(root_paths, errors, save_manager, gallery_manager)
    offset = len(root_paths)
    for i, (name, paths) in enumerate(folders.items(), start=1):
        entries.append({
            "index": offset + i,
            "type": "folder",
            "label": name,
            "story_count": len(paths),
        })
    return entries


def _build_entries(
    paths: list[Path],
    errors: dict[Path, str],
    save_manager: SaveManager,
    gallery_manager: GalleryManager,
) -> list[dict]:
    entries = []
    for i, path in enumerate(paths, start=1):
        if path in errors:
            entries.append({"index": i, "label": path.stem, "error": True})
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
            "index": i,
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


def _load_story_info(path: Path) -> tuple[str, str, int, int, str, bool, str, str]:
    try:
        s = StoryLoader.load(path)
        return (s.title, s.id, s.node_count, s.ending_count, s.est_time, bool(s.warnings), s.author, s.version)
    except StoryValidationError:
        return (path.stem, "", 0, 0, "", False, "", "")


if __name__ == "__main__":
    main()
