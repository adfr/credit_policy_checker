from agents.base_agent import BaseAgent
from typing import Dict, List, Any
import json

class UniversalAgent(BaseAgent):
    """Universal agent that can handle any type of policy check"""
    
    def __init__(self, check_definition: Dict):
        self.check_definition = check_definition
        self.domain = check_definition.get('domain', 'general')
        self.complexity = check_definition.get('complexity', 'simple')
        super().__init__(f"universal_{self.domain}_{check_definition.get('check_type', 'analysis')}")
    
    def check(self, policy_check: Dict, data: Dict) -> Dict:
        """Perform any type of compliance/analysis check"""
        
        # Determine the analysis approach based on complexity
        if self.complexity == 'multi_step':
            return self._multi_step_analysis(policy_check, data)
        elif self.complexity == 'comparative':
            return self._comparative_analysis(policy_check, data)
        elif self.complexity == 'quantitative':
            return self._quantitative_analysis(policy_check, data)
        else:
            return self._simple_analysis(policy_check, data)
    
    def _simple_analysis(self, policy_check: Dict, data: Dict) -> Dict:
        """Simple single-step analysis"""
        
        # Get agent configuration from check definition
        agent_config = self.check_definition
        agent_name = agent_config.get('agent_name', 'Policy Check')
        requirement = agent_config.get('requirement', policy_check.get('criteria', ''))
        data_fields = agent_config.get('data_fields', [])
        
        # Check for missing required fields
        missing_fields = []
        for field in data_fields:
            if field not in data or data.get(field) is None:
                missing_fields.append(field)
        
        # If critical fields are missing, check if they might not be applicable
        if missing_fields:
            # Let the LLM determine if the missing fields are applicable to this document type
            missing_fields_str = ', '.join(f"'{field}'" for field in missing_fields)
            
            applicability_prompt = f"""
            You are evaluating whether a policy check is applicable to a document.
            
            Policy Check: {agent_name}
            Requirement: {requirement}
            Missing Fields: {missing_fields_str}
            Available Data: {json.dumps(data, indent=2)}
            
            Based on the available data, determine if the missing fields are:
            1. Simply not extracted from the document (but might be present)
            2. Not applicable to this type of document/application
            
            Examples:
            - If checking "Home Equity Loan Amount" but the document is a "primary mortgage application", then home_equity_loan_amount is NOT APPLICABLE
            - If checking "Credit Score" but no credit scores are found, they might just be MISSING
            
            Return JSON:
            {{
                "applicable": true/false,
                "reason": "explanation of why the check is or isn't applicable to this document"
            }}
            """
            
            try:
                applicability_response = self.process(applicability_prompt)
                applicability_result = json.loads(applicability_response)
                
                if not applicability_result.get('applicable', True):
                    return {
                        'check_type': policy_check.get('check_type'),
                        'description': policy_check.get('description'),
                        'passed': None,  # Neither passed nor failed - not applicable
                        'reason': f"Check not applicable: {applicability_result.get('reason', 'Required fields not applicable to this document type')}",
                        'confidence': 0.95,
                        'missing_fields': missing_fields,
                        'applicable': False,
                        'domain': self.domain,
                        'agent_type': 'universal'
                    }
            except:
                # Fallback to generic missing fields message
                pass
            
            return {
                'check_type': policy_check.get('check_type'),
                'description': policy_check.get('description'),
                'passed': False,
                'reason': f"Cannot evaluate {agent_name}: Required field(s) {missing_fields_str} not found in the document. This check requires these fields to assess compliance.",
                'confidence': 1.0,
                'missing_fields': missing_fields,
                'domain': self.domain,
                'agent_type': 'universal'
            }
        
        # Check if this is a threshold agent (like LTV) that needs focused checking
        is_threshold_agent = 'threshold' in agent_config.get('agent_id', '').lower() or 'TH' in agent_config.get('agent_id', '')
        
        if is_threshold_agent:
            prompt = f"""
            You are a focused compliance checker for: {agent_name}
            
            CRITICAL: You MUST ONLY evaluate the specific requirement stated below. 
            DO NOT evaluate or comment on ANY other aspect of the application.
            
            Requirement to Check:
            {requirement}
            
            Required Data Fields: {', '.join(data_fields)}
            
            Available Data (ONLY data relevant to your check):
            {json.dumps(data, indent=2)}
            
            STRICT INSTRUCTIONS:
            1. ONLY verify compliance with the EXACT requirement stated above
            2. If you need to calculate values, use ONLY the data fields provided
            3. Compare against the specific limits/thresholds in your requirement
            4. CRITICAL: When comparing numbers, be mathematically accurate:
               - If requirement says "must be below X%", then actual value > X% = FAILED
               - If requirement says "must be above X%", then actual value < X% = FAILED
               - Double-check your mathematical comparison logic
            5. DO NOT mention or evaluate any data not related to your specific check
            6. DO NOT provide any general creditworthiness assessment
            7. Your response should be laser-focused on ONLY your assigned check
            
            Return JSON:
            {{
                "passed": true/false,
                "calculation": "show specific calculation if applicable",
                "threshold_checked": "the specific limit being checked",
                "actual_value": "the calculated/found value",
                "confidence": 0.0-1.0,
                "reason": "focused explanation ONLY about this specific requirement"
            }}
            
            Return only JSON, no other text.
            """
        else:
            # For non-threshold agents, also be focused on the specific check
            prompt = f"""
            You are a specialized {agent_name} checker.
            
            CRITICAL: You MUST ONLY evaluate the specific requirement stated below.
            
            Requirement to Check:
            {requirement}
            
            Required Data Fields: {', '.join(data_fields)}
            
            Available Data:
            {json.dumps(data, indent=2)}
            
            INSTRUCTIONS:
            1. Focus ONLY on verifying the stated requirement
            2. Use ONLY the data fields provided
            3. Do NOT evaluate aspects outside your specific check
            4. Provide a focused assessment of compliance
            
            Return JSON:
            {{
                "passed": true/false,
                "findings": ["list of findings ONLY related to your specific check"],
                "confidence": 0.0-1.0,
                "reason": "clear explanation focused ONLY on your specific requirement"
            }}
            
            Return only the JSON, no other text.
            """
        
        return self._execute_analysis(prompt, policy_check)
    
    def _quantitative_analysis(self, policy_check: Dict, data: Dict) -> Dict:
        """Quantitative analysis with calculations"""
        
        # Get agent configuration from check definition
        agent_config = self.check_definition
        agent_name = agent_config.get('agent_name', 'Quantitative Check')
        requirement = agent_config.get('requirement', policy_check.get('criteria', ''))
        data_fields = agent_config.get('data_fields', [])
        
        # Check for missing required fields
        missing_fields = []
        for field in data_fields:
            if field not in data or data.get(field) is None:
                missing_fields.append(field)
        
        # If critical fields are missing, check if they might not be applicable
        if missing_fields:
            # Let the LLM determine if the missing fields are applicable to this document type
            missing_fields_str = ', '.join(f"'{field}'" for field in missing_fields)
            
            applicability_prompt = f"""
            You are evaluating whether a quantitative policy check is applicable to a document.
            
            Policy Check: {agent_name}
            Requirement: {requirement}
            Missing Fields: {missing_fields_str}
            Available Data: {json.dumps(data, indent=2)}
            
            Based on the available data, determine if the missing fields are:
            1. Simply not extracted from the document (but might be present)
            2. Not applicable to this type of document/application
            
            Examples:
            - If checking "Home Equity Loan Amount" but the document is a "primary mortgage application", then home_equity_loan_amount is NOT APPLICABLE
            - If checking "Credit Score" but no credit scores are found, they might just be MISSING
            
            Return JSON:
            {{
                "applicable": true/false,
                "reason": "explanation of why the check is or isn't applicable to this document"
            }}
            """
            
            try:
                applicability_response = self.process(applicability_prompt)
                applicability_result = json.loads(applicability_response)
                
                if not applicability_result.get('applicable', True):
                    return {
                        'check_type': policy_check.get('check_type'),
                        'description': policy_check.get('description'),
                        'passed': None,  # Neither passed nor failed - not applicable
                        'reason': f"Check not applicable: {applicability_result.get('reason', 'Required fields not applicable to this document type')}",
                        'confidence': 0.95,
                        'missing_fields': missing_fields,
                        'applicable': False,
                        'domain': self.domain,
                        'agent_type': 'universal'
                    }
            except:
                # Fallback to generic missing fields message
                pass
            
            return {
                'check_type': policy_check.get('check_type'),
                'description': policy_check.get('description'),
                'passed': False,
                'reason': f"Cannot evaluate {agent_name}: Required field(s) {missing_fields_str} not found in the document. This check requires these fields to perform calculations.",
                'confidence': 1.0,
                'missing_fields': missing_fields,
                'domain': self.domain,
                'agent_type': 'universal'
            }
        
        # Check if this is a threshold agent that needs focused checking
        is_threshold_agent = 'threshold' in agent_config.get('agent_id', '').lower() or 'TH' in agent_config.get('agent_id', '')
        
        if is_threshold_agent:
            prompt = f"""
            You are a focused quantitative compliance checker for: {agent_name}
            
            SCOPE: You ONLY check this specific requirement. Do NOT provide general assessments.
            
            Requirement to Check:
            {requirement}
            
            Required Data Fields: {', '.join(data_fields)}
            
            Available Data:
            {json.dumps(data, indent=2)}
            
            INSTRUCTIONS:
            1. ONLY calculate and verify compliance with the stated requirement
            2. Show the specific calculation performed
            3. Compare the calculated value against the specific threshold/limit
            4. CRITICAL: When comparing numbers, be mathematically accurate:
               - If requirement says "must be below X%", then actual value > X% = FAILED
               - If requirement says "must be above X%", then actual value < X% = FAILED
               - Double-check your mathematical comparison logic before concluding
            5. Do NOT comment on other aspects of creditworthiness
            6. Focus solely on this single quantitative check
            
            Return JSON:
            {{
                "passed": true/false,
                "calculation": "detailed calculation with formula and steps",
                "calculated_value": "the numerical result",
                "threshold_limit": "the specific limit being checked against",
                "threshold_checked": "description of what threshold was verified",
                "confidence": 0.0-1.0,
                "reason": "focused explanation ONLY about this specific calculation and threshold"
            }}
            
            Return only JSON, no other text.
            """
        else:
            # For non-threshold quantitative agents, also be focused
            prompt = f"""
            You are a specialized quantitative checker for: {agent_name}
            
            CRITICAL: You MUST ONLY evaluate the specific requirement stated below.
            
            Requirement to Check:
            {requirement}
            
            Required Data Fields: {', '.join(data_fields)}
            
            Available Data:
            {json.dumps(data, indent=2)}
            
            INSTRUCTIONS:
            1. Perform calculations ONLY related to your specific requirement
            2. Use ONLY the data fields provided
            3. Do NOT calculate or comment on metrics outside your check
            4. Focus solely on quantitative assessment of your requirement
            
            Return JSON:
            {{
                "passed": true/false,
                "calculations": {{"metric_name": {{"value": number, "formula": "description"}}}},
                "confidence": 0.0-1.0,
                "reason": "quantitative explanation focused ONLY on your requirement"
            }}
            """
        
        return self._execute_analysis(prompt, policy_check)
    
    def _comparative_analysis(self, policy_check: Dict, data: Dict) -> Dict:
        """Comparative analysis against benchmarks or peers"""
        prompt = f"""
        You are a comparative analyst specializing in: {self.domain}
        
        Task: {policy_check.get('description')}
        Perform comparative analysis against benchmarks, industry standards, or peer groups.
        
        Requirements:
        {policy_check.get('criteria')}
        
        Data to Compare:
        {json.dumps(data, indent=2)}
        
        Benchmarks/Standards:
        {policy_check.get('benchmarks', 'Use industry standards')}
        
        Return JSON:
        {{
            "passed": true/false,
            "comparison_result": {{"vs_benchmark": number, "performance": "above/below/at"}},
            "confidence": 0.0-1.0,
            "reason": "comparative analysis explanation"
        }}
        """
        
        return self._execute_analysis(prompt, policy_check)
    
    def _multi_step_analysis(self, policy_check: Dict, data: Dict) -> Dict:
        """Complex multi-step analysis"""
        steps = policy_check.get('analysis_steps', [])
        if not steps:
            # Generate analysis steps
            steps = self._generate_analysis_steps(policy_check)
        
        step_results = []
        overall_passed = True
        
        for i, step in enumerate(steps):
            prompt = f"""
            You are conducting step {i+1} of a multi-step analysis in: {self.domain}
            
            Overall Task: {policy_check.get('description')}
            Current Step: {step}
            
            Data:
            {json.dumps(data, indent=2)}
            
            Previous Steps Results:
            {json.dumps(step_results, indent=2) if step_results else "None"}
            
            Focus only on this step. Return JSON:
            {{
                "step_passed": true/false,
                "step_findings": ["findings for this step"],
                "confidence": 0.0-1.0
            }}
            """
            
            step_result = self._execute_analysis(prompt, policy_check, f"step_{i+1}")
            
            if isinstance(step_result, dict) and not step_result.get('step_passed', False):
                overall_passed = False
            
            step_results.append({
                'step_number': i + 1,
                'step_description': step,
                'result': step_result
            })
        
        # Final synthesis
        synthesis_prompt = f"""
        Synthesize the multi-step analysis results for: {policy_check.get('description')}
        
        All Step Results:
        {json.dumps(step_results, indent=2)}
        
        Provide final assessment:
        {{
            "passed": true/false,
            "overall_assessment": "comprehensive summary",
            "confidence": 0.0-1.0
        }}
        """
        
        final_result = self._execute_analysis(synthesis_prompt, policy_check, "synthesis")
        final_result['step_results'] = step_results
        
        return final_result
    
    def _generate_analysis_steps(self, policy_check: Dict) -> List[str]:
        """Generate analysis steps for complex checks"""
        prompt = f"""
        Break down this analysis into logical steps:
        
        Task: {policy_check.get('description')}
        Domain: {self.domain}
        Requirements: {policy_check.get('criteria')}
        
        Return a JSON array of 3-7 analysis steps in logical order:
        ["step 1 description", "step 2 description", ...]
        """
        
        try:
            response = self.process(prompt)
            steps = json.loads(response)
            return steps if isinstance(steps, list) else ["Analyze data", "Check compliance", "Provide recommendation"]
        except:
            return ["Analyze data", "Check compliance", "Provide recommendation"]
    
    def _execute_analysis(self, prompt: str, policy_check: Dict, step_type: str = "main") -> Dict:
        """Execute analysis and handle errors"""
        try:
            ai_response = self.process(prompt)
            
            # Check if response is already a JSON error from base agent
            if isinstance(ai_response, str) and ai_response.strip().startswith('{"passed": false'):
                result = json.loads(ai_response)
                result.update({
                    'check_type': policy_check.get('check_type'),
                    'description': policy_check.get('description'),
                    'domain': self.domain,
                    'agent_type': 'universal'
                })
                return result
            
            # Debug: Print the raw response if parsing fails
            try:
                result = json.loads(ai_response)
            except json.JSONDecodeError as json_err:
                print(f"DEBUG: JSON parsing failed for {policy_check.get('check_type', 'unknown')}")
                print(f"DEBUG: Raw AI response (first 500 chars): {str(ai_response)[:500]}")
                print(f"DEBUG: JSON error: {str(json_err)}")
                
                return {
                    'check_type': policy_check.get('check_type'),
                    'description': policy_check.get('description'),
                    'passed': False,
                    'reason': f"Analysis error: Could not parse AI response. Response was: {str(ai_response)[:200]}...",
                    'confidence': 0.0,
                    'domain': self.domain,
                    'agent_type': 'universal'
                }
            
            # Add metadata
            result.update({
                'check_type': policy_check.get('check_type'),
                'description': policy_check.get('description'),
                'domain': self.domain,
                'complexity': self.complexity,
                'agent_type': 'universal',
                'step_type': step_type
            })
            
            return result
            
        except Exception as e:
            print(f"DEBUG: General error in _execute_analysis: {str(e)}")
            return {
                'check_type': policy_check.get('check_type'),
                'description': policy_check.get('description'),
                'passed': False,
                'reason': f"Universal agent error: {str(e)}",
                'confidence': 0.0,
                'domain': self.domain,
                'agent_type': 'universal'
            }