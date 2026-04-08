from pathlib import Path

from app.schemas.chunk import DocumentChunk
from app.schemas.document import ParsedDocument
from app.storage.sqlite_registry import SQLiteRegistry


def _build_document(source_path: Path, content: str = "Hello world") -> ParsedDocument:
    return ParsedDocument(
        source_path=source_path.resolve(),
        filename=source_path.name,
        extension=source_path.suffix.lower(),
        checksum_sha256="a" * 64,
        parser_name="txt",
        content=content,
        char_count=len(content),
        metadata={"tag": "study"},
    )


def _build_chunk(source_path: Path, document_id: str, text: str = "Hello") -> DocumentChunk:
    return DocumentChunk(
        chunk_id="chk_123",
        document_id=document_id,
        document_checksum_sha256="a" * 64,
        source_path=source_path.resolve(),
        file_name=source_path.name,
        chunk_index=0,
        text=text,
        token_count=1,
        char_start=0,
        char_end=len(text),
        metadata={"section": "intro"},
    )


def test_sqlite_registry_initializes_schema(tmp_path):
    db_path = tmp_path / "registry.db"
    registry = SQLiteRegistry(db_path=db_path)
    try:
        document_tables = registry._connection.execute(  # noqa: SLF001
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('documents', 'chunks')"
        ).fetchall()
        table_names = sorted([row["name"] for row in document_tables])
        assert table_names == ["chunks", "documents"]
    finally:
        registry.close()


def test_sqlite_registry_upsert_and_lookup_document_and_chunk(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Hello world", encoding="utf-8")

    registry = SQLiteRegistry(db_path=tmp_path / "registry.db")
    try:
        document_id = "doc_abc"
        document = _build_document(file_path)
        chunk = _build_chunk(file_path, document_id=document_id)

        registry.upsert_document(document_id=document_id, document=document)
        registry.upsert_chunk(chunk)

        stored_doc = registry.get_document(document_id)
        stored_chunk = registry.get_chunk(chunk.chunk_id)
        chunks_for_doc = registry.get_chunks_for_document(document_id)

        assert stored_doc is not None
        assert stored_doc["document_id"] == document_id
        assert stored_doc["file_name"] == "sample.txt"
        assert stored_doc["metadata_json"]["tag"] == "study"

        assert stored_chunk is not None
        assert stored_chunk["chunk_id"] == chunk.chunk_id
        assert stored_chunk["document_id"] == document_id
        assert stored_chunk["metadata_json"]["section"] == "intro"

        assert len(chunks_for_doc) == 1
        assert chunks_for_doc[0]["chunk_id"] == chunk.chunk_id
    finally:
        registry.close()


def test_sqlite_registry_repeated_upsert_updates_values(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Hello world", encoding="utf-8")

    registry = SQLiteRegistry(db_path=tmp_path / "registry.db")
    try:
        document_id = "doc_abc"
        base_document = _build_document(file_path, content="Hello world")
        updated_document = _build_document(file_path, content="Hello updated world")
        updated_document.metadata = {"tag": "updated"}

        registry.upsert_document(document_id=document_id, document=base_document)
        registry.upsert_document(document_id=document_id, document=updated_document)

        base_chunk = _build_chunk(file_path, document_id=document_id, text="Hello")
        updated_chunk = _build_chunk(file_path, document_id=document_id, text="Hello updated")
        registry.upsert_chunk(base_chunk)
        registry.upsert_chunk(updated_chunk)

        stored_doc = registry.get_document(document_id)
        stored_chunk = registry.get_chunk(base_chunk.chunk_id)

        assert stored_doc is not None
        assert stored_doc["content_length"] == len("Hello updated world")
        assert stored_doc["metadata_json"]["tag"] == "updated"

        assert stored_chunk is not None
        assert stored_chunk["text"] == "Hello updated"
        assert stored_chunk["char_end"] == len("Hello updated")
    finally:
        registry.close()

