"""
Export Pagila PostgreSQL database to CSV files.

Requirements:
    pip install psycopg2-binary

Usage:
    python export_pagila_to_csv.py
"""

import psycopg2
import csv
from pathlib import Path

def export_pagila_to_csv(
    output_dir: Path = Path("data/pagila/csv"),
    host: str = "localhost",
    database: str = "pagila",
    user: str = "postgres",
    password: str = None
):
    """
    Export all Pagila tables to CSV files.
    
    Args:
        output_dir: Where to save CSV files
        host: PostgreSQL host
        database: Database name (default: pagila)
        user: PostgreSQL username
        password: PostgreSQL password (will prompt if None)
    """
    
    # Prompt for password if not provided
    if password is None:
        import getpass
        password = getpass.getpass(f"PostgreSQL password for user '{user}': ")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🔗 Connecting to PostgreSQL at {host}/{database}...")
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        
        print("✓ Connected successfully")
        
        # Tables to export (in dependency order)
        tables = [
            'country',
            'city', 
            'address',
            'language',
            'category',
            'actor',
            'film',
            'film_actor',
            'film_category',
            'store',
            'staff',
            'customer',
            'inventory',
            'rental',
            'payment'
        ]
        
        print(f"\n📤 Exporting {len(tables)} tables to {output_dir}...\n")
        
        total_rows = 0
        
        for table in tables:
            csv_path = output_dir / f"{table}.csv"
            
            try:
                # Get column names
                cursor.execute(f"SELECT * FROM {table} LIMIT 0")
                columns = [desc[0] for desc in cursor.description]
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]
                
                # Export data
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Write headers
                    writer.writerow(columns)
                    
                    # Write data
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()
                    writer.writerows(rows)
                
                total_rows += row_count
                print(f"  ✓ {table:20s} → {row_count:6d} rows")
                
            except Exception as e:
                print(f"  ✗ {table:20s} → Error: {e}")
        
        cursor.close()
        conn.close()
        
        print(f"\n{'='*60}")
        print(f"✅ SUCCESS! Exported {len(tables)} tables ({total_rows:,} total rows)")
        print(f"📁 Files saved to: {output_dir.absolute()}")
        print(f"{'='*60}")
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Is PostgreSQL running? Check with: pg_ctl status")
        print("  2. Does the 'pagila' database exist? Check with: psql -U postgres -c '\\l'")
        print("  3. Is the password correct?")
        print("  4. Try: psql -U postgres -d pagila")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


def verify_csv_files(csv_dir: Path = Path("data/pagila/csv")):
    """Verify that CSV files were created correctly."""
    
    if not csv_dir.exists():
        print(f"❌ Directory not found: {csv_dir}")
        return False
    
    csv_files = list(csv_dir.glob("*.csv"))
    
    if not csv_files:
        print(f"❌ No CSV files found in {csv_dir}")
        return False
    
    print(f"\n📋 CSV Files Summary:")
    print(f"{'='*60}")
    
    total_rows = 0
    
    for csv_file in sorted(csv_files):
        with open(csv_file, 'r', encoding='utf-8') as f:
            row_count = sum(1 for _ in f) - 1  # Subtract header row
            total_rows += row_count
            print(f"  {csv_file.stem:20s} → {row_count:6d} rows")
    
    print(f"{'='*60}")
    print(f"Total: {len(csv_files)} files, {total_rows:,} rows")
    
    return True


if __name__ == "__main__":
    print("="*60)
    print("PAGILA POSTGRESQL → CSV EXPORTER")
    print("="*60)
    print()
    
    # Configuration
    config = {
        'output_dir': Path("data/pagila/csv"),
        'host': 'localhost',
        'database': 'pagila',
        'user': 'postgres',
        'password': None  # Will prompt
    }
    
    # Allow user to customize
    print("Press Enter to use defaults, or type custom values:")
    
    user_input = input(f"  Database name [{config['database']}]: ").strip()
    if user_input:
        config['database'] = user_input
    
    user_input = input(f"  PostgreSQL user [{config['user']}]: ").strip()
    if user_input:
        config['user'] = user_input
    
    user_input = input(f"  Output directory [{config['output_dir']}]: ").strip()
    if user_input:
        config['output_dir'] = Path(user_input)
    
    print()
    
    # Export
    success = export_pagila_to_csv(**config)
    
    if success:
        print("\n" + "="*60)
        print("NEXT STEPS:")
        print("="*60)
        print("1. Run your SQL agent initialization:")
        print("   python src/agents/sql_agent.py")
        print()
        print("2. The database will automatically import these CSV files")
        print("   and create pagila.db")
        print("="*60)
        
        # Verify
        verify_csv_files(config['output_dir'])
    else:
        print("\n⚠️ Export failed. Please fix the errors above and try again.")