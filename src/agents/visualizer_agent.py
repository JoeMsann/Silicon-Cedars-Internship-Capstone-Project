"""
Visualizer Agent - LangGraph Subgraph for Chart.js Visualization
Transforms SQL/RAG query results into interactive HTML charts.
"""

import json
import re
from typing import TypedDict, Dict, List, Any, Optional
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from src.config import app_config
from pathlib import Path
from datetime import datetime

# Create output directory for visualizations
PROJECT_ROOT = Path(__file__).parent.parent.parent
VISUALIZATIONS_DIR = PROJECT_ROOT / "data" / "visualizations"
VISUALIZATIONS_DIR.mkdir(parents=True, exist_ok=True)
# =============================================================================
# STATE DEFINITION
# =============================================================================

class VisualizerState(TypedDict):
    """State for visualization workflow"""
    # Input from main workflow
    user_input: str           # Original user query
    intent: str               # "sql" or "rag" 
    response: str             # Raw text output from SQL/RAG agent
    
    # Analysis node outputs
    chart_type: str           # "bar", "line", "pie", "doughnut", "scatter", "radar"
    data_structure: str       # "time_series", "categorical", "proportional", "correlation"
    
    # Data handling node outputs
    parsed_data: dict         # Structured data extracted from response text
    chart_data: dict          # Chart.js-formatted data object
    
    # Chart construction node outputs
    html_output: str          # Final HTML string with embedded Chart.js
    
    # Debugging
    debug_log: list           # Accumulates debug messages from each node

    file_path: str            # Path to saved HTML file
    file_url: str             # Relative URL for browser access

# =============================================================================
# DATA PARSING FUNCTIONS (Pure Python - No LLM)
# =============================================================================

def parse_sql_results(text: str) -> Dict[str, Any]:
    """
    Parse SQL agent text output into structured format.
    
    Handles pipe-delimited tables with headers and rows.
    
    Args:
        text: Raw SQL output text
        
    Returns:
        Dict with columns and rows, or error state
    """
    # Check for empty results
    if "returned no results" in text.lower():
        return {"error": "No data to visualize", "rows": [], "columns": []}
    
    lines = text.strip().split('\n')
    
    # Find the header line (contains |)
    header_line = None
    data_lines = []
    in_data_section = False
    
    for line in lines:
        # Skip separator lines
        if set(line.strip()) <= {'-', '=', ' '}:
            continue
            
        if '|' in line:
            if header_line is None:
                header_line = line
                in_data_section = True
            elif in_data_section:
                data_lines.append(line)
        elif "Total rows:" in line:
            break
    
    if not header_line:
        return {"error": "Could not parse SQL results", "rows": [], "columns": []}
    
    # Parse headers
    columns = [col.strip() for col in header_line.split('|') if col.strip()]
    
    # Parse rows
    rows = []
    for line in data_lines:
        values = [val.strip() for val in line.split('|') if val.strip()]
        if len(values) == len(columns):
            row_dict = {}
            for i, col in enumerate(columns):
                # Convert numeric values
                val = values[i]
                if val.upper() == 'NULL' or val == '':
                    row_dict[col] = None
                else:
                    # Try to convert to number
                    try:
                        if '.' in val:
                            row_dict[col] = float(val.replace('$', '').replace(',', ''))
                        else:
                            row_dict[col] = int(val.replace(',', ''))
                    except:
                        row_dict[col] = val
            rows.append(row_dict)
    
    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows)
    }

def parse_rag_results(text: str) -> Dict[str, Any]:
    """
    Parse RAG agent text output to extract structured data.
    
    Looks for patterns like lists, timelines, key-value pairs.
    
    Args:
        text: Raw RAG output text
        
    Returns:
        Dict with extracted entities and values
    """
    entities = []
    values = []
    data_type = "general"
    
    # Look for timeline patterns (e.g., "Detection: 0-15 minutes")
    timeline_pattern = r'[-•]\s*([^:]+):\s*([^\n]+)'
    timeline_matches = re.findall(timeline_pattern, text)
    
    if timeline_matches:
        data_type = "timeline"
        for phase, duration in timeline_matches:
            entities.append(phase.strip())
            # Extract numeric value from duration
            numbers = re.findall(r'[\d.]+', duration)
            if numbers:
                # Use the last number (usually the max duration)
                values.append(float(numbers[-1]))
            else:
                values.append(0)
    
    # Look for bullet point lists
    if not entities:
        bullet_pattern = r'[-•]\s*([^\n:]+)'
        bullet_matches = re.findall(bullet_pattern, text)
        if bullet_matches:
            data_type = "list"
            entities = [match.strip() for match in bullet_matches]
            # Assign equal values for list items
            values = [1] * len(entities)
    
    # Look for percentage patterns
    if not entities:
        percent_pattern = r'(\w+[^:]*?):\s*([\d.]+)%'
        percent_matches = re.findall(percent_pattern, text)
        if percent_matches:
            data_type = "percentages"
            for label, value in percent_matches:
                entities.append(label.strip())
                values.append(float(value))
    
    return {
        "type": data_type,
        "entities": entities,
        "values": values,
        "count": len(entities)
    }

def format_for_chartjs(parsed_data: Dict, chart_type: str, data_structure: str) -> Dict:
    """
    Convert parsed data to Chart.js format.
    
    Args:
        parsed_data: Structured data from parsing functions
        chart_type: Type of chart to create
        data_structure: Data structure type
        
    Returns:
        Chart.js data configuration object
    """
    # Color palette (professional, accessible)
    colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']
    
    # Handle error states
    if parsed_data.get("error"):
        return {"error": parsed_data["error"]}
    
    # Handle empty data
    if not parsed_data.get("rows") and not parsed_data.get("entities"):
        return {"error": "No data to visualize"}
    
    # SQL data formatting
    if parsed_data.get("columns"):
        rows = parsed_data["rows"]
        columns = parsed_data["columns"]
        
        # Single row - suggest table format
        if len(rows) == 1:
            return {
                "type": "table",
                "data": parsed_data,
                "message": "Single row result - displaying as table"
            }
        
        # Determine labels and values
        if len(columns) == 2:
            # Simple 2-column data
            labels = [str(row[columns[0]]) for row in rows]
            values = [row[columns[1]] if row[columns[1]] is not None else 0 for row in rows]
        else:
            # Multi-column - use first as label, rest as datasets
            labels = [str(row[columns[0]]) for row in rows]
            datasets = []
            for i, col in enumerate(columns[1:]):
                dataset_values = [row[col] if row[col] is not None else 0 for row in rows]
                datasets.append({
                    "label": col,
                    "data": dataset_values,
                    "backgroundColor": colors[i % len(colors)],
                    "borderColor": colors[i % len(colors)],
                    "borderWidth": 2
                })
        
        # Limit to top 20 for large datasets
        if len(labels) > 20:
            labels = labels[:20]
            if len(columns) == 2:
                values = values[:20]
            else:
                for dataset in datasets:
                    dataset["data"] = dataset["data"][:20]
        
        # Format based on chart type
        if chart_type in ["pie", "doughnut"]:
            return {
                "labels": labels,
                "datasets": [{
                    "data": values if len(columns) == 2 else datasets[0]["data"],
                    "backgroundColor": colors[:len(labels)],
                    "borderWidth": 2,
                    "borderColor": '#fff'
                }]
            }
        elif chart_type == "scatter":
            # Convert to x,y points
            points = [{"x": i, "y": val} for i, val in enumerate(values if len(columns) == 2 else datasets[0]["data"])]
            return {
                "datasets": [{
                    "label": columns[1] if len(columns) == 2 else columns[1],
                    "data": points,
                    "backgroundColor": colors[0],
                    "borderColor": colors[0]
                }]
            }
        else:  # bar, line, radar
            if len(columns) == 2:
                return {
                    "labels": labels,
                    "datasets": [{
                        "label": columns[1],
                        "data": values,
                        "backgroundColor": colors[0] if chart_type == "bar" else 'transparent',
                        "borderColor": colors[0],
                        "borderWidth": 2,
                        "fill": False if chart_type == "line" else True
                    }]
                }
            else:
                return {
                    "labels": labels,
                    "datasets": datasets
                }
    
    # RAG data formatting
    elif parsed_data.get("entities"):
        entities = parsed_data["entities"]
        values = parsed_data["values"]
        
        if chart_type in ["pie", "doughnut"]:
            return {
                "labels": entities,
                "datasets": [{
                    "data": values,
                    "backgroundColor": colors[:len(entities)],
                    "borderWidth": 2,
                    "borderColor": '#fff'
                }]
            }
        else:
            return {
                "labels": entities,
                "datasets": [{
                    "label": "Value",
                    "data": values,
                    "backgroundColor": colors[0] if chart_type == "bar" else 'transparent',
                    "borderColor": colors[0],
                    "borderWidth": 2,
                    "fill": False if chart_type == "line" else True
                }]
            }
    
    return {"error": "Unable to format data for visualization"}

# =============================================================================
# HTML GENERATION FUNCTIONS
# =============================================================================

def generate_chartjs_html(chart_data: Dict, chart_type: str, title: str) -> str:
    """
    Generate complete HTML page with embedded Chart.js.
    
    Args:
        chart_data: Chart.js data configuration
        chart_type: Type of chart
        title: Chart title
        
    Returns:
        Complete HTML string
    """
    # Handle error states
    if chart_data.get("error"):
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Visualization Error</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f5f5f5;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }}
        .error-container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        h2 {{ color: #ef4444; }}
        p {{ color: #6b7280; }}
    </style>
</head>
<body>
    <div class="error-container">
        <h2>⚠️ Visualization Not Available</h2>
        <p>{chart_data.get("error", "Unable to generate visualization")}</p>
        {f'<p>{chart_data.get("message", "")}</p>' if chart_data.get("message") else ''}
    </div>
</body>
</html>
"""
    
    # Handle table format for single row
    if chart_data.get("type") == "table":
        data = chart_data.get("data", {})
        rows = data.get("rows", [])
        columns = data.get("columns", [])
        
        table_html = "<table>"
        table_html += "<tr>" + "".join(f"<th>{col}</th>" for col in columns) + "</tr>"
        for row in rows:
            table_html += "<tr>" + "".join(f"<td>{row.get(col, '')}</td>" for col in columns) + "</tr>"
        table_html += "</table>"
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f5f5f5;
            padding: 40px;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 800px;
            margin: 0 auto;
        }}
        h2 {{ color: #1f2937; margin-bottom: 20px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        th {{
            background: #f9fafb;
            font-weight: 600;
            color: #374151;
        }}
        .note {{
            margin-top: 20px;
            padding: 10px;
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            color: #92400e;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>{title}</h2>
        {table_html}
        <div class="note">
            ℹ️ Single row result displayed as table
        </div>
    </div>
</body>
</html>
"""
    
    # Determine if we need scales configuration
    scales_config = ""
    if chart_type not in ["pie", "doughnut", "radar"]:
        # Check if data contains currency (has $ in any label)
        has_currency = any('$' in str(label) for label in chart_data.get("labels", []))
        
        # Check if labels look like dates
        labels = chart_data.get("labels", [])
        has_dates = any('-' in str(label) for label in labels[:3]) if labels else False
        
        y_axis_config = """
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }""" if has_currency else """
                y: {
                    beginAtZero: true
                }"""
        
        scales_config = f"""
            scales: {{
                {y_axis_config}
            }},"""
    
    # Convert chart_data to JSON
    chart_data_json = json.dumps(chart_data, indent=12)
    
    # Generate complete HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .chart-container {{
            position: relative;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 90%;
            max-width: 1000px;
            height: 70vh;
            max-height: 600px;
        }}
        canvas {{
            max-height: 100%;
        }}
        h1 {{
            color: #1f2937;
            text-align: center;
            margin-bottom: 30px;
            font-size: 24px;
        }}
    </style>
</head>
<body>
    <div class="chart-container">
        <canvas id="myChart"></canvas>
    </div>
    <script>
        const ctx = document.getElementById('myChart').getContext('2d');
        new Chart(ctx, {{
            type: '{chart_type}',
            data: {chart_data_json},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: '{title}',
                        font: {{ size: 18, weight: 'bold' }},
                        padding: {{ bottom: 30 }}
                    }},
                    legend: {{
                        display: true,
                        position: 'top',
                        labels: {{
                            padding: 15,
                            font: {{ size: 12 }}
                        }}
                    }},
                    tooltip: {{
                        enabled: true,
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        padding: 12,
                        cornerRadius: 8,
                        titleFont: {{ size: 14, weight: 'bold' }},
                        bodyFont: {{ size: 13 }},
                        callbacks: {{
                            label: function(context) {{
                                let label = context.dataset.label || '';
                                if (label) {{
                                    label += ': ';
                                }}
                                const value = context.parsed.y !== undefined ? context.parsed.y : context.parsed;
                                if (typeof value === 'number') {{
                                    label += value.toLocaleString();
                                }}
                                return label;
                            }}
                        }}
                    }}
                }},{scales_config}
                animation: {{
                    duration: 1000,
                    easing: 'easeInOutQuart'
                }}
            }}
        }});
    </script>
</body>
</html>"""
    
    return html

def save_html_to_file(html_content: str, user_query: str) -> tuple[str, str]:
    """Save HTML content to a file with timestamped filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Clean query for filename (first 30 chars, alphanumeric only)
    safe_query = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in user_query[:30])
    safe_query = safe_query.strip().replace(' ', '_')
    
    filename = f"viz_{timestamp}_{safe_query}.html"
    file_path = VISUALIZATIONS_DIR / filename
    
    # Save HTML to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"   ✅ Saved visualization to: {file_path.name}")
    
    # Generate relative URL for browser access
    relative_url = f"data/visualizations/{filename}"
    
    return str(file_path.absolute()), relative_url

# =============================================================================
# NODE IMPLEMENTATIONS
# =============================================================================

def analysis_node(state: VisualizerState) -> VisualizerState:
    """
    Analyze data source and determine optimal chart type.
    
    Uses reasoning model to analyze the query and response structure.
    """
    print(f"\n📊 ANALYSIS NODE")
    print(f"   Intent: {state['intent']}")
    print(f"   Response length: {len(state['response'])} chars")
    
    # Build analysis prompt
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a data visualization and SQL analysis expert.

Your tasks:
1. If the intent is "sql", before analyzing for chart type,
   edit the SQL query **response** text as follows:
   - Remove all unnecessary text, explanations, and metadata. Only keep the raw tabular data.
   - Keep only the numeric columns that represent measurable values 
     (such as totals, revenue, counts, spending), excluding ID columns.
   - Merge all other descriptive or textual columns 
     (e.g., customer name, email, film title, actor name) 
     into a single column called "information".
   - Ensure each row now contains:
       information | <numeric_column(s)>
     ready for visualization.
   - If the number of rows exceeds 100, limit to the top 100 rows based on the first numeric column. 

2. Then, based on the rewritten response and the user query,
   determine the optimal chart type and data structure.

Chart type options: [bar, line, pie, doughnut, scatter, radar]
Data structure options: [time_series, categorical, proportional, correlation]

Decision guidelines:
- Time-series data → line chart
- Categorical comparisons or rankings → bar chart
- Percentages or proportions → pie/doughnut
- Correlations between numeric pairs → scatter
- Multi-dimension comparisons → radar

Respond ONLY with a JSON object:
{{"chart_type": "...", "data_structure": "...", "new_response": "..."}}"""),
        ("user", f"""Intent: {state['intent']}
User Query: {state['user_input']}
Response: {state['response']}...

Determine the optimal chart type and data structure.""")
    ])
    
    try:
        chain = analysis_prompt | app_config.reasoning_model
        result = chain.invoke({})
        
        # Parse JSON response
        content = result.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        analysis = json.loads(content)
        chart_type = analysis.get("chart_type", "bar")
        data_structure = analysis.get("data_structure", "categorical")
        new_response = analysis.get("new_response", state["response"])
        
    except Exception as e:
        print(f"   ⚠️ Analysis failed: {e}")
        # Fallback defaults
        chart_type = "bar"
        data_structure = "categorical"
        new_response = state["response"]
    
    print(f"   Detected chart type: {chart_type}")
    print(f"   Data structure: {data_structure}")
    print(f"   New response: {new_response[:100]}...")
    
    # Update debug log
    debug_entry = f"[ANALYSIS] Chart: {chart_type}, Structure: {data_structure}"
    state["debug_log"].append(debug_entry)
    
    return {
        **state,
        "chart_type": chart_type,
        "data_structure": data_structure,
        "response": new_response,
    }

def data_handler_node(state: VisualizerState) -> VisualizerState:
    """
    Parse raw text and format for Chart.js.
    
    Uses pure Python functions for reliability.
    """
    print(f"\n🔧 DATA HANDLER NODE")
    
    # Parse based on intent
    if state["intent"] == "sql":
        parsed_data = parse_sql_results(state["response"])
        print(f"   Parsed {len(parsed_data.get('rows', []))} rows from SQL")
    else:  # rag
        parsed_data = parse_rag_results(state["response"])
        print(f"   Parsed {len(parsed_data.get('entities', []))} entities from RAG")
    
    # Format for Chart.js
    chart_data = format_for_chartjs(
        parsed_data, 
        state["chart_type"], 
        state["data_structure"]
    )
    
    if chart_data.get("datasets"):
        print(f"   Chart.js format: {len(chart_data['datasets'])} dataset(s)")
        if chart_data.get("labels"):
            preview = chart_data["labels"][:5]
            print(f"   Labels: {preview}{'...' if len(chart_data['labels']) > 5 else ''}")
    elif chart_data.get("error"):
        print(f"   ⚠️ Error: {chart_data['error']}")
    
    # Update debug log
    debug_entry = f"[DATA_HANDLER] Parsed: {parsed_data.get('row_count', parsed_data.get('count', 0))} items"
    state["debug_log"].append(debug_entry)
    
    return {
        **state,
        "parsed_data": parsed_data,
        "chart_data": chart_data
    }

def chart_builder_node(state: VisualizerState) -> VisualizerState:
    """
    Generate complete HTML with embedded Chart.js.
    
    Uses template-based generation for reliability.
    """
    print(f"\nðŸŽ¨ CHART BUILDER NODE")
    
    # Generate professional title using LLM
    title_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a data visualization expert. Create a concise, professional chart title.

Rules:
- Maximum 6-8 words
- Use title case (capitalize main words)
- Be descriptive but brief
- Focus on WHAT is being shown, not HOW
- No mentions of "chart", "graph", "visualization" in the title
- No verbs like "Show", "Display", "Visualize"

Examples:
Query: "Show me the top 10 customers by total spending as a bar chart"
Title: "Top 10 Customers by Total Spending"

Query: "Visualize film categories by number of rentals"
Title: "Film Categories by Rental Count"

Query: "Show monthly rental trends for 2024 as a line graph"
Title: "Monthly Rental Trends (2024)"

Respond with ONLY the title text, nothing else."""),
        ("user", f"Query: {state['user_input']}\nChart type: {state['chart_type']}")
    ])
    
    try:
        chain = title_prompt | app_config.reasoning_model
        title_result = chain.invoke({})
        title = title_result.content.strip().strip('"').strip("'")
        
        # Fallback if title is too long
        if len(title) > 60:
            title = title[:57] + "..."
    except Exception as e:
        print(f"   âš ï¸ Title generation failed: {e}")
        # Simple fallback
        title = "Data Visualization"
    
    print(f"   Chart type: {state['chart_type']}")
    print(f"   Title: {title}")
    
    # Generate HTML
    html_output = generate_chartjs_html(
        state["chart_data"],
        state["chart_type"],
        title
    )
    
    print(f"   HTML length: {len(html_output)} chars")
    print(f"   ✅ Chart ready for rendering")
    
    # Update debug log
    debug_entry = f"[CHART_BUILDER] Generated {len(html_output)} chars of HTML"
    state["debug_log"].append(debug_entry)
    
    # SAVE TO FILE
    file_path, file_url = save_html_to_file(html_output, state["user_input"])

    print(f"   📁 File path: {file_path}")
    print(f"   🌐 URL: {file_url}")

    return {
        **state,
        "html_output": html_output,
        "file_path": file_path,      
        "file_url": file_url          
    }


def save_html_to_file(html_content: str, user_query: str) -> tuple[str, str]:
    """Save HTML content to a file with timestamped filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Clean query for filename (first 30 chars, alphanumeric only)
    safe_query = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in user_query[:30])
    safe_query = safe_query.strip().replace(' ', '_')
    
    filename = f"viz_{timestamp}_{safe_query}.html"
    file_path = VISUALIZATIONS_DIR / filename
    
    # Save HTML to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"   ✅ Saved visualization to: {file_path.name}")
    
    # Generate relative URL for browser access
    relative_url = f"data/visualizations/{filename}"
    
    return str(file_path.absolute()), relative_url
    
# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

# Build the subgraph
visualizer_builder = StateGraph(VisualizerState)

# Add nodes
visualizer_builder.add_node("analysis", analysis_node)
visualizer_builder.add_node("data_handler", data_handler_node)
visualizer_builder.add_node("chart_builder", chart_builder_node)

# Linear flow
visualizer_builder.add_edge(START, "analysis")
visualizer_builder.add_edge("analysis", "data_handler")
visualizer_builder.add_edge("data_handler", "chart_builder")
visualizer_builder.add_edge("chart_builder", END)

# Compile
visualizer_workflow = visualizer_builder.compile()

