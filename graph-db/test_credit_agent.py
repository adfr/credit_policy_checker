import sys
sys.path.append('..')

from agents.credit_agent import CreditAgent
import json

def test_credit_agent():
    """Test the credit agent with sample credit data"""
    
    # Sample credit data
    credit_data = {
        "applicant": {
            "name": "John Doe",
            "age": 35,
            "income": 75000,
            "credit_score": 720,
            "employment_status": "Full-time",
            "years_employed": 5
        },
        "loan_details": {
            "amount": 250000,
            "purpose": "Home Purchase",
            "term_years": 30,
            "interest_rate": 4.5
        },
        "financial_history": {
            "bankruptcies": 0,
            "late_payments": 2,
            "debt_to_income_ratio": 0.35,
            "existing_loans": 1
        }
    }
    
    print("Initializing Credit Agent...")
    agent = CreditAgent()
    
    try:
        # Test 1: Get all requirements from graph
        print("\n1. Fetching requirements from graph database:")
        requirements = agent.get_requirements()
        print(f"Found {len(requirements)} requirements")
        for req in requirements[:3]:  # Show first 3
            print(f"  - {req.get('name', 'Unknown')}: {req.get('description', 'No description')}")
        
        # Test 2: Check linkages for first requirement
        if requirements:
            first_req = requirements[0]
            print(f"\n2. Checking linkages for '{first_req.get('name', 'Unknown')}':")
            linkages = agent.get_requirement_linkages(first_req['id'])
            print(f"Found {len(linkages)} linkages")
            for link in linkages:
                print(f"  - Linked to: {link.get('linked_name', 'Unknown')} (Type: {link.get('linkage_type', 'Unknown')})")
        
        # Test 3: Analyze credit compliance
        print("\n3. Analyzing credit compliance:")
        results = agent.analyze_credit_compliance(credit_data)
        
        print(f"\nOverall Compliance: {'PASSED' if results['overall_compliance'] else 'FAILED'}")
        print(f"Compliance Score: {results['compliance_score']:.1f}%")
        print(f"Requirements Checked: {len(results['requirements_checked'])}")
        
        # Show some requirement results
        print("\nRequirement Check Results:")
        for check in results['requirements_checked'][:3]:
            status = "✓" if check['passed'] else "✗"
            print(f"  {status} {check.get('requirement_name', 'Unknown')}: {check.get('reason', 'No reason provided')}")
        
        # Test 4: Custom query example
        print("\n4. Running custom graph query:")
        custom_query = """
            MATCH (r:Requirement)
            WHERE r.type = 'Credit Score'
            RETURN r.name as name, r.description as description
            LIMIT 5
        """
        custom_results = agent.query_graph(custom_query)
        print(f"Found {len(custom_results)} credit score requirements")
        
    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        agent.close()
        print("\nCredit Agent closed.")

if __name__ == "__main__":
    test_credit_agent()