#!/usr/bin/env python3
"""
Test script for Galileo hierarchical workflow spans with automatic agent selection
"""

import sys
import os

# Add app directory to path for imports
app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
sys.path.insert(0, app_path)

from services.galileo_agent_workflow_logger import get_agent_workflow_logger

def test_hierarchical_workflow():
    """Test the hierarchical workflow structure with sub-workflows"""

    print("🧪 Testing Hierarchical Workflow Structure...")

    # Initialize the workflow logger
    logger = get_agent_workflow_logger(
        project_name="test_hierarchical_workflow",
        log_stream="test_hierarchical_spans"
    )

    # Test data
    test_document = "This is a conventional loan application with a credit score of 720 and a debt-to-income ratio of 35%..."

    test_available_agents = [
        {
            "agent_id": "TH0101",
            "agent_name": "Minimum FICO Score",
            "display_type": "threshold",
            "priority": "critical",
            "data_fields": ["credit_score", "loan_type"]
        },
        {
            "agent_id": "CR0205",
            "agent_name": "Identity Verification",
            "display_type": "criteria",
            "priority": "high",
            "data_fields": ["id_documents", "ssn_documentation"]
        },
        {
            "agent_id": "SC0301",
            "agent_name": "Debt-to-Income Ratio",
            "display_type": "score",
            "priority": "critical",
            "data_fields": ["monthly_income", "monthly_debt"]
        }
    ]

    test_selected_agents = [test_available_agents[0], test_available_agents[2]]  # Select threshold and score agents

    loan_detection_result = {
        "loan_type": "conventional",
        "confidence": 0.85,
        "characteristics": ["first_time_buyer", "primary_residence"]
    }

    try:
        # Step 1: Start main workflow
        print("📝 Starting main workflow...")
        workflow = logger.start_credit_evaluation_workflow("test_hierarchical_doc_789", "hierarchical_compliance")

        # Step 2: Start automatic selection span (sub-workflow)
        print("🎯 Starting automatic selection span...")
        logger.start_automatic_selection_span(
            document_content=test_document,
            all_available_agents=test_available_agents,
            selection_metadata={
                "min_relevance_score": 0.3,
                "max_agents": 10
            }
        )

        # Step 3: Log loan detection within the selection span
        print("📍 Logging loan detection step...")
        logger.log_loan_detection_step(loan_detection_result)

        # Step 4: Log agent scoring within the selection span
        print("📊 Logging agent scoring step...")
        logger.log_agent_scoring_step(test_available_agents, test_selected_agents)

        # Step 5: Complete automatic selection span
        print("✅ Completing automatic selection span...")
        logger.complete_automatic_selection_span(test_selected_agents)

        # Step 6: Start agent execution span (sub-workflow)
        print("🤖 Starting agent execution span...")
        logger.start_agent_execution_span()

        # Step 7: Log individual agent executions within execution span
        print("⚙️ Logging individual agent executions...")
        for agent in test_selected_agents:
            test_agent_data = {"credit_score": 720, "loan_type": "conventional", "debt_to_income": 0.35}
            test_result = {
                "passed": True,
                "confidence": 0.95,
                "reason": f"{agent['agent_name']} check passed",
                "agent_id": agent['agent_id']
            }

            logger.log_agent_execution(
                agent_config=agent,
                agent_input_data=test_agent_data,
                agent_result=test_result
            )

        # Step 8: Complete agent execution span
        print("✅ Completing agent execution span...")
        execution_summary = {
            "total_agents_executed": len(test_selected_agents),
            "passed_agents": len(test_selected_agents),
            "overall_execution_success": True
        }
        logger.complete_agent_execution_span(execution_summary)

        # Step 9: Log overall assessment in main workflow
        print("📋 Logging overall assessment...")
        test_compliance_results = [
            {"agent_id": "TH0101", "passed": True, "confidence": 0.95},
            {"agent_id": "SC0301", "passed": True, "confidence": 0.90}
        ]
        test_overall_assessment = {
            "overall_compliance": True,
            "confidence_score": 0.925,
            "risk_level": "low"
        }

        logger.log_overall_assessment(test_compliance_results, test_overall_assessment)

        # Step 10: Complete main workflow
        print("🎉 Completing main workflow...")
        final_result = {
            "status": "completed",
            "hierarchical_structure": {
                "automatic_selection_span": "completed",
                "agent_execution_span": "completed",
                "main_workflow": "completed"
            },
            "agents_processed": len(test_selected_agents),
            "overall_result": test_overall_assessment
        }

        logger.complete_workflow(final_result)

        print("🎉 Hierarchical workflow test completed successfully!")
        print(f"   Main Workflow ID: {logger.workflow_id}")
        print("   Check Galileo console for hierarchical structure:")
        print("   📁 Main Workflow")
        print("   ├── 🎯 Automatic Agent Selection (sub-workflow)")
        print("   │   ├── 📍 LoanTypeDetector")
        print("   │   └── 📊 AgentScorer")
        print("   ├── 🤖 Agent Execution (sub-workflow)")
        print("   │   ├── ⚙️ TH0101: Minimum FICO Score")
        print("   │   └── ⚙️ SC0301: Debt-to-Income Ratio")
        print("   └── 📋 Overall Assessment")

        return True

    except Exception as e:
        print(f"❌ Error in hierarchical workflow test: {e}")
        return False

if __name__ == "__main__":
    success = test_hierarchical_workflow()
    sys.exit(0 if success else 1)