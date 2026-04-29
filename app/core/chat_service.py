import re
import uuid
from typing import List, Optional

from app.core.qa_service import QAResult
from app.core.fact_service import FactService
from app.core.habit_service import HabitService
from app.services.news_service import NewsService, NewsArticle
from app.services.reminders_service import RemindersService
from app.core.tool_executor import ToolExecutor
from app.core.tools import ToolRegistry
from app.services.web_search_service import WebSearchService
from app.providers.ollama_chat import OllamaChatProvider
from app.retrieval.prompt_builder import build_chat_messages, build_system_message_with_tools
from app.retrieval.retriever import Retriever, RetrievalResult
from app.storage.sqlite_registry import SQLiteRegistry


class ChatService:
    """Session-aware chat service with conversation history and persistence."""

    CONVERSATIONAL_PATTERNS = [
        r"^(hi|hello|hey|howdy|sup|yo)\b",
        r"^how are you",
        r"^good (morning|afternoon|evening|night)",
        r"what (is |'s )?(your |my )?(name|last name|surname|birthday|birth year|age|location|job|work)",
        r"where (do |)i (live|work)",
        r"what (do |)i (do|work as)",
        r"who are you",
        r"what are you",
        r"are you (an? )?(ai|bot|assistant)",
        r"what did (i|you) (ask|say|tell)",
        r"\b(earlier|previous(ly)?|before|last (time|message|question))\b",
        r"^(thanks|thank you|cheers|great|nice|cool|awesome|ok|okay|sure|got it|understood|perfect)\b",
        r"^bye|^see you|^goodbye|^farewell",
    ]

    NEWS_PATTERNS = [
        r"(what('s| is) the news (on|about|for|regarding))",
        r"(latest|recent|current|today'?s?) news (on|about|for|regarding)",
        r"(any )?news (on|about|for|regarding)",
        r"what happened (to|with|in)",
        r"news (on|about)",
    ]

    def __init__(
        self,
        retriever: Retriever,
        chat_provider: OllamaChatProvider,
        registry: SQLiteRegistry,
        fact_service: Optional[FactService] = None,
        news_service: Optional[NewsService] = None,
        reminders_service: Optional[RemindersService] = None,
        web_search_service: Optional[WebSearchService] = None,
        habit_service: Optional[HabitService] = None,
        max_prompt_chunks: int = 5,
        assistant_name: str = "Sage",
        enable_tools: bool = True,
    ):
        self._retriever = retriever
        self._chat_provider = chat_provider
        self._registry = registry
        self._fact_service = fact_service
        self._news_service = news_service
        self._reminders_service = reminders_service
        self._web_search_service = web_search_service
        self._habit_service = habit_service
        self._max_prompt_chunks = max_prompt_chunks
        self._assistant_name = assistant_name
        self._enable_tools = enable_tools

        # Tool registry and executor for open source model
        self._tool_registry = ToolRegistry(
            news_service=news_service,
            fact_service=fact_service,
            reminders_service=reminders_service,
            retriever=retriever,
            web_search_service=web_search_service,
            habit_service=habit_service,
        )
        self._tool_executor = ToolExecutor(self._tool_registry)

        # In-memory cache of news articles per session for follow-up questions
        self._session_news: dict[str, list[dict]] = {}

    @staticmethod
    def _is_conversational(question: str) -> bool:
        """Check if a question is conversational (doesn't need document retrieval).

        Uses regex patterns to detect greetings, meta-questions, and identity questions.
        """
        q_lower = question.lower().strip()
        for pattern in ChatService.CONVERSATIONAL_PATTERNS:
            if re.search(pattern, q_lower):
                return True
        return False

    @staticmethod
    def _is_news_query(question: str) -> bool:
        """Check if a question is asking for news.

        Uses regex patterns to detect news-related queries.
        """
        q_lower = question.lower().strip()
        for pattern in ChatService.NEWS_PATTERNS:
            if re.search(pattern, q_lower):
                return True
        return False

    @staticmethod
    def _extract_news_topic(question: str) -> Optional[str]:
        """Extract the news topic from a question.

        Args:
            question: The user question

        Returns:
            The extracted topic or None if not found
        """
        q_lower = question.lower().strip()

        # Try to extract from common patterns
        patterns = [
            r"(what('s| is) the news (on|about|for|regarding)\s+)(.+)",
            r"(latest|recent|current|today'?s?) news (on|about|for|regarding)\s+(.+)",
            r"(any )?news (on|about|for|regarding)\s+(.+)",
            r"what happened (to|with|in)\s+(.+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, q_lower)
            if match:
                topic = match.group(match.lastindex)  # Get last capture group
                # Clean up common suffixes
                topic = re.sub(r"\s+(today|yesterday|this week|right now)", "", topic).strip()
                return topic

        return None

    def answer_in_session(
        self, session_id: str, question: str, top_k: Optional[int] = None
    ) -> QAResult:
        """Answer a question within a chat session with full conversation history.

        Uses tool calling if enabled, allowing the model to call tools (news, todos, etc.)
        based on natural language understanding. Falls back to document retrieval for
        research questions.

        Args:
            session_id: The chat session ID
            question: The user's question
            top_k: Override number of retrieved chunks

        Returns:
            QAResult with the answer and sources
        """
        history = self.get_history(session_id)

        # Build messages with tool-aware system prompt
        if self._enable_tools:
            tool_schemas = self._tool_registry.to_schemas()
            system_message = build_system_message_with_tools(
                assistant_name=self._assistant_name,
                tools_schemas=tool_schemas,
            )
        else:
            system_message = (
                f"You are {self._assistant_name} — a wise, knowledgeable personal companion.\n"
                "Be thoughtful, direct, and helpful."
            )

        messages = [{"role": "system", "content": system_message}]
        messages.extend(history)
        messages.append({"role": "user", "content": question})

        # Tool-calling loop
        answer = ""
        news_articles: List[NewsArticle] = []
        web_sources: List[dict] = []
        chunks = []
        sources = []
        retrieval = RetrievalResult(question=question, chunks=[], top_k=0)

        if self._enable_tools:
            self._tool_executor.reset()
            tool_calls_made = []

            # Loop until model stops calling tools or max calls reached
            while self._tool_executor.call_count < self._tool_executor.max_calls:
                # Get model response
                response = self._chat_provider.chat(messages=messages)

                # Check for tool calls
                tool_result, response_text = self._tool_executor.process_model_output(response)

                if tool_result:
                    # Tool was called: add to conversation history and loop
                    tool_calls_made.append((tool_result.tool_name, tool_result.parameters))

                    # Track news articles if fetch_news was called
                    if tool_result.tool_name == "fetch_news" and self._news_service:
                        query = tool_result.parameters.get("query", "")
                        fetched_articles = (
                            self._news_service.search_news(query)
                            if query
                            else self._news_service.get_top_news()
                        )
                        if fetched_articles:
                            news_articles.extend(fetched_articles)

                    # Track web search results if web_search was called
                    if tool_result.tool_name == "web_search":
                        raw = tool_result.result.get("raw_results", [])
                        web_sources.extend(raw)

                    tool_output_msg = f"Tool result for {tool_result.tool_name}:\n{tool_result.output}"
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user", "content": tool_output_msg})
                else:
                    # No tool call: model gave final response
                    answer = response_text or response
                    break
            else:
                # Max calls reached
                answer = response_text or response

            # If no answer was generated, use the last response
            if not answer and messages and messages[-1].get("role") == "assistant":
                answer = messages[-1].get("content", "I couldn't generate a response.")
        else:
            # No tool calling: use traditional approach with RAG
            if self._is_conversational(question):
                chunks = []
                retrieval = RetrievalResult(question=question, chunks=[], top_k=0)
            else:
                retrieval = self._retriever.retrieve(question=question, top_k=top_k)
                chunks = retrieval.chunks

            learned_facts_list = []
            if self._fact_service:
                personal_facts = self._fact_service.get_relevant_facts("personal", limit=3)
                work_facts = self._fact_service.get_relevant_facts("work", limit=3)
                learned_facts_list = [
                    {"content": f.content} for f in (personal_facts + work_facts)
                ]

            messages = build_chat_messages(
                question=question,
                chunks=chunks,
                history=history,
                max_chunks=self._max_prompt_chunks,
                assistant_name=self._assistant_name,
                learned_facts=learned_facts_list if learned_facts_list else None,
            )

            answer = self._chat_provider.chat(messages=messages)

        # Save to session history
        user_turn_id = str(uuid.uuid4())
        assistant_turn_id = str(uuid.uuid4())

        turn_index = len(history)
        self._registry.append_turn(
            session_id=session_id,
            turn_id=user_turn_id,
            role="user",
            content=question,
            turn_index=turn_index,
        )

        self._registry.append_turn(
            session_id=session_id,
            turn_id=assistant_turn_id,
            role="assistant",
            content=answer,
            turn_index=turn_index + 1,
        )

        # Sources are used if we have news articles, web results, or document chunks
        sources_used = bool(news_articles or web_sources or chunks)
        return QAResult(
            question=question,
            answer=answer,
            sources=sources,
            retrieval=retrieval,
            prompt="",
            sources_used=sources_used,
            news_sources=[{"title": a.title, "source": a.source, "url": a.url} for a in news_articles],
            web_sources=web_sources,
        )

    def create_session(self, session_id: str, title: str = "") -> None:
        """Create a new chat session.

        Args:
            session_id: Unique session identifier
            title: Optional session title
        """
        self._registry.create_session(session_id=session_id, title=title)

    def list_sessions(self, limit: int = 20) -> List[dict]:
        """List recent chat sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session dicts with session_id, title, created_at, updated_at
        """
        return self._registry.list_sessions(limit=limit)

    def get_history(self, session_id: str) -> List[dict]:
        """Get conversation history for a session as messages.

        Args:
            session_id: The chat session ID

        Returns:
            List of dicts with "role" and "content" keys
        """
        turns = self._registry.get_session_turns(session_id)
        return [{"role": turn["role"], "content": turn["content"]} for turn in turns]

    def get_fact_service(self) -> Optional[FactService]:
        """Get the fact service for external use."""
        return self._fact_service

    def get_web_search_service(self) -> Optional[WebSearchService]:
        """Get the web search service for external use."""
        return self._web_search_service

    def get_registry(self) -> SQLiteRegistry:
        """Get the registry for external use."""
        return self._registry

    def get_habit_service(self) -> Optional[HabitService]:
        """Get the habit service for external use."""
        return self._habit_service
