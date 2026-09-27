import requests
import time
import json

BASE_URL = "http://localhost:8000/api"

def test_session_management():
    print("\n" + "="*60)
    print("📊 SESSION MANAGEMENT TESTING")
    print("="*60)
    
    # Login
    login_response = requests.post(f"{BASE_URL}/auth/login/", json={
        "email": "admin@university.edu",
        "password": "admin123"
    })
    
    if login_response.status_code == 200:
        token = login_response.json()['token']
        session_id = login_response.json()['session_id']
        
        print(f"✓ Session created with ID: {session_id}")
        
        # Get active sessions
        headers = {"Authorization": f"Bearer {token}"}
        sessions_response = requests.get(f"{BASE_URL}/auth/sessions/", headers=headers)
        
        if sessions_response.status_code == 200:
            sessions = sessions_response.json()
            print(f"\n📋 Active Sessions: {len(sessions)}")
            for session in sessions:
                print(f"  - Session ID: {session['session_id']}")
                print(f"    Active: {session['is_active']}")
                print(f"    Login Time: {session['login_time']}")
        
        # Revoke session
        if sessions_response.status_code == 200 and len(sessions) > 0:
            session_to_revoke = sessions[0]['session_id']
            revoke_response = requests.post(
                f"{BASE_URL}/auth/sessions/{session_to_revoke}/revoke/",
                headers=headers
            )
            
            if revoke_response.status_code == 200:
                print(f"\n✓ Session {session_to_revoke} revoked successfully")
                
                # Check sessions again
                sessions_response2 = requests.get(f"{BASE_URL}/auth/sessions/", headers=headers)
                if sessions_response2.status_code == 200:
                    active_count = len([s for s in sessions_response2.json() if s['is_active']])
                    print(f"✓ Active sessions after revoke: {active_count}")
    
    # Test logout
    print("\n🚪 Testing Logout...")
    logout_response = requests.post(f"{BASE_URL}/auth/logout/", 
                                   headers={"X-Session-Token": token})
    print(f"Logout response: {logout_response.status_code}")

if __name__ == "__main__":
    test_session_management()