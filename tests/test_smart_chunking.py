#!/usr/bin/env python3
"""
Test the new smart chunking functionality
"""

import os
import sys
sys.path.append('.')

from app.services.policy_agent_extractor import PolicyAgentExtractor

# Sample policy text with clear sections
sample_policy = """
LENDING POLICY DOCUMENT

1. GENERAL REQUIREMENTS
This policy establishes the framework for all lending activities. All loans must comply with federal regulations and internal guidelines.

2. CREDIT REQUIREMENTS
2.1 Minimum Credit Score
All applicants must have a minimum FICO score of 620 for conventional loans.

2.2 Employment History
Borrowers must demonstrate 2 years of continuous employment history. Recent graduates with job offers may be considered with additional documentation.

3. INCOME VERIFICATION
Income must be verified through:
- 2 years of tax returns
- Recent pay stubs (last 30 days)
- Employment verification letter

4. DEBT-TO-INCOME RATIOS
4.1 Housing DTI
Housing debt-to-income ratio must not exceed 28% of gross monthly income.

4.2 Total DTI
Total debt-to-income ratio must not exceed 43% of gross monthly income.

5. LOAN-TO-VALUE REQUIREMENTS
5.1 Conventional Loans
Maximum LTV ratio of 80% for conventional loans without PMI.
Loans with LTV above 80% require private mortgage insurance.

5.2 FHA Loans
Maximum LTV ratio of 96.5% for FHA loans.

6. PROPERTY REQUIREMENTS
Properties must be:
- Owner-occupied primary residences
- Single-family homes, condominiums, or approved townhomes
- Located in acceptable geographic areas
- Appraised at or above contract price

7. APPROVAL LIMITS
7.1 Loan Officer Authority
Loan officers may approve loans up to $500,000 with standard criteria.

7.2 Manager Authority
Managers may approve loans up to $1,000,000 or loans with compensating factors.

7.3 Senior Management
Senior management approval required for:
- Loans exceeding $1,000,000
- Non-standard loan products
- Exception cases

8. DOCUMENTATION REQUIREMENTS
Required documentation includes:
- Credit report (no older than 90 days)
- Employment verification
- Income documentation
- Asset verification
- Property appraisal
- Title insurance commitment
"""

def test_smart_chunking():
    """Test the smart chunking functionality"""
    print("Testing Smart Chunking Implementation")
    print("=" * 50)
    
    extractor = PolicyAgentExtractor()
    
    # Test the chunking
    print(f"Original document length: {len(sample_policy)} characters")
    print(f"Original document tokens: {extractor._count_tokens(sample_policy)}")
    print()
    
    # Test smart chunking
    chunks = extractor._smart_chunk_document(sample_policy, target_chunk_tokens=400)
    
    print(f"Smart chunking created {len(chunks)} chunks:")
    print("-" * 30)
    
    for i, chunk in enumerate(chunks):
        tokens = extractor._count_tokens(chunk)
        preview = chunk[:100].replace('\n', ' ').strip() + "..."
        print(f"Chunk {i+1}: {tokens} tokens")
        print(f"Preview: {preview}")
        print()
    
    # Test section identification
    print("Testing section identification:")
    print("-" * 30)
    sections = extractor._identify_policy_sections(sample_policy)
    
    if sections:
        print(f"Identified {len(sections)} sections:")
        for i, section in enumerate(sections):
            lines = section.split('\n')
            first_line = lines[0].strip() if lines else "Empty section"
            tokens = extractor._count_tokens(section)
            print(f"Section {i+1}: {tokens} tokens - {first_line}")
    else:
        print("No sections identified")
    
    return chunks

def test_extraction_with_smart_chunking():
    """Test actual agent extraction with smart chunking"""
    print("\nTesting Agent Extraction with Smart Chunking")
    print("=" * 50)
    
    extractor = PolicyAgentExtractor()
    
    # Extract agents
    result = extractor.extract_policy_agents(sample_policy, domain_hint="lending")
    
    if 'error' not in result:
        print("Extraction successful!")
        
        # Count agents by type
        agent_counts = {
            'threshold': len(result.get('threshold_agents', [])),
            'criteria': len(result.get('criteria_agents', [])),
            'score': len(result.get('score_agents', [])),
            'qualitative': len(result.get('qualitative_agents', []))
        }
        
        total_agents = sum(agent_counts.values())
        print(f"Total agents extracted: {total_agents}")
        print(f"Agent breakdown: {agent_counts}")
        
        # Show some examples
        if result.get('threshold_agents'):
            print("\nThreshold agents found:")
            for agent in result['threshold_agents'][:3]:  # Show first 3
                print(f"  - {agent['agent_name']}: {agent['requirement']}")
        
        if result.get('criteria_agents'):
            print("\nCriteria agents found:")
            for agent in result['criteria_agents'][:3]:  # Show first 3
                print(f"  - {agent['agent_name']}: {agent['requirement']}")
    else:
        print(f"Extraction failed: {result['error']}")

if __name__ == "__main__":
    chunks = test_smart_chunking()
    test_extraction_with_smart_chunking() 