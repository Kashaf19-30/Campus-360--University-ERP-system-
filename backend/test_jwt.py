import jwt
import requests
from django.conf import settings
import json

BASE_URL = "http://localhost:8000/api"

def test_jwt_token():
    print("\n" + "="*60)
    print("🔑 JWT TOKEN TESTING")
    print("="*60)
    
    # Login to get token
    login_response = requests.post(f"{BASE_URL}/auth/login/", json={
        "email": "admin@university.edu",
        "password": "admin123"
    })
    
    if login_response.status_code == 200:
        token = login_response.json()['token']
        print(f"✓ Token received: {token[:50]}...")
        
        # Decode token
        try:
            # Note: You need to have the secret key
            # This is just for testing - don't hardcode in production
            decoded = jwt.decode(token, options={"verify_signature": False})
            print(f"\n📋 Decoded Token Payload:")
            print(json.dumps(decoded, indent=2))
            
            # Check required fields
            required_fields = ['user_id', 'email', 'user_type', 'exp', 'iat']
            missing_fields = [field for field in required_fields if field not in decoded]
            
            if missing_fields:
                print(f"\n❌ Missing fields: {missing_fields}")
            else:
                print("\n✅ All required fields present in token!")
                
            # Check user_type (should be 'user_type', not 'role')
            if 'user_type' in decoded:
                print(f"✓ user_type: {decoded['user_type']}")
            if 'role' in decoded:
                print("⚠️  WARNING: 'role' field found - should be 'user_type'")
                
        except Exception as e:
            print(f"❌ Error decoding token: {e}")
    else:
        print("❌ Failed to get token")

if __name__ == "__main__":
    test_jwt_token()