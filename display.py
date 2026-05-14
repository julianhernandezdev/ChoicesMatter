from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich import box

from config import load_settings
from story import Choice

_ENDING_COLORS = {
    "good": "bright_green",
    "bad": "bright_red",
    "neutral": "bright_yellow",
}


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
        """Each entry: {"index": int, "label": str, "error": bool}"""
        self.console.print(Rule("[bold cyan]Select a Story[/bold cyan]"))
        self.console.print()
        for entry in entries:
            num = entry["index"]
            label = entry["label"]
            if entry.get("error"):
                self.console.print(f"  [dim]{num}.[/dim] [red]{label}  [italic]-ERROR[/italic][/red]")
            else:
                self.console.print(f"  [bold cyan]{num}.[/bold cyan]  {label}")
        self.console.print()
        self.console.print(f"  [dim]Q.[/dim]  [dim]Quit[/dim]")
        self.console.print()

    def show_picker_error(self, name: str, message: str) -> None:
        self.console.print(
            f"\n  [bold red]Error loading '{name}':[/bold red] {message}\n"
        )

    # ------------------------------------------------------------------
    # In-game rendering
    # ------------------------------------------------------------------

    def show_node(self, story_title: str, node_text: str) -> None:
        self.console.print()
        self.console.print(
            Panel(
                node_text,
                title=f"[bold]{story_title}[/bold]",
                border_style="white",
                padding=(1, 2),
            )
        )

    def show_choices(
        self,
        choices: list[Choice],
        before_overlays: list[str] | None = None,
        after_overlays: list[str] | None = None,
    ) -> None:
        self.console.print()
        for text in (before_overlays or []):
            self._render_overlay(text)
        for i, choice in enumerate(choices, start=1):
            self.console.print(f"  [bold cyan]{i}.[/bold cyan] {choice.label}")
        for text in (after_overlays or []):
            self._render_overlay(text)
        self.console.print()

    def show_ending(
        self,
        node_text: str,
        ending_type: str,
        overlays: list[str] | None = None,
    ) -> None:
        color = _ENDING_COLORS.get(ending_type, "bright_yellow")
        label = ending_type.upper()
        self.console.print()
        for text in (overlays or []):
            self._render_overlay(text)
        self.console.print(
            Panel(
                Text(node_text, justify="center"),
                title=f"[bold {color}]— {label} ENDING —[/bold {color}]",
                border_style=color,
                padding=(1, 4),
                expand=True,
            )
        )
        self.console.print()

    def show_save_indicator(self) -> None:
        self.console.print("  [dim green]✓ Progress saved.[/dim green]")

    def _render_overlay(self, text: str) -> None:
        cfg = self._cfg["overlay"]
        _MODIFIERS = ("bold", "dim", "italic", "underline", "strike")
        parts = [m for m in _MODIFIERS if cfg.get(m)]
        color = cfg.get("color", "cyan")
        style = f"{' '.join(parts)} {color}".strip()
        prefix = cfg.get("prefix", "✦ ")
        self.console.print(f"  {prefix}{text}", style=style)

    # ------------------------------------------------------------------
    # Input prompts
    # ------------------------------------------------------------------

    def prompt_story_select(self, count: int) -> int | None:
        """Return 1-based index, or None if the user quits."""
        while True:
            raw = self.console.input("  [bold]Enter a number, or Q to quit:[/bold] ").strip().lower()
            if raw == "q":
                return None
            if raw.isdigit():
                value = int(raw)
                if 1 <= value <= count:
                    return value
            self.console.print("  [red]Please enter a number from the list, or Q to quit.[/red]")

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
