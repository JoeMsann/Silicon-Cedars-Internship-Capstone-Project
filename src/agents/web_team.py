"""
Web Research Team - Multi-Agent Subgraph for External Information Retrieval
Uses DuckDuckGo and Wikipedia for comprehensive web research.
"""

from src.config import app_config
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from src.prompts import WEB_COORDINATOR_PROMPT, REPORT_WRITER_PROMPT, RESEARCHER_PROMPT

# Import search tools
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_community.tools import WikipediaQueryRun

# =============================================================================
# SEARCH TOOLS SETUP
# =============================================================================

# DuckDuckGo for general web search
try:
    ddg_search = DuckDuckGoSearchRun()
    print("✅ DuckDuckGo search tool initialized")
except Exception as e:
    print(f"⚠️  DuckDuckGo initialization warning: {e}")
    ddg_search = None

# Wikipedia for structured knowledge
try:
    wikipedia = WikipediaQueryRun(
        api_wrapper=WikipediaAPIWrapper(
            top_k_results=3,  # Return top 3 most relevant articles
            doc_content_chars_max=4000  # Limit content length per article
        )
    )
    print("✅ Wikipedia search tool initialized")
except Exception as e:
    print(f"⚠️  Wikipedia initialization warning: {e}")
    wikipedia = None

# Combine tools (filter out None if initialization failed)
search_tools = [tool for tool in [ddg_search, wikipedia] if tool is not None]

if not search_tools:
    print("❌ ERROR: No search tools available! Install dependencies:")
    print("   pip install duckduckgo-search wikipedia")
    # Create dummy tool to prevent crashes
    from langchain_core.tools import Tool
    search_tools = [Tool(
        name="dummy_search",
        func=lambda x: "Search functionality unavailable. Please install duckduckgo-search and wikipedia packages.",
        description="Placeholder search tool"
    )]

# =============================================================================
# RESEARCH AGENT WITH DUAL SEARCH CAPABILITY
# =============================================================================

research_agent = create_react_agent(
    model=app_config.search_tool_model,
    tools=search_tools,
    prompt=RESEARCHER_PROMPT
)

# =============================================================================
# REPORT WRITER AGENT (NO TOOLS NEEDED)
# =============================================================================

report_writer_agent = create_react_agent(
    model=app_config.reasoning_model,
    tools=[],
    prompt=REPORT_WRITER_PROMPT
)

# =============================================================================
# WEB COORDINATOR AGENT (NO TOOLS NEEDED)
# =============================================================================

web_coordinator = create_react_agent(
    model=app_config.reasoning_model,
    tools=[],
    prompt=WEB_COORDINATOR_PROMPT
)

# =============================================================================
# COORDINATOR PROMPT TEMPLATE
# =============================================================================

coordinator_prompt_template = PromptTemplate.from_template("""
Please analyze this query well:
User Query: {query}

Respond in this EXACT format:
INTENT: [True/False]
OPTIMIZED_QUERY: [your optimized search query]

Guidelines:
- INTENT: True if user needs comprehensive report/analysis, False for quick facts
- OPTIMIZED_QUERY: Transform query into search-friendly keywords
  * Remove conversational filler
  * Add relevant technical terms
  * Include current year if time-sensitive
  * Keep concise but comprehensive

Examples:
"Can you tell me about Tesla's stock price?" 
-> INTENT: False
-> OPTIMIZED_QUERY: Tesla TSLA stock price current

"Explain how renewable energy impacts the environment"
-> INTENT: True  
-> OPTIMIZED_QUERY: renewable energy environmental impact analysis 2025
""")

# =============================================================================
# STATE DEFINITION
# =============================================================================

class WebTeamState(TypedDict):
    query: str           # Optimized search query
    results: str         # Raw search results from researcher
    report: str          # Formatted report (if needs_report=True)
    needs_report: bool   # Controls whether to generate comprehensive report

# =============================================================================
# NODE IMPLEMENTATIONS
# =============================================================================

def coordinator_node(state: WebTeamState) -> WebTeamState:
    """
    Analyze user query and decide search strategy.
    
    Determines:
    1. Whether to generate comprehensive report (needs_report)
    2. Optimized search query for better results
    
    Args:
        state: Current state with user query
        
    Returns:
        Updated state with needs_report decision and optimized query
    """
    print("\n🧭 WEB COORDINATOR NODE")
    print(f"   Original query: {state['query']}")
    
    prompt = coordinator_prompt_template.invoke({"query": state["query"]})
    response = web_coordinator.invoke({
        "messages": [{"role": "user", "content": prompt.text}]
    })
    content = response['messages'][-1].content.strip()
    
    # Parse the structured response
    lines = content.split('\n')
    
    # Extract intent (needs_report)
    intent_line = next((line for line in lines if line.startswith('INTENT:')), None)
    if intent_line:
        intent_str = intent_line.replace('INTENT:', '').strip()
        needs_report = intent_str.lower() == 'true'
    else:
        needs_report = True  # Default to comprehensive
    
    # Extract optimized query
    query_line = next((line for line in lines if line.startswith('OPTIMIZED_QUERY:')), None)
    if query_line:
        optimized_query = query_line.replace('OPTIMIZED_QUERY:', '').strip()
    else:
        optimized_query = state["query"]  # Fallback to original
    
    print(f"   ✅ Optimized query: {optimized_query}")
    print(f"   📊 Needs report: {needs_report}")
    
    return {
        **state,
        "query": optimized_query,
        "needs_report": needs_report
    }

def researcher_node(state: WebTeamState) -> WebTeamState:
    """
    Execute web search using DuckDuckGo and Wikipedia.
    
    Strategy:
    1. Use research agent with both tools available
    2. Agent decides which tool(s) to use based on query
    3. Aggregates results from multiple sources
    
    Args:
        state: Current state with optimized query
        
    Returns:
        Updated state with search results
    """
    print("\n🔍 RESEARCHER NODE")
    print(f"   Searching for: {state['query']}")
    print(f"   Available tools: {[tool.name for tool in search_tools]}")
    
    try:
        # Invoke research agent with search tools
        search_message = f"""Search for information about: {state['query']}

Use BOTH DuckDuckGo and Wikipedia when appropriate:
- DuckDuckGo: Current news, recent events, real-time data
- Wikipedia: Definitions, background, historical context

Provide comprehensive search results from multiple sources."""
        
        result = research_agent.invoke({
            "messages": [{"role": "user", "content": search_message}]
        })
        
        # Extract final message content
        search_results = result["messages"][-1].content
        
        print(f"   ✅ Search completed ({len(search_results)} characters)")
        
        return {
            **state,
            "results": search_results
        }
        
    except Exception as e:
        error_msg = f"Search error: {str(e)}\n\nPlease try rephrasing your query or checking your internet connection."
        print(f"   ❌ Error: {e}")
        
        return {
            **state,
            "results": error_msg
        }

def report_writer_node(state: WebTeamState) -> WebTeamState:
    """
    Generate comprehensive report from search results.
    
    Synthesizes findings into:
    - Executive summary
    - Key findings (bullet points)
    - Detailed analysis
    - Sources cited
    
    Args:
        state: Current state with search results
        
    Returns:
        Updated state with formatted report
    """
    print("\n📝 REPORT WRITER NODE")
    print("   Generating comprehensive report...")
    
    try:
        report_prompt = f"""Please create a comprehensive, well-structured report based on these web search results:

{state['results']}

Format your report with:
1. **Executive Summary** (2-3 sentences)
2. **Key Findings** (bullet points)
3. **Detailed Analysis** (organized by topic)
4. **Sources** (mention which tools/sources were used)

Make the report professional, readable, and actionable."""
        
        result = report_writer_agent.invoke({
            "messages": [{"role": "user", "content": report_prompt}]
        })
        
        report = result["messages"][-1].content
        
        print(f"   ✅ Report generated ({len(report)} characters)")
        
        return {
            **state,
            "report": report
        }
        
    except Exception as e:
        error_msg = f"Report generation error: {str(e)}"
        print(f"   ❌ Error: {e}")
        
        return {
            **state,
            "report": error_msg
        }

# =============================================================================
# CONDITIONAL ROUTING
# =============================================================================

def route_after_researcher(state: WebTeamState) -> str:
    """
    Route based on coordinator's decision.
    
    If needs_report=True: Generate comprehensive report
    If needs_report=False: Return raw search results
    
    Args:
        state: Current state with needs_report flag
        
    Returns:
        Next node name or END
    """
    if state.get("needs_report"):
        print("   → Routing to report writer")
        return "report_writer"
    else:
        print("   → Returning search results directly")
        return END

# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

web_team_builder = StateGraph(WebTeamState)

# Add nodes
web_team_builder.add_node("coordinator", coordinator_node)
web_team_builder.add_node("researcher", researcher_node)
web_team_builder.add_node("report_writer", report_writer_node)

# Build workflow
web_team_builder.add_edge(START, "coordinator")
web_team_builder.add_edge("coordinator", "researcher")

# Conditional routing after researcher
web_team_builder.add_conditional_edges(
    "researcher",
    route_after_researcher,
    {
        "report_writer": "report_writer",
        END: END
    }
)

# Report writer always ends
web_team_builder.add_edge("report_writer", END)

# Compile the subgraph
web_team_workflow = web_team_builder.compile()

# =============================================================================
# CONVENIENCE FUNCTION FOR TESTING
# =============================================================================

def query_web_team(user_query: str, needs_report: bool = None) -> dict:
    """
    High-level interface for web research team.
    
    Args:
        user_query: Natural language query
        needs_report: Override coordinator's decision (None = auto-detect)
        
    Returns:
        Dict with 'results' and/or 'report' keys
    """
    print(f"\n{'='*80}")
    print(f"WEB RESEARCH TEAM: {user_query}")
    print(f"{'='*80}")
    
    initial_state = {
        "query": user_query,
        "results": "",
        "report": "",
        "needs_report": needs_report if needs_report is not None else False
    }
    
    final_state = web_team_workflow.invoke(initial_state)
    
    return final_state

# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("WEB RESEARCH TEAM TEST")
    print("=" * 80)
    
    # Test 1: Quick fact lookup (no report)
    print("\n\nTest 1: Quick Fact Lookup")
    print("-" * 80)
    result1 = query_web_team("What is the current price of Bitcoin?")
    print("\nFinal Output:")
    print(result1.get("report") or result1.get("results"))
    
    # Test 2: Comprehensive research (with report)
    print("\n\nTest 2: Comprehensive Research")
    print("-" * 80)
    result2 = query_web_team(
        "Explain the environmental impact of renewable energy sources",
        needs_report=True
    )
    print("\nFinal Output:")
    print(result2.get("report"))
    
    print("\n" + "=" * 80)
    print("✅ All tests completed!")