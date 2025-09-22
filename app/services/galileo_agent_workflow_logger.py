import time
import hashlib
from typing import Dict, List, Optional, Any
import json

try:
    import promptquality as pq
    PROMPTQUALITY_AVAILABLE = True
except ImportError:
    PROMPTQUALITY_AVAILABLE = False
    print("Warning: promptquality not available. Agent workflow logging will be disabled.")

from app.services.galileo_client_v2 import GalileoClientV2


class GalileoAgentWorkflowLogger:
    """Enhanced Galileo client for agent-based workflow logging in credit evaluation"""

    def __init__(self, project_name: str = "policy_compliance", log_stream: str = "agent_workflows"):
        global PROMPTQUALITY_AVAILABLE

        self.project_name = project_name
        self.log_stream = log_stream
        # Initialize the Galileo client with specific parameters
        self.galileo_client = GalileoClientV2(project_name=project_name, log_stream=log_stream)
        self.current_workflow = None
        self.workflow_id = None
        self.automatic_selection_span = None  # Track the automatic selection sub-workflow
        self.agent_execution_span = None      # Track the agent execution sub-workflow

        # Initialize promptquality if available
        if PROMPTQUALITY_AVAILABLE:
            try:
                # Use environment variable for API key
                import os
                api_key = os.environ.get("GALILEO_API_KEY")
                if api_key:
                    pq.login(api_key)
                    pq.set_project(project_name)
                    print(f"GalileoAgentWorkflowLogger initialized with project: {project_name}, stream: {log_stream}")
                else:
                    print(f"Warning: GALILEO_API_KEY not found, using fallback logging")
                    PROMPTQUALITY_AVAILABLE = False
            except Exception as e:
                print(f"Warning: Could not initialize promptquality: {e}")
                PROMPTQUALITY_AVAILABLE = False

    def start_credit_evaluation_workflow(self, document_id: str, workflow_type: str = "credit_evaluation") -> Optional[Any]:
        """
        Start a new workflow for credit evaluation

        Args:
            document_id: Unique identifier for the document being evaluated
            workflow_type: Type of workflow (default: credit_evaluation)

        Returns:
            Workflow object for logging steps
        """
        self.workflow_id = f"credit_eval_{document_id}_{int(time.time())}"

        # Since GalileoClientV2 doesn't have log_llm_call, we'll just track internally
        self.current_workflow = {
            "workflow_id": self.workflow_id,
            "status": "started",
            "document_id": document_id,
            "workflow_type": workflow_type
        }
        print(f"Started workflow: {self.workflow_id}")
        return self.current_workflow

    def start_automatic_selection_span(self, document_content: str, all_available_agents: List[Dict],
                                      selection_metadata: Optional[Dict] = None) -> None:
        """
        Start a hierarchical workflow span for automatic agent selection process

        Args:
            document_content: Document content being analyzed
            all_available_agents: All agents available for selection
            selection_metadata: Additional metadata about the selection process
        """
        if not self.current_workflow:
            print("Warning: No active workflow to start automatic selection span")
            return

        # Prepare input data for the automatic selection span
        selection_input = {
            "document_summary": document_content[:500] + "..." if len(document_content) > 500 else document_content,
            "total_available_agents": len(all_available_agents),
            "available_agent_types": list(set([agent.get('display_type', 'unknown') for agent in all_available_agents])),
            "selection_criteria": {
                "min_relevance_score": selection_metadata.get("min_relevance_score", 0.3),
                "max_agents": selection_metadata.get("max_agents", 20)
            }
        }

        # Track automatic selection internally
        self.automatic_selection_span = {
            "span_id": f"selection_{self.workflow_id}",
            "active": True,
            "total_agents": len(all_available_agents),
            "metadata": selection_metadata
        }
        print(f"Started automatic selection span for {len(all_available_agents)} available agents")

    def log_loan_detection_step(self, loan_detection_result: Dict) -> None:
        """
        Log the loan detection step within the automatic selection span

        Args:
            loan_detection_result: Result from loan type detection
        """
        if not self.automatic_selection_span:
            print("Warning: No active automatic selection span for loan detection")
            return

        detection_input = "Document analysis for loan type classification"
        detection_output = {
            "loan_type": loan_detection_result.get("loan_type", "unknown"),
            "confidence": loan_detection_result.get("confidence", 0.0),
            "characteristics": loan_detection_result.get("characteristics", [])
        }

        # Track loan detection internally
        print(f"Logged loan detection: {loan_detection_result.get('loan_type', 'unknown')} (confidence: {loan_detection_result.get('confidence', 0.0)})")

    def log_agent_scoring_step(self, all_available_agents: List[Dict], selected_agents: List[Dict]) -> None:
        """
        Log the agent scoring and selection step within the automatic selection span

        Args:
            all_available_agents: All agents that were evaluated
            selected_agents: Agents that were selected based on scoring
        """
        if not self.automatic_selection_span:
            print("Warning: No active automatic selection span for agent scoring")
            return

        scoring_input = {
            "agents_to_evaluate": [
                {
                    "agent_id": agent.get('agent_id'),
                    "agent_name": agent.get('agent_name'),
                    "agent_type": agent.get('display_type')
                }
                for agent in all_available_agents
            ]
        }

        scoring_output = {
            "selected_agents": [
                {
                    "agent_id": agent.get('agent_id'),
                    "agent_name": agent.get('agent_name'),
                    "agent_type": agent.get('display_type'),
                    "relevance_score": agent.get('relevance_score', 0.0),
                    "selection_reason": agent.get('selection_reason', 'automatically selected')
                }
                for agent in selected_agents
            ],
            "selection_count": len(selected_agents),
            "total_evaluated": len(all_available_agents)
        }

        if PROMPTQUALITY_AVAILABLE and hasattr(self.automatic_selection_span, 'add_llm'):
            try:
                self.automatic_selection_span.add_llm(
                    input=json.dumps(scoring_input, indent=2),
                    output=json.dumps(scoring_output, indent=2),
                    model="gpt-4",
                    metadata={
                        "step_type": "agent_scoring",
                        "agent_name": "AgentScorer",
                        "total_evaluated": str(len(all_available_agents)),
                        "selected_count": str(len(selected_agents))
                    }
                )
                print(f"Logged agent scoring: {len(selected_agents)} agents selected from {len(all_available_agents)} evaluated")
            except Exception as e:
                print(f"Error logging agent scoring: {e}")

    def complete_automatic_selection_span(self, selected_agents: List[Dict]) -> None:
        """
        Complete the automatic selection span with final results

        Args:
            selected_agents: Final list of selected agents
        """
        if not self.automatic_selection_span:
            print("Warning: No active automatic selection span to complete")
            return

        final_output = {
            "selected_agents": [
                {
                    "agent_id": agent.get('agent_id'),
                    "agent_name": agent.get('agent_name'),
                    "agent_type": agent.get('display_type')
                }
                for agent in selected_agents
            ],
            "total_selected": len(selected_agents)
        }

        if PROMPTQUALITY_AVAILABLE and hasattr(self.automatic_selection_span, 'conclude'):
            try:
                self.automatic_selection_span.conclude(
                    output=json.dumps(final_output, indent=2)
                )
                print(f"Completed automatic selection span with {len(selected_agents)} agents selected")
                self.automatic_selection_span = None  # Reset the span
            except Exception as e:
                print(f"Error completing automatic selection span: {e}")

    def start_agent_execution_span(self) -> None:
        """
        Start a hierarchical workflow span for individual agent executions
        """
        if not self.current_workflow:
            print("Warning: No active workflow to start agent execution span")
            return

        execution_input = "Execute selected agents for compliance checking"

        if PROMPTQUALITY_AVAILABLE and hasattr(self.current_workflow, 'add_sub_workflow'):
            try:
                # Create a sub-workflow for agent execution
                self.agent_execution_span = self.current_workflow.add_sub_workflow(
                    input=execution_input,
                    name="Agent Execution",
                    metadata={
                        "span_type": "agent_execution",
                        "workflow_phase": "execution"
                    }
                )
                print("Started agent execution span")
            except Exception as e:
                print(f"Error starting agent execution span: {e}")
        else:
            print("Agent Execution Span: Started (promptquality not available)")

    def log_automatic_agent_selector(self, document_content: str, all_available_agents: List[Dict],
                                    loan_detection_result: Dict, selected_agents: List[Dict],
                                    selection_metadata: Optional[Dict] = None) -> None:
        """
        Log the automatic agent selector as its own agent step

        Args:
            document_content: Document content being analyzed
            all_available_agents: All agents available for selection
            loan_detection_result: Result from loan type detection
            selected_agents: Agents selected by the automatic selector
            selection_metadata: Additional metadata about the selection process
        """
        if not self.current_workflow:
            print("Warning: No active workflow to log automatic agent selector")
            return

        # Prepare input data for the automatic selector agent
        selector_input = {
            "document_summary": document_content[:500] + "..." if len(document_content) > 500 else document_content,
            "total_available_agents": len(all_available_agents),
            "available_agent_types": list(set([agent.get('display_type', 'unknown') for agent in all_available_agents])),
            "loan_detection": loan_detection_result,
            "selection_criteria": {
                "min_relevance_score": selection_metadata.get("min_relevance_score", 0.3),
                "max_agents": selection_metadata.get("max_agents", 20)
            }
        }

        # Prepare output data from the automatic selector
        selector_output = {
            "selected_agents": [
                {
                    "agent_id": agent.get('agent_id'),
                    "agent_name": agent.get('agent_name'),
                    "agent_type": agent.get('display_type'),
                    "relevance_score": agent.get('relevance_score', 0.0),
                    "selection_reason": agent.get('selection_reason', 'automatically selected')
                }
                for agent in selected_agents
            ],
            "selection_count": len(selected_agents),
            "loan_type_detected": loan_detection_result.get("loan_type", "unknown"),
            "confidence": loan_detection_result.get("confidence", 0.0),
            "selection_metadata": selection_metadata or {}
        }

        if PROMPTQUALITY_AVAILABLE and hasattr(self.current_workflow, 'add_llm'):
            try:
                self.current_workflow.add_llm(
                    input=json.dumps(selector_input, indent=2),
                    output=json.dumps(selector_output, indent=2),
                    model="gpt-4",
                    metadata={
                        "step_type": "automatic_agent_selector",
                        "workflow_phase": "selection",
                        "agent_name": "AutomaticAgentSelector",
                        "total_available": str(len(all_available_agents)),
                        "selected_count": str(len(selected_agents)),
                        "loan_type": str(loan_detection_result.get("loan_type", "unknown")),
                        "detection_confidence": str(loan_detection_result.get("confidence", 0.0))
                    }
                )
                print(f"Logged automatic agent selector: {len(selected_agents)} agents selected from {len(all_available_agents)} available")
            except Exception as e:
                print(f"Error logging automatic agent selector: {e}")
        else:
            # Fallback logging
            print(f"Automatic Agent Selector: {len(selected_agents)} agents selected from {len(all_available_agents)} available")

    def log_agent_selection_phase(self, document_content: str, all_available_agents: List[Dict],
                                 selected_agents: List[Dict], selection_metadata: Optional[Dict] = None) -> None:
        """
        Log the agent selection phase of the workflow

        Args:
            document_content: Document content being analyzed
            all_available_agents: All agents that were available for selection
            selected_agents: Agents that were selected for execution
            selection_metadata: Additional metadata about the selection process
        """
        if not self.current_workflow:
            print("Warning: No active workflow to log agent selection")
            return

        # Prepare selection data
        selection_input = {
            "document_summary": document_content[:500] + "..." if len(document_content) > 500 else document_content,
            "total_available_agents": len(all_available_agents),
            "available_agent_types": list(set([agent.get('display_type', 'unknown') for agent in all_available_agents]))
        }

        selection_output = {
            "selected_agents": [
                {
                    "agent_id": agent.get('agent_id'),
                    "agent_name": agent.get('agent_name'),
                    "agent_type": agent.get('display_type'),
                    "priority": agent.get('priority')
                }
                for agent in selected_agents
            ],
            "selection_count": len(selected_agents),
            "selection_metadata": selection_metadata or {}
        }

        if PROMPTQUALITY_AVAILABLE and hasattr(self.current_workflow, 'add_llm'):
            try:
                self.current_workflow.add_llm(
                    input=json.dumps(selection_input, indent=2),
                    output=json.dumps(selection_output, indent=2),
                    model="gpt-4",
                    metadata={
                        "step_type": "agent_selection",
                        "workflow_phase": "selection",
                        "total_available": str(len(all_available_agents)),
                        "selected_count": str(len(selected_agents))
                    }
                )
                print(f"Logged agent selection: {len(selected_agents)} agents selected from {len(all_available_agents)} available")
            except Exception as e:
                print(f"Error logging agent selection: {e}")
        else:
            # Fallback logging
            print(f"Agent Selection Phase: {len(selected_agents)} agents selected from {len(all_available_agents)} available")

    def log_agent_execution(self, agent_config: Dict, agent_input_data: Dict,
                           agent_result: Dict, execution_metadata: Optional[Dict] = None) -> None:
        """
        Log individual agent execution within the agent execution span

        Args:
            agent_config: Configuration of the agent being executed
            agent_input_data: Input data provided to the agent
            agent_result: Result returned by the agent
            execution_metadata: Additional metadata about the execution
        """
        # Try to log to agent execution span first, fallback to main workflow
        target_span = self.agent_execution_span if self.agent_execution_span else self.current_workflow

        if not target_span:
            print("Warning: No active workflow or span to log agent execution")
            return

        agent_id = agent_config.get('agent_id', 'unknown')
        agent_name = agent_config.get('agent_name', 'Unknown Agent')

        # Prepare execution data
        execution_input = {
            "agent_config": {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "agent_type": agent_config.get('display_type'),
                "priority": agent_config.get('priority'),
                "data_fields": agent_config.get('data_fields', [])
            },
            "extracted_data": agent_input_data
        }

        execution_output = agent_result

        if PROMPTQUALITY_AVAILABLE and hasattr(target_span, 'add_llm'):
            try:
                target_span.add_llm(
                    input=json.dumps(execution_input, indent=2),
                    output=json.dumps(execution_output, indent=2),
                    model="gpt-4",
                    metadata={
                        "step_type": "agent_execution",
                        "workflow_phase": "execution",
                        "agent_id": str(agent_id),
                        "agent_name": str(agent_name),
                        "agent_type": str(agent_config.get('display_type', '')),
                        "agent_priority": str(agent_config.get('priority', '')),
                        "passed": str(execution_output.get('passed', False)),
                        "confidence": str(execution_output.get('confidence', 0.0))
                    }
                )
                span_location = "agent execution span" if self.agent_execution_span else "main workflow"
                print(f"Logged execution of agent {agent_id}: {agent_name} in {span_location}")
            except Exception as e:
                print(f"Error logging agent execution for {agent_id}: {e}")
        else:
            # Fallback logging
            status = "PASSED" if execution_output.get('passed', False) else "FAILED"
            print(f"Agent Execution: {agent_id} ({agent_name}) - {status}")

    def complete_agent_execution_span(self, execution_summary: Dict) -> None:
        """
        Complete the agent execution span with final results

        Args:
            execution_summary: Summary of all agent executions
        """
        if not self.agent_execution_span:
            print("Warning: No active agent execution span to complete")
            return

        if PROMPTQUALITY_AVAILABLE and hasattr(self.agent_execution_span, 'conclude'):
            try:
                self.agent_execution_span.conclude(
                    output=json.dumps(execution_summary, indent=2)
                )
                print(f"Completed agent execution span")
                self.agent_execution_span = None  # Reset the span
            except Exception as e:
                print(f"Error completing agent execution span: {e}")

    def log_overall_assessment(self, compliance_results: List[Dict], overall_assessment: Dict) -> None:
        """
        Log the overall compliance assessment

        Args:
            compliance_results: Results from all agent executions
            overall_assessment: Final overall assessment
        """
        if not self.current_workflow:
            print("Warning: No active workflow to log overall assessment")
            return

        # Prepare assessment data
        assessment_input = {
            "individual_results": [
                {
                    "agent_id": result.get('agent_id'),
                    "passed": result.get('passed'),
                    "confidence": result.get('confidence')
                }
                for result in compliance_results
            ],
            "total_checks": len(compliance_results)
        }

        assessment_output = overall_assessment

        if PROMPTQUALITY_AVAILABLE and hasattr(self.current_workflow, 'add_llm'):
            try:
                self.current_workflow.add_llm(
                    input=json.dumps(assessment_input, indent=2),
                    output=json.dumps(assessment_output, indent=2),
                    model="gpt-4",
                    metadata={
                        "step_type": "overall_assessment",
                        "workflow_phase": "assessment",
                        "total_agents": str(len(compliance_results)),
                        "passed_agents": str(sum(1 for r in compliance_results if r.get('passed', False))),
                        "overall_passed": str(overall_assessment.get('overall_compliance', False)),
                        "overall_confidence": str(overall_assessment.get('confidence_score', 0.0))
                    }
                )
                print(f"Logged overall assessment: {len(compliance_results)} agents processed")
            except Exception as e:
                print(f"Error logging overall assessment: {e}")
        else:
            # Fallback logging
            status = "COMPLIANT" if overall_assessment.get('overall_compliance', False) else "NON-COMPLIANT"
            print(f"Overall Assessment: {status} (based on {len(compliance_results)} agents)")

    def complete_workflow(self, final_result: Dict) -> None:
        """
        Complete the workflow with final results

        Args:
            final_result: Final result of the entire workflow
        """
        if not self.current_workflow:
            print("Warning: No active workflow to complete")
            return

        if PROMPTQUALITY_AVAILABLE and hasattr(self.current_workflow, 'conclude'):
            try:
                # Complete the workflow with final results
                self.current_workflow.conclude(
                    output=json.dumps(final_result, indent=2)
                )

                # Flush traces to ensure they are sent to Galileo
                if hasattr(self.galileo_client, 'flush_traces'):
                    self.galileo_client.flush_traces()

                print(f"Completed workflow: {self.workflow_id}")
            except Exception as e:
                print(f"Error completing workflow: {e}")
        else:
            # Fallback logging
            print(f"Workflow completed: {self.workflow_id}")

        # Reset current workflow
        self.current_workflow = None
        self.workflow_id = None

    def log_error(self, error_message: str, error_context: Optional[Dict] = None) -> None:
        """
        Log an error in the workflow

        Args:
            error_message: Description of the error
            error_context: Additional context about the error
        """
        if not self.current_workflow:
            print(f"Workflow Error: {error_message}")
            return

        if PROMPTQUALITY_AVAILABLE and hasattr(self.current_workflow, 'add_llm'):
            try:
                self.current_workflow.add_llm(
                    input=json.dumps({"error_context": error_context or {}}, indent=2),
                    output=f"ERROR: {error_message}",
                    model="gpt-4",
                    metadata={
                        "step_type": "error",
                        "error_message": error_message,
                        "error_time": str(time.time())
                    }
                )
                print(f"Logged workflow error: {error_message}")
            except Exception as e:
                print(f"Error logging workflow error: {e}")
        else:
            print(f"Workflow Error: {error_message}")


def get_agent_workflow_logger(project_name: str = "policy_compliance",
                             log_stream: str = "agent_workflows") -> GalileoAgentWorkflowLogger:
    """
    Factory function to get an agent workflow logger instance

    Args:
        project_name: Galileo project name
        log_stream: Galileo log stream name

    Returns:
        GalileoAgentWorkflowLogger instance
    """
    return GalileoAgentWorkflowLogger(project_name=project_name, log_stream=log_stream)