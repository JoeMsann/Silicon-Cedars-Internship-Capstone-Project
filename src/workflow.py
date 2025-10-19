from typing import TypedDict
from src.config import app_config
from langgraph.graph import StateGraph, START, END
from src.prompts import * 
from src.agents.web_team import web_team_builder
from src.agents.sql_agent import query_sql_agent
from src.agents.rag_agent import rag_node
from src.agents.visualizer_agent import visualizer_builder
import json
import re
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing_extensions import Annotated

# =============================================================================
# CONVERSATION SUMMARIZATION
# =============================================================================
def should_summarize(messages: list) -> bool:
    """
    Determine if conversation should be summarized.
    
    Triggers summarization when:
    - More than 12 messages (6-7 exchanges)
    - Excludes system messages from count
    
    Called by: supervisor_node (before routing to agents)
    Benefit: Saves tokens by summarizing BEFORE agent processing
    
    Args:
        messages: Current message history
        
    Returns:
        bool: True if summarization needed
    """
    # Count only user and assistant messages (exclude system messages)
    conversation_messages = [
        msg for msg in messages 
        if isinstance(msg, (HumanMessage, AIMessage))
    ]
    
    # Trigger after 6-7 exchanges (12-14 messages)
    return len(conversation_messages) > 12

def summarize_conversation(messages: list) -> list:
    """
    Summarize conversation history when it gets too long.
    
    Strategy:
    1. Keep system messages (prompts, instructions)
    2. Keep last 4 messages (2 recent exchanges)
    3. Summarize everything in between
    4. Return: [system messages] + [summary] + [recent messages]
    
    Called by: supervisor_node (before routing)
    This ensures all agents work with a compressed context window.
    
    Args:
        messages: Full conversation history
        
    Returns:
        Condensed message list with summary
    """
    print("\n🔄 SUMMARIZING CONVERSATION (reducing context window)...")
    
    # Separate message types
    system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
    conversation_messages = [msg for msg in messages if isinstance(msg, (HumanMessage, AIMessage))]
    
    if len(conversation_messages) <= 4:
        # Not enough to summarize
        return messages
    
    # Keep last 4 messages (2 exchanges)
    recent_messages = conversation_messages[-4:]
    messages_to_summarize = conversation_messages[:-4]
    
    # Build summarization prompt
    conversation_text = "\n".join([
        f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
        for msg in messages_to_summarize
    ])
    
    summarization_prompt = f"""Please create a concise summary of this conversation history. 
Focus on:
- Key topics discussed
- Important information shared (data, policies, procedures)
- User's goals or questions
- Decisions or conclusions reached

Keep the summary to 3-4 sentences maximum.

Conversation to summarize:
{conversation_text}

Summary:"""
    
    # Use conversation model for summarization
    summary_response = app_config.conversation_model.invoke([
        SystemMessage(content="You are a helpful assistant that creates concise conversation summaries."),
        HumanMessage(content=summarization_prompt)
    ])
    
    summary_text = summary_response.content
    
    print(f"✅ Summary created: {summary_text[:100]}...")
    print(f"   Reduced from {len(messages_to_summarize)} to 1 summary message\n")
    
    # Build new message list
    summary_message = SystemMessage(
        content=f"[Previous conversation summary]: {summary_text}"
    )
    
    # Return: system messages + summary + recent messages
    return system_messages + [summary_message] + recent_messages

# =============================================================================
# CUSTOM REDUCER FOR MESSAGES WITH SUMMARIZATION
# =============================================================================

def messages_reducer(left: list, right: list) -> list:
    """
    Custom reducer for messages that supports both appending and replacing.
    
    If right list starts with a SystemMessage containing "REPLACE_HISTORY",
    it means we want to replace the entire history (for summarization).
    Otherwise, append normally.
    
    Usage patterns:
    - Normal append: return {"messages": [new_message]}
    - Replace history: return {"messages": [SystemMessage("REPLACE_HISTORY"), ...new_history]}
    
    Args:
        left: Existing messages in state
        right: New messages to add/replace
        
    Returns:
        Updated message list
    """
    if not right:
        return left
    
    # Check if this is a replace operation (for summarization)
    if (len(right) > 0 and 
        isinstance(right[0], SystemMessage) and 
        "REPLACE_HISTORY" in right[0].content):
        # Replace operation - return everything except the marker
        print("   🔄 Replacing message history (summarization)")
        return right[1:]  # Skip the marker message
    
    # Normal append operation
    return left + right

# =============================================================================
# AGENT SETUP
# =============================================================================

conversation_agent = app_config.conversation_model
conversation_prompt = ChatPromptTemplate.from_messages([
    ("system", CONVERSATION_AGENT_PROMPT),
    MessagesPlaceholder(variable_name="history")
])
conversation_chain = conversation_prompt | conversation_agent

supervisor = app_config.reasoning_model
supervisor_prompt = ChatPromptTemplate.from_messages([
    ("system", MAIN_SUPERVISOR_PROMPT),
    ("user", "{user_input}")
])
supervisor_chain = supervisor_prompt | supervisor

# =============================================================================
# STATE DEFINITION
# =============================================================================

class WorkflowState(TypedDict):
    user_input: str
    intent: str
    needs_visualization: bool
    response: str
    messages: Annotated[list, messages_reducer]  # Use custom reducer instead of operator.add

# =============================================================================
# SQL ERROR VALIDATION
# =============================================================================

def has_sql_error(sql_response: str) -> bool:
    """
    Check if SQL agent response contains error indicators.
    
    Detects various error patterns:
    - Security rejections (❌ QUERY REJECTED)
    - SQL execution errors (❌ SQL ERROR)
    - Unexpected errors (❌ UNEXPECTED ERROR)
    - Agent failures (❌ Agent Error)
    - Clarification requests (CLARIFICATION_NEEDED, "I need some clarification")
    - Empty results that would fail visualization
    
    Args:
        sql_response: Raw text response from SQL agent
        
    Returns:
        bool: True if error detected, False if successful query
    """
    # Convert to lowercase for case-insensitive matching
    response_lower = sql_response.lower()
    
    # Error indicators
    error_patterns = [
        "❌ query rejected",
        "❌ sql error",
        "❌ unexpected error",
        "❌ agent error",
        "❌ security check failed",
        "clarification_needed:",
        "i need some clarification",
        "returned no results",
        "query executed successfully but returned no results",
        "error:",
        "failed to",
        "could not",
        "unable to"
    ]
    
    # Check for error patterns
    for pattern in error_patterns:
        if pattern in response_lower:
            return True
    
    # Check if response has actual data (presence of pipe-delimited table)
    # Valid SQL results should have at least one pipe character for the table
    if "|" not in sql_response:
        # No table structure found - likely an error or explanation
        return True
    
    return False

# =============================================================================
# SQL FORMATTING HELPER
# =============================================================================

def format_sql_response(sql_output: str) -> str:
    """
    Convert SQL agent's pipe-delimited output to clean markdown tables.
    
    Args:
        sql_output: Raw SQL agent output with pipe-delimited tables
        
    Returns:
        Formatted markdown string with proper tables
    """
    lines = sql_output.split('\n')
    formatted_lines = []
    in_table = False
    headers = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if this is a query explanation section
        if line.startswith("Query:") or line.startswith("Generated SQL:") or line.startswith("Notes:"):
            if in_table:
                formatted_lines.append("")  # Add spacing after table
                in_table = False
            formatted_lines.append(f"**{line}**")
            i += 1
            continue
        
        # Check if this is a SQL code block
        if line.startswith("```sql") or line.startswith("```"):
            if in_table:
                formatted_lines.append("")
                in_table = False
            # Keep SQL code blocks as-is
            formatted_lines.append(line)
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                formatted_lines.append(lines[i])
                i += 1
            if i < len(lines):
                formatted_lines.append(lines[i])  # Closing ```
            i += 1
            continue
        
        # Skip separator lines (===, ---)
        if set(line) <= {'=', '-', ' ', '|'} and len(line) > 5:
            i += 1
            continue
        
        # Check if this is a table header (contains |)
        if '|' in line and not in_table:
            # Extract headers
            headers = [col.strip() for col in line.split('|') if col.strip()]
            
            # Start markdown table
            formatted_lines.append("")  # Blank line before table
            formatted_lines.append("| " + " | ".join(headers) + " |")
            formatted_lines.append("|" + "|".join(["---" for _ in headers]) + "|")
            in_table = True
            i += 1
            continue
        
        # Check if this is a table row
        if '|' in line and in_table:
            values = [val.strip() for val in line.split('|') if val.strip()]
            if len(values) == len(headers):
                formatted_lines.append("| " + " | ".join(values) + " |")
            i += 1
            continue
        
        # Check for "Total rows:" line
        if "Total rows:" in line:
            if in_table:
                formatted_lines.append("")  # Add spacing after table
                in_table = False
            formatted_lines.append(f"\n**{line}**")
            i += 1
            continue
        
        # Check for "... (X more rows)" line
        if "more rows)" in line:
            if in_table:
                formatted_lines.append("")
                in_table = False
            formatted_lines.append(f"\n*{line}*")
            i += 1
            continue
        
        # Regular line
        if in_table and line == "":
            formatted_lines.append("")
            in_table = False
        elif line:
            formatted_lines.append(line)
        
        i += 1
    
    return '\n'.join(formatted_lines)

# =============================================================================
# NODE IMPLEMENTATIONS
# =============================================================================

def supervisor_node(state: WorkflowState) -> dict:
    """
    Supervisor node that analyzes user input and determines:
    1. Intent (conversation, web, rag, or sql)
    2. Whether visualization is needed (for rag and sql intents)
    3. Whether to summarize conversation history (BEFORE routing to agents)
    """
    user_input = state["user_input"]
    messages = list(state.get("messages", []))
    
    print(f"\n🎯 SUPERVISOR NODE")
    print(f"   Current message count: {len(messages)}")
    
    # Check if summarization needed BEFORE processing
    if should_summarize(messages):
        print("   📊 Triggering conversation summarization...")
        summarized = summarize_conversation(messages)
        print(f"   ✅ Summarized to {len(summarized)} messages")
        messages_to_use = summarized
        needs_replace = True
    else:
        messages_to_use = messages
        needs_replace = False

    analysis_prompt = f"""
User Query: "{user_input}"

Analyze this query and determine the intent and visualization needs.
"""
    response = supervisor_chain.invoke({"user_input": analysis_prompt})
    response_content = response.content

    # Parse the JSON response from the supervisor
    try:
        # Clean the response to extract JSON
        if "```json" in response_content:
            json_str = response_content.split("```json")[1].split("```")[0].strip()
        elif "```" in response_content:
            json_str = response_content.split("```")[1].split("```")[0].strip()
        else:
            json_match = re.search(r'\{[^}]+\}', response_content)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_content
        
        supervisor_decision = json.loads(json_str)
        
        intent = supervisor_decision.get("intent", "conversation")
        
        # Only set needs_visualization for rag and sql intents
        if intent in ["rag", "sql"]:
            needs_visualization = supervisor_decision.get("needs_visualization", False)
        else:
            needs_visualization = False
            
    except (json.JSONDecodeError, AttributeError, KeyError) as e:
        print(f"Error parsing supervisor response: {e}")
        print(f"Response content: {response_content}")
        intent = "conversation"
        needs_visualization = False
    
    print(f"   📍 Intent: {intent}")
    print(f"   📊 Needs visualization: {needs_visualization}")
    
    # Return with history replacement if summarization occurred
    if needs_replace:
        replace_marker = SystemMessage(content="REPLACE_HISTORY")
        return {
            "intent": intent,
            "needs_visualization": needs_visualization,
            "messages": [replace_marker] + messages_to_use
        }
    else:
        # Don't add any new messages (user message already in state from app.py)
        return {
            "intent": intent,
            "needs_visualization": needs_visualization,
            "messages": []
        }

def conversation_node(state: WorkflowState) -> dict:
    """Handle conversational queries with memory"""
    messages = list(state.get("messages", []))
    
    print(f"\n💬 CONVERSATION NODE")
    print(f"   Message count: {len(messages)}")
    
    # Use full history for conversation
    response = conversation_chain.invoke({
        "history": messages
    })
    
    ai_message = AIMessage(content=response.content, name="conversation")
    
    return {
        "response": response.content,
        "messages": [ai_message]
    }

def rag_agent_node(state: WorkflowState) -> dict:
    """Handle RAG queries"""
    rag_node_state = rag_node(state)
    rag_response = rag_node_state["rag_response"]
    
    ai_message = AIMessage(content=rag_response, name="rag_agent")
    
    return {
        "response": rag_response,
        "messages": [ai_message]
    }

def sql_node(state: WorkflowState) -> dict:
    """
    Handle SQL queries with improved formatting and error validation.
    
    CRITICAL: This node now validates SQL responses for errors.
    If an error is detected AND visualization was requested,
    needs_visualization is automatically set to False to prevent
    the visualizer from attempting to chart error messages.
    """
    print(f"\n🗄️ SQL NODE")
    
    sql_response = query_sql_agent(state["user_input"])
    
    # VALIDATION: Check for errors in SQL response
    has_error = has_sql_error(sql_response)
    
    if has_error:
        print(f"   ⚠️ SQL Error detected - preventing visualization")
        
        # Format the error response
        formatted_response = format_sql_response(sql_response)
        
        ai_message = AIMessage(content=formatted_response, name="sql_agent")
        
        # CRITICAL: Override needs_visualization to False
        return {
            "response": formatted_response,
            "messages": [ai_message],
            "needs_visualization": False  # Prevent visualizer from running
        }
    
    # Success path - format and optionally visualize
    print(f"   ✅ SQL query successful - continuing to visualization if requested")
    
    formatted_response = format_sql_response(sql_response)
    
    ai_message = AIMessage(content=formatted_response, name="sql_agent")
    
    return {
        "response": formatted_response,
        "messages": [ai_message]
        # needs_visualization remains unchanged (from supervisor decision)
    }

def web_subgraph_node(state: WorkflowState) -> dict:
    """Handle web research queries"""
    user_input = state["user_input"]
    
    # Call web team subgraph
    web_state = {"query": user_input, "results": "", "report": "", "needs_report": False}
    web_result = web_team_builder.compile().invoke(web_state)
    
    # Extract response
    response_content = web_result.get("report", "") or web_result.get("results", "No results found.")
    
    ai_message = AIMessage(content=response_content, name="web_team")
    
    return {
        "response": response_content,
        "messages": [ai_message]
    }

def visualization_node(state: WorkflowState) -> dict:
    """
    Handle visualization of data.
    Returns both file path and HTML content for flexible rendering.
    """
    user_input = state["user_input"]
    intent = state["intent"]
    response = state["response"]
    
    visualizer_state = {
        "user_input": user_input, 
        "intent": intent, 
        "response": response,
        "chart_type": "",
        "data_structure": "",
        "parsed_data": {},
        "chart_data": {},
        "html_output": "",
        "debug_log": [],
        "file_path": "",
        "file_url": ""
    }

    visualization_result = visualizer_builder.compile().invoke(visualizer_state)
    
    # Extract results
    file_path = visualization_result.get("file_path", "")
    file_url = visualization_result.get("file_url", "")
    html_output = visualization_result.get("html_output", "")
    
    # Create a structured response that includes metadata for the frontend
    # This allows Streamlit to parse and render appropriately
    response_content = f"""📊 Visualization created!

File: {file_path}
Open in browser: {file_url}

<!-- HTML_CONTENT_START -->
{html_output}
<!-- HTML_CONTENT_END -->"""

    ai_message = AIMessage(content=response_content, name="visualizer_agent")
    
    return {
        "response": response_content,
        "messages": [ai_message]
    }
# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

builder = StateGraph(WorkflowState)

# Add nodes
builder.add_node("main_supervisor", supervisor_node)
builder.add_node("conversation_node", conversation_node)
builder.add_node("web_team", web_subgraph_node)
builder.add_node("sql_agent", sql_node)
builder.add_node("rag_agent", rag_agent_node)
builder.add_node("visualizer_agent", visualization_node)

# Routing functions
def route_supervisor(state) -> str:
    """Decide which first-level node to call from the supervisor."""
    intent = state.get("intent")

    if intent == "conversation":
        return "conversation_node"
    elif intent == "sql":
        return "sql_agent"
    elif intent == "rag":
        return "rag_agent"
    elif intent == "web":
        return "web_team"
    else:
        return "conversation_node"

def route_visualizer(state) -> str:
    """
    Check if visualization is needed after SQL or RAG.
    
    CRITICAL: This now respects the needs_visualization flag that
    may have been overridden by sql_node if errors were detected.
    """
    if state.get("needs_visualization"):
        print(f"   → Routing to visualizer")
        return "visualizer_agent"
    else:
        print(f"   → Skipping visualization (needs_visualization=False)")
        return END

# Build edges
builder.add_edge(START, "main_supervisor")
builder.add_conditional_edges(
    "main_supervisor",
    route_supervisor,
    {
        "conversation_node": "conversation_node",
        "sql_agent": "sql_agent",
        "rag_agent": "rag_agent",
        "web_team": "web_team",
    },
)
builder.add_conditional_edges(
    "sql_agent",
    route_visualizer,
    {
        "visualizer_agent": "visualizer_agent",
        END: END,
    },
)
builder.add_conditional_edges(
    "rag_agent",
    route_visualizer,
    {
        "visualizer_agent": "visualizer_agent",
        END: END,
    },
)

builder.add_edge("conversation_node", END)
builder.add_edge("web_team", END)
builder.add_edge("visualizer_agent", END)

workflow = builder.compile()