"""Pressing a key to skip the typing text, on Mac and Linux.

Three kinds of test live here:

1. Pretend keyboard. These load a second copy of display.py and tell it that
   it is on a Mac or Linux machine with a fake keyboard plugged in. They run
   everywhere, Windows included, so the Mac and Linux half of the code is
   never completely unwatched.
2. Real terminal. These start a small game inside a make-believe terminal and
   press real keys. Only Mac and Linux can do that, so Windows skips them.
3. Windows. A couple of checks that Windows still does what it always did.
"""
from __future__ import annotations

import importlib.util
import os
import signal
import subprocess
import sys
import time
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parent.parent
DISPLAY_FILE = REPO / "src" / "display.py"


# ------------------------------------------------------------------
# 1. Pretend keyboard (runs everywhere)
# ------------------------------------------------------------------

class PretendKeyboard:
    """Stands in for a Mac or Linux terminal. It remembers what was done to it."""

    FD = 7
    NORMAL = ["normal settings"]

    def __init__(self, is_keyboard: bool = True) -> None:
        self.is_keyboard = is_keyboard
        self.waiting: list[bytes] = []   # key presses nobody has picked up yet
        self.instant_keys = False        # True while keys arrive without Enter
        self.put_back: list = []         # every time the settings were restored
        self.binned = 0                  # times leftover keys were thrown away
        self.looked = 0                  # times anyone asked "is a key waiting?"
        self.reads = 0

    # the bits of termios / tty / os / select that display.py uses
    def tcgetattr(self, fd):
        assert fd == self.FD
        return list(self.NORMAL)

    def tcsetattr(self, fd, when, settings):
        assert fd == self.FD
        self.instant_keys = False
        self.put_back.append(settings)
        if when == "flush":
            self.waiting.clear()
            self.binned += 1

    def setcbreak(self, fd, when="flush"):
        assert fd == self.FD
        assert when != "flush", "keys pressed just before the text must still count"
        self.instant_keys = True

    def isatty(self, fd):
        return self.is_keyboard

    def select(self, readers, _w, _x, _timeout=None):
        self.looked += 1
        assert readers == [self.FD], "must watch the keyboard itself, nothing else"
        return (readers if self.waiting else [], [], [])

    def read(self, fd, _size):
        assert fd == self.FD
        self.reads += 1
        return self.waiting.pop(0)


def load_mac_linux_display(monkeypatch, keyboard: PretendKeyboard):
    """Load a private copy of display.py that believes it is not on Windows."""
    termios = types.ModuleType("termios")
    termios.TCSADRAIN = "drain"
    termios.TCSAFLUSH = "flush"
    termios.tcgetattr = keyboard.tcgetattr
    termios.tcsetattr = keyboard.tcsetattr
    tty = types.ModuleType("tty")
    tty.setcbreak = keyboard.setcbreak
    monkeypatch.setitem(sys.modules, "msvcrt", None)   # "this is not Windows"
    monkeypatch.setitem(sys.modules, "termios", termios)
    monkeypatch.setitem(sys.modules, "tty", tty)

    spec = importlib.util.spec_from_file_location("src._display_mac_linux_copy", DISPLAY_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    stdin = types.SimpleNamespace(fileno=lambda: keyboard.FD)
    monkeypatch.setattr(module, "sys", types.SimpleNamespace(stdin=stdin))
    monkeypatch.setattr(module, "_os", types.SimpleNamespace(isatty=keyboard.isatty, read=keyboard.read))
    monkeypatch.setattr(module, "_select", types.SimpleNamespace(select=keyboard.select))
    return module


def test_keys_arrive_without_enter_only_while_the_text_is_typing(monkeypatch):
    kb = PretendKeyboard()
    display = load_mac_linux_display(monkeypatch, kb)

    assert kb.instant_keys is False
    with display._listen_for_skip_key():
        assert kb.instant_keys is True
    assert kb.instant_keys is False
    assert kb.put_back == [PretendKeyboard.NORMAL]


def test_terminal_is_put_back_even_after_ctrl_c(monkeypatch):
    kb = PretendKeyboard()
    display = load_mac_linux_display(monkeypatch, kb)

    with pytest.raises(KeyboardInterrupt):
        with display._listen_for_skip_key():
            raise KeyboardInterrupt

    assert kb.instant_keys is False
    assert kb.put_back == [PretendKeyboard.NORMAL]
    assert display._key_pending() is False


def test_one_key_press_skips(monkeypatch):
    kb = PretendKeyboard()
    display = load_mac_linux_display(monkeypatch, kb)

    with display._listen_for_skip_key():
        assert display._key_pending() is False
        kb.waiting.append(b"x")
        assert display._key_pending() is True
        display._consume_key()
        assert kb.waiting == []
        assert display._key_pending() is False


@pytest.mark.parametrize("pieces", [
    [b"\x1b[A"],                # an arrow key, all at once
    [b"\x1b", b"[A"],           # the same arrow key, arriving in two parts
    [b"\n\n\n"],                # somebody leaning on Enter
    [b"x", b"\n"],              # a letter, then Enter out of habit
])
def test_nothing_is_left_behind_for_the_next_question(monkeypatch, pieces):
    kb = PretendKeyboard()
    display = load_mac_linux_display(monkeypatch, kb)

    with display._listen_for_skip_key():
        kb.waiting.extend(pieces)
        display._consume_key()
        assert kb.waiting == []


def test_key_pressed_in_the_last_moment_is_thrown_away(monkeypatch):
    """A key nobody got round to looking at must not answer the next question."""
    kb = PretendKeyboard()
    display = load_mac_linux_display(monkeypatch, kb)

    with display._listen_for_skip_key():
        kb.waiting.append(b"\n")

    assert kb.waiting == []
    assert kb.binned == 1


def test_a_closed_keyboard_does_not_hang_the_game(monkeypatch):
    kb = PretendKeyboard()
    display = load_mac_linux_display(monkeypatch, kb)
    # A terminal that went away keeps saying "ready" and keeps handing over nothing.
    monkeypatch.setattr(display._select, "select", lambda r, w, x, t=None: (r, [], []))
    monkeypatch.setattr(display._os, "read", lambda fd, size: b"")

    with display._listen_for_skip_key():
        display._consume_key()   # the test is that this line comes back at all


def test_input_from_a_file_or_another_program_is_left_alone(monkeypatch):
    kb = PretendKeyboard(is_keyboard=False)
    display = load_mac_linux_display(monkeypatch, kb)
    kb.waiting.append(b"1\n2\n")   # answers lined up for the questions later on

    with display._listen_for_skip_key():
        assert display._key_pending() is False
        display._consume_key()

    assert kb.waiting == [b"1\n2\n"]
    assert kb.put_back == [] and kb.looked == 0 and kb.reads == 0


@pytest.mark.parametrize("stdin", [
    None,                                                         # no input at all
    types.SimpleNamespace(fileno=MagicMock(side_effect=ValueError("no file number"))),
    types.SimpleNamespace(fileno=MagicMock(side_effect=OSError("closed"))),
])
def test_missing_or_odd_input_does_not_crash(monkeypatch, stdin):
    kb = PretendKeyboard()
    display = load_mac_linux_display(monkeypatch, kb)
    display.sys.stdin = stdin

    with display._listen_for_skip_key():
        assert display._key_pending() is False

    assert kb.put_back == []


def test_no_peeking_at_the_keyboard_outside_the_typing(monkeypatch):
    kb = PretendKeyboard()
    display = load_mac_linux_display(monkeypatch, kb)
    kb.waiting.append(b"1\n")

    assert display._key_pending() is False
    display._consume_key()

    assert kb.waiting == [b"1\n"]
    assert kb.looked == 0 and kb.reads == 0


def test_whole_typing_run_skips_and_cleans_up(monkeypatch):
    """The real typing loop, start to finish, with a key pressed part way through."""
    kb = PretendKeyboard()
    display = load_mac_linux_display(monkeypatch, kb)
    d = display.Display()
    d.console = MagicMock()
    d._cfg["typewriter"]["punctuation_pauses"] = {}

    shown: list[str] = []
    live = MagicMock()
    live.__enter__ = MagicMock(return_value=live)
    live.__exit__ = MagicMock(return_value=False)
    live.update = shown.append

    def player_gets_bored(_seconds):
        if len(shown) == 3:
            assert kb.instant_keys is True
            kb.waiting.append(b"\x1b[B")   # down arrow

    monkeypatch.setattr(display, "Live", MagicMock(return_value=live))
    monkeypatch.setattr(display, "time", types.SimpleNamespace(sleep=player_gets_bored))
    d._typewrite(lambda text: text, ["A long and winding sentence."], 0.0)

    assert shown[2] == "A l"
    assert shown[-1] == "A long and winding sentence."
    assert len(shown) == 4, "it should jump to the end, not keep typing"
    assert kb.waiting == []
    assert kb.instant_keys is False
    assert kb.put_back == [PretendKeyboard.NORMAL]


# ------------------------------------------------------------------
# 2. Real terminal (Mac and Linux only)
# ------------------------------------------------------------------

# A tiny game: one screen of text that takes 20 seconds to type out if nobody
# skips it, then one question. It reports what the question actually received.
PLAYER = r'''
import signal
import termios
from src.display import Display

signal.signal(signal.SIGINT, signal.default_int_handler)
d = Display()
d._cfg["typewriter"] = {"enabled": True, "delay_ms": 50, "pause_ms": 0, "punctuation_pauses": {}}
before = termios.tcgetattr(0)
try:
    d.show_node("Title", ["a" * 400])
except KeyboardInterrupt:
    print("INTERRUPTED", flush=True)
print("RESTORED:" + str(termios.tcgetattr(0) == before), flush=True)
answer = d.console.input("ANSWER> ")
print("GOT:" + repr(answer), flush=True)
'''

# Same idea with no terminal at all: the answers arrive down a pipe.
PIPED_PLAYER = r'''
from src.display import Display

d = Display()
d._cfg["typewriter"] = {"enabled": True, "delay_ms": 1, "pause_ms": 0, "punctuation_pauses": {}}
d.show_node("Title", ["abc"])
answer = d.console.input("ANSWER> ")
print("GOT:" + repr(answer), flush=True)
'''

needs_real_terminal = pytest.mark.skipif(
    sys.platform == "win32", reason="Windows has no make-believe terminals to test with"
)


class GameInATerminal:
    def __init__(self) -> None:
        import pty

        try:
            self.master, player_end = pty.openpty()
        except OSError:
            pytest.skip("this machine will not hand out a make-believe terminal")
        env = dict(os.environ, TERM="xterm-256color", COLUMNS="80", LINES="24", PYTHONIOENCODING="utf-8")
        self.proc = subprocess.Popen(
            [sys.executable, "-c", PLAYER],
            stdin=player_end, stdout=player_end, stderr=player_end,
            cwd=str(REPO), env=env, close_fds=True,
        )
        os.close(player_end)
        self.screen = b""

    def wait_for(self, words: bytes, seconds: float) -> bool:
        import select

        give_up = time.monotonic() + seconds
        while words not in self.screen:
            left = give_up - time.monotonic()
            if left <= 0 or not select.select([self.master], [], [], left)[0]:
                return False
            try:
                more = os.read(self.master, 4096)
            except OSError:   # Linux reports a closed terminal as an error
                return False
            if not more:      # a Mac reports it as nothing
                return False
            self.screen += more
        return True

    def press(self, keys: bytes) -> None:
        os.write(self.master, keys)

    def tail(self) -> str:
        return self.screen[-400:].decode("utf-8", "replace")

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait()
        os.close(self.master)


@pytest.fixture
def game():
    g = GameInATerminal()
    try:
        # The panel title showing up means the text has started typing.
        assert g.wait_for(b"Title", 30), g.tail()
        time.sleep(0.3)
        yield g
    finally:
        g.close()


@needs_real_terminal
def test_real_terminal_one_key_skips_without_enter(game):
    game.press(b"@")

    assert game.wait_for(b"ANSWER>", 8), "the key did not skip the text: " + game.tail()
    assert b"@" not in game.screen, "the key was printed into the story"
    assert b"RESTORED:True" in game.screen
    game.press(b"hello\n")
    assert game.wait_for(b"GOT:'hello'", 8), game.tail()


@needs_real_terminal
def test_real_terminal_enter_twice_does_not_answer_the_question(game):
    game.press(b"\n\n")

    assert game.wait_for(b"ANSWER>", 8), "Enter did not skip the text: " + game.tail()
    assert not game.wait_for(b"GOT:", 1.5), "a leftover Enter answered the question: " + game.tail()
    game.press(b"yes\n")
    assert game.wait_for(b"GOT:'yes'", 8), game.tail()


@needs_real_terminal
def test_real_terminal_arrow_key_is_swallowed_whole(game):
    game.press(b"\x1b[A")

    assert game.wait_for(b"ANSWER>", 8), "the arrow key did not skip the text: " + game.tail()
    game.press(b"north\n")
    assert game.wait_for(b"GOT:'north'", 8), game.tail()


@needs_real_terminal
def test_real_terminal_is_put_back_after_ctrl_c(game):
    game.proc.send_signal(signal.SIGINT)

    assert game.wait_for(b"INTERRUPTED", 8), game.tail()
    assert game.wait_for(b"RESTORED:True", 8), game.tail()


def test_answers_piped_in_reach_the_question_untouched():
    """Nobody is at the keyboard here. The first line must arrive whole."""
    done = subprocess.run(
        [sys.executable, "-c", PIPED_PLAYER],
        input=b"first\n", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=str(REPO), env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=60,
    )

    assert b"GOT:'first'" in done.stdout, done.stdout[-400:] + done.stderr[-400:]


# ------------------------------------------------------------------
# 3. Windows keeps doing what it always did
# ------------------------------------------------------------------

only_on_windows = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")


@only_on_windows
def test_windows_still_asks_windows_for_keys():
    import src.display as display

    keys = MagicMock()
    keys.kbhit.return_value = 1
    keys.getch.side_effect = [b"\xe0", b"H"]   # an arrow key is two pieces on Windows
    with patch.object(display, "_msvcrt", keys):
        assert display._key_pending() is True
        display._consume_key()

    assert keys.getch.call_count == 2


@only_on_windows
def test_windows_needs_no_terminal_setup():
    import src.display as display

    with patch.object(display, "_msvcrt", MagicMock()) as keys:
        with display._listen_for_skip_key():
            pass

    assert keys.mock_calls == []
