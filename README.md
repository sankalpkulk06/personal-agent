# Personal RAG Study Agent

Local-first personal knowledge assistant for your own files.

## What Phase 1 MVP does

- Ingest local `.txt`, `.md`, and `.pdf` files.
- Chunk document text deterministically.
- Generate embeddings with local Ollama models.
- Persist metadata in SQLite and vectors in ChromaDB.
- Answer questions grounded in retrieved local context.
- Run fully on your machine (no cloud dependency required by design).

## Prerequisites

- Python 3.9+
- Ollama installed and running locally

## Setup

```bash
git clone <your-repo-url>
cd personal-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ollama setup

Start Ollama (in a separate terminal if needed):

```bash
ollama serve
```

Pull recommended models:

```bash
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

Optional `.env` configuration:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=llama3.2:3b
CHUNK_SIZE=800
CHUNK_OVERLAP=120
RETRIEVAL_TOP_K=5
DATA_DIR=./data
```

## CLI usage

Show config:

```bash
python -m app.main config
```

Ingest a file or folder:

```bash
python -m app.main ingest --path "./data/my-notes"
```

Ask a grounded question:

```bash
python -m app.main ask "What did I write about vector databases?"
```

Optional retrieval depth override:

```bash
python -m app.main ask "Summarize my distributed systems notes" --top-k 7
```

## Testing

```bash
python -m pytest -q
```

## Current limitations

- Supports only `.txt`, `.md`, `.pdf` parsing.
- No OCR or scanned-PDF extraction.
- No reranking/hybrid retrieval.
- No long-term conversational memory.
- CLI-only interface in Phase 1.

## Next steps

- Improve prompt quality and citation formatting.
- Add metadata filters during retrieval.
- Add optional summarization/study workflows.
