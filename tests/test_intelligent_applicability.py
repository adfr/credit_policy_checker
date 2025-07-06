"""
Test to verify agents can intelligently determine when checks are not applicable
"""

import pytest
import json
import os
from unittest.mock import Mock, patch
from agents.universal_agent import UniversalAgent
from agents.hybrid_credit_agent import HybridCreditAgent

# Set dummy API key for testing
os.environ['OPENAI_API_KEY'] = 'test-key-123'


class TestIntelligentApplicability:
    """Test suite for intelligent applicability checking"""
    
    def test_home_equity_loan_not_applicable_to_primary_mortgage(self):
        """Test that home equity loan check is marked as not applicable for primary mortgage"""
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Mock the applicability response
            mock_process.return_value = json.dumps({
                "applicable": False,
                "reason": "This is a primary mortgage application, not a home equity loan. The home_equity_loan_amount field is not applicable to this document type."
            })
            
            check_definition = {
                'agent_id': 'HE_TH_001',
                'agent_name': 'Home Equity Loan Amount Limit',
                'requirement': 'Home equity loan amount must be below $100,000',
                'data_fields': ['home_equity_loan_amount'],
                'check_type': 'home_equity_loan_amount_threshold'
            }
            
            agent = UniversalAgent(check_definition)
            
            # Primary mortgage data (no home equity loan amount)
            primary_mortgage_data = {
                'loan_amount': 385000,
                'property_value': 428000,
                'application_type': 'primary_mortgage'
            }
            
            result = agent.check({}, primary_mortgage_data)
            
            assert result['passed'] is None  # Not applicable
            assert result['applicable'] is False
            assert 'not applicable' in result['reason'].lower()
            assert 'primary mortgage' in result['reason'].lower()
    
    def test_credit_score_missing_but_applicable(self):
        """Test that missing credit score is treated as missing (not non-applicable)"""
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Mock the applicability response indicating it IS applicable
            mock_process.return_value = json.dumps({
                "applicable": True,
                "reason": "Credit score checks are applicable to all loan applications. The credit scores may just not have been extracted properly."
            })
            
            check_definition = {
                'agent_id': 'CR_TH_001',
                'agent_name': 'Credit Score Check',
                'requirement': 'Average credit score must be above 680',
                'data_fields': ['average_credit_score'],
                'check_type': 'credit_score_threshold'
            }
            
            agent = UniversalAgent(check_definition)
            
            # Data without credit scores
            data_without_scores = {
                'loan_amount': 385000,
                'property_value': 428000
            }
            
            result = agent.check({}, data_without_scores)
            
            # Should fall back to standard missing field handling since it IS applicable
            assert result['passed'] is False
            assert 'missing_fields' in result
            assert 'average_credit_score' in result['missing_fields']
    
    @patch('agents.hybrid_credit_agent.GraphDatabase.driver')
    def test_hybrid_agent_applicability_check(self, mock_driver):
        """Test that hybrid agent also performs applicability checks"""
        
        mock_driver.return_value = None
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Mock the applicability response
            mock_process.return_value = json.dumps({
                "applicable": False,
                "reason": "This document is for a primary mortgage, not a home equity loan. Home equity loan amount limits do not apply."
            })
            
            agent = HybridCreditAgent()
            agent.driver = None
            agent.check_definition = {
                'agent_id': 'HE_TH_001',
                'agent_name': 'Home Equity Loan Amount Limit',
                'requirement': 'Home equity loan amount must be below $100,000',
                'data_fields': ['home_equity_loan_amount'],
                'check_type': 'home_equity_loan_amount_threshold'
            }
            
            policy_check = {
                'check_type': 'home_equity_loan_amount_threshold',
                'description': 'Home Equity Loan Amount Limit'
            }
            
            primary_mortgage_data = {
                'loan_amount': 385000,
                'property_value': 428000
            }
            
            result = agent.check(policy_check, primary_mortgage_data)
            
            assert result['passed'] is None  # Not applicable
            assert result['applicable'] is False
            assert 'not applicable' in result['reason'].lower()
            assert result['methodology'] == 'hybrid_graph_llm'
    
    def test_fallback_to_generic_error_on_llm_failure(self):
        """Test fallback behavior when LLM applicability check fails"""
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Mock LLM failure (invalid JSON)
            mock_process.return_value = "Invalid JSON response"
            
            check_definition = {
                'agent_id': 'TEST_001',
                'agent_name': 'Test Check',
                'requirement': 'Test requirement',
                'data_fields': ['missing_field'],
                'check_type': 'test_threshold'
            }
            
            agent = UniversalAgent(check_definition)
            
            result = agent.check({}, {})
            
            # Should fall back to generic missing field message
            assert result['passed'] is False
            assert 'Cannot evaluate' in result['reason']
            assert 'missing_field' in result['reason']
    
    def test_quantitative_analysis_applicability(self):
        """Test applicability checking in quantitative analysis"""
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Mock the applicability response for quantitative check
            mock_process.return_value = json.dumps({
                "applicable": False,
                "reason": "DTI calculations are not applicable to business loan applications where personal DTI is not relevant."
            })
            
            check_definition = {
                'agent_id': 'DTI_CALC_001',
                'agent_name': 'DTI Calculation',
                'requirement': 'Calculate and verify DTI ratio below 43%',
                'data_fields': ['monthly_income', 'monthly_debt'],
                'check_type': 'dti_calculation',
                'complexity': 'quantitative'
            }
            
            agent = UniversalAgent(check_definition)
            
            # Business loan data (no personal DTI applicable)
            business_loan_data = {
                'loan_amount': 500000,
                'business_revenue': 2000000,
                'loan_type': 'business'
            }
            
            result = agent.check({}, business_loan_data)
            
            assert result['passed'] is None
            assert result['applicable'] is False
            assert 'business loan' in result['reason'].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])