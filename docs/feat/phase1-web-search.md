# Phase 1 — Web Search

**Est. effort:** 3–4 days  
**Dependencies:** None — fully independent  
**Status:** Not started

---

## Goal

Register a `web_search` tool alongside the existing `fetch_news` tool so the LLM can call it automatically based on intent. Add a `/search` command as an explicit shortcut.

---

## New Files

- `app/core/web_search_service.py`

## Modified Files

- `app/core/tools.py` — register `web_search` tool definition
- `app/core/tool_executor.py` — add `web_search` execution handler
- `app/core/chat_service.py` — inject `WebSearchService`; add `WEB_SEARCH_PATTERNS` routing + `/search` command handler
- `app/config/settings.py` — add `TAVILY_API_KEY`, `WEB_SEARCH_MAX_RESULTS`, `WEB_SEARCH_PROVIDER`
- `pyproject.toml` / `setup.py` — add `tavily-python`, `duckduckgo-search`
- `.env.example` — document new env vars

---

## Tasks

### 1.1 — `WebSearchService` + `SearchResult` dataclass

**File:** `app/core/web_search_service.py`

```python
@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    published_date: str | None

class WebSearchService:
    def __init__(self, api_key: str | None = None, provider: str = "tavily", max_results: int = 5)
    def search(self, query: str) -> list[SearchResult]
    def format_for_context(self, results: list[SearchResult]) -> str
    def _search_tavily(self, query: str) -> list[SearchResult]
    def _search_duckduckgo(self, query: str) -> list[SearchResult]
```

- If `TAVILY_API_KEY` is set and `provider == "tavily"`, use Tavily.
- Otherwise fall back to DuckDuckGo (`duckduckgo_search.DDGS`).
- `format_for_context` returns numbered citation block:
  ```
  [1] Title — snippet (url)
  [2] ...
  ```

**AC:**
- [ ] `search()` returns up to `max_results` results from Tavily when key is set
- [ ] Falls back to DuckDuckGo when `TAVILY_API_KEY` is absent or provider is `"duckduckgo"`
- [ ] `format_for_context()` produces numbered citation output

---

### 1.2 — Register `web_search` tool

**File:** `app/core/tools.py`

Add to the tool registry alongside `fetch_news`:

```python
{
    "name": "web_search",
    "description": "Search the web for current factual information, recent events, definitions, tutorials, or anything not in the user's documents.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"}
        },
        "required": ["query"]
    }
}
```

**File:** `app/core/tool_executor.py`

Add handler:
```python
elif tool_name == "web_search":
    results = web_search_service.search(tool_input["query"])
    return web_search_service.format_for_context(results)
```

**AC:**
- [ ] `web_search` appears in the tools list sent to the LLM
- [ ] LLM can invoke it; `ToolExecutor` executes it and returns formatted results

---

### 1.3 — Inject `WebSearchService` into `ChatService`

**File:** `app/core/chat_service.py`

- Add optional `web_search_service: WebSearchService | None = None` parameter to `__init__`.
- Pass it through to `ToolExecutor`.
- Add `WEB_SEARCH_PATTERNS` list (for factual/definitional queries) alongside existing `NEWS_PATTERNS`.
- Add `/search <query>` explicit command handler — bypasses routing, calls `web_search_service.search()` directly, formats citations, and prints.

Routing priority (from most to least specific):
1. `/search <query>` → always web search
2. `/news <topic>` → always NewsService
3. Matches `NEWS_PATTERNS` → LLM chooses `fetch_news` or `web_search`
4. Everything else → LLM decides (tools available)

**AC:**
- [ ] `sage ask "What is LangGraph?"` returns a web-grounded answer with citations
- [ ] `/search rust tutorial` works in both `sage chat` and `sage ask` modes
- [ ] `/news AI` still uses NewsService as before

---

### 1.4 — Settings + env vars

**File:** `app/config/settings.py`

```python
TAVILY_API_KEY: str = ""
WEB_SEARCH_MAX_RESULTS: int = 5
WEB_SEARCH_PROVIDER: str = "tavily"  # "tavily" | "duckduckgo"
```

**File:** `.env.example`

```env
TAVILY_API_KEY=your_key_here
WEB_SEARCH_MAX_RESULTS=5
WEB_SEARCH_PROVIDER=tavily
```

**AC:**
- [ ] App starts without `TAVILY_API_KEY` set (falls back to DuckDuckGo)
- [ ] Setting `WEB_SEARCH_PROVIDER=duckduckgo` forces DuckDuckGo even if key exists

---

### 1.5 — Add dependencies

**File:** `setup.py` / `pyproject.toml`

```
tavily-python>=0.3
duckduckgo-search>=6.0
```

**AC:**
- [ ] `pip install -e .` installs both packages
- [ ] Both imports succeed in a fresh venv

---

## Citation Format

Responses must include a `web sources:` section when web search results are used:

```
According to [1], LangGraph is a framework for building stateful multi-agent workflows.

web sources:
- [1] LangGraph Docs — https://langchain-ai.github.io/langgraph/
- [2] LangGraph Tutorial — https://medium.com/...
```

---

## Acceptance Criteria (phase complete)

- [ ] `WebSearchService.search()` returns results from Tavily or DuckDuckGo
- [ ] `web_search` registered as callable tool in `ChatService`
- [ ] LLM routes factual questions to web search vs. RAG vs. news correctly
- [ ] Results cited with title + URL in response
- [ ] Works in both `sage chat` and `sage ask` modes
- [ ] Falls back to DuckDuckGo when Tavily key not set
- [ ] `/search <query>` command works as explicit shortcut
