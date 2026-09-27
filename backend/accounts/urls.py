# accounts/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/me/', views.get_current_user, name='current-user'),
    path('auth/change-password/', views.change_password, name='change-password'),
    path('auth/refresh/', views.refresh_token, name='refresh-token'),
    
    # Password reset endpoints
    path('auth/password-reset/request/', views.request_password_reset, name='request-reset'),
    path('auth/password-reset/confirm/', views.confirm_password_reset, name='confirm-reset'),
    
    # Session management endpoints
    path('auth/sessions/', views.get_user_sessions, name='user-sessions'),
    path('auth/sessions/<int:session_id>/revoke/', views.revoke_session, name='revoke-session'),
    
    # Role management endpoints
    path('roles/', views.get_roles, name='roles'),
    path('roles/assign/', views.assign_role, name='assign-role'),
    path('roles/remove/', views.remove_role, name='remove-role'),
    path('roles/user/', views.get_user_roles, name='user-roles'),
    path('roles/user/<int:user_id>/', views.get_user_roles, name='user-roles-specific'),
    path('users/change-type/', views.change_user_type, name='change-user-type'),
    path('admin/create-credentials/', views.create_user_credentials, name='create-credentials'),
    path('audit-logs/', views.list_audit_logs, name='audit-logs'),
    path('permissions/', views.list_app_permissions, name='app-permissions'),
    path('role-permissions/', views.list_role_permissions, name='role-permissions'),
    path('roles/<int:role_id>/permissions/', views.role_permissions_detail, name='role-permissions-detail'),
]