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
    display.show_title_screen()

    save_manager = SaveManager(SAVES_DIR)
    gallery_manager = GalleryManager(SAVES_DIR)
    errors: dict[Path, str] = {}

    while True:
        paths = StoryLoader.discover(STORIES_DIR)

        if not paths:
            display.show_no_stories()
            return

        display.show_story_picker(_build_entries(paths, errors, save_manager, gallery_manager))

        selection = display.prompt_story_select(len(paths))
        if selection is None:
            return
        if selection == "toggle_typewriter":
            display.toggle_typewriter()
            continue
        if selection == "clear":
            if display.prompt_clear_confirm():
                save_manager.clear_all()
                gallery_manager.clear_all()
                display.show_clear_complete()
            continue

        chosen_path = paths[selection - 1]

        if chosen_path in errors:
            display.show_picker_error(chosen_path.name, errors[chosen_path])
            continue

        try:
            story = StoryLoader.load(chosen_path)
        except StoryValidationError as e:
            errors[chosen_path] = str(e)
            display.show_picker_error(chosen_path.name, str(e))
            continue

        if story.warnings:
            if not display.show_content_warnings(story.title, story.warnings):
                continue

        Engine(story, save_manager, display, gallery_manager).run()


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
