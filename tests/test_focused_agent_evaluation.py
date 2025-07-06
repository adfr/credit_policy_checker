"""
Test to verify that agents only evaluate their specific policy checks
and not all available data.
"""

import pytest
import json
from unittest.mock import Mock, patch
from app.services.agent_compliance_checker import AgentComplianceChecker
from agents.universal_agent import UniversalAgent
from agents.hybrid_credit_agent import HybridCreditAgent


class TestFocusedAgentEvaluation:
    """Test suite to ensure agents focus only on their specific checks"""
    
    @pytest.fixture
    def mock_document_analyzer(self):
        """Mock document analyzer to avoid LLM calls"""
        mock = Mock()
        return mock
    
    @pytest.fixture
    def mock_agent_factory(self):
        """Mock agent factory"""
        mock = Mock()
        return mock
    
    @pytest.fixture
    def sample_credit_data(self):
        """Sample credit application data"""
        return {
            "loan_amount": 385000,
            "property_value": 428000,
            "down_payment": 40000,
            "credit_score_borrower_1": 745,
            "credit_score_borrower_2": 740,
            "average_credit_score": 742.5,
            "monthly_income": 15000,
            "monthly_debt": 3000,
            "home_equity_loan_amount": 0,
            "ltv_ratio": 90.0,
            "dti_ratio": 20.0
        }
    
    @pytest.fixture
    def credit_score_agent_config(self):
        """Configuration for credit score checking agent"""
        return {
            "agent_id": "CR_TH_001",
            "agent_name": "Average Credit Score Limit",
            "requirement": "Average credit score must be above 680",
            "data_fields": ["average_credit_score", "credit_score_borrower_1", "credit_score_borrower_2"],
            "check_type": "credit_score_threshold",
            "priority": "critical",
            "agent_type": "threshold"
        }
    
    @pytest.fixture
    def ltv_agent_config(self):
        """Configuration for LTV checking agent"""
        return {
            "agent_id": "LTV_TH_001",
            "agent_name": "Home Equity Loan LTV Limit",
            "requirement": "LTV ratio must be below 95%",
            "data_fields": ["ltv_ratio", "loan_amount", "property_value"],
            "check_type": "ltv_threshold",
            "priority": "critical",
            "agent_type": "threshold"
        }
    
    @pytest.fixture
    def dti_agent_config(self):
        """Configuration for DTI checking agent"""
        return {
            "agent_id": "DTI_TH_001",
            "agent_name": "Debt-to-Income Ratio Limit",
            "requirement": "DTI ratio must be below 43%",
            "data_fields": ["dti_ratio", "monthly_income", "monthly_debt"],
            "check_type": "dti_threshold",
            "priority": "high",
            "agent_type": "threshold"
        }
    
    def test_agent_receives_only_relevant_data(self, mock_document_analyzer, mock_agent_factory, 
                                               sample_credit_data, credit_score_agent_config):
        """Test that agents receive only the data fields they need"""
        
        # Setup
        checker = AgentComplianceChecker()
        checker.document_analyzer = mock_document_analyzer
        checker.agent_factory = mock_agent_factory
        
        # Create a mock agent
        mock_agent = Mock()
        mock_agent.check = Mock(return_value={
            "passed": True,
            "reason": "Credit score check passed",
            "confidence": 0.95
        })
        mock_agent_factory.create_agent.return_value = mock_agent
        
        # Run check with single agent
        selected_agents = [credit_score_agent_config]
        checker._run_agent_checks(selected_agents, sample_credit_data)
        
        # Verify the agent received only credit score related data
        mock_agent.check.assert_called_once()
        _, received_data = mock_agent.check.call_args[0]
        
        # Should only contain the fields specified in data_fields
        expected_fields = set(credit_score_agent_config["data_fields"])
        expected_fields.add("_extraction_metadata")  # Always included
        
        assert set(received_data.keys()) <= expected_fields
        assert "average_credit_score" in received_data
        assert "ltv_ratio" not in received_data  # Should not include LTV data
        assert "dti_ratio" not in received_data  # Should not include DTI data
    
    def test_multiple_agents_receive_different_data(self, mock_document_analyzer, mock_agent_factory,
                                                    sample_credit_data, credit_score_agent_config,
                                                    ltv_agent_config, dti_agent_config):
        """Test that different agents receive different subsets of data"""
        
        # Setup
        checker = AgentComplianceChecker()
        checker.document_analyzer = mock_document_analyzer
        checker.agent_factory = mock_agent_factory
        
        # Track what data each agent receives
        agent_data_received = {}
        
        def create_mock_agent(check_type, config):
            mock_agent = Mock()
            agent_id = config.get('agent_id')
            
            def mock_check(policy_check, data):
                agent_data_received[agent_id] = set(data.keys())
                return {
                    "passed": True,
                    "reason": f"{agent_id} check passed",
                    "confidence": 0.95
                }
            
            mock_agent.check = mock_check
            return mock_agent
        
        mock_agent_factory.create_agent.side_effect = create_mock_agent
        
        # Run checks with multiple agents
        selected_agents = [credit_score_agent_config, ltv_agent_config, dti_agent_config]
        checker._run_agent_checks(selected_agents, sample_credit_data)
        
        # Verify each agent received only its relevant data
        credit_score_fields = set(credit_score_agent_config["data_fields"])
        credit_score_fields.add("_extraction_metadata")
        assert agent_data_received["CR_TH_001"] <= credit_score_fields
        
        ltv_fields = set(ltv_agent_config["data_fields"])
        ltv_fields.add("_extraction_metadata")
        assert agent_data_received["LTV_TH_001"] <= ltv_fields
        
        dti_fields = set(dti_agent_config["data_fields"])
        dti_fields.add("_extraction_metadata")
        assert agent_data_received["DTI_TH_001"] <= dti_fields
        
        # Verify no overlap of exclusive fields
        assert "average_credit_score" in agent_data_received["CR_TH_001"]
        assert "average_credit_score" not in agent_data_received["LTV_TH_001"]
        assert "average_credit_score" not in agent_data_received["DTI_TH_001"]
    
    @patch('agents.base_agent.BaseAgent.process')
    def test_universal_agent_focused_prompt(self, mock_process, credit_score_agent_config):
        """Test that UniversalAgent generates focused prompts"""
        
        # Setup
        mock_process.return_value = json.dumps({
            "passed": True,
            "calculation": "Average credit score: 742.5",
            "threshold_checked": "680",
            "actual_value": "742.5",
            "confidence": 0.95,
            "reason": "Average credit score of 742.5 exceeds minimum requirement of 680"
        })
        
        agent = UniversalAgent(credit_score_agent_config)
        
        # Only provide credit score data
        limited_data = {
            "average_credit_score": 742.5,
            "credit_score_borrower_1": 745,
            "credit_score_borrower_2": 740
        }
        
        result = agent.check({}, limited_data)
        
        # Verify the prompt contains strict focusing instructions
        mock_process.assert_called_once()
        prompt = mock_process.call_args[0][0]
        
        assert "CRITICAL: You MUST ONLY evaluate the specific requirement" in prompt
        assert "DO NOT evaluate or comment on ANY other aspect" in prompt
        assert "Available Data (ONLY data relevant to your check)" in prompt
        assert "Your response should be laser-focused on ONLY your assigned check" in prompt
        
        # Verify result is focused
        assert result["passed"] is True
        assert "742.5" in result["reason"]
        assert "680" in result["reason"]
        # Should not mention LTV, DTI, or other aspects
        assert "ltv" not in result["reason"].lower()
        assert "dti" not in result["reason"].lower()
        assert "loan" not in result["reason"].lower()
    
    @patch('agents.base_agent.BaseAgent.process')
    def test_hybrid_agent_focused_prompt(self, mock_process):
        """Test that HybridCreditAgent generates focused prompts"""
        
        # Setup
        mock_process.return_value = json.dumps({
            "passed": True,
            "reason": "LTV ratio of 90% is below the 95% limit",
            "confidence": 0.95,
            "requirements_evaluated": ["LTV_001"],
            "linked_impacts": [],
            "recommendations": []
        })
        
        with patch('agents.hybrid_credit_agent.GraphDatabase.driver'):
            agent = HybridCreditAgent()
            agent.driver = None  # Disable graph DB for this test
            
            policy_check = {
                "check_type": "ltv_threshold",
                "description": "Check LTV ratio"
            }
            
            # Only provide LTV data
            limited_data = {
                "ltv_ratio": 90.0,
                "loan_amount": 385000,
                "property_value": 428000
            }
            
            result = agent._hybrid_check(policy_check, limited_data, [], {})
            
            # Verify the prompt contains strict focusing instructions
            mock_process.assert_called_once()
            prompt = mock_process.call_args[0][0]
            
            assert "CRITICAL: You MUST ONLY evaluate the specific policy check" in prompt
            assert "Focus your reasoning ONLY on the specific requirement" in prompt
            assert "Use ONLY the data fields provided" in prompt
            assert "explanation focused ONLY on the specific requirement checked" in prompt
    
    def test_agent_results_are_focused(self, mock_document_analyzer, mock_agent_factory,
                                      sample_credit_data, credit_score_agent_config,
                                      ltv_agent_config):
        """Test that agent results mention only their specific checks"""
        
        # Setup
        checker = AgentComplianceChecker()
        checker.document_analyzer = mock_document_analyzer
        checker.agent_factory = mock_agent_factory
        
        # Create mock agents with focused responses
        def create_mock_agent(check_type, config):
            mock_agent = Mock()
            agent_id = config.get('agent_id')
            
            if agent_id == "CR_TH_001":
                mock_agent.check.return_value = {
                    "passed": True,
                    "reason": "Average credit score of 742.5 exceeds minimum requirement of 680",
                    "confidence": 0.95,
                    "calculation": "Average: (745 + 740) / 2 = 742.5"
                }
            elif agent_id == "LTV_TH_001":
                mock_agent.check.return_value = {
                    "passed": True,
                    "reason": "LTV ratio of 90% is below the maximum limit of 95%",
                    "confidence": 0.95,
                    "calculation": "LTV = 385000 / 428000 = 0.90"
                }
            
            return mock_agent
        
        mock_agent_factory.create_agent.side_effect = create_mock_agent
        
        # Run checks
        selected_agents = [credit_score_agent_config, ltv_agent_config]
        results = checker._run_agent_checks(selected_agents, sample_credit_data)
        
        # Verify each result is focused on its specific check
        credit_result = next(r for r in results if r['agent_config']['agent_id'] == 'CR_TH_001')
        ltv_result = next(r for r in results if r['agent_config']['agent_id'] == 'LTV_TH_001')
        
        # Credit score result should only mention credit scores
        assert "credit score" in credit_result['reason'].lower()
        assert "ltv" not in credit_result['reason'].lower()
        assert "742.5" in credit_result['reason']
        
        # LTV result should only mention LTV
        assert "ltv" in ltv_result['reason'].lower()
        assert "credit score" not in ltv_result['reason'].lower()
        assert "90%" in ltv_result['reason']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])