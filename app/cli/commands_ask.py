from typing import Optional

import typer

from app.config import get_settings
from app.core.qa_service import QAService
from app.providers.ollama_chat import OllamaChatProvider
from app.providers.ollama_embeddings import OllamaEmbeddingsProvider, OllamaProviderError
from app.retrieval.retriever import Retriever
from app.storage.chroma_store import ChromaStore
from app.storage.sqlite_registry import SQLiteRegistry


def create_qa_service() -> QAService:
    settings = get_settings()
    paths = settings.resolve_paths()
    retriever = Retriever(
        embeddings_provider=OllamaEmbeddingsProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_embedding_model,
        ),
        vector_store=ChromaStore(paths.chroma_dir),
        metadata_registry=SQLiteRegistry(paths.sqlite_db_path),
        default_top_k=settings.retrieval_top_k,
    )
    chat_provider = OllamaChatProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_chat_model,
    )
    return QAService(retriever=retriever, chat_provider=chat_provider)


def ask_command(
    question: str = typer.Argument(..., help="Question to ask about your local documents."),
    top_k: Optional[int] = typer.Option(None, "--top-k", help="Override number of retrieved chunks."),
) -> None:
    service = create_qa_service()
    try:
        result = service.answer_question(question=question, top_k=top_k)
    except OllamaProviderError as exc:
        typer.echo(f"Error: Ollama unavailable: {exc}")
        raise typer.Exit(code=1)
    except Exception as exc:
        typer.echo(f"Error: ask failed: {exc}")
        raise typer.Exit(code=1)

    if not result.sources:
        typer.echo("No relevant sources found in indexed documents.")

    typer.echo("Answer:")
    typer.echo(result.answer)

    if result.sources:
        typer.echo("Sources:")
        seen = set()
        for source in result.sources:
            source_label = source.file_name or source.source_path or source.document_id
            if source_label in seen:
                continue
            seen.add(source_label)
            typer.echo(f"- {source_label}")

