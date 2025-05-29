#!/usr/bin/env python3
"""Test the complete system functionality"""

import os
import sys
import json
import traceback

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test imports
print("Testing imports...")
try:
    from app.services.policy_analyzer import PolicyAnalyzer
    from app.services.compliance_checker import ComplianceChecker
    from app.services.document_processor import DocumentProcessor
    from app.services.document_classifier import DocumentClassifier
    from agents.agent_factory import AgentFactory
    from agents.universal_agent import UniversalAgent
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    traceback.print_exc()
    sys.exit(1)

# Test 1: Policy Extraction
print("\n" + "="*80)
print("TEST 1: Policy Extraction")
print("="*80)

test_policy = """
CREDIT POLICY REQUIREMENTS

1. Minimum Credit Score: 700
2. Maximum Debt-to-Income Ratio: 43%
3. Minimum Income: $50,000 annually
4. Employment History: 2 years minimum
5. Maximum Loan-to-Value: 80%
"""

try:
    analyzer = PolicyAnalyzer()
    checks = analyzer.extract_checks(test_policy, domain_hint="financial")
    print(f"✓ Extracted {len(checks)} policy checks")
    
    # Show first few checks
    for i, check in enumerate(checks[:3]):
        print(f"\nCheck {i+1}:")
        print(f"  Type: {check.get('check_type', 'N/A')}")
        print(f"  Description: {check.get('description', 'N/A')}")
        print(f"  Priority: {check.get('priority', 'N/A')}")
        
except Exception as e:
    print(f"✗ Policy extraction failed: {e}")
    traceback.print_exc()

# Test 2: Agent Creation
print("\n" + "="*80)
print("TEST 2: Agent Creation")
print("="*80)

try:
    factory = AgentFactory()
    
    # Test check
    test_check = {
        'check_type': 'minimum_credit_score',
        'description': 'Check minimum credit score requirement',
        'criteria': 'Credit score must be at least 700',
        'threshold': '700',
        'priority': 'critical',
        'complexity': 'simple',
        'domain': 'financial'
    }
    
    agent = factory.create_agent(test_check['check_type'], test_check)
    print(f"✓ Created agent: {agent.agent_type}")
    print(f"  Domain: {agent.domain}")
    print(f"  Complexity: {agent.complexity}")
    
except Exception as e:
    print(f"✗ Agent creation failed: {e}")
    traceback.print_exc()

# Test 3: Document Classification
print("\n" + "="*80)
print("TEST 3: Document Classification")
print("="*80)

test_mortgage_doc = {
    'text_content': """
    MORTGAGE LOAN APPLICATION
    
    Borrower: John Smith
    Property: 123 Main St
    Loan Amount: $300,000
    Property Value: $400,000
    LTV: 75%
    Credit Score: 720
    """
}

try:
    classifier = DocumentClassifier()
    classification = classifier.classify_document(test_mortgage_doc)
    print(f"✓ Document classified as: {classification.get('primary_loan_type', 'unknown')}")
    print(f"  Confidence: {classification.get('confidence', 0):.2f}")
    
except Exception as e:
    print(f"✗ Document classification failed: {e}")
    traceback.print_exc()

# Test 4: Compliance Checking
print("\n" + "="*80)
print("TEST 4: Compliance Checking")
print("="*80)

try:
    if 'checks' in locals() and len(checks) > 0:
        checker = ComplianceChecker()
        
        # Sample compliance data
        compliance_data = {
            'text_content': 'Credit Score: 750, Income: $85,000, DTI: 38%',
            'credit_score': 750,
            'income': 85000,
            'dti_ratio': 0.38
        }
        
        # Run compliance check (first 3 checks only for testing)
        results = checker.check_compliance(
            checks[:3], 
            compliance_data, 
            filter_by_relevance=False
        )
        
        print(f"✓ Compliance check completed")
        print(f"  Executed: {len([r for r in results if r.get('status') != 'skipped'])}")
        print(f"  Passed: {len([r for r in results if r.get('passed') == True])}")
        print(f"  Failed: {len([r for r in results if r.get('passed') == False])}")
        
    else:
        print("✗ No checks available for compliance testing")
        
except Exception as e:
    print(f"✗ Compliance checking failed: {e}")
    traceback.print_exc()

# Test 5: End-to-End Flow
print("\n" + "="*80)
print("TEST 5: End-to-End Flow")
print("="*80)

try:
    # Step 1: Extract policy checks
    analyzer = PolicyAnalyzer()
    policy_checks = analyzer.extract_checks(test_policy, domain_hint="financial")
    print(f"✓ Step 1: Extracted {len(policy_checks)} checks from policy")
    
    # Step 2: Classify document
    classifier = DocumentClassifier()
    doc_classification = classifier.classify_document(test_mortgage_doc)
    print(f"✓ Step 2: Document classified as {doc_classification.get('primary_loan_type', 'unknown')}")
    
    # Step 3: Filter applicable checks
    applicable_checks, skipped_checks = classifier.determine_applicable_agents(
        doc_classification, policy_checks
    )
    print(f"✓ Step 3: {len(applicable_checks)} applicable, {len(skipped_checks)} skipped")
    
    # Step 4: Run compliance
    checker = ComplianceChecker()
    compliance_results = checker.check_compliance(
        policy_checks, 
        test_mortgage_doc, 
        filter_by_relevance=True
    )
    print(f"✓ Step 4: Compliance check completed")
    
    # Step 5: Analyze results
    analysis = checker.analyze_compliance_results(compliance_results)
    print(f"✓ Step 5: Analysis complete")
    print(f"  Overall status: {analysis.get('overall_status', 'unknown')}")
    print(f"  Pass rate: {analysis['summary']['pass_rate']:.1%}")
    
except Exception as e:
    print(f"✗ End-to-end flow failed: {e}")
    traceback.print_exc()

# Test 6: Check for common issues
print("\n" + "="*80)
print("TEST 6: Common Issues Check")
print("="*80)

# Check environment variables
if os.environ.get('OPENAI_API_KEY'):
    print("✓ OPENAI_API_KEY is set")
else:
    print("✗ OPENAI_API_KEY is not set - API calls will fail")

# Check upload directory
if os.path.exists('uploads'):
    print("✓ Uploads directory exists")
else:
    print("! Uploads directory missing - will be created when needed")

# Check for new vs old document processor
try:
    from app.services.policy_agent_extractor import PolicyAgentExtractor
    from app.services.agent_compliance_checker import AgentComplianceChecker
    print("✓ New agent-based system available")
except ImportError:
    print("! New agent-based system not found - using legacy system")

print("\n" + "="*80)
print("Test Summary: Check for any ✗ marks above to identify issues")
print("="*80)