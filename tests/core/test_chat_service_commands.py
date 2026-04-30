import pytest

from app.core.chat_service import ChatService
from app.core.fact_service import FactService
from app.core.habit_service import HabitService
from app.services.news_service import NewsArticle
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


class _NewsChatProvider:
    def chat(self, messages):
        raise AssertionError("news queries should not rely on chat tool selection")

    def generate(self, prompt):
        return "Sam Altman and Elon Musk are in the news today."


class _StubNewsService:
    def __init__(self):
        self.queries = []

    def search_news(self, query):
        self.queries.append(query)
        return [
            NewsArticle(
                title="OpenAI Trial Live Updates",
                source="The New York Times",
                url="https://example.com/openai-trial",
                published="Wed, 29 Apr 2026 12:00:00 GMT",
                snippet="Elon Musk and Sam Altman are central to the latest coverage.",
            )
        ]

    def get_top_news(self):
        raise AssertionError("specific news queries should use search_news")

    def generate_summary(self, articles, chat_provider):
        return chat_provider.generate("summarize")


def _news_service(registry):
    return ChatService(
        retriever=_UnusedRetriever(),
        chat_provider=_NewsChatProvider(),
        registry=registry,
        fact_service=FactService(registry),
        habit_service=HabitService(registry),
        news_service=_StubNewsService(),
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


def test_habits_command_can_use_whatsapp_style(registry):
    service = _service(registry)
    service.create_session("session")

    habit_service = HabitService(registry)
    habit_service.add_habit("gym")
    habit_service.log_habit("gym")

    result = service.answer_in_session(
        session_id="session",
        question="/habits",
        response_style="whatsapp",
    )

    assert "📊 *Habit Summary*" in result.answer
    assert "🔥 1-day streak" in result.answer
    assert "✅ Total logged this week: 1/7" in result.answer


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


def test_remember_command_can_use_whatsapp_style(registry):
    service = _service(registry)
    service.create_session("session")

    result = service.answer_in_session(
        session_id="session",
        question="/remember-personal I prefer morning workouts",
        response_style="whatsapp",
    )

    assert result.answer.startswith("🧠 Personal fact saved:")


def test_current_news_query_uses_news_service_with_whatsapp_style(registry):
    service = _news_service(registry)
    service.create_session("session")

    result = service.answer_in_session(
        session_id="session",
        question="what is the latest news on Sam Altman and Elon Musk",
        response_style="whatsapp",
    )

    assert result.sources_used is True
    assert result.news_sources[0]["title"] == "OpenAI Trial Live Updates"
    assert "📰 *Latest News: sam altman and elon musk*" in result.answer
    assert "⚡ *Summary*" in result.answer
    assert "🔗 *Sources*" in result.answer
