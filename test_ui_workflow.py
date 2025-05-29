#!/usr/bin/env python3
"""
Test script to verify the new UI can communicate with the API endpoints correctly
"""

import requests
import json
import os

def test_extract_policy_agents():
    """Test the extract-policy-agents endpoint that the UI calls"""
    
    # Use the actual policy document
    policy_file = "consumer-bank-credit-policy-v2.pdf"
    
    if not os.path.exists(policy_file):
        print(f"❌ Policy file not found: {policy_file}")
        return False, None
    
    url = "http://localhost:5000/api/extract-policy-agents"
    
    with open(policy_file, 'rb') as f:
        files = {'file': f}
        data = {'domain_hint': 'financial'}
        
        try:
            response = requests.post(url, files=files, data=data)
            
            print(f"Status Code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    print("✅ Policy agents extracted successfully!")
                    print(f"   - Total agents: {sum(result['agent_counts'].values())}")
                    print(f"   - Threshold: {result['agent_counts']['threshold']}")
                    print(f"   - Criteria: {result['agent_counts']['criteria']}")
                    print(f"   - Score: {result['agent_counts']['score']}")
                    print(f"   - Qualitative: {result['agent_counts']['qualitative']}")
                    return True, result
                else:
                    print(f"❌ API returned error: {result.get('error')}")
                    return False, result
            else:
                print(f"❌ HTTP Error {response.status_code}")
                print(f"Response content: {response.text[:500]}")
                return False, None
                
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to Flask app. Is it running on localhost:5000?")
            return False, None
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response: {e}")
            print(f"Response content: {response.text[:500]}")
            return False, None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False, None

def test_ui_compatibility():
    """Test that UI can get the expected response format"""
    
    success, result = test_extract_policy_agents()
    
    if success:
        print("\n🔍 Checking UI compatibility...")
        
        # Check expected fields for UI
        required_fields = ['success', 'extracted_agents', 'agent_counts', 'validation']
        
        for field in required_fields:
            if field in result:
                print(f"   ✅ Has field: {field}")
            else:
                print(f"   ❌ Missing field: {field}")
                return False
        
        # Check agent structure
        agents = result['extracted_agents']
        agent_types = ['threshold_agents', 'criteria_agents', 'score_agents', 'qualitative_agents']
        
        for agent_type in agent_types:
            if agent_type in agents and len(agents[agent_type]) > 0:
                agent = agents[agent_type][0]
                required_agent_fields = ['agent_id', 'agent_name', 'description', 'requirement', 'data_fields', 'priority']
                
                print(f"   🔍 Checking {agent_type} structure...")
                for field in required_agent_fields:
                    if field in agent:
                        print(f"      ✅ Has field: {field}")
                    else:
                        print(f"      ❌ Missing field: {field}")
                        return False
        
        print("✅ UI compatibility check passed!")
        return True
    else:
        print("❌ Cannot test UI compatibility - API call failed")
        return False

def main():
    print("🧪 Testing new UI workflow API compatibility...")
    print("=" * 60)
    
    # Test policy extraction
    print("1. Testing policy agent extraction...")
    success = test_ui_compatibility()
    
    if success:
        print("\n🎉 All tests passed! The UI should now work with the new API.")
        print("\n📋 Next steps:")
        print("   1. Open http://localhost:5000 in your browser")
        print("   2. Upload a policy document in Step 1")
        print("   3. Select agents in Step 2")
        print("   4. Upload assessment document and run compliance check in Step 4")
    else:
        print("\n❌ Tests failed. The UI may still have issues.")

if __name__ == "__main__":
    main() 