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
        prompt = f"""
        You are an expert analyst specializing in: {self.domain}
        
        Task: {policy_check.get('description')}
        Check Type: {policy_check.get('check_type')}
        Domain: {self.domain}
        
        Requirements/Criteria:
        {policy_check.get('criteria')}
        
        Data to Analyze:
        {json.dumps(data, indent=2)}
        
        Additional Instructions:
        {policy_check.get('agent_instructions', 'Perform standard compliance check')}
        
        Analyze the data against the requirements and return a JSON response:
        {{
            "passed": true/false,
            "findings": ["list of key findings"],
            "confidence": 0.0-1.0,
            "reason": "clear explanation of the decision"
        }}
        
        Return only the JSON, no other text.
        """
        
        return self._execute_analysis(prompt, policy_check)
    
    def _quantitative_analysis(self, policy_check: Dict, data: Dict) -> Dict:
        """Quantitative analysis with calculations"""
        prompt = f"""
        You are a quantitative analyst specializing in: {self.domain}
        
        Task: {policy_check.get('description')}
        Perform quantitative analysis including calculations, ratios, and statistical measures.
        
        Requirements:
        {policy_check.get('criteria')}
        
        Data:
        {json.dumps(data, indent=2)}
        
        Calculate relevant metrics and provide detailed quantitative assessment.
        
        Return JSON:
        {{
            "passed": true/false,
            "calculations": {{"metric_name": {{"value": number, "formula": "description"}}}},
            "confidence": 0.0-1.0,
            "reason": "detailed quantitative explanation"
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
            result = json.loads(ai_response)
            
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
            
        except json.JSONDecodeError:
            return {
                'check_type': policy_check.get('check_type'),
                'description': policy_check.get('description'),
                'passed': False,
                'reason': f"Analysis error: Could not parse AI response",
                'domain': self.domain,
                'agent_type': 'universal'
            }
        except Exception as e:
            return {
                'check_type': policy_check.get('check_type'),
                'description': policy_check.get('description'),
                'passed': False,
                'reason': f"Universal agent error: {str(e)}",
                'domain': self.domain,
                'agent_type': 'universal'
            }