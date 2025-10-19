"""
RAG Agent Implementation
Handles retrieval-augmented generation over company documents.
"""

import os
from pathlib import Path
from typing import TypedDict, Annotated, Sequence
from operator import add

from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.tools.retriever import create_retriever_tool
from langgraph.prebuilt import create_react_agent

from src.config import app_config
from src.prompts import RAG_AGENT_PROMPT


# =============================================================================
# PATHS CONFIGURATION
# =============================================================================
PROJECT_ROOT = Path(__file__).parent.parent.parent
DOCS_PATH = PROJECT_ROOT / "data" / "docs"
INDEX_PATH = PROJECT_ROOT / "data" / "index"


# =============================================================================
# VECTOR STORE INITIALIZATION
# =============================================================================
def initialize_vector_store(force_rebuild: bool = False):
    """
    Initialize or load the FAISS vector store for company documents.
    
    Args:
        force_rebuild: If True, rebuild the index even if it exists
        
    Returns:
        FAISS vector store instance
    """
    # Create index directory if it doesn't exist
    INDEX_PATH.mkdir(parents=True, exist_ok=True)
    
    # Check if index already exists
    index_file = INDEX_PATH / "index.faiss"
    
    if index_file.exists() and not force_rebuild:
        print("Loading existing vector store from disk...")
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        vectorstore = FAISS.load_local(
            str(INDEX_PATH), 
            embeddings,
            allow_dangerous_deserialization=True
        )
        print(f"Vector store loaded successfully with {vectorstore.index.ntotal} documents")
        return vectorstore
    
    print("Building new vector store from documents...")
    
    # Load documents from the docs directory
    documents = []
    
    # Support multiple file types
    loaders = {
        "*.txt": TextLoader,
        "*.md": TextLoader,
        "*.pdf": PyPDFLoader
    }
    
    for pattern, loader_cls in loaders.items():
        try:
            loader = DirectoryLoader(
                str(DOCS_PATH),
                glob=pattern,
                loader_cls=loader_cls,
                show_progress=True
            )
            docs = loader.load()
            documents.extend(docs)
            print(f"Loaded {len(docs)} documents matching {pattern}")
        except Exception as e:
            print(f"Warning: Could not load {pattern} files: {e}")
    
    if not documents:
        raise ValueError(f"No documents found in {DOCS_PATH}. Please add documents to index.")
    
    print(f"Total documents loaded: {len(documents)}")
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    splits = text_splitter.split_documents(documents)
    print(f"Split into {len(splits)} chunks")
    
    # Create embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    # Create vector store
    vectorstore = FAISS.from_documents(splits, embeddings)
    
    # Save to disk
    vectorstore.save_local(str(INDEX_PATH))
    print(f"Vector store saved to {INDEX_PATH}")
    
    return vectorstore


# =============================================================================
# RETRIEVER TOOL SETUP
# =============================================================================
# Initialize vector store (will load from disk if exists)
try:
    vectorstore = initialize_vector_store(force_rebuild=False)
except Exception as e:
    print(f"Error initializing vector store: {e}")
    print("Please ensure documents exist in data/docs directory")
    vectorstore = None

# Create retriever with optimized parameters
if vectorstore:
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 5,  # Return top 5 most relevant chunks
            "fetch_k": 20,  # Fetch 20 candidates before filtering to 5
        }
    )
    
    # Create retriever tool for the agent
    retriever_tool = create_retriever_tool(
        retriever,
        name="company_knowledge_base",
        description=(
            "Search and retrieve information from company internal documents. "
            "This includes the Employee Handbook, Code of Conduct, Incident Response procedures, "
            "Company Policy, and operational Procedures. "
            "Use this tool to answer questions about HR policies, ethics guidelines, security protocols, "
            "and company operational procedures. "
            "Input should be a search query related to company policies or procedures."
        )
    )
    
    tools = [retriever_tool]
else:
    tools = []
    print("WARNING: RAG agent initialized without retriever tool")


# =============================================================================
# RAG AGENT CREATION
# =============================================================================
rag_agent = create_react_agent(
    model=app_config.rag_model,
    tools=tools,
    prompt=RAG_AGENT_PROMPT
)


# =============================================================================
# RAG NODE FUNCTION
# =============================================================================
def rag_node(state):
    """
    RAG node for LangGraph workflow.
    
    Args:
        state: Graph state containing user_input and other workflow data
        
    Returns:
        Updated state with RAG response
    """
    user_input = state.get("user_input", "")
    
    if not user_input:
        return {
            "messages": state.get("messages", []) + [{
                "role": "assistant",
                "content": "I didn't receive a query. Please provide a question about company policies or procedures."
            }],
            "rag_response": "No input provided"
        }
    
    # Check if vectorstore is initialized
    if not vectorstore:
        return {
            "messages": state.get("messages", []) + [{
                "role": "assistant",
                "content": "I'm sorry, but the document retrieval system is not available. Please ensure company documents are loaded in the data/docs directory."
            }],
            "rag_response": "Vector store not initialized",
            "error": "RAG system unavailable"
        }
    
    try:
        # Invoke the RAG agent
        result = rag_agent.invoke({
            "messages": [
                {"role": "user", "content": user_input}
            ]
        })
        
        # Extract the final response
        agent_messages = result.get("messages", [])
        if agent_messages:
            # Get the last assistant message
            final_message = None
            for msg in reversed(agent_messages):
                if hasattr(msg, 'content') and msg.content:
                    final_message = msg.content
                    break
                elif isinstance(msg, dict) and msg.get("content"):
                    final_message = msg["content"]
                    break
            
            if final_message:
                response = final_message
            else:
                response = "I retrieved the documents but couldn't formulate a response."
        else:
            response = "No response generated from the RAG agent."
        
        # Update state
        return {
            "messages": state.get("messages", []) + [{
                "role": "assistant",
                "content": response
            }],
            "rag_response": response,
            "rag_success": True
        }
        
    except Exception as e:
        error_msg = f"Error during RAG retrieval: {str(e)}"
        print(error_msg)
        
        return {
            "messages": state.get("messages", []) + [{
                "role": "assistant",
                "content": "I apologize, but I encountered an error while searching the company documents. Please try rephrasing your question or contact support if the issue persists."
            }],
            "rag_response": error_msg,
            "rag_success": False,
            "error": error_msg
        }


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================
def rebuild_index():
    """
    Utility function to force rebuild the vector store index.
    Call this when documents are updated.
    """
    print("Rebuilding vector store index...")
    global vectorstore, retriever, retriever_tool, rag_agent
    
    vectorstore = initialize_vector_store(force_rebuild=True)
    
    if vectorstore:
        retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5, "fetch_k": 20}
        )
        
        retriever_tool = create_retriever_tool(
            retriever,
            name="company_knowledge_base",
            description=(
                "Search and retrieve information from company internal documents. "
                "This includes the Employee Handbook, Code of Conduct, Incident Response procedures, "
                "Company Policy, and operational Procedures."
            )
        )
        
        # Recreate agent with new tool
        rag_agent = create_react_agent(
            model=app_config.rag_model,
            tools=[retriever_tool],
            prompt=RAG_AGENT_PROMPT
        )
        
        print("Index rebuilt successfully!")
    else:
        print("Failed to rebuild index")


def search_documents(query: str, k: int = 5):
    """
    Direct search utility for testing the vector store.
    
    Args:
        query: Search query
        k: Number of results to return
        
    Returns:
        List of relevant document chunks
    """
    if not vectorstore:
        print("Vector store not initialized")
        return []
    
    results = vectorstore.similarity_search(query, k=k)
    return results


# =============================================================================
# MAIN (for testing)
# =============================================================================
if __name__ == "__main__":
    # Test the RAG system
    print("=" * 60)
    print("RAG Agent Test")
    print("=" * 60)
    
    # Test query
    test_query = "What is our policy on accepting gifts from vendors?"
    
    print(f"\nQuery: {test_query}")
    print("-" * 60)
    
    # Test state
    test_state = {
        "user_input": test_query,
        "messages": []
    }
    
    # Run RAG node
    result_state = rag_node(test_state)
    
    print("\nResponse:")
    print(result_state.get("rag_response", "No response"))
    print("=" * 60)
    
    # Test direct search
    print("\nDirect Vector Store Search Results:")
    print("-" * 60)
    docs = search_documents(test_query, k=3)
    for i, doc in enumerate(docs, 1):
        print(f"\n{i}. Source: {doc.metadata.get('source', 'Unknown')}")
        print(f"Content: {doc.page_content[:200]}...")