from typing import Dict, List, Any, Optional
from agents.base_agent import BaseAgent
import json

class ThresholdAgent(BaseAgent):
    """Agent that checks numeric thresholds, ratios, and limits"""
    
    def __init__(self, agent_config: Dict):
        super().__init__("threshold_agent")
        self.config = agent_config
        
    def check(self, policy_check: Dict, applicant_data: Dict) -> Dict:
        """Check if applicant data meets threshold requirements"""
        
        prompt = f"""
        You are a threshold compliance checker. Evaluate if the applicant meets this threshold requirement.
        
        THRESHOLD REQUIREMENT:
        Agent ID: {self.config.get('agent_id')}
        Name: {self.config.get('agent_name')}
        Requirement: {self.config.get('requirement')}
        Threshold Value: {self.config.get('threshold_value')}
        Threshold Type: {self.config.get('threshold_type')}  (minimum/maximum/exact/range)
        Unit: {self.config.get('unit', 'numeric')}
        Calculation: {self.config.get('calculation', 'direct comparison')}
        Data Fields Needed: {self.config.get('data_fields')}
        
        APPLICANT DATA:
        {json.dumps(applicant_data, indent=2)}
        
        INSTRUCTIONS:
        1. Extract the required data fields from applicant data
        2. Perform the calculation if specified, otherwise use direct values
        3. Compare against the threshold based on threshold_type:
           - minimum: value must be >= threshold
           - maximum: value must be <= threshold  
           - exact: value must equal threshold
           - range: value must be within specified range
        4. Account for the unit (percentage, dollars, ratio, etc.)
        5. Consider any exceptions mentioned in the policy
        
        Return JSON result:
        {{
            "agent_id": "{self.config.get('agent_id')}",
            "agent_type": "threshold",
            "passed": true/false,
            "calculated_value": actual_calculated_value,
            "threshold_value": {self.config.get('threshold_value')},
            "comparison": "calculated_value [operator] threshold_value",
            "reason": "specific explanation of pass/fail",
            "confidence": 0.0-1.0,
            "data_used": {{"field_name": "value_extracted"}},
            "missing_data": ["list of required fields not found"],
            "warnings": ["any concerns or edge cases"]
        }}
        
        If data is missing or invalid, set passed=false and explain what's needed.
        Be precise about calculations and reasoning.
        
        Return only JSON, no other text.
        """
        
        try:
            response = self.process(prompt)
            result = json.loads(response)
            
            # Ensure required fields are present
            result.setdefault("agent_id", self.config.get('agent_id'))
            result.setdefault("agent_type", "threshold")
            result.setdefault("passed", False)
            result.setdefault("confidence", 0.0)
            
            return result
            
        except json.JSONDecodeError:
            return {
                "agent_id": self.config.get('agent_id'),
                "agent_type": "threshold", 
                "passed": False,
                "reason": "Failed to parse LLM response",
                "confidence": 0.0,
                "error": True
            }


class CriteriaAgent(BaseAgent):
    """Agent that checks specific criteria and conditions"""
    
    def __init__(self, agent_config: Dict):
        super().__init__("criteria_agent")
        self.config = agent_config
        
    def check(self, policy_check: Dict, applicant_data: Dict) -> Dict:
        """Check if applicant data meets criteria requirements"""
        
        prompt = f"""
        You are a criteria compliance checker. Evaluate if the applicant meets this criteria requirement.
        
        CRITERIA REQUIREMENT:
        Agent ID: {self.config.get('agent_id')}
        Name: {self.config.get('agent_name')}
        Requirement: {self.config.get('requirement')}
        Criteria Type: {self.config.get('criteria_type')}
        Expected Value: {self.config.get('expected_value')}
        Verification Method: {self.config.get('verification_method')}
        Data Fields Needed: {self.config.get('data_fields')}
        Exceptions: {self.config.get('exceptions', [])}
        
        APPLICANT DATA:
        {json.dumps(applicant_data, indent=2)}
        
        INSTRUCTIONS:
        1. Look for the required data fields in applicant data
        2. Evaluate if the criteria is met based on criteria_type:
           - boolean: true/false check
           - duration: time period requirements
           - categorical: specific category/status
           - existence: presence of required items
           - count: number of items/occurrences
        3. Consider verification method and data quality
        4. Check for any applicable exceptions
        5. Look for alternative evidence if primary data missing
        
        Return JSON result:
        {{
            "agent_id": "{self.config.get('agent_id')}",
            "agent_type": "criteria",
            "passed": true/false,
            "criteria_met": "description of what was found vs required",
            "found_value": "actual value/status found in data",
            "expected_value": "{self.config.get('expected_value')}",
            "reason": "specific explanation of pass/fail",
            "confidence": 0.0-1.0,
            "data_used": {{"field_name": "value_extracted"}},
            "missing_data": ["list of required fields not found"],
            "exceptions_applied": ["any exceptions that were considered"],
            "verification_notes": "notes about data quality/verification"
        }}
        
        If data is missing, ambiguous, or insufficient for verification, set passed=false.
        Be specific about what evidence was found or missing.
        
        Return only JSON, no other text.
        """
        
        try:
            response = self.process(prompt)
            result = json.loads(response)
            
            # Ensure required fields are present
            result.setdefault("agent_id", self.config.get('agent_id'))
            result.setdefault("agent_type", "criteria")
            result.setdefault("passed", False)
            result.setdefault("confidence", 0.0)
            
            return result
            
        except json.JSONDecodeError:
            return {
                "agent_id": self.config.get('agent_id'),
                "agent_type": "criteria",
                "passed": False,
                "reason": "Failed to parse LLM response", 
                "confidence": 0.0,
                "error": True
            }


class ScoreAgent(BaseAgent):
    """Agent that calculates scores and ratings"""
    
    def __init__(self, agent_config: Dict):
        super().__init__("score_agent")
        self.config = agent_config
        
    def check(self, policy_check: Dict, applicant_data: Dict) -> Dict:
        """Calculate score based on scoring model"""
        
        prompt = f"""
        You are a scoring compliance checker. Calculate the score for this applicant using the specified scoring model.
        
        SCORING MODEL:
        Agent ID: {self.config.get('agent_id')}
        Name: {self.config.get('agent_name')}
        Requirement: {self.config.get('requirement')}
        Scoring Factors: {self.config.get('scoring_factors')}
        Scoring Weights: {self.config.get('scoring_weights', {})}
        Score Range: {self.config.get('score_range', [0, 100])}
        Data Fields Needed: {self.config.get('data_fields')}
        
        APPLICANT DATA:
        {json.dumps(applicant_data, indent=2)}
        
        INSTRUCTIONS:
        1. Extract values for each scoring factor from applicant data
        2. Normalize values to appropriate scales if needed
        3. Apply weights to each factor
        4. Calculate overall score using the scoring model
        5. Ensure score is within the specified range
        6. Provide breakdown of how score was calculated
        
        Return JSON result:
        {{
            "agent_id": "{self.config.get('agent_id')}",
            "agent_type": "score",
            "passed": true,  # Scoring agents typically always "pass" but provide the score
            "calculated_score": final_calculated_score,
            "score_range": {self.config.get('score_range', [0, 100])},
            "score_breakdown": {{
                "factor_name": {{"value": extracted_value, "weight": applied_weight, "weighted_score": contribution}}
            }},
            "normalization_applied": "description of any normalization",
            "reason": "explanation of score calculation",
            "confidence": 0.0-1.0,
            "data_used": {{"field_name": "value_extracted"}},
            "missing_data": ["list of required fields not found"],
            "score_interpretation": "what this score means (e.g., 'excellent', 'poor')"
        }}
        
        If critical data is missing, indicate in missing_data but still calculate with available data.
        Adjust confidence based on data completeness.
        
        Return only JSON, no other text.
        """
        
        try:
            response = self.process(prompt)
            result = json.loads(response)
            
            # Ensure required fields are present
            result.setdefault("agent_id", self.config.get('agent_id'))
            result.setdefault("agent_type", "score")
            result.setdefault("passed", True)  # Score agents typically pass but provide score
            result.setdefault("confidence", 0.0)
            
            return result
            
        except json.JSONDecodeError:
            return {
                "agent_id": self.config.get('agent_id'),
                "agent_type": "score",
                "passed": True,
                "calculated_score": None,
                "reason": "Failed to parse LLM response",
                "confidence": 0.0,
                "error": True
            }


class QualitativeAgent(BaseAgent):
    """Agent that performs qualitative assessments requiring judgment"""
    
    def __init__(self, agent_config: Dict):
        super().__init__("qualitative_agent")
        self.config = agent_config
        
    def check(self, policy_check: Dict, applicant_data: Dict) -> Dict:
        """Perform qualitative assessment"""
        
        prompt = f"""
        You are a qualitative assessment agent. Perform a judgment-based evaluation of this applicant.
        
        QUALITATIVE ASSESSMENT:
        Agent ID: {self.config.get('agent_id')}
        Name: {self.config.get('agent_name')}
        Requirement: {self.config.get('requirement')}
        Assessment Criteria: {self.config.get('assessment_criteria')}
        Evaluation Guidelines: {self.config.get('evaluation_guidelines')}
        Data Fields Needed: {self.config.get('data_fields')}
        
        APPLICANT DATA:
        {json.dumps(applicant_data, indent=2)}
        
        INSTRUCTIONS:
        1. Review all relevant data about the applicant
        2. Apply the assessment criteria systematically
        3. Use the evaluation guidelines to make judgment
        4. Look for patterns, red flags, and positive indicators
        5. Consider the overall picture, not just individual factors
        6. Provide specific evidence for your assessment
        
        Assessment Guidelines:
        - Be objective and evidence-based in your evaluation
        - Look for consistency across different data points
        - Consider compensating factors that might offset weaknesses
        - Note any areas requiring human review or additional information
        
        Return JSON result:
        {{
            "agent_id": "{self.config.get('agent_id')}",
            "agent_type": "qualitative",
            "passed": true/false,
            "assessment_result": "favorable/unfavorable/requires_review",
            "key_findings": ["list of important observations"],
            "positive_factors": ["strengths identified"],
            "negative_factors": ["concerns identified"],
            "compensating_factors": ["factors that offset concerns"],
            "reason": "detailed explanation of assessment",
            "confidence": 0.0-1.0,
            "data_used": {{"field_name": "value_extracted"}},
            "missing_data": ["list of desired but unavailable data"],
            "recommendation": "approve/deny/request_more_info/human_review",
            "additional_requirements": ["any additional steps recommended"]
        }}
        
        Use your best judgment based on available information.
        Lower confidence if critical qualitative data is missing.
        
        Return only JSON, no other text.
        """
        
        try:
            response = self.process(prompt)
            result = json.loads(response)
            
            # Ensure required fields are present
            result.setdefault("agent_id", self.config.get('agent_id'))
            result.setdefault("agent_type", "qualitative")
            result.setdefault("passed", False)
            result.setdefault("confidence", 0.0)
            
            return result
            
        except json.JSONDecodeError:
            return {
                "agent_id": self.config.get('agent_id'),
                "agent_type": "qualitative",
                "passed": False,
                "reason": "Failed to parse LLM response",
                "confidence": 0.0,
                "error": True
            }


class AgentFactory:
    """Factory to create appropriate agent instances"""
    
    @staticmethod
    def create_agent(agent_config: Dict) -> BaseAgent:
        """Create an agent instance based on configuration"""
        
        agent_type = agent_config.get('agent_type', '').lower()
        
        if 'threshold' in agent_type:
            return ThresholdAgent(agent_config)
        elif 'criteria' in agent_type:
            return CriteriaAgent(agent_config)
        elif 'score' in agent_type:
            return ScoreAgent(agent_config)
        elif 'qualitative' in agent_type:
            return QualitativeAgent(agent_config)
        else:
            # Default to criteria agent for unknown types
            return CriteriaAgent(agent_config)
    
    @staticmethod
    def create_agents_from_extraction(extracted_agents: Dict) -> List[BaseAgent]:
        """Create agent instances from extracted policy agents"""
        
        agents = []
        
        # Create threshold agents
        for agent_config in extracted_agents.get('threshold_agents', []):
            agent_config['agent_type'] = 'threshold'
            agents.append(ThresholdAgent(agent_config))
        
        # Create criteria agents  
        for agent_config in extracted_agents.get('criteria_agents', []):
            agent_config['agent_type'] = 'criteria'
            agents.append(CriteriaAgent(agent_config))
        
        # Create score agents
        for agent_config in extracted_agents.get('score_agents', []):
            agent_config['agent_type'] = 'score'
            agents.append(ScoreAgent(agent_config))
        
        # Create qualitative agents
        for agent_config in extracted_agents.get('qualitative_agents', []):
            agent_config['agent_type'] = 'qualitative'
            agents.append(QualitativeAgent(agent_config))
        
        return agents 