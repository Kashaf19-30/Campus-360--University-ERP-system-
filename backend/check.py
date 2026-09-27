import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

import re
from accounts import models, views, serializers, utils, permissions
import inspect

def check_consistency():
    print("="*60)
    print("CODE CONSISTENCY CHECKER")
    print("="*60)
    
    issues = []
    
    # 1. Check models for correct field names
    print("\n1. CHECKING MODELS...")
    if hasattr(models.User, 'user_type'):
        print("  ✓ User model has 'user_type' field")
    else:
        issues.append("User model missing 'user_type' field")
    
    if hasattr(models.User, 'user_role'):
        issues.append("User model has 'user_role' field - should be 'user_type'")
    
    # 2. Check utils.py
    print("\n2. CHECKING UTILS.PY...")
    with open('accounts/utils.py', 'r') as f:
        utils_content = f.read()
        if "user.user_type" in utils_content:
            print("  ✓ utils.py uses user.user_type")
        if "user.user_role" in utils_content:
            issues.append("utils.py still uses user.user_role (should be user.user_type)")
    
    # 3. Check views.py
    print("\n3. CHECKING VIEWS.PY...")
    with open('accounts/views.py', 'r') as f:
        views_content = f.read()
        if "user.user_type" in views_content:
            print("  ✓ views.py uses user.user_type")
        if "user.user_role" in views_content:
            issues.append("views.py still uses user.user_role (should be user.user_type)")
    
    # 4. Check serializers.py
    print("\n4. CHECKING SERIALIZERS.PY...")
    with open('accounts/serializers.py', 'r') as f:
        serializers_content = f.read()
        if "user_type" in serializers_content:
            print("  ✓ serializers.py includes user_type")
        if "user_role" in serializers_content:
            issues.append("serializers.py includes user_role (should be user_type)")
    
    # 5. Check permissions.py
    print("\n5. CHECKING PERMISSIONS.PY...")
    with open('accounts/permissions.py', 'r') as f:
        permissions_content = f.read()
        if "user_type" in permissions_content:
            print("  ✓ permissions.py uses user_type")
        if "user_role" in permissions_content:
            issues.append("permissions.py uses user_role (should be user_type)")
    
    # 6. Check URL patterns
    print("\n6. CHECKING URLS.PY...")
    with open('accounts/urls.py', 'r') as f:
        urls_content = f.read()
        expected_endpoints = [
            'auth/register/', 'auth/login/', 'auth/logout/', 
            'auth/me/', 'auth/change-password/', 'roles/'
        ]
        for endpoint in expected_endpoints:
            if endpoint in urls_content:
                print(f"  ✓ {endpoint} endpoint exists")
            else:
                issues.append(f"Missing {endpoint} endpoint")
    
    # 7. Check JWT token generation
    print("\n7. CHECKING JWT TOKEN...")
    try:
        from accounts.utils import generate_jwt_token
        from accounts.models import User
        
        # Get a test user
        test_user = User.objects.first()
        if test_user:
            token = generate_jwt_token(test_user)
            print(f"  ✓ JWT token generation works")
            
            # Decode to check payload
            import jwt
            from django.conf import settings
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            if 'user_type' in payload:
                print(f"  ✓ JWT payload contains 'user_type'")
            if 'role' in payload:
                issues.append("JWT payload contains 'role' - should be 'user_type'")
    except Exception as e:
        issues.append(f"JWT token generation error: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    if issues:
        print(f"⚠️  {len(issues)} ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("✓ NO ISSUES FOUND! Code is consistent.")
    
    print("="*60)

if __name__ == "__main__":
    check_consistency()