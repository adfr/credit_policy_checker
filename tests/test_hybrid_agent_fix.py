"""
Test to verify hybrid agent works correctly with focused data and proper error handling
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from agents.hybrid_credit_agent import HybridCreditAgent
from agents.universal_agent import UniversalAgent

# Set a dummy API key for testing
os.environ['OPENAI_API_KEY'] = 'test-key-123'


class TestHybridAgentFix:
    """Test suite to verify hybrid agent fixes"""
    
    @patch('agents.hybrid_credit_agent.GraphDatabase.driver')
    def test_hybrid_agent_with_policy_check(self, mock_driver):
        """Test that hybrid agent works when given proper policy check"""
        
        # Mock the driver to return None (no graph connection)
        mock_driver.return_value = None
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Mock successful response
            mock_process.return_value = json.dumps({
                "passed": True,
                "reason": "Credit score of 742.5 exceeds minimum requirement",
                "confidence": 0.95,
                "requirements_evaluated": ["CR_001"],
                "linked_impacts": [],
                "recommendations": []
            })
            
            agent = HybridCreditAgent()
            agent.driver = None  # No graph connection
            
            policy_check = {
                'check_type': 'credit_score_threshold',
                'description': 'Average Credit Score Limit',
                'criteria': 'Average credit score must be above 680'
            }
            
            credit_data = {
                'average_credit_score': 742.5
            }
            
            result = agent.check(policy_check, credit_data)
            
            assert result['passed'] is True
            assert 'methodology' in result
            assert result['methodology'] == 'hybrid_graph_llm'
    
    @patch('agents.hybrid_credit_agent.GraphDatabase.driver')
    def test_hybrid_agent_handles_api_error(self, mock_driver):
        """Test that hybrid agent properly handles OpenAI API errors"""
        
        mock_driver.return_value = None
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Mock API error response (as returned by base agent)
            mock_process.return_value = json.dumps({
                "passed": False,
                "reason": "OpenAI API error: Connection timeout",
                "confidence": 0.0,
                "error": True
            })
            
            agent = HybridCreditAgent()
            agent.driver = None
            
            policy_check = {
                'check_type': 'credit_score_threshold',
                'description': 'Average Credit Score Limit'
            }
            
            credit_data = {'average_credit_score': 742.5}
            
            result = agent.check(policy_check, credit_data)
            
            assert result['passed'] is False
            assert 'OpenAI API error' in result['reason']
            assert result['methodology'] == 'hybrid_graph_llm'
    
    def test_universal_agent_handles_api_error(self):
        """Test that universal agent properly handles OpenAI API errors"""
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Mock API error response
            mock_process.return_value = json.dumps({
                "passed": False,
                "reason": "OpenAI API error: Rate limit exceeded",
                "confidence": 0.0,
                "error": True
            })
            
            check_definition = {
                'agent_id': 'TEST_001',
                'agent_name': 'Test Agent',
                'requirement': 'Test requirement',
                'data_fields': ['test_field'],
                'check_type': 'test_threshold'
            }
            
            agent = UniversalAgent(check_definition)
            
            policy_check = {}
            data = {'test_field': 100}
            
            result = agent.check(policy_check, data)
            
            assert result['passed'] is False
            assert 'OpenAI API error' in result['reason']
            assert result['agent_type'] == 'universal'
    
    @patch('agents.hybrid_credit_agent.GraphDatabase.driver')
    def test_hybrid_agent_with_graph_connection(self, mock_driver_class):
        """Test hybrid agent with mocked graph database"""
        
        # Create mock driver instance
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock graph query results
        mock_result = MagicMock()
        mock_result.__iter__ = Mock(return_value=iter([
            MagicMock(data=Mock(return_value={
                'id': 'CR_001',
                'name': 'Credit Score Requirement',
                'description': 'Minimum credit score',
                'type': 'threshold',
                'threshold': '680',
                'conditions': None
            }))
        ]))
        mock_session.run.return_value = mock_result
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            mock_process.return_value = json.dumps({
                "passed": True,
                "reason": "Compliance check passed",
                "confidence": 0.95,
                "requirements_evaluated": ["CR_001"],
                "linked_impacts": [],
                "recommendations": []
            })
            
            agent = HybridCreditAgent()
            agent.driver = mock_driver
            
            policy_check = {
                'check_type': 'credit_score_threshold',
                'description': 'Credit Score Check'
            }
            
            result = agent.check(policy_check, {'average_credit_score': 742.5})
            
            assert result['passed'] is True
            assert result['graph_requirements_used'] > 0
            assert result['methodology'] == 'hybrid_graph_llm'
    
    def test_universal_agent_focused_data(self):
        """Test that universal agent only uses provided data fields"""
        
        with patch('agents.base_agent.BaseAgent.process') as mock_process:
            # Track what prompt was sent
            sent_prompt = None
            
            def capture_prompt(prompt):
                nonlocal sent_prompt
                sent_prompt = prompt
                return json.dumps({
                    "passed": True,
                    "calculation": "742.5 > 680",
                    "threshold_checked": "680",
                    "actual_value": "742.5",
                    "confidence": 0.95,
                    "reason": "Credit score passes threshold"
                })
            
            mock_process.side_effect = capture_prompt
            
            check_definition = {
                'agent_id': 'CR_TH_001',
                'agent_name': 'Credit Score Check',
                'requirement': 'Average credit score must be above 680',
                'data_fields': ['average_credit_score'],
                'check_type': 'credit_score_threshold'
            }
            
            agent = UniversalAgent(check_definition)
            
            # Only provide credit score data
            limited_data = {'average_credit_score': 742.5}
            
            result = agent.check({}, limited_data)
            
            # Verify the prompt only contains the limited data
            assert 'average_credit_score' in sent_prompt
            assert '742.5' in sent_prompt
            # Should not contain other fields
            assert 'ltv_ratio' not in sent_prompt
            assert 'dti_ratio' not in sent_prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])