#!/usr/bin/env python3
"""
Test script for Galileo agent-based workflow logging
"""

import sys
import os

# Add app directory to path for imports
app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
sys.path.insert(0, app_path)

from services.galileo_agent_workflow_logger import get_agent_workflow_logger

def test_workflow_logging():
    """Test the basic workflow logging functionality"""

    print("🧪 Testing Galileo Agent Workflow Logging...")

    # Initialize the workflow logger
    logger = get_agent_workflow_logger(
        project_name="test_policy_compliance",
        log_stream="test_agent_workflows"
    )

    # Test document and agents data
    test_document = "Sample credit application document content for testing..."

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
        }
    ]

    test_selected_agents = [test_available_agents[0]]  # Select only first agent

    try:
        # Step 1: Start workflow
        print("📝 Starting workflow...")
        workflow = logger.start_credit_evaluation_workflow("test_doc_123")

        # Step 2: Log agent selection
        print("🎯 Logging agent selection...")
        logger.log_agent_selection_phase(
            document_content=test_document,
            all_available_agents=test_available_agents,
            selected_agents=test_selected_agents,
            selection_metadata={"test_mode": True}
        )

        # Step 3: Log agent execution
        print("🤖 Logging agent execution...")
        test_agent_data = {"credit_score": 720, "loan_type": "conventional"}
        test_result = {"passed": True, "confidence": 0.95, "reason": "Credit score meets minimum requirement"}

        logger.log_agent_execution(
            agent_config=test_selected_agents[0],
            agent_input_data=test_agent_data,
            agent_result=test_result
        )

        # Step 4: Log overall assessment
        print("📊 Logging overall assessment...")
        test_compliance_results = [test_result]
        test_overall_assessment = {
            "overall_compliance": True,
            "confidence_score": 0.95,
            "risk_level": "low"
        }

        logger.log_overall_assessment(test_compliance_results, test_overall_assessment)

        # Step 5: Complete workflow
        print("✅ Completing workflow...")
        final_result = {
            "status": "completed",
            "agents_processed": 1,
            "overall_result": test_overall_assessment
        }

        logger.complete_workflow(final_result)

        print("🎉 Workflow logging test completed successfully!")
        print(f"   Workflow ID: {logger.workflow_id}")
        print("   Check Galileo console for workflow visualization.")

        return True

    except Exception as e:
        print(f"❌ Error in workflow logging test: {e}")
        return False

if __name__ == "__main__":
    success = test_workflow_logging()
    sys.exit(0 if success else 1)