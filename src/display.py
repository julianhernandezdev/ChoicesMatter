from __future__ import annotations

import copy
import sys
import time

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich import box

from .config import load_settings, save_settings
from .story import Choice, Inset, Overlay

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

def _strip_pause_tokens(text: str) -> str:
    return text.replace("{pause}", "")


_TW_SPEED_PRESETS = [
    ("Slowest", 60),
    ("Slow",    40),
    ("Normal",  35),
    ("Fast",    15),
    ("Fastest",  5),
]



class Display:
    def __init__(self, debug: dict | None = None) -> None:
        self.console = Console()
        self._cfg = load_settings()
        self._debug: dict = debug or {"enabled": False, "all": False}

    # ------------------------------------------------------------------
    # Title / chrome
    # ------------------------------------------------------------------

    def clear_screen(self) -> None:
        self.console.clear()

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

    def get_page_size(self) -> int:
        return max(1, self._cfg.get("picker", {}).get("page_size", 5))

    def show_story_picker(
        self,
        entries: list[dict],
        title: str = "Select a Story",
        page: int = 0,
        total_pages: int = 1,
    ) -> None:
        self.console.print(Rule(f"[bold cyan]{title}[/bold cyan]"))
        self.console.print()
        for entry in entries:
            num = entry["index"]
            label = entry["label"]
            if entry.get("type") == "folder":
                count = entry.get("story_count", 0)
                noun = "story" if count == 1 else "stories"
                self.console.print(f"  [bold cyan]{num}.[/bold cyan]  [bold]📁 {label}/[/bold]")
                self.console.print(f"      [dim]{count} {noun}[/dim]")
            elif entry.get("error"):
                self.console.print(f"  [dim]{num}.[/dim] [red]{label}  [italic]-ERROR[/italic][/red]")
            else:
                resume = "  [bold green]● RESUME[/bold green]" if entry.get("has_save") else ""
                warn = "  [yellow][!][/yellow]" if entry.get("has_warnings") else ""
                self.console.print(f"  [bold cyan]{num}.[/bold cyan]  {label}{warn}{resume}")
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
        if total_pages > 1:
            self.console.print(
                f"  [cyan]Page {page + 1} of {total_pages}[/cyan]  "
                f"[dim]·  A prev · D next · 0 first page[/dim]"
            )
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
        current_scene: str | None = None,
    ) -> None:
        self.console.print()
        if current_scene:
            self.console.print(Rule(f"[dim]{current_scene}[/dim]", style="dim"))
            self.console.print()
        make = lambda t: self._node_panel(story_title, t, before_insets, after_insets)
        delay_s = self._typewriter_delay()
        if delay_s:
            self._typewrite(make, node_text, delay_s)
        else:
            self.console.print(make(_strip_pause_tokens(node_text)))

    def show_choices(
        self,
        choices: list[Choice],
        before_overlays: list[Overlay] | None = None,
        after_overlays: list[Overlay] | None = None,
        choice_number_color: str | None = None,
        debug_state: dict | None = None,
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
            num_color = choice.color or choice_number_color or "cyan"
            if choice.obfuscated:
                label_markup = "[dim]████ ██████ ████ ████████[/dim]"
                if self._debug["enabled"]:
                    label_markup += r"  [dim]\[redacted][/dim]"
            else:
                label_markup = choice.label
            self.console.print(f"  [bold {num_color}]{i}.[/bold {num_color}] {label_markup}")
            if stagger:
                time.sleep(stagger)
        for overlay in (after_overlays or []):
            self._render_overlay(overlay)
            if stagger:
                time.sleep(stagger)
        if self._debug["enabled"] and debug_state is not None:
            self._render_debug_panel(debug_state)
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
            self.console.print(make(_strip_pause_tokens(node_text)))
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
        raw_pauses = self._cfg.get("typewriter", {}).get("punctuation_pauses", {})
        pauses = {k: v / 1000 for k, v in raw_pauses.items()}
        pause_s = self._cfg.get("typewriter", {}).get("pause_ms", 500) / 1000
        clean_text = _strip_pause_tokens(text)
        segments = text.split("{pause}")
        with Live(make_panel(""), console=self.console, auto_refresh=False) as live:
            displayed = ""
            for seg_idx, segment in enumerate(segments):
                for char in segment:
                    if _key_pending():
                        _consume_key()
                        live.update(make_panel(clean_text))
                        live.refresh()
                        return
                    displayed += char
                    live.update(make_panel(displayed))
                    live.refresh()
                    time.sleep(delay_s + pauses.get(char, 0.0))
                if seg_idx < len(segments) - 1:
                    if _key_pending():
                        _consume_key()
                        live.update(make_panel(clean_text))
                        live.refresh()
                        return
                    time.sleep(pause_s)

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
        cfg = self._style_cfg(overlay.style or "")
        parts = [m for m in _MODIFIERS if cfg.get(m)]
        color = cfg.get("color", "cyan")
        style = f"{' '.join(parts)} {color}".strip()
        prefix = cfg.get("prefix", "✦ ")
        if self._debug["enabled"] and overlay.style is not None:
            tag = overlay.style if overlay.style else "empty"
            t = Text(f"  {prefix}{overlay.text}", style=style)
            t.append(f"  [{tag}]", style="dim")
            self.console.print(t)
        else:
            self.console.print(f"  {prefix}{overlay.text}", style=style)

    def _render_debug_panel(self, state: dict) -> None:
        show_all = self._debug["all"]
        pairs = [(k, v) for k, v in state.items() if show_all or not k.startswith("visited_")]
        hint_text = "(showing all flags)" if show_all else "(visited_* hidden — pass --all to show)"
        if not pairs:
            content: object = Group(
                Text("(no flags set)", style="dim italic"),
                Text(hint_text, style="dim italic"),
            )
        else:
            table = Table.grid(padding=(0, 2))
            table.add_column()
            table.add_column()
            row: list[Text] = []
            for k, v in pairs:
                row.append(Text(f"{k}: {v}", style="dim"))
                if len(row) == 2:
                    table.add_row(*row)
                    row = []
            if row:
                row.append(Text(""))
                table.add_row(*row)
            content = Group(table, Text(hint_text, style="dim italic"))
        self.console.print(
            Panel(content, title="debug: flags", border_style="dim", style="dim", padding=(0, 2))
        )

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
        t = Text(f"{prefix}{inset.text}", style=style)
        if self._debug["enabled"] and inset.style is not None:
            tag = inset.style if inset.style else "empty"
            t.append(f"  [{tag}]", style="dim")
        return t

    # ------------------------------------------------------------------
    # Input prompts
    # ------------------------------------------------------------------

    def prompt_story_select(
        self,
        count: int,
        has_back: bool = False,
        total_pages: int = 1,
    ) -> int | None | str:
        """Return 1-based index, None to quit, 'back', 'clear', 'toggle_typewriter', 'settings',
        'prev_page', 'next_page', or 'first_page'."""
        while True:
            enabled = self._cfg.get("typewriter", {}).get("enabled", False)
            tw_label = "[green]ON[/green]" if enabled else "[dim]OFF[/dim]"
            if has_back:
                hint = "Enter a number, B to go back, or Q to quit"
                if total_pages > 1:
                    hint += "  ·  A prev · D next · 0 first page"
                self.console.print(f"  [bold]{hint}:[/bold]")
            else:
                hint = "Enter a number, Q to quit, C to clear saves, or S for settings"
                if total_pages > 1:
                    hint += "  ·  A prev · D next · 0 first page"
                self.console.print(f"  [bold]{hint}:[/bold]")
                self.console.print(f"  [dim]T · Toggle typewriter (session only)[/dim]  {tw_label}")
            raw = self.console.input("  › ").strip().lower()
            if raw == "q":
                return None
            if has_back and raw == "b":
                return "back"
            if not has_back:
                if raw == "c":
                    return "clear"
                if raw == "t":
                    return "toggle_typewriter"
                if raw == "s":
                    return "settings"
            if total_pages > 1:
                if raw == "a":
                    return "prev_page"
                if raw == "d":
                    return "next_page"
                if raw == "0":
                    return "first_page"
            if raw.isdigit() and raw != "0":
                value = int(raw)
                if 1 <= value <= count:
                    return value
            self.console.print("  [red]Please enter a valid number.[/red]")

    def show_settings_screen(self) -> None:
        draft = copy.deepcopy(self._cfg)

        while True:
            self.clear_screen()
            tw = draft.setdefault("typewriter", {})
            picker = draft.setdefault("picker", {})
            enabled = tw.get("enabled", True)
            delay = tw.get("delay_ms", 35)
            pauses = tw.setdefault("punctuation_pauses", {})
            page_size = picker.get("page_size", 5)
            tw_state = "[green]on[/green]" if enabled else "[dim]off[/dim]"

            self.console.print()
            self.console.print(Rule("[bold cyan]Settings[/bold cyan]"))
            self.console.print()
            self.console.print(f"  [cyan]1.[/cyan]  Enabled          {tw_state}")
            self.console.print(f"  [cyan]2.[/cyan]  Speed            [bold]{delay} ms[/bold]")
            self.console.print(f"  [cyan]3.[/cyan]  Pause after  .   [bold]{pauses.get('.', 550)} ms[/bold]")
            self.console.print(f"  [cyan]4.[/cyan]  Pause after  !   [bold]{pauses.get('!', 250)} ms[/bold]")
            self.console.print(f"  [cyan]5.[/cyan]  Pause after  ?   [bold]{pauses.get('?', 350)} ms[/bold]")
            self.console.print(f"  [cyan]6.[/cyan]  Pause after  …   [bold]{pauses.get('…', 700)} ms[/bold]")
            self.console.print(f"  [cyan]7.[/cyan]  Pause after  —   [bold]{pauses.get('—', 600)} ms[/bold]")
            self.console.print(f"  [cyan]8.[/cyan]  Stories per page [bold]{page_size}[/bold]")
            self.console.print()
            self.console.print("  [dim]Enter a number to edit · [green]S[/green] save · [red]X[/red] discard[/dim]")
            raw = self.console.input("  › ").strip().lower()

            if raw == "s":
                save_settings(draft)
                self.console.print("\n  [dim green]✓ Saved. Changes take effect next launch.[/dim green]")
                self.console.input("\n  [dim]Press Enter to return.[/dim] ")
                return
            if raw == "x":
                return
            if raw == "1":
                tw["enabled"] = not enabled
            elif raw == "2":
                self._settings_edit_speed(tw)
            elif raw in ("3", "4", "5", "6", "7"):
                punct_map = {3: (".", 550), 4: ("!", 250), 5: ("?", 350), 6: ("…", 700), 7: ("—", 600)}
                key, default = punct_map[int(raw)]
                self._settings_edit_pause(pauses, key, pauses.get(key, default))
            elif raw == "8":
                self._settings_edit_page_size(picker)

    def _settings_edit_speed(self, tw: dict) -> None:
        self.clear_screen()
        self.console.print()
        self.console.print(Rule("[bold cyan]Settings — Typewriter Speed[/bold cyan]"))
        self.console.print()
        current_ms = tw.get("delay_ms", 35)
        for i, (label, ms) in enumerate(_TW_SPEED_PRESETS, start=1):
            marker = "[bold green]›[/bold green]" if ms == current_ms else " "
            self.console.print(f"  {marker} [cyan]{i}.[/cyan]  {label:<10} {ms} ms")
        self.console.print(f"    [cyan]6.[/cyan]  Custom")
        self.console.print()
        while True:
            raw = self.console.input("  › ").strip()
            if raw in ("1", "2", "3", "4", "5"):
                tw["delay_ms"] = _TW_SPEED_PRESETS[int(raw) - 1][1]
                return
            if raw == "6":
                while True:
                    val = self.console.input("  Enter ms (5–200): ").strip()
                    if val.isdigit() and 5 <= int(val) <= 200:
                        tw["delay_ms"] = int(val)
                        return
                    self.console.print("  [red]Enter a number between 5 and 200.[/red]")
            self.console.print("  [red]Enter 1–6.[/red]")

    def _settings_edit_pause(self, pauses: dict, key: str, current: int) -> None:
        self.clear_screen()
        self.console.print()
        self.console.print(Rule("[bold cyan]Settings — Typewriter[/bold cyan]"))
        self.console.print()
        self.console.print(f"  Pause after [bold]'{key}'[/bold]  —  current: [bold]{current} ms[/bold]")
        self.console.print()
        while True:
            raw = self.console.input("  Enter ms (0–2000, or Enter to keep): ").strip()
            if raw == "":
                return
            if raw.isdigit() and 0 <= int(raw) <= 2000:
                pauses[key] = int(raw)
                return
            self.console.print("  [red]Enter a number between 0 and 2000.[/red]")

    def _settings_edit_page_size(self, picker: dict) -> None:
        self.clear_screen()
        self.console.print()
        self.console.print(Rule("[bold cyan]Settings — Stories Per Page[/bold cyan]"))
        self.console.print()
        current = picker.get("page_size", 5)
        self.console.print(f"  Current: [bold]{current}[/bold]")
        self.console.print()
        while True:
            raw = self.console.input("  Enter number (1–50, or Enter to keep): ").strip()
            if raw == "":
                return
            if raw.isdigit() and 1 <= int(raw) <= 50:
                picker["page_size"] = int(raw)
                return
            self.console.print("  [red]Enter a number between 1 and 50.[/red]")

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

    def show_content_warnings(self, title: str, warnings: list[str]) -> bool:
        """Show warning panel. Returns True to proceed, False to go back."""
        lines = "\n".join(f"  · {w}" for w in warnings)
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]This story contains:[/bold]\n\n{lines}",
                title="[bold yellow][!] Content Warnings[/bold yellow]",
                subtitle=f"[dim]{title}[/dim]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        self.console.print()
        while True:
            raw = self.console.input(
                "  [bold]Proceed? ([green]Y[/green] to continue, [red]N[/red] to go back):[/bold] "
            ).strip().lower()
            if raw in ("y", "yes"):
                return True
            if raw in ("n", "no"):
                return False
            self.console.print("  [red]Press Y to continue or N to go back.[/red]")

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
