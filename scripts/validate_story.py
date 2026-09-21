"""
Validate one or more story JSON files for structural and reachability issues.

Usage:
    python validate_story.py [--strict] <story.json> [<story.json> ...]

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
    4. Saga checks (cross-file, over the files passed) — chapter graph problems,
       dangling next_story, export and flag-provision warnings.  --strict
       promotes dangling links to ERROR.

Exit codes:
    0 — all files valid (warnings may be present)
    1 — one or more files have errors
    2 — no arguments provided
"""
import re
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.saga import ChapterInfo, SagaGraph, chapter_info_from_story
from src.story import Story, StoryLoader, StoryValidationError


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


_INLINE_FLAG_RE = re.compile(r"\{(\w+)\?")


def _flags_set(story: Story) -> set[str]:
    return {key for node in story.nodes.values() for choice in node.choices for key in choice.sets}


def _flags_needed(story: Story) -> dict[str, str]:
    """flag -> first node that needs it: a non-trivial `requires`, or an inline conditional."""
    needed: dict[str, str] = {}

    def scan(requires: dict, node_id: str) -> None:
        for flag, condition in requires.items():
            if condition is False:
                continue  # absence satisfies it
            if isinstance(condition, int) and not isinstance(condition, bool) and condition <= 0:
                continue  # absence satisfies a threshold of 0 or less
            needed.setdefault(flag, node_id)

    for node_id, node in story.nodes.items():
        for choice in node.choices:
            scan(choice.requires, node_id)
        for item in (*node.overlays, *node.insets):
            scan(item.requires, node_id)
        texts = [node.text, *(i.text for i in node.insets), *(o.text for o in node.overlays)]
        for text in texts:
            for match in _INLINE_FLAG_RE.finditer(text):
                needed.setdefault(match.group(1), node_id)
    return needed


def validate_sagas(paths: list[Path], strict: bool = False) -> tuple[list[str], list[str]]:
    """Cross-file saga checks over the files passed in. Returns (warnings, errors)."""
    warnings: list[str] = []
    errors: list[str] = []
    stories: dict[str, Story] = {}
    chapters: list[ChapterInfo] = []
    declared_in: dict[str, list[Path]] = {}
    seen_files: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen_files:
            continue  # the same file passed twice is not a duplicate id
        seen_files.add(resolved)
        try:
            story = StoryLoader.load(path)
        except StoryValidationError:
            continue  # already reported by validate_file
        if story.saga_id:
            stories.setdefault(story.id, story)
            chapters.append(chapter_info_from_story(story))
            declared_in.setdefault(story.id, []).append(path)
    if not chapters:
        return warnings, errors

    # SagaGraph drops a chapter whose meta.id repeats an earlier one, and a saga that
    # held only that chapter disappears without a message, so duplicate ids are detected
    # here directly. One ERROR per id; the graph's own copy of the message is skipped.
    duplicated = {sid: files for sid, files in declared_in.items() if len(files) > 1}
    for sid, files in duplicated.items():
        errors.append(
            f"duplicate meta.id '{sid}' among saga chapters, declared in: "
            + ", ".join(str(f) for f in files)
        )
    graph_duplicate_messages = {f"duplicate story id '{sid}'" for sid in duplicated}

    graph = SagaGraph.build(chapters)
    for saga in graph.sagas.values():
        for problem in saga.problems:
            if problem in graph_duplicate_messages:
                continue
            errors.append(f"saga '{saga.saga_id}': {problem}")
        if len(saga.chapters) < 2:
            warnings.append(
                f"saga '{saga.saga_id}': no sibling chapter among validated files "
                f"(only '{saga.chapters[0]}') — pass sibling chapters together to check "
                "saga-wide consistency"
            )
            continue

        members = {cid: graph.chapter(cid) for cid in saga.chapters}
        parent_exports: dict[str, set[str]] = {cid: set() for cid in saga.chapters}
        for info in members.values():
            for edge in info.edges:
                if edge.target in parent_exports:
                    parent_exports[edge.target].update(edge.exports)

        for cid, info in members.items():
            story = stories[cid]
            set_here = _flags_set(story)
            provided = set_here | parent_exports[cid] | {"player_name"}

            for edge in info.edges:
                if edge.target not in graph.known_ids:
                    message = (
                        f"chapter '{cid}' node '{edge.node_id}' next_story '{edge.target}' "
                        "matches no chapter among validated files"
                    )
                    (errors if strict else warnings).append(message)
                for name in edge.exports:
                    if name.startswith("visited_"):
                        target = stories.get(edge.target)
                        node = name[len("visited_"):]
                        if target is not None and edge.target in members and node in target.nodes:
                            errors.append(
                                f"chapter '{cid}' node '{edge.node_id}' exports '{name}', but "
                                f"chapter '{edge.target}' has its own node '{node}' "
                                "(the carried flag would read as a real visit)"
                            )
                    elif name not in set_here and name not in parent_exports[cid]:
                        warnings.append(
                            f"chapter '{cid}' node '{edge.node_id}' exports '{name}' but nothing "
                            f"in '{cid}' sets it and no parent chapter exports it"
                        )

            if not info.edges and not info.saga_end_nodes:
                warnings.append(
                    f"chapter '{cid}' has no chaining or saga_end ending, "
                    "so the saga cannot progress from it"
                )

            for flag, node_id in _flags_needed(story).items():
                if flag in provided:
                    continue
                if flag.startswith("visited_") and story.auto_visited_flags:
                    continue
                warnings.append(
                    f"chapter '{cid}' node '{node_id}' needs flag '{flag}' but the chapter never "
                    "sets it and no parent chapter exports it"
                )
    return warnings, errors


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    strict = "--strict" in args
    paths = [Path(p) for p in args if p != "--strict"]
    if not paths:
        print("Usage: python validate_story.py [--strict] <story.json> [...]", file=sys.stderr)
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

    saga_warnings, saga_errors = validate_sagas(paths, strict=strict)
    if saga_warnings or saga_errors:
        print("Saga checks:")
        for w in saga_warnings:
            print(f"  WARN  {w}")
        for e in saga_errors:
            print(f"  ERROR {e}")
    total_warnings += len(saga_warnings)
    total_errors += len(saga_errors)

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
