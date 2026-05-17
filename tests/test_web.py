"""
Playwright tests for the Choices Matter web player.
Runs against the live GitHub Pages deployment.
"""
import re
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://julianhernandezdev.github.io/ChoicesMatter/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Clear localStorage before each test session."""
    return {**browser_context_args, "storage_state": None}


@pytest.fixture
def page_fresh(page: Page):
    """Navigate to the app with localStorage cleared."""
    page.goto(BASE_URL)
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_selector(".terminal-title-box", timeout=10000)
    return page


# ---------------------------------------------------------------------------
# 1. Page load
# ---------------------------------------------------------------------------

class TestPageLoad:
    def test_title_in_browser_tab(self, page_fresh: Page):
        expect(page_fresh).to_have_title("Choices Matter")

    def test_library_header_visible(self, page_fresh: Page):
        expect(page_fresh.locator(".terminal-title-box")).to_have_text("Choices Matter")

    def test_story_list_rendered(self, page_fresh: Page):
        items = page_fresh.locator(".terminal-list-item")
        assert items.count() > 0, "Expected at least one item in the library"

    def test_footer_hint_visible(self, page_fresh: Page):
        expect(page_fresh.locator(".footer-hint")).to_be_visible()

    def test_prompt_cursor_visible(self, page_fresh: Page):
        expect(page_fresh.locator(".terminal-cursor")).to_be_visible()

    def test_typewriter_toggle_label_visible(self, page_fresh: Page):
        expect(page_fresh.locator(".footer-typewriter")).to_be_visible()

    def test_folders_present(self, page_fresh: Page):
        """At least one folder entry (📁) should exist."""
        folders = page_fresh.locator("[data-action='open-folder']")
        assert folders.count() > 0, "Expected at least one folder in the library"


# ---------------------------------------------------------------------------
# 2. Folder navigation
# ---------------------------------------------------------------------------

class TestFolderNavigation:
    def _open_first_folder(self, page: Page):
        folder = page.locator("[data-action='open-folder']").first
        folder_name = folder.get_attribute("data-folder")
        folder.click()
        page.wait_for_selector(".terminal-list-item[data-action='pick-story']", timeout=5000)
        return folder_name

    def test_click_folder_shows_stories(self, page_fresh: Page):
        self._open_first_folder(page_fresh)
        stories = page_fresh.locator("[data-action='pick-story']")
        assert stories.count() > 0

    def test_folder_screen_shows_back_hint(self, page_fresh: Page):
        self._open_first_folder(page_fresh)
        hint = page_fresh.locator(".footer-hint")
        expect(hint).to_contain_text("back")

    def test_b_key_returns_to_library(self, page_fresh: Page):
        self._open_first_folder(page_fresh)
        page_fresh.keyboard.press("b")
        page_fresh.keyboard.press("Enter")
        page_fresh.wait_for_selector(".terminal-title-box", timeout=5000)
        expect(page_fresh.locator(".terminal-title-box")).to_be_visible()

    def test_keyboard_number_enters_folder(self, page_fresh: Page):
        """Typing '1' + Enter should open the first item (folder or story)."""
        page_fresh.keyboard.press("1")
        page_fresh.keyboard.press("Enter")
        # Should navigate somewhere (folder or story screen)
        page_fresh.wait_for_timeout(1000)
        # Prompt should still be visible
        expect(page_fresh.locator(".terminal-cursor")).to_be_visible()


# ---------------------------------------------------------------------------
# 3. Settings screen
# ---------------------------------------------------------------------------

class TestSettings:
    def _open_settings(self, page: Page):
        page.keyboard.press("s")
        page.keyboard.press("Enter")
        page.wait_for_selector(".terminal-settings-row", timeout=5000)

    def test_settings_opens_with_s_key(self, page_fresh: Page):
        self._open_settings(page_fresh)
        rows = page_fresh.locator(".terminal-settings-row")
        assert rows.count() > 0

    def test_settings_has_enabled_row(self, page_fresh: Page):
        self._open_settings(page_fresh)
        text = page_fresh.locator(".terminal-list").inner_text()
        assert "Enabled" in text

    def test_settings_has_speed_row(self, page_fresh: Page):
        self._open_settings(page_fresh)
        text = page_fresh.locator(".terminal-list").inner_text()
        assert "Speed" in text

    def test_settings_has_page_size_row(self, page_fresh: Page):
        self._open_settings(page_fresh)
        text = page_fresh.locator(".terminal-list").inner_text()
        assert "Stories per page" in text

    def test_discard_returns_to_library(self, page_fresh: Page):
        self._open_settings(page_fresh)
        page_fresh.keyboard.press("x")
        page_fresh.keyboard.press("Enter")
        page_fresh.wait_for_selector(".terminal-title-box", timeout=5000)
        expect(page_fresh.locator(".terminal-title-box")).to_be_visible()


# ---------------------------------------------------------------------------
# 4. Typewriter toggle
# ---------------------------------------------------------------------------

class TestTypewriterToggle:
    def _get_tw_state(self, page: Page) -> str:
        el = page.locator(".tw-state-on, .tw-state-off").first
        return el.inner_text()

    def test_t_key_toggles_typewriter(self, page_fresh: Page):
        state_before = self._get_tw_state(page_fresh)
        page_fresh.keyboard.press("t")
        page_fresh.keyboard.press("Enter")
        state_after = self._get_tw_state(page_fresh)
        assert state_before != state_after, f"Expected typewriter to toggle; was '{state_before}' → '{state_after}'"

    def test_t_key_toggles_back(self, page_fresh: Page):
        state_original = self._get_tw_state(page_fresh)
        page_fresh.keyboard.press("t")
        page_fresh.keyboard.press("Enter")
        page_fresh.keyboard.press("t")
        page_fresh.keyboard.press("Enter")
        state_after = self._get_tw_state(page_fresh)
        assert state_after == state_original


# ---------------------------------------------------------------------------
# 5. Gameplay — entering and playing a story
# ---------------------------------------------------------------------------

class TestGameplay:
    def _enter_first_story_in_folder(self, page: Page):
        """Open first folder then pick first story; return to game screen."""
        page.locator("[data-action='open-folder']").first.click()
        page.wait_for_selector("[data-action='pick-story']", timeout=5000)
        page.keyboard.press("1")
        page.keyboard.press("Enter")
        # Handle content warning if present
        page.wait_for_timeout(800)
        if page.locator(".warning-panel").count():
            page.keyboard.press("y")
            page.keyboard.press("Enter")
            page.wait_for_timeout(500)
        # Handle resume prompt if present
        if "A save was found" in (page.locator(".terminal-prose").first.inner_text() if page.locator(".terminal-prose").count() else ""):
            page.keyboard.press("n")
            page.keyboard.press("Enter")
            page.wait_for_timeout(500)
        page.wait_for_selector(".terminal-panel", timeout=8000)

    def test_story_panel_appears(self, page_fresh: Page):
        self._enter_first_story_in_folder(page_fresh)
        expect(page_fresh.locator(".terminal-panel")).to_be_visible()

    def test_prose_text_is_not_empty(self, page_fresh: Page):
        self._enter_first_story_in_folder(page_fresh)
        prose = page_fresh.locator(".terminal-prose").first
        assert len(prose.inner_text().strip()) > 0

    def test_choices_are_visible(self, page_fresh: Page):
        self._enter_first_story_in_folder(page_fresh)
        choices = page_fresh.locator(".terminal-choice")
        assert choices.count() > 0

    def test_choice_numbers_rendered(self, page_fresh: Page):
        self._enter_first_story_in_folder(page_fresh)
        first_num = page_fresh.locator(".choice-num").first
        assert re.match(r"^\d+\.$", first_num.inner_text().strip())

    def test_prompt_shows_game_hint(self, page_fresh: Page):
        self._enter_first_story_in_folder(page_fresh)
        prompt = page_fresh.locator(".terminal-prompt-line")
        expect(prompt).to_contain_text("choice")

    def test_click_choice_advances_story(self, page_fresh: Page):
        self._enter_first_story_in_folder(page_fresh)
        prose_before = page_fresh.locator(".terminal-prose").first.inner_text()
        page_fresh.locator(".terminal-choice").first.click()
        page_fresh.wait_for_timeout(500)
        prose_after = page_fresh.locator(".terminal-prose").first.inner_text()
        # Either the prose changed or we hit an ending
        advanced = (prose_before != prose_after) or page_fresh.locator(".terminal-ending-label").count() > 0
        assert advanced, "Clicking a choice should advance the story or reach an ending"

    def test_keyboard_choice_advances_story(self, page_fresh: Page):
        self._enter_first_story_in_folder(page_fresh)
        prose_before = page_fresh.locator(".terminal-prose").first.inner_text()
        page_fresh.keyboard.press("1")
        page_fresh.keyboard.press("Enter")
        page_fresh.wait_for_timeout(500)
        prose_after = page_fresh.locator(".terminal-prose").first.inner_text()
        advanced = (prose_before != prose_after) or page_fresh.locator(".terminal-ending-label").count() > 0
        assert advanced

    def test_q_returns_to_library(self, page_fresh: Page):
        self._enter_first_story_in_folder(page_fresh)
        page_fresh.keyboard.press("q")
        page_fresh.keyboard.press("Enter")
        page_fresh.wait_for_selector(".terminal-title-box", timeout=5000)
        expect(page_fresh.locator(".terminal-title-box")).to_be_visible()


# ---------------------------------------------------------------------------
# 6. Mobile keyboard button
# ---------------------------------------------------------------------------

class TestMobileKeyboard:
    def test_mobile_keyboard_button_visible(self, page_fresh: Page):
        expect(page_fresh.locator(".mobile-keyboard-btn").first).to_be_visible()


# ---------------------------------------------------------------------------
# 7. Keyboard — arrow key pagination
# ---------------------------------------------------------------------------

class TestPagination:
    def test_arrow_down_does_not_crash(self, page_fresh: Page):
        """ArrowDown should either paginate or do nothing, but not crash."""
        page_fresh.keyboard.press("ArrowDown")
        page_fresh.wait_for_timeout(300)
        expect(page_fresh.locator(".terminal-cursor")).to_be_visible()

    def test_arrow_up_does_not_crash(self, page_fresh: Page):
        page_fresh.keyboard.press("ArrowUp")
        page_fresh.wait_for_timeout(300)
        expect(page_fresh.locator(".terminal-cursor")).to_be_visible()


# ---------------------------------------------------------------------------
# 8. Content Security Policy / no console errors
# ---------------------------------------------------------------------------

class TestNoBrokenAssets:
    def test_no_404_errors(self, page: Page):
        failed_urls = []

        def on_response(response):
            if response.status == 404:
                failed_urls.append(response.url)

        page.on("response", on_response)
        page.goto(BASE_URL)
        page.wait_for_selector(".terminal-title-box", timeout=10000)
        assert not failed_urls, f"404 responses for: {failed_urls}"

    def test_no_js_errors_on_load(self, page: Page):
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE_URL)
        page.wait_for_selector(".terminal-title-box", timeout=10000)
        assert not errors, f"JavaScript errors on load: {errors}"


# ---------------------------------------------------------------------------
# Debug mode
# ---------------------------------------------------------------------------

class TestDebugMode:
    """
    Tests for the - key debug mode toggle.
    Run after deploy: requires .debug-panel, .debug-tag CSS classes in production.
    """

    def _navigate_to_game(self, page: Page) -> None:
        """Get to a game node: open first folder, pick first story, skip warnings/resume."""
        # Step 1: open the first folder
        page.locator("[data-action='open-folder']").first.click()
        page.wait_for_selector("[data-action='pick-story']", timeout=5000)
        # Step 2: select the first story in the folder
        page.keyboard.press("1")
        page.keyboard.press("Enter")
        # Step 3: handle content warning if present
        page.wait_for_timeout(800)
        if page.locator(".warning-panel").count():
            page.keyboard.press("y")
            page.keyboard.press("Enter")
            page.wait_for_timeout(500)
        # Step 4: handle resume prompt if present (start fresh for predictable state)
        if "A save was found" in (page.locator(".terminal-prose").first.inner_text() if page.locator(".terminal-prose").count() else ""):
            page.keyboard.press("n")
            page.keyboard.press("Enter")
            page.wait_for_timeout(500)
        # Step 5: wait for choices to confirm we're at a game node
        page.wait_for_selector(".terminal-choice", timeout=8000)

    def test_debug_panel_hidden_by_default(self, page_fresh: Page):
        self._navigate_to_game(page_fresh)
        expect(page_fresh.locator(".debug-panel")).to_have_count(0)

    def test_dash_shows_debug_panel(self, page_fresh: Page):
        self._navigate_to_game(page_fresh)
        page_fresh.keyboard.press("-")
        expect(page_fresh.locator(".debug-panel")).to_be_visible()

    def test_dash_cycles_through_three_states(self, page_fresh: Page):
        self._navigate_to_game(page_fresh)
        # State 1: author mode — panel visible
        page_fresh.keyboard.press("-")
        expect(page_fresh.locator(".debug-panel")).to_be_visible()
        # State 2: all mode — panel still visible
        page_fresh.keyboard.press("-")
        expect(page_fresh.locator(".debug-panel")).to_be_visible()
        # State 3: off — panel gone
        page_fresh.keyboard.press("-")
        expect(page_fresh.locator(".debug-panel")).to_have_count(0)

    def test_dash_ignored_on_library_screen(self, page_fresh: Page):
        # On library screen, - should not open a debug panel
        page_fresh.keyboard.press("-")
        expect(page_fresh.locator(".debug-panel")).to_have_count(0)
