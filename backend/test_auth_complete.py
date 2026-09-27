import requests
import json
import time

BASE_URL = "http://localhost:8000/api"

def print_response(title, response):
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")
    return response

def test_registration():
    print("\n📝 TEST 1: User Registration")
    data = {
        "username": "newstudent2024",
        "email": "newstudent2024@university.edu",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "user_type": "student"
    }
    response = requests.post(f"{BASE_URL}/auth/register/", json=data)
    return print_response("Register New Student", response)

def test_duplicate_registration():
    print("\n📝 TEST 2: Duplicate Registration (Should Fail)")
    data = {
        "username": "newstudent2024",
        "email": "newstudent2024@university.edu",
        "password": "TestPass123!",
        "confirm_password": "TestPass123!",
        "user_type": "student"
    }
    response = requests.post(f"{BASE_URL}/auth/register/", json=data)
    return print_response("Duplicate Registration", response)

def test_login(email, password, test_name):
    print(f"\n🔐 TEST: {test_name}")
    data = {
        "email": email,
        "password": password
    }
    response = requests.post(f"{BASE_URL}/auth/login/", json=data)
    result = print_response(f"Login - {test_name}", response)
    
    if response.status_code == 200:
        return response.json().get('token'), response.json().get('user')
    return None, None

def test_invalid_login():
    print("\n🔐 TEST: Invalid Login (Should Fail)")
    data = {
        "email": "admin@university.edu",
        "password": "wrongpassword"
    }
    response = requests.post(f"{BASE_URL}/auth/login/", json=data)
    return print_response("Invalid Login", response)

def test_get_current_user(token, test_name):
    print(f"\n👤 TEST: {test_name}")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/auth/me/", headers=headers)
    return print_response(f"Get Current User - {test_name}", response)

def test_get_user_without_token():
    print("\n👤 TEST: Get User Without Token (Should Fail)")
    response = requests.get(f"{BASE_URL}/auth/me/")
    return print_response("Get User Without Token", response)

def test_get_user_with_invalid_token():
    print("\n👤 TEST: Get User With Invalid Token (Should Fail)")
    headers = {"Authorization": "Bearer invalid.token.here"}
    response = requests.get(f"{BASE_URL}/auth/me/", headers=headers)
    return print_response("Get User With Invalid Token", response)

def test_change_password(token):
    print("\n🔑 TEST: Change Password")
    data = {
        "old_password": "TestPass123!",
        "new_password": "NewPass123!",
        "confirm_password": "NewPass123!"
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/auth/change-password/", json=data, headers=headers)
    return print_response("Change Password", response)

def test_login_with_new_password(email):
    print("\n🔐 TEST: Login With New Password")
    return test_login(email, "NewPass123!", "Login After Password Change")

def test_logout(token):
    print("\n🚪 TEST: Logout")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Session-Token": token
    }
    response = requests.post(f"{BASE_URL}/auth/logout/", headers=headers)
    return print_response("Logout", response)

def test_get_user_sessions(token):
    print("\n📊 TEST: Get User Sessions")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/auth/sessions/", headers=headers)
    return print_response("User Sessions", response)

def test_get_roles(token):
    print("\n👥 TEST: Get All Roles (Admin Only)")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/roles/", headers=headers)
    return print_response("Get Roles", response)

def test_assign_role(token):
    print("\n👥 TEST: Assign Role to User (Admin Only)")
    
    # First get a user to assign role to
    test_login_token, _ = test_login("student@university.edu", "student123", "Get Student User")
    
    if test_login_token:
        # Get the student user ID from login response
        student_login = requests.post(f"{BASE_URL}/auth/login/", json={
            "email": "student@university.edu",
            "password": "student123"
        })
        student_data = student_login.json()
        student_id = student_data['user']['user_id']
        
        # Get role ID for TEACHER role
        headers = {"Authorization": f"Bearer {token}"}
        roles_response = requests.get(f"{BASE_URL}/roles/", headers=headers)
        roles = roles_response.json()
        
        teacher_role = None
        for role in roles:
            if role['role_name'] == 'TEACHER':
                teacher_role = role
                break
        
        if teacher_role:
            data = {
                "user_id": student_id,
                "role_id": teacher_role['role_id']
            }
            response = requests.post(f"{BASE_URL}/roles/assign/", json=data, headers=headers)
            return print_response("Assign Role", response)
    
    return None

def test_get_user_roles(token):
    print("\n👥 TEST: Get User Roles")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/roles/user/", headers=headers)
    return print_response("Get Current User Roles", response)

def test_password_reset_request():
    print("\n📧 TEST: Password Reset Request")
    data = {
        "email": "newstudent2024@university.edu"
    }
    response = requests.post(f"{BASE_URL}/auth/password-reset/request/", json=data)
    result = print_response("Password Reset Request", response)
    
    if response.status_code == 200:
        return response.json().get('reset_token')
    return None

def test_password_reset_confirm(token):
    print("\n📧 TEST: Password Reset Confirm")
    data = {
        "token": token,
        "new_password": "ResetPass123!",
        "confirm_password": "ResetPass123!"
    }
    response = requests.post(f"{BASE_URL}/auth/password-reset/confirm/", json=data)
    return print_response("Password Reset Confirm", response)

def test_unauthorized_access(token):
    print("\n🚫 TEST: Unauthorized Access (Student trying to access admin endpoint)")
    
    # First, get a student token
    student_token, _ = test_login("student@university.edu", "student123", "Get Student Token")
    
    if student_token:
        headers = {"Authorization": f"Bearer {student_token}"}
        response = requests.get(f"{BASE_URL}/roles/", headers=headers)
        return print_response("Student Accessing Admin Endpoint", response)
    return None

def run_all_tests():
    print("\n" + "="*60)
    print("🚀 STARTING COMPREHENSIVE AUTHENTICATION TESTING")
    print("="*60)
    
    results = {
        "passed": 0,
        "failed": 0,
        "total": 0
    }
    
    # Test 1: Registration
    register_response = test_registration()
    results["total"] += 1
    if register_response.status_code == 201:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 2: Duplicate Registration
    duplicate_response = test_duplicate_registration()
    results["total"] += 1
    if duplicate_response.status_code == 400:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 3: Valid Login - Admin
    admin_token, admin_user = test_login("admin@university.edu", "admin123", "Admin Login")
    results["total"] += 1
    if admin_token:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 4: Valid Login - Student
    student_token, student_user = test_login("student@university.edu", "student123", "Student Login")
    results["total"] += 1
    if student_token:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 5: Invalid Login
    invalid_response = test_invalid_login()
    results["total"] += 1
    if invalid_response.status_code == 400:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 6: Get Current User with Valid Token
    if admin_token:
        user_response = test_get_current_user(admin_token, "Get Admin User")
        results["total"] += 1
        if user_response.status_code == 200:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test 7: Get Current User Without Token
    no_token_response = test_get_user_without_token()
    results["total"] += 1
    if no_token_response.status_code == 403:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 8: Get Current User With Invalid Token
    invalid_token_response = test_get_user_with_invalid_token()
    results["total"] += 1
    if invalid_token_response.status_code in [401, 403]:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 9: Get User Sessions
    if admin_token:
        sessions_response = test_get_user_sessions(admin_token)
        results["total"] += 1
        if sessions_response.status_code == 200:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test 10: Get Roles (Admin Only)
    if admin_token:
        roles_response = test_get_roles(admin_token)
        results["total"] += 1
        if roles_response.status_code == 200:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test 11: Unauthorized Access Test
    unauthorized_response = test_unauthorized_access(admin_token)
    if unauthorized_response:
        results["total"] += 1
        if unauthorized_response.status_code == 403:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test 12: Change Password
    if student_token:
        change_response = test_change_password(student_token)
        results["total"] += 1
        if change_response.status_code == 200:
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        # Test 13: Login with new password
        if change_response.status_code == 200:
            new_login_token, _ = test_login_with_new_password("newstudent2024@university.edu")
            results["total"] += 1
            if new_login_token:
                results["passed"] += 1
            else:
                results["failed"] += 1
    
    # Test 14: Password Reset Flow
    reset_token = test_password_reset_request()
    if reset_token:
        results["total"] += 1
        if reset_token:
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        # Test 15: Confirm Password Reset
        confirm_response = test_password_reset_confirm(reset_token)
        results["total"] += 1
        if confirm_response.status_code == 200:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test 16: Get User Roles
    if admin_token:
        user_roles_response = test_get_user_roles(admin_token)
        results["total"] += 1
        if user_roles_response.status_code == 200:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Test 17: Assign Role (Admin Only)
    if admin_token:
        assign_response = test_assign_role(admin_token)
        if assign_response:
            results["total"] += 1
            if assign_response.status_code == 200:
                results["passed"] += 1
            else:
                results["failed"] += 1
    
    # Test 18: Logout
    if admin_token:
        logout_response = test_logout(admin_token)
        results["total"] += 1
        if logout_response.status_code == 200:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Final Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {results['total']}")
    print(f"✅ Passed: {results['passed']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"Success Rate: {(results['passed']/results['total']*100):.1f}%")
    print("="*60)
    
    if results['failed'] == 0:
        print("\n🎉 ALL TESTS PASSED! Authentication system is working perfectly!")
    else:
        print(f"\n⚠️  {results['failed']} tests failed. Please check the failed tests above.")
    
    return results

if __name__ == "__main__":
    run_all_tests()