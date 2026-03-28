from pathlib import Path
from typing import Optional

import typer

from app import __version__
from app.cli.commands_chat import chat_command
from app.config import get_settings
from app.cli.commands_ask import ask_command
from app.cli.commands_ingest import ingest_command

cli = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Local-first personal RAG agent CLI.",
)


@cli.callback(invoke_without_command=True)
def root(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the CLI version and exit.",
        is_eager=True,
    ),
) -> None:
    if version:
        typer.echo(f"personal-rag-study-agent {__version__}")
        raise typer.Exit()


@cli.command("config")
def show_config() -> None:
    settings = get_settings()
    paths = settings.resolve_paths()
    typer.echo(f"app_name={settings.app_name}")
    typer.echo(f"app_env={settings.app_env}")
    typer.echo(f"ollama_base_url={settings.ollama_base_url}")
    typer.echo(f"ollama_chat_model={settings.ollama_chat_model}")
    typer.echo(f"ollama_embedding_model={settings.ollama_embedding_model}")
    typer.echo(f"chunk_size={settings.chunk_size}")
    typer.echo(f"chunk_overlap={settings.chunk_overlap}")
    typer.echo(f"retrieval_top_k={settings.retrieval_top_k}")
    typer.echo(f"data_dir={paths.data_dir}")
    typer.echo(f"chroma_dir={paths.chroma_dir}")
    typer.echo(f"sqlite_db_path={paths.sqlite_db_path}")


@cli.command("ingest")
def ingest(path: str = typer.Option(..., "--path", "-p", help="File or directory path to ingest.")) -> None:
    ingest_command(path=Path(path))


@cli.command("ask")
def ask(
    question: str = typer.Argument(..., help="Question to ask about your local documents."),
    top_k: Optional[int] = typer.Option(None, "--top-k", help="Override number of retrieved chunks."),
    export: bool = typer.Option(False, "--export", help="Export answer to Markdown file."),
) -> None:
    ask_command(question=question, top_k=top_k, export=export)


@cli.command("chat")
def chat(
    top_k: Optional[int] = typer.Option(None, "--top-k", help="Default retrieval depth for chat session."),
) -> None:
    chat_command(top_k=top_k)
