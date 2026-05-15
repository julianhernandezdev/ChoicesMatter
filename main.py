from __future__ import annotations

from pathlib import Path

from display import Display
from engine import Engine
from gallery import GalleryManager
from save import SaveManager
from story import StoryLoader, StoryValidationError

STORIES_DIR = Path("stories")
SAVES_DIR = Path("saves")


def main() -> None:
    STORIES_DIR.mkdir(exist_ok=True)
    SAVES_DIR.mkdir(exist_ok=True)

    display = Display()
    display.clear_screen()
    display.show_title_screen()

    save_manager = SaveManager(SAVES_DIR)
    gallery_manager = GalleryManager(SAVES_DIR)
    errors: dict[Path, str] = {}

    while True:
        root_paths, folders = StoryLoader.discover_with_folders(STORIES_DIR)

        if not root_paths and not folders:
            display.show_no_stories()
            return

        entries = _build_top_level_entries(root_paths, folders, errors, save_manager, gallery_manager)
        display.show_story_picker(entries)

        total = len(root_paths) + len(folders)
        selection = display.prompt_story_select(total)
        if selection is None:
            return
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

        chosen_entry = entries[selection - 1]

        if chosen_entry.get("type") == "folder":
            folder_name = chosen_entry["label"]
            folder_paths = folders[folder_name]
            chosen_path = _run_folder_picker(
                folder_name, folder_paths, errors, save_manager, gallery_manager, display
            )
            if chosen_path is None:
                continue
        else:
            chosen_path = root_paths[selection - 1]

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
    while True:
        display.clear_screen()
        entries = _build_entries(paths, errors, save_manager, gallery_manager)
        display.show_story_picker(entries, title=f"📁 {folder_name}/")
        selection = display.prompt_story_select(len(paths), has_back=True)
        if selection is None or selection == "back":
            display.clear_screen()
            return None
        chosen_entry = entries[selection - 1]
        chosen_path = paths[selection - 1]
        if chosen_entry.get("error"):
            display.show_picker_error(chosen_path.name, errors[chosen_path])
            continue
        return chosen_path


def _launch_story(
    path: Path,
    errors: dict[Path, str],
    save_manager: SaveManager,
    gallery_manager: GalleryManager,
    display: Display,
) -> None:
    if path in errors:
        display.show_picker_error(path.name, errors[path])
        return
    try:
        story = StoryLoader.load(path)
    except StoryValidationError as e:
        errors[path] = str(e)
        display.show_picker_error(path.name, str(e))
        return
    if story.warnings:
        if not display.show_content_warnings(story.title, story.warnings):
            return
    Engine(story, save_manager, display, gallery_manager).run()
    display.clear_screen()


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
        title, story_id, node_count, ending_count, est_time, has_warnings = info

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
        })
    return entries


def _load_story_info(path: Path) -> tuple[str, str, int, int, str, bool]:
    try:
        s = StoryLoader.load(path)
        return (s.title, s.id, s.node_count, s.ending_count, s.est_time, bool(s.warnings))
    except StoryValidationError:
        return (path.stem, "", 0, 0, "", False)


if __name__ == "__main__":
    main()
