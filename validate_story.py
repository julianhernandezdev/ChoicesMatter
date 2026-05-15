"""
Validate one or more story JSON files for structural and reachability issues.

Usage:
    python validate_story.py <story.json> [<story.json> ...]

Checks performed (in order):
    1. Schema validation via StoryLoader — invalid JSON, missing fields, bad
       next references, etc.  Any StoryValidationError is reported as an ERROR.
    2. Reachability — BFS from start_node following all choice.next values
       (requires is ignored; static analysis only).  Nodes defined in the file
       but unreachable from start_node are reported as WARNings.
    3. Dead-end detection — reachable nodes with an empty choices array and no
       is_ending marker are reported as ERRORs.  (The engine treats empty
       choices as an implicit ending, but the missing marker is almost always
       an authoring mistake.)

Exit codes:
    0 — all files valid (warnings may be present)
    1 — one or more files have errors
    2 — no arguments provided
"""
import sys
from collections import deque
from pathlib import Path

from story import Story, StoryLoader, StoryValidationError


def reachable_nodes(story: Story) -> set[str]:
    """BFS from start_node; all choice.next values are treated as reachable."""
    seen: set[str] = set()
    queue: deque[str] = deque([story.start_node])
    while queue:
        node_id = queue.popleft()
        if node_id in seen:
            continue
        seen.add(node_id)
        node = story.nodes.get(node_id)
        if node is None:
            continue
        for choice in node.choices:
            if choice.next not in seen:
                queue.append(choice.next)
    return seen


def validate_file(path: Path) -> tuple[list[str], list[str]]:
    """Return (warnings, errors) for one story file."""
    warnings: list[str] = []
    errors: list[str] = []

    try:
        story = StoryLoader.load(path)
    except StoryValidationError as exc:
        errors.append(str(exc))
        return warnings, errors

    reachable = reachable_nodes(story)

    for node_id in sorted(story.nodes):
        if node_id not in reachable:
            warnings.append(f"unreachable node: '{node_id}'")

    for node_id in sorted(reachable):
        node = story.nodes[node_id]
        if not node.choices and not node.is_ending:
            errors.append(f"dead-end node (no is_ending): '{node_id}'")

    return warnings, errors


def main() -> int:
    paths = [Path(p) for p in sys.argv[1:]]
    if not paths:
        print("Usage: python validate_story.py <story.json> [...]", file=sys.stderr)
        return 2

    total_warnings = 0
    total_errors = 0

    for path in paths:
        print(f"Validating {path} ...", end=" ", flush=True)
        warnings, errors = validate_file(path)

        if not warnings and not errors:
            print("OK")
        else:
            print()
            for w in warnings:
                print(f"  WARN  {w}")
            for e in errors:
                print(f"  ERROR {e}")

        total_warnings += len(warnings)
        total_errors += len(errors)

    if len(paths) > 1:
        parts = []
        if total_errors:
            parts.append(f"{total_errors} error{'s' if total_errors != 1 else ''}")
        if total_warnings:
            parts.append(f"{total_warnings} warning{'s' if total_warnings != 1 else ''}")
        print()
        print(", ".join(parts) if parts else "All files OK")

    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
