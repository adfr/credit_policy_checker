"""
Test to verify the new agent-by-agent processing with tailored data extraction
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, call
from app.services.agent_compliance_checker import AgentComplianceChecker

# Set dummy API key for testing
os.environ['OPENAI_API_KEY'] = 'test-key-123'


class TestAgentByAgentProcessing:
    """Test suite for agent-by-agent processing flow"""
    
    def test_individual_agent_data_extraction(self):
        """Test that each agent gets its own tailored data extraction"""
        
        checker = AgentComplianceChecker()
        
        # Mock the document analyzer to track calls
        with patch.object(checker.document_analyzer, 'process') as mock_process:
            # Mock different responses for different agents
            mock_process.side_effect = [
                # Credit Score Agent extraction
                json.dumps({
                    "extracted_fields": {
                        "average_credit_score": {"value": 742.5, "found": True, "location": "page 1"},
                        "credit_score_borrower_1": {"value": 745, "found": True, "location": "page 1"}
                    },
                    "document_type": "mortgage_application",
                    "extraction_notes": "Credit scores found for both borrowers"
                }),
                # LTV Agent extraction
                json.dumps({
                    "extracted_fields": {
                        "ltv_ratio": {"value": 90.0, "found": True, "location": "page 2"},
                        "loan_amount": {"value": 385000, "found": True, "location": "page 1"},
                        "property_value": {"value": 428000, "found": True, "location": "page 1"}
                    },
                    "document_type": "mortgage_application",
                    "extraction_notes": "LTV calculation data found"
                })
            ]
            
            # Mock agent factory to return mock agents
            with patch.object(checker.agent_factory, 'create_agent') as mock_create_agent:
                mock_agents = []
                for i in range(2):
                    mock_agent = Mock()
                    mock_agent.check.return_value = {
                        'passed': True,
                        'reason': f'Check {i+1} passed',
                        'confidence': 0.95
                    }
                    mock_agent._origin = 'test'
                    mock_agent._origin_reason = 'test reason'
                    mock_agents.append(mock_agent)
                
                mock_create_agent.side_effect = mock_agents
                
                # Define test agents
                selected_agents = [
                    {
                        'agent_id': 'CR_TH_001',
                        'agent_name': 'Credit Score Check',
                        'requirement': 'Average credit score must be above 680',
                        'data_fields': ['average_credit_score', 'credit_score_borrower_1'],
                        'check_type': 'credit_score_threshold'
                    },
                    {
                        'agent_id': 'LTV_TH_001',
                        'agent_name': 'LTV Check',
                        'requirement': 'LTV ratio must be below 95%',
                        'data_fields': ['ltv_ratio', 'loan_amount', 'property_value'],
                        'check_type': 'ltv_threshold'
                    }
                ]
                
                # Run compliance check
                result = checker.check_compliance("Sample document content", selected_agents)
                
                # Verify each agent got its own extraction call
                assert mock_process.call_count == 2
                
                # Verify the extraction prompts were tailored to each agent
                call_args_list = mock_process.call_args_list
                
                # First call should be for credit score agent
                first_prompt = call_args_list[0][0][0]
                assert "Credit Score Check" in first_prompt
                assert "average_credit_score, credit_score_borrower_1" in first_prompt
                assert "ONLY extract the fields: average_credit_score, credit_score_borrower_1" in first_prompt
                
                # Second call should be for LTV agent
                second_prompt = call_args_list[1][0][0]
                assert "LTV Check" in second_prompt
                assert "ltv_ratio, loan_amount, property_value" in second_prompt
                assert "ONLY extract the fields: ltv_ratio, loan_amount, property_value" in second_prompt
                
                # Verify results structure
                assert result['processing_status'] == 'completed'
                assert len(result['agent_results']) == 2
                assert len(result['extracted_data']) == 2
                assert 'CR_TH_001' in result['extracted_data']
                assert 'LTV_TH_001' in result['extracted_data']
    
    def test_agent_specific_data_content(self):
        """Test that agents receive only their specific data"""
        
        checker = AgentComplianceChecker()
        
        with patch.object(checker.document_analyzer, 'process') as mock_process:
            # Mock extraction response
            mock_process.return_value = json.dumps({
                "extracted_fields": {
                    "average_credit_score": {"value": 742.5, "found": True, "location": "page 1"}
                },
                "document_type": "mortgage_application",
                "extraction_notes": "Credit score found"
            })
            
            # Mock agent to capture what data it receives
            received_data = None
            with patch.object(checker.agent_factory, 'create_agent') as mock_create_agent:
                mock_agent = Mock()
                
                def capture_check_call(policy_check, data):
                    nonlocal received_data
                    received_data = data
                    return {
                        'passed': True,
                        'reason': 'Test passed',
                        'confidence': 0.95
                    }
                
                mock_agent.check.side_effect = capture_check_call
                mock_agent._origin = 'test'
                mock_agent._origin_reason = 'test reason'
                mock_create_agent.return_value = mock_agent
                
                # Single agent configuration
                agent_config = {
                    'agent_id': 'CR_TH_001',
                    'agent_name': 'Credit Score Check',
                    'requirement': 'Average credit score must be above 680',
                    'data_fields': ['average_credit_score'],
                    'check_type': 'credit_score_threshold'
                }
                
                # Run compliance check
                checker.check_compliance("Sample document", [agent_config])
                
                # Verify the agent received only the credit score data
                assert received_data is not None
                assert 'average_credit_score' in received_data
                assert received_data['average_credit_score'] == 742.5
                
                # Should not contain unrelated fields
                assert 'ltv_ratio' not in received_data
                assert 'dti_ratio' not in received_data
                
                # Should contain metadata
                assert '_extraction_metadata' in received_data
                assert received_data['_extraction_metadata']['agent_name'] == 'Credit Score Check'
    
    def test_applicant_data_integration_per_agent(self):
        """Test that applicant data is properly integrated per agent"""
        
        checker = AgentComplianceChecker()
        
        with patch.object(checker.document_analyzer, 'process') as mock_process:
            # Mock extraction that finds no credit score in document
            mock_process.return_value = json.dumps({
                "extracted_fields": {
                    "average_credit_score": {"value": None, "found": False, "location": "not found"}
                },
                "document_type": "mortgage_application",
                "extraction_notes": "Credit score not found in document"
            })
            
            # Mock agent
            received_data = None
            with patch.object(checker.agent_factory, 'create_agent') as mock_create_agent:
                mock_agent = Mock()
                
                def capture_check_call(policy_check, data):
                    nonlocal received_data
                    received_data = data
                    return {'passed': True, 'reason': 'Test passed', 'confidence': 0.95}
                
                mock_agent.check.side_effect = capture_check_call
                mock_agent._origin = 'test'
                mock_agent._origin_reason = 'test reason'
                mock_create_agent.return_value = mock_agent
                
                # Agent configuration
                agent_config = {
                    'agent_id': 'CR_TH_001',
                    'agent_name': 'Credit Score Check',
                    'data_fields': ['average_credit_score'],
                    'check_type': 'credit_score_threshold'
                }
                
                # Applicant data with credit score
                applicant_data = {
                    'average_credit_score': 750,
                    'irrelevant_field': 'should not be included'
                }
                
                # Run compliance check
                checker.check_compliance("Sample document", [agent_config], applicant_data)
                
                # Verify applicant data was used for the relevant field
                assert received_data['average_credit_score'] == 750
                
                # Verify irrelevant applicant data was not included
                assert 'irrelevant_field' not in received_data
    
    def test_error_handling_per_agent(self):
        """Test that errors in one agent don't affect others"""
        
        checker = AgentComplianceChecker()
        
        with patch.object(checker.document_analyzer, 'process') as mock_process:
            # Mock successful extraction for both agents
            mock_process.side_effect = [
                json.dumps({
                    "extracted_fields": {"average_credit_score": {"value": 742.5, "found": True}},
                    "document_type": "mortgage_application",
                    "extraction_notes": "Credit score found"
                }),
                json.dumps({
                    "extracted_fields": {"ltv_ratio": {"value": 90.0, "found": True}},
                    "document_type": "mortgage_application", 
                    "extraction_notes": "LTV found"
                })
            ]
            
            with patch.object(checker.agent_factory, 'create_agent') as mock_create_agent:
                # First agent succeeds, second agent fails
                mock_agents = []
                
                # Successful agent
                success_agent = Mock()
                success_agent.check.return_value = {'passed': True, 'reason': 'Success', 'confidence': 0.95}
                success_agent._origin = 'test'
                success_agent._origin_reason = 'test reason'
                mock_agents.append(success_agent)
                
                # Failing agent
                failing_agent = Mock()
                failing_agent.check.side_effect = Exception("Agent failure")
                failing_agent._origin = 'test'
                failing_agent._origin_reason = 'test reason'
                mock_agents.append(failing_agent)
                
                mock_create_agent.side_effect = mock_agents
                
                selected_agents = [
                    {
                        'agent_id': 'CR_TH_001',
                        'agent_name': 'Credit Score Check',
                        'data_fields': ['average_credit_score'],
                        'check_type': 'credit_score_threshold'
                    },
                    {
                        'agent_id': 'LTV_TH_001', 
                        'agent_name': 'LTV Check',
                        'data_fields': ['ltv_ratio'],
                        'check_type': 'ltv_threshold'
                    }
                ]
                
                result = checker.check_compliance("Sample document", selected_agents)
                
                # Verify both agents were processed
                assert len(result['agent_results']) == 2
                
                # First agent should succeed
                assert result['agent_results'][0]['passed'] is True
                
                # Second agent should fail but be handled gracefully
                assert result['agent_results'][1]['passed'] is False
                assert 'Agent execution error' in result['agent_results'][1]['reason']
                assert result['agent_results'][1]['error'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])