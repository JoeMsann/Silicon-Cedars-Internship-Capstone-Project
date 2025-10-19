"""
SQL Agent for Pagila Database Queries
Provides secure, read-only access to the Pagila SQLite database.
Thread-safe implementation for use with LangGraph and async frameworks.
"""

import sqlite3
import csv
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool

from src.config import app_config
from src.prompts import SQL_AGENT_PROMPT


# ============================================================================
# DATABASE SCHEMA DEFINITION
# ============================================================================

PAGILA_SQLITE_SCHEMA = """
-- Pagila DVD Rental Database - SQLite Version

CREATE TABLE actor (
    actor_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    last_update TEXT DEFAULT (datetime('now'))
);

CREATE TABLE category (
    category_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    last_update TEXT DEFAULT (datetime('now'))
);

CREATE TABLE country (
    country_id INTEGER PRIMARY KEY,
    country TEXT NOT NULL,
    last_update TEXT DEFAULT (datetime('now'))
);

CREATE TABLE city (
    city_id INTEGER PRIMARY KEY,
    city TEXT NOT NULL,
    country_id INTEGER NOT NULL,
    last_update TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (country_id) REFERENCES country(country_id)
);

CREATE TABLE address (
    address_id INTEGER PRIMARY KEY,
    address TEXT NOT NULL,
    address2 TEXT,
    district TEXT,  -- Allow NULL since CSV has empty values
    city_id INTEGER NOT NULL,
    postal_code TEXT,
    phone TEXT,  -- Allow NULL since CSV has empty values
    last_update TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (city_id) REFERENCES city(city_id)
);

CREATE TABLE language (
    language_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    last_update TEXT DEFAULT (datetime('now'))
);

CREATE TABLE film (
    film_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    release_year INTEGER,
    language_id INTEGER NOT NULL,
    original_language_id INTEGER,
    rental_duration INTEGER DEFAULT 3,
    rental_rate REAL DEFAULT 4.99,
    length INTEGER,
    replacement_cost REAL DEFAULT 19.99,
    rating TEXT DEFAULT 'G',
    last_update TEXT DEFAULT (datetime('now')),
    special_features TEXT,
    fulltext TEXT,  -- Keep this column to match CSV
    FOREIGN KEY (language_id) REFERENCES language(language_id)
);

CREATE TABLE film_actor (
    actor_id INTEGER NOT NULL,
    film_id INTEGER NOT NULL,
    last_update TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (actor_id, film_id),
    FOREIGN KEY (actor_id) REFERENCES actor(actor_id),
    FOREIGN KEY (film_id) REFERENCES film(film_id)
);

CREATE TABLE film_category (
    film_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    last_update TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (film_id, category_id),
    FOREIGN KEY (film_id) REFERENCES film(film_id),
    FOREIGN KEY (category_id) REFERENCES category(category_id)
);

CREATE TABLE store (
    store_id INTEGER PRIMARY KEY,
    manager_staff_id INTEGER NOT NULL,
    address_id INTEGER NOT NULL,
    last_update TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (address_id) REFERENCES address(address_id)
);

CREATE TABLE staff (
    staff_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    address_id INTEGER NOT NULL,
    email TEXT,
    store_id INTEGER NOT NULL,
    active INTEGER DEFAULT 1,
    username TEXT NOT NULL,
    password TEXT,
    last_update TEXT DEFAULT (datetime('now')),
    picture BLOB,
    FOREIGN KEY (address_id) REFERENCES address(address_id),
    FOREIGN KEY (store_id) REFERENCES store(store_id)
);

CREATE TABLE customer (
    customer_id INTEGER PRIMARY KEY,
    store_id INTEGER NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT,
    address_id INTEGER NOT NULL,
    activebool INTEGER,  -- Keep original column name from CSV
    create_date TEXT DEFAULT (date('now')),
    last_update TEXT DEFAULT (datetime('now')),
    active INTEGER,  -- Additional active column exists in CSV
    FOREIGN KEY (address_id) REFERENCES address(address_id),
    FOREIGN KEY (store_id) REFERENCES store(store_id)
);

CREATE TABLE inventory (
    inventory_id INTEGER PRIMARY KEY,
    film_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    last_update TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (film_id) REFERENCES film(film_id),
    FOREIGN KEY (store_id) REFERENCES store(store_id)
);

CREATE TABLE rental (
    rental_id INTEGER PRIMARY KEY,
    rental_date TEXT NOT NULL,
    inventory_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    return_date TEXT,
    staff_id INTEGER NOT NULL,
    last_update TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY (staff_id) REFERENCES staff(staff_id)
);

CREATE TABLE payment (
    payment_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    staff_id INTEGER NOT NULL,
    rental_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    payment_date TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY (staff_id) REFERENCES staff(staff_id),
    FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
);

-- Indexes for performance
CREATE INDEX idx_actor_last_name ON actor(last_name);
CREATE INDEX idx_film_title ON film(title);
CREATE INDEX idx_customer_last_name ON customer(last_name);
CREATE INDEX idx_rental_date ON rental(rental_date);
CREATE INDEX idx_payment_date ON payment(payment_date);
"""


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def initialize_database() -> sqlite3.Connection:
    """
    Initialize Pagila SQLite database.
    
    Steps:
    1. Check if database exists (cached)
    2. If not, create schema
    3. Import data from CSVs if available
    4. Return connection
    
    Returns:
        sqlite3.Connection: Active database connection
    """
    # Get project root - go up from src/agents/ to project root
    project_root = Path(__file__).parent.parent.parent  # sql_agent.py -> agents -> src -> project
    
    # Use absolute path resolution to avoid issues
    db_path = project_root / "data" / "pagila" / "pagila.db"
    csv_dir = project_root / "data" / "pagila" / "csv"
    
    print(f"📁 Project root: {project_root.absolute()}")
    print(f"📁 Looking for CSVs at: {csv_dir.absolute()}")
    print(f"📁 Database will be at: {db_path.absolute()}")
    
    # Check if database already exists
    if db_path.exists():
        print(f"✅ Database already exists at {db_path}")
        
        # Check if it has data
        temp_conn = sqlite3.connect(str(db_path), check_same_thread=False)
        cursor = temp_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM customer")
        row_count = cursor.fetchone()[0]
        temp_conn.close()
        
        if row_count == 0:
            print("⚠️  Database exists but is EMPTY!")
            print("   Deleting and recreating with data...")
            db_path.unlink()  # Delete empty database
        else:
            return sqlite3.connect(str(db_path), check_same_thread=False)
    
    print(f"⚙️  Initializing new database at {db_path}")
    
    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create database with schema (thread-safe connection)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        print("📋 Creating tables...")
        cursor.executescript(PAGILA_SQLITE_SCHEMA)
        conn.commit()
        print("✅ Schema created successfully")
        
        # Import data from CSVs if available
        if csv_dir.exists():
            csv_files = list(csv_dir.glob("*.csv"))
            if csv_files:
                print(f"📥 Importing data from {csv_dir}...")
                print(f"   Found {len(csv_files)} CSV files")
                import_csv_data(conn, csv_dir)
            else:
                print(f"⚠️  CSV directory exists but contains no .csv files!")
                print(f"   Location: {csv_dir.absolute()}")
                print(f"\n   To populate the database:")
                print(f"   1. Run: python export_pagila_to_csv.py")
                print(f"   2. CSV files should be saved to: {csv_dir}")
        else:
            print(f"⚠️  CSV directory does not exist!")
            print(f"   Expected location: {csv_dir.absolute()}")
            print(f"\n   To populate the database:")
            print(f"   1. Create directory: mkdir -p {csv_dir}")
            print(f"   2. Run: python export_pagila_to_csv.py")
            print(f"   3. Delete pagila.db and re-run this script")
        
        # Verify tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        print(f"✅ Database initialized with {len(tables)} tables")
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        conn.close()
        if db_path.exists():
            db_path.unlink()
        raise
    
    return conn


def import_csv_data(conn: sqlite3.Connection, csv_dir: Path) -> None:
    """
    Import data from CSV files into database tables.
    
    Expected CSV file names match table names: actor.csv, customer.csv, etc.
    CSVs should have headers in the first row.
    """
    cursor = conn.cursor()
    
    # Temporarily disable foreign key constraints during import
    cursor.execute("PRAGMA foreign_keys = OFF")
    
    # Define import order (respects foreign key dependencies)
    table_order = [
        'country', 'city', 'address', 'language', 'category', 'actor',
        'film', 'film_actor', 'film_category', 'store', 'staff',
        'customer', 'inventory', 'rental', 'payment'
    ]
    
    imported_count = 0
    total_rows = 0
    failed_tables = []
    
    for table_name in table_order:
        csv_path = csv_dir / f"{table_name}.csv"
        
        if not csv_path.exists():
            print(f"  ⚠️  Skipping {table_name} (CSV not found)")
            continue
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                headers = next(csv_reader)  # First row is headers
                
                # Clean headers (remove BOM, whitespace, quotes)
                headers = [h.strip().strip('\ufeff').strip('"').strip("'") for h in headers]
                
                # Build INSERT statement with explicit column names
                placeholders = ','.join(['?' for _ in headers])
                insert_sql = f"INSERT INTO {table_name} ({','.join(headers)}) VALUES ({placeholders})"
                
                # Import rows with better error handling
                rows = []
                line_num = 1  # Start at 1 (after header)
                
                for row in csv_reader:
                    line_num += 1
                    try:
                        # Clean row data
                        cleaned_row = []
                        for val in row:
                            # Handle empty strings as NULL for numeric fields
                            if val.strip() == '':
                                cleaned_row.append(None)
                            else:
                                cleaned_row.append(val.strip())
                        rows.append(cleaned_row)
                    except Exception as e:
                        print(f"      Warning: Error on line {line_num}: {e}")
                        continue
                
                if rows:
                    cursor.executemany(insert_sql, rows)
                    conn.commit()
                    
                    print(f"  ✅ Imported {len(rows):6d} rows into {table_name}")
                    imported_count += 1
                    total_rows += len(rows)
                else:
                    print(f"  ⚠️  No valid data found in {table_name}.csv")
                    failed_tables.append(table_name)
                
        except Exception as e:
            print(f"  ✗ Error importing {table_name}: {e}")
            print(f"     CSV path: {csv_path}")
            print(f"     First few rows for debugging:")
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if i < 3:  # Show first 3 lines
                            print(f"       Line {i}: {line[:100]}")
                        else:
                            break
            except:
                pass
            conn.rollback()
            failed_tables.append(table_name)
    
    # Re-enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON")
    
    print(f"✅ Successfully imported {imported_count} tables ({total_rows:,} total rows)")
    
    if failed_tables:
        print(f"\n⚠️  Failed to import {len(failed_tables)} tables: {', '.join(failed_tables)}")
        print(f"   Check the CSV files for formatting issues")


# ============================================================================
# SQL QUERY VALIDATION
# ============================================================================

def validate_user_input(user_query: str) -> Tuple[bool, str]:
    """
    Validate user input for suspicious patterns before sending to LLM.
    
    This is the FIRST line of defense - checks the natural language query
    for injection attempts and malicious patterns.
    
    Args:
        user_query: Natural language query from user
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    query_lower = user_query.lower()
    
    # Check for SQL comment syntax in user input
    if '--' in user_query or '/*' in user_query or '*/' in user_query:
        return False, "Your query contains SQL comment syntax which is not allowed. Please rephrase without using '--' or '/* */' characters."
    
    # Check for semicolons (multiple statements)
    if ';' in user_query:
        return False, "Your query contains semicolons which could indicate multiple statements. Please ask one question at a time."
    
    # Check for explicit write operation requests
    write_keywords = [
        'insert', 'update', 'delete', 'drop', 'create', 'alter',
        'truncate', 'modify', 'remove', 'add', 'change', 'erase'
    ]
    
    for keyword in write_keywords:
        # Use word boundaries to avoid false positives
        import re
        if re.search(rf'\b{keyword}\b', query_lower):
            return False, f"I can only retrieve data (SELECT queries). I cannot {keyword.upper()} data. If you need to modify the database, please contact your database administrator."
    
    return True, ""


def validate_sql_query(query: str) -> Tuple[bool, str]:
    """
    Validate SQL query for security and safety.
    
    Multi-layer validation:
    1. Injection protection first (highest priority)
    2. Whitelist: Must be a SELECT query
    3. Blacklist: No write operations (word boundary detection)
    
    Args:
        query: SQL query string to validate
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    import re
    
    query_stripped = query.strip()
    query_upper = query_stripped.upper()
    
    # Layer 1: Injection protection - Check FIRST before any other validation
    # This catches attempts to hide malicious code in "comments"
    if '--' in query or '/*' in query or '*/' in query:
        return False, "SQL comments are not allowed for security reasons."
    
    # Layer 2: Multiple statements check
    # Allow semicolon only at the very end
    query_no_trailing_semi = query_stripped.rstrip(';')
    if ';' in query_no_trailing_semi:
        return False, "Multiple statements are not allowed. Only single SELECT queries."
    
    # Layer 3: Whitelist - Must start with SELECT
    if not query_upper.startswith('SELECT'):
        return False, "Only SELECT queries are allowed. Cannot execute write operations."
    
    # Layer 4: Blacklist - No write operations (with word boundary detection)
    # Use regex to match whole words only, avoiding false positives like "last_update"
    forbidden_patterns = [
        r'\bINSERT\b', r'\bUPDATE\b', r'\bDELETE\b', 
        r'\bDROP\b', r'\bCREATE\b', r'\bALTER\b',
        r'\bTRUNCATE\b', r'\bGRANT\b', r'\bREVOKE\b', 
        r'\bEXEC\b', r'\bEXECUTE\b'
    ]
    
    for pattern in forbidden_patterns:
        if re.search(pattern, query_upper):
            # Extract just the keyword for error message
            keyword = pattern.strip(r'\b')
            return False, f"Forbidden operation detected: {keyword}. Only SELECT queries are allowed."
    
    return True, ""


# ============================================================================
# THREAD-SAFE CONNECTION FACTORY
# ============================================================================

def create_db_connection() -> sqlite3.Connection:
    """
    Create a fresh thread-safe database connection.
    
    This function creates a new connection for each operation, avoiding
    SQLite's "objects created in a thread can only be used in that same thread" error.
    
    Returns:
        sqlite3.Connection: New database connection with thread-safety enabled
    """
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "pagila" / "pagila.db"
    
    # Create connection with thread-safety and timeout
    conn = sqlite3.connect(
        str(db_path),
        check_same_thread=False,  # CRITICAL: Allow cross-thread usage
        timeout=10.0  # 10 second timeout for busy database
    )
    
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    
    return conn


# ============================================================================
# LANGCHAIN TOOLS - THREAD-SAFE VERSIONS
# ============================================================================

@tool
def get_database_schema() -> str:
    """
    Get the database schema including all table names, columns, and types.
    Use this tool to understand the database structure before writing queries.
    """
    # Create fresh connection for this operation
    conn = create_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        schema_info = ["=== PAGILA DATABASE SCHEMA ===\n"]
        
        for (table_name,) in tables:
            # Get columns for this table
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            schema_info.append(f"\nTable: {table_name}")
            schema_info.append("-" * 50)
            
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, is_pk = col
                
                # Build column description
                col_desc = f"  {col_name}: {col_type}"
                if is_pk:
                    col_desc += " (PRIMARY KEY)"
                if not_null:
                    col_desc += " NOT NULL"
                if default_val:
                    col_desc += f" DEFAULT {default_val}"
                
                schema_info.append(col_desc)
        
        return "\n".join(schema_info)
    
    finally:
        # Always close the connection when done
        conn.close()


@tool
def execute_sql_query(query: str) -> str:
    """
    Execute a SELECT query against the Pagila database.
    
    SECURITY CONSTRAINTS:
    - Only SELECT queries are allowed
    - No INSERT, UPDATE, DELETE, DROP, or other write operations
    - No multiple statements
    - No SQL comments
    
    Args:
        query: A valid SELECT SQL query
        
    Returns:
        Query results formatted as a readable table or error message
    """
    # Validate query
    is_valid, error_msg = validate_sql_query(query)
    if not is_valid:
        return f"❌ QUERY REJECTED: {error_msg}"
    
    # Create fresh connection for this operation
    conn = create_db_connection()
    cursor = conn.cursor()
    
    try:
        # Execute query
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        # Format results
        if not results:
            return "Query executed successfully but returned no results."
        
        # Build table
        output = []
        output.append("\n" + "=" * 80)
        output.append("QUERY RESULTS")
        output.append("=" * 80)
        
        # Header
        header = " | ".join(column_names)
        output.append(header)
        output.append("-" * len(header))
        
        # Rows (limit to 100 for readability)
        for i, row in enumerate(results[:100]):
            row_str = " | ".join(str(val) if val is not None else "NULL" for val in row)
            output.append(row_str)
        
        if len(results) > 100:
            output.append(f"\n... ({len(results) - 100} more rows)")
        
        output.append(f"\nTotal rows: {len(results)}")
        output.append("=" * 80)
        
        return "\n".join(output)
        
    except sqlite3.Error as e:
        return f"❌ SQL ERROR: {str(e)}\n\nPlease check your query syntax and try again."
    except Exception as e:
        return f"❌ UNEXPECTED ERROR: {str(e)}"
    
    finally:
        # Always close the connection when done
        conn.close()


# ============================================================================
# AGENT CREATION
# ============================================================================

def create_sql_agent() -> AgentExecutor:
    """
    Create the SQL agent with schema inspection and query execution tools.
    
    Returns:
        AgentExecutor: Configured agent ready to handle SQL queries
    """
    # Ensure database is initialized (uses thread-safe connection)
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "pagila" / "pagila.db"
    
    if not db_path.exists():
        print("⚙️  Database not found. Initializing...")
        initialize_database()
    
    # Create tools
    tools = [get_database_schema, execute_sql_query]
    
    # Create a wrapper around the model that disables native tool calling
    # This forces ReAct to use text-based tool invocation which works with Groq
    llm = app_config.sql_model
    
    # ReAct prompt template with all required variables
    react_prompt = PromptTemplate.from_template(
        """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format EXACTLY:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

IMPORTANT: 
- Always start with "Thought:" 
- Use "Action:" followed by EXACTLY one of the tool names
- Use "Action Input:" for the tool's input
- After seeing an "Observation:", continue with another "Thought:"

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
    )
    
    # Create the agent - ReAct will handle tool calling via text parsing
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=react_prompt,
    )
    
    # Create executor with better error handling
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True,
        return_intermediate_steps=False,
        max_execution_time=60,  # 60 second timeout
    )
    
    return agent_executor


"""
Partial update for sql_agent.py - query_sql_agent() function
This fixes the issue where clarification questions are incorrectly validated as SQL
"""

def query_sql_agent(user_query: str) -> str:
    """
    High-level interface for querying the SQL agent.
    Custom implementation for Groq models that don't support native tool calling.
    
    Args:
        user_query: Natural language query from user
        
    Returns:
        Agent's response with query results
    """
    from langchain_core.prompts import ChatPromptTemplate
    
    print(f"\n{'='*80}")
    print(f"SQL AGENT PROCESSING: {user_query}")
    print(f"{'='*80}\n")
    
    try:
        # Step 0: Validate user input BEFORE sending to LLM
        print("Step 0: Validating user input for security...")
        is_valid_input, input_error = validate_user_input(user_query)
        if not is_valid_input:
            print(f"❌ User input rejected: {input_error}\n")
            return f"❌ SECURITY CHECK FAILED: {input_error}"
        print("✅ User input passed security checks\n")
        
        # Step 1: Get database schema (uses its own thread-safe connection)
        print("Step 1: Fetching database schema...")
        schema = get_database_schema.invoke({})
        print(f"✅ Schema retrieved ({len(schema)} characters)\n")
        
        # Step 2: Generate SQL query using LLM
        print("Step 2: Generating SQL query...")
        sql_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""{SQL_AGENT_PROMPT}

Database Schema:
{schema}

**CRITICAL: This is a SQLite database, NOT PostgreSQL.**

SQLite-Specific Syntax Rules:
- Date functions: Use strftime('%Y-%m', rental_date) for month grouping
- No DATE_TRUNC: Use strftime() instead
- No :: casting: Use CAST(column AS type) or strftime() for dates
- Date comparisons: Use DATE(column) or strftime()
- Text dates: Dates stored as TEXT, use DATE() function to extract date part

Example SQLite date queries:
- Monthly grouping: SELECT strftime('%Y-%m', rental_date) AS month, COUNT(*) FROM rental GROUP BY month
- Date filtering: WHERE DATE(rental_date) >= '2024-01-01'
- Year extraction: WHERE strftime('%Y', rental_date) = '2024'

Generate a SQL query to answer the user's question using SQLite syntax.

IMPORTANT: If the user's question is unclear or you need clarification about which columns to use, 
respond with "CLARIFICATION_NEEDED: " followed by your question for the user.
Do NOT generate SQL if you're uncertain about the schema mapping.

Return ONLY the SQL query with no explanations, markdown, or additional text.
OR return "CLARIFICATION_NEEDED: your question" if clarification is needed."""),
            ("user", user_query)
        ])
        
        chain = sql_prompt | app_config.sql_model
        response = chain.invoke({})
        sql_query = response.content.strip()
        
        # Check if LLM is asking for clarification
        if sql_query.startswith("CLARIFICATION_NEEDED:"):
            clarification = sql_query.replace("CLARIFICATION_NEEDED:", "").strip()
            print(f"ℹ️  Clarification needed: {clarification}\n")
            return f"I need some clarification to answer your question:\n\n{clarification}"
        
        # Clean up SQL (remove markdown if present)
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        
        # Check if the response looks like SQL at all
        sql_query_upper = sql_query.upper().strip()
        if not sql_query_upper.startswith("SELECT"):
            # LLM returned a clarification or explanation instead of SQL
            print(f"ℹ️  LLM response is not SQL: {sql_query[:100]}\n")
            return f"I need some clarification about your query:\n\n{sql_query}"
        
        # Remove SQL comments from LLM-generated query (for security validation)
        # Keep the original for display, but validate the cleaned version
        sql_query_for_display = sql_query
        
        # Remove single-line comments (-- ...)
        sql_query_lines = sql_query.split('\n')
        sql_query_no_comments = []
        for line in sql_query_lines:
            # Remove everything after -- on each line
            if '--' in line:
                line = line.split('--')[0]
            # Keep non-empty lines
            if line.strip():
                sql_query_no_comments.append(line.strip())
        sql_query_clean = ' '.join(sql_query_no_comments)
        
        # Remove multi-line comments (/* ... */)
        import re
        sql_query_clean = re.sub(r'/\*.*?\*/', '', sql_query_clean, flags=re.DOTALL)
        
        print(f"✅ Generated SQL:\n{sql_query_for_display}\n")
        if sql_query_clean != sql_query:
            print(f"🔍 SQL after comment removal (for validation):\n{sql_query_clean}\n")
        
        # Step 3: Validate and execute the cleaned query
        print("Step 3: Validating and executing query...")
        result = execute_sql_query.invoke({"query": sql_query_clean})
        print(f"✅ Query executed\n")
        
        # Step 4: Format final response (show original with comments for readability)
        final_response = f"""Query: {user_query}

Generated SQL:
{sql_query_for_display}

{result}"""
        
        return final_response
        
    except Exception as e:
        error_msg = str(e)
        print(f"⚠️  Error: {error_msg}\n")
        return f"❌ Agent Error: {error_msg}"
    
# ============================================================================
# SQL NODE FOR LANGGRAPH WORKFLOW
# ============================================================================

def sql_node(state):
    """
    SQL node for LangGraph workflow.
    
    Args:
        state: Graph state containing user_input and other workflow data
        
    Returns:
        Updated state with SQL response
    """
    user_input = state.get("user_input", "")
    
    if not user_input:
        return {
            **state,
            "response": "No SQL query provided."
        }
    
    try:
        # Query the SQL agent
        result = query_sql_agent(user_input)
        
        return {
            **state,
            "response": result
        }
        
    except Exception as e:
        error_msg = f"SQL Agent Error: {str(e)}"
        print(error_msg)
        
        return {
            **state,
            "response": error_msg,
            "error": error_msg
        }


