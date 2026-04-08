import uuid
from typing import Optional

import typer
from rich.console import Console

from app.cli.commands_ask import create_chat_service
from app.providers.ollama_embeddings import OllamaProviderError
from app.ui.spinner import thinking_spinner

console = Console()


def _print_help() -> None:
    typer.echo("Commands:")
    typer.echo("- /help : show help")
    typer.echo("- /topk <n> : set retrieval depth for this chat session")
    typer.echo("- /session : show current session ID")
    typer.echo("- /sessions : list recent chat sessions")
    typer.echo("- /remember-personal <fact> : remember a personal fact")
    typer.echo("- /remember-work <fact> : remember a work fact")
    typer.echo("- /facts [personal|work] : list learned facts (optionally by category)")
    typer.echo("- /forget <fact-id> : forget a learned fact")
    typer.echo("- exit | quit : leave chat mode")


def chat_command(top_k: Optional[int] = None, session_id: Optional[str] = None) -> None:
    """Run an interactive chat session with conversation history."""
    service = create_chat_service()
    fact_service = service.get_fact_service()
    session_top_k = top_k

    if session_id is None:
        session_id = str(uuid.uuid4())
        service.create_session(session_id=session_id)
    else:
        service.create_session(session_id=session_id)

    console.print(f"[dim]Session: {session_id}  (resume with: sanky --resume {session_id})[/dim]")
    console.print()
    typer.echo("Personal RAG Chat")
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
        if lowered == "/session":
            typer.echo(f"Session: {session_id}")
            continue
        if lowered == "/sessions":
            sessions = service.list_sessions(limit=10)
            if sessions:
                console.print("[bold]Recent sessions:[/bold]")
                for s in sessions:
                    title = s["title"] or "(untitled)"
                    console.print(f"  {s['session_id'][:8]}... | {s['updated_at']} | {title}")
            else:
                typer.echo("No sessions found.")
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
        if lowered.startswith("/remember-personal "):
            fact_text = question[len("/remember-personal "):].strip()
            if fact_text:
                fact_service.remember(content=fact_text, category="personal")
                typer.echo(f"✓ Remembered (personal): {fact_text}")
            else:
                typer.echo("Usage: /remember-personal <fact>")
            continue
        if lowered.startswith("/remember-work "):
            fact_text = question[len("/remember-work "):].strip()
            if fact_text:
                fact_service.remember(content=fact_text, category="work")
                typer.echo(f"✓ Remembered (work): {fact_text}")
            else:
                typer.echo("Usage: /remember-work <fact>")
            continue
        if lowered.startswith("/facts"):
            parts = lowered.split()
            category = parts[1] if len(parts) > 1 else None
            facts = fact_service.list_facts(category=category)
            if facts:
                cat_label = f" ({category})" if category else ""
                console.print(f"[bold]Learned facts{cat_label}:[/bold]")
                for i, fact in enumerate(facts[:20], 1):
                    fact_id = fact["fact_id"][:8]
                    console.print(f"  [{i}] {fact['content']}")
                    console.print(f"      [dim]{fact_id}... | {fact['created_at'][:10]}[/dim]")
            else:
                typer.echo("No facts learned yet.")
            continue
        if lowered.startswith("/forget "):
            fact_id = question[len("/forget "):].strip()
            try:
                fact_service.forget(fact_id)
                typer.echo(f"✓ Forgotten.")
            except Exception as e:
                typer.echo(f"Error: {e}")
            continue

        try:
            with thinking_spinner("generating answer..."):
                result = service.answer_in_session(
                    session_id=session_id, question=question, top_k=session_top_k
                )
        except OllamaProviderError as exc:
            typer.echo(f"error: Ollama unavailable: {exc}")
            continue
        except Exception as exc:
            typer.echo(f"error: ask failed: {exc}")
            continue

        console.print("\n[bold magenta]assistant[/bold magenta]")
        console.print(result.answer)
        if result.sources_used and result.sources:
            console.print("[dim]sources:[/dim]")
            shown = set()
            for source in result.sources:
                source_label = source.file_name or source.source_path or source.document_id
                if source_label in shown:
                    continue
                shown.add(source_label)
                console.print(f"[dim]- {source_label}[/dim]")
        console.print()

