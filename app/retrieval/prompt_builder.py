from typing import Any, List

from app.retrieval.retriever import RetrievedChunk


def build_grounded_prompt(question: str, chunks: List[RetrievedChunk], max_chunks: int = 5) -> str:
    limited_chunks = chunks[:max_chunks]
    if not limited_chunks:
        context_block = "No supporting context was retrieved."
    else:
        lines = []
        for idx, chunk in enumerate(limited_chunks, start=1):
            source = chunk.file_name or chunk.source_path or chunk.document_id
            lines.append(f"[{idx}] SOURCE={source}")
            lines.append("BEGIN_SNIPPET")
            lines.append(chunk.text.strip())
            lines.append("END_SNIPPET")
            lines.append("")
        context_block = "\n".join(lines).strip()

    return (
        "You are a local-first study assistant.\n"
        "Use only the provided context snippets.\n"
        "If the user asks about a specific file (for example, sample.md), prioritize snippets where SOURCE matches.\n"
        "If an answer is present in context, answer directly and quote short exact phrases from snippets.\n"
        "Only if the answer is truly absent, reply exactly: "
        "\"I don't know based on the provided documents.\"\n\n"
        f"Question:\n{question}\n\n"
        f"Context:\n{context_block}\n\n"
        "Answer:"
    )


def build_chat_messages(
    question: str,
    chunks: List[RetrievedChunk],
    history: List[dict[str, Any]],
    max_chunks: int = 5,
) -> List[dict[str, Any]]:
    """Build a messages list for /api/chat endpoint with conversation history.

    Args:
        question: The current user question
        chunks: Retrieved context chunks
        history: Prior conversation turns, each a dict with "role" and "content"
        max_chunks: Max context chunks to include

    Returns:
        A list of message dicts for the /api/chat endpoint
    """
    limited_chunks = chunks[:max_chunks]
    if not limited_chunks:
        context_block = "No supporting context was retrieved."
    else:
        lines = []
        for idx, chunk in enumerate(limited_chunks, start=1):
            source = chunk.file_name or chunk.source_path or chunk.document_id
            lines.append(f"[{idx}] SOURCE={source}")
            lines.append("BEGIN_SNIPPET")
            lines.append(chunk.text.strip())
            lines.append("END_SNIPPET")
            lines.append("")
        context_block = "\n".join(lines).strip()

    system_message = (
        "You are a local-first study assistant.\n"
        "Use only the provided context snippets.\n"
        "If the user asks about a specific file (for example, sample.md), prioritize snippets where SOURCE matches.\n"
        "If an answer is present in context, answer directly and quote short exact phrases from snippets.\n"
        "Only if the answer is truly absent, reply exactly: "
        "\"I don't know based on the provided documents.\"\n\n"
        f"Context:\n{context_block}"
    )

    messages: List[dict[str, Any]] = [{"role": "system", "content": system_message}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    return messages
