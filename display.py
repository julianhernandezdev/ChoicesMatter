from __future__ import annotations

import sys
import time

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich import box

from config import load_settings
from story import Choice, Inset, Overlay

try:
    import msvcrt as _msvcrt

    def _key_pending() -> bool:
        return bool(_msvcrt.kbhit())

    def _consume_key() -> None:
        key = _msvcrt.getch()
        if key in (b"\x00", b"\xe0"):  # special key — consume the second byte too
            _msvcrt.getch()

except ImportError:
    import select as _select

    def _key_pending() -> bool:
        return bool(_select.select([sys.stdin], [], [], 0)[0])

    def _consume_key() -> None:
        sys.stdin.read(1)

_ENDING_COLORS = {
    "good": "bright_green",
    "bad": "bright_red",
    "neutral": "bright_yellow",
}

_MODIFIERS = ("bold", "dim", "italic", "underline", "strike")

_PUNCTUATION_PAUSE = {".": 0.15, "!": 0.15, "?": 0.15, "…": 0.20}


class Display:
    def __init__(self) -> None:
        self.console = Console()
        self._cfg = load_settings()

    # ------------------------------------------------------------------
    # Title / chrome
    # ------------------------------------------------------------------

    def show_title_screen(self) -> None:
        self.console.print()
        self.console.print(
            Panel(
                Text("Choices Matter", justify="center", style="bold white"),
                subtitle="A text adventure engine",
                border_style="cyan",
                box=box.DOUBLE,
                padding=(1, 4),
            )
        )
        self.console.print()

    # ------------------------------------------------------------------
    # Story picker
    # ------------------------------------------------------------------

    def show_no_stories(self) -> None:
        self.console.print(
            Panel(
                "[yellow]No stories found in the [bold]/stories[/bold] directory.\n"
                "Drop a .json story file there and relaunch.[/yellow]",
                border_style="yellow",
                title="No Stories Loaded",
            )
        )

    def show_story_picker(self, entries: list[dict]) -> None:
        self.console.print(Rule("[bold cyan]Select a Story[/bold cyan]"))
        self.console.print()
        for entry in entries:
            num = entry["index"]
            label = entry["label"]
            if entry.get("error"):
                self.console.print(f"  [dim]{num}.[/dim] [red]{label}  [italic]-ERROR[/italic][/red]")
            else:
                resume = "  [bold green]● RESUME[/bold green]" if entry.get("has_save") else ""
                self.console.print(f"  [bold cyan]{num}.[/bold cyan]  {label}{resume}")
                node_count = entry.get("node_count", 0)
                ending_count = entry.get("ending_count", 0)
                endings_found = entry.get("endings_found", 0)
                est_time = entry.get("est_time", "")
                if node_count or est_time:
                    denom = "?" if ending_count == 1 else str(ending_count)
                    endings_str = f"{endings_found}/{denom}"
                    stats = f"{node_count} nodes · {endings_str} endings · {est_time}"
                    self.console.print(f"      [dim]{stats}[/dim]")
        self.console.print()

    def show_picker_error(self, name: str, message: str) -> None:
        self.console.print(
            f"\n  [bold red]Error loading '{name}':[/bold red] {message}\n"
        )

    # ------------------------------------------------------------------
    # In-game rendering
    # ------------------------------------------------------------------

    def show_node(
        self,
        story_title: str,
        node_text: str,
        before_insets: list[Inset] | None = None,
        after_insets: list[Inset] | None = None,
    ) -> None:
        self.console.print()
        make = lambda t: self._node_panel(story_title, t, before_insets, after_insets)
        delay_s = self._typewriter_delay()
        if delay_s:
            self._typewrite(make, node_text, delay_s)
        else:
            self.console.print(make(node_text))

    def show_choices(
        self,
        choices: list[Choice],
        before_overlays: list[Overlay] | None = None,
        after_overlays: list[Overlay] | None = None,
    ) -> None:
        self.console.print()
        stagger = 0.06 if self._typewriter_delay() else 0.0
        if stagger:
            time.sleep(0.25)
        for overlay in (before_overlays or []):
            self._render_overlay(overlay)
            if stagger:
                time.sleep(stagger)
        for i, choice in enumerate(choices, start=1):
            self.console.print(f"  [bold cyan]{i}.[/bold cyan] {choice.label}")
            if stagger:
                time.sleep(stagger)
        for overlay in (after_overlays or []):
            self._render_overlay(overlay)
            if stagger:
                time.sleep(stagger)
        self.console.print()

    def show_ending(
        self,
        node_text: str,
        ending_type: str,
        overlays: list[Overlay] | None = None,
    ) -> None:
        color = _ENDING_COLORS.get(ending_type, "bright_yellow")
        label = ending_type.upper()
        self.console.print()
        for overlay in (overlays or []):
            self._render_overlay(overlay)
        make = lambda t: Panel(
            Text(t, justify="center"),
            title=f"[bold {color}]— {label} ENDING —[/bold {color}]",
            border_style=color,
            padding=(1, 4),
            expand=True,
        )
        delay_s = self._typewriter_delay()
        if delay_s:
            self._typewrite(make, node_text, delay_s)
        else:
            self.console.print(make(node_text))
        self.console.print()

    def show_save_indicator(self) -> None:
        self.console.print("  [dim green]✓ Progress saved.[/dim green]")

    # ------------------------------------------------------------------
    # Internal rendering helpers
    # ------------------------------------------------------------------

    def _typewriter_delay(self) -> float:
        cfg = self._cfg.get("typewriter", {})
        if not cfg.get("enabled"):
            return 0.0
        return max(0.0, cfg.get("delay_ms", 20) / 1000)

    def _typewrite(self, make_panel, text: str, delay_s: float) -> None:
        with Live(make_panel(""), console=self.console, auto_refresh=False) as live:
            displayed = ""
            for char in text:
                if _key_pending():
                    _consume_key()
                    live.update(make_panel(text))
                    live.refresh()
                    return
                displayed += char
                live.update(make_panel(displayed))
                live.refresh()
                time.sleep(delay_s + _PUNCTUATION_PAUSE.get(char, 0.0))

    def _node_panel(
        self,
        story_title: str,
        text: str,
        before_insets: list[Inset] | None,
        after_insets: list[Inset] | None,
    ) -> Panel:
        parts: list = []
        for inset in (before_insets or []):
            parts.append(self._inset_renderable(inset))
            parts.append(Rule(style="dim white"))
        parts.append(Text(text))
        for inset in (after_insets or []):
            parts.append(Rule(style="dim white"))
            parts.append(self._inset_renderable(inset))
        content = Group(*parts) if len(parts) > 1 else Text(text)
        return Panel(content, title=f"[bold]{story_title}[/bold]", border_style="white", padding=(1, 2))

    def _style_cfg(self, style_name: str) -> dict:
        """Return config dict for a named style, falling back to the default overlay config."""
        if style_name:
            named = self._cfg.get("styles", {}).get(style_name)
            if named:
                return named
        return self._cfg["overlay"]

    def _render_overlay(self, overlay: Overlay) -> None:
        cfg = self._style_cfg(overlay.style)
        parts = [m for m in _MODIFIERS if cfg.get(m)]
        color = cfg.get("color", "cyan")
        style = f"{' '.join(parts)} {color}".strip()
        prefix = cfg.get("prefix", "✦ ")
        self.console.print(f"  {prefix}{overlay.text}", style=style)

    def _inset_renderable(self, inset: Inset) -> Text:
        if inset.style:
            cfg = self._style_cfg(inset.style)
            parts = [m for m in _MODIFIERS if cfg.get(m)]
            color = cfg.get("color", "white")
            style = f"{' '.join(parts)} {color}".strip()
            prefix = cfg.get("prefix", "")
        else:
            style = "dim italic"
            prefix = ""
        return Text(f"{prefix}{inset.text}", style=style)

    # ------------------------------------------------------------------
    # Input prompts
    # ------------------------------------------------------------------

    def prompt_story_select(self, count: int) -> int | None | str:
        """Return 1-based index, None to quit, 'clear', or 'toggle_typewriter'."""
        while True:
            enabled = self._cfg.get("typewriter", {}).get("enabled", False)
            tw_label = "[green]ON[/green]" if enabled else "[dim]OFF[/dim]"
            self.console.print("  [bold]Enter a number, Q to quit, or C to clear save data:[/bold]")
            self.console.print(f"  [dim]T · Toggle typewriter[/dim]  {tw_label}")
            raw = self.console.input("  › ").strip().lower()
            if raw == "q":
                return None
            if raw == "c":
                return "clear"
            if raw == "t":
                return "toggle_typewriter"
            if raw.isdigit():
                value = int(raw)
                if 1 <= value <= count:
                    return value
            self.console.print("  [red]Please enter a valid number, Q, C, or T.[/red]")

    def toggle_typewriter(self) -> None:
        cfg = self._cfg.setdefault("typewriter", {})
        cfg["enabled"] = not cfg.get("enabled", False)
        state = "[green]ON[/green]" if cfg["enabled"] else "[dim]OFF[/dim]"
        self.console.print(f"  Typewriter mode: {state}\n")

    def prompt_clear_confirm(self) -> bool:
        """Return True if the user confirms clearing all save data."""
        self.console.print(
            "\n  [yellow]This will delete all active saves and ending progress for every story.[/yellow]"
        )
        while True:
            raw = self.console.input(
                "  [bold]Confirm? ([red]Y[/red] to clear, any other key to cancel):[/bold] "
            ).strip().lower()
            return raw in ("y", "yes")

    def show_clear_complete(self) -> None:
        self.console.print("  [dim green]✓ All save data cleared.[/dim green]\n")

    def prompt_continue_or_new(self) -> bool:
        """Return True to continue saved game, False for new game."""
        self.console.print("\n  [yellow]A save was found for this story.[/yellow]")
        while True:
            raw = self.console.input(
                "  [bold]Continue saved game? ([green]C[/green]/[red]N[/red] for new):[/bold] "
            ).strip().lower()
            if raw in ("c", "continue", ""):
                return True
            if raw in ("n", "new"):
                return False
            self.console.print("  [red]Press C to continue or N for a new game.[/red]")

    def prompt_choice(self, choices: list[Choice]) -> int | None:
        """Return 1-based index, or None if the player quits to menu."""
        while True:
            raw = self.console.input("  [bold]Your choice (or Q to return to menu):[/bold] ").strip().lower()
            if raw == "q":
                return None
            if raw.isdigit():
                value = int(raw)
                if 1 <= value <= len(choices):
                    return value
            self.console.print(f"  [red]Enter a number between 1 and {len(choices)}, or Q to return to the story menu.[/red]")

    def prompt_play_again(self) -> bool:
        """Return True to play again, False to return to picker."""
        while True:
            raw = self.console.input(
                "  [bold]Play again? ([green]Y[/green]/[red]N[/red]):[/bold] "
            ).strip().lower()
            if raw in ("y", "yes"):
                return True
            if raw in ("n", "no"):
                return False
            self.console.print("  [red]Press Y or N.[/red]")
