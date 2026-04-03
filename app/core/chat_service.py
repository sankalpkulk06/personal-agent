import uuid
from typing import List, Optional

from app.core.qa_service import QAResult
from app.providers.ollama_chat import OllamaChatProvider
from app.retrieval.prompt_builder import build_chat_messages
from app.retrieval.retriever import Retriever
from app.storage.sqlite_registry import SQLiteRegistry


class ChatService:
    """Session-aware chat service with conversation history and persistence."""

    def __init__(
        self,
        retriever: Retriever,
        chat_provider: OllamaChatProvider,
        registry: SQLiteRegistry,
        max_prompt_chunks: int = 5,
    ):
        self._retriever = retriever
        self._chat_provider = chat_provider
        self._registry = registry
        self._max_prompt_chunks = max_prompt_chunks

    def answer_in_session(
        self, session_id: str, question: str, top_k: Optional[int] = None
    ) -> QAResult:
        """Answer a question within a chat session with full conversation history.

        Args:
            session_id: The chat session ID
            question: The user's question
            top_k: Override number of retrieved chunks

        Returns:
            QAResult with the answer and sources
        """
        history = self.get_history(session_id)
        retrieval = self._retriever.retrieve(question=question, top_k=top_k)

        messages = build_chat_messages(
            question=question,
            chunks=retrieval.chunks,
            history=history,
            max_chunks=self._max_prompt_chunks,
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
            sources=retrieval.chunks,
            retrieval=retrieval,
            prompt="",
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
