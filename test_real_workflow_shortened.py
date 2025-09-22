#!/usr/bin/env python3
"""
Shortened version of real automatic workflow test that should complete quickly
"""

import sys
import os

# Add app directory to path for imports
app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
sys.path.insert(0, app_path)

from services.document_processor import DocumentProcessor
import json

def test_shortened_real_workflow():
    """Test real workflow with fewer agents to complete faster"""

    print("🧪 Testing Shortened Real Automatic Workflow...")

    # Initialize document processor
    processor = DocumentProcessor()

    # Use only 2 agents to make it faster
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
        "score_agents": [],
        "qualitative_agents": []
    }

    # Use an existing PDF file
    test_file_path = "/Users/adrienchenailler/Documents/integrate_policy_checker/mortgage-credit-memo.pdf"

    try:
        print("📄 Processing test document with 2 agents only...")

        # Test the actual automatic compliance workflow with fewer agents
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
            max_agents=2  # Limit to 2 agents max
        )

        print("✅ Shortened automatic workflow completed!")
        print(f"   Processing Status: {result.get('processing_status', 'unknown')}")
        print(f"   Selection Mode: {result.get('selection_mode', 'unknown')}")
        print(f"   Galileo Session ID: {result.get('galileo_session_id', 'unknown')}")
        print(f"   Hierarchical Structure: {result.get('hierarchical_structure', {})}")

        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            return False
        else:
            # Check how many agents were selected and executed
            compliance_results = result.get('compliance_results', {})
            agent_results = compliance_results.get('agent_results', [])
            selected_agents = result.get('automatic_selection', {}).get('selected_agents', [])

            print(f"   Agents Selected: {len(selected_agents)}")
            print(f"   Agents Executed: {len(agent_results)}")

            for i, agent in enumerate(selected_agents):
                print(f"     {i+1}. {agent.get('agent_name', 'Unknown')} ({agent.get('agent_id', 'Unknown')})")

            print("🎉 Check Galileo console for the hierarchical workflow!")
            print("Expected structure:")
            print("📁 Main Workflow: Automatic Credit Evaluation")
            print("├── 🎯 Automatic Agent Selection (sub-workflow)")
            print("│   ├── 📍 LoanTypeDetector")
            print("│   └── 📊 AgentScorer")
            print("├── 🤖 Agent Execution (sub-workflow)")
            for agent in selected_agents:
                print(f"│   ├── ⚙️ {agent.get('agent_id', 'Unknown')}: {agent.get('agent_name', 'Unknown')}")
            print("└── 📋 Overall Assessment")
            return True

    except Exception as e:
        print(f"❌ Error in shortened real workflow test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_shortened_real_workflow()
    sys.exit(0 if success else 1)