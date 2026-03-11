from typing import List

from typer.testing import CliRunner

from app.cli.app import cli
from app.core.qa_service import QAResult
from app.retrieval.retriever import RetrievalResult, RetrievedChunk


runner = CliRunner()


class _StubQAService:
    def __init__(self, result: QAResult):
        self._result = result
        self.calls = []

    def answer_question(self, question: str, top_k=None) -> QAResult:
        self.calls.append((question, top_k))
        return self._result


def _qa_result(answer: str, sources: List[RetrievedChunk]) -> QAResult:
    retrieval = RetrievalResult(question="q", chunks=sources, top_k=5)
    return QAResult(
        question="q",
        answer=answer,
        sources=sources,
        retrieval=retrieval,
        prompt="prompt",
    )


def test_chat_command_single_turn_and_exit(monkeypatch):
    sources = [
        RetrievedChunk(
            chunk_id="chk_1",
            document_id="doc_1",
            text="chunk text",
            score=0.1,
            source_path="/tmp/sample.md",
            file_name="sample.md",
            chunk_index=0,
            token_count=2,
            document_metadata={},
        )
    ]
    stub = _StubQAService(_qa_result("Chat answer", sources))
    monkeypatch.setattr("app.cli.commands_chat.create_qa_service", lambda: stub)

    result = runner.invoke(cli, ["chat"], input="What is in sample.md?\nexit\n")

    assert result.exit_code == 0
    assert "Personal RAG Chat (basic)" in result.stdout
    assert "assistant:" in result.stdout
    assert "Chat answer" in result.stdout
    assert "sample.md" in result.stdout
    assert stub.calls == [("What is in sample.md?", None)]


def test_chat_command_topk_command(monkeypatch):
    stub = _StubQAService(_qa_result("A", []))
    monkeypatch.setattr("app.cli.commands_chat.create_qa_service", lambda: stub)

    result = runner.invoke(cli, ["chat"], input="/topk 2\nWhat now?\nquit\n")

    assert result.exit_code == 0
    assert "top_k set to 2" in result.stdout
    assert stub.calls == [("What now?", 2)]

