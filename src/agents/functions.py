# import re
# import sqlite3
# from pathlib import Path

# def convert_postgres_to_sqlite(sql: str) -> str:
#     """
#     Convert PostgreSQL-specific syntax to SQLite-compatible syntax.
#     """
    
#     # Remove SET statements and configuration commands
#     sql = re.sub(r'SELECT pg_catalog\.set_config.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
#     sql = re.sub(r'SET\s+\w+.*?;', '', sql, flags=re.IGNORECASE)
    
#     # Remove comments that are standalone (keep inline comments)
#     sql = re.sub(r'^--[^\n]*\n', '', sql, flags=re.MULTILINE)
    
#     # Remove ALL ALTER TABLE statements (more aggressive - do this early)
#     sql = re.sub(r'ALTER\s+TABLE\s+.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
    
#     # Remove other ALTER statements (schema, domain, type, etc.)
#     sql = re.sub(r'ALTER\s+SCHEMA.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
#     sql = re.sub(r'ALTER\s+DOMAIN.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
#     sql = re.sub(r'ALTER\s+TYPE.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
#     sql = re.sub(r'ALTER\s+FUNCTION.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
#     sql = re.sub(r'ALTER\s+AGGREGATE.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
    
#     # Remove CREATE DOMAIN
#     sql = re.sub(r'CREATE\s+DOMAIN.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
    
#     # Remove CREATE TYPE (ENUMs, composite types)
#     sql = re.sub(r'CREATE\s+TYPE.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
    
#     # Remove CREATE FUNCTION with ANY dollar-quote delimiter ($ or $_$ or $tag$)
#     # This catches functions with all dollar-quote variants
#     sql = re.sub(r'CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION.*?\$[^$]*\$;', '', sql, flags=re.IGNORECASE | re.DOTALL)
    
#     # Remove any remaining DECLARE...END blocks (orphaned function bodies)
#     sql = re.sub(r'\bDECLARE\b.*?\bEND\s*\$[^$]*\$;?', '', sql, flags=re.IGNORECASE | re.DOTALL)
    
#     # Remove CREATE AGGREGATE
#     sql = re.sub(r'CREATE\s+AGGREGATE.*?\);', '', sql, flags=re.IGNORECASE | re.DOTALL)
    
#     # Remove MATERIALIZED VIEWs
#     sql = re.sub(r'CREATE\s+MATERIALIZED\s+VIEW.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
    
#     # Remove sequence operations
#     sql = re.sub(r'DROP SEQUENCE.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
#     sql = re.sub(r'CREATE SEQUENCE.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
#     sql = re.sub(r'SELECT pg_catalog\.setval.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
    
#     # Remove table partitioning syntax
#     sql = re.sub(r'PARTITION BY RANGE.*?\)', ')', sql, flags=re.IGNORECASE | re.DOTALL)
#     sql = re.sub(r'PARTITION BY.*?\)', ')', sql, flags=re.IGNORECASE)
    
#     # Remove ACL/GRANT/REVOKE statements
#     sql = re.sub(r'REVOKE.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
#     sql = re.sub(r'GRANT.*?;', '', sql, flags=re.IGNORECASE | re.DOTALL)
    
#     # Remove PostgreSQL-specific triggers
#     sql = re.sub(r'CREATE\s+TRIGGER.*?EXECUTE\s+(?:FUNCTION|PROCEDURE).*?\);', '', sql, flags=re.IGNORECASE | re.DOTALL)
    
#     # Remove schema qualifiers
#     sql = re.sub(r'\bpublic\.', '', sql, flags=re.IGNORECASE)
    
#     # Remove DEFAULT nextval() calls
#     sql = re.sub(r"DEFAULT\s+nextval\(['\"][^'\"]*['\"]\s*::\s*regclass\)", '', sql, flags=re.IGNORECASE)
#     sql = re.sub(r"DEFAULT\s+nextval\(['\"][^'\"]*['\"]\)", '', sql, flags=re.IGNORECASE)
    
#     # Convert SERIAL types
#     sql = re.sub(r'(\w+)\s+SERIAL\s+PRIMARY KEY', r'\1 INTEGER PRIMARY KEY AUTOINCREMENT', sql, flags=re.IGNORECASE)
#     sql = re.sub(r'(\w+)\s+SERIAL\b', r'\1 INTEGER', sql, flags=re.IGNORECASE)
    
#     # Type conversions
#     type_mappings = {
#         r'\bTIMESTAMP\s+WITH\s+TIME\s+ZONE\b': 'TEXT',
#         r'\bTIMESTAMP\b': 'TEXT',
#         r'\bTIMESTAMPTZ\b': 'TEXT',
#         r'\bBYTEA\b': 'BLOB',
#         r'\bMONEY\b': 'REAL',
#         r'\bSMALLSERIAL\b': 'INTEGER',
#         r'\bBIGSERIAL\b': 'INTEGER',
#         r'\bTEXT\[\]': 'TEXT',
#         r'\bINTEGER\[\]': 'TEXT',
#         r'\bVARCHAR\[\]': 'TEXT',
#         r'\btsvector\b': 'TEXT',
#         r'\bregclass\b': 'TEXT',
#     }
    
#     for pg_type, sqlite_type in type_mappings.items():
#         sql = re.sub(pg_type, sqlite_type, sql, flags=re.IGNORECASE)
    
#     # Remove custom type references
#     sql = re.sub(r'\bmpaa_rating\b', 'TEXT', sql, flags=re.IGNORECASE)
#     sql = re.sub(r'\byear\b(?=\s*,|\s*\))', 'INTEGER', sql, flags=re.IGNORECASE)
    
#     # Remove ::type casts
#     sql = re.sub(r'::\w+', '', sql, flags=re.IGNORECASE)
    
#     # Remove ON UPDATE/DELETE clauses
#     sql = re.sub(r'\s+ON\s+UPDATE\s+CASCADE', '', sql, flags=re.IGNORECASE)
#     sql = re.sub(r'\s+ON\s+DELETE\s+RESTRICT', '', sql, flags=re.IGNORECASE)
    
#     # Convert time functions
#     sql = re.sub(r'\bNOW\(\)', "datetime('now')", sql, flags=re.IGNORECASE)
#     sql = re.sub(r'\bCURRENT_TIMESTAMP\b', "datetime('now')", sql, flags=re.IGNORECASE)
#     sql = re.sub(r'\bCURRENT_DATE\b', "date('now')", sql, flags=re.IGNORECASE)
    
#     # Remove RETURNING clauses
#     sql = re.sub(r'\s+RETURNING\s+\*;', ';', sql, flags=re.IGNORECASE)
    
#     # Remove CONCURRENTLY
#     sql = re.sub(r'\bCONCURRENTLY\b', '', sql, flags=re.IGNORECASE)
    
#     # Remove USING index_method from CREATE INDEX
#     sql = re.sub(r'\s+USING\s+(?:btree|gist|hash|gin|spgist|brin)\s*\(', ' (', sql, flags=re.IGNORECASE)
    
#     # Clean up whitespace
#     sql = re.sub(r'\n\s*\n+', '\n\n', sql)
    
#     return sql


# def test_conversion_step_by_step(schema_path: Path):
#     """Test the conversion and identify problematic statements."""
    
#     print("="*70)
#     print("TESTING POSTGRESQL TO SQLITE CONVERSION")
#     print("="*70)
    
#     # Read schema
#     with open(schema_path, 'r', encoding='utf-8') as f:
#         original_sql = f.read()
    
#     print(f"\n✓ Read schema file: {len(original_sql)} characters")
    
#     # Convert
#     converted_sql = convert_postgres_to_sqlite(original_sql)
#     print(f"✓ Converted schema: {len(converted_sql)} characters")
    
#     # Save converted version
#     debug_path = schema_path.parent / "converted_schema.sql"
#     with open(debug_path, 'w', encoding='utf-8') as f:
#         f.write(converted_sql)
#     print(f"✓ Saved to: {debug_path}")
    
#     # Try to execute statement by statement
#     print("\n" + "="*70)
#     print("ATTEMPTING TO EXECUTE STATEMENTS")
#     print("="*70)
    
#     # Create in-memory database for testing
#     conn = sqlite3.connect(':memory:')
#     cursor = conn.cursor()
    
#     # Split into statements (simple split by semicolon)
#     statements = [s.strip() for s in converted_sql.split(';') if s.strip()]
    
#     print(f"\nTotal statements to execute: {len(statements)}")
    
#     successful = 0
#     failed = 0
    
#     for i, stmt in enumerate(statements, 1):
#         # Skip comments and empty statements
#         if stmt.startswith('--') or not stmt.strip():
#             continue
            
#         try:
#             cursor.execute(stmt)
#             successful += 1
            
#             # Show CREATE TABLE statements that succeed
#             if 'CREATE TABLE' in stmt.upper():
#                 table_match = re.search(r'CREATE TABLE\s+(\w+)', stmt, re.IGNORECASE)
#                 if table_match:
#                     print(f"  ✓ Statement {i}: Created table '{table_match.group(1)}'")
#         except sqlite3.Error as e:
#             failed += 1
#             print(f"\n  ✗ Statement {i} FAILED:")
#             print(f"     Error: {e}")
#             print(f"     Statement preview: {stmt[:200]}...")
            
#             # Stop after first few errors to avoid spam
#             if failed >= 5:
#                 print("\n  [Stopping after 5 errors for readability]")
#                 break
    
#     print(f"\n{'='*70}")
#     print(f"RESULTS: {successful} successful, {failed} failed")
#     print(f"{'='*70}")
    
#     # Show tables created
#     cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
#     tables = cursor.fetchall()
#     if tables:
#         print(f"\nTables created: {len(tables)}")
#         for table in tables:
#             print(f"  • {table[0]}")
    
#     conn.close()


# if __name__ == "__main__":
#     # Update this path to your actual location
#     schema_path = Path("C:/Users/Hp/anaconda3/envs/capstone-project/data/pagila/pagila-schema.sql")
    
#     if not schema_path.exists():
#         print(f"❌ Schema file not found: {schema_path}")
#     else:
#         test_conversion_step_by_step(schema_path)


import sqlite3
import csv
from pathlib import Path
from typing import Optional

# Clean SQLite schema for Pagila database
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
    district TEXT NOT NULL,
    city_id INTEGER NOT NULL,
    postal_code TEXT,
    phone TEXT NOT NULL,
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
    active INTEGER DEFAULT 1,
    create_date TEXT DEFAULT (date('now')),
    last_update TEXT DEFAULT (datetime('now')),
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


def initialize_database() -> sqlite3.Connection:
    """
    Initialize Pagila SQLite database.
    
    Strategy:
    1. Check if database exists (cached)
    2. If not, create schema
    3. Import data from CSVs if available
    4. Return connection
    """
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "pagila" / "pagila.db"
    csv_dir = project_root / "data" / "pagila" / "csv"
    
    # Check if database already exists
    if db_path.exists():
        print(f"✓ Database already exists at {db_path}")
        return sqlite3.connect(str(db_path))
    
    print(f"⚙️ Initializing new database at {db_path}")
    
    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create database with schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        print("📋 Creating tables...")
        cursor.executescript(PAGILA_SQLITE_SCHEMA)
        conn.commit()
        print("✓ Schema created successfully")
        
        # Import data from CSVs if available
        if csv_dir.exists():
            print(f"📥 Importing data from {csv_dir}...")
            import_csv_data(conn, csv_dir)
        else:
            print(f"⚠️ No CSV data found at {csv_dir}")
            print(f"   Database created with empty tables")
            print(f"   To import data:")
            print(f"   1. Place CSV files in {csv_dir}")
            print(f"   2. Run: python -c 'from sql_agent import import_csv_data; import_csv_data(conn, \"{csv_dir}\")'")
        
        # Verify tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        print(f"✓ Database initialized with {len(tables)} tables")
        
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
    """
    cursor = conn.cursor()
    
    # Define import order (respects foreign key dependencies)
    table_order = [
        'country', 'city', 'address', 'language', 'category', 'actor',
        'film', 'film_actor', 'film_category', 'store', 'staff',
        'customer', 'inventory', 'rental', 'payment'
    ]
    
    imported_count = 0
    
    for table_name in table_order:
        csv_path = csv_dir / f"{table_name}.csv"
        
        if not csv_path.exists():
            print(f"  ⚠️ Skipping {table_name} (CSV not found)")
            continue
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                headers = next(csv_reader)  # First row is headers
                
                # Build INSERT statement
                placeholders = ','.join(['?' for _ in headers])
                insert_sql = f"INSERT INTO {table_name} ({','.join(headers)}) VALUES ({placeholders})"
                
                # Import rows
                rows = list(csv_reader)
                cursor.executemany(insert_sql, rows)
                conn.commit()
                
                print(f"  ✓ Imported {len(rows)} rows into {table_name}")
                imported_count += 1
                
        except Exception as e:
            print(f"  ✗ Error importing {table_name}: {e}")
            conn.rollback()
    
    print(f"✓ Successfully imported {imported_count} tables")


def export_postgres_to_csv(pg_conn_string: str, output_dir: Path) -> None:
    """
    Helper function to export PostgreSQL Pagila data to CSV files.
    
    Usage:
        export_postgres_to_csv(
            "postgresql://user:password@localhost/pagila",
            Path("data/pagila/csv")
        )
    """
    import psycopg2
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    tables = [
        'actor', 'category', 'country', 'city', 'address', 'language',
        'film', 'film_actor', 'film_category', 'store', 'staff',
        'customer', 'inventory', 'rental', 'payment'
    ]
    
    conn = psycopg2.connect(pg_conn_string)
    cursor = conn.cursor()
    
    for table in tables:
        csv_path = output_dir / f"{table}.csv"
        
        # Get column names
        cursor.execute(f"SELECT * FROM {table} LIMIT 0")
        columns = [desc[0] for desc in cursor.description]
        
        # Export data
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)  # Headers
            
            cursor.execute(f"SELECT * FROM {table}")
            writer.writerows(cursor.fetchall())
        
        print(f"✓ Exported {table} to {csv_path}")
    
    conn.close()
    print(f"✓ All tables exported to {output_dir}")


# Test the initialization
if __name__ == "__main__":
    try:
        conn = initialize_database()
        cursor = conn.cursor()
        
        # Show table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        print("\n" + "="*50)
        print("DATABASE STATUS")
        print("="*50)
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  {table[0]}: {count} rows")
        
        conn.close()
        print("\n✅ Database ready!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise