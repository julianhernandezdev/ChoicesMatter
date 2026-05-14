from __future__ import annotations

from pathlib import Path

from display import Display
from engine import Engine
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
    errors: dict[Path, str] = {}

    while True:
        paths = StoryLoader.discover(STORIES_DIR)

        if not paths:
            display.show_no_stories()
            return

        display.show_story_picker(_build_entries(paths, errors))

        selection = display.prompt_story_select(len(paths))
        if selection is None:
            return

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

        Engine(story, save_manager, display).run()


def _build_entries(paths: list[Path], errors: dict[Path, str]) -> list[dict]:
    entries = []
    for i, path in enumerate(paths, start=1):
        if path in errors:
            entries.append({"index": i, "label": path.stem, "error": True})
        else:
            entries.append({"index": i, "label": _get_title(path), "error": False})
    return entries


def _get_title(path: Path) -> str:
    try:
        return StoryLoader.load(path).title
    except StoryValidationError:
        return path.stem


if __name__ == "__main__":
    main()
