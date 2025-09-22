#!/usr/bin/env python3
"""
Debug test to understand why traces aren't appearing in Galileo
"""

import sys
import os
import time

# Add app directory to path for imports
app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
sys.path.insert(0, app_path)

def test_debug_workflow():
    """Debug test to check if promptquality is working"""

    print("🧪 Testing Workflow Debug...")

    # First check if promptquality is available
    try:
        import promptquality as pq
        print(f"✅ promptquality imported successfully, version: {pq.__version__ if hasattr(pq, '__version__') else 'unknown'}")
    except ImportError as e:
        print(f"❌ Failed to import promptquality: {e}")
        return False

    # Now test the workflow logger
    from services.galileo_agent_workflow_logger import get_agent_workflow_logger

    logger = get_agent_workflow_logger(
        project_name="policy_compliance",
        log_stream="debug_test"
    )

    print(f"📊 Workflow logger initialized")
    print(f"   PROMPTQUALITY_AVAILABLE: {logger.PROMPTQUALITY_AVAILABLE if hasattr(logger, 'PROMPTQUALITY_AVAILABLE') else 'N/A'}")
    print(f"   Project: {logger.galileo_client.project_name}")
    print(f"   Log Stream: {logger.galileo_client.log_stream}")

    try:
        # Test creating a workflow with promptquality directly
        print("\n🔬 Testing direct promptquality workflow creation...")

        # Initialize promptquality session
        pq.login(os.environ.get("GALILEO_API_KEY"))
        pq.set_project("policy_compliance")

        # Create a test workflow
        print("Creating test workflow...")
        test_workflow = pq.WorkflowSpan(
            name="debug_test_workflow",
            metadata={
                "test": "true",
                "timestamp": str(int(time.time()))
            }
        )

        print(f"✅ Created workflow: {test_workflow.name if hasattr(test_workflow, 'name') else 'workflow created'}")

        # Add a sub-workflow
        print("Adding sub-workflow...")
        sub_workflow = test_workflow.add_sub_workflow(
            name="debug_sub_workflow",
            metadata={"sub": "true"}
        )
        print(f"✅ Created sub-workflow: {sub_workflow.name if hasattr(sub_workflow, 'name') else 'sub-workflow created'}")

        # Add an LLM step
        print("Adding LLM step to sub-workflow...")
        llm_step = sub_workflow.add_llm(
            name="debug_llm_step",
            input="test input",
            output="test output",
            model="test-model"
        )
        print(f"✅ Added LLM step")

        # Conclude sub-workflow
        print("Concluding sub-workflow...")
        sub_workflow.conclude()
        print(f"✅ Concluded sub-workflow")

        # Add another LLM step to main workflow
        print("Adding LLM step to main workflow...")
        main_llm_step = test_workflow.add_llm(
            name="main_llm_step",
            input="main test input",
            output="main test output",
            model="test-model"
        )
        print(f"✅ Added main LLM step")

        # Conclude main workflow
        print("Concluding main workflow...")
        test_workflow.conclude()
        print(f"✅ Concluded main workflow")

        # Flush traces
        print("\n💾 Flushing traces...")
        # Note: promptquality should automatically flush when workflow concludes

        print("\n✅ Debug test completed successfully!")
        print("\n🔍 Check Galileo console in project 'policy_compliance' for:")
        print("   - Log stream: 'debug_test'")
        print("   - Workflow: 'debug_test_workflow'")
        print("   └── Sub-workflow: 'debug_sub_workflow'")
        print("       └── LLM step: 'debug_llm_step'")
        print("   └── LLM step: 'main_llm_step'")

        return True

    except Exception as e:
        print(f"❌ Error in debug workflow test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_debug_workflow()
    sys.exit(0 if success else 1)