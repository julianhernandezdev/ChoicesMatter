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


from scripts.audit_skill_tokens import (
    build_snapshot,
    format_delta,
    format_report,
    load_baseline,
    main,
    save_baseline,
)


# ---------------------------------------------------------------------------
# build_snapshot
# ---------------------------------------------------------------------------

def test_build_snapshot_computes_read_share_and_fruitless_rate() -> None:
    acc = AuditAccumulator()
    acc.tool_calls = {"Read": 100, "mcp__semble__search": 2}
    acc.semble_calls = 2
    acc.result_chars_by_tool = {"Read": 4000, "Grep": 1000}  # -> 1000 tok, 250 tok
    acc.grep_glob_total = 10
    acc.fruitless_grep_glob = 3
    acc.true_duplicate_reads = 7

    snapshot = build_snapshot(acc)

    assert snapshot["read_calls"] == 100
    assert snapshot["semble_calls"] == 2
    assert snapshot["read_share_of_exploration_tokens"] == 0.8  # 1000 / (1000 + 250)
    assert snapshot["fruitless_grep_glob_rate"] == 0.3
    assert snapshot["true_duplicate_reads"] == 7


def test_build_snapshot_handles_zero_totals() -> None:
    acc = AuditAccumulator()
    snapshot = build_snapshot(acc)
    assert snapshot["read_share_of_exploration_tokens"] == 0.0
    assert snapshot["fruitless_grep_glob_rate"] == 0.0


# ---------------------------------------------------------------------------
# baseline persistence
# ---------------------------------------------------------------------------

def test_load_baseline_missing_file_returns_none(tmp_path: Path) -> None:
    assert load_baseline(tmp_path / "does-not-exist.json") is None


def test_save_then_load_baseline_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "baseline.json"
    snapshot = {"read_calls": 1140, "semble_calls": 3}

    save_baseline(path, snapshot)
    loaded = load_baseline(path)

    assert loaded == snapshot


# ---------------------------------------------------------------------------
# format_delta / format_report
# ---------------------------------------------------------------------------

def test_format_delta_shows_before_and_after() -> None:
    baseline = {
        "read_calls": 1140, "semble_calls": 3,
        "read_share_of_exploration_tokens": 0.79,
        "fruitless_grep_glob_rate": 0.183,
        "true_duplicate_reads": 60,
    }
    current = {
        "read_calls": 900, "semble_calls": 40,
        "read_share_of_exploration_tokens": 0.55,
        "fruitless_grep_glob_rate": 0.10,
        "true_duplicate_reads": 20,
    }

    text = format_delta(current, baseline)

    assert "1140:3" in text
    assert "900:40" in text
    assert "79.0%" in text and "55.0%" in text


def test_format_report_lists_tool_calls() -> None:
    acc = AuditAccumulator()
    acc.tool_calls = {"Read": 5, "Grep": 2}
    acc.result_chars_by_tool = {"Read": 400}
    acc.result_calls_by_tool = {"Read": 5}
    acc.files_read_count = {"a.py": 3}

    text = format_report(acc)

    assert "Read" in text
    assert "a.py" in text


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def test_main_first_run_writes_baseline(tmp_path: Path) -> None:
    transcripts_dir = tmp_path / "transcripts"
    _write_transcript(transcripts_dir / "session.jsonl", [
        _assistant_entry(tool_uses=[{"id": "t1", "name": "Read", "input": {"file_path": "a.py"}}]),
    ])
    baseline_path = tmp_path / "baseline.json"

    exit_code = main(["--transcripts-dir", str(transcripts_dir)], baseline_path=baseline_path)

    assert exit_code == 0
    assert baseline_path.exists()
    assert load_baseline(baseline_path)["read_calls"] == 1


def test_main_second_run_prints_delta(tmp_path: Path, capsys) -> None:
    transcripts_dir = tmp_path / "transcripts"
    _write_transcript(transcripts_dir / "session.jsonl", [
        _assistant_entry(tool_uses=[{"id": "t1", "name": "Read", "input": {"file_path": "a.py"}}]),
    ])
    baseline_path = tmp_path / "baseline.json"
    save_baseline(baseline_path, build_snapshot(AuditAccumulator()))

    main(["--transcripts-dir", str(transcripts_dir)], baseline_path=baseline_path)

    captured = capsys.readouterr()
    assert "Delta vs baseline" in captured.out


def test_main_missing_transcripts_dir_returns_error(tmp_path: Path) -> None:
    exit_code = main(
        ["--transcripts-dir", str(tmp_path / "nope")],
        baseline_path=tmp_path / "baseline.json",
    )
    assert exit_code == 1
