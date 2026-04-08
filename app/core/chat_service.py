import re
import uuid
from typing import List, Optional

from app.core.qa_service import QAResult
from app.core.fact_service import FactService
from app.providers.ollama_chat import OllamaChatProvider
from app.retrieval.prompt_builder import build_chat_messages
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

    def __init__(
        self,
        retriever: Retriever,
        chat_provider: OllamaChatProvider,
        registry: SQLiteRegistry,
        fact_service: Optional[FactService] = None,
        max_prompt_chunks: int = 5,
        assistant_name: str = "Sanky",
    ):
        self._retriever = retriever
        self._chat_provider = chat_provider
        self._registry = registry
        self._fact_service = fact_service
        self._max_prompt_chunks = max_prompt_chunks
        self._assistant_name = assistant_name

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

    def answer_in_session(
        self, session_id: str, question: str, top_k: Optional[int] = None
    ) -> QAResult:
        """Answer a question within a chat session with full conversation history.

        Automatically skips document retrieval for conversational messages (greetings,
        meta-questions) to keep responses fast and natural.

        Args:
            session_id: The chat session ID
            question: The user's question
            top_k: Override number of retrieved chunks

        Returns:
            QAResult with the answer and sources
        """
        history = self.get_history(session_id)

        if self._is_conversational(question):
            chunks = []
            sources = []
            retrieval = RetrievalResult(question=question, chunks=[], top_k=0)
        else:
            retrieval = self._retriever.retrieve(question=question, top_k=top_k)
            chunks = retrieval.chunks
            sources = retrieval.chunks

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

        return QAResult(
            question=question,
            answer=answer,
            sources=sources,
            retrieval=retrieval,
            prompt="",
            sources_used=not self._is_conversational(question),
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
