"""Command-line interface for claude-smart-fork."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from claude_smart_fork import __version__
from claude_smart_fork.backends import list_available_backends
from claude_smart_fork.config import get_config, init_config
from claude_smart_fork.embeddings import list_available_providers
from claude_smart_fork.indexer import Indexer
from claude_smart_fork.search import format_results, format_results_json, search_sessions
from claude_smart_fork.summarizers import list_available_summarizers

app = typer.Typer(
    name="smart-fork",
    help="Semantic search across Claude Code sessions.",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"claude-smart-fork v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Smart Fork - Find the best context for your next Claude Code session."""
    pass


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config"),
) -> None:
    """Initialize configuration and directories."""
    config = init_config(force=force)
    console.print(f"✅ Initialized configuration at {config.data_dir}")
    console.print("\nConfiguration:")
    console.print(f"  Sessions path: {config.sessions_path}")
    console.print(f"  Backend: {config.backend}")
    console.print(f"  Summarizer: {config.summarizer}")

    # Show available options
    console.print("\n[dim]Available backends:[/dim]", list_available_backends())
    console.print("[dim]Available summarizers:[/dim]", list_available_summarizers())
    console.print("[dim]Available embedding providers:[/dim]", list_available_providers())


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", "-n", help="Maximum results"),
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project path"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed results"),
) -> None:
    """Search for relevant sessions."""
    try:
        results = search_sessions(query=query, limit=limit, project_filter=project)

        if json_output:
            console.print(json.dumps(format_results_json(results), indent=2))
        else:
            console.print(format_results(results, show_details=detailed))

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command()
def index(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without indexing"),
    limit: int | None = typer.Option(None, "--limit", "-n", help="Maximum sessions to index"),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-index all sessions"),
    min_messages: int = typer.Option(3, "--min-messages", help="Minimum messages to index"),
) -> None:
    """Index sessions for search."""
    config = get_config()
    indexer = Indexer(config)

    if dry_run:
        unindexed = indexer.get_unindexed_sessions()
        if limit:
            unindexed = unindexed[:limit]

        console.print(f"\n[bold]Dry run[/bold] - would index {len(unindexed)} sessions:\n")

        from claude_smart_fork.parser import parse_session_file

        for filepath in unindexed[:20]:
            session = parse_session_file(filepath)
            if session and session.message_count >= min_messages:
                console.print(f"  {session.session_id[:12]}...")
                console.print(f"    Project: {session.project_path}")
                console.print(f"    Messages: {session.message_count}")
                console.print(f"    Duration: {session.duration_minutes:.1f} min")
                console.print()

        if len(unindexed) > 20:
            console.print(f"  ... and {len(unindexed) - 20} more")

        return

    indexed = 0
    skipped = 0
    errors = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Indexing sessions...", total=None)

        for session_id, success, error in indexer.index_all(
            limit=limit,
            force=force,
            min_messages=min_messages,
        ):
            if success:
                indexed += 1
                progress.update(task, description=f"Indexed: {session_id[:12]}...")
            elif error == "Already indexed":
                skipped += 1
            else:
                errors += 1
                if error:
                    console.print(f"[yellow]Warning:[/yellow] {session_id[:12]}: {error}")

    console.print(f"\n✅ Indexed: {indexed}")
    console.print(f"⏭️  Skipped: {skipped}")
    if errors:
        console.print(f"[yellow]❌ Errors: {errors}[/yellow]")


@app.command("index-session")
def index_session(
    session_id: str = typer.Argument(..., help="Session ID to index"),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-index"),
) -> None:
    """Index a specific session."""
    config = get_config()
    indexer = Indexer(config)

    with console.status("Indexing session..."):
        success = indexer.index_session_by_id(session_id, force=force)

    if success:
        console.print(f"✅ Indexed session: {session_id}")
    else:
        console.print(f"[yellow]Session not found or already indexed: {session_id}[/yellow]")


@app.command()
def stats() -> None:
    """Show indexing statistics."""
    config = get_config()
    indexer = Indexer(config)
    stats = indexer.get_stats()

    table = Table(title="Smart Fork Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total session files", str(stats["total_session_files"]))
    table.add_row("Indexed sessions", str(stats["indexed_sessions"]))
    table.add_row("Pending sessions", str(stats["pending_sessions"]))
    table.add_row("Last full index", stats["last_full_index"] or "Never")
    table.add_row("Backend", stats["backend"]["backend"])
    table.add_row("Summarizer", stats["summarizer"])
    table.add_row("Embedding provider", stats["embedding_provider"])

    console.print(table)


@app.command()
def config(
    show: bool = typer.Option(True, "--show", "-s", help="Show current config"),
    edit: bool = typer.Option(False, "--edit", "-e", help="Open config in editor"),
) -> None:
    """Show or edit configuration."""
    cfg = get_config()

    if edit:
        config_path = cfg.data_dir / "config.json"
        if not config_path.exists():
            init_config()
        typer.launch(str(config_path))
        return

    if show:
        console.print(
            Panel.fit(
                f"""[bold]Configuration[/bold]

[cyan]Data directory:[/cyan] {cfg.data_dir}
[cyan]Sessions path:[/cyan] {cfg.sessions_path}

[bold]Backend:[/bold] {cfg.backend}
[bold]Summarizer:[/bold] {cfg.summarizer}
[bold]Embedding provider:[/bold] {cfg.embedding_provider}
[bold]Embedding model:[/bold] {cfg.embedding_model}

[bold]Search results limit:[/bold] {cfg.search_results_limit}
[bold]Min session messages:[/bold] {cfg.min_session_messages}
[bold]Auto-index:[/bold] {cfg.auto_index}
""",
                title="smart-fork config",
            )
        )


@app.command("config-set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(..., help="New value"),
) -> None:
    """Set a configuration value."""
    cfg = get_config()

    # Validate key exists
    if not hasattr(cfg, key):
        console.print(f"[red]Unknown config key: {key}[/red]")
        raise typer.Exit(1)

    # Load existing config file
    config_path = cfg.data_dir / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            data = json.load(f)
    else:
        data = {}

    # Convert value to appropriate type
    current = getattr(cfg, key)
    converted_value: str | bool | int
    if isinstance(current, bool):
        converted_value = value.lower() in ("true", "1", "yes")
    elif isinstance(current, int):
        converted_value = int(value)
    elif isinstance(current, Path):
        converted_value = str(value)
    else:
        converted_value = value

    data[key] = converted_value

    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)

    console.print(f"✅ Set {key} = {converted_value}")


@app.command()
def clear(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Clear all indexed data."""
    if not confirm:
        confirm = typer.confirm("Are you sure you want to clear all indexed data?")

    if not confirm:
        raise typer.Abort()

    config = get_config()
    indexer = Indexer(config)
    indexer.clear()

    console.print("✅ Cleared all indexed data")


if __name__ == "__main__":
    app()
