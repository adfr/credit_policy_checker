#!/usr/bin/env python3
"""
Demo script for the new Agent-Based Policy Extraction and Compliance Checking workflow

This script demonstrates:
1. Extracting policy agents from a policy document using LLM
2. Selecting relevant agents for compliance checking
3. Using selected agents to check document compliance
"""

import os
import sys
sys.path.append('.')

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from app.services.document_processor import DocumentProcessor
from app.services.policy_agent_extractor import PolicyAgentExtractor
from app.services.agent_compliance_checker import AgentComplianceChecker
import json

def demo_agent_workflow():
    """Demonstrate the complete agent-based workflow"""
    
    print("🤖 Agent-Based Policy Extraction and Compliance Checking Demo")
    print("=" * 70)
    
    # Initialize services
    document_processor = DocumentProcessor()
    agent_extractor = PolicyAgentExtractor()
    compliance_checker = AgentComplianceChecker()
    
    # Step 1: Extract Policy Agents from Policy Document
    print("\n📋 Step 1: Extracting Policy Agents from Policy Document")
    print("-" * 50)
    
    policy_file = "consumer-bank-credit-policy-v2.pdf"
    if not os.path.exists(policy_file):
        print(f"❌ Policy file not found: {policy_file}")
        print("Please ensure the policy document is in the current directory")
        return
    
    print(f"📄 Processing policy document: {policy_file}")
    
    # Extract agents using LLM
    extraction_result = document_processor.extract_policy_agents(policy_file, "credit lending")
    
    if 'error' in extraction_result:
        print(f"❌ Error extracting agents: {extraction_result['error']}")
        return
    
    extracted_agents = extraction_result['extracted_agents']
    validation = extraction_result['validation']
    
    print(f"✅ Successfully extracted {validation['agent_counts']['threshold'] + validation['agent_counts']['criteria'] + validation['agent_counts']['score'] + validation['agent_counts']['qualitative']} agents")
    print(f"   - Threshold Agents: {validation['agent_counts']['threshold']}")
    print(f"   - Criteria Agents: {validation['agent_counts']['criteria']}")
    print(f"   - Score Agents: {validation['agent_counts']['score']}")
    print(f"   - Qualitative Agents: {validation['agent_counts']['qualitative']}")
    
    # Show some example agents
    print("\n🔍 Sample Extracted Agents:")
    
    # Show first threshold agent
    if extracted_agents.get('threshold_agents'):
        agent = extracted_agents['threshold_agents'][0]
        print(f"   🎯 Threshold Agent: {agent.get('agent_name')}")
        print(f"      ID: {agent.get('agent_id')}")
        print(f"      Requirement: {agent.get('requirement')}")
        print(f"      Priority: {agent.get('priority')}")
    
    # Show first criteria agent
    if extracted_agents.get('criteria_agents'):
        agent = extracted_agents['criteria_agents'][0]
        print(f"   ✓ Criteria Agent: {agent.get('agent_name')}")
        print(f"      ID: {agent.get('agent_id')}")
        print(f"      Requirement: {agent.get('requirement')}")
        print(f"      Priority: {agent.get('priority')}")
    
    # Step 2: Simulate Agent Selection (in real app, user would select via UI)
    print("\n🎯 Step 2: Selecting Relevant Agents")
    print("-" * 50)
    
    selected_agents = []
    
    # Select first 3 agents from each type for demo
    for agent_type in ['threshold_agents', 'criteria_agents', 'score_agents', 'qualitative_agents']:
        agents = extracted_agents.get(agent_type, [])
        selected_agents.extend(agents[:2])  # Select first 2 from each type
    
    print(f"📊 Selected {len(selected_agents)} agents for compliance checking")
    
    # Get data requirements for selected agents
    requirements = compliance_checker.get_agent_summary(selected_agents)
    print(f"📋 Data fields required: {len(requirements['data_requirements'])}")
    print(f"   Example fields: {requirements['data_requirements'][:5]}")  # Show first 5
    
    # Step 3: Check Document Compliance with Selected Agents
    print("\n🔍 Step 3: Checking Document Compliance")
    print("-" * 50)
    
    # Use the credit memo document for compliance checking
    assessment_file = "mortgage-credit-memo.pdf"
    if not os.path.exists(assessment_file):
        print(f"❌ Assessment file not found: {assessment_file}")
        print("Please ensure the assessment document is in the current directory")
        return
    
    print(f"📄 Checking compliance for: {assessment_file}")
    
    # Run compliance check
    compliance_result = document_processor.check_document_compliance(
        assessment_file, 
        selected_agents,
        applicant_data=None  # Could provide structured data here
    )
    
    if 'error' in compliance_result:
        print(f"❌ Error checking compliance: {compliance_result['error']}")
        return
    
    # Analyze results
    compliance_summary = compliance_result['compliance_results']['compliance_summary']
    agent_results = compliance_result['compliance_results']['agent_results']
    
    print(f"📊 Compliance Assessment Results:")
    print(f"   Overall Status: {compliance_summary.get('overall_status')}")
    print(f"   Decision: {compliance_summary.get('decision')}")
    print(f"   Confidence Score: {compliance_summary.get('confidence_score', 0):.2f}")
    
    stats = compliance_summary.get('statistics', {})
    print(f"   Agent Results: {stats.get('passed_agents', 0)}/{stats.get('total_agents', 0)} passed")
    print(f"   Pass Rate: {stats.get('pass_rate', 0):.1%}")
    
    # Show failure breakdown
    failures = compliance_summary.get('failure_breakdown', {})
    if failures.get('critical_failures', 0) > 0:
        print(f"   ⚠️  Critical Failures: {failures['critical_failures']}")
    if failures.get('high_priority_failures', 0) > 0:
        print(f"   🔸 High Priority Failures: {failures['high_priority_failures']}")
    if failures.get('warnings', 0) > 0:
        print(f"   💡 Warnings: {failures['warnings']}")
    
    # Show some example agent results
    print("\n📋 Sample Agent Results:")
    for result in agent_results[:3]:  # Show first 3 results
        status = "✅ PASS" if result.get('passed') else "❌ FAIL"
        print(f"   {status} {result.get('agent_id')} - {result.get('reason', 'No reason provided')[:80]}...")
    
    # Show recommendations
    recommendations = compliance_summary.get('recommendations', [])
    if recommendations:
        print(f"\n💡 Recommendations:")
        for rec in recommendations[:3]:  # Show first 3
            print(f"   • {rec}")
    
    # Show next steps
    next_steps = compliance_summary.get('next_steps', [])
    if next_steps:
        print(f"\n📝 Next Steps:")
        for step in next_steps:
            print(f"   • {step}")
    
    print(f"\n🎉 Demo completed successfully!")
    print("\n" + "=" * 70)
    print("This demonstrates the new agent-based approach:")
    print("1. ✅ LLM extracts specific policy agents from documents")
    print("2. ✅ User can select relevant agents for their use case")
    print("3. ✅ LLM performs compliance checking using selected agents")
    print("4. ✅ No regex pattern matching - pure LLM intelligence")
    print("5. ✅ Comprehensive compliance assessment with detailed reasoning")

def test_individual_components():
    """Test individual components of the agent workflow"""
    
    print("\n🧪 Testing Individual Components")
    print("=" * 70)
    
    # Test 1: Policy Agent Extraction
    print("\n1. Testing Policy Agent Extraction")
    extractor = PolicyAgentExtractor()
    
    sample_policy = """
    Loan-to-Value Ratio Requirements:
    - Conventional loans: Maximum LTV of 80%
    - FHA loans: Maximum LTV of 96.5%
    - VA loans: Maximum LTV of 100%
    
    Credit Score Requirements:
    - Minimum FICO score of 620 for conventional loans
    - Minimum FICO score of 580 for FHA loans
    
    Employment History:
    - Borrower must have 2+ years continuous employment
    - Self-employed borrowers need 2 years tax returns
    """
    
    agents = extractor.extract_policy_agents(sample_policy, "credit")
    if 'error' not in agents:
        print(f"✅ Extracted {sum(len(agents.get(k, [])) for k in ['threshold_agents', 'criteria_agents', 'score_agents', 'qualitative_agents'])} agents from sample policy")
    else:
        print(f"❌ Error in extraction: {agents['error']}")
    
    # Test 2: Agent Creation
    print("\n2. Testing Agent Creation")
    from agents.policy_agents import AgentFactory
    
    sample_agent_config = {
        'agent_id': 'TH001',
        'agent_name': 'LTV Ratio Check',
        'agent_type': 'threshold',
        'requirement': 'LTV must not exceed 80%',
        'threshold_value': 80,
        'threshold_type': 'maximum',
        'data_fields': ['loan_amount', 'property_value'],
        'priority': 'critical'
    }
    
    agent = AgentFactory.create_agent(sample_agent_config)
    print(f"✅ Created agent: {type(agent).__name__}")
    
    # Test 3: Compliance Checking
    print("\n3. Testing Compliance Checking")
    checker = AgentComplianceChecker()
    
    sample_document = """
    Loan Application Summary:
    - Loan Amount: $400,000
    - Property Value: $500,000
    - FICO Score: 750
    - Employment: 3 years at current job
    - Annual Income: $120,000
    """
    
    sample_applicant_data = {
        'loan_amount': 400000,
        'property_value': 500000,
        'fico_score': 750,
        'employment_years': 3,
        'annual_income': 120000
    }
    
    # Create a simple agent for testing
    test_agents = [sample_agent_config]
    
    result = checker.check_compliance(sample_document, test_agents, sample_applicant_data)
    print(f"✅ Compliance check completed with {len(result['agent_results'])} agent results")
    
    print("\n✅ All component tests completed!")

if __name__ == "__main__":
    print("🚀 Starting Agent-Based Policy Checking Demo")
    
    # Check if we have the required environment
    if not os.environ.get('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key to run this demo")
        sys.exit(1)
    
    try:
        # Run the full demo
        demo_agent_workflow()
        
        # Optionally run component tests
        print("\n" + "="*70)
        response = input("Would you like to run component tests? (y/n): ")
        if response.lower() == 'y':
            test_individual_components()
            
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc() 