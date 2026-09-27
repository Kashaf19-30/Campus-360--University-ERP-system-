from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from django.utils import timezone
import jwt
from django.conf import settings

from .models import LoginSession

User = get_user_model()


class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return None

        try:
            parts = auth_header.split()
            if len(parts) != 2:
                raise AuthenticationFailed('Invalid authorization header format. Use: Bearer <token>')

            prefix, token = parts
            if prefix.lower() != 'bearer':
                raise AuthenticationFailed('Invalid token prefix. Use: Bearer')

            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

            user_id = payload.get('user_id')
            if not user_id:
                raise AuthenticationFailed('Invalid token payload: missing user_id')

            sid = payload.get('sid')
            if not sid:
                raise AuthenticationFailed('Session invalid. Please login again.')

            session = LoginSession.objects.filter(
                session_token=sid,
                user_id=user_id,
                is_active=True,
                expires_at__gt=timezone.now(),
            ).first()
            if not session:
                raise AuthenticationFailed('Session expired or revoked. Please login again.')

            user = User.objects.get(user_id=user_id, is_active=True)
            return (user, token)

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token')
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found or inactive')
        except AuthenticationFailed:
            raise
        except Exception as e:
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')

    def authenticate_header(self, request):
        return 'Bearer'
