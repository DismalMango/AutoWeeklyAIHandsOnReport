from __future__ import annotations

from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt

from .config import ConfigError, Settings
from .graph.workflow import run_until_selection, run_workflow
from .reporting import write_report

app = typer.Typer(help="Discover one recent AI-native product and write a Chinese Markdown report.")
console = Console()


@app.callback()
def main() -> None:
    """Auto Weekly AI Feedback CLI."""


@app.command()
def run(
    days: int = typer.Option(30, min=1, max=90, help="Recent-day search window."),
    output: Path = typer.Option(Path("reports"), help="Directory for generated reports."),
    topic: str = typer.Option("general", help="Search topic hint."),
    max_candidates: int = typer.Option(8, min=1, max=20, help="Maximum candidate products to consider."),
    selection_mode: str = typer.Option("auto", help="Selection mode: auto or user."),
) -> None:
    """Run the AI product research agent."""
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    if selection_mode not in {"auto", "user"}:
        console.print("[red]selection-mode must be 'auto' or 'user'[/red]")
        raise typer.Exit(code=2)

    today = date.today()
    initial_state = {
        "today": today.isoformat(),
        "days": days,
        "topic": topic,
        "max_candidates": max_candidates,
    }

    console.print("[cyan]Running AI product research workflow...[/cyan]")

    if selection_mode == "user":
        preselection_state = run_until_selection(initial_state=initial_state, settings=settings)
        selection = preselection_state["selection"]
        options = selection["options"]
        recommended_slug = selection["recommended_slug"]
        console.print(f"[bold]Recommended candidate:[/bold] {recommended_slug}")
        console.print("[bold]Options:[/bold]")
        for option in options:
            console.print(f"- {option['slug']}: {option['rationale']}")
        chosen_slug = Prompt.ask(
            "Enter slug to continue",
            choices=[option["slug"] for option in options],
            default=recommended_slug,
        )
        final_state = run_workflow(
            initial_state=initial_state,
            settings=settings,
            user_selected_slug=chosen_slug,
        )
    else:
        final_state = run_workflow(initial_state=initial_state, settings=settings)

    report_path = write_report(final_state["report_markdown"], output, today)
    console.print(f"[green]Report written:[/green] {report_path}")


if __name__ == "__main__":
    app()
