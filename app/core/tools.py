"""Tool definitions for the open source model to call."""
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.core.fact_service import FactService
from app.core.news_service import NewsService
from app.core.reminders_service import RemindersService
from app.retrieval.retriever import Retriever


class ToolParameter(BaseModel):
    """Describes a parameter for a tool."""

    name: str
    type: str  # "string", "integer", "boolean", etc.
    description: str
    required: bool = True
    enum: Optional[List[str]] = None


class Tool(ABC):
    """Base class for all tools."""

    def __init__(self, name: str, description: str, parameters: List[ToolParameter]):
        self.name = name
        self.description = description
        self.parameters = parameters

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters.

        Returns:
            Dict with "success" and "result" or "error" keys
        """
        pass

    def to_schema(self) -> Dict[str, Any]:
        """Convert tool to JSON schema for prompt."""
        param_properties = {}
        required_params = []

        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            param_properties[param.name] = prop
            if param.required:
                required_params.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": param_properties,
                "required": required_params,
            },
        }


class FetchNewsTool(Tool):
    """Fetch live news about a topic."""

    def __init__(self, news_service: NewsService):
        super().__init__(
            name="fetch_news",
            description="Fetch the latest news articles about a specific topic. Returns a summary and list of articles.",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The news topic to search for (e.g., 'Tesla', 'climate change')",
                    required=True,
                )
            ],
        )
        self.news_service = news_service

    def execute(self, query: str = "", **kwargs) -> Dict[str, Any]:
        try:
            articles = self.news_service.search_news(query) if query else self.news_service.get_top_news()
            if articles:
                article_texts = "\n".join(
                    f"- {a.title} ({a.source}): {a.snippet[:100]}..." for a in articles[:5]
                )
                return {
                    "success": True,
                    "result": f"Found {len(articles)} articles about {query or 'top news'}:\n\n{article_texts}",
                }
            return {"success": True, "result": f"No news found for '{query}'"}
        except Exception as e:
            return {"success": False, "error": f"Failed to fetch news: {str(e)}"}


class RememberFactTool(Tool):
    """Remember a personal or work fact."""

    def __init__(self, fact_service: FactService):
        super().__init__(
            name="remember_fact",
            description="Save a fact to remember. Can be personal (about you) or work-related.",
            parameters=[
                ToolParameter(
                    name="fact",
                    type="string",
                    description="The fact to remember",
                    required=True,
                ),
                ToolParameter(
                    name="category",
                    type="string",
                    description="Category: personal or work",
                    required=True,
                    enum=["personal", "work"],
                ),
            ],
        )
        self.fact_service = fact_service

    def execute(self, fact: str = "", category: str = "personal", **kwargs) -> Dict[str, Any]:
        try:
            if not fact:
                return {"success": False, "error": "Fact cannot be empty"}
            self.fact_service.remember(content=fact, category=category)
            return {"success": True, "result": f"✓ {category.title()} fact saved: {fact}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to save fact: {str(e)}"}


class ListFactsTool(Tool):
    """List learned facts by category."""

    def __init__(self, fact_service: FactService):
        super().__init__(
            name="list_facts",
            description="List all learned facts, optionally filtered by category.",
            parameters=[
                ToolParameter(
                    name="category",
                    type="string",
                    description="Filter by category (personal, work, or all)",
                    required=False,
                    enum=["personal", "work", "all"],
                )
            ],
        )
        self.fact_service = fact_service

    def execute(self, category: str = "all", **kwargs) -> Dict[str, Any]:
        try:
            filter_cat = None if category == "all" else category
            facts = self.fact_service.list_facts(category=filter_cat)
            if facts:
                fact_list = "\n".join(f"- {f.content} ({f.category})" for f in facts[:10])
                return {
                    "success": True,
                    "result": f"Your learned facts ({category}):\n\n{fact_list}",
                }
            return {"success": True, "result": f"No {category} facts learned yet."}
        except Exception as e:
            return {"success": False, "error": f"Failed to list facts: {str(e)}"}


class AddTodoTool(Tool):
    """Add a task to Apple Reminders."""

    def __init__(self, reminders_service: RemindersService):
        super().__init__(
            name="add_todo",
            description="Add a task to Apple Reminders with optional due date and list.",
            parameters=[
                ToolParameter(
                    name="task",
                    type="string",
                    description="The task to add",
                    required=True,
                ),
                ToolParameter(
                    name="list_name",
                    type="string",
                    description="Which Reminders list to add to (default: Reminders)",
                    required=False,
                ),
                ToolParameter(
                    name="due_date",
                    type="string",
                    description="Due date in natural language (e.g., tomorrow, next Tuesday, April 15 at 3pm)",
                    required=False,
                ),
            ],
        )
        self.reminders_service = reminders_service

    def execute(self, task: str = "", list_name: Optional[str] = None, due_date: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        try:
            if not task:
                return {"success": False, "error": "Task cannot be empty"}

            # Parse due_date if provided
            parsed_due_date = None
            if due_date:
                try:
                    from dateutil import parser as date_parser
                    parsed_due_date = date_parser.parse(due_date, fuzzy=True)
                except Exception:
                    pass

            target_list = self.reminders_service.add_reminder(
                task=task, list_name=list_name, due_date=parsed_due_date
            )
            due_str = f" due {parsed_due_date.strftime('%a, %b %d at %I:%M%p')}" if parsed_due_date else ""
            return {"success": True, "result": f"✓ Added to {target_list}: {task}{due_str}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to add todo: {str(e)}"}


class SearchDocumentsTool(Tool):
    """Search through your documents for information."""

    def __init__(self, retriever: Retriever):
        super().__init__(
            name="search_documents",
            description="Search through your personal documents and notes using semantic search.",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="What to search for in your documents",
                    required=True,
                ),
                ToolParameter(
                    name="top_k",
                    type="integer",
                    description="Number of results to return (default: 5)",
                    required=False,
                ),
            ],
        )
        self.retriever = retriever

    def execute(self, query: str = "", top_k: int = 5, **kwargs) -> Dict[str, Any]:
        try:
            if not query:
                return {"success": False, "error": "Query cannot be empty"}
            result = self.retriever.retrieve(query, top_k=top_k)
            if result.chunks:
                doc_list = "\n".join(
                    f"- {c.file_name}: {c.text[:100]}..." for c in result.chunks[:3]
                )
                return {"success": True, "result": f"Found in your documents:\n\n{doc_list}"}
            return {"success": True, "result": f"No documents found matching '{query}'"}
        except Exception as e:
            return {"success": False, "error": f"Failed to search documents: {str(e)}"}


class ToolRegistry:
    """Registry of all available tools."""

    def __init__(
        self,
        news_service: Optional[NewsService] = None,
        fact_service: Optional[FactService] = None,
        reminders_service: Optional[RemindersService] = None,
        retriever: Optional[Retriever] = None,
    ):
        self.tools: Dict[str, Tool] = {}

        if news_service:
            self.register(FetchNewsTool(news_service))
        if fact_service:
            self.register(RememberFactTool(fact_service))
            self.register(ListFactsTool(fact_service))
        if reminders_service:
            self.register(AddTodoTool(reminders_service))
        if retriever:
            self.register(SearchDocumentsTool(retriever))

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def get_all(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self.tools.values())

    def to_schemas(self) -> List[Dict[str, Any]]:
        """Convert all tools to JSON schemas for prompt."""
        return [tool.to_schema() for tool in self.get_all()]

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name with parameters."""
        tool = self.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}
        return tool.execute(**parameters)
