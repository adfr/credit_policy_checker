#!/usr/bin/env python3

import os
from app.services.document_processor import DocumentProcessor
from agents.agent_factory import AgentFactory
import json

def test_integrated_system():
    """Test the integrated document processing and agent creation system"""
    
    print("=== Testing Integrated Policy Checker with Graph Database ===\n")
    
    # Initialize components
    doc_processor = DocumentProcessor()
    agent_factory = AgentFactory()
    
    # Sample credit application data
    credit_data = {
        "applicant": {
            "name": "Jane Smith",
            "age": 42,
            "income": 95000,
            "credit_score": 750,
            "employment_status": "Full-time",
            "years_employed": 8
        },
        "loan_details": {
            "amount": 350000,
            "purpose": "Home Purchase",
            "term_years": 20,
            "interest_rate": 3.9
        },
        "financial_history": {
            "bankruptcies": 0,
            "late_payments": 1,
            "debt_to_income_ratio": 0.28,
            "existing_loans": 2
        }
    }
    
    # Test document path (you'll need to update this)
    test_doc_path = "path/to/your/policy/document.pdf"
    
    print("1. Processing Document with Hybrid Approach...")
    print("-" * 50)
    
    if os.path.exists(test_doc_path):
        # Process document with graph creation
        result = doc_processor.process_with_graph(test_doc_path, "credit_policy")
        
        print(f"Methodology used: {result.get('methodology', 'unknown')}")
        print(f"Policy agents extracted: {len(result.get('extracted_agents', {}).get('policy_checks', []))}")
        
        if 'graph_creation' in result:
            graph_info = result['graph_creation']
            print(f"Graph requirements extracted: {graph_info.get('requirements_extracted', 0)}")
            print(f"Graph linkages created: {graph_info.get('linkages_created', 0)}")
        
        print("\n2. Creating Agents with Hybrid Approach...")
        print("-" * 50)
        
        # Get extracted policy checks
        policy_checks = result.get('extracted_agents', {}).get('policy_checks', [])
        
        for i, check in enumerate(policy_checks[:3]):  # Test first 3 checks
            print(f"\nCreating agent for: {check.get('check_type', 'Unknown')}")
            
            # Create agent (will automatically use hybrid if appropriate)
            agent = agent_factory.create_agent(
                check_type=check.get('check_type'),
                check_definition=check
            )
            
            print(f"Agent type created: {type(agent).__name__}")
            
            # Test the agent
            check_result = agent.check(check, credit_data)
            print(f"Check result: {'PASSED' if check_result.get('passed') else 'FAILED'}")
            print(f"Reason: {check_result.get('reason', 'No reason provided')}")
            
            if 'graph_requirements_used' in check_result:
                print(f"Graph requirements used: {check_result['graph_requirements_used']}")
                print(f"Linked requirements considered: {check_result['linked_requirements_considered']}")
    
    else:
        print(f"Test document not found at: {test_doc_path}")
        print("\nDemonstrating system without document...")
        
        # Create sample policy check
        sample_check = {
            "check_type": "Credit Score Requirement",
            "description": "Applicant must have minimum credit score",
            "criteria": "Credit score >= 650",
            "threshold": 650
        }
        
        # Create agent
        agent = agent_factory.create_agent(
            check_type=sample_check['check_type'],
            check_definition=sample_check
        )
        
        print(f"Agent created: {type(agent).__name__}")
        print(f"Graph database available: {agent_factory.graph_available}")
    
    print("\n3. System Integration Summary:")
    print("-" * 50)
    print(f"Document Processor: {'✓' if doc_processor else '✗'}")
    print(f"Graph Builder: {'✓' if doc_processor.graph_builder else '✗'}")
    print(f"Agent Factory: {'✓' if agent_factory else '✗'}")
    print(f"Neo4j Connection: {'✓' if agent_factory.graph_available else '✗'}")
    
    # Close any open connections
    if hasattr(agent, 'close'):
        agent.close()
    if doc_processor.graph_builder:
        doc_processor.graph_builder.close()

if __name__ == "__main__":
    test_integrated_system()