from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _story_paths() -> list[str]:
    return sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "stories").glob("**/*.json")
    )


def test_web_manifest_lists_all_bundled_stories() -> None:
    manifest_path = ROOT / "web" / "stories.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert sorted(item["path"] for item in manifest["stories"]) == _story_paths()


def test_github_pages_entrypoint_references_web_player_assets() -> None:
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert '<main id="app"' in index
    assert 'web/style.css' in index
    assert 'web/app.js' in index
    assert 'assets/banner.png' in index
    assert 'Content-Security-Policy' in index
    assert 'https://julianhernandezdev.github.io/ChoicesMatter/' in readme


def test_web_player_is_static_and_persists_progress_in_browser() -> None:
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    assert 'fetch("web/stories.json")' in app
    assert "localStorage" in app
    assert "python" not in app.lower()
    assert "localhost" not in app.lower()


def test_css_has_terminal_palette() -> None:
    css = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
    for token in ("--bg", "--cyan", "--green", "--yellow", "--red", "--panel-border", "--dim"):
        assert token in css, f"Missing CSS variable: {token}"


def test_css_has_terminal_column() -> None:
    css = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
    assert "76ch" in css
    assert "Consolas" in css


def test_app_js_has_make_rule() -> None:
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert "function makeRule(" in app


def test_app_js_fixes_empty_style() -> None:
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert 'style === ""' in app


def test_app_js_has_resolve_color() -> None:
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert "function resolveColor(" in app


def test_app_js_has_settings_store() -> None:
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert "TYPEWRITER_DEFAULTS" in app
    assert "function loadTypewriterSettings(" in app
    assert "function saveTypewriterSettings(" in app


def test_app_js_has_typewriter() -> None:
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert "function startTypewriter(" in app
    assert "function skipTypewriter(" in app


def test_app_js_has_keyboard_handler() -> None:
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert "'keydown'" in app or '"keydown"' in app


def test_app_js_has_settings_screen() -> None:
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert "function renderSettings(" in app
    assert "SETTINGS_ROWS" in app
