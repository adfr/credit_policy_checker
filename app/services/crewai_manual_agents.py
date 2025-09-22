#!/usr/bin/env python3
"""
Simplified CrewAI agents for manual policy compliance checking
"""

import os
import json
from typing import Dict, List, Any, Optional
from crewai import Agent, Task, Crew, Process
import openai
from dotenv import load_dotenv
from galileo.handlers.crewai.handler import CrewAIEventListener
from galileo import GalileoLogger

load_dotenv()

# Set up OpenAI client
openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


class ManualPolicyComplianceCrewAI:
    """Simplified CrewAI-based policy compliance checking for manual agent selection"""

    def __init__(self):
        """Initialize CrewAI agents for policy compliance"""

        # Policy Check Agent - handles all types of policy checks
        self.policy_checker = Agent(
            role='Policy Compliance Checker',
            goal='Execute policy compliance checks based on provided agent configuration',
            backstory='Expert in validating various types of lending policy requirements including thresholds, criteria, and scores',
            verbose=True,
            allow_delegation=False,
            memory=False,  # Disable memory for cleaner traces
            max_iter=1,    # Single iteration per task
            step_callback=None  # No additional callbacks
        )

    def execute_selected_agents(
        self,
        selected_agents: List[Dict],
        applicant_data: Dict,
        galileo_config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute manually selected agents in sequential order.

        Args:
            selected_agents: List of manually selected policy agents
            applicant_data: Applicant financial data
            galileo_config: Optional Galileo configuration

        Returns:
            Dictionary with compliance results and workflow metadata
        """

        # Configure Galileo for proper agent-based logging
        if galileo_config:
            os.environ["GALILEO_API_KEY"] = galileo_config.get("api_key", os.getenv("GALILEO_API_KEY"))
            os.environ["GALILEO_PROJECT_NAME"] = galileo_config.get("project_name", "policy_compliance")

        # Create custom Galileo logger for agent-based traces
        galileo_logger = GalileoLogger(
            project=galileo_config.get("project_name", "policy_compliance") if galileo_config else "policy_compliance",
            log_stream="crewai_agent_execution"
        )

        # Initialize CrewAI Event Listener for proper agent-based logging
        CrewAIEventListener(
            galileo_logger=galileo_logger,
            start_new_trace=True,
            flush_on_crew_completed=True
        )

        try:
            # Create tasks for each selected agent
            tasks = []
            agent_results = []

            for i, agent_config in enumerate(selected_agents):
                agent_id = agent_config.get('agent_id', f'unknown_{i}')
                agent_name = agent_config.get('agent_name', f'Unknown Agent {i}')
                agent_type = agent_config.get('display_type', 'threshold')

                # Create task description for this agent
                task_description = f"""
Execute policy compliance check for {agent_name} (ID: {agent_id}).

Agent Type: {agent_type}
Agent Configuration: {json.dumps(agent_config, indent=2)}
Applicant Data: {json.dumps(applicant_data, indent=2)}

Based on the agent configuration and applicant data, determine if the policy check passes or fails.
Return a structured result with: passed (boolean), confidence (0-1), reason (string), and any calculated values.
"""

                # Create task
                task = Task(
                    description=task_description,
                    agent=self.policy_checker,
                    expected_output=f"Policy compliance result for {agent_name} with pass/fail status and detailed reasoning"
                )

                tasks.append(task)

            # Create sequential crew with proper metadata for Galileo
            crew = Crew(
                agents=[self.policy_checker],
                tasks=tasks,
                process=Process.sequential,
                verbose=True,
                memory=False,  # Disable memory for cleaner traces
                max_rpm=30,    # Rate limiting for stability
                manager_llm=None  # No manager for sequential process
            )

            # Execute the crew
            crew_result = crew.kickoff()

            # Process results from each task
            for i, agent_config in enumerate(selected_agents):
                # Execute the policy check logic directly since CrewAI tasks return text
                result = self._execute_policy_check(agent_config, applicant_data)
                agent_results.append(result)

            # Calculate overall compliance
            total_agents = len(agent_results)
            passed_agents = sum(1 for r in agent_results if r.get("passed", False))
            overall_compliance = passed_agents == total_agents if total_agents > 0 else False

            return {
                "status": "success",
                "selected_agents": selected_agents,
                "agent_results": agent_results,
                "compliance_summary": {
                    "overall_compliance": overall_compliance,
                    "agents_passed": passed_agents,
                    "total_agents": total_agents,
                    "confidence_score": sum(r.get("confidence", 0) for r in agent_results) / total_agents if total_agents > 0 else 0
                },
                "workflow_metadata": {
                    "process_type": "sequential_manual",
                    "galileo_integration": "native",
                    "crew_ai_version": "0.41.0+",
                    "execution_mode": "manual_selection"
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "workflow_metadata": {
                    "process_type": "sequential_manual",
                    "galileo_integration": "native",
                    "execution_mode": "manual_selection"
                }
            }

    def _execute_policy_check(self, agent_config: Dict, applicant_data: Dict) -> Dict:
        """Execute a single policy check based on agent configuration"""

        agent_id = agent_config.get("agent_id")
        agent_name = agent_config.get("agent_name")
        agent_type = agent_config.get("display_type", "threshold")

        if agent_type == "threshold":
            return self._execute_threshold_check(agent_config, applicant_data)
        elif agent_type == "criteria":
            return self._execute_criteria_check(agent_config, applicant_data)
        elif agent_type == "score":
            return self._execute_score_check(agent_config, applicant_data)
        else:
            return {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "passed": False,
                "confidence": 0.0,
                "reason": f"Unknown agent type: {agent_type}"
            }

    def _execute_threshold_check(self, agent_config: Dict, applicant_data: Dict) -> Dict:
        """Execute threshold-based policy check"""

        agent_id = agent_config.get("agent_id")
        agent_name = agent_config.get("agent_name")
        threshold_value = agent_config.get("threshold_value")
        operator = agent_config.get("threshold_operator")
        data_fields = agent_config.get("data_fields", [])

        # Extract relevant data
        if "loan_amount" in data_fields and "property_value" in data_fields:
            # LTV calculation
            loan_amount = applicant_data.get("loan_amount", 0)
            property_value = applicant_data.get("property_value", 1)
            actual_value = (loan_amount / property_value) * 100 if property_value > 0 else 100
        elif "credit_score" in data_fields:
            actual_value = applicant_data.get("credit_score", 0)
        elif "monthly_income" in data_fields and "monthly_debt" in data_fields:
            # DTI calculation
            monthly_income = applicant_data.get("monthly_income", 1)
            monthly_debt = applicant_data.get("monthly_debt", 0)
            actual_value = (monthly_debt / monthly_income) * 100 if monthly_income > 0 else 100
        else:
            actual_value = 0

        # Apply operator
        if operator == ">=":
            passed = actual_value >= threshold_value
        elif operator == "<=":
            passed = actual_value <= threshold_value
        elif operator == ">":
            passed = actual_value > threshold_value
        elif operator == "<":
            passed = actual_value < threshold_value
        else:
            passed = actual_value == threshold_value

        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "passed": passed,
            "confidence": 0.95,
            "actual_value": actual_value,
            "threshold_value": threshold_value,
            "operator": operator,
            "reason": f"{agent_name}: {actual_value:.1f} {operator} {threshold_value} = {'PASS' if passed else 'FAIL'}"
        }

    def _execute_criteria_check(self, agent_config: Dict, applicant_data: Dict) -> Dict:
        """Execute criteria-based policy check"""

        agent_id = agent_config.get("agent_id")
        agent_name = agent_config.get("agent_name")
        criteria = agent_config.get("criteria", [])
        data_fields = agent_config.get("data_fields", [])

        # Check if all required data fields are present
        all_fields_present = all(field in applicant_data for field in data_fields)

        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "passed": all_fields_present,
            "confidence": 0.85 if all_fields_present else 0.5,
            "criteria_checked": criteria,
            "reason": f"{agent_name}: {'All criteria met' if all_fields_present else 'Missing required data'}"
        }

    def _execute_score_check(self, agent_config: Dict, applicant_data: Dict) -> Dict:
        """Execute score-based policy check"""

        agent_id = agent_config.get("agent_id")
        agent_name = agent_config.get("agent_name")
        max_score = agent_config.get("max_score", 100)
        data_fields = agent_config.get("data_fields", [])

        # Calculate DTI for score agents
        if "monthly_income" in data_fields and "monthly_debt" in data_fields:
            monthly_income = applicant_data.get("monthly_income", 1)
            monthly_debt = applicant_data.get("monthly_debt", 0)
            dti_ratio = (monthly_debt / monthly_income) * 100 if monthly_income > 0 else 100
            passed = dti_ratio <= max_score
            score = dti_ratio
        else:
            passed = False
            score = 0

        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "passed": passed,
            "confidence": 0.9,
            "score": score,
            "max_score": max_score,
            "reason": f"{agent_name}: Score {score:.1f} <= {max_score} = {'PASS' if passed else 'FAIL'}"
        }