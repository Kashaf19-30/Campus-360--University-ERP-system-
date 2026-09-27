import jwt
import uuid
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import LoginSession, PasswordReset 

def generate_jwt_token(user, session_token: str):
    """Generate JWT token bound to an active login session."""
    payload = {
        'user_id': user.user_id,
        'email': user.email,
        'user_type': user.user_type,
        'sid': session_token,
        'exp': datetime.utcnow() + timedelta(minutes=20),
        'iat': datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return token

def create_login_session(user, request):
    """Create a new login session"""
    session_token = str(uuid.uuid4())
    expires_at = timezone.now() + timedelta(hours=2)
    
    # Get client IP and device info
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    
    device_info = request.META.get('HTTP_USER_AGENT', '')
    
    # Deactivate all other active sessions for this user
    LoginSession.objects.filter(user=user, is_active=True).update(is_active=False)
    
    # Create new session
    session = LoginSession.objects.create(
        user=user,
        ip_address=ip_address,
        device_info=device_info,
        session_token=session_token,
        expires_at=expires_at
    )
    
    return session

def generate_password_reset_token(user):
    """Generate a password reset token"""
    token = str(uuid.uuid4())
    expires_at = timezone.now() + timedelta(hours=24)
    
    # Deactivate any existing unused reset tokens for this user
    PasswordReset.objects.filter(user=user, is_used=False).update(is_used=True)
    
    # Create new reset token
    reset = PasswordReset.objects.create(
        user=user,
        reset_token=token,
        expires_at=expires_at
    )
    
    return token, expires_at

def decode_jwt_token(token):
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.InvalidTokenError:
        return None