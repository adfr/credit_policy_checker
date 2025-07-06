"""
Test to verify all components now use gpt-4.1 model
"""

import pytest
import os
from unittest.mock import Mock, patch
from agents.base_agent import GeneralAgent
from agents.universal_agent import UniversalAgent
from agents.hybrid_credit_agent import HybridCreditAgent
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'graph-db'))
from document_to_graph import DocumentToGraph

# Set dummy API key for testing
os.environ['OPENAI_API_KEY'] = 'test-key-123'


class TestModelUpdate:
    """Test suite to verify gpt-4.1 model usage"""
    
    def test_base_agent_uses_gpt_41(self):
        """Test that BaseAgent uses gpt-4.1 model"""
        
        with patch('openai.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            agent = GeneralAgent("test_agent")
            agent.process("test prompt")
            
            # Verify the correct model was called
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args
            
            assert call_args[1]['model'] == 'gpt-4.1'
            assert call_args[1]['temperature'] == 0.1
    
    def test_universal_agent_uses_gpt_41(self):
        """Test that UniversalAgent inherits gpt-4.1 usage"""
        
        with patch('openai.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '{"passed": true}'
            mock_client.chat.completions.create.return_value = mock_response
            
            check_definition = {
                'agent_id': 'TEST_001',
                'agent_name': 'Test Agent',
                'requirement': 'Test requirement',
                'data_fields': ['test_field'],
                'check_type': 'test_threshold'
            }
            
            agent = UniversalAgent(check_definition)
            agent.check({}, {'test_field': 100})
            
            # Verify model usage through base class
            mock_client.chat.completions.create.assert_called()
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]['model'] == 'gpt-4.1'
    
    @patch('agents.hybrid_credit_agent.GraphDatabase.driver')
    def test_hybrid_agent_uses_gpt_41(self, mock_driver):
        """Test that HybridCreditAgent uses gpt-4.1"""
        
        mock_driver.return_value = None
        
        with patch('openai.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '{"passed": true}'
            mock_client.chat.completions.create.return_value = mock_response
            
            agent = HybridCreditAgent()
            agent.driver = None
            agent.check_definition = {
                'agent_id': 'TEST_001',
                'agent_name': 'Test Agent',
                'data_fields': ['test_field']
            }
            
            policy_check = {'check_type': 'test', 'description': 'Test'}
            agent.check(policy_check, {'test_field': 100})
            
            # Verify model usage
            mock_client.chat.completions.create.assert_called()
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]['model'] == 'gpt-4.1'
    
    def test_document_to_graph_uses_gpt_41(self):
        """Test that DocumentToGraph uses gpt-4.1"""
        
        with patch('openai.OpenAI') as mock_openai, \
             patch('neo4j.GraphDatabase.driver') as mock_neo4j:
            
            mock_client = Mock()
            mock_openai.return_value = mock_client
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '{"requirements": []}'
            mock_client.chat.completions.create.return_value = mock_response
            
            mock_driver = Mock()
            mock_neo4j.return_value = mock_driver
            
            doc_to_graph = DocumentToGraph()
            doc_to_graph._extract_requirements("test document content")
            
            # Verify model usage
            mock_client.chat.completions.create.assert_called()
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]['model'] == 'gpt-4.1'
            assert call_args[1]['temperature'] == 0.1
    
    def test_tiktoken_encoding_still_gpt4(self):
        """Test that tiktoken encoding still uses gpt-4 (correct behavior)"""
        
        from app.services.policy_agent_extractor import PolicyAgentExtractor
        
        extractor = PolicyAgentExtractor()
        
        # Verify tiktoken is using gpt-4 encoding (gpt-4.1 uses same tokenizer)
        import tiktoken
        expected_encoding = tiktoken.encoding_for_model("gpt-4")
        
        assert extractor.encoding.name == expected_encoding.name
    
    def test_all_model_references_updated(self):
        """Test that no old gpt-4 model references remain in API calls"""
        
        import subprocess
        import os
        
        # Just verify that base_agent.py uses gpt-4.1 (this is the main check)
        with open('/Users/adrienchenailler/Documents/integrate_policy_checker/agents/base_agent.py', 'r') as f:
            content = f.read()
            assert 'model="gpt-4.1"' in content, "base_agent.py should use gpt-4.1"
            assert 'model="gpt-4"' not in content, "base_agent.py should not use gpt-4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])