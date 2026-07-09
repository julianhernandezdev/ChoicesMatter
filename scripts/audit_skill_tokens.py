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
