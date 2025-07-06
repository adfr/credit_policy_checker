"""
Test to verify agents handle missing required fields appropriately
"""

import pytest
import json
import os
from unittest.mock import Mock, patch
from agents.universal_agent import UniversalAgent
from agents.hybrid_credit_agent import HybridCreditAgent

# Set dummy API key for testing
os.environ['OPENAI_API_KEY'] = 'test-key-123'


class TestMissingFieldsHandling:
    """Test suite for missing fields handling"""
    
    def test_universal_agent_missing_fields(self):
        """Test that universal agent handles missing fields correctly"""
        
        # Create agent that requires home_equity_loan_amount
        check_definition = {
            'agent_id': 'HE_TH_001',
            'agent_name': 'Home Equity Loan Amount Limit',
            'requirement': 'Home equity loan amount must be below $100,000',
            'data_fields': ['home_equity_loan_amount', 'property_value'],
            'check_type': 'home_equity_loan_amount_threshold'
        }
        
        agent = UniversalAgent(check_definition)
        
        # Provide data without home_equity_loan_amount
        incomplete_data = {
            'property_value': 428000
            # Missing: home_equity_loan_amount
        }
        
        result = agent.check({}, incomplete_data)
        
        assert result['passed'] is False
        assert 'home_equity_loan_amount' in result['reason']
        assert 'not found in the document' in result['reason']
        assert result['missing_fields'] == ['home_equity_loan_amount']
        assert result['confidence'] == 1.0
    
    def test_universal_agent_all_fields_present(self):
        """Test that universal agent processes normally when all fields are present"""
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            mock_process.return_value = json.dumps({
                "passed": True,
                "calculation": "$50,000 < $100,000",
                "threshold_checked": "$100,000",
                "actual_value": "$50,000",
                "confidence": 0.95,
                "reason": "Home equity loan amount is within limit"
            })
            
            check_definition = {
                'agent_id': 'HE_TH_001',
                'agent_name': 'Home Equity Loan Amount Limit',
                'requirement': 'Home equity loan amount must be below $100,000',
                'data_fields': ['home_equity_loan_amount', 'property_value'],
                'check_type': 'home_equity_loan_amount_threshold'
            }
            
            agent = UniversalAgent(check_definition)
            
            # Provide complete data
            complete_data = {
                'home_equity_loan_amount': 50000,
                'property_value': 428000
            }
            
            result = agent.check({}, complete_data)
            
            assert result['passed'] is True
            assert 'missing_fields' not in result
            mock_process.assert_called_once()
    
    def test_universal_agent_multiple_missing_fields(self):
        """Test handling of multiple missing fields"""
        
        check_definition = {
            'agent_id': 'DTI_TH_001',
            'agent_name': 'DTI Ratio Check',
            'requirement': 'DTI ratio must be below 43%',
            'data_fields': ['dti_ratio', 'monthly_income', 'monthly_debt'],
            'check_type': 'dti_threshold'
        }
        
        agent = UniversalAgent(check_definition)
        
        # Missing all required fields
        empty_data = {}
        
        result = agent.check({}, empty_data)
        
        assert result['passed'] is False
        assert all(field in result['reason'] for field in ['dti_ratio', 'monthly_income', 'monthly_debt'])
        assert len(result['missing_fields']) == 3
    
    @patch('agents.hybrid_credit_agent.GraphDatabase.driver')
    def test_hybrid_agent_missing_fields(self, mock_driver):
        """Test that hybrid agent handles missing fields correctly"""
        
        mock_driver.return_value = None
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Mock fallback to generic missing field message
            mock_process.side_effect = Exception("Mocked LLM failure")
            
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
            
            # Missing home_equity_loan_amount
            incomplete_data = {
                'property_value': 428000
            }
            
            result = agent.check(policy_check, incomplete_data)
            
            assert result['passed'] is False
            assert 'home_equity_loan_amount' in result['reason']
            assert 'not found in the document' in result['reason']
            assert result['methodology'] == 'hybrid_graph_llm'
            assert result['graph_requirements_used'] == 0
    
    def test_universal_agent_null_values_treated_as_missing(self):
        """Test that null values are treated as missing fields"""
        
        check_definition = {
            'agent_id': 'CR_TH_001',
            'agent_name': 'Credit Score Check',
            'requirement': 'Average credit score must be above 680',
            'data_fields': ['average_credit_score'],
            'check_type': 'credit_score_threshold'
        }
        
        agent = UniversalAgent(check_definition)
        
        # Provide null value
        data_with_null = {
            'average_credit_score': None
        }
        
        result = agent.check({}, data_with_null)
        
        assert result['passed'] is False
        assert 'average_credit_score' in result['reason']
        assert result['missing_fields'] == ['average_credit_score']
    
    def test_quantitative_analysis_missing_fields(self):
        """Test quantitative analysis handles missing fields"""
        
        check_definition = {
            'agent_id': 'LTV_CALC_001',
            'agent_name': 'LTV Calculation',
            'requirement': 'Calculate and verify LTV ratio',
            'data_fields': ['loan_amount', 'property_value'],
            'check_type': 'ltv_calculation',
            'complexity': 'quantitative'
        }
        
        agent = UniversalAgent(check_definition)
        
        # Missing loan_amount
        incomplete_data = {
            'property_value': 428000
        }
        
        result = agent.check({}, incomplete_data)
        
        assert result['passed'] is False
        assert 'loan_amount' in result['reason']
        assert 'perform calculations' in result['reason']
        assert result['missing_fields'] == ['loan_amount']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])