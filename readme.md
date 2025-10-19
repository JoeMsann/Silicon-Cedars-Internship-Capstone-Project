# Capstone Multi-Agent System (Supervisor → Workers)

This project implements a Supervisor-Worker multi-agent system using **LangGraph**, **LangChain**, **Groq**, **Tavily**, **FAISS**, and **Chainlit**. It follows the required hierarchy:

- **Supervisor** (LLM router using structured output)  
  Routes to one of:
  - **SQL Query Agent** — NL → SQL for **Pagila (Postgres)**, executes safely, explains results  
  - **Web Research Team** — Tavily search → synthesized report  
  - **Visualization Agent** — Generates **Chart.js** interactive HTML (attached in chat)  
  - **Conversation Agent** — General assistant  
  - **RAG Agent** — Answers from local `data/docs/*.txt` via FAISS  
  - **Finish**

## Quick Start (Windows `cmd`)

```cmd
:: Activate the conda env you already set up
conda activate capstone-project

:: Required API keys
set GROQ_API_KEY=YOUR_GROQ_KEY
set TAVILY_API_KEY=YOUR_TAVILY_KEY

:: Optional LangSmith for tracing
set LANGSMITH_API_KEY=YOUR_LANGSMITH_KEY
set LANGSMITH_TRACING=true
set LANGSMITH_PROJECT=capstone-project

:: (Optional) Ensure Postgres Pagila is reachable with your creds in config.py
:: Default: host=localhost port=5432 db=pagila user=postgres password=postgres

:: Run the app
chainlit run src/app.py -w
