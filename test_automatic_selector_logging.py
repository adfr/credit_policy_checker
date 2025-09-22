#!/usr/bin/env python3
"""
Test script for Galileo automatic agent selector logging
"""

import sys
import os

# Add app directory to path for imports
app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
sys.path.insert(0, app_path)

from services.galileo_agent_workflow_logger import get_agent_workflow_logger

def test_automatic_selector_logging():
    """Test the automatic agent selector logging functionality"""

    print("🧪 Testing Automatic Agent Selector Logging...")

    # Initialize the workflow logger
    logger = get_agent_workflow_logger(
        project_name="test_automatic_selector",
        log_stream="test_automatic_workflows"
    )

    # Test data
    test_document = "This is a conventional loan application with a credit score of 720..."

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
        # Step 1: Start workflow
        print("📝 Starting workflow...")
        workflow = logger.start_credit_evaluation_workflow("test_auto_doc_456", "automatic_compliance")

        # Step 2: Log automatic agent selector as its own agent step
        print("🤖 Logging automatic agent selector...")
        logger.log_automatic_agent_selector(
            document_content=test_document,
            all_available_agents=test_available_agents,
            loan_detection_result=loan_detection_result,
            selected_agents=test_selected_agents,
            selection_metadata={
                "min_relevance_score": 0.3,
                "max_agents": 10,
                "selection_timestamp": 1234567890,
                "selection_mode": "automatic"
            }
        )

        # Step 3: Log individual agent executions (simulate)
        print("🎯 Logging individual agent executions...")
        for agent in test_selected_agents:
            test_agent_data = {"credit_score": 720, "loan_type": "conventional"}
            test_result = {"passed": True, "confidence": 0.95, "reason": f"{agent['agent_name']} check passed"}

            logger.log_agent_execution(
                agent_config=agent,
                agent_input_data=test_agent_data,
                agent_result=test_result
            )

        # Step 4: Log overall assessment
        print("📊 Logging overall assessment...")
        test_compliance_results = [
            {"agent_id": "TH0101", "passed": True, "confidence": 0.95},
            {"agent_id": "SC0301", "passed": True, "confidence": 0.88}
        ]
        test_overall_assessment = {
            "overall_compliance": True,
            "confidence_score": 0.92,
            "risk_level": "low"
        }

        logger.log_overall_assessment(test_compliance_results, test_overall_assessment)

        # Step 5: Complete workflow
        print("✅ Completing workflow...")
        final_result = {
            "status": "completed",
            "automatic_selection": {
                "agents_selected": len(test_selected_agents),
                "loan_type_detected": loan_detection_result["loan_type"]
            },
            "agents_processed": len(test_selected_agents),
            "overall_result": test_overall_assessment
        }

        logger.complete_workflow(final_result)

        print("🎉 Automatic selector workflow logging test completed successfully!")
        print(f"   Workflow ID: {logger.workflow_id}")
        print("   Check Galileo console for:")
        print("   1. AutomaticAgentSelector as its own agent step")
        print("   2. Individual agent executions (TH0101, SC0301)")
        print("   3. Overall assessment")
        print("   4. Complete workflow visualization")

        return True

    except Exception as e:
        print(f"❌ Error in automatic selector workflow test: {e}")
        return False

if __name__ == "__main__":
    success = test_automatic_selector_logging()
    sys.exit(0 if success else 1)