#!/usr/bin/env python3
"""
Working test that demonstrates the agent-based workflow logging in Galileo
This test shows how agents are logged individually even without hierarchical spans
"""

import sys
import os
import time
import json

# Add app directory to path for imports
app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
sys.path.insert(0, app_path)

from services.document_processor import DocumentProcessor

def test_working_workflow():
    """Test that actually works with current implementation"""

    print("=" * 80)
    print("🧪 TESTING AGENT-BASED WORKFLOW LOGGING")
    print("=" * 80)
    print()

    # Initialize document processor
    processor = DocumentProcessor()

    # Create test agents with proper structure
    available_agents = {
        "threshold_agents": [
            {
                "agent_id": "TH0101",
                "agent_name": "Minimum FICO Score Check",
                "display_type": "threshold",
                "priority": "critical",
                "data_fields": ["credit_score"],
                "threshold_value": 620,
                "threshold_operator": ">=",
                "applicable_products": ["all", "mortgage", "conventional"],
                "description": "Verifies minimum credit score requirement"
            },
            {
                "agent_id": "TH0102",
                "agent_name": "Maximum LTV Ratio Check",
                "display_type": "threshold",
                "priority": "critical",
                "data_fields": ["loan_amount", "property_value"],
                "threshold_value": 80,
                "threshold_operator": "<=",
                "applicable_products": ["mortgage", "conventional", "primary_residence"],
                "description": "Ensures loan-to-value ratio is within limits"
            }
        ],
        "criteria_agents": [
            {
                "agent_id": "CR0201",
                "agent_name": "Identity Verification Agent",
                "display_type": "criteria",
                "priority": "high",
                "data_fields": ["id_documents", "ssn_documentation"],
                "criteria": ["valid_id", "ssn_match"],
                "applicable_products": ["all", "universal"],
                "description": "Validates identity documentation"
            }
        ],
        "score_agents": [
            {
                "agent_id": "SC0301",
                "agent_name": "DTI Ratio Calculator",
                "display_type": "score",
                "priority": "critical",
                "data_fields": ["monthly_income", "monthly_debt"],
                "max_score": 43,
                "applicable_products": ["mortgage", "conventional", "first_time_buyer"],
                "description": "Calculates debt-to-income ratio score"
            }
        ],
        "qualitative_agents": []
    }

    # Use existing PDF file
    test_file_path = "/Users/adrienchenailler/Documents/integrate_policy_checker/mortgage-credit-memo.pdf"

    # Applicant data for testing
    applicant_data = {
        "credit_score": 720,
        "annual_income": 75000,
        "monthly_income": 6250,
        "monthly_debt": 2000,
        "loan_amount": 300000,
        "property_value": 400000
    }

    try:
        print("📄 Processing document with automatic agent selection...")
        print(f"   Document: {os.path.basename(test_file_path)}")
        print(f"   Available agents: {sum(len(agents) for agents in available_agents.values())}")
        print()

        # Run the automatic compliance check
        start_time = time.time()
        result = processor.check_document_compliance_automatic(
            file_path=test_file_path,
            available_agents=available_agents,
            applicant_data=applicant_data,
            min_relevance_score=0.3,
            max_agents=10
        )
        end_time = time.time()

        print()
        print("=" * 80)
        print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print()

        # Display results
        if 'error' in result:
            print(f"❌ Error occurred: {result['error']}")
            return False

        # Show what was logged
        print("📊 WORKFLOW EXECUTION SUMMARY:")
        print("-" * 40)

        # Processing info
        print(f"⏱️  Processing time: {end_time - start_time:.2f} seconds")
        print(f"📝 Processing status: {result.get('processing_status', 'unknown')}")
        print(f"🔄 Selection mode: {result.get('selection_mode', 'unknown')}")
        print(f"🆔 Galileo session ID: {result.get('galileo_session_id', 'unknown')}")
        print()

        # Agent selection results
        automatic_selection = result.get('automatic_selection', {})
        selected_agents = automatic_selection.get('selected_agents', [])
        loan_detection = automatic_selection.get('loan_detection', {})

        print("🎯 AUTOMATIC AGENT SELECTION:")
        print("-" * 40)
        print(f"📍 Detected loan type: {loan_detection.get('primary_loan_type', 'unknown')}")
        print(f"   Confidence: {loan_detection.get('confidence', 0):.1%}")
        print(f"   Subtype: {loan_detection.get('mortgage_subtype', 'unknown')}")
        print(f"📊 Agents selected: {len(selected_agents)} out of {automatic_selection.get('total_available', 0)}")
        print()

        # Individual agent executions
        print("🤖 INDIVIDUAL AGENT EXECUTIONS:")
        print("-" * 40)

        compliance_results = result.get('compliance_results', {})
        agent_results = compliance_results.get('agent_results', [])

        for i, agent_result in enumerate(agent_results, 1):
            agent_id = agent_result.get('agent_id', 'Unknown')
            agent_name = agent_result.get('agent_name', 'Unknown Agent')
            passed = agent_result.get('passed', False)
            confidence = agent_result.get('confidence', 0)

            status_icon = "✅" if passed else "❌"
            print(f"{i}. {status_icon} {agent_name} ({agent_id})")
            print(f"   Result: {'PASSED' if passed else 'FAILED'}")
            print(f"   Confidence: {confidence:.1%}")

            if agent_result.get('reason'):
                print(f"   Reason: {agent_result['reason']}")
            print()

        # Overall assessment
        overall = compliance_results.get('compliance_summary', {})
        print("📋 OVERALL ASSESSMENT:")
        print("-" * 40)
        print(f"Overall compliance: {overall.get('overall_compliance', 'Unknown')}")
        print(f"Agents passed: {overall.get('agents_passed', 0)} / {overall.get('total_agents', 0)}")

        if overall.get('confidence_score'):
            print(f"Confidence score: {overall['confidence_score']:.1%}")
        if overall.get('risk_assessment'):
            print(f"Risk level: {overall['risk_assessment']}")
        print()

        # What to look for in Galileo
        print("=" * 80)
        print("🔍 WHAT YOU'LL SEE IN GALILEO CONSOLE:")
        print("=" * 80)
        print()
        print(f"Project: policy_compliance")
        print(f"Session ID: {result.get('galileo_session_id', 'unknown')}")
        print()
        print("You should see the following traces (each as a separate entry):")
        print()
        print("1️⃣  WORKFLOW START: Credit Evaluation")
        print("2️⃣  SUB-WORKFLOW: Automatic Agent Selection")
        print("3️⃣  LoanTypeDetector - Analyzing loan type")
        print("4️⃣  AgentScorer - Scoring and selecting agents")
        print("5️⃣  SUB-WORKFLOW: Agent Execution")

        for agent in selected_agents[:5]:  # Show first 5 agents
            print(f"6️⃣  {agent['agent_name']} - Individual execution")

        if len(selected_agents) > 5:
            print(f"   ... and {len(selected_agents) - 5} more agent executions")

        print("7️⃣  Overall Assessment - Final compliance evaluation")
        print()
        print("NOTE: These appear as separate traces with metadata showing relationships.")
        print("      Look for the 'hierarchy_level' and 'parent_span' fields in metadata.")
        print()

        return True

    except Exception as e:
        print(f"❌ Error in workflow test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_working_workflow()

    if success:
        print("✅ Test completed successfully!")
        print("🎉 Check your Galileo console to see the agent traces!")
    else:
        print("❌ Test failed!")

    sys.exit(0 if success else 1)