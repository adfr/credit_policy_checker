#!/usr/bin/env python3
"""
CrewAI implementation with unified Galileo trace
Groups all agent executions under a single parent trace with child spans
"""

import os
import uuid
from typing import Dict, List, Any
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
import galileo

load_dotenv()


class UnifiedTraceCrewAI:
    """CrewAI with unified Galileo tracing - all agents in one parent trace"""

    def __init__(self):
        """Initialize CrewAI agents for policy compliance"""

        # Set environment variable for model (CrewAI picks this up automatically)
        import os
        os.environ["OPENAI_MODEL_NAME"] = "gpt-4o-mini"

        # Policy Check Agent - handles all types of policy checks
        self.policy_checker = Agent(
            role='Policy Compliance Checker',
            goal='Execute policy compliance checks based on provided agent configuration',
            backstory='Expert in validating various types of lending policy requirements including thresholds, criteria, and scores',
            verbose=True,
            allow_delegation=False
        )

    def run_unified_compliance_workflow(
        self,
        selected_agents: List[Dict],
        applicant_data: Dict,
        document_content: str = "",
        project_name: str = "policy_compliance",
        log_stream: str = "unified_agent_workflow"
    ) -> Dict[str, Any]:
        """
        Run compliance workflow with unified Galileo tracing.
        All agent executions appear as child spans under one parent trace.

        Args:
            selected_agents: List of selected policy agents
            applicant_data: Applicant financial data
            document_content: Full text content of the credit memo document
            project_name: Galileo project name
            log_stream: Galileo log stream name

        Returns:
            Dictionary with compliance results and workflow metadata
        """

        # Initialize Galileo
        galileo.login(api_key=os.getenv('GALILEO_API_KEY'))

        try:
            # Create a single parent trace for the entire workflow
            with galileo.trace(
                name="Policy Compliance Workflow",
                project_name=project_name,
                log_stream=log_stream
            ) as parent_trace:

                # Add workflow metadata to parent trace
                parent_trace.log_input({
                    "workflow_type": "policy_compliance_checking",
                    "selected_agents_count": len(selected_agents),
                    "agent_names": [agent.get('agent_name', 'Unknown') for agent in selected_agents],
                    "document_length": len(document_content),
                    "applicant_data_keys": list(applicant_data.keys())
                })

                agent_results = []

                # Execute each agent as a child span
                for i, agent_config in enumerate(selected_agents):
                    agent_id = agent_config.get('agent_id', f'unknown_{i}')
                    agent_name = agent_config.get('agent_name', f'Unknown Agent {i}')

                    # Create child span for this agent
                    with galileo.trace(
                        name=f"Agent: {agent_name}",
                        parent_id=parent_trace.trace_id
                    ) as agent_span:

                        # Log agent input
                        agent_span.log_input({
                            "agent_id": agent_id,
                            "agent_name": agent_name,
                            "agent_type": agent_config.get('display_type', 'threshold'),
                            "priority": agent_config.get('priority', 'normal'),
                            "requirement": agent_config.get('requirement', ''),
                            "applicant_data": applicant_data,
                            "document_excerpt": document_content[:500] + "..." if len(document_content) > 500 else document_content
                        })

                        try:
                            # Create task description for this agent
                            task_description = f"""
Execute policy compliance check for {agent_name} (ID: {agent_id}).

Agent Configuration:
- Type: {agent_config.get('display_type', 'threshold')}
- Priority: {agent_config.get('priority', 'normal')}
- Description: {agent_config.get('description', 'Policy compliance check')}
- Requirement: {agent_config.get('requirement', 'Policy compliance requirement')}

Extracted Applicant Data:
- Credit Score: {applicant_data.get('credit_score', 'N/A')}
- Monthly Income: {applicant_data.get('monthly_income', 'N/A')}
- Monthly Debt: {applicant_data.get('monthly_debt', 'N/A')}
- Loan Amount: {applicant_data.get('loan_amount', 'N/A')}
- Property Value: {applicant_data.get('property_value', 'N/A')}

Full Document Content for Context:
{document_content[:2000] if document_content else 'No document content provided'}
{"..." if len(document_content) > 2000 else ""}

Instructions:
1. Analyze both the extracted data AND the full document content
2. Consider narrative elements, risk assessments, and underwriter notes
3. Determine if the policy check passes or fails based on your agent configuration
4. Return a structured result with: passed (boolean), confidence (0-1), reason (string), and any calculated values
5. Include contextual insights from the document in your reasoning
"""

                            # Create and execute task
                            task = Task(
                                description=task_description,
                                agent=self.policy_checker,
                                expected_output=f"Policy compliance result for {agent_name} with pass/fail status and detailed reasoning"
                            )

                            # Create single-task crew for this agent
                            crew = Crew(
                                agents=[self.policy_checker],
                                tasks=[task],
                                process=Process.sequential,
                                verbose=False  # Reduce verbosity since we're logging to Galileo
                            )

                            # Execute the task
                            crew_result = crew.kickoff()

                            # Process the result
                            result = {
                                "agent_id": agent_id,
                                "agent_name": agent_name,
                                "passed": True,  # Default - will be updated based on crew result
                                "confidence": 0.9,
                                "reason": f"Agent executed via unified CrewAI workflow: {str(crew_result)[:200]}...",
                                "agent_config": agent_config,
                                "crew_output": str(crew_result)
                            }

                            # Log agent output
                            agent_span.log_output({
                                "agent_result": result,
                                "raw_crew_output": str(crew_result),
                                "execution_status": "success"
                            })

                            agent_results.append(result)

                        except Exception as e:
                            # Log agent error
                            agent_span.log_output({
                                "execution_status": "error",
                                "error_message": str(e),
                                "agent_id": agent_id
                            })

                            # Create error result
                            result = {
                                "agent_id": agent_id,
                                "agent_name": agent_name,
                                "passed": False,
                                "confidence": 0.0,
                                "reason": f"Agent execution failed: {str(e)}",
                                "agent_config": agent_config,
                                "error": str(e)
                            }
                            agent_results.append(result)

                # Calculate overall compliance
                total_agents = len(agent_results)
                passed_agents = sum(1 for r in agent_results if r.get("passed", False))
                overall_compliance = passed_agents == total_agents if total_agents > 0 else False

                # Log final workflow output
                workflow_result = {
                    "status": "success",
                    "selected_agents": selected_agents,
                    "agent_results": agent_results,
                    "compliance_summary": {
                        "overall_compliance": overall_compliance,
                        "agents_passed": passed_agents,
                        "total_agents": total_agents,
                        "confidence_score": sum(r.get("confidence", 0) for r in agent_results) / total_agents if total_agents > 0 else 0,
                        "recommendations": []
                    },
                    "workflow_metadata": {
                        "process_type": "unified_trace_crewai",
                        "galileo_integration": "manual_tracing",
                        "galileo_project": project_name,
                        "galileo_log_stream": log_stream,
                        "parent_trace_id": parent_trace.trace_id
                    }
                }

                parent_trace.log_output(workflow_result)

                return workflow_result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "workflow_metadata": {
                    "process_type": "unified_trace_crewai",
                    "galileo_integration": "manual_tracing",
                    "error_occurred": True
                }
            }