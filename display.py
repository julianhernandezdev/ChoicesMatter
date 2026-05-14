from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule
from rich import box

from config import load_settings
from story import Choice, Inset, Overlay

_ENDING_COLORS = {
    "good": "bright_green",
    "bad": "bright_red",
    "neutral": "bright_yellow",
}

_MODIFIERS = ("bold", "dim", "italic", "underline", "strike")


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
                est_time = entry.get("est_time", "")
                if node_count or est_time:
                    endings_str = "?" if ending_count == 1 else str(ending_count)
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
        parts: list = []
        for inset in (before_insets or []):
            parts.append(self._inset_renderable(inset))
            parts.append(Rule(style="dim white"))
        parts.append(Text(node_text))
        for inset in (after_insets or []):
            parts.append(Rule(style="dim white"))
            parts.append(self._inset_renderable(inset))

        content = Group(*parts) if len(parts) > 1 else node_text
        self.console.print(
            Panel(
                content,
                title=f"[bold]{story_title}[/bold]",
                border_style="white",
                padding=(1, 2),
            )
        )

    def show_choices(
        self,
        choices: list[Choice],
        before_overlays: list[Overlay] | None = None,
        after_overlays: list[Overlay] | None = None,
    ) -> None:
        self.console.print()
        for overlay in (before_overlays or []):
            self._render_overlay(overlay)
        for i, choice in enumerate(choices, start=1):
            self.console.print(f"  [bold cyan]{i}.[/bold cyan] {choice.label}")
        for overlay in (after_overlays or []):
            self._render_overlay(overlay)
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

    # ------------------------------------------------------------------
    # Internal rendering helpers
    # ------------------------------------------------------------------

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
