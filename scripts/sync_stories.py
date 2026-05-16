"""
Regenerate web/stories.json from the stories/ directory.

Walks stories/ recursively, skips examples/ and showcase/ (WIP stubs),
uses the immediate parent folder name as the category, sorts by story title,
and writes web/stories.json.

Usage:
    python scripts/sync_stories.py
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
STORIES_DIR = ROOT / "stories"
OUTPUT = ROOT / "web" / "stories.json"

SKIP_DIRS = {"examples", "showcase"}


def story_title(path: pathlib.Path) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("meta", {}).get("title") or path.stem
    except Exception:
        return path.stem


def main() -> int:
    entries = []
    for json_file in sorted(STORIES_DIR.rglob("*.json")):
        parts = json_file.relative_to(STORIES_DIR).parts
        if not parts:
            continue
        category = parts[0] if len(parts) > 1 else "uncategorized"
        if category in SKIP_DIRS:
            continue
        rel = json_file.relative_to(ROOT).as_posix()
        entries.append({"path": rel, "category": category, "_title": story_title(json_file)})

    entries.sort(key=lambda e: e["_title"].lower())
    for e in entries:
        del e["_title"]

    output = {"stories": entries}
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} stories to {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
