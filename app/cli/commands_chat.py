import uuid
from typing import Optional

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from rich.console import Console

from app.cli.commands_ask import create_chat_service, create_news_service, create_reminders_service
from app.core.reminders_service import RemindersServiceError
from app.providers.ollama_embeddings import OllamaProviderError
from app.ui.spinner import thinking_spinner

console = Console()

# Custom key bindings: Enter submits, Shift+Enter creates newline
def create_key_bindings():
    bindings = KeyBindings()

    @bindings.add(Keys.Enter, eager=True)
    def _(event):
        # Enter submits the input
        event.app.exit(result=event.app.current_buffer.text)

    @bindings.add(Keys.Escape, Keys.Enter, eager=True)
    def _(event):
        # Escape+Enter creates a newline
        event.current_buffer.insert_text('\n')

    @bindings.add(Keys.ControlM, eager=True)
    def _(event):
        # Ctrl+M (alternative Enter) also submits
        event.app.exit(result=event.app.current_buffer.text)

    return bindings

key_bindings = create_key_bindings()


def _print_help() -> None:
    console.print("\n[bold cyan]━━━━━━━━━━ Available Commands ━━━━━━━━━━[/bold cyan]")
    console.print()
    commands = [
        ("/help", "Show this help message"),
        ("/topk <n>", "Set retrieval depth (default: 5)"),
        ("/session", "Show current session ID"),
        ("/sessions", "List recent chat sessions"),
        ("/remember-personal <fact>", "Remember a personal fact"),
        ("/remember-work <fact>", "Remember a work fact"),
        ("/facts [category]", "List facts (personal|work)"),
        ("/forget <fact-id>", "Delete a fact"),
        ("/news [query]", "Fetch live news"),
        ("/todo <task>", "Add a task to Apple Reminders"),
        ("exit | quit", "Exit chat mode"),
    ]
    for cmd, desc in commands:
        console.print(f"[bold green]{cmd:<30}[/bold green] {desc}")
    console.print()


def chat_command(top_k: Optional[int] = None, session_id: Optional[str] = None) -> None:
    """Run an interactive chat session with conversation history."""
    service = create_chat_service()
    fact_service = service.get_fact_service()
    news_service = create_news_service()
    reminders_service = create_reminders_service()
    session_top_k = top_k

    if session_id is None:
        session_id = str(uuid.uuid4())
        service.create_session(session_id=session_id)
    else:
        service.create_session(session_id=session_id)

    console.print()
    console.print("[bold cyan]╭─ Sage — Your Personal AI ─╮[/bold cyan]")
    console.print(f"[dim]│ Session: {session_id[:8]}...[/dim]")
    console.print(f"[dim]│ Resume: sage --resume {session_id}[/dim]")
    console.print("[bold cyan]╰──────────────────────────╯[/bold cyan]")
    console.print()
    console.print("[green]💡 Tip:[/green] Type [bold]/help[/bold] for commands | [bold]Shift+Enter[/bold] for multi-line")
    console.print()

    # Create prompt session with history
    session = PromptSession(
        history=InMemoryHistory(),
        enable_history_search=True,
    )

    while True:
        try:
            # Print colored prompt with newline for proper cursor placement
            console.print("[bold blue]you[/bold blue]")
            user_input = session.prompt(
                "> ",  # Input indicator on new line
                multiline=True,
                editing_mode=EditingMode.EMACS,
                key_bindings=key_bindings,
            )
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye[/dim]")
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
            console.print(f"\n[dim]Session ID:[/dim] [bold]{session_id}[/bold]\n")
            continue
        if lowered == "/sessions":
            sessions = service.list_sessions(limit=10)
            if sessions:
                console.print()
                console.print("[bold cyan]━━━━━━━━━━ Recent Sessions ━━━━━━━━━━[/bold cyan]")
                console.print()
                for i, s in enumerate(sessions, 1):
                    title = s["title"] or "(untitled)"
                    sid = s["session_id"][:8]
                    updated = s["updated_at"].split("T")[0]  # Extract date
                    console.print(f"[bold]{i}.[/bold] {sid}...  [dim]{updated}[/dim]")
                console.print()
            else:
                console.print("\n[dim]No sessions found.[/dim]\n")
            continue
        if lowered.startswith("/topk "):
            maybe_value = question.split(maxsplit=1)[1].strip()
            try:
                parsed = int(maybe_value)
                if parsed <= 0:
                    raise ValueError("top_k must be positive")
                session_top_k = parsed
                console.print(f"\n[green]✓[/green] Retrieval depth set to [bold]{session_top_k}[/bold]\n")
            except ValueError:
                console.print("\n[red]✗[/red] Invalid value. Usage: /topk 5\n")
            continue
        if lowered.startswith("/remember-personal "):
            fact_text = question[len("/remember-personal "):].strip()
            if fact_text:
                fact_service.remember(content=fact_text, category="personal")
                console.print(f"\n[green]✓[/green] [bold magenta]Personal fact[/bold magenta] saved: {fact_text}\n")
            else:
                console.print("\n[yellow]Usage:[/yellow] /remember-personal <fact>\n")
            continue
        if lowered.startswith("/remember-work "):
            fact_text = question[len("/remember-work "):].strip()
            if fact_text:
                fact_service.remember(content=fact_text, category="work")
                console.print(f"\n[green]✓[/green] [bold cyan]Work fact[/bold cyan] saved: {fact_text}\n")
            else:
                console.print("\n[yellow]Usage:[/yellow] /remember-work <fact>\n")
            continue
        if lowered.startswith("/facts"):
            parts = lowered.split()
            category = parts[1] if len(parts) > 1 else None
            facts = fact_service.list_facts(category=category)
            if facts:
                cat_icon = {"personal": "👤", "work": "💼"}.get(category, "🧠")
                cat_label = f" {cat_icon} {category.title()}" if category else " 🧠 All"
                console.print(f"\n[bold cyan]━━━━━━ Learned Facts{cat_label} ━━━━━━[/bold cyan]")
                console.print()
                for i, fact in enumerate(facts[:20], 1):
                    fact_id = fact["fact_id"][:8]
                    date = fact["created_at"][:10]
                    console.print(f"[bold green][{i}][/bold green] {fact['content']}")
                    console.print(f"[dim]    {fact_id}... | {date}[/dim]")
                    console.print()
            else:
                console.print("\n[dim]No facts learned yet. Use /remember-personal or /remember-work[/dim]\n")
            continue
        if lowered.startswith("/forget "):
            fact_id = question[len("/forget "):].strip()
            try:
                fact_service.forget(fact_id)
                console.print(f"\n[green]✓[/green] Fact forgotten\n")
            except Exception as e:
                console.print(f"\n[red]✗[/red] Error: {e}\n")
            continue
        if lowered.startswith("/news"):
            query = question[len("/news"):].strip()
            try:
                with thinking_spinner("fetching news..."):
                    if query:
                        articles = news_service.search_news(query)
                    else:
                        articles = news_service.get_top_news()

                if articles:
                    news_title = f"News: {query}" if query else "Top News Today"
                    console.print(f"\n[bold cyan]━━━━━━ {news_title} ━━━━━━[/bold cyan]\n")
                    for i, article in enumerate(articles, 1):
                        console.print(f"[bold green][{i}][/bold green] [bold]{article.title}[/bold]")
                        console.print(f"[yellow]{article.source}[/yellow] [dim]| {article.published}[/dim]")
                        console.print(f"[blue underline]{article.url}[/blue underline]")
                        console.print()
                else:
                    console.print("\n[dim]No news found for your query.[/dim]\n")
            except Exception as e:
                console.print(f"\n[red]Error fetching news:[/red] {e}\n")
            continue
        if lowered == "/todo" or lowered.startswith("/todo "):
            task = question[len("/todo"):].strip()
            if not task:
                console.print("\n[yellow]Usage:[/yellow] /todo <task>\n")
                continue

            try:
                target_list = reminders_service.add_reminder(task=task)
                console.print(
                    f"\n[green]✓[/green] Added todo to [bold]{target_list}[/bold]: {task}\n"
                )
            except RemindersServiceError as exc:
                console.print(f"\n[red]✗[/red] {exc}\n")
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

        console.print()
        console.print("[bold cyan]╭─ Sage ─╮[/bold cyan]")
        console.print()
        console.print(result.answer)
        console.print()

        if result.news_sources or (result.sources_used and result.sources):
            console.print("[bold cyan]─ Sources ─[/bold cyan]")
            if result.news_sources:
                for i, source in enumerate(result.news_sources, 1):
                    console.print(f"[yellow]📰 [{i}][/yellow] {source['title']}")
                    console.print(f"    [dim]{source['source']}[/dim]")
            if result.sources_used and result.sources:
                shown = set()
                for source in result.sources:
                    source_label = source.file_name or source.source_path or source.document_id
                    if source_label in shown:
                        continue
                    shown.add(source_label)
                    console.print(f"[cyan]📄[/cyan] {source_label}")
            console.print()

        console.print("[bold cyan]╰──────────╯[/bold cyan]")
        console.print()
