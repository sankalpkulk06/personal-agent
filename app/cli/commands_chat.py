from typing import Optional

import typer
from rich.console import Console

from app.cli.commands_ask import create_qa_service
from app.providers.ollama_embeddings import OllamaProviderError
from app.ui.spinner import thinking_spinner

console = Console()


def _print_help() -> None:
    typer.echo("Commands:")
    typer.echo("- /help : show help")
    typer.echo("- /topk <n> : set retrieval depth for this chat session")
    typer.echo("- exit | quit : leave chat mode")


def chat_command(top_k: Optional[int] = None) -> None:
    service = create_qa_service()
    session_top_k = top_k

    typer.echo("Personal RAG Chat (basic)")
    typer.echo("Type your question. Use /help for commands, exit to quit.")

    while True:
        try:
            console.print("[bold blue]you[/bold blue]", end=" ")
            user_input = typer.prompt("")
        except (EOFError, KeyboardInterrupt):
            typer.echo("\nbye")
            break

        question = user_input.strip()
        if not question:
            continue

        lowered = question.lower()
        if lowered in ("exit", "quit"):
            typer.echo("bye")
            break
        if lowered == "/help":
            _print_help()
            continue
        if lowered.startswith("/topk "):
            maybe_value = question.split(maxsplit=1)[1].strip()
            try:
                parsed = int(maybe_value)
                if parsed <= 0:
                    raise ValueError("top_k must be positive")
                session_top_k = parsed
                typer.echo(f"top_k set to {session_top_k}")
            except ValueError:
                typer.echo("Invalid /topk value. Example: /topk 3")
            continue

        try:
            with thinking_spinner("generating answer..."):
                result = service.answer_question(question=question, top_k=session_top_k)
        except OllamaProviderError as exc:
            typer.echo(f"error: Ollama unavailable: {exc}")
            continue
        except Exception as exc:
            typer.echo(f"error: ask failed: {exc}")
            continue

        console.print("\n[bold magenta]assistant[/bold magenta]")
        console.print(result.answer)
        if result.sources:
            console.print("[dim]sources:[/dim]")
            shown = set()
            for source in result.sources:
                source_label = source.file_name or source.source_path or source.document_id
                if source_label in shown:
                    continue
                shown.add(source_label)
                console.print(f"[dim]- {source_label}[/dim]")
        else:
            console.print("[dim]sources: none[/dim]")
        console.print()

