# 🎓 Multi-Modal AI Enterprise Assistant

> **A production-ready LangGraph-based multi-agent orchestration system that intelligently routes user queries to specialized AI agents for seamless enterprise data access.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/LangChain-🦜-green.svg)](https://github.com/langchain-ai/langchain)
[![LangGraph](https://img.shields.io/badge/LangGraph-🕸️-orange.svg)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📊 Executive Summary

This project provides a **unified natural language interface** to multiple enterprise data sources through an intelligent routing layer. Non-technical users can query structured databases (SQL), internal documents (RAG), and real-time web data without writing code or switching tools.

**Core Innovation:** Automatic intent classification with security-first architecture, enabling:
- 🔒 **Secure database access** with multi-layer SQL injection prevention
- 📚 **Semantic document search** across company knowledge bases
- 🌐 **Real-time web research** for external data needs
- 💬 **Natural conversation** with intelligent agent recommendations
- 📊 **Automatic visualization** of data insights

---

## ✨ Key Features

### 🎯 Intelligent Query Routing
- **Automatic Intent Classification**: GPT OSS 20B supervisor analyzes queries and routes to the optimal agent
- **Multi-Source Integration**: Seamlessly combines SQL databases, document stores, web search, and conversation
- **Visualization Detection**: Automatically generates charts when queries benefit from visual representation

### 🔐 Enterprise-Grade Security
- **Read-Only SQL Access**: Whitelist-based validation blocks all write operations
- **SQL Injection Prevention**: Multi-layer protection with comment stripping and statement validation
- **Secure Architecture**: No direct database modifications, all queries validated before execution

### 🤖 Specialized AI Agents

#### 1. **SQL Agent** (Production-Ready ✅)
- Natural language → SQL query generation
- Pagila DVD rental database (49,636 rows, 15 tables)
- SQLite backend for portability
- Complex joins, aggregations, and analytics

#### 2. **RAG Agent** (Production-Ready ✅)
- Semantic search over 5 internal documents
- FAISS vector store with persistent caching
- Document types: Employee Handbook, Code of Conduct, Incident Response, Company Policy, Procedures
- Citation-backed responses with source attribution

#### 3. **Conversation Agent** (Functional ✅)
- Friendly, approachable personality
- System capability explanations
- Query refinement assistance
- Intelligent fallback for non-data questions

#### 4. **Visualizer Agent** (Fully Implemented ✅)
- Automatic chart type selection (bar, line, pie, scatter, area)
- Responsive Chart.js HTML generation
- Color palette optimization
- File-based persistence with browser preview

#### 5. **Web Research Team** (Architecture Complete ⚠️)
- Multi-node subgraph (Coordinator → Researcher → Report Writer)
- External data synthesis and competitive analysis
- *Note: Currently blocked by Tavily API issues; replacement in progress*

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Query (Natural Language)               │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
                    ┌─────────────────┐
                    │  Main Supervisor │ (GPT OSS 20B)
                    │  Intent Classifier│
                    └────────┬──────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   ┌──────────┐        ┌──────────┐       ┌──────────┐
   │SQL Agent │        │RAG Agent │       │Conv Agent│
   │(Database)│        │(Docs)    │       │(Chat)    │
   └────┬─────┘        └────┬─────┘       └────┬─────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                             │
                     ┌───────▼────────┐
                     │   Visualizer   │ (Conditional)
                     │   Agent        │
                     └────────────────┘
                             │
                             ▼
                      ┌─────────────┐
                      │   Response  │
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
- **Streamlit** (1.41.1): Web interface and chart rendering

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
│       ├── 📄 sql_agent.py         # Database query agent ✅
│       ├── 📄 rag_agent.py         # Document retrieval agent ✅
│       ├── 📄 conversation_agent.py # Chat interface agent ✅
│       ├── 📄 visualizer_agent.py  # Chart generation agent ✅
│       └── 📄 web_team.py          # Web research subgraph ⚠️
│
├── 📂 front-end/
│   └── 📄 app.py                   # Streamlit web application
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

6. **Build the RAG index** (first run only)
   ```python
   from src.agents.rag_agent import initialize_vector_store
   initialize_vector_store(force_rebuild=True)
   ```

### Running the Application

#### Option 1: Streamlit Web Interface (Recommended)
```bash
streamlit run front-end/app.py
```
- Opens at `http://localhost:8501`
- Includes chat interface and automatic chart rendering

#### Option 2: Python Script (CLI)
```python
from src.workflow import workflow, WorkflowState

# Execute a query
result = workflow.invoke({
    "user_input": "Show me top 5 customers by revenue",
    "intent": "conversation",
    "needs_visualization": False,
    "response": "",
    "messages": []
})

print(result["response"])
```

#### Option 3: LangGraph Studio (Development)
```bash
# Install LangGraph CLI
pip install langgraph-cli

# Launch Studio
langgraph dev
```
- Visual workflow debugging
- Step-by-step execution tracing
- State inspection at each node

---

## 💡 Example Queries

### SQL Database Queries
```
✅ "What are the top 10 movies with the highest rental rates?"
✅ "Show me monthly rental trends for 2024"
✅ "Which films have the highest rental rates?"
✅ "List all customers in Canada with their email addresses"
✅ "Create a chart of revenue by store location"
```

(Please note that the SQL agent is currently academically challenged which means it might not understand some requests. Make sure that you are using the correct Pagila terms)

### Document Retrieval (RAG)
```
✅ "What is our policy on accepting gifts from vendors?"
✅ "Summarize the incident response procedure for ransomware"
✅ "What are the eligibility requirements for remote work?"
✅ "Explain the process for requesting leave approval"
✅ "What does our code of conduct say about conflicts of interest?"
```

### General Conversation
```
✅ "How does this system work?"
✅ "What data sources can you access?"
✅ "I need help finding information about our travel policy"
✅ "Can you explain the difference between SQL and RAG queries?"
✅ "What's the best way to visualize sales trends?"
```

### Web Research
```
⏳ Ask virtually anything but make sure to specify web searching
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

### Adding New Tests
```python
# tests/test_rag_agent.py
def test_document_retrieval():
    from src.agents.rag_agent import search_documents
    results = search_documents("remote work policy")
    assert len(results) > 0
    assert "handbook" in results[0].metadata["source"]
```

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

### Database Settings
- **Path:** `data/pagila/pagila.db`
- **Type:** SQLite 3
- **Size:** ~8MB
- **Rebuild:** Delete `pagila.db` and run `initialize_database()`

### Vector Store Settings
- **Path:** `data/index/index.faiss`
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2`
- **Chunk Size:** 1000 characters
- **Overlap:** 200 characters
- **Rebuild:** Call `initialize_vector_store(force_rebuild=True)`

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
| Visualization | ~2-3s | ✅ (HTML file cache) |
| Supervisor Routing | ~0.5s | ❌ |

**Optimization Opportunities:**
- SQL query result caching (Redis/in-memory)
- Conversation history summarization
- Pre-computed aggregations for common queries

---

## 🐛 Known Issues & Limitations

### Current Limitations
1. **Web Research Agent:** Blocked by Tavily API integration issues
   - **Workaround:** Use conversation agent for web-related queries
   - **Fix in Progress:** DuckDuckGo/Wikipedia replacement

2. **Conversation Memory:** Agent is stateless between queries
   - **Impact:** No context retention across messages
   - **Planned Fix:** Conversation buffer in Phase 1 roadmap

3. **Visualization Errors:** Non-numeric data causes chart generation to fail
   - **Workaround:** System gracefully falls back to text response
   - **Expected Behavior:** Error handling with user-friendly messages

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

- **Project Maintainer:** [Joe Al Msann]
- **Email:** [18joe.msane18@gmail.com]

---

## 🎯 Project Goals Achieved

✅ **Multi-Agent Orchestration:** LangGraph-based workflow with intelligent routing  
✅ **Security-First Design:** SQL injection prevention and read-only access  
✅ **Production-Ready SQL Agent:** Comprehensive test coverage (5/5 passing)  
✅ **Semantic Document Search:** FAISS vector store with persistent caching  
✅ **Natural Language Interface:** User-friendly query processing  
✅ **Automatic Visualization:** Chart.js integration with Chart type detection  
✅ **Extensible Architecture:** Easy to add new agents or data sources  
✅ **Enterprise-Grade Features:** Error handling, logging, observability  

---

**Built with ❤️ using LangChain, LangGraph, and Groq**