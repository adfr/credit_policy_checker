#!/usr/bin/env python3
"""
Quick test to verify hierarchical workflow logging is working
"""

import sys
import os

# Add app directory to path for imports
app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
sys.path.insert(0, app_path)

from services.galileo_agent_workflow_logger import get_agent_workflow_logger
import time

def test_quick_workflow():
    """Test the hierarchical workflow structure with mock data"""

    print("🧪 Testing Quick Hierarchical Workflow...")

    # Initialize the workflow logger
    logger = get_agent_workflow_logger(
        project_name="policy_compliance",
        log_stream="quick_test"
    )

    # Mock data for quick testing
    test_document = "Mock credit memo for conventional mortgage loan with 720 credit score..."

    test_agents = [
        {
            "agent_id": "TH0101",
            "agent_name": "Minimum FICO Score",
            "display_type": "threshold",
            "priority": "critical",
            "applicable_products": ["all", "mortgage", "conventional"]
        },
        {
            "agent_id": "SC0301",
            "agent_name": "Debt-to-Income Ratio",
            "display_type": "score",
            "priority": "critical",
            "applicable_products": ["mortgage", "conventional"]
        }
    ]

    selected_agents = test_agents  # All agents selected for this test

    try:
        # Step 1: Start main workflow
        print("📝 Starting main workflow...")
        document_id = f"quick_test_{int(time.time())}"
        workflow = logger.start_credit_evaluation_workflow(document_id, "quick_test")

        # Step 2: Start automatic selection span
        print("🎯 Starting automatic selection span...")
        logger.start_automatic_selection_span(
            document_content=test_document,
            all_available_agents=test_agents,
            selection_metadata={
                "min_relevance_score": 0.3,
                "max_agents": 10,
                "test_mode": True
            }
        )

        # Step 3: Log loan detection
        print("📍 Logging loan detection...")
        loan_detection_result = {
            "primary_loan_type": "mortgage",
            "mortgage_subtype": "conventional",
            "confidence": 0.95,
            "reasoning": "Mock loan detection for testing"
        }
        logger.log_loan_detection_step(loan_detection_result)

        # Step 4: Log agent scoring
        print("📊 Logging agent scoring...")
        logger.log_agent_scoring_step(test_agents, selected_agents)

        # Step 5: Complete selection span
        print("✅ Completing automatic selection span...")
        logger.complete_automatic_selection_span(selected_agents)

        # Step 6: Start agent execution span
        print("🤖 Starting agent execution span...")
        logger.start_agent_execution_span()

        # Step 7: Mock agent executions
        print("⚙️ Logging mock agent executions...")
        for i, agent in enumerate(selected_agents):
            mock_input_data = {"credit_score": 720, "debt_to_income": 0.35}
            mock_result = {
                "passed": True,
                "confidence": 0.95,
                "reason": f"Mock execution result for {agent['agent_name']}",
                "agent_id": agent['agent_id']
            }

            logger.log_agent_execution(
                agent_config=agent,
                agent_input_data=mock_input_data,
                agent_result=mock_result
            )
            print(f"   ✓ Logged execution for {agent['agent_name']}")

        # Step 8: Complete execution span
        print("✅ Completing agent execution span...")
        execution_summary = {
            "total_agents_executed": len(selected_agents),
            "passed_agents": len(selected_agents),
            "test_mode": True
        }
        logger.complete_agent_execution_span(execution_summary)

        # Step 9: Log overall assessment
        print("📋 Logging overall assessment...")
        mock_compliance_results = [
            {"agent_id": agent["agent_id"], "passed": True, "confidence": 0.95}
            for agent in selected_agents
        ]
        mock_overall_assessment = {
            "overall_compliance": True,
            "confidence_score": 0.95,
            "test_mode": True
        }
        logger.log_overall_assessment(mock_compliance_results, mock_overall_assessment)

        # Step 10: Complete main workflow
        print("🎉 Completing main workflow...")
        final_result = {
            "status": "completed",
            "test_mode": True,
            "hierarchical_structure": {
                "automatic_selection_span": "completed",
                "agent_execution_span": "completed",
                "main_workflow": "completed"
            }
        }
        logger.complete_workflow(final_result)

        # Flush traces
        print("💾 Flushing traces to Galileo...")
        logger.galileo_client.flush_traces()

        print("✅ Quick hierarchical workflow test completed successfully!")
        print(f"   Workflow ID: {logger.workflow_id}")
        print(f"   Project: {logger.galileo_client.project_name}")
        print(f"   Log Stream: {logger.galileo_client.log_stream}")
        print("")
        print("🔍 Check Galileo console for hierarchical structure:")
        print("   📁 Main Workflow: Quick Test Credit Evaluation")
        print("   ├── 🎯 Automatic Agent Selection (sub-workflow)")
        print("   │   ├── 📍 LoanTypeDetector")
        print("   │   └── 📊 AgentScorer")
        print("   ├── 🤖 Agent Execution (sub-workflow)")
        print("   │   ├── ⚙️ TH0101: Minimum FICO Score")
        print("   │   └── ⚙️ SC0301: Debt-to-Income Ratio")
        print("   └── 📋 Overall Assessment")

        return True

    except Exception as e:
        print(f"❌ Error in quick workflow test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_quick_workflow()
    sys.exit(0 if success else 1)