"""Guard: CLAUDE.md must keep naming every Display method and every src module.

CLAUDE.md is the contributor-facing map of the codebase. When a public Display
method or a src/ module is added without a matching mention, this fails so the
doc is updated in the same change instead of drifting silently.
"""
import inspect
from pathlib import Path

import pytest

from src.display import Display

ROOT = Path(__file__).resolve().parents[1]
CLAUDE_MD = ROOT / "CLAUDE.md"

pytestmark = pytest.mark.skipif(not CLAUDE_MD.exists(), reason="CLAUDE.md not present")


def _doc() -> str:
    return CLAUDE_MD.read_text(encoding="utf-8")


def test_claude_md_mentions_every_public_display_method() -> None:
    doc = _doc()
    public = [
        name
        for name, _ in inspect.getmembers(Display, inspect.isfunction)
        if not name.startswith("_")
    ]
    missing = [name for name in public if f"`{name}(" not in doc]
    assert not missing, f"CLAUDE.md Display Layer table is missing: {missing}"


def test_claude_md_mentions_every_src_module() -> None:
    doc = _doc()
    modules = [p.name for p in (ROOT / "src").glob("*.py") if p.name != "__init__.py"]
    missing = [name for name in modules if f"`src/{name}`" not in doc]
    assert not missing, f"CLAUDE.md does not mention: {missing}"
