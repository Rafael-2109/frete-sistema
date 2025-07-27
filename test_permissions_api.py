"""
Test script for Permission System REST API
=========================================

Tests all API endpoints to ensure they're working correctly.
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000/api/v1/permissions"
AUTH_TOKEN = "your-jwt-token-here"  # Replace with actual token

# Headers
headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def test_health_check():
    """Test health check endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_list_categories():
    """Test list categories endpoint"""
    print("\n=== Testing List Categories ===")
    params = {
        "active": "true",
        "include_modules": "true",
        "include_counts": "true"
    }
    response = requests.get(f"{BASE_URL}/categories", headers=headers, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_create_category():
    """Test create category endpoint"""
    print("\n=== Testing Create Category ===")
    data = {
        "name": "test_category",
        "display_name": "Test Category",
        "description": "Test category for API testing",
        "icon": "test",
        "color": "#FF0000",
        "order_index": 99
    }
    response = requests.post(f"{BASE_URL}/categories", headers=headers, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code in [200, 201, 409]  # 409 if already exists

def test_list_modules():
    """Test list modules endpoint"""
    print("\n=== Testing List Modules ===")
    params = {
        "active": "true",
        "include_submodules": "true",
        "page": 1,
        "per_page": 10
    }
    response = requests.get(f"{BASE_URL}/modules", headers=headers, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_user_permissions():
    """Test get user permissions endpoint"""
    print("\n=== Testing Get User Permissions ===")
    user_id = 1  # Replace with actual user ID
    params = {
        "effective": "true",
        "include_inherited": "true"
    }
    response = requests.get(f"{BASE_URL}/users/{user_id}/permissions", headers=headers, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code in [200, 404]

def test_update_user_permissions():
    """Test update user permissions endpoint"""
    print("\n=== Testing Update User Permissions ===")
    user_id = 1  # Replace with actual user ID
    data = {
        "permissions": [
            {
                "type": "module",
                "id": 1,
                "can_view": True,
                "can_edit": False,
                "can_delete": False,
                "can_export": True,
                "reason": "Test permission update"
            }
        ],
        "notify_user": False
    }
    response = requests.post(f"{BASE_URL}/users/{user_id}/permissions", headers=headers, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code in [200, 404]

def test_user_vendors():
    """Test get user vendors endpoint"""
    print("\n=== Testing Get User Vendors ===")
    user_id = 1  # Replace with actual user ID
    response = requests.get(f"{BASE_URL}/users/{user_id}/vendors", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code in [200, 404]

def test_audit_logs():
    """Test get audit logs endpoint"""
    print("\n=== Testing Get Audit Logs ===")
    params = {
        "page": 1,
        "limit": 10
    }
    response = requests.get(f"{BASE_URL}/audit", headers=headers, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_permission_templates():
    """Test list permission templates endpoint"""
    print("\n=== Testing List Permission Templates ===")
    params = {
        "active": "true"
    }
    response = requests.get(f"{BASE_URL}/templates", headers=headers, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def main():
    """Run all tests"""
    print("Starting Permission System API Tests")
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    tests = [
        ("Health Check", test_health_check),
        ("List Categories", test_list_categories),
        ("Create Category", test_create_category),
        ("List Modules", test_list_modules),
        ("User Permissions", test_user_permissions),
        ("Update User Permissions", test_update_user_permissions),
        ("User Vendors", test_user_vendors),
        ("Audit Logs", test_audit_logs),
        ("Permission Templates", test_permission_templates)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, "PASS" if success else "FAIL"))
        except Exception as e:
            print(f"\nError in {test_name}: {str(e)}")
            results.append((test_name, "ERROR"))
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    for test_name, result in results:
        print(f"{test_name:<30} {result}")
    
    passed = sum(1 for _, result in results if result == "PASS")
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)