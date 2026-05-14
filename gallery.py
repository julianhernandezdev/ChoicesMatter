from __future__ import annotations

import json
import re
from pathlib import Path

_SAFE_STORY_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


class GalleryManager:
    def __init__(self, saves_dir: Path) -> None:
        self.saves_dir = saves_dir
        saves_dir.mkdir(parents=True, exist_ok=True)

    def _gallery_path(self, story_id: str) -> Path:
        if not isinstance(story_id, str) or not _SAFE_STORY_ID.fullmatch(story_id):
            raise ValueError("story_id may only contain letters, numbers, dots, underscores, and hyphens")
        return self.saves_dir / f"{story_id}.gallery.json"

    def record_ending(self, story_id: str, node_id: str) -> None:
        found = self.get_found(story_id)
        found.add(node_id)
        path = self._gallery_path(story_id)
        path.write_text(
            json.dumps({"story_id": story_id, "endings_found": sorted(found)}, indent=2),
            encoding="utf-8",
        )

    def get_found(self, story_id: str) -> set[str]:
        path = self._gallery_path(story_id)
        if not path.exists():
            return set()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return set(data.get("endings_found", []))
        except (json.JSONDecodeError, KeyError):
            return set()

    def get_count(self, story_id: str) -> int:
        return len(self.get_found(story_id))

    def clear_all(self) -> None:
        for p in self.saves_dir.glob("*.gallery.json"):
            p.unlink()
