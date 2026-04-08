# Sage - Personal Agent

A **local-first, privacy-respecting personal AI assistant** that combines retrieval-augmented generation (RAG) with persistent memory, live news, and intelligent conversation. Sage is your personal study companion with personality—answering questions about your documents, remembering what you tell it, fetching live news, and maintaining full conversation context.

**No cloud. No tracking. Everything stays on your machine.**

---

## ✨ Core Capabilities

### **1. Smart Chat with Tool Calling** 💬
- **Natural language understanding** — ask for things naturally without commands
- **Automatic tool invocation** — model decides when to fetch news, save facts, add todos
- **Persistent session history** — conversations are saved and can be resumed later
- **Multi-turn context** — LLM remembers everything said in the session
- **Resume any session** — `sage --resume <session-id>` to continue where you left off
- **Session management** — list, view, and organize chat sessions

### **2. Learned Facts** 🧠
- **Remember personal facts** — `/remember-personal Your favorite hobby is reading`
- **Remember work facts** — `/remember-work I lead the ML team`
- **Smart categorization** — personal and work facts organized separately
- **Automatic context** — facts are automatically injected into responses
- **Manage facts** — view all facts, delete unwanted ones, organize by category

### **3. Selective RAG Retrieval** 🎯
- **Conversational questions** (greetings, meta-questions) — skip document retrieval entirely
- **Document-based questions** — retrieve and cite sources only when needed
- **Smart pattern detection** — knows when to use docs vs. just chat
- **Fast responses** — no embedding latency for casual conversation

### **4. Live News Fetching** 📰
- **Natural language news queries** — "What is the news on NASA today?"
- **Direct news command** — `/news SpaceX` for instant formatted news
- **AI-generated summaries** — get a consolidated summary (under 200 words) of all articles
- **Topic extraction** — automatically extracts topics from questions
- **Full sentence search** — `/news What happened with the Mars launch` works perfectly
- **Persistent news context** — follow-up questions remember the articles
- **Proper citations** — news sources cited separately from documents

### **5. Apple Reminders Todos** ✅
- **Quick todo capture** — `/todo Buy oat milk` adds a reminder from chat
- **Natural language due dates** — `/todo Buy milk @tomorrow` or `/todo Call mom @next Tuesday at 3pm`
- **Custom reminder lists** — `/todo Buy milk #Shopping` to add to specific lists
- **Flexible date parsing** — supports relative dates, specific dates, and times
- **Native macOS integration** — uses the built-in Reminders app through AppleScript
- **Configurable target list** — choose a default list with `REMINDERS_DEFAULT_LIST`

### **6. Document Management** 📚
- **Multi-format support** — `.txt`, `.md`, `.pdf` files
- **Bulk ingestion** — `sage ingest --path ./documents/`
- **Metadata tracking** — file size, type, date, checksums
- **Vector embeddings** — semantic search across all documents
- **Citation system** — all answers cite exact document sources

### **7. Personality-Driven Responses** 🎭
- **Named assistant** — "You are Sage — a wise, knowledgeable personal companion"
- **Natural tone** — conversational, not robotic
- **Context-aware** — different response style for personal facts vs. document answers
- **Thoughtful advice** — like a trusted advisor, not a search engine

### **8. Conversation Analytics** 📊
- **Usage patterns** — track total sessions, turns, and conversation frequency
- **Activity insights** — discover your most active days and times
- **Command statistics** — see which commands you use most
- **Topic analysis** — understand your top question types
- **Fact insights** — review learned facts by category
- **Dashboard view** — `/analytics` command for visual stats

### **9. Configuration & Customization** ⚙️
- **Environment variables** — all settings configurable via `.env`
- **Custom assistant name** — change who you're talking to
- **Retrieval depth** — adjust how many documents to retrieve (in-session)
- **Chunk size & overlap** — fine-tune document chunking
- **Max results** — control news result count

---

## 🤖 How It Works: Open Source Tool Calling

Sage uses **open source Ollama models with tool calling** — the model understands when to call tools based on natural language, without needing explicit commands.

**The Flow:**
1. **You ask naturally:** "What's the news on Tesla?" or "Remember that I like coffee"
2. **Model understands intent:** Identifies that it needs to fetch news or save a fact
3. **Automatically calls tools:** Generates JSON with the tool name and parameters
4. **Tools execute:** Fetches news, saves facts, adds todos, searches documents
5. **Model responds:** Incorporates tool results into a natural response

**No `/commands` required** — but they still work as shortcuts if you prefer them.

Example:
```
you: What's happening with SpaceX and can you add it to my reminders?
Sage: I'll fetch the latest news and add it to your reminders.
[Tool: fetch_news(query="SpaceX")]
[Tool: add_todo(task="Check SpaceX update", due_date="today")]
→ Found 5 articles about SpaceX... I've also added a reminder for you.
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Ollama installed and running
- 2GB+ RAM available

### Installation

```bash
git clone <repo-url>
cd personal-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Start Ollama

```bash
ollama serve
```

In another terminal, pull the models:

```bash
ollama pull nomic-embed-text      # Embeddings (small & fast)
ollama pull llama3.2:3b           # Chat model (lightweight)
```

### First Steps

```bash
# Show configuration
sage config

# Ingest your documents
sage ingest --path "./my-documents"

# Start chatting!
sage chat
```

---

## 💬 Interactive Chat Mode

### Starting Chat

```bash
# New session
sage chat

# Resume a previous session
sage chat --resume <session-id>
sage --resume <session-id>  # Shortcut
```

### Chat Commands

| Command | Purpose |
|---------|---------|
| `/help` | Show all commands |
| `/session` | Display current session ID |
| `/sessions` | List recent chat sessions |
| `/analytics` | View usage statistics and patterns |
| `/topk <n>` | Set retrieval depth for this session |
| `/remember-personal <fact>` | Save a personal fact |
| `/remember-work <fact>` | Save a work fact |
| `/facts [personal\|work]` | List learned facts |
| `/forget <fact-id>` | Delete a fact |
| `/news [query]` | Fetch live news |
| `/todo <task> [#list] [@due]` | Add a task to Apple Reminders (with optional list & date/time) |
| `exit` or `quit` | Exit chat |

### Usage Examples

**Learn about yourself:**
```
you : /remember-personal I live in NYC
✓ Personal fact saved: I live in NYC

you : /remember-work I'm a software engineer
✓ Work fact saved: I'm a software engineer

you : where do I live?
assistant
You live in NYC.
```

**Fetch news with AI-generated summary:**
```
you : /news Tesla
━━━━━━ News: Tesla ━━━━━━

📋 Summary
Tesla's latest developments include advances in autonomous driving capabilities, expanding production facilities globally, and strategic partnerships in the EV market. The company continues to lead in battery technology innovation while facing competition from traditional automakers entering the electric vehicle space. Recent quarterly earnings show strong growth despite market volatility.

📰 Articles
[1] Tesla releases next-gen Model improvements
    Reuters | 2026-04-08
    https://news.google.com/...

[2] Elon Musk announces new Gigafactory plans
    Bloomberg | 2026-04-07
    https://news.google.com/...

[3] Tesla stock surges on strong earnings report
    CNBC | 2026-04-06
    https://news.google.com/...
```

**Chat with persistence:**
```
you : What is the news on SpaceX today?
# Fetches live articles, displays summary, injects into context

you : where was it launched from?
assistant
According to the latest news [1], SpaceX launched from...
news sources:
- [1] SpaceX launches Falcon 9... — Reuters

you : /sessions
# Resume this session later!
```

**Search documents:**
```
you : what did I write about machine learning?
assistant
According to your notes [1], machine learning is...
document sources:
- [1] machine-learning-notes.md
```

**Capture a todo in Apple Reminders:**
```
you : /todo Buy oat milk
✓ Added todo to Reminders: Buy oat milk

you : /todo Buy groceries #Shopping
✓ Added todo to Shopping: Buy groceries

you : /todo Buy organic items #Shopping List
✓ Added todo to Shopping List: Buy organic items

you : /todo Call mom @tomorrow
✓ Added todo to Reminders: Call mom due Wed, Apr 08 at 12:00AM

you : /todo Pay rent #Bills @next 1st
✓ Added todo to Bills: Pay rent due Thu, May 01 at 12:00AM

you : /todo Email tax documents @April 8th at 3pm #Todo
✓ Added todo to Todo: Email tax documents due Wed, Apr 08 at 03:00PM

you : /todo Meeting #Work @next Tuesday at 3pm
✓ Added todo to Work: Meeting due Tue, Apr 15 at 03:00PM

you : /todo Planning #Work Projects @next Friday at 10am
✓ Added todo to Work Projects: Planning due Fri, Apr 11 at 10:00AM
```

**Manage facts:**
```
you : /facts work
[1] I'm a software engineer
    a1b2c3d4... | 2026-04-07

[2] I lead the ML team
    b2c3d4e5... | 2026-04-06

you : /forget a1b2c3d4
✓ Fact forgotten
```

**View conversation analytics:**
```
you : /analytics
╭─ Analytics Dashboard ─╮

📊 Conversation Overview
  Total Sessions:         12
  Total Turns:            156
  Avg Turns per Session:  13.0
  Longest Session:        34 turns

📈 Activity Patterns
  First Session:          2026-03-20
  Last Session:           2026-04-08
  Days Active:            15
  Sessions per Day:       0.80
  Most Active Day:        Tuesday (3 sessions)
  Most Active Hour:       14:00

⚡ Top Commands
  /news                  24 times
  /todo                  18 times
  /facts                 12 times

💬 Top Question Words
  what                   28 times
  how                    15 times
  why                    8 times

🧠 Learned Facts by Category
  personal               8 facts
  work                   5 facts

╰──────────────────────╯
```

---

## 🛠️ CLI Commands

### Configuration

```bash
sage config
# Output: Shows all current settings
```

### Document Ingestion

```bash
# Ingest a single file
sage ingest --path "./document.pdf"

# Ingest entire directory
sage ingest --path "./documents/"

# Both .md, .txt, .pdf are supported
```

### Single Question Mode

```bash
# Ask a question and exit
sage ask "What are the key concepts in distributed systems?"

# Override retrieval depth
sage ask "Summarize my notes" --top-k 10

# Export answer to Markdown
sage ask "What did I learn?" --export
```

### Interactive Chat

```bash
sage chat                    # New session
sage chat --top-k 7          # Custom retrieval depth
sage chat --resume <id>      # Resume session
sage --resume <id>           # Quick resume
```

### Todo with Natural Language Dates and Custom Lists

In chat mode, use `/todo` to add tasks to Apple Reminders with optional due dates and custom lists:

```bash
# Basic task
/todo Buy milk

# Add to specific Reminders list
/todo Buy groceries #Shopping
/todo Pay utilities #Bills
/todo Review PR #Work

# Lists with spaces in names
/todo Buy organic items #Shopping List
/todo Pay rent #Bills and Expenses
/todo Sprint planning #Work Projects

# Add with due date
/todo Call mom @tomorrow
/todo Meeting @next Tuesday at 3pm
/todo Workout @3pm

# Combine list and due date
/todo Dinner prep #Personal @6pm
/todo Project deadline #Work @next Friday
/todo Anniversary #Important Dates @April 15
```

**List syntax:** Use `#ListName` to specify which Reminders list to add to. List names can include spaces (e.g., `#Shopping List`, `#Bills and Expenses`). If omitted, uses `REMINDERS_DEFAULT_LIST` (default: "Reminders").

**Date patterns:**
- **Relative:** today, tomorrow, tonight, next Monday, next week, etc.
- **Specific dates:** April 15, 2026-04-20, April 15 at 9am
- **Times:** 3pm, 9:30am, 14:45, etc.
- **Combinations:** next Tuesday at 3pm, April 20 at 6:30pm

---

## ⚙️ Configuration

### Environment Variables (`.env`)

```env
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=llama3.2:3b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
REMINDERS_DEFAULT_LIST=Reminders

# Chunking
CHUNK_SIZE=800
CHUNK_OVERLAP=120

# Retrieval
RETRIEVAL_TOP_K=5
NEWS_MAX_RESULTS=5

# Personality
ASSISTANT_NAME=Sage

# Storage
DATA_DIR=./data
```

### Recommended Ollama Models

**For Tool Calling (recommended):**
```bash
ollama pull llama3.1:8b           # Excellent tool calling, good speed
ollama pull mistral:7b            # Very good tool calling, fast
```

**For Speed (lightweight, but less reliable tool calling):**
```bash
ollama pull llama3.2:3b           # Smaller, but tool calling less reliable
ollama pull nomic-embed-text      # 274MB — fast embeddings
```

**Note:** Smaller models (3b) have lower tool-calling accuracy. For best results with tool calling, use `llama3.1:8b` or `mistral:7b` (requires ~8GB RAM).

**For Embeddings:**
```bash
ollama pull nomic-embed-text      # Fast and effective
ollama pull all-minilm:22m        # Better quality, smaller than others
```

---

## 📊 How It Works

### Conversation Flow

```
User Input
    ↓
Pattern Detection
    ├─ Conversational? (greeting, meta-question)
    │  └→ No RAG retrieval, just chat
    ├─ News query? ("news on X", "what happened to Y")
    │  └→ Fetch live news, inject context
    ├─ Has cached news context?
    │  └→ Re-inject articles, continue conversation
    └─ Document question?
       └→ RAG retrieval, cite sources
    ↓
Inject Context
    ├─ Learned facts (personal + work)
    ├─ Retrieved documents (if applicable)
    ├─ Live news articles (if applicable)
    └─ Conversation history
    ↓
LLM Response (Ollama)
    ↓
Display with Citations
    ├─ News sources (📰)
    └─ Document sources (📄)
    ↓
Save to Session
```

### Session Persistence

```
Session created → Turns stored in SQLite
├─ Turn 1: User question
├─ Turn 2: Assistant answer
├─ Turn 3: User follow-up
└─ ...
    ↓
Later: Resume session
├─ Load all turns
├─ Re-inject context
└─ Continue conversation
```

---

## 🎯 Real-World Examples

### Scenario 1: Research with Follow-ups

```
you : What is the news on climate change today?
# Fetches 5 articles about climate change

you : What are the main solutions mentioned?
# Re-uses cached articles, LLM answers in context

you : Tell me about renewable energy
# Switches to document search (new topic)
# Clears news cache, does RAG
```

### Scenario 2: Personal Knowledge Base

```
you : /remember-personal I have a dog named Max
you : /remember-personal Max's birthday is July 15

you : When is Max's birthday?
# Sage remembers from learned facts

you : /facts personal
# Lists all personal facts with dates
```

### Scenario 3: Work Context

```
you : /remember-work I work on the payment system
you : /remember-work My team has 4 people

you : Tell me about payment systems in the book
# Sage knows you work on payments, includes in context
```

---

## 📈 Architecture

### Core Components

| Component | Purpose |
|-----------|---------|
| **ChatService** | Manages sessions, routing, context injection |
| **FactService** | Stores and retrieves learned facts |
| **NewsService** | Fetches live news from Google News RSS |
| **TodoService** | Adds tasks to macOS Reminders app |
| **Retriever** | RAG retrieval with embeddings |
| **OllamaChatProvider** | LLM interface to Ollama |
| **SQLiteRegistry** | Persists sessions, facts, metadata |
| **ChromaStore** | Vector database for embeddings |

### Data Storage

```
data/
├── sqlite/registry.db         # Sessions, facts, metadata
├── chroma/                    # Vector embeddings
└── cache/                     # Temporary files
```

---

## 🚀 Performance

### Typical Response Times

| Query Type | Time | Notes |
|-----------|------|-------|
| Conversational | <100ms | No RAG overhead |
| News query | 2-3s | Web fetch + LLM |
| Document search | 1-2s | Embedding + retrieval + LLM |
| Follow-up (cached news) | 1-2s | Uses cached articles |

### Memory Usage

- **Base system**: ~300MB
- **With 1 model loaded**: ~800MB
- **With large documents**: +500MB per 100MB docs

---

## 🔧 Troubleshooting

### Ollama not connecting

```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# Start Ollama if not running
ollama serve
```

### No embeddings error

```bash
# Ensure embedding model is pulled
ollama pull nomic-embed-text

# Check it's available
ollama list
```

### Out of memory

- Use smaller model: `mistral:7b` instead of `llama2:13b`
- Reduce `CHUNK_SIZE` in `.env`
- Free up system RAM

### Chat feels slow

- Reduce `RETRIEVAL_TOP_K` in `.env` (default: 5)
- Use `/topk 3` in chat to retrieve fewer documents
- Switch to faster model in Ollama

---

## 📚 Settings Reference

### Environment Variables

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=llama3.2:3b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Document Chunking
CHUNK_SIZE=800              # Characters per chunk
CHUNK_OVERLAP=120           # Overlap between chunks

# Retrieval
RETRIEVAL_TOP_K=5           # Documents to retrieve
NEWS_MAX_RESULTS=5          # News articles to fetch

# Reminders (macOS)
REMINDERS_DEFAULT_LIST=Reminders  # Default Reminders list for /todo

# Personality
ASSISTANT_NAME=Sage        # Your assistant's name
APP_ENV=development

# Storage
DATA_DIR=./data             # Where to store data
```

---

## 🎯 Features Roadmap

### ✅ Completed
- [x] Chat with session history
- [x] Learned facts (personal/work)
- [x] Live news fetching
- [x] Selective RAG routing
- [x] Document management
- [x] Conversation context
- [x] Source citations
- [x] Apple Reminders integration

### 🚀 Upcoming
- [ ] Fact verification against documents
- [ ] Automatic fact extraction from responses
- [ ] Semantic fact linking & inference
- [ ] Chat history search
- [ ] Web API server mode
- [ ] Dashboard UI
- [ ] Batch processing
- [ ] Multi-user support

---

## 💡 Tips & Tricks

### Optimize for Your Use Case

**For research:**
```bash
sage config
# Increase RETRIEVAL_TOP_K to 10 in .env
sage chat --top-k 10
```

**For quick answers:**
```bash
# Use single question mode
sage ask "Quick answer?"
```

**For casual chat:**
```bash
# Session mode remembers everything
sage chat
sage --resume <id>
```

### Best Practices

- **Regular ingestion** — keep your documents up to date
- **Organized facts** — use `/remember-personal` and `/remember-work` to keep knowledge organized
- **Session management** — `/sessions` to find relevant past conversations
- **Topic switching** — start a new session for different topics
- **Fact cleanup** — use `/forget` to remove outdated facts

---

## 📝 License

[Add your license here]

---

## 🙋 Contributing

[Add contribution guidelines]

---

## 📧 Support

For issues, feature requests, or questions:
- Check the [Troubleshooting](#-troubleshooting) section
- Review existing settings in `.env`
- Ensure Ollama is running and models are pulled

---

**Made with ❤️ for your personal knowledge base.**
