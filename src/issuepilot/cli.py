from __future__ import annotations

import subprocess
import sys
import webbrowser
from pathlib import Path

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from issuepilot.api import app as api_app
from issuepilot.config import get_settings
from issuepilot.db import get_session_factory, init_db
from issuepilot.logging import configure_logging
from issuepilot.services.overnight import OvernightService

app = typer.Typer(no_args_is_help=True, help="Prepare excellent GitHub issues for Codex.")
console = Console()


@app.callback()
def main() -> None:
    configure_logging(get_settings().log_level)


@app.command()
def overnight() -> None:
    """Search, rank, clone, analyze, and prepare the best GitHub issues."""
    init_db()
    settings = get_settings()
    with get_session_factory()() as session:
        result = OvernightService(settings).run(session)
    table = Table(title="Overnight scan complete")
    table.add_column("Discovered")
    table.add_column("Prepared")
    table.add_column("Failed")
    table.add_row(str(result.discovered), str(result.prepared), str(result.failed))
    console.print(table)
    if result.failed:
        raise typer.Exit(code=1)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="API bind address"),
    port: int = typer.Option(8000, min=1, max=65535),
    reload: bool = typer.Option(False, help="Reload server during backend development"),
) -> None:
    """Run the API and production dashboard."""
    init_db()
    uvicorn.run(
        "issuepilot.api:app" if reload else api_app,
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def dashboard() -> None:
    """Start IssuePilot and open the local dashboard."""
    settings = get_settings()
    init_db()
    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if not (frontend_dist / "index.html").is_file():
        console.print("[red]Dashboard is not built. Run `npm run build` in frontend/.[/red]")
        raise typer.Exit(code=1)
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "issuepilot.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    subprocess.Popen(command)
    webbrowser.open(settings.api_url)
    console.print(f"Dashboard opened at {settings.api_url}")


if __name__ == "__main__":
    app()
