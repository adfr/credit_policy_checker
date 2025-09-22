#!/usr/bin/env python3
"""
Test the actual automatic compliance workflow with real agents
"""

import sys
import os

# Add app directory to path for imports
app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
sys.path.insert(0, app_path)

from services.document_processor import DocumentProcessor
import json

def test_real_automatic_workflow():
    """Test the real automatic compliance workflow"""

    print("🧪 Testing Real Automatic Compliance Workflow...")

    # Initialize document processor
    processor = DocumentProcessor()

    # Load some real available agents (simulated)
    available_agents = {
        "threshold_agents": [
            {
                "agent_id": "TH0101",
                "agent_name": "Minimum FICO Score",
                "display_type": "threshold",
                "priority": "critical",
                "data_fields": ["credit_score", "loan_type"],
                "threshold_value": 620,
                "threshold_operator": ">=",
                "applicable_products": ["all", "mortgage", "conventional"]
            },
            {
                "agent_id": "TH0102",
                "agent_name": "Maximum LTV Ratio",
                "display_type": "threshold",
                "priority": "critical",
                "data_fields": ["loan_amount", "property_value"],
                "threshold_value": 80,
                "threshold_operator": "<=",
                "applicable_products": ["mortgage", "conventional", "primary_residence"]
            }
        ],
        "criteria_agents": [
            {
                "agent_id": "CR0201",
                "agent_name": "Identity Verification",
                "display_type": "criteria",
                "priority": "high",
                "data_fields": ["id_documents", "ssn_documentation"],
                "criteria": ["valid_id", "ssn_match"],
                "applicable_products": ["all", "universal"]
            }
        ],
        "score_agents": [
            {
                "agent_id": "SC0301",
                "agent_name": "Debt-to-Income Ratio",
                "display_type": "score",
                "priority": "critical",
                "data_fields": ["monthly_income", "monthly_debt"],
                "max_score": 43,
                "applicable_products": ["mortgage", "conventional", "first_time_buyer"]
            }
        ],
        "qualitative_agents": []
    }

    # Test document content
    test_document_content = """
    This is a conventional loan application for a primary residence.

    Applicant Information:
    - Credit Score: 720
    - Annual Income: $75,000
    - Monthly Debt: $2,000
    - Loan Amount: $300,000
    - Property Value: $400,000

    The applicant has provided valid identification and SSN documentation.
    This is a first-time homebuyer seeking a 30-year fixed-rate mortgage.
    """

    # Use an existing PDF file
    test_file_path = "/Users/adrienchenailler/Documents/integrate_policy_checker/mortgage-credit-memo.pdf"

    try:
        print("📄 Processing test document with automatic agent selection...")

        # Test the actual automatic compliance workflow
        result = processor.check_document_compliance_automatic(
            file_path=test_file_path,
            available_agents=available_agents,
            applicant_data={
                "credit_score": 720,
                "annual_income": 75000,
                "monthly_debt": 2000,
                "loan_amount": 300000,
                "property_value": 400000
            },
            min_relevance_score=0.3,
            max_agents=10
        )

        print("✅ Automatic compliance workflow completed!")
        print(f"   Processing Status: {result.get('processing_status', 'unknown')}")
        print(f"   Selection Mode: {result.get('selection_mode', 'unknown')}")
        print(f"   Galileo Session ID: {result.get('galileo_session_id', 'unknown')}")
        print(f"   Hierarchical Structure: {result.get('hierarchical_structure', {})}")

        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            return False
        else:
            print("🎉 Check Galileo console for the hierarchical workflow!")
            print("Expected structure:")
            print("📁 Main Workflow: Automatic Credit Evaluation")
            print("├── 🎯 Automatic Agent Selection (sub-workflow)")
            print("│   ├── 📍 LoanTypeDetector")
            print("│   └── 📊 AgentScorer")
            print("├── 🤖 Agent Execution (sub-workflow)")
            print("│   ├── ⚙️ [Selected Agent 1 by name]")
            print("│   ├── ⚙️ [Selected Agent 2 by name]")
            print("│   └── ⚙️ [Selected Agent N by name]")
            print("└── 📋 Overall Assessment")
            return True

    except Exception as e:
        print(f"❌ Error in real automatic workflow test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # No cleanup needed for existing PDF file
        pass

if __name__ == "__main__":
    success = test_real_automatic_workflow()
    sys.exit(0 if success else 1)