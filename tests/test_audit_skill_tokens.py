from scripts.audit_skill_tokens import derive_project_slug


# ---------------------------------------------------------------------------
# derive_project_slug
# ---------------------------------------------------------------------------

def test_derive_project_slug_backslash_path() -> None:
    assert derive_project_slug(r"D:\Project\ChoicesMatter") == "d--Project-ChoicesMatter"


def test_derive_project_slug_forward_slash_path() -> None:
    assert derive_project_slug("D:/Project/ChoicesMatter") == "d--Project-ChoicesMatter"


def test_derive_project_slug_lowercases_only_drive_letter() -> None:
    assert derive_project_slug(r"C:\Users\julia\SomeProject") == "c--Users-julia-SomeProject"


import json
from pathlib import Path

from scripts.audit_skill_tokens import AuditAccumulator, scan_project


# ---------------------------------------------------------------------------
# fixture helpers
# ---------------------------------------------------------------------------

def _assistant_entry(tool_uses=None, usage=None) -> dict:
    return {
        "type": "assistant",
        "message": {
            "usage": usage or {},
            "content": [
                {"type": "tool_use", "id": tu["id"], "name": tu["name"], "input": tu.get("input", {})}
                for tu in (tool_uses or [])
            ],
        },
    }


def _user_entry(tool_results) -> dict:
    return {
        "type": "user",
        "message": {
            "content": [
                {"type": "tool_result", "tool_use_id": tr["id"], "content": tr["content"]}
                for tr in tool_results
            ],
        },
    }


def _write_transcript(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")


# ---------------------------------------------------------------------------
# scan_project
# ---------------------------------------------------------------------------

def test_scan_project_counts_tool_calls(tmp_path: Path) -> None:
    entries = [
        _assistant_entry(tool_uses=[
            {"id": "t1", "name": "Read", "input": {"file_path": "a.py"}},
            {"id": "t2", "name": "mcp__semble__search", "input": {"query": "how does x work"}},
        ]),
    ]
    _write_transcript(tmp_path / "session.jsonl", entries)

    acc = scan_project(tmp_path)

    assert acc.tool_calls["Read"] == 1
    assert acc.tool_calls["mcp__semble__search"] == 1
    assert acc.semble_calls == 1


def test_scan_project_detects_true_duplicate_read(tmp_path: Path) -> None:
    entries = [
        _assistant_entry(tool_uses=[
            {"id": "t1", "name": "Read", "input": {"file_path": "a.py", "offset": None, "limit": None}},
        ]),
        _assistant_entry(tool_uses=[
            {"id": "t2", "name": "Read", "input": {"file_path": "a.py", "offset": None, "limit": None}},
        ]),
        _assistant_entry(tool_uses=[
            {"id": "t3", "name": "Read", "input": {"file_path": "a.py", "offset": 200, "limit": 100}},
        ]),
    ]
    _write_transcript(tmp_path / "session.jsonl", entries)

    acc = scan_project(tmp_path)

    assert acc.files_read_count["a.py"] == 3
    # t2 repeats t1's exact (file, offset, limit) -> 1 true duplicate.
    # t3 uses a different range -> legitimate pagination, not a duplicate.
    assert acc.true_duplicate_reads == 1


def test_scan_project_subagent_vs_main_totals(tmp_path: Path) -> None:
    main_entries = [_assistant_entry(usage={"cache_creation_input_tokens": 100, "output_tokens": 10})]
    sub_entries = [_assistant_entry(usage={"cache_creation_input_tokens": 5000, "output_tokens": 50})]
    _write_transcript(tmp_path / "main.jsonl", main_entries)
    _write_transcript(tmp_path / "subagents" / "agent-a1.jsonl", sub_entries)

    acc = scan_project(tmp_path)

    assert acc.main_totals["cache_creation"] == 100
    assert acc.sub_totals["cache_creation"] == 5000


def test_scan_project_records_first_turn_cold_start_once(tmp_path: Path) -> None:
    sub_entries = [
        _assistant_entry(usage={"cache_creation_input_tokens": 19000}),
        _assistant_entry(usage={"cache_creation_input_tokens": 500}),
    ]
    _write_transcript(tmp_path / "subagents" / "agent-a1.jsonl", sub_entries)

    acc = scan_project(tmp_path)

    assert acc.sub_first_turn_cc == [19000]


def test_scan_project_fruitless_grep_glob(tmp_path: Path) -> None:
    entries = [
        _assistant_entry(tool_uses=[
            {"id": "t1", "name": "Grep", "input": {"pattern": "found_thing"}},
            {"id": "t2", "name": "Grep", "input": {"pattern": "missing_thing"}},
        ]),
        _user_entry([
            {"id": "t1", "content": "src/a.py:1:found_thing here"},
            {"id": "t2", "content": "No matches found"},
        ]),
    ]
    _write_transcript(tmp_path / "session.jsonl", entries)

    acc = scan_project(tmp_path)

    assert acc.grep_glob_total == 2
    assert acc.fruitless_grep_glob == 1


def test_scan_project_ignores_blank_and_malformed_lines(tmp_path: Path) -> None:
    path = tmp_path / "session.jsonl"
    path.write_text('\n{"type": "assistant", "message": {}}\n\nnot json at all\n', encoding="utf-8")

    acc = scan_project(tmp_path)  # must not raise

    assert acc.tool_calls == {}
