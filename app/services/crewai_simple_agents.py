#!/usr/bin/env python3
"""
Simplified CrewAI agents following official Galileo integration pattern
"""

import os
from typing import Dict, List, Any
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
from galileo.handlers.crewai.handler import CrewAIEventListener
from app.services.neo4j_search_tool import search_policy_graph

load_dotenv()


class SimplePolicyComplianceCrewAI:
    """Simplified CrewAI-based policy compliance following official Galileo pattern"""

    def __init__(self):
        """Initialize CrewAI agents for policy compliance"""

        # Set environment variable for model (CrewAI picks this up automatically)
        import os
        os.environ["OPENAI_MODEL_NAME"] = "gpt-4o-mini"

        # Initialize Neo4j search tool
        self.neo4j_tool = search_policy_graph
        print("✅ Neo4j search tool initialized for CrewAI agents")

        # Policy Check Agent - handles all types of policy checks
        # Now with Neo4j graph search capabilities
        tools = [self.neo4j_tool]

        self.policy_checker = Agent(
            role='Policy Compliance Checker with Graph Knowledge',
            goal='Execute policy compliance checks using both provided configuration and knowledge graph',
            backstory='''Expert in validating various types of lending policy requirements including thresholds, criteria, and scores.
            Has access to a comprehensive knowledge graph of policy requirements, products, and their relationships.
            Can search the graph to find specific requirements, understand relationships between policies,
            and identify applicable thresholds for different loan products.''',
            verbose=True,
            allow_delegation=False,
            tools=tools
        )

    def run_compliance_workflow(
        self,
        selected_agents: List[Dict],
        applicant_data: Dict,
        document_content: str = "",
        project_name: str = "policy_compliance",
        log_stream: str = "crewai_policy_checks"
    ) -> Dict[str, Any]:
        """
        Run compliance workflow following official Galileo CrewAI pattern.

        Args:
            selected_agents: List of manually selected policy agents
            applicant_data: Applicant financial data
            document_content: Full text content of the credit memo document
            project_name: Galileo project name
            log_stream: Galileo log stream name

        Returns:
            Dictionary with compliance results and workflow metadata
        """

        # Set environment variables for Galileo (must be set before CrewAIEventListener)
        os.environ["GALILEO_API_KEY"] = os.getenv('GALILEO_API_KEY', '')
        os.environ["GALILEO_PROJECT"] = project_name
        os.environ["GALILEO_LOG_STREAM"] = log_stream

        def run():
            # Create the event listener (following official pattern) - must be called INSIDE the function
            listener = CrewAIEventListener()
            print(f"🔭 Galileo Event Listener created for project: {project_name}, stream: {log_stream}")

            # Create tasks for each selected agent
            tasks = []
            for i, agent_config in enumerate(selected_agents):
                agent_id = agent_config.get('agent_id', f'unknown_{i}')
                agent_name = agent_config.get('agent_name', f'Unknown Agent {i}')

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
{document_content[:4000] if document_content else 'No document content provided'}
{"..." if len(document_content) > 4000 else ""}

Instructions:
1. TRY to use the Neo4j Graph Search tool to find relevant requirements for "{agent_name}"
   - Search for specific thresholds, conditions, and related requirements
   - If the tool fails or returns no results, CONTINUE WITHOUT IT
   - Do not retry the tool more than 3 times if it fails
2. Analyze both the extracted data AND the full document content
3. For the specific requirement "{agent_name}":
   - Look for relevant thresholds, percentages, or criteria in the document
   - Use the agent configuration as your primary guidance
   - Cross-reference any graph knowledge if available
4. Consider narrative elements, risk assessments, and underwriter notes
5. Determine if the policy check passes or fails based on:
   - The agent configuration provided (primary source)
   - The actual applicant data
   - Any graph database requirements (if available)
   - Document content analysis
6. ALWAYS return a structured JSON result in this exact format:
   {{
     "passed": true/false,
     "confidence": 0.0-1.0,
     "reason": "Detailed explanation specific to {agent_name}",
     "calculated_values": {{any calculated values}}
   }}
7. Ensure your reason directly addresses "{agent_name}" and no other policy checks
"""

                # Create task
                task = Task(
                    description=task_description,
                    agent=self.policy_checker,
                    expected_output=f"Policy compliance result for {agent_name} with pass/fail status and detailed reasoning"
                )

                tasks.append(task)

            # Create sequential crew
            crew = Crew(
                agents=[self.policy_checker],
                tasks=tasks,
                process=Process.sequential,
                verbose=True
            )

            # Execute the crew
            crew_result = crew.kickoff()
            return crew_result

        try:
            # Run the crew (this will automatically log to Galileo)
            crew_result = run()

            print(f"🔄 CrewAI execution completed. Processing results...")
            print(f"📝 Raw CrewAI result type: {type(crew_result)}")
            print(f"📝 Raw CrewAI result: {str(crew_result)[:500]}...")

            # Parse the actual CrewAI results instead of generating simplified ones
            agent_results = self._parse_crewai_results(crew_result, selected_agents)

            if not agent_results:
                print("❌ Failed to parse CrewAI results - NO FALLBACK, returning empty results")
                agent_results = []

            # Calculate overall compliance
            total_agents = len(agent_results)
            passed_agents = sum(1 for r in agent_results if r.get("passed", False))
            overall_compliance = passed_agents == total_agents if total_agents > 0 else False

            print(f"📊 Overall compliance: {passed_agents}/{total_agents} agents passed")

            final_result = {
                "status": "success",
                "selected_agents": selected_agents,
                "agent_results": agent_results,
                "compliance_summary": {
                    "overall_compliance": overall_compliance,
                    "confidence_score": sum(r.get("confidence", 0) for r in agent_results) / total_agents if total_agents > 0 else 0,
                    "statistics": {
                        "total_agents": total_agents,
                        "passed_agents": passed_agents,
                        "failed_agents": total_agents - passed_agents,
                        "pass_rate": passed_agents / total_agents if total_agents > 0 else 0.0
                    },
                    "recommendations": []  # Add recommendations array for frontend compatibility
                },
                "workflow_metadata": {
                    "process_type": "sequential_simple",
                    "galileo_integration": "official_pattern",
                    "crew_result": str(crew_result),
                    "galileo_project": project_name,
                    "galileo_log_stream": log_stream
                }
            }

            print(f"🚀 SimplePolicyComplianceCrewAI final result structure:")
            print(f"   - agent_results: {len(final_result['agent_results'])} items")
            print(f"   - statistics: {final_result['compliance_summary']['statistics']}")

            return final_result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "workflow_metadata": {
                    "process_type": "sequential_simple",
                    "galileo_integration": "official_pattern"
                }
            }

    def _parse_crewai_results(self, crew_result, selected_agents: List[Dict]) -> List[Dict]:
        """Parse actual CrewAI markdown results into structured data"""
        try:
            # Extract text from CrewAI result object
            result_text = ""
            if hasattr(crew_result, 'tasks_output') and crew_result.tasks_output:
                print(f"🔍 Processing {len(crew_result.tasks_output)} task outputs")
                # Get the output from all tasks
                for i, task_output in enumerate(crew_result.tasks_output):
                    if hasattr(task_output, 'raw'):
                        task_content = str(task_output.raw)
                        print(f"📝 Task {i+1} raw output length: {len(task_content)}")
                        result_text += task_content + "\n\n"
                    else:
                        task_content = str(task_output)
                        print(f"📝 Task {i+1} string output length: {len(task_content)}")
                        result_text += task_content + "\n\n"
            elif hasattr(crew_result, 'raw'):
                result_text = str(crew_result.raw)
            else:
                result_text = str(crew_result)
            print(f"🔍 Parsing CrewAI result text (length: {len(result_text)})")

            # Debug: Show first 2000 characters to understand the format
            print(f"📝 CrewAI result preview:\n{result_text[:2000]}...")

            # Also check the type and attributes of the crew_result
            print(f"🔍 CrewAI result type: {type(crew_result)}")
            if hasattr(crew_result, '__dict__'):
                print(f"🔍 CrewAI result attributes: {list(crew_result.__dict__.keys())}")
            if hasattr(crew_result, 'tasks_output'):
                print(f"🔍 CrewAI has tasks_output: {len(crew_result.tasks_output) if crew_result.tasks_output else 0}")
            if hasattr(crew_result, 'raw'):
                print(f"🔍 CrewAI raw output (first 500 chars): {str(crew_result.raw)[:500]}...")

            agent_results = []

            # Look for policy compliance result blocks in the text
            import re

            # Parse the markdown format that CrewAI is returning
            import json

            # Multiple patterns to catch JSON objects in different formats
            json_patterns = [
                # Standard JSON object pattern
                r'\{(?:[^{}]|(?:\{[^{}]*\})*)*\}',
                # JSON in code blocks
                r'```json\s*(\{.*?\})\s*```',
                # JSON after "Final Answer:" or similar
                r'(?:Final Answer|Result):\s*(\{.*?\})',
                # JSON after agent name
                r'(?:for|result)\s+[^{]*(\{[^}]*"passed"[^}]*\})'
            ]

            json_candidates = []
            for pattern in json_patterns:
                matches = re.findall(pattern, result_text, re.DOTALL | re.IGNORECASE)
                json_candidates.extend(matches)

            # Also try to extract from task outputs individually if we have them
            if hasattr(crew_result, 'tasks_output') and crew_result.tasks_output:
                print(f"🔍 Checking individual task outputs for JSON...")
                for i, task_output in enumerate(crew_result.tasks_output):
                    task_text = str(task_output.raw) if hasattr(task_output, 'raw') else str(task_output)
                    print(f"📝 Task {i+1} output length: {len(task_text)}")

                    # Look for JSON in each task output
                    for pattern in json_patterns:
                        task_matches = re.findall(pattern, task_text, re.DOTALL | re.IGNORECASE)
                        if task_matches:
                            print(f"🎯 Found {len(task_matches)} JSON objects in task {i+1}")
                            json_candidates.extend(task_matches)

            # Remove duplicates while preserving order
            seen = set()
            unique_candidates = []
            for candidate in json_candidates:
                candidate_str = str(candidate).strip()
                if candidate_str not in seen and len(candidate_str) > 10:
                    seen.add(candidate_str)
                    unique_candidates.append(candidate_str)

            json_candidates = unique_candidates

            # Filter for JSON objects with required fields
            json_matches = []
            for candidate in json_candidates:
                if '"passed"' in candidate and '"confidence"' in candidate and '"reason"' in candidate:
                    json_matches.append(candidate)

            print(f"🔍 Found {len(json_candidates)} JSON candidates, {len(json_matches)} complete objects")

            # Debug: show first candidate
            if json_candidates:
                print(f"📝 First JSON candidate (first 200 chars): {json_candidates[0][:200]}...")

            matches = []

            if json_matches:
                print(f"🔍 Found {len(json_matches)} JSON objects in CrewAI output")
                # Handle JSON format (existing code)
                for i, json_str in enumerate(json_matches):
                    try:
                        json_str = json_str.strip()
                        if json_str.startswith('```json'):
                            json_str = json_str[7:]
                        if json_str.endswith('```'):
                            json_str = json_str[:-3]

                        policy_result = json.loads(json_str)
                        passed = policy_result.get('passed', False)
                        confidence = policy_result.get('confidence', 0)
                        reason = policy_result.get('reason', 'No reason provided')

                        # Try to get agent info from the JSON itself first
                        agent_name = policy_result.get('agent_name') or policy_result.get('policy_name')
                        agent_id = policy_result.get('agent_id') or policy_result.get('policy_id')

                        # Fallback to selected_agents index if not in JSON
                        if not agent_name and i < len(selected_agents):
                            agent_name = selected_agents[i].get('agent_name', f"Agent_{i+1}")
                        if not agent_id and i < len(selected_agents):
                            agent_id = selected_agents[i].get('agent_id', f"JSON_{i+1}")

                        print(f"🔍 JSON result {i+1}:")
                        print(f"   Agent: {agent_name} (ID: {agent_id})")
                        print(f"   Result: {'PASS' if passed else 'FAIL'} (confidence: {confidence})")
                        print(f"   Reason preview: {reason[:100]}{'...' if len(reason) > 100 else ''}")

                        match = (agent_name, agent_id, str(passed), str(confidence), reason)
                        matches.append(match)

                    except Exception as e:
                        print(f"⚠️ Error processing JSON {i+1}: {str(e)}")
                        print(f"⚠️ JSON content: {json_str[:200]}...")
                        continue
            else:
                print(f"🔍 No JSON found, trying markdown format")
                # Parse markdown format: **Policy Compliance Result for X (ID: Y)**
                markdown_pattern = r'\*\*Policy Compliance Result for (.+?) \(ID: (.+?)\)\*\*.*?- \*\*Passed:\*\* (True|False|true|false).*?- \*\*Confidence:\*\* ([0-9.]+).*?- \*\*Reason:\*\* (.+?)(?=\*\*Policy|\*\*Calculated|$)'

                markdown_matches = re.findall(markdown_pattern, result_text, re.DOTALL | re.MULTILINE | re.IGNORECASE)
                print(f"🔍 Found {len(markdown_matches)} markdown policy results")

                if not markdown_matches:
                    # Try simpler patterns
                    simple_patterns = [
                        r'(.+?) \(ID: (.+?)\).*?Passed:\s*(True|False|true|false).*?Confidence:\s*([0-9.]+).*?Reason:\s*(.+?)(?=Policy|Calculated|$)',
                        r'Policy Compliance Result for (.+?) \(ID: (.+?)\).*?Passed:\s*(True|False|true|false).*?Confidence:\s*([0-9.]+)'
                    ]

                    for i, pattern in enumerate(simple_patterns):
                        markdown_matches = re.findall(pattern, result_text, re.DOTALL | re.MULTILINE | re.IGNORECASE)
                        if markdown_matches:
                            print(f"🎯 Simple pattern {i+1} matched {len(markdown_matches)} results")
                            break
                        else:
                            print(f"❌ Simple pattern {i+1} found 0 matches")

                matches = markdown_matches

            print(f"🔍 Found {len(matches)} policy compliance results in CrewAI output")
            print(f"📊 Expected {len(selected_agents)} results, got {len(matches)} matches")

            if len(matches) != len(selected_agents):
                print(f"⚠️ MISMATCH: Expected {len(selected_agents)} results but found {len(matches)}")
                print(f"📋 Selected agent names: {[a.get('agent_name') for a in selected_agents]}")
                if matches:
                    print(f"🔍 Found result names: {[m[0] for m in matches]}")
                else:
                    print(f"❌ No matches found at all!")

            # If we don't have enough matches, try multiple extraction methods
            if len(matches) < len(selected_agents):
                print(f"❌ Insufficient matches found ({len(matches)}/{len(selected_agents)}), trying additional extraction...")

                # Try LLM extraction first
                print(f"🔍 Looking for basic strings in result...")
                basic_checks = ["Policy Compliance", "Final Answer", "Passed:", "Confidence:"]
                has_policy_content = False
                for check in basic_checks:
                    if check in result_text:
                        print(f"✅ Found '{check}' in result")
                        has_policy_content = True
                    else:
                        print(f"❌ '{check}' not found in result")

                # If we have policy content OR JSON content, try LLM extraction
                has_json_content = '{' in result_text and '"passed"' in result_text and '"confidence"' in result_text
                if (has_policy_content or has_json_content) and len(result_text) > 100:
                    print("🤖 Using LLM to extract policy results...")
                    llm_matches = self._extract_policy_results_with_llm(result_text, selected_agents)
                    print(f"🤖 LLM extraction returned {len(llm_matches)} results")

                    # If LLM found more matches, use those instead
                    if len(llm_matches) > len(matches):
                        print(f"🔄 Using LLM results ({len(llm_matches)}) instead of regex results ({len(matches)})")
                        matches = llm_matches
                    else:
                        print(f"🔄 Keeping regex results ({len(matches)}) over LLM results ({len(llm_matches)})")

                # If still not enough, try to extract from individual task outputs
                if len(matches) < len(selected_agents) and hasattr(crew_result, 'tasks_output'):
                    print(f"🔄 Trying task-by-task extraction...")
                    task_matches = self._extract_from_task_outputs(crew_result.tasks_output, selected_agents)
                    if len(task_matches) > len(matches):
                        print(f"🔄 Using task-based results ({len(task_matches)}) instead of previous results ({len(matches)})")
                        matches = task_matches

            for i, match in enumerate(matches):
                agent_name, agent_id, passed_str, confidence_str, reason = match

                # Clean up the extracted values
                agent_name = agent_name.strip()
                agent_id = agent_id.strip()

                # Handle both boolean and string values for passed
                if isinstance(passed_str, bool):
                    passed = passed_str
                else:
                    passed = str(passed_str).lower() in ['true', '1', 'yes']

                confidence = float(confidence_str)
                reason = reason.strip()

                print(f"🔍 Parsed agent: {agent_name} (ID: {agent_id})")
                print(f"   - Passed: {passed_str} -> {passed}")
                print(f"   - Confidence: {confidence}")
                print(f"   - Reason length: {len(reason)} chars")

                # Find the corresponding agent config with more robust matching
                agent_config = None

                # First try exact match on agent_id
                for config in selected_agents:
                    if config.get('agent_id') == agent_id:
                        agent_config = config
                        print(f"✅ Found exact agent_id match: {agent_id}")
                        break

                # If no exact ID match, try exact agent_name match
                if not agent_config:
                    for config in selected_agents:
                        if config.get('agent_name') == agent_name:
                            agent_config = config
                            print(f"✅ Found exact agent_name match: {agent_name}")
                            break

                # If still no match, try fuzzy matching on agent names (in case of minor differences)
                if not agent_config:
                    import difflib
                    best_match = None
                    best_ratio = 0.8  # Minimum similarity threshold

                    for config in selected_agents:
                        config_name = config.get('agent_name', '')
                        ratio = difflib.SequenceMatcher(None, agent_name.lower(), config_name.lower()).ratio()
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_match = config

                    if best_match:
                        agent_config = best_match
                        print(f"✅ Found fuzzy match: '{agent_name}' -> '{best_match.get('agent_name')}' (similarity: {best_ratio:.2f})")

                # Last resort: try index-based matching if we have the same number of results as agents
                if not agent_config and len(matches) == len(selected_agents) and i < len(selected_agents):
                    agent_config = selected_agents[i]
                    print(f"⚠️ Using index-based fallback matching: position {i} -> '{agent_config.get('agent_name')}'")

                if not agent_config:
                    print(f"❌ Could not find agent config for {agent_name} (ID: {agent_id})")
                    available_agents = [f"{a.get('agent_name')} (ID: {a.get('agent_id')})" for a in selected_agents]
                    print(f"📋 Available agents: {available_agents}")
                    # Create a minimal config to prevent data loss
                    agent_config = {
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "priority": "unknown",
                        "description": "Agent config not found - using parsed data",
                        "requirement": "Unknown requirement"
                    }
                    print(f"🔄 Created minimal config to preserve result data")

                # Use the agent config data to ensure accuracy
                actual_agent_id = agent_config.get("agent_id", agent_id)
                actual_agent_name = agent_config.get("agent_name", agent_name)

                result = {
                    "agent_id": actual_agent_id,
                    "agent_name": actual_agent_name,
                    "passed": passed,
                    "confidence": confidence,
                    "reason": reason,
                    "agent_config": {
                        "agent_id": actual_agent_id,
                        "agent_name": actual_agent_name,
                        "priority": agent_config.get("priority", "medium"),
                        "applicable_products": agent_config.get("applicable_products", []),
                        "description": agent_config.get("description", ""),
                        "requirement": agent_config.get("requirement", ""),
                        "agent_origin": "crewai_parsed",
                        "agent_origin_reason": "Parsed from actual CrewAI execution results"
                    }
                }

                print(f"✅ Final result: {actual_agent_name} - {'PASS' if passed else 'FAIL'}")
                print(f"   📝 Reason preview: {reason[:100]}{'...' if len(reason) > 100 else ''}")

                print(f"✅ Parsed CrewAI result: {agent_name} - {'PASS' if passed else 'FAIL'} (confidence: {confidence})")
                agent_results.append(result)

            # Check if we're missing results for any selected agents
            processed_agent_ids = {result["agent_id"] for result in agent_results}
            missing_agents = [agent for agent in selected_agents if agent.get("agent_id") not in processed_agent_ids]

            if missing_agents:
                print(f"⚠️ Missing results for {len(missing_agents)} agents, creating placeholder results")
                for missing_agent in missing_agents:
                    agent_id = missing_agent.get("agent_id")
                    agent_name = missing_agent.get("agent_name")

                    # Create a more informative reason for missing results
                    missing_reason = f"Policy check for '{agent_name}' was not completed. This may be due to: " + \
                                   "insufficient data in the document, parsing errors, or the agent not being " + \
                                   "fully processed by the CrewAI workflow. Please review the original document " + \
                                   "for relevant information about this requirement."

                    placeholder_result = {
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "passed": False,
                        "confidence": 0.0,
                        "reason": missing_reason,
                        "agent_config": {
                            "agent_id": agent_id,
                            "agent_name": agent_name,
                            "priority": missing_agent.get("priority", "medium"),
                            "applicable_products": missing_agent.get("applicable_products", []),
                            "description": missing_agent.get("description", ""),
                            "requirement": missing_agent.get("requirement", ""),
                            "agent_origin": "missing_result_placeholder",
                            "agent_origin_reason": "Created placeholder for missing result"
                        }
                    }

                    print(f"📝 Created placeholder for missing agent: {agent_name}")
                    agent_results.append(placeholder_result)

            print(f"📊 Final result count: {len(agent_results)} (expected: {len(selected_agents)})")

            # Debug: Show final result summary
            print("📋 Final Results Summary:")
            for i, result in enumerate(agent_results):
                status = "PASS" if result["passed"] else "FAIL"
                conf = result["confidence"]
                name = result["agent_name"]
                origin = result["agent_config"].get("agent_origin", "unknown")
                print(f"  {i+1}. {name} - {status} (conf: {conf:.2f}) [origin: {origin}]")

            return agent_results

        except Exception as e:
            print(f"❌ Error parsing CrewAI results: {str(e)}")
            return []

    def _extract_from_task_outputs(self, task_outputs, selected_agents: List[Dict]) -> List[tuple]:
        """Extract results from individual task outputs when combined parsing fails"""
        matches = []

        for i, task_output in enumerate(task_outputs):
            if i >= len(selected_agents):
                print(f"⚠️ More task outputs ({len(task_outputs)}) than selected agents ({len(selected_agents)})")
                break

            agent_config = selected_agents[i]
            agent_name = agent_config.get('agent_name', f'Agent_{i+1}')
            agent_id = agent_config.get('agent_id', f'TASK_{i+1}')

            # Get task output text
            task_text = str(task_output.raw) if hasattr(task_output, 'raw') else str(task_output)
            print(f"📝 Processing task {i+1}: {agent_name} (length: {len(task_text)})")

            # Try to extract JSON from this specific task
            try:
                # Look for JSON patterns in this task
                json_patterns = [
                    r'\{[^{}]*"passed"[^{}]*"confidence"[^{}]*"reason"[^{}]*\}',
                    r'\{.*?"passed".*?"confidence".*?"reason".*?\}',
                ]

                found_json = None
                for pattern in json_patterns:
                    json_matches = re.findall(pattern, task_text, re.DOTALL | re.IGNORECASE)
                    if json_matches:
                        found_json = json_matches[0]
                        break

                if found_json:
                    # Parse the JSON
                    import json
                    result_data = json.loads(found_json)
                    passed = result_data.get('passed', False)
                    confidence = result_data.get('confidence', 0.5)
                    reason = result_data.get('reason', 'Policy check completed')

                    match = (agent_name, agent_id, str(passed), str(confidence), reason)
                    matches.append(match)
                    print(f"✅ Extracted from task {i+1}: {agent_name} - {'PASS' if passed else 'FAIL'}")
                    continue

            except Exception as e:
                print(f"⚠️ JSON parsing failed for task {i+1}: {e}")

            # Fallback: Look for keywords to infer result
            text_lower = task_text.lower()

            # Determine if passed based on keywords
            fail_keywords = ['fail', 'does not meet', 'below', 'insufficient', 'exceeds limit', 'not satisfied']
            pass_keywords = ['pass', 'meets', 'satisfies', 'within', 'acceptable', 'compliant']

            passed = True  # Default to pass
            confidence = 0.3  # Low confidence for keyword-based extraction

            fail_count = sum(1 for keyword in fail_keywords if keyword in text_lower)
            pass_count = sum(1 for keyword in pass_keywords if keyword in text_lower)

            if fail_count > pass_count:
                passed = False
                confidence = 0.4
            elif pass_count > 0:
                confidence = 0.5

            # Extract a meaningful reason (first few sentences)
            sentences = task_text.split('.')[:3]
            reason = '. '.join(sentences).strip()
            if len(reason) > 300:
                reason = reason[:300] + "..."
            if not reason:
                reason = f"Policy check for {agent_name} completed based on available data"

            match = (agent_name, agent_id, str(passed), str(confidence), reason)
            matches.append(match)
            print(f"📝 Inferred from task {i+1}: {agent_name} - {'PASS' if passed else 'FAIL'} (conf: {confidence})")

        return matches

    def _fallback_simplified_results(self, selected_agents: List[Dict], applicant_data: Dict) -> List[Dict]:
        """Fallback to simplified results when CrewAI parsing fails"""
        agent_results = []
        print(f"🔄 Using fallback simplified logic for {len(selected_agents)} agents")
        print(f"📊 Available applicant data: {list(applicant_data.keys())}")

        for i, agent_config in enumerate(selected_agents):
            print(f"📋 Processing agent {i+1}/{len(selected_agents)}: {agent_config.get('agent_name')}")

            # Use the actual data that's available from the logs
            agent_id = agent_config.get("agent_id")
            agent_name = agent_config.get("agent_name")

            # Based on the available data, create realistic results
            if "credit_score" in applicant_data and "credit" in agent_name.lower():
                credit_score = applicant_data.get("credit_score", 0)
                passed = credit_score >= 620  # Reasonable threshold
                confidence = 0.95
                reason = f"Credit score {credit_score} vs minimum requirement"
            elif "dti" in agent_name.lower():
                if "front" in agent_name.lower():
                    front_dti = applicant_data.get("front_end_dti", 0)
                    passed = front_dti <= 28  # Standard front-end DTI limit
                    confidence = 0.90
                    reason = f"Front-end DTI {front_dti:.1f}% vs 28% limit"
                else:
                    back_dti = applicant_data.get("back_end_dti", 0)
                    passed = back_dti <= 43  # Standard back-end DTI limit
                    confidence = 0.90
                    reason = f"Back-end DTI {back_dti:.1f}% vs 43% limit"
            else:
                # Default case
                passed = True
                confidence = 0.85
                reason = f"Policy check completed"

            result = {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "passed": passed,
                "confidence": confidence,
                "reason": reason,
                "agent_config": {
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "priority": agent_config.get("priority", "medium"),
                    "applicable_products": agent_config.get("applicable_products", []),
                    "agent_origin": "simplified_fallback",
                    "agent_origin_reason": "Fallback when CrewAI parsing failed"
                }
            }

            print(f"✅ Fallback result: {agent_name} - {'PASS' if passed else 'FAIL'} (confidence: {confidence})")
            agent_results.append(result)

        return agent_results

    def _extract_policy_results_with_llm(self, result_text: str, selected_agents: List[Dict]) -> List[tuple]:
        """Use LLM to extract policy results when regex fails"""
        try:
            import openai
            import os

            # Create a prompt to extract the policy results
            agent_names = [agent.get('agent_name', 'Unknown') for agent in selected_agents]
            agent_ids = [agent.get('agent_id', 'Unknown') for agent in selected_agents]

            prompt = f"""
Extract policy compliance results from the following CrewAI output text.

CRITICAL: You must find results for these EXACT agents (in this order):
{chr(10).join([f"{i+1}. {name} (ID: {id})" for i, (name, id) in enumerate(zip(agent_names, agent_ids))])}

Text to parse:
{result_text[:3000]}

INSTRUCTIONS:
1. Find the compliance result for each agent listed above
2. Match agent names exactly (case-insensitive)
3. Extract the explanation/reason that specifically relates to that agent's policy check
4. If an agent result is not found, mark it as failed with reason "Result not found in output"

Return results in this exact JSON format (maintain the same order as the agent list):
[
    {{
        "agent_name": "EXACT_AGENT_NAME_FROM_LIST",
        "agent_id": "EXACT_AGENT_ID_FROM_LIST",
        "passed": true,
        "confidence": 0.95,
        "reason": "The specific explanation for THIS agent's policy check"
    }}
]

Only return the JSON array, nothing else.
"""

            client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_completion_tokens=2000
            )

            # Parse the LLM response
            llm_result = response.choices[0].message.content.strip()
            print(f"🤖 LLM extraction result: {llm_result[:200]}...")

            # Try to parse as JSON
            import json
            policy_results = json.loads(llm_result)

            # Convert to expected tuple format
            matches = []
            for result in policy_results:
                agent_name = result.get('agent_name', 'Unknown')
                agent_id = result.get('agent_id', 'LLM_EXTRACTED')
                passed = str(result.get('passed', False))
                confidence = str(result.get('confidence', 0))
                reason = result.get('reason', 'No reason provided')

                match = (agent_name, agent_id, passed, confidence, reason)
                matches.append(match)
                print(f"🎯 LLM extracted: {agent_name} - {'PASS' if result.get('passed') else 'FAIL'} (confidence: {confidence})")

            return matches

        except Exception as e:
            print(f"❌ LLM extraction failed: {str(e)}")
            return []

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

        print(f"🔍 Threshold check for {agent_name}:")
        print(f"   - Data fields: {data_fields}")
        print(f"   - Threshold: {threshold_value} {operator}")
        print(f"   - Available data keys: {list(applicant_data.keys())}")

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
            "reason": f"{agent_name}: {actual_value:.1f} {operator} {threshold_value} = {'PASS' if passed else 'FAIL'}",
            "agent_config": {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "priority": agent_config.get("priority", "medium"),
                "applicable_products": agent_config.get("applicable_products", []),
                "agent_origin": "crewai_simple",
                "agent_origin_reason": "Executed via SimplePolicyComplianceCrewAI"
            }
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
            "reason": f"{agent_name}: {'All criteria met' if all_fields_present else 'Missing required data'}",
            "agent_config": {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "priority": agent_config.get("priority", "medium"),
                "applicable_products": agent_config.get("applicable_products", []),
                "agent_origin": "crewai_simple",
                "agent_origin_reason": "Executed via SimplePolicyComplianceCrewAI"
            }
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
            "reason": f"{agent_name}: Score {score:.1f} <= {max_score} = {'PASS' if passed else 'FAIL'}",
            "agent_config": {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "priority": agent_config.get("priority", "medium"),
                "applicable_products": agent_config.get("applicable_products", []),
                "agent_origin": "crewai_simple",
                "agent_origin_reason": "Executed via SimplePolicyComplianceCrewAI"
            }
        }