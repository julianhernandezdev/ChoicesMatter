"""
Audit Read/Grep/Glob/Bash/Agent/semble tool usage and token cost from this
project's Claude Code transcript history, to measure whether the
exploration-tooling guidance in CLAUDE.md is actually changing agent
behavior over time.

Usage:
    python scripts/audit_skill_tokens.py [--transcripts-dir PATH]

On first run, writes a baseline snapshot to
docs/projectmanagement/skill-token-baseline.json. On every subsequent run,
prints a delta against that baseline instead of overwriting it.

Read-only against ~/.claude/projects/ — the only file this script ever
writes is its own baseline snapshot.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


def derive_project_slug(cwd: str) -> str:
    """Convert an absolute project path to Claude Code's ~/.claude/projects
    folder-name convention, e.g. 'D:\\Project\\ChoicesMatter' ->
    'd--Project-ChoicesMatter': lowercase the drive letter, then replace
    ':' and path separators with '-'."""
    normalized = cwd.replace("/", "\\")
    if len(normalized) >= 2 and normalized[1] == ":":
        normalized = normalized[0].lower() + normalized[1:]
    return normalized.replace(":", "-").replace("\\", "-")


@dataclass
class AuditAccumulator:
    tool_calls: dict[str, int] = field(default_factory=dict)
    skill_calls: dict[str, int] = field(default_factory=dict)
    files_read_count: dict[str, int] = field(default_factory=dict)
    result_chars_by_tool: dict[str, int] = field(default_factory=dict)
    result_calls_by_tool: dict[str, int] = field(default_factory=dict)
    main_totals: dict[str, int] = field(
        default_factory=lambda: {"cache_creation": 0, "cache_read": 0, "input": 0, "output": 0}
    )
    sub_totals: dict[str, int] = field(
        default_factory=lambda: {"cache_creation": 0, "cache_read": 0, "input": 0, "output": 0}
    )
    sub_first_turn_cc: list[int] = field(default_factory=list)
    agent_dispatch_count: int = 0
    semble_calls: int = 0
    true_duplicate_reads: int = 0
    grep_glob_total: int = 0
    fruitless_grep_glob: int = 0

    _seen_reads: set = field(default_factory=set, repr=False)
    _seen_first_turn: bool = field(default=False, repr=False)
    _id_to_tool: dict = field(default_factory=dict, repr=False)

    def begin_file(self) -> None:
        """Reset per-transcript-file scratch state. Call once before
        processing each new transcript file."""
        self._seen_reads = set()
        self._seen_first_turn = False
        self._id_to_tool = {}

    def add_assistant_message(self, message: dict, is_subagent: bool) -> None:
        usage = message.get("usage", {}) or {}
        cc = usage.get("cache_creation_input_tokens", 0) or 0
        cr = usage.get("cache_read_input_tokens", 0) or 0
        ip = usage.get("input_tokens", 0) or 0
        op = usage.get("output_tokens", 0) or 0

        totals = self.sub_totals if is_subagent else self.main_totals
        totals["cache_creation"] += cc
        totals["cache_read"] += cr
        totals["input"] += ip
        totals["output"] += op

        if is_subagent and not self._seen_first_turn:
            self.sub_first_turn_cc.append(cc)
            self._seen_first_turn = True

        for block in message.get("content", []) or []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name", "?")
            self.tool_calls[name] = self.tool_calls.get(name, 0) + 1
            self._id_to_tool[block.get("id")] = name

            if name == "Agent":
                self.agent_dispatch_count += 1
            if name == "Skill":
                skill_name = (block.get("input", {}) or {}).get("skill", "?")
                self.skill_calls[skill_name] = self.skill_calls.get(skill_name, 0) + 1
            if "semble" in name.lower():
                self.semble_calls += 1
            if name in ("Grep", "Glob"):
                self.grep_glob_total += 1
            if name == "Read":
                inp = block.get("input", {}) or {}
                file_path = str(inp.get("file_path") or "?").replace("\\", "/").lower()
                self.files_read_count[file_path] = self.files_read_count.get(file_path, 0) + 1
                dup_key = (file_path, inp.get("offset"), inp.get("limit"))
                if dup_key in self._seen_reads:
                    self.true_duplicate_reads += 1
                else:
                    self._seen_reads.add(dup_key)

    def add_user_message(self, message: dict) -> None:
        for block in message.get("content", []) or []:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            tool_use_id = block.get("tool_use_id")
            name = self._id_to_tool.get(tool_use_id, "UNKNOWN")
            content = block.get("content", "")

            text = ""
            if isinstance(content, list):
                text = "".join(
                    part.get("text", "") for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                )
            elif isinstance(content, str):
                text = content

            self.result_chars_by_tool[name] = self.result_chars_by_tool.get(name, 0) + len(text)
            self.result_calls_by_tool[name] = self.result_calls_by_tool.get(name, 0) + 1

            if name in ("Grep", "Glob"):
                stripped = text.strip().lower()
                if len(stripped) < 40 and ("no files" in stripped or "no matches" in stripped or stripped == ""):
                    self.fruitless_grep_glob += 1


def read_jsonl(path: Path) -> Iterator[dict]:
    """Yield parsed JSON objects from a .jsonl file, skipping blank or
    malformed lines rather than raising."""
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def scan_project(transcripts_dir: Path) -> AuditAccumulator:
    """Walk every .jsonl transcript under transcripts_dir (main sessions and
    any */subagents/*.jsonl dispatch transcripts) and return the aggregated
    AuditAccumulator. Read-only: never writes to any file under
    transcripts_dir."""
    acc = AuditAccumulator()
    for path in sorted(transcripts_dir.rglob("*.jsonl")):
        is_subagent = "subagents" in path.parts
        acc.begin_file()
        for entry in read_jsonl(path):
            message = entry.get("message", {}) or {}
            entry_type = entry.get("type")
            if entry_type == "assistant":
                acc.add_assistant_message(message, is_subagent)
            elif entry_type == "user":
                acc.add_user_message(message)
    return acc
