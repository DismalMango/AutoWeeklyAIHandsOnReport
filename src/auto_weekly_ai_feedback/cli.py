from __future__ import annotations

from datetime import date
from pathlib import Path

import typer
from rich.console import Console

from .agent import AIProductAgent
from .config import ConfigError, Settings
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
) -> None:
    """Run the AI product research agent."""
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc

    console.print("[cyan]Running AI product research agent...[/cyan]")
    agent = AIProductAgent(settings)
    markdown = agent.run(days=days, topic=topic, max_candidates=max_candidates)
    report_path = write_report(markdown, output, date.today())
    console.print(f"[green]Report written:[/green] {report_path}")


if __name__ == "__main__":
    app()
