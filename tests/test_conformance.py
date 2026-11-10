"""
Conformance suite runner.

conformance/*.json holds language-neutral vectors ("given this input, the
engine must produce this output"). Every case runs against both reference
engines: src/engine.py directly, and web/engine.js through Node. A future
GDScript port is correct when it passes the same files.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from src.engine import apply_sets, check_requires

ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE_DIR = ROOT / "conformance"

# suite name -> how the Python engine evaluates one case
PY_SUITES = {
    "requires": lambda c: check_requires(c["requires"], c["state"]),
    "sets": lambda c: apply_sets(c["sets"], c["state"]),
}


def _load(suite: str) -> dict:
    return json.loads((CONFORMANCE_DIR / f"{suite}.json").read_text(encoding="utf-8"))


def _canon(value: object) -> str:
    # Compare as canonical JSON so types are strict: in Python, 1 == True.
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


CASES = [
    pytest.param(suite, case, id=f"{suite}:{case['id']}")
    for suite in PY_SUITES
    for case in _load(suite)["cases"]
]


@pytest.fixture(scope="module")
def js_results() -> dict:
    result = subprocess.run(
        ["node", str(ROOT / "tests" / "conformance_runner.mjs")],
        capture_output=True,
        cwd=ROOT,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode()
    return json.loads(result.stdout.decode())


@pytest.mark.parametrize("suite,case", CASES)
def test_python_engine(suite: str, case: dict) -> None:
    assert _canon(PY_SUITES[suite](case)) == _canon(case["expect"]), case["why"]


@pytest.mark.parametrize("suite,case", CASES)
def test_web_engine(suite: str, case: dict, js_results: dict) -> None:
    assert _canon(js_results[suite][case["id"]]) == _canon(case["expect"]), case["why"]


def test_every_vector_file_has_a_runner() -> None:
    files = {p.stem for p in CONFORMANCE_DIR.glob("*.json")}
    assert files == set(PY_SUITES), "add the new suite to PY_SUITES and conformance_runner.mjs"


@pytest.mark.parametrize("suite", sorted(PY_SUITES))
def test_vector_file_is_well_formed(suite: str) -> None:
    data = _load(suite)
    assert data["suite"] == suite
    assert data["format"] == 1
    ids = [c["id"] for c in data["cases"]]
    assert len(ids) == len(set(ids)), "case ids must be unique"
    for case in data["cases"]:
        assert case.get("why"), f"{case['id']}: every case needs a 'why'"


def test_inputs_are_not_mutated() -> None:
    state = {"k": 1}
    apply_sets({"k": "+1"}, state)
    assert state == {"k": 1}
