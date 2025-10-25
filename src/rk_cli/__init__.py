#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer",
#     "rich",
#     "httpx",
# ]
# ///
"""
RK CLI - Setup tool for ResearchKit projects

Usage:
    uvx rk-cli init <project-name>
    uvx rk-cli init .
    uvx rk-cli init --here

Or install globally:
    uv tool install rk-cli --from git+https://github.com/adamjdavidson/ResearchKit.git
    rk init <project-name>
    rk init .
    rk init --here
"""

import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(no_args_is_help=True)
console = Console()

RESEARCHKIT_REPO = "adamjdavidson/ResearchKit"
RESEARCHKIT_BRANCH = "main"

BANNER = """
╦═╗╔═╗╔═╗╔═╗╔═╗╦═╗╔═╗╦ ╦╦╔═╦╔╦╗
╠╦╝║╣ ╚═╗║╣ ╠═╣╠╦╝║  ╠═╣╠╩╗║ ║
╩╚═╚═╝╚═╝╚═╝╩ ╩╩╚═╚═╝╩ ╩╩ ╩╩ ╩
"""

TAGLINE = "ResearchKit - Systematic Research Framework"


def get_github_token() -> Optional[str]:
    """Get GitHub token from environment."""
    return os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")


def download_researchkit(target_dir: Path, console: Console) -> bool:
    """Download ResearchKit from GitHub."""
    token = get_github_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    url = f"https://github.com/{RESEARCHKIT_REPO}/archive/refs/heads/{RESEARCHKIT_BRANCH}.zip"

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Downloading ResearchKit...", total=None)

            response = httpx.get(url, headers=headers, follow_redirects=True, timeout=30.0)
            response.raise_for_status()

            # Save and extract zip
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)

            os.unlink(tmp_path)

            # Find extracted folder (will be ResearchKit-main or similar)
            extracted = list(target_dir.glob("ResearchKit-*"))
            if extracted:
                return extracted[0]

        return None

    except Exception as e:
        console.print(f"[red]Error downloading ResearchKit: {e}[/red]")
        return None


def copy_commands(source_dir: Path, target_dir: Path, console: Console) -> bool:
    """Copy .claude/commands from source to target."""
    source_commands = source_dir / ".claude" / "commands"
    target_commands = target_dir / ".claude" / "commands"

    if not source_commands.exists():
        console.print(f"[red]Error: Source commands not found at {source_commands}[/red]")
        return False

    try:
        target_commands.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_commands, target_commands, dirs_exist_ok=True)
        console.print(f"[green]✓[/green] Installed ResearchKit commands to {target_commands}")
        return True
    except Exception as e:
        console.print(f"[red]Error copying commands: {e}[/red]")
        return False


def copy_templates(source_dir: Path, target_dir: Path, console: Console) -> bool:
    """Copy templates from source to target."""
    source_templates = source_dir / "templates"
    target_templates = target_dir / "templates"

    if not source_templates.exists():
        console.print(f"[red]Error: Source templates not found at {source_templates}[/red]")
        return False

    try:
        shutil.copytree(source_templates, target_templates, dirs_exist_ok=True)
        console.print(f"[green]✓[/green] Copied templates to {target_templates}")
        return True
    except Exception as e:
        console.print(f"[red]Error copying templates: {e}[/red]")
        return False


@app.command()
def init(
    project_name: Optional[str] = typer.Argument(None, help="Project name or '.' for current directory"),
    here: bool = typer.Option(False, "--here", help="Initialize in current directory"),
):
    """Initialize a new ResearchKit project."""

    console.print(Panel(f"[cyan]{BANNER}[/cyan]\n[dim]{TAGLINE}[/dim]", border_style="cyan"))

    # Determine target directory
    if here or project_name == ".":
        target_dir = Path.cwd()
        console.print(f"[cyan]Initializing ResearchKit in current directory: {target_dir}[/cyan]\n")
    elif project_name:
        target_dir = Path.cwd() / project_name
        if target_dir.exists():
            console.print(f"[yellow]Directory {project_name} already exists.[/yellow]")
            if not typer.confirm("Continue anyway?"):
                raise typer.Abort()
        else:
            target_dir.mkdir(parents=True)
        console.print(f"[cyan]Initializing ResearchKit in: {target_dir}[/cyan]\n")
    else:
        console.print("[red]Error: Please specify a project name or use --here[/red]")
        raise typer.Abort()

    # Check if we're running from ResearchKit repo
    script_dir = Path(__file__).parent.parent.parent
    local_commands = script_dir / ".claude" / "commands"
    local_templates = script_dir / "templates"

    if local_commands.exists() and local_templates.exists():
        # Use local files
        console.print("[dim]Using local ResearchKit files...[/dim]\n")
        source_dir = script_dir
    else:
        # Download from GitHub
        console.print("[dim]Downloading ResearchKit from GitHub...[/dim]\n")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source_dir = download_researchkit(tmp_path, console)
            if not source_dir:
                console.print("[red]Failed to download ResearchKit[/red]")
                raise typer.Abort()

    # Copy commands
    if not copy_commands(source_dir, target_dir, console):
        raise typer.Abort()

    # Copy templates
    if not copy_templates(source_dir, target_dir, console):
        raise typer.Abort()

    # Success message
    console.print("\n[green]✓ ResearchKit initialized successfully![/green]\n")
    console.print(Panel(
        "[cyan]Next steps:[/cyan]\n\n"
        "1. Navigate to your project:\n"
        f"   [dim]cd {target_dir}[/dim]\n\n"
        "2. Start Claude Code:\n"
        "   [dim]claude[/dim]\n\n"
        "3. Initialize your research project:\n"
        "   [dim]/rk.init[/dim]\n\n"
        "4. Create your research constitution:\n"
        "   [dim]/rk.constitution[/dim]",
        title="Getting Started",
        border_style="green"
    ))


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
