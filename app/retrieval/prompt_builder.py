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
    assistant_name: str = "Sanky",
    learned_facts: List[dict[str, Any]] = None,
    news_articles: List[dict[str, Any]] = None,
) -> List[dict[str, Any]]:
    """Build a messages list for /api/chat endpoint with conversation history.

    Args:
        question: The current user question
        chunks: Retrieved context chunks
        history: Prior conversation turns, each a dict with "role" and "content"
        max_chunks: Max context chunks to include
        assistant_name: Name of the assistant for personality
        learned_facts: Optional list of learned facts to inject
        news_articles: Optional list of live news articles to inject

    Returns:
        A list of message dicts for the /api/chat endpoint
    """
    limited_chunks = chunks[:max_chunks]
    context_block = ""
    if limited_chunks:
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
        f"You are {assistant_name} — a sharp, witty personal study companion with a dry sense of humor.\n\n"
        "You have access to the user's personal documents. When they ask about those documents, answer from them "
        "— precisely, quoting where useful. When no documents are relevant, just talk naturally like a knowledgeable friend.\n\n"
        "Rules:\n"
        "- Be direct. No padding. Short answers unless depth is needed.\n"
        "- Remember everything said in this session — you have full conversation history.\n"
        "- If given context snippets below, ground your answer in them and cite sources naturally.\n"
        "- If no context is provided, answer conversationally from the conversation history.\n"
        "- Never robotically refuse — just be honest if you don't know something.\n"
        "- Use humor when it fits. You're a companion, not a search engine."
    )

    if learned_facts:
        facts_block = "\n".join([f"- {fact['content']}" for fact in learned_facts])
        system_message += f"\n\nAbout the user (what I know):\n{facts_block}"

    if news_articles:
        news_block = "\n".join(
            [
                f"[{i}] {article['title']}\n    Source: {article['source']} | {article['published']}\n    URL: {article['url']}"
                for i, article in enumerate(news_articles, 1)
            ]
        )
        system_message += f"\n\nCurrent news (fetched live):\n{news_block}\n\nWhen citing these articles, reference them by number (e.g., '[1]')."

    if context_block:
        system_message += f"\n\nRelevant documents:\n{context_block}"

    messages: List[dict[str, Any]] = [{"role": "system", "content": system_message}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    return messages
