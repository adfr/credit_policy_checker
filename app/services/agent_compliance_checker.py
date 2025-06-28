from typing import Dict, List, Optional
from agents.policy_agents import ThresholdAgent, CriteriaAgent, ScoreAgent, QualitativeAgent
from agents.agent_factory import AgentFactory
from agents.base_agent import GeneralAgent
import json
import concurrent.futures

class AgentComplianceChecker:
    """Agent-based compliance checker that uses selected policy agents to check document compliance"""
    
    def __init__(self):
        self.document_analyzer = GeneralAgent("document_analyzer")
        self.agent_factory = AgentFactory()
        
    def check_compliance(self, document_content: str, selected_agents: List[Dict], applicant_data: Optional[Dict] = None) -> Dict:
        """
        Check compliance using selected policy agents
        
        Args:
            document_content: Full text content of the document to check
            selected_agents: List of agent configurations selected by user
            applicant_data: Optional structured applicant data
            
        Returns:
            Comprehensive compliance report
        """
        
        # First, extract relevant data from the document
        extracted_data = self._extract_data_from_document(document_content, selected_agents)
        
        # Combine document data with any provided applicant data
        combined_data = self._combine_data_sources(extracted_data, applicant_data)
        
        # Run compliance checks using selected agents
        compliance_results = self._run_agent_checks(selected_agents, combined_data)
        
        # Generate overall compliance assessment
        overall_assessment = self._generate_overall_assessment(compliance_results, selected_agents)
        
        return {
            "compliance_summary": overall_assessment,
            "agent_results": compliance_results,
            "extracted_data": extracted_data,
            "data_sources": {
                "document_extraction": bool(extracted_data),
                "applicant_data_provided": bool(applicant_data),
                "total_data_points": len(combined_data)
            },
            "processing_status": "completed"
        }
    
    def _extract_data_from_document(self, document_content: str, selected_agents: List[Dict]) -> Dict:
        """Extract relevant data points from document based on agent requirements"""
        
        # Collect all data fields needed by the selected agents
        required_fields = set()
        for agent in selected_agents:
            required_fields.update(agent.get('data_fields', []))
        
        prompt = f"""
        You are a document data extraction expert. Extract specific data points from this document.
        
        DOCUMENT CONTENT:
        {document_content}
        
        REQUIRED DATA FIELDS:
        {list(required_fields)}
        
        INSTRUCTIONS:
        1. Scan the document for mentions of each required data field
        2. Extract exact values, numbers, percentages, dates, and text
        3. Look for synonyms and related terms (e.g., "income" might be "salary", "earnings")
        4. For numeric values, preserve the original format and unit
        5. For dates, extract in original format
        6. For text fields, extract relevant phrases or sentences
        7. If a field is not found, mark it as "not_found"
        8. Provide the context/location where each value was found
        
        Common financial document fields to look for:
        - loan_amount, property_value, ltv_ratio
        - fico_score, credit_score, credit_rating
        - income, employment_history, dti_ratio
        - down_payment, cash_reserves
        - property_type, occupancy_type
        - employment_start_date, years_employed
        - monthly_payment, debt_amounts
        
        Return JSON with extracted data:
        {{
            "extracted_fields": {{
                "field_name": {{
                    "value": "extracted_value",
                    "unit": "if applicable (%, $, years, etc.)",
                    "context": "surrounding text where found",
                    "confidence": 0.0-1.0,
                    "location": "approximate location in document"
                }}
            }},
            "missing_fields": ["list of fields not found"],
            "additional_data": {{
                "field_name": "any additional relevant data found"
            }},
            "document_type": "detected document type",
            "extraction_notes": "any important observations"
        }}
        
        Be thorough but precise. Extract actual values, not estimates.
        
        Return only JSON, no other text.
        """
        
        try:
            response = self.document_analyzer.process(prompt)
            
            # Handle case where response is already a JSON error string
            if isinstance(response, str) and response.strip().startswith('{"passed": false'):
                return {
                    '_extraction_error': 'LLM service error during document extraction',
                    '_extraction_metadata': {
                        'missing_fields': list(required_fields),
                        'document_type': 'unknown',
                        'extraction_notes': 'LLM service unavailable'
                    }
                }
            
            # Handle empty or None response
            if not response or not response.strip():
                return {
                    '_extraction_error': 'Empty response from document extraction',
                    '_extraction_metadata': {
                        'missing_fields': list(required_fields),
                        'document_type': 'unknown',
                        'extraction_notes': 'No data extracted'
                    }
                }
            
            result = json.loads(response)
            
            # Validate response structure
            if not isinstance(result, dict):
                return {
                    '_extraction_error': 'Invalid response structure from document extraction',
                    '_extraction_metadata': {
                        'missing_fields': list(required_fields),
                        'document_type': 'unknown',
                        'extraction_notes': 'Malformed extraction response'
                    }
                }
            
            # Flatten the extracted fields for easier access
            flattened_data = {}
            extracted_fields = result.get('extracted_fields', {})
            
            if isinstance(extracted_fields, dict):
                for field_name, field_info in extracted_fields.items():
                    if isinstance(field_info, dict):
                        flattened_data[field_name] = field_info.get('value')
                    else:
                        flattened_data[field_name] = field_info
            
            # Add additional data
            additional_data = result.get('additional_data', {})
            if isinstance(additional_data, dict):
                flattened_data.update(additional_data)
            
            # Store extraction metadata
            flattened_data['_extraction_metadata'] = {
                'missing_fields': result.get('missing_fields', []),
                'document_type': result.get('document_type', 'unknown'),
                'extraction_notes': result.get('extraction_notes', 'Extraction completed')
            }
            
            return flattened_data
            
        except json.JSONDecodeError as e:
            return {
                '_extraction_error': f'Failed to parse document extraction response: {str(e)}',
                '_extraction_metadata': {
                    'missing_fields': list(required_fields),
                    'document_type': 'unknown',
                    'extraction_notes': 'JSON parsing failed'
                }
            }
        except Exception as e:
            return {
                '_extraction_error': f'Unexpected error during document extraction: {str(e)}',
                '_extraction_metadata': {
                    'missing_fields': list(required_fields),
                    'document_type': 'unknown',
                    'extraction_notes': 'Extraction failed with unexpected error'
                }
            }
    
    def _combine_data_sources(self, document_data: Dict, applicant_data: Optional[Dict]) -> Dict:
        """Combine data from document extraction and provided applicant data"""
        
        combined_data = document_data.copy()
        
        if applicant_data:
            # Applicant data takes precedence over document extraction
            combined_data.update(applicant_data)
            
            # Track data sources
            combined_data['_data_sources'] = {
                'document_fields': list(document_data.keys()),
                'applicant_fields': list(applicant_data.keys()),
                'override_fields': [k for k in applicant_data.keys() if k in document_data]
            }
        
        return combined_data
    
    def _remove_duplicate_agents(self, selected_agents: List[Dict]) -> List[Dict]:
        """Remove duplicate agents based on agent_id and requirements"""
        seen_agents = {}
        unique_agents = []
        duplicates_removed = 0
        
        for agent in selected_agents:
            agent_id = agent.get('agent_id')
            requirement = agent.get('requirement', '')
            
            # Create a composite key for detecting duplicates
            composite_key = f"{agent_id}_{hash(requirement)}"
            
            if composite_key not in seen_agents:
                seen_agents[composite_key] = agent
                unique_agents.append(agent)
            else:
                duplicates_removed += 1
                # Log duplicate found (could be enhanced with actual logging)
                print(f"Duplicate agent detected and removed: {agent_id}")
        
        if duplicates_removed > 0:
            print(f"Removed {duplicates_removed} duplicate agents. {len(unique_agents)} unique agents remaining.")
        
        return unique_agents
    
    def _run_agent_checks(self, selected_agents: List[Dict], combined_data: Dict) -> List[Dict]:
        """Run compliance checks using selected agents in parallel"""
        
        # First, remove duplicate agents
        unique_agents = self._remove_duplicate_agents(selected_agents)
        
        results = []
        
        # Process agents in parallel for better performance
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_agent = {}
            
            for agent_config in unique_agents:
                # Create agent instance
                agent = self.agent_factory.create_agent(
                    agent_config.get('check_type', 'general'),
                    agent_config
                )
                
                # Submit check to executor
                future = executor.submit(agent.check, {}, combined_data)
                future_to_agent[future] = (agent_config, agent)
            
            # Collect results
            for future in concurrent.futures.as_completed(future_to_agent):
                agent_config, agent_instance = future_to_agent[future]
                try:
                    result = future.result()
                    
                    # Add agent metadata to result
                    result['agent_config'] = {
                        'agent_id': agent_config.get('agent_id'),
                        'agent_name': agent_config.get('agent_name'),
                        'priority': agent_config.get('priority'),
                        'applicable_products': agent_config.get('applicable_products', []),
                        'agent_origin': getattr(agent_instance, '_origin', 'unknown'),
                        'agent_origin_reason': getattr(agent_instance, '_origin_reason', 'No reason provided')
                    }
                    
                    results.append(result)
                    
                except Exception as e:
                    # Handle agent execution errors
                    error_result = {
                        'agent_id': agent_config.get('agent_id'),
                        'agent_type': agent_config.get('agent_type', 'unknown'),
                        'passed': False,
                        'reason': f'Agent execution error: {str(e)}',
                        'confidence': 0.0,
                        'error': True,
                        'agent_config': {
                            'agent_id': agent_config.get('agent_id'),
                            'agent_name': agent_config.get('agent_name'),
                            'priority': agent_config.get('priority'),
                            'agent_origin': getattr(agent_instance, '_origin', 'unknown'),
                            'agent_origin_reason': getattr(agent_instance, '_origin_reason', 'Error during execution')
                        }
                    }
                    results.append(error_result)
        
        return results
    
    def _generate_overall_assessment(self, compliance_results: List[Dict], selected_agents: List[Dict]) -> Dict:
        """Generate overall compliance assessment from agent results"""
        
        # Categorize results by priority and type
        critical_failures = []
        high_priority_failures = []
        warnings = []
        passed_checks = []
        
        total_agents = len(compliance_results)
        passed_agents = 0
        failed_agents = 0
        
        for result in compliance_results:
            agent_id = result.get('agent_id')
            priority = result.get('agent_config', {}).get('priority', 'medium')
            passed = result.get('passed', False)
            
            if passed:
                passed_checks.append(result)
                passed_agents += 1
            else:
                failed_agents += 1
                if priority == 'critical':
                    critical_failures.append(result)
                elif priority == 'high':
                    high_priority_failures.append(result)
                else:
                    warnings.append(result)
        
        # Determine overall status
        if critical_failures:
            overall_status = "FAIL_CRITICAL"
            overall_decision = "DENY"
        elif len(high_priority_failures) > 2:  # More than 2 high priority failures
            overall_status = "FAIL_HIGH_PRIORITY"
            overall_decision = "DENY"
        elif high_priority_failures:
            overall_status = "REVIEW_REQUIRED"
            overall_decision = "MANUAL_REVIEW"
        elif warnings:
            overall_status = "PASS_WITH_CONDITIONS"
            overall_decision = "APPROVE_WITH_CONDITIONS"
        else:
            overall_status = "PASS"
            overall_decision = "APPROVE"
        
        # Calculate confidence scores
        confidence_scores = [r.get('confidence', 0.0) for r in compliance_results if 'confidence' in r]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        return {
            "overall_status": overall_status,
            "decision": overall_decision,
            "confidence_score": avg_confidence,
            "statistics": {
                "total_agents": total_agents,
                "passed_agents": passed_agents,
                "failed_agents": failed_agents,
                "pass_rate": passed_agents / total_agents if total_agents > 0 else 0.0
            },
            "failure_breakdown": {
                "critical_failures": len(critical_failures),
                "high_priority_failures": len(high_priority_failures),
                "warnings": len(warnings)
            },
            "critical_issues": [
                {
                    "agent_id": r.get('agent_id'),
                    "agent_name": r.get('agent_config', {}).get('agent_name'),
                    "reason": r.get('reason')
                }
                for r in critical_failures
            ],
            "recommendations": self._generate_recommendations(critical_failures, high_priority_failures, warnings),
            "next_steps": self._generate_next_steps(overall_decision, critical_failures, high_priority_failures)
        }
    
    def _generate_recommendations(self, critical_failures: List[Dict], high_priority_failures: List[Dict], warnings: List[Dict]) -> List[str]:
        """Generate recommendations based on failure patterns"""
        
        recommendations = []
        
        if critical_failures:
            recommendations.append("Address all critical policy violations before proceeding")
            
            # Specific recommendations for common critical failures
            for failure in critical_failures:
                agent_type = failure.get('agent_type')
                if agent_type == 'threshold':
                    recommendations.append(f"Review threshold calculations for {failure.get('agent_id')}")
                elif agent_type == 'criteria':
                    recommendations.append(f"Obtain required documentation for {failure.get('agent_id')}")
        
        if high_priority_failures:
            recommendations.append("Review high-priority policy requirements")
            
            if len(high_priority_failures) > 1:
                recommendations.append("Consider if compensating factors can address multiple issues")
        
        if warnings:
            recommendations.append("Monitor warning conditions during loan lifecycle")
        
        return recommendations
    
    def _generate_next_steps(self, decision: str, critical_failures: List[Dict], high_priority_failures: List[Dict]) -> List[str]:
        """Generate specific next steps based on decision"""
        
        next_steps = []
        
        if decision == "DENY":
            next_steps.append("Document denial reasons")
            next_steps.append("Provide adverse action notice if required")
            if critical_failures:
                next_steps.append("Inform applicant of specific policy violations")
        
        elif decision == "MANUAL_REVIEW":
            next_steps.append("Escalate to senior underwriter")
            next_steps.append("Review compensating factors")
            next_steps.append("Consider policy exceptions if applicable")
        
        elif decision == "APPROVE_WITH_CONDITIONS":
            next_steps.append("Document approval conditions")
            next_steps.append("Set up monitoring for warning conditions")
        
        elif decision == "APPROVE":
            next_steps.append("Proceed with standard approval process")
            next_steps.append("Document compliance verification")
        
        return next_steps
    
    def get_agent_summary(self, selected_agents: List[Dict]) -> Dict:
        """Get summary of selected agents for UI display"""
        
        summary = {
            "total_agents": len(selected_agents),
            "by_type": {
                "threshold": 0,
                "criteria": 0,
                "score": 0,
                "qualitative": 0
            },
            "by_priority": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "data_requirements": set(),
            "applicable_products": set()
        }
        
        for agent in selected_agents:
            # Count by type
            agent_id = agent.get('agent_id', '')
            if agent_id.startswith('TH'):
                summary["by_type"]["threshold"] += 1
            elif agent_id.startswith('CR'):
                summary["by_type"]["criteria"] += 1
            elif agent_id.startswith('SC'):
                summary["by_type"]["score"] += 1
            elif agent_id.startswith('QL'):
                summary["by_type"]["qualitative"] += 1
            
            # Count by priority
            priority = agent.get('priority', 'medium')
            summary["by_priority"][priority] += 1
            
            # Collect data requirements
            summary["data_requirements"].update(agent.get('data_fields', []))
            
            # Collect applicable products
            summary["applicable_products"].update(agent.get('applicable_products', []))
        
        # Convert sets to lists for JSON serialization
        summary["data_requirements"] = list(summary["data_requirements"])
        summary["applicable_products"] = list(summary["applicable_products"])
        
        return summary 