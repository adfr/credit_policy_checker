#!/usr/bin/env python3
"""
Comprehensive test script for the agent-based policy compliance workflow.
Tests all API endpoints and identifies potential bugs.
"""

import requests
import json
import os
import time
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:5000"
TEST_FILES_DIR = Path(__file__).parent

class AgentWorkflowTester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, details=None, response=None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        if response:
            result['status_code'] = response.status_code
            try:
                result['response_data'] = response.json()
            except:
                result['response_text'] = response.text[:500]
        
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        if response and not success:
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
        print()

    def test_server_health(self):
        """Test if the server is running"""
        try:
            response = self.session.get(f"{self.base_url}/")
            success = response.status_code == 200
            self.log_test("Server Health Check", success, f"Server responding on {self.base_url}", response)
            return success
        except requests.ConnectionError:
            self.log_test("Server Health Check", False, f"Cannot connect to {self.base_url}")
            return False

    def test_restart_workflow(self):
        """Test the restart workflow endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/api/restart-workflow")
            success = response.status_code == 200
            
            if success:
                data = response.json()
                expected_keys = ['message', 'status', 'steps', 'new_agent_workflow']
                missing_keys = [key for key in expected_keys if key not in data]
                if missing_keys:
                    success = False
                    details = f"Missing keys: {missing_keys}"
                else:
                    details = f"Status: {data.get('status')}"
            else:
                details = "Endpoint not responding correctly"
                
            self.log_test("Restart Workflow API", success, details, response)
            return success
        except Exception as e:
            self.log_test("Restart Workflow API", False, f"Exception: {str(e)}")
            return False

    def test_extract_policy_agents(self):
        """Test policy agent extraction with a sample file"""
        # Find a policy file to test with
        policy_files = [
            'consumer-bank-credit-policy-v2.pdf',
            'policy.pdf',
            'mortgage-credit-memo.pdf'
        ]
        
        test_file = None
        for filename in policy_files:
            if os.path.exists(filename):
                test_file = filename
                break
        
        if not test_file:
            self.log_test("Extract Policy Agents", False, "No test policy file found")
            return False
        
        try:
            with open(test_file, 'rb') as f:
                files = {'file': f}
                data = {'domain_hint': 'banking_credit_policy'}
                
                response = self.session.post(
                    f"{self.base_url}/api/extract-policy-agents",
                    files=files,
                    data=data
                )
            
            success = response.status_code == 200
            
            if success:
                result = response.json()
                expected_keys = ['success', 'extracted_agents', 'validation', 'document_summary']
                missing_keys = [key for key in expected_keys if key not in result]
                
                if missing_keys:
                    success = False
                    details = f"Missing response keys: {missing_keys}"
                else:
                    agents = result.get('extracted_agents', {})
                    total_agents = sum(len(agents.get(agent_type, [])) for agent_type in ['threshold_agents', 'criteria_agents', 'score_agents', 'qualitative_agents'])
                    details = f"Extracted {total_agents} agents from {test_file}"
                    
                    # Store extracted agents for next test
                    self.extracted_agents = result['extracted_agents']
            else:
                details = f"Failed to extract agents from {test_file}"
                
            self.log_test("Extract Policy Agents", success, details, response)
            return success
            
        except Exception as e:
            self.log_test("Extract Policy Agents", False, f"Exception: {str(e)}")
            return False

    def test_refine_agents(self):
        """Test agent refinement"""
        if not hasattr(self, 'extracted_agents'):
            self.log_test("Refine Agents", False, "No extracted agents available (extract test failed)")
            return False
        
        try:
            # Simulate user feedback
            user_feedback = {
                "remove_agents": [],
                "modify_agents": [],
                "add_requirements": "Focus on debt-to-income ratio validation"
            }
            
            payload = {
                'extracted_agents': self.extracted_agents,
                'user_feedback': user_feedback
            }
            
            response = self.session.post(
                f"{self.base_url}/api/refine-agents",
                json=payload
            )
            
            success = response.status_code == 200
            
            if success:
                result = response.json()
                expected_keys = ['success', 'refined_agents', 'validation']
                missing_keys = [key for key in expected_keys if key not in result]
                
                if missing_keys:
                    success = False
                    details = f"Missing response keys: {missing_keys}"
                else:
                    details = "Agent refinement completed successfully"
                    self.refined_agents = result['refined_agents']
            else:
                details = "Failed to refine agents"
                
            self.log_test("Refine Agents", success, details, response)
            return success
            
        except Exception as e:
            self.log_test("Refine Agents", False, f"Exception: {str(e)}")
            return False

    def test_get_agent_data_requirements(self):
        """Test getting data requirements for agents"""
        if not hasattr(self, 'refined_agents'):
            if hasattr(self, 'extracted_agents'):
                agents = self.extracted_agents
            else:
                self.log_test("Get Agent Data Requirements", False, "No agents available")
                return False
        else:
            agents = self.refined_agents
        
        try:
            # Select some agents to test with
            selected_agents = []
            
            for agent_type in ['threshold_agents', 'criteria_agents', 'score_agents']:
                agent_list = agents.get(agent_type, [])
                if agent_list:
                    selected_agents.extend(agent_list[:2])  # Take first 2 from each type
            
            if not selected_agents:
                self.log_test("Get Agent Data Requirements", False, "No agents to test with")
                return False
            
            payload = {'selected_agents': selected_agents}
            
            response = self.session.post(
                f"{self.base_url}/api/get-agent-data-requirements",
                json=payload
            )
            
            success = response.status_code == 200
            
            if success:
                result = response.json()
                if 'data_requirements' in result:
                    details = f"Retrieved data requirements for {len(selected_agents)} agents"
                    self.selected_agents = selected_agents  # Store for compliance test
                else:
                    success = False
                    details = "Missing data_requirements in response"
            else:
                details = "Failed to get data requirements"
                
            self.log_test("Get Agent Data Requirements", success, details, response)
            return success
            
        except Exception as e:
            self.log_test("Get Agent Data Requirements", False, f"Exception: {str(e)}")
            return False

    def test_check_compliance_with_agents(self):
        """Test compliance checking with agents"""
        if not hasattr(self, 'selected_agents'):
            self.log_test("Check Compliance with Agents", False, "No selected agents available")
            return False
        
        # Find an assessment document to test with
        assessment_files = [
            'mortgage-credit-memo.pdf',
            'creditmemo.pdf',
            'consumer-bank-credit-policy-v2.pdf'
        ]
        
        test_file = None
        for filename in assessment_files:
            if os.path.exists(filename):
                test_file = filename
                break
        
        if not test_file:
            self.log_test("Check Compliance with Agents", False, "No test assessment file found")
            return False
        
        try:
            with open(test_file, 'rb') as f:
                files = {'file': f}
                data = {
                    'selected_agents': json.dumps(self.selected_agents),
                    'applicant_data': json.dumps({
                        'applicant_name': 'Test Applicant',
                        'loan_amount': '250000'
                    })
                }
                
                response = self.session.post(
                    f"{self.base_url}/api/check-compliance-with-agents",
                    files=files,
                    data=data
                )
            
            success = response.status_code == 200
            
            if success:
                result = response.json()
                expected_keys = ['success', 'compliance_results', 'document_summary']
                missing_keys = [key for key in expected_keys if key not in result]
                
                if missing_keys:
                    success = False
                    details = f"Missing response keys: {missing_keys}"
                else:
                    compliance_results = result.get('compliance_results', [])
                    details = f"Compliance check completed for {len(compliance_results)} agents"
            else:
                details = f"Failed to check compliance with {test_file}"
                
            self.log_test("Check Compliance with Agents", success, details, response)
            return success
            
        except Exception as e:
            self.log_test("Check Compliance with Agents", False, f"Exception: {str(e)}")
            return False

    def test_legacy_endpoints(self):
        """Test that legacy endpoints are properly handled"""
        legacy_endpoints = [
            '/api/upload-policy-document',
            '/api/select-agents',
            '/api/upload-assessment-document',
            '/api/run-compliance-assessment'
        ]
        
        all_legacy_handled = True
        
        for endpoint in legacy_endpoints:
            try:
                response = self.session.post(f"{self.base_url}{endpoint}")
                # These should either return 404 (removed) or have proper error handling
                if response.status_code == 404:
                    status = "Properly removed"
                    success = True
                elif response.status_code in [400, 405]:  # Bad request or method not allowed
                    status = "Still exists but handled"
                    success = True
                else:
                    status = f"Unexpected status: {response.status_code}"
                    success = False
                    all_legacy_handled = False
                
                self.log_test(f"Legacy Endpoint {endpoint}", success, status, response)
                
            except Exception as e:
                self.log_test(f"Legacy Endpoint {endpoint}", False, f"Exception: {str(e)}")
                all_legacy_handled = False
        
        return all_legacy_handled

    def run_all_tests(self):
        """Run the complete test suite"""
        print("🧪 Starting Agent Workflow Test Suite")
        print("=" * 50)
        
        # Test sequence
        tests = [
            self.test_server_health,
            self.test_restart_workflow,
            self.test_extract_policy_agents,
            self.test_refine_agents,
            self.test_get_agent_data_requirements,
            self.test_check_compliance_with_agents,
            self.test_legacy_endpoints
        ]
        
        total_tests = len(tests)
        passed_tests = 0
        
        for test in tests:
            if test():
                passed_tests += 1
        
        print("=" * 50)
        print(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All tests passed! The agent workflow is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the details above.")
            print("\n🔧 Common issues to check:")
            print("   - Make sure the Flask app is running on localhost:5000")
            print("   - Ensure all required service files exist")
            print("   - Check that test policy/document files are available")
            print("   - Verify OpenAI API key is configured")
        
        return passed_tests == total_tests

    def generate_report(self):
        """Generate a detailed test report"""
        print("\n📋 Detailed Test Report")
        print("=" * 50)
        
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']} ({result['timestamp']})")
            
            if result.get('details'):
                print(f"   Details: {result['details']}")
            
            if result.get('status_code'):
                print(f"   HTTP Status: {result['status_code']}")
            
            if not result['success'] and result.get('response_data'):
                print(f"   Response: {json.dumps(result['response_data'], indent=2)}")
            
            print()

if __name__ == "__main__":
    # Check if server is specified
    import sys
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = BASE_URL
    
    print(f"🎯 Testing agent workflow at {base_url}")
    
    tester = AgentWorkflowTester(base_url)
    success = tester.run_all_tests()
    
    # Generate detailed report
    tester.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1) 