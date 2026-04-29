"""Skill management CLI handlers (list, add, show, edit, remove).

Lazy-loaded only when skill commands are used — keeps ask/run startup unaffected.
Follows the same Rich + Prompt/Confirm patterns as config_commands.py.

Skills are stored as:
    ~/.config/codedjinn/skills/<name>/SKILL.md

SKILL.md format:
    ---
    name: search
    title: Search
    steps: 5
    extra_commands:
      - rg
    ---

    Strategy description in markdown.
"""

import re
import shutil
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from codedjinn.skills import SKILL_FILENAME, SKILLS_DIR

console = Console()


def handle_skill(action: str, name: str | None) -> None:
    dispatch = {
        "list-skills": _list_skills,
        "add-skill": _add_skill,
        "show-skill": _show_skill,
        "edit-skill": _edit_skill,
        "remove-skill": _remove_skill,
    }
    if action not in dispatch:
        console.print(f"[red]Unknown skill action: {action}[/red]")
        raise SystemExit(1)

    if action in ("show-skill", "edit-skill", "remove-skill"):
        _require_name(name, action)

    dispatch[action](name)


def _require_name(name: str | None, action: str) -> None:
    if not name:
        console.print(f"[red]'{action}' requires a skill name.[/red]")
        raise SystemExit(1)


def _valid_name(name: str) -> bool:
    return bool(re.match(r"^[a-z][a-z0-9_-]*$", name))


def _skill_file(name: str) -> Path:
    return SKILLS_DIR / name / SKILL_FILENAME


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

def _list_skills(name: str | None = None) -> None:
    from codedjinn.skills.loader import load_all_skill_names, load_skill

    names = load_all_skill_names(SKILLS_DIR)
    if not names:
        console.print(
            "[yellow]No skills defined.[/yellow] "
            "Use [bold]code-djinn settings add-skill <name>[/bold] to create one."
        )
        return

    table = Table(title="Skills", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="cyan", min_width=16)
    table.add_column("Steps", justify="right", width=6)
    table.add_column("Extra commands", style="dim")
    table.add_column("Description", style="green")

    for n in names:
        try:
            skill = load_skill(n, SKILLS_DIR)
        except ValueError as exc:
            table.add_row(n, "?", "?", f"[red]{exc}[/red]")
            continue
        if skill:
            cmds = ", ".join(skill.extra_commands) or "[dim]-[/dim]"
            desc = skill.description[:60] + "…" if len(skill.description) > 60 else skill.description
            table.add_row(n, str(skill.steps), cmds, desc)

    console.print(table)
    console.print(f"\n[dim]Skills dir: {SKILLS_DIR}[/dim]")


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

def _add_skill(name: str | None = None) -> None:
    from codedjinn.skills.loader import EXTRA_COMMANDS_REGISTRY

    console.print(Panel.fit("[bold blue]New Skill[/bold blue]", title="add-skill"))

    if not name:
        name = Prompt.ask("Skill name")

    name = name.strip().lower()
    if not _valid_name(name):
        console.print(
            "[red]Error:[/red] name must start with a letter and contain only "
            "letters, digits, hyphens, or underscores."
        )
        raise SystemExit(1)

    skill_dir = SKILLS_DIR / name
    if skill_dir.exists():
        console.print(
            f"[yellow]Skill '{name}' already exists.[/yellow] "
            "Use [bold]edit-skill[/bold] to modify it."
        )
        raise SystemExit(1)

    title = Prompt.ask(
        "Title", default=name.replace("-", " ").replace("_", " ").capitalize()
    )

    steps_str = Prompt.ask("Reasoning steps (1–10)", default="3")
    try:
        steps = int(steps_str)
        if not 1 <= steps <= 10:
            raise ValueError
    except ValueError:
        console.print("[red]Error:[/red] steps must be an integer between 1 and 10.")
        raise SystemExit(1)

    known = sorted(EXTRA_COMMANDS_REGISTRY)
    console.print(f"Available extra commands: [bold]{', '.join(known)}[/bold]")
    raw_cmds = Prompt.ask("Extra commands (comma-separated, or leave blank)", default="")
    extra_commands = [c.strip() for c in raw_cmds.split(",") if c.strip()]
    for cmd in extra_commands:
        if cmd not in EXTRA_COMMANDS_REGISTRY:
            console.print(
                f"[red]Error:[/red] unknown command '{cmd}'. Known: {', '.join(known)}"
            )
            raise SystemExit(1)

    description = Prompt.ask("Strategy description (shown to the model)")

    # Build SKILL.md content
    extra_lines = "".join(f"  - {c}\n" for c in extra_commands)
    empty_cmds = "  []\n"
    skill_md = (
        f"---\n"
        f"name: {name}\n"
        f"title: {title}\n"
        f"steps: {steps}\n"
        f"extra_commands:\n{extra_lines if extra_lines else empty_cmds}"
        f"---\n\n"
        f"{description}\n"
    )

    skill_dir.mkdir(parents=True, exist_ok=True)
    _skill_file(name).write_text(skill_md, encoding="utf-8")

    console.print(
        Panel.fit(
            f"[green]Skill '{name}' created.[/green]\n"
            f"Invoke as: [bold]/{name}[/bold] at the start of your query\n"
            f"[dim]{_skill_file(name)}[/dim]",
            title="Success",
        )
    )


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------

def _show_skill(name: str | None = None) -> None:
    sf = _skill_file(name)
    if not sf.exists():
        console.print(f"[red]Skill '{name}' not found.[/red]")
        raise SystemExit(1)
    console.print(Panel(sf.read_text(encoding="utf-8"), title=f"[cyan]{name}/SKILL.md[/cyan]"))
    console.print(f"[dim]Invoked as: /{name}[/dim]")


# ---------------------------------------------------------------------------
# edit
# ---------------------------------------------------------------------------

def _edit_skill(name: str | None = None) -> None:
    import os

    sf = _skill_file(name)
    if not sf.exists():
        console.print(f"[red]Skill '{name}' not found.[/red]")
        raise SystemExit(1)

    editor = os.environ.get("EDITOR", "vim")
    try:
        console.print(f"[dim]Opening {sf} with {editor}...[/dim]")
        subprocess.run([editor, str(sf)], check=True)
        console.print("[green]✓ Skill updated[/green]")
    except subprocess.CalledProcessError:
        console.print(f"[red]Editor exited with an error: {editor}[/red]")
    except FileNotFoundError:
        console.print(f"[red]Editor not found: {editor}[/red]")
        console.print(f"Set EDITOR or edit manually: {sf}")


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------

def _remove_skill(name: str | None = None) -> None:
    skill_dir = SKILLS_DIR / name
    if not (skill_dir / SKILL_FILENAME).exists():
        console.print(f"[red]Skill '{name}' not found.[/red]")
        raise SystemExit(1)

    if Confirm.ask(f"Delete skill '[bold]{name}[/bold]'?", default=False):
        shutil.rmtree(skill_dir)
        console.print(f"[green]Skill '{name}' removed.[/green]")
    else:
        console.print("[dim]Cancelled.[/dim]")
