import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_role_access():
    print("\n" + "="*60)
    print("🔐 ROLE-BASED ACCESS CONTROL TESTING")
    print("="*60)
    
    # Test users and their expected access
    test_cases = [
        {
            "name": "Admin",
            "email": "admin@university.edu",
            "password": "admin123",
            "expected_access": {
                "roles_endpoint": 200,
                "assign_role": 200,
                "all_users": 200
            }
        },
        {
            "name": "Teacher",
            "email": "teacher@university.edu",
            "password": "teacher123",
            "expected_access": {
                "roles_endpoint": 403,
                "assign_role": 403,
                "all_users": 403
            }
        },
        {
            "name": "Student",
            "email": "student@university.edu",
            "password": "student123",
            "expected_access": {
                "roles_endpoint": 403,
                "assign_role": 403,
                "all_users": 403
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n📋 Testing {test['name']} Access:")
        print("-" * 40)
        
        # Login
        login_response = requests.post(f"{BASE_URL}/auth/login/", json={
            "email": test["email"],
            "password": test["password"]
        })
        
        if login_response.status_code == 200:
            token = login_response.json()['token']
            headers = {"Authorization": f"Bearer {token}"}
            
            # Test roles endpoint
            roles_response = requests.get(f"{BASE_URL}/roles/", headers=headers)
            status = roles_response.status_code
            expected = test["expected_access"]["roles_endpoint"]
            status_icon = "✅" if status == expected else "❌"
            print(f"{status_icon} Roles Endpoint: Got {status}, Expected {expected}")
            
            # Test assign role endpoint
            assign_response = requests.post(f"{BASE_URL}/roles/assign/", 
                                          json={"user_id": 1, "role_id": 1},
                                          headers=headers)
            status = assign_response.status_code
            expected = test["expected_access"]["assign_role"]
            status_icon = "✅" if status == expected else "❌"
            print(f"{status_icon} Assign Role Endpoint: Got {status}, Expected {expected}")
            
        else:
            print(f"❌ Failed to login as {test['name']}")

if __name__ == "__main__":
    test_role_access()