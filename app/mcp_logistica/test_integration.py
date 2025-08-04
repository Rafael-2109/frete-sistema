"""
Integration Test Script for MCP Logistics
Run this after applying the fixes to verify everything works
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
API_PREFIX = "/api/mcp/logistica"

# Test credentials (update with valid ones)
TEST_USER = "rafael6250@gmail.com"
TEST_PASSWORD = "rafa2109"

class MCPLogisticsIntegrationTest:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        
    def run_all_tests(self):
        """Run all integration tests"""
        print("=" * 50)
        print("MCP Logistics Integration Test Suite")
        print("=" * 50)
        print(f"Started at: {datetime.now()}")
        print(f"Target: {BASE_URL}{API_PREFIX}")
        print("=" * 50)
        
        tests = [
            self.test_health_check,
            self.test_authentication,
            self.test_basic_query,
            self.test_query_with_entities,
            self.test_error_handling,
            self.test_preferences,
            self.test_suggestions,
            self.test_claude_config,
            self.test_session_management
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                print(f"\n▶ Running: {test.__name__}")
                result = test()
                if result:
                    print(f"✅ PASSED: {test.__name__}")
                    passed += 1
                else:
                    print(f"❌ FAILED: {test.__name__}")
                    failed += 1
            except Exception as e:
                print(f"❌ ERROR in {test.__name__}: {str(e)}")
                failed += 1
                
        print("\n" + "=" * 50)
        print(f"Test Results: {passed} passed, {failed} failed")
        print("=" * 50)
        
    def test_health_check(self):
        """Test 1: Health check endpoint"""
        response = self.session.get(f"{BASE_URL}{API_PREFIX}/health")
        
        if response.status_code != 200:
            print(f"  Status code: {response.status_code}")
            return False
            
        data = response.json()
        if data.get('status') != 'healthy':
            print(f"  Health status: {data.get('status')}")
            return False
            
        print(f"  Components: {data.get('components')}")
        return True
        
    def test_authentication(self):
        """Test 2: Authentication flow"""
        # Login first
        login_data = {
            'username': TEST_USER,
            'password': TEST_PASSWORD
        }
        
        response = self.session.post(f"{BASE_URL}/auth/login", data=login_data)
        
        if response.status_code != 200:
            print(f"  Login failed with status: {response.status_code}")
            return False
            
        # Try to access protected endpoint
        response = self.session.get(f"{BASE_URL}{API_PREFIX}/preferences")
        
        if response.status_code == 401:
            print("  Authentication not working properly")
            return False
            
        return response.status_code == 200
        
    def test_basic_query(self):
        """Test 3: Basic query processing"""
        query_data = {
            'query': 'Quantos pedidos estão pendentes?',
            'output_format': 'json'
        }
        
        response = self.session.post(
            f"{BASE_URL}{API_PREFIX}/query",
            json=query_data
        )
        
        if response.status_code != 200:
            print(f"  Query failed with status: {response.status_code}")
            return False
            
        data = response.json()
        print(f"  Success: {data.get('success')}")
        print(f"  Intent: {data.get('intent', {}).get('primary')}")
        
        return data.get('success', False)
        
    def test_query_with_entities(self):
        """Test 4: Query with entity recognition"""
        query_data = {
            'query': 'Mostre as entregas do cliente ABC LTDA para São Paulo',
            'output_format': 'table'
        }
        
        response = self.session.post(
            f"{BASE_URL}{API_PREFIX}/query",
            json=query_data
        )
        
        if response.status_code != 200:
            return False
            
        data = response.json()
        metadata = data.get('metadata', {})
        entities = metadata.get('entities_found', [])
        
        print(f"  Entities found: {entities}")
        
        return len(entities) > 0
        
    def test_error_handling(self):
        """Test 5: Error handling"""
        # Send invalid query
        query_data = {
            'query': '',  # Empty query
            'output_format': 'invalid_format'
        }
        
        response = self.session.post(
            f"{BASE_URL}{API_PREFIX}/query",
            json=query_data
        )
        
        # Should return 400 for bad request
        if response.status_code != 400:
            print(f"  Expected 400, got: {response.status_code}")
            return False
            
        data = response.json()
        return 'error' in data
        
    def test_preferences(self):
        """Test 6: User preferences"""
        # Get preferences
        response = self.session.get(f"{BASE_URL}{API_PREFIX}/preferences")
        
        if response.status_code != 200:
            return False
            
        data = response.json()
        
        # Update preferences
        update_data = {
            'default_output_format': 'table',
            'default_limit': 50
        }
        
        response = self.session.put(
            f"{BASE_URL}{API_PREFIX}/preferences",
            json=update_data
        )
        
        return response.status_code == 200
        
    def test_suggestions(self):
        """Test 7: Query suggestions"""
        response = self.session.get(
            f"{BASE_URL}{API_PREFIX}/suggestions",
            params={'q': 'mostrar'}
        )
        
        if response.status_code != 200:
            return False
            
        data = response.json()
        suggestions = data.get('suggestions', [])
        
        print(f"  Suggestions returned: {len(suggestions)}")
        
        return data.get('success', False)
        
    def test_claude_config(self):
        """Test 8: Claude configuration"""
        response = self.session.get(f"{BASE_URL}{API_PREFIX}/claude/config")
        
        if response.status_code != 200:
            return False
            
        data = response.json()
        config = data.get('config', {})
        
        print(f"  Claude enabled: {config.get('enabled')}")
        print(f"  Model: {config.get('model')}")
        
        return data.get('success', False)
        
    def test_session_management(self):
        """Test 9: Session management"""
        # Get session summary
        response = self.session.get(
            f"{BASE_URL}{API_PREFIX}/session/summary",
            headers={'X-Session-Id': 'test-session-123'}
        )
        
        if response.status_code != 200:
            return False
            
        # Clear session
        response = self.session.post(
            f"{BASE_URL}{API_PREFIX}/session/clear",
            headers={'X-Session-Id': 'test-session-123'}
        )
        
        return response.status_code == 200

if __name__ == "__main__":
    tester = MCPLogisticsIntegrationTest()
    tester.run_all_tests()
    
    print("\n📝 Next Steps:")
    print("1. If tests fail, check app logs for detailed errors")
    print("2. Ensure blueprint is registered in app/__init__.py")
    print("3. Verify static files exist in app/static/mcp_logistica/")
    print("4. Check database models are imported correctly")
    print("5. Confirm authentication is working properly")