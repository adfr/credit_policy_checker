"""
Demo script to show that agents now focus only on their specific checks
"""

import json
from app.services.agent_compliance_checker import AgentComplianceChecker

def demo_focused_agents():
    """Demonstrate focused agent evaluation"""
    
    # Sample credit data
    sample_data = {
        "loan_amount": 385000,
        "property_value": 428000,
        "down_payment": 40000,
        "credit_score_borrower_1": 745,
        "credit_score_borrower_2": 740,
        "average_credit_score": 742.5,
        "monthly_income": 15000,
        "monthly_debt": 3000,
        "ltv_ratio": 90.0,
        "dti_ratio": 20.0
    }
    
    # Three different agents with different focuses
    agents = [
        {
            "agent_id": "CR_TH_001",
            "agent_name": "Average Credit Score Limit",
            "requirement": "Average credit score must be above 680",
            "data_fields": ["average_credit_score", "credit_score_borrower_1", "credit_score_borrower_2"],
            "check_type": "credit_score_threshold",
            "priority": "critical",
            "agent_type": "threshold"
        },
        {
            "agent_id": "LTV_TH_001",
            "agent_name": "Home Equity Loan LTV Limit",
            "requirement": "LTV ratio must be below 95%",
            "data_fields": ["ltv_ratio", "loan_amount", "property_value"],
            "check_type": "ltv_threshold",
            "priority": "critical",
            "agent_type": "threshold"
        },
        {
            "agent_id": "DTI_TH_001",
            "agent_name": "Debt-to-Income Ratio Limit",
            "requirement": "DTI ratio must be below 43%",
            "data_fields": ["dti_ratio", "monthly_income", "monthly_debt"],
            "check_type": "dti_threshold",
            "priority": "high",
            "agent_type": "threshold"
        }
    ]
    
    print("=== DEMONSTRATION: Focused Agent Evaluation ===\n")
    print("Before the fix: Each agent would evaluate ALL data and provide general assessments.")
    print("After the fix: Each agent only receives and evaluates data relevant to its specific check.\n")
    
    checker = AgentComplianceChecker()
    
    # Simulate what each agent receives
    print("DATA EACH AGENT RECEIVES:")
    print("-" * 50)
    
    for agent in agents:
        agent_data = {}
        for field in agent['data_fields']:
            if field in sample_data:
                agent_data[field] = sample_data[field]
        
        print(f"\n{agent['agent_name']}:")
        print(f"  Requirement: {agent['requirement']}")
        print(f"  Data fields received: {list(agent_data.keys())}")
        print(f"  Data values: {json.dumps(agent_data, indent=4)}")
    
    print("\n" + "=" * 50)
    print("\nKEY IMPROVEMENTS:")
    print("1. Credit Score Agent only sees: average_credit_score, credit_score_borrower_1/2")
    print("2. LTV Agent only sees: ltv_ratio, loan_amount, property_value")
    print("3. DTI Agent only sees: dti_ratio, monthly_income, monthly_debt")
    print("\nThis ensures each agent focuses ONLY on its specific compliance check!")


if __name__ == "__main__":
    demo_focused_agents()