from typing import List

from app.retrieval.retriever import RetrievedChunk


def build_grounded_prompt(question: str, chunks: List[RetrievedChunk], max_chunks: int = 5) -> str:
    limited_chunks = chunks[:max_chunks]
    if not limited_chunks:
        context_block = "No supporting context was retrieved."
    else:
        lines = []
        for idx, chunk in enumerate(limited_chunks, start=1):
            source = chunk.file_name or chunk.source_path or chunk.document_id
            lines.append(f"[{idx}] Source: {source}")
            lines.append(chunk.text.strip())
            lines.append("")
        context_block = "\n".join(lines).strip()

    return (
        "You are a local-first study assistant. "
        "Answer the question using only the provided context when possible.\n\n"
        "If the context does not contain enough information, say clearly: "
        "\"I don't know based on the provided documents.\"\n\n"
        f"Question:\n{question}\n\n"
        f"Context:\n{context_block}\n\n"
        "Answer:"
    )

