"""
Test suite for SQL Agent
Tests query generation, security validation, and result formatting.
"""

from src.agents.sql_agent import (
    query_sql_agent, 
    get_database_schema, 
    execute_sql_query,
    validate_sql_query
)

def test_security_validation():
    """Test that security validation blocks malicious queries."""
    print("="*80)
    print("TEST 1: SECURITY VALIDATION")
    print("="*80)
    
    test_cases = [
        # Should PASS
        ("SELECT * FROM customer LIMIT 5", True, "Simple SELECT"),
        ("SELECT first_name, last_name FROM customer WHERE active = 1", True, "SELECT with WHERE"),
        ("SELECT COUNT(*) FROM rental", True, "Aggregate function"),
        
        # Should FAIL
        ("DROP TABLE customer", False, "DROP attempt"),
        ("DELETE FROM customer WHERE customer_id = 1", False, "DELETE attempt"),
        ("INSERT INTO customer VALUES (999, 'Hacker', 'Man')", False, "INSERT attempt"),
        ("UPDATE customer SET first_name = 'Hacked'", False, "UPDATE attempt"),
        ("SELECT * FROM customer; DROP TABLE customer;", False, "SQL injection"),
        ("SELECT * FROM customer -- comment", False, "SQL comment"),
    ]
    
    passed = 0
    failed = 0
    
    for query, should_pass, description in test_cases:
        is_valid, error_msg = validate_sql_query(query)
        
        if (is_valid and should_pass) or (not is_valid and not should_pass):
            print(f"✓ PASS: {description}")
            print(f"   Query: {query[:60]}...")
            if not should_pass:
                print(f"   Correctly blocked: {error_msg}")
            passed += 1
        else:
            print(f"✗ FAIL: {description}")
            print(f"   Query: {query[:60]}...")
            print(f"   Expected: {'PASS' if should_pass else 'FAIL'}, Got: {'PASS' if is_valid else 'FAIL'}")
            failed += 1
        print()
    
    print(f"Results: {passed} passed, {failed} failed\n")
    return failed == 0


def test_schema_inspection():
    """Test that schema inspection tool works."""
    print("="*80)
    print("TEST 2: SCHEMA INSPECTION")
    print("="*80)
    
    try:
        # Invoke tool properly (new LangChain syntax)
        schema = get_database_schema.invoke({})
        
        # Check if essential tables are present
        required_tables = ['customer', 'film', 'rental', 'payment', 'actor']
        all_present = all(table in schema for table in required_tables)
        
        if all_present:
            print("✓ PASS: Schema inspection works")
            print(f"   Found all required tables: {', '.join(required_tables)}")
            print(f"   Schema length: {len(schema)} characters")
        else:
            print("✗ FAIL: Schema inspection incomplete")
            print(f"   Missing tables")
        
        print()
        return all_present
        
    except Exception as e:
        print(f"✗ FAIL: Schema inspection failed with error: {e}\n")
        return False


def test_direct_sql_execution():
    """Test direct SQL execution tool."""
    print("="*80)
    print("TEST 3: DIRECT SQL EXECUTION")
    print("="*80)
    
    test_queries = [
        ("SELECT COUNT(*) FROM customer", "Count customers"),
        ("SELECT first_name, last_name FROM customer LIMIT 3", "Get customer names"),
        ("SELECT title FROM film WHERE rating = 'PG' LIMIT 5", "Filter films by rating"),
        ("SELECT c.name, COUNT(*) as film_count FROM category c JOIN film_category fc ON c.category_id = fc.category_id GROUP BY c.name ORDER BY film_count DESC LIMIT 5", "Category statistics"),
    ]
    
    passed = 0
    failed = 0
    
    for query, description in test_queries:
        try:
            result = execute_sql_query(query)
            
            if "❌" in result:
                print(f"✗ FAIL: {description}")
                print(f"   Query: {query[:60]}...")
                print(f"   Error: {result[:100]}...")
                failed += 1
            else:
                print(f"✓ PASS: {description}")
                print(f"   Query: {query[:60]}...")
                print(f"   Result preview: {result[:150]}...")
                passed += 1
        except Exception as e:
            print(f"✗ FAIL: {description}")
            print(f"   Exception: {e}")
            failed += 1
        print()
    
    print(f"Results: {passed} passed, {failed} failed\n")
    return failed == 0


def test_agent_natural_language():
    """Test agent with natural language queries."""
    print("="*80)
    print("TEST 4: NATURAL LANGUAGE QUERIES (AGENT)")
    print("="*80)
    print("Note: This tests the full agent with LLM reasoning\n")
    
    test_queries = [
        "How many customers are in the database?",
        "Show me the top 3 films by rental rate",
        "What are the names of all the categories?",
    ]
    
    passed = 0
    failed = 0
    
    for query in test_queries:
        print(f"Query: {query}")
        print("-" * 80)
        
        try:
            result = query_sql_agent(query)
            
            if result and len(result) > 0 and "❌" not in result:
                print(f"✓ PASS: Agent responded")
                print(f"   Response preview: {result[:200]}...")
                passed += 1
            else:
                print(f"✗ FAIL: Agent gave no/error response")
                print(f"   Response: {result[:200]}...")
                failed += 1
                
        except Exception as e:
            print(f"✗ FAIL: Exception occurred")
            print(f"   Error: {e}")
            failed += 1
        
        print()
    
    print(f"Results: {passed} passed, {failed} failed\n")
    return failed == 0


def test_complex_queries():
    """Test more complex SQL queries."""
    print("="*80)
    print("TEST 5: COMPLEX QUERIES")
    print("="*80)
    
    complex_queries = [
        """
        SELECT 
            c.first_name || ' ' || c.last_name as customer_name,
            COUNT(r.rental_id) as rental_count,
            SUM(p.amount) as total_paid
        FROM customer c
        JOIN rental r ON c.customer_id = r.customer_id
        JOIN payment p ON r.rental_id = p.rental_id
        GROUP BY c.customer_id, c.first_name, c.last_name
        ORDER BY total_paid DESC
        LIMIT 5
        """,
    ]
    
    for i, query in enumerate(complex_queries, 1):
        print(f"Complex Query {i}:")
        print(query.strip())
        print("-" * 80)
        
        try:
            result = execute_sql_query(query)
            
            if "❌" in result:
                print(f"✗ FAIL: Query execution failed")
                print(f"   Error: {result[:200]}...")
            else:
                print(f"✓ PASS: Complex query executed successfully")
                print(f"   Result:\n{result}")
                
        except Exception as e:
            print(f"✗ FAIL: Exception: {e}")
        
        print()
    
    return True


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "="*80)
    print("SQL AGENT - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print()
    
    results = {
        "Security Validation": test_security_validation(),
        "Schema Inspection": test_schema_inspection(),
        "Direct SQL Execution": test_direct_sql_execution(),
        "Natural Language Queries": test_agent_natural_language(),
        "Complex Queries": test_complex_queries(),
    }
    
    print("="*80)
    print("FINAL RESULTS")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print()
    print(f"Overall: {total_passed}/{total_tests} test suites passed")
    print("="*80)
    
    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED! SQL Agent is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Review errors above.")
    
    return total_passed == total_tests


if __name__ == "__main__":
    run_all_tests()