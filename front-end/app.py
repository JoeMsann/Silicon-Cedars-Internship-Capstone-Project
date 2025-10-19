import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import streamlit as st
import streamlit.components.v1 as components
from src.workflow import workflow, WorkflowState
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import List
from pathlib import Path

# --- 1. CONFIGURATION ---

st.set_page_config(page_title="LangGraph AI Workflow", layout="wide", initial_sidebar_state="collapsed")

st.title("🤖 LangGraph Conversational Assistant")

# --- 2. SESSION STATE INITIALIZATION ---

if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "current_chart_html" not in st.session_state:
    st.session_state["current_chart_html"] = None

# --- 3. CORE LOGIC: RUNNING THE GRAPH ---

def run_workflow(user_input: str) -> str:
    """
    Executes the LangGraph workflow and updates the session state.
    """
    
    current_messages = st.session_state.messages
    user_message = HumanMessage(content=user_input)
    current_messages_with_user = current_messages + [user_message]
    
    initial_state: WorkflowState = {
        "user_input": user_input,
        "intent": "conversation",
        "needs_visualization": False,
        "response": "",
        "messages": current_messages_with_user
    }

    try:
        final_state: WorkflowState = workflow.invoke(initial_state)
        st.session_state.messages = final_state["messages"]
        return final_state["response"]

    except Exception as e:
        st.error(f"An error occurred during workflow execution: {e}")
        error_message = AIMessage(content=f"Sorry, an internal error occurred: {e}", name="error")
        st.session_state.messages.append(error_message)
        return "Sorry, I couldn't process your request due to an error."


# --- 4. HELPER FUNCTION TO DISPLAY CHARTS ---

def display_chart_message(message_content: str, message_index: int):
    """
    Display a chart message with embedded HTML (in-memory only).
    """
    # Extract HTML content from message
    html_content = None
    if "<!-- HTML_CONTENT_START -->" in message_content:
        try:
            html_start = message_content.index("<!-- HTML_CONTENT_START -->") + len("<!-- HTML_CONTENT_START -->")
            html_end = message_content.index("<!-- HTML_CONTENT_END -->")
            html_content = message_content[html_start:html_end].strip()
        except (ValueError, IndexError):
            pass
    
    if not html_content:
        st.warning("⚠️ Visualization content not available.")
        return
    
    # Display success banner
    st.success("✅ Visualization created successfully!")
    
    # Embed the chart directly in Streamlit
    components.html(html_content, height=600, scrolling=True)
    
    # Download button for offline use
    st.download_button(
        label="💾 Download Chart HTML",
        data=html_content,
        file_name=f"chart_{message_index}.html",
        mime="text/html",
        key=f"download_{message_index}"
    )

# --- 5. DISPLAY CHAT HISTORY ---

for idx, message in enumerate(st.session_state.messages):
    if isinstance(message, HumanMessage):
        with st.chat_message("user"):
            st.markdown(message.content)
    
    elif isinstance(message, AIMessage):
        with st.chat_message("assistant"):
            # Check if this is a visualization response
            if "📊 Visualization created!" in message.content:
                display_chart_message(message.content, idx)
            else:
                st.markdown(message.content)


# --- 6. CHAT INPUT HANDLING ---

if user_input := st.chat_input("Ask me anything..."):
    with st.spinner("🤔 Thinking..."):
        ai_response_text = run_workflow(user_input)
    
    st.rerun()


# --- 7. SIDEBAR WITH USAGE TIPS ---

with st.sidebar:
    st.header("💡 Usage Tips")
    
    st.markdown("""
    ### Chart Visualizations
    When you request a chart, you can:
    - **View it embedded** in the chat
    - **Download** the HTML file
    - **Open in browser** for full-screen view
    - **Copy the file path** for manual access
    
    ### Example Queries
    Try asking:
    - *"Show top 10 customers by revenue as a bar chart"*
    - *"Visualize monthly rental trends for 2024"*
    - *"Graph film categories by popularity"*
    
    ### Conversation Memory
    The system remembers your conversation history and will automatically summarize when needed.
    """)
    
    if st.button("🗑️ Clear Chat History", key="clear_history"):
        st.session_state.messages = []
        st.session_state.current_chart_html = None
        st.rerun()