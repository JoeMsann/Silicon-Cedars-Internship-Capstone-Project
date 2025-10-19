# 🤖 AI-Powered Multi-Agent System with LangGraph

> **Enterprise-grade conversational AI system** combining SQL database queries, document retrieval, and natural language processing through intelligent agent orchestration.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3.16-green.svg)](https://www.langchain.com/)
[![Groq](https://img.shields.io/badge/Groq-Cloud-purple.svg)](https://groq.com/)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Usage Examples](#-usage-examples)
- [Known Issues & Limitations](#-known-issues--limitations)
- [Testing](#-testing)
- [Configuration](#-configuration)
- [Security](#-security)
- [Performance](#-performance)
- [Contributing](#-contributing)
- [Roadmap](#-roadmap)
- [License](#-license)

---

## 🎯 Overview

This project demonstrates a **production-ready multi-agent system** built with **LangChain** and **LangGraph**, orchestrating specialized AI agents to handle diverse user queries through natural language processing. The system intelligently routes requests to the appropriate agent and provides accurate, context-aware responses.

### Key Capabilities

- 🗄️ **Natural Language to SQL**: Query business data using plain English
- 📚 **Semantic Document Search**: Retrieve information from company documents
- 💬 **Conversational AI**: Friendly chat interface for general queries
- 🌐 **Web Research**: ⚠️ Multi-agent web search (Work in Progress)
- 📊 **Data Visualization**: ⚠️ Automatic chart generation (Work in Progress)

---

## ✨ Features

### ✅ Production-Ready Components

| Feature | Status | Description |
|---------|--------|-------------|
| **SQL Agent** | ✅ **COMPLETE** | Natural language database queries with security validation |
| **RAG Agent** | ✅ **COMPLETE** | Semantic search across 5 company documents using FAISS |
| **Conversation Agent** | ✅ **COMPLETE** | Friendly chat interface (stateless) |
| **Security Layer** | ✅ **COMPLETE** | Multi-layer SQL injection prevention |
| **Test Suite** | ✅ **COMPLETE** | 5/5 SQL agent tests passing |
| **LangGraph Workflow** | ✅ **COMPLETE** | Supervisor-based intent routing |

### ⚠️ Work in Progress Components

| Feature | Status | Notes |
|---------|--------|-------|
| **Web Research Team** | ⚠️ **BLOCKED** | DuckDuckGo/Wikipedia integration in progress |
| **Visualizer Agent** | ⚠️ **PLACEHOLDER** | Chart.js generation framework ready |
| **RAG Visualization** | ⚠️ **NOT FUNCTIONAL** | Currently no company documents support visualization data |
| **Streamlit Frontend** | ⚠️ **IN DEVELOPMENT** | Web interface coming soon |

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input (Natural Language)            │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Supervisor    │ ← Classifies intent
                    │   (Reasoning)   │   (sql|rag|conversation|web)
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  SQL Agent   │    │  RAG Agent   │    │Conversation  │
│              │    │              │    │    Agent     │
│ Query Pagila │    │ Search Docs  │    │  General AI  │
│   Database   │    │ (FAISS)      │    │    Chat      │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                    │
       │                   │                    │
       └───────────────────┴────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Visualizer   │ (Work in Progress)
                    │   Agent      │
                    └──────┬───────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Response   │
                    │(Text/HTML)  │
                    └─────────────┘
```

### State Management (LangGraph)
```python
class WorkflowState(TypedDict):
    user_input: str              # Original query
    intent: str                  # sql|rag|conversation|web
    needs_visualization: bool    # Chart generation flag
    response: str                # Final output
    messages: List[BaseMessage]  # Conversation history
```

---

## 🛠️ Technology Stack

### Core Frameworks
- **LangChain** (0.3.16): Agent orchestration and tool integration
- **LangGraph** (0.2.62): State-based workflow management
- **Streamlit** (1.41.1): Web interface (coming soon)

### AI Models (via Groq Cloud)
| Agent | Model | Temperature | Purpose |
|-------|-------|-------------|---------|
| Supervisor | GPT OSS 20B | 0.0 | Intent classification |
| SQL Agent | GPT OSS 120B | 0.0 | Query generation |
| RAG Agent | Qwen 3 32B | 0.0 | Document retrieval |
| Conversation | Kimi K2 Instruct | 1.0 | Natural dialogue |

### Data & Storage
- **SQLite**: Portable database (no external dependencies)
- **FAISS**: Local vector store with disk persistence
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim)

### Security & Validation
- Custom SQL injection prevention layer
- Whitelist/blacklist validation system
- Read-only database access enforcement

---

## 📁 Project Structure

```
capstone-project/
│
├── 📄 README.md                    # This file
├── 📄 requirements.txt             # Python dependencies
├── 📄 .env.example                 # Environment variables template
├── 📄 .gitignore                   # Git ignore rules
│
├── 📂 data/
│   ├── 📂 documents/               # RAG source documents (5 files)
│   │   ├── code_of_conduct.txt
│   │   ├── handbook.txt
│   │   ├── incident_response.txt
│   │   ├── company_policy.txt
│   │   └── procedures.txt
│   │
│   ├── 📂 pagila/                  # Database files
│   │   ├── 📂 csv/                 # 15 CSV files (49,636 rows total)
│   │   ├── pagila.db               # SQLite database (auto-generated)
│   │   └── pagila-schema.sql       # Original PostgreSQL schema
│   │
│   └── 📂 index/                   # FAISS vector store cache
│       └── index.faiss
│
├── 📂 src/
│   ├── 📄 config.py                # API keys & LLM configurations
│   ├── 📄 prompts.py               # All agent system prompts
│   ├── 📄 workflow.py              # Main LangGraph orchestration
│   │
│   └── 📂 agents/
│       ├── 📄 sql_agent.py         # ✅ Database query agent
│       ├── 📄 rag_agent.py         # ✅ Document retrieval agent
│       ├── 📄 conversation_agent.py # ✅ Chat interface agent
│       ├── 📄 visualizer_agent.py  # ⚠️ Chart generation (WIP)
│       └── 📄 web_team.py          # ⚠️ Web research (WIP)
│
├── 📂 front-end/
│   └── 📄 app.py                   # ⚠️ Streamlit application (WIP)
│
└── 📂 tests/
    └── 📄 test_sql_agent.py        # SQL agent test suite (5/5 passing)
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- Groq API key ([Get one free](https://console.groq.com/))
- 2GB disk space (for database + vector index)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/capstone-project.git
   cd capstone-project
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys:
   # GROQ_API_KEY=your_groq_api_key_here
   # LANGSMITH_API_KEY=your_langsmith_key_here (optional)
   ```

5. **Initialize the database** (first run only)
   ```python
   from src.agents.sql_agent import initialize_database
   initialize_database()
   ```

6. **Run the application**
   ```bash
   streamlit run front-end/app.py
   ```

### 🌐 Web Interface (Coming Soon!)

**A hosted web application will be available soon**, allowing you to interact with the chatbot directly through your browser without needing to install anything locally. Stay tuned for the deployment announcement!

---

## 💡 Usage Examples

### SQL Queries (Database)
```
✅ "Show me the top 5 customers by total payment amount"
✅ "What are all the action movies in our inventory?"
✅ "Find customers who rented more than 30 films"
✅ "List all stores with their total revenue"
```

**⚠️ Known Issue: SQL Agent Limitations**

The SQL agent can sometimes **take queries too literally**, which may cause it to get stuck or fail to execute certain requests. For example:

- **Overly specific interpretations**: If you ask "show me customers in city X", it might look for an exact city name match rather than using fuzzy matching
- **Complex aggregations**: Multi-level GROUP BY queries with multiple JOINs can sometimes cause timeouts
- **Ambiguous requests**: Questions like "give me the best customers" without clear metrics may confuse the agent

**Workarounds:**
- Be as specific as possible in your queries (e.g., "top 10 customers by total payment amount")
- Break complex questions into simpler sub-queries
- If the agent seems stuck, try rephrasing your question

This behavior is **work in progress** and will be improved in future updates with better query parsing and error recovery.

---

### RAG Queries (Company Documents)
```
✅ "What is our remote work policy?"
✅ "Summarize the incident response procedure for ransomware"
✅ "What are the eligibility requirements for remote work?"
✅ "Explain the process for requesting leave approval"
✅ "What does our code of conduct say about conflicts of interest?"
```

---

### General Conversation
```
✅ "How does this system work?"
✅ "What data sources can you access?"
✅ "I need help finding information about our travel policy"
✅ "Can you explain the difference between SQL and RAG queries?"
```

---

### Web Research
```
⚠️ Web research functionality is currently under development
```

---

### Data Visualization
```
⚠️ Visualization is currently not functional with RAG queries
```

**⚠️ RAG Visualization Limitation**

Currently, **visualization does not work with RAG queries** because:
- The company documents in the knowledge base do not contain structured numerical data suitable for charts
- The RAG agent is designed for text-based information retrieval, not data analysis
- Chart generation requires tabular data (which comes from SQL queries), not prose text

**What works:**
- ✅ SQL query results can be visualized (when visualization agent is complete)
- ✅ RAG queries return text-based answers from documents

**What doesn't work:**
- ❌ Asking "visualize the remote work policy" (no numerical data to chart)
- ❌ Trying to create graphs from document content

This is expected behavior and **not a bug**. Visualization features are specifically designed for SQL query results containing numerical data. RAG queries will continue to provide excellent text-based responses for policy and procedure questions.

---

## 🛑 Known Issues & Limitations

### Current Limitations

**⚠️ ALL FEATURES MARKED AS "WORK IN PROGRESS" ARE ACTIVELY BEING DEVELOPED**

1. **SQL Agent Behavior Issues**
   - **Problem:** The SQL agent sometimes interprets queries too literally, causing it to block or fail
   - **Impact:** Complex or ambiguous queries may not execute properly
   - **Status:** 🔧 **Work in Progress** - Improving query parsing and error handling
   - **Workaround:** Be specific in your queries and break complex questions into simpler parts

2. **RAG Visualization Not Functional**
   - **Problem:** Visualization does not work with RAG queries
   - **Reason:** Company documents contain no numerical data suitable for charts
   - **Status:** ⏳ **Expected Behavior** - This is by design, not a bug
   - **Workaround:** Use SQL queries for data that needs visualization

3. **Web Research Agent**
   - **Problem:** DuckDuckGo/Wikipedia integration incomplete
   - **Impact:** Web search functionality not available
   - **Status:** 🔧 **Work in Progress** - Implementing search tool integration
   - **Workaround:** Use conversation agent for general information

4. **Visualizer Agent**
   - **Problem:** Chart.js generation not yet implemented
   - **Impact:** No automatic chart creation from SQL results
   - **Status:** 🔧 **Work in Progress** - Framework ready, generation logic in development
   - **Workaround:** SQL query results returned as formatted text tables

5. **Streamlit Frontend**
   - **Problem:** Web interface incomplete
   - **Impact:** No user-friendly GUI currently available
   - **Status:** 🔧 **Work in Progress** - Interface design and deployment in progress
   - **Update:** **Web application coming soon!** You'll be able to interact with the chatbot directly through a hosted website without local installation

6. **Conversation Memory**
   - **Problem:** Agent is stateless between queries
   - **Impact:** No context retention across messages
   - **Status:** 🔧 **Work in Progress** - Memory buffer planned in next update

---

### Troubleshooting

**Issue:** `ModuleNotFoundError: No module named 'src'`
```bash
# Solution: Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
# Or run from project root
cd capstone-project && python front-end/app.py
```

**Issue:** `No such table: actor` (SQL errors)
```python
# Solution: Rebuild database
from src.agents.sql_agent import initialize_database
initialize_database()
```

**Issue:** `Index file not found` (RAG errors)
```python
# Solution: Rebuild FAISS index
from src.agents.rag_agent import initialize_vector_store
initialize_vector_store(force_rebuild=True)
```

---

## 🧪 Testing

### Run SQL Agent Tests
```bash
pytest tests/test_sql_agent.py -v
```

**Current Test Coverage:**
- ✅ Security validation (injection prevention)
- ✅ Schema inspection
- ✅ SQL execution
- ✅ Natural language queries
- ✅ Complex multi-table joins

**Test Results:** 5/5 passing

---

## ⚙️ Configuration

### API Keys (`.env` file)
```bash
# Required
GROQ_API_KEY=gsk_your_key_here

# Optional (for observability)
LANGSMITH_API_KEY=ls_your_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=capstone-project
```

### Model Configuration (`src/config.py`)
```python
class Config:
    tool_model = ChatGroq(model="openai/gpt-oss-120b")       # Intent classification
    sql_model = ChatGroq(model="openai/gpt-oss-120b")        # SQL generation
    rag_model = ChatGroq(model="qwen/qwen3-32b")             # Document retrieval
    conversation_model = ChatGroq(model="moonshotai/kimi-k2-instruct-0905")
    reasoning_model = ChatGroq(model="openai/gpt-oss-20b")   # Supervisor
```

---

## 🔒 Security Features

### SQL Injection Prevention
1. **Whitelist Validation:** Only `SELECT` statements allowed
2. **Blacklist Filtering:** Blocks `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`, `EXEC`
3. **Comment Stripping:** Removes `--`, `/*`, `*/` to prevent comment-based injection
4. **Statement Separation:** Allows only single `;` at end (no chained queries)

### Data Access Controls
- **Read-Only Mode:** Database opened with `check_same_thread=False` for concurrent access
- **No Direct Modifications:** All writes blocked at validation layer
- **Schema Inspection Only:** Users can view structure but not alter it

### API Key Management
- Environment variables (not committed to Git)
- `.env.example` template provided
- Keys never exposed in logs or responses

---

## 📊 Performance Metrics

| Component | Latency | Caching |
|-----------|---------|---------|
| SQL Query | ~1-2s | ❌ |
| RAG Retrieval | ~0.5-1s | ✅ (FAISS disk cache) |
| Conversation | ~1-1.5s | ❌ |
| Visualization | ~2-3s | ✅ (HTML file cache - WIP) |
| Supervisor Routing | ~0.5s | ❌ |

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Write tests** for new functionality
4. **Ensure all tests pass** (`pytest tests/`)
5. **Commit changes** (`git commit -m 'Add amazing feature'`)
6. **Push to branch** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request**

### Code Style
- Follow PEP 8 guidelines
- Use type hints for function signatures
- Add docstrings for all public functions
- Keep functions under 50 lines when possible

---

## 🗺️ Roadmap

### Phase 1 (Current Sprint) 🔄
- [ ] Complete web research agent (DuckDuckGo/Wikipedia integration)
- [ ] Implement visualizer agent (Chart.js generation)
- [ ] Add conversation memory buffer
- [ ] Deploy Streamlit frontend

### Phase 2 (Next Quarter)
- [ ] Add more RAG document sources
- [ ] Implement caching layer (Redis)
- [ ] Add conversation history persistence
- [ ] Performance optimizations

### Phase 3 (Future)
- [ ] Multi-database support
- [ ] Custom visualization templates
- [ ] Advanced analytics dashboard
- [ ] Mobile-responsive design

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **LangChain Team:** For the excellent orchestration framework
- **Groq:** For fast, affordable LLM inference
- **PostgreSQL/Pagila:** For the sample database schema
- **FAISS Team:** For the efficient vector search library
- **Anthropic Claude:** For assistance in development and documentation

---

## 📧 Contact

- **Project Maintainer:** Joe Al Msann
- **Email:** 18joe.msane18@gmail.com

---

## 🎯 Project Goals Achieved

✅ **Multi-Agent Orchestration:** LangGraph-based workflow with intelligent routing  
✅ **Security-First Design:** SQL injection prevention and read-only access  
✅ **Production-Ready SQL Agent:** Comprehensive test coverage (5/5 passing)  
✅ **Semantic Document Search:** FAISS vector store with persistent caching  
✅ **Natural Language Interface:** User-friendly query processing  
⚠️ **Automatic Visualization:** Framework ready, implementation in progress  
✅ **Extensible Architecture:** Easy to add new agents or data sources  
✅ **Enterprise-Grade Features:** Error handling, logging, observability  

---

**Built with ❤️ using LangChain, LangGraph, and Groq**