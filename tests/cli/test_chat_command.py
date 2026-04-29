from contextlib import contextmanager

from typer.testing import CliRunner

from app.cli.app import cli
from app.core.qa_service import QAResult
from app.services.reminders_service import RemindersServiceError
from app.retrieval.retriever import RetrievalResult, RetrievedChunk


runner = CliRunner()


class _StubPromptSession:
    def __init__(self, responses):
        self._responses = iter(responses)

    def prompt(self, *args, **kwargs):
        try:
            return next(self._responses)
        except StopIteration as exc:
            raise EOFError from exc


class _StubFactService:
    def remember(self, content, category):
        return None

    def list_facts(self, category=None):
        return []

    def forget(self, fact_id):
        return None


class _StubChatService:
    def __init__(self, result: QAResult):
        self._result = result
        self.answer_calls = []
        self.created_sessions = []

    def create_session(self, session_id, title=""):
        self.created_sessions.append((session_id, title))

    def get_fact_service(self):
        return _StubFactService()

    def get_web_search_service(self):
        return None

    def list_sessions(self, limit=10):
        return []

    def answer_in_session(self, session_id, question, top_k=None):
        self.answer_calls.append((session_id, question, top_k))
        return self._result


class _StubNewsService:
    def search_news(self, query):
        return []

    def get_top_news(self):
        return []


class _StubRemindersService:
    def __init__(self, list_name="Reminders", error=None):
        self.default_list_name = list_name
        self.error = error
        self.calls = []

    def add_reminder(self, task):
        self.calls.append(task)
        if self.error:
            raise self.error
        return self.default_list_name


@contextmanager
def _noop_spinner(message="thinking..."):
    yield


def _qa_result(answer: str, sources=None) -> QAResult:
    sources = sources or []
    retrieval = RetrievalResult(question="q", chunks=sources, top_k=5)
    return QAResult(
        question="q",
        answer=answer,
        sources=sources,
        retrieval=retrieval,
        prompt="prompt",
    )


def _patch_chat_dependencies(monkeypatch, responses, chat_service, reminders_service=None):
    monkeypatch.setattr(
        "app.cli.commands_chat.PromptSession",
        lambda *args, **kwargs: _StubPromptSession(responses),
    )
    monkeypatch.setattr("app.cli.commands_chat.thinking_spinner", _noop_spinner)
    monkeypatch.setattr("app.cli.commands_chat.create_chat_service", lambda: chat_service)
    monkeypatch.setattr("app.cli.commands_chat.create_news_service", lambda: _StubNewsService())
    monkeypatch.setattr(
        "app.cli.commands_chat.create_reminders_service",
        lambda: reminders_service or _StubRemindersService(),
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
    chat_service = _StubChatService(_qa_result("Chat answer", sources))
    _patch_chat_dependencies(monkeypatch, ["What is in sample.md?", "exit"], chat_service)

    result = runner.invoke(cli, ["chat"])

    assert result.exit_code == 0
    assert "Sage — Your Personal AI" in result.stdout
    assert "Chat answer" in result.stdout
    assert "sample.md" in result.stdout
    assert len(chat_service.created_sessions) == 1
    session_id, title = chat_service.created_sessions[0]
    assert title == ""
    assert chat_service.answer_calls == [(session_id, "What is in sample.md?", None)]


def test_chat_command_topk_command(monkeypatch):
    chat_service = _StubChatService(_qa_result("A"))
    _patch_chat_dependencies(monkeypatch, ["/topk 2", "What now?", "quit"], chat_service)

    result = runner.invoke(cli, ["chat"])

    assert result.exit_code == 0
    assert "Retrieval depth set to" in result.stdout
    session_id, _ = chat_service.created_sessions[0]
    assert chat_service.answer_calls == [(session_id, "What now?", 2)]


def test_chat_command_todo_adds_reminder_without_hitting_llm(monkeypatch):
    chat_service = _StubChatService(_qa_result("unused"))
    reminders_service = _StubRemindersService(list_name="Errands")
    _patch_chat_dependencies(monkeypatch, ["/todo Buy oat milk", "quit"], chat_service, reminders_service)

    result = runner.invoke(cli, ["chat"])

    assert result.exit_code == 0
    assert "Added todo to" in result.stdout
    assert "Errands" in result.stdout
    assert "Buy oat milk" in result.stdout
    assert reminders_service.calls == ["Buy oat milk"]
    assert chat_service.answer_calls == []


def test_chat_command_todo_without_task_shows_usage(monkeypatch):
    chat_service = _StubChatService(_qa_result("unused"))
    reminders_service = _StubRemindersService()
    _patch_chat_dependencies(monkeypatch, ["/todo", "quit"], chat_service, reminders_service)

    result = runner.invoke(cli, ["chat"])

    assert result.exit_code == 0
    assert "Usage:" in result.stdout
    assert "/todo <task>" in result.stdout
    assert reminders_service.calls == []


def test_chat_command_todo_failure_prints_error_and_continues(monkeypatch):
    chat_service = _StubChatService(_qa_result("unused"))
    reminders_service = _StubRemindersService(
        error=RemindersServiceError("Reminders access was denied.")
    )
    _patch_chat_dependencies(monkeypatch, ["/todo Buy oat milk", "quit"], chat_service, reminders_service)

    result = runner.invoke(cli, ["chat"])

    assert result.exit_code == 0
    assert "Reminders access was denied." in result.stdout
    assert reminders_service.calls == ["Buy oat milk"]
    assert chat_service.answer_calls == []
