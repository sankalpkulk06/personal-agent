import pytest

from app.core.chat_service import ChatService
from app.core.fact_service import FactService
from app.core.habit_service import HabitService
from app.storage.sqlite_registry import SQLiteRegistry


class _UnusedRetriever:
    def retrieve(self, question, top_k=None):
        raise AssertionError("direct slash commands should not use retrieval")


class _UnusedChatProvider:
    def chat(self, messages):
        raise AssertionError("direct slash commands should not call the model")


@pytest.fixture
def registry(tmp_path):
    db = SQLiteRegistry(tmp_path / "registry.db")
    try:
        yield db
    finally:
        db.close()


def _service(registry):
    return ChatService(
        retriever=_UnusedRetriever(),
        chat_provider=_UnusedChatProvider(),
        registry=registry,
        fact_service=FactService(registry),
        habit_service=HabitService(registry),
    )


def test_habits_command_reads_shared_habit_data(registry):
    service = _service(registry)
    service.create_session("session")

    habit_service = HabitService(registry)
    habit_service.add_habit("gym")
    habit_service.log_habit("gym")

    result = service.answer_in_session(session_id="session", question="/habits")

    assert "Habit Summary" in result.answer
    assert "gym" in result.answer
    assert "1/7 days" in result.answer


def test_remember_command_writes_shared_fact_data(registry):
    service = _service(registry)
    service.create_session("session")

    result = service.answer_in_session(
        session_id="session",
        question="/remember-personal I prefer morning workouts",
    )

    assert "Personal fact saved" in result.answer
    facts = FactService(registry).list_facts(category="personal")
    assert [fact.content for fact in facts] == ["I prefer morning workouts"]
