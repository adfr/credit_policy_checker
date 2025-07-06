"""
Test to verify agents make mathematically accurate comparisons
"""

import pytest
import json
import os
from unittest.mock import Mock, patch
from agents.universal_agent import UniversalAgent
from agents.hybrid_credit_agent import HybridCreditAgent

# Set dummy API key for testing
os.environ['OPENAI_API_KEY'] = 'test-key-123'


class TestMathematicalAccuracy:
    """Test suite to verify mathematical comparison accuracy"""
    
    def test_ltv_above_threshold_should_fail(self):
        """Test that LTV of 90.59% correctly fails against 80% limit"""
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Mock correct mathematical response
            mock_process.return_value = json.dumps({
                "passed": False,
                "calculation": "LTV = 385000 / 428000 = 0.9059 = 90.59%",
                "threshold_checked": "80%",
                "actual_value": "90.59%",
                "confidence": 0.95,
                "reason": "LTV ratio of 90.59% exceeds the maximum limit of 80%. Requirement FAILED."
            })
            
            check_definition = {
                'agent_id': 'LTV_TH_001',
                'agent_name': 'LTV Ratio Check',
                'requirement': 'LTV ratio must be below 80% for primary residence',
                'data_fields': ['ltv_ratio', 'loan_amount', 'property_value'],
                'check_type': 'ltv_threshold'
            }
            
            agent = UniversalAgent(check_definition)
            
            # Data where LTV is above the limit
            data = {
                'ltv_ratio': 90.59,
                'loan_amount': 385000,
                'property_value': 428000
            }
            
            result = agent.check({}, data)
            
            # Verify the prompt contains mathematical accuracy instructions
            mock_process.assert_called_once()
            prompt = mock_process.call_args[0][0]
            
            assert "CRITICAL: When comparing numbers, be mathematically accurate" in prompt
            assert "If requirement says \"must be below X%\", then actual value > X% = FAILED" in prompt
            
            # Verify the result correctly identifies this as a failure
            assert result['passed'] is False
            assert "90.59%" in result['reason']
            assert "80%" in result['reason']
    
    def test_credit_score_below_threshold_should_fail(self):
        """Test that credit score below minimum correctly fails"""
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Mock correct mathematical response
            mock_process.return_value = json.dumps({
                "passed": False,
                "calculation": "Average credit score: (650 + 660) / 2 = 655",
                "threshold_checked": "680",
                "actual_value": "655",
                "confidence": 0.95,
                "reason": "Average credit score of 655 is below the minimum requirement of 680. Requirement FAILED."
            })
            
            check_definition = {
                'agent_id': 'CR_TH_001',
                'agent_name': 'Credit Score Check',
                'requirement': 'Average credit score must be above 680',
                'data_fields': ['average_credit_score', 'credit_score_borrower_1', 'credit_score_borrower_2'],
                'check_type': 'credit_score_threshold'
            }
            
            agent = UniversalAgent(check_definition)
            
            # Data where credit score is below the limit
            data = {
                'average_credit_score': 655,
                'credit_score_borrower_1': 650,
                'credit_score_borrower_2': 660
            }
            
            result = agent.check({}, data)
            
            # Verify the prompt contains mathematical accuracy instructions
            prompt = mock_process.call_args[0][0]
            assert "If requirement says \"must be above X%\", then actual value < X% = FAILED" in prompt
            
            # Verify correct failure identification
            assert result['passed'] is False
    
    def test_dti_within_threshold_should_pass(self):
        """Test that DTI within limits correctly passes"""
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Mock correct mathematical response
            mock_process.return_value = json.dumps({
                "passed": True,
                "calculation": "DTI = 3000 / 15000 = 0.20 = 20%",
                "threshold_checked": "43%",
                "actual_value": "20%",
                "confidence": 0.95,
                "reason": "DTI ratio of 20% is below the maximum limit of 43%. Requirement PASSED."
            })
            
            check_definition = {
                'agent_id': 'DTI_TH_001',
                'agent_name': 'DTI Ratio Check',
                'requirement': 'DTI ratio must be below 43%',
                'data_fields': ['dti_ratio', 'monthly_income', 'monthly_debt'],
                'check_type': 'dti_threshold',
                'complexity': 'quantitative'
            }
            
            agent = UniversalAgent(check_definition)
            
            # Data where DTI is within the limit
            data = {
                'dti_ratio': 20.0,
                'monthly_income': 15000,
                'monthly_debt': 3000
            }
            
            result = agent.check({}, data)
            
            # Verify correct pass identification
            assert result['passed'] is True
            assert "20%" in result['reason']
            assert "43%" in result['reason']
    
    @patch('agents.hybrid_credit_agent.GraphDatabase.driver')
    def test_hybrid_agent_mathematical_accuracy(self, mock_driver):
        """Test that hybrid agent also includes mathematical accuracy instructions"""
        
        mock_driver.return_value = None
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Mock correct mathematical response
            mock_process.return_value = json.dumps({
                "passed": False,
                "reason": "LTV ratio of 95.5% exceeds the maximum limit of 95%. Requirement FAILED.",
                "confidence": 0.95,
                "requirements_evaluated": ["LTV_001"],
                "linked_impacts": [],
                "recommendations": ["Increase down payment to reduce LTV"]
            })
            
            agent = HybridCreditAgent()
            agent.driver = None
            agent.check_definition = {
                'agent_id': 'LTV_TH_001',
                'agent_name': 'LTV Ratio Check',
                'requirement': 'LTV ratio must be below 95%',
                'data_fields': ['ltv_ratio'],
                'check_type': 'ltv_threshold'
            }
            
            policy_check = {
                'check_type': 'ltv_threshold',
                'description': 'LTV Ratio Check'
            }
            
            data = {'ltv_ratio': 95.5}
            
            result = agent.check(policy_check, data)
            
            # Verify the prompt contains mathematical accuracy instructions
            mock_process.assert_called_once()
            prompt = mock_process.call_args[0][0]
            
            assert "CRITICAL: When comparing numbers, be mathematically accurate" in prompt
            assert "Double-check your mathematical comparison logic before concluding" in prompt
    
    def test_edge_case_exactly_at_threshold(self):
        """Test behavior when value is exactly at the threshold"""
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Mock response for exact threshold case
            mock_process.return_value = json.dumps({
                "passed": True,  # 80% exactly at 80% limit should pass
                "calculation": "LTV = 80.0%",
                "threshold_checked": "80%",
                "actual_value": "80%",
                "confidence": 0.95,
                "reason": "LTV ratio of 80% meets the maximum limit of 80%. Requirement PASSED."
            })
            
            check_definition = {
                'agent_id': 'LTV_TH_001',
                'agent_name': 'LTV Ratio Check',
                'requirement': 'LTV ratio must be 80% or below',
                'data_fields': ['ltv_ratio'],
                'check_type': 'ltv_threshold'
            }
            
            agent = UniversalAgent(check_definition)
            
            # Data exactly at the threshold
            data = {'ltv_ratio': 80.0}
            
            result = agent.check({}, data)
            
            # This tests that the agent handles edge cases correctly
            assert result['passed'] is True
            assert "80%" in result['reason']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])