from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import logout as django_logout
from django.utils import timezone
from django.db import transaction
from .models import User, LoginSession, PasswordReset, UserRole, Role, AuditLog, Permission, RolePermission
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    RoleSerializer, LoginSessionSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, ChangePasswordSerializer
)
from .utils import generate_jwt_token, create_login_session, generate_password_reset_token, decode_jwt_token
from .permissions import IsAdmin, require_permission
from .rbac import ensure_user_role_for_type, get_user_permission_names
from .rbac_policy import validate_role_permission_update, PROTECTED_ROLE_NAME
from .audit import log_audit
from faculty.models import Faculty, EmployeeProfile, Designation
from academics.models import Department, DegreeProgram
import jwt
from django.conf import settings

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """User registration endpoint"""
    from admissions.settings_utils import is_admissions_open
    if not is_admissions_open():
        return Response(
            {'error': 'Admissions are currently closed. Registration is not available.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        from django.db import IntegrityError
        try:
            with transaction.atomic():
                user = serializer.save()
                ensure_user_role_for_type(user)

                from admissions.models import Applicant
                profile_data = getattr(user, '_registration_profile', {}) or {}
                dob = profile_data.get('date_of_birth') or None
                cnic = profile_data.get('cnic') or None
                if cnic == '':
                    cnic = None
                Applicant.objects.update_or_create(
                    user=user,
                    defaults={
                        'first_name': profile_data.get('first_name') or '',
                        'last_name': profile_data.get('last_name') or '',
                        'gender': profile_data.get('gender') or '',
                        'date_of_birth': dob,
                        'cnic': cnic,
                        'phone': profile_data.get('phone') or '',
                    },
                )

                # Auto-login after registration
                session = create_login_session(user, request)
                token = generate_jwt_token(user, session.session_token)
        except IntegrityError as exc:
            msg = str(exc).lower()
            if 'username' in msg:
                return Response(
                    {'username': ['This username is already taken.']},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if 'email' in msg:
                return Response(
                    {'email': ['This email is already registered.']},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {'error': 'Registration failed due to a duplicate value.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get user roles
        user_roles = UserRole.objects.filter(user=user).select_related('role')
        roles = [ur.role.role_name for ur in user_roles]
        permissions = sorted(get_user_permission_names(user))
        if '*' in permissions:
            permissions = ['*']

        return Response({
            'message': 'Registration successful',
            'user': {
                'user_id': user.user_id,
                'username': user.username,
                'email': user.email,
                'user_type': user.user_type,
                'roles': roles,
                'permissions': permissions,
            },
            'token': token,
            'session_id': session.session_id,
            'session_token': session.session_token,
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """User login endpoint"""
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        ensure_user_role_for_type(user)
        
        session = create_login_session(user, request)
        token = generate_jwt_token(user, session.session_token)
        
        # Get user roles and permissions
        user_roles = UserRole.objects.filter(user=user).select_related('role')
        roles = [ur.role.role_name for ur in user_roles]
        permissions = sorted(get_user_permission_names(user))
        if '*' in permissions:
            permissions = ['*']
        
        return Response({
            'message': 'Login successful',
            'user': {
                'user_id': user.user_id,
                'username': user.username,
                'email': user.email,
                'user_type': user.user_type,
                'roles': roles,
                'permissions': permissions,
            },
            'token': token,
            'session_id': session.session_id,
            'session_token': session.session_token,
            'expires_in': '20 minutes'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """User logout endpoint — revokes the JWT-bound login session."""
    try:
        auth_header = request.headers.get('Authorization', '')
        sid = None
        if auth_header.startswith('Bearer '):
            payload = decode_jwt_token(auth_header[7:])
            sid = payload.get('sid') if payload else None

        session_token = request.headers.get('X-Session-Token') or sid
        if session_token:
            LoginSession.objects.filter(
                session_token=session_token,
                user=request.user,
                is_active=True,
            ).update(is_active=False, logout_time=timezone.now())

        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
    except Exception:
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """Get current authenticated user info"""
    ensure_user_role_for_type(request.user)
    serializer = UserSerializer(request.user)
    
    user_roles = UserRole.objects.filter(user=request.user).select_related('role')
    roles = [ur.role.role_name for ur in user_roles]
    permissions = sorted(get_user_permission_names(request.user))
    if '*' in permissions:
        permissions = ['*']
    
    data = serializer.data
    data['roles'] = roles
    data['permissions'] = permissions
    
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change user password"""
    serializer = ChangePasswordSerializer(data=request.data)
    if serializer.is_valid():
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        
        if not request.user.check_password(old_password):
            return Response({'error': 'Current password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
        
        request.user.set_password(new_password)
        request.user.save()

        LoginSession.objects.filter(user=request.user, is_active=True).update(
            is_active=False, logout_time=timezone.now()
        )
        
        return Response({'message': 'Password changed successfully. Please login again.'})
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """Request password reset email"""
    serializer = PasswordResetRequestSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        user = User.objects.filter(email=email).first()

        if user:
            token, _expires_at = generate_password_reset_token(user)
            frontend_base = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')
            reset_link = f"{frontend_base}/reset-password?token={token}"
            # Email delivery can be wired here when SMTP is configured.
            if settings.DEBUG:
                return Response({
                    'message': 'If an account exists for this email, a reset link has been sent.',
                    'reset_link': reset_link,
                    'reset_token': token,
                }, status=status.HTTP_200_OK)

        return Response({
            'message': 'If an account exists for this email, a reset link has been sent.',
        }, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    """Confirm password reset with token"""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if serializer.is_valid():
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        try:
            reset = PasswordReset.objects.get(
                reset_token=token,
                is_used=False,
                expires_at__gt=timezone.now()
            )
            
            user = reset.user
            user.set_password(new_password)
            user.save()
            
            reset.is_used = True
            reset.used_at = timezone.now()
            reset.save()
            
            # Deactivate all active sessions
            LoginSession.objects.filter(user=user, is_active=True).update(is_active=False)
            
            return Response({'message': 'Password reset successful. Please login.'})
            
        except PasswordReset.DoesNotExist:
            return Response({'error': 'Invalid or expired reset token'}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """Issue a new JWT when the login session is still active (extends working session beyond 20 min JWT)."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response({'error': 'Authorization required.'}, status=status.HTTP_401_UNAUTHORIZED)

    token = auth_header[7:]
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=['HS256'],
            options={'verify_exp': False},
        )
    except jwt.InvalidTokenError:
        return Response({'error': 'Invalid token.'}, status=status.HTTP_401_UNAUTHORIZED)

    sid = payload.get('sid')
    user_id = payload.get('user_id')
    if not sid or not user_id:
        return Response({'error': 'Invalid token payload.'}, status=status.HTTP_401_UNAUTHORIZED)

    session = LoginSession.objects.filter(
        session_token=sid,
        user_id=user_id,
        is_active=True,
        expires_at__gt=timezone.now(),
    ).first()
    if not session:
        return Response({'error': 'Session expired. Please login again.'}, status=status.HTTP_401_UNAUTHORIZED)

    user = User.objects.filter(user_id=user_id, is_active=True).first()
    if not user:
        return Response({'error': 'User not found.'}, status=status.HTTP_401_UNAUTHORIZED)

    new_token = generate_jwt_token(user, sid)
    return Response({
        'token': new_token,
        'expires_in': '20 minutes',
        'session_expires_at': session.expires_at.isoformat(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_sessions(request):
    """Get all active sessions for current user"""
    sessions = LoginSession.objects.filter(user=request.user, is_active=True)
    serializer = LoginSessionSerializer(sessions, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_session(request, session_id):
    """Revoke a specific session"""
    try:
        session = LoginSession.objects.get(
            session_id=session_id,
            user=request.user,
            is_active=True
        )
        session.is_active = False
        session.logout_time = timezone.now()
        session.save()
        
        return Response({'message': 'Session revoked successfully'})
    except LoginSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAdmin])
def get_roles(request):
    """Get all roles (admin only)"""
    roles = Role.objects.all()
    serializer = RoleSerializer(roles, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAdmin])
def assign_role(request):
    """Assign role to user (admin only)"""
    user_id = request.data.get('user_id')
    role_id = request.data.get('role_id')
    
    if not user_id or not role_id:
        return Response({'error': 'user_id and role_id are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(user_id=user_id)
        role = Role.objects.get(role_id=role_id)
        
        # Check if assignment already exists
        user_role, created = UserRole.objects.get_or_create(
            user=user,
            role=role,
            defaults={'assigned_by': request.user}
        )
        
        if created:
            return Response({
                'message': 'Role assigned successfully',
                'user': user.email,
                'role': role.role_name
            })
        else:
            return Response({
                'message': 'Role already assigned to this user',
                'user': user.email,
                'role': role.role_name
            })
            
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Role.DoesNotExist:
        return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAdmin])
def remove_role(request):
    """Remove role from user (admin only)"""
    user_id = request.data.get('user_id')
    role_id = request.data.get('role_id')
    
    if not user_id or not role_id:
        return Response({'error': 'user_id and role_id are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(user_id=user_id)
        role = Role.objects.get(role_id=role_id)
        
        # Delete the role assignment
        deleted, _ = UserRole.objects.filter(user=user, role=role).delete()
        
        if deleted:
            return Response({
                'message': 'Role removed successfully',
                'user': user.email,
                'role': role.role_name
            })
        else:
            return Response({
                'message': 'Role was not assigned to this user'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Role.DoesNotExist:
        return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_roles(request, user_id=None):
    """Get roles for a specific user (admin only for other users, users can see their own)"""
    # If no user_id provided, get current user's roles
    if user_id is None:
        target_user = request.user
    else:
        if not IsAdmin().has_permission(request, None):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        try:
            target_user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    user_roles = UserRole.objects.filter(user=target_user).select_related('role')
    roles = [{
        'role_id': ur.role.role_id,
        'role_name': ur.role.role_name,
        'description': ur.role.description,
        'assigned_at': ur.assigned_at,
        'assigned_by': ur.assigned_by.email if ur.assigned_by else None
    } for ur in user_roles]
    
    return Response({
        'user_id': target_user.user_id,
        'email': target_user.email,
        'username': target_user.username,
        'roles': roles
    })


@api_view(['POST'])
@permission_classes([IsAdmin])
def change_user_type(request):
    """Change a user's primary role (user_type) for dashboard routing."""
    user_id = request.data.get('user_id')
    new_type = request.data.get('user_type')

    valid_types = [choice[0] for choice in User.USER_TYPE_CHOICES]
    if not user_id or not new_type:
        return Response(
            {'error': 'user_id and user_type are required'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if new_type not in valid_types:
        return Response(
            {'error': f'user_type must be one of: {", ".join(valid_types)}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.get(user_id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    # Restriction: Admin can only change applicant into student role only
    if user.user_type == 'applicant' and new_type != 'student':
        return Response(
            {'error': 'Applicants can only be changed to the student role.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if user.user_id == request.user.user_id and new_type != 'admin':
        return Response(
            {'error': 'You cannot change your own role away from admin.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    old_type = user.user_type
    user.user_type = new_type
    user.save(update_fields=['user_type'])

    role_name_map = {
        'student': 'Student',
        'teacher': 'Teacher',
        'admin': 'Admin',
        'applicant': 'Applicant',
        'finance_officer': 'Finance Officer',
    }
    role_name = role_name_map.get(new_type)
    if role_name:
        role, _ = Role.objects.get_or_create(
            role_name=role_name,
            defaults={'description': f'{role_name} role'},
        )
        UserRole.objects.filter(user=user).delete()
        UserRole.objects.create(user=user, role=role, assigned_by=request.user)

    return Response({
        'message': f'User role changed from {old_type} to {new_type}.',
        'user_id': user.user_id,
        'email': user.email,
        'username': user.username,
        'user_type': user.user_type,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, require_permission('accounts.create_credentials')])
def create_user_credentials(request):
    """
    Admin endpoint to create user credentials and set role (teacher or admin).
    For teachers, auto-populates Faculty record and EmployeeProfile.
    """
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    user_type = request.data.get('user_type') or request.data.get('role')

    if not username or not email or not password or not user_type:
        return Response({'error': 'username, email, password, and user_type/role are required.'}, status=status.HTTP_400_BAD_REQUEST)

    if user_type not in ['admin', 'teacher', 'finance_officer']:
        return Response({'error': 'user_type must be admin, teacher, or finance_officer.'}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(email=email).exists():
        return Response({'error': 'Email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    if user_type == 'teacher':
        dept_id = request.data.get('department_id')
        prog_id = request.data.get('program_id')
        if not dept_id:
            return Response({'error': 'department_id is required for teachers.'}, status=status.HTTP_400_BAD_REQUEST)
        if not prog_id:
            return Response({'error': 'program_id is required for teachers.'}, status=status.HTTP_400_BAD_REQUEST)
        course_id = request.data.get('course_id')
        if not course_id:
            return Response({'error': 'course_id is required for teachers.'}, status=status.HTTP_400_BAD_REQUEST)
        department = Department.objects.filter(department_id=dept_id).first()
        if not department:
            return Response({'error': 'Invalid department_id.'}, status=status.HTTP_400_BAD_REQUEST)
        program = DegreeProgram.objects.filter(program_id=prog_id, department=department).first()
        if not program:
            return Response({'error': 'Invalid program_id for selected department.'}, status=status.HTTP_400_BAD_REQUEST)
        from academics.models import Course, ProgramCourse
        from faculty.models import FacultyCourseAssignment
        course = Course.objects.filter(course_id=course_id).first()
        if not course:
            return Response({'error': 'Invalid course_id.'}, status=status.HTTP_400_BAD_REQUEST)
        if not ProgramCourse.objects.filter(program=program, course=course).exists():
            return Response(
                {'error': f'{course.course_code} is not in {program.program_code} curriculum.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if FacultyCourseAssignment.objects.filter(program=program, course=course, is_active=True).exists():
            return Response(
                {'error': f'{course.course_code} already has a teacher for {program.program_code}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    with transaction.atomic():
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_type=user_type
        )

        role_map = {'admin': 'Admin', 'teacher': 'Teacher', 'finance_officer': 'Finance Officer'}
        role_obj, _ = Role.objects.get_or_create(role_name=role_map[user_type])
        UserRole.objects.create(user=user, role=role_obj, assigned_by=request.user)

        if user_type == 'teacher':
            dept_id = request.data.get('department_id')
            prog_id = request.data.get('program_id')
            desig_id = request.data.get('designation_id')
            department = Department.objects.get(department_id=dept_id)
            program = DegreeProgram.objects.get(program_id=prog_id, department=department)

            designation = None
            if desig_id:
                designation = Designation.objects.filter(designation_id=desig_id).first()
            if not designation:
                designation = Designation.objects.first()
                if not designation:
                    designation = Designation.objects.create(designation_title='Lecturer')

            emp_type = request.data.get('employment_type', 'permanent')
            emp_status = request.data.get('status', 'active')
            joining_date = timezone.now().date()
            year = joining_date.year

            cnic = request.data.get('cnic', '0000000000000')
            dob = request.data.get('date_of_birth') or request.data.get('dob') or '2000-01-01'
            gender = request.data.get('gender', 'Male')
            phone = request.data.get('phone_number') or request.data.get('phone') or '03000000000'
            em_name = request.data.get('emergency_contact_name') or 'N/A'
            em_phone = request.data.get('emergency_contact_phone') or '03000000000'
            em_rel = request.data.get('emergency_contact_relation') or 'Parent'
            curr_addr = request.data.get('current_address') or 'N/A'
            perm_addr = request.data.get('permanent_address') or curr_addr

            count = Faculty.objects.count()
            emp_code = f"FAC-{year}-{str(count + 1).zfill(4)}"
            qual = request.data.get('qualification', 'Master')
            fac_obj = Faculty.objects.create(
                user=user,
                department=department,
                program=program,
                designation=designation,
                employee_code=emp_code,
                qualification=qual,
                joining_date=joining_date,
                employment_type=emp_type if emp_type in ('permanent', 'visiting', 'contract', 'contractual') else 'permanent',
                status=emp_status,
                office_floor=str(request.data.get('office_floor', '')).strip(),
                office_hours=str(request.data.get('office_hours', '')).strip(),
                profile_completed=False,
            )
            EmployeeProfile.objects.create(
                employee_id=fac_obj.faculty_id,
                employee_type='faculty',
                cnic=cnic if not EmployeeProfile.objects.filter(cnic=cnic).exists() else f"{cnic[:9]}{count+1:04d}",
                date_of_birth=dob,
                gender=gender,
                phone_number=phone,
                emergency_contact_name=em_name,
                emergency_contact_phone=em_phone,
                emergency_contact_relation=em_rel,
                current_address=curr_addr,
                permanent_address=perm_addr,
            )
            from academics.models import Course
            from faculty.assignment_utils import assign_faculty_to_course
            course = Course.objects.get(course_id=request.data.get('course_id'))
            try:
                assign_faculty_to_course(fac_obj, program, course, assigned_by=request.user)
            except ValueError as exc:
                return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    log_audit(request, 'create_credentials', 'user', user.user_id, new_value={'user_type': user_type})

    return Response({
        'message': f'User credentials created successfully with role {user_type}.',
        'user_id': user.user_id,
        'username': user.username,
        'email': user.email,
        'user_type': user.user_type,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated, require_permission('system.view_audit_log')])
def list_audit_logs(request):
    from .serializers import AuditLogSerializer
    logs = AuditLog.objects.select_related('user').order_by('-created_at')[:500]
    table = request.query_params.get('table')
    if table:
        logs = logs.filter(table_name=table)
    return Response(AuditLogSerializer(logs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAdmin])
def list_app_permissions(request):
    from .serializers import PermissionSerializer
    perms = Permission.objects.all().order_by('module_name', 'permission_name')
    return Response(PermissionSerializer(perms, many=True).data)


@api_view(['GET'])
@permission_classes([IsAdmin])
def list_role_permissions(request):
    role_id = request.query_params.get('role_id')
    qs = RolePermission.objects.select_related('role', 'permission')
    if role_id:
        qs = qs.filter(role_id=role_id)
    data = [{
        'role_id': rp.role.role_id,
        'role': rp.role.role_name,
        'permission_id': rp.permission.permission_id,
        'permission': rp.permission.permission_name,
        'module': rp.permission.module_name,
    } for rp in qs]
    return Response(data)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated, require_permission('system.manage_role_permissions')])
def role_permissions_detail(request, role_id):
    """
    GET: permissions assigned to a role.
    PUT: replace role permissions (Teacher, Student, Applicant only).
    """
    try:
        role = Role.objects.get(role_id=role_id)
    except Role.DoesNotExist:
        return Response({'error': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        if role.role_name == PROTECTED_ROLE_NAME:
            perms = Permission.objects.all().order_by('module_name', 'permission_name')
            return Response({
                'role_id': role.role_id,
                'role_name': role.role_name,
                'editable': False,
                'permissions': [{
                    'permission_id': p.permission_id,
                    'permission_name': p.permission_name,
                    'module_name': p.module_name,
                    'description': p.description,
                } for p in perms],
            })
        assigned = RolePermission.objects.filter(role=role).select_related('permission')
        return Response({
            'role_id': role.role_id,
            'role_name': role.role_name,
            'editable': True,
            'permissions': [{
                'permission_id': rp.permission.permission_id,
                'permission_name': rp.permission.permission_name,
                'module_name': rp.permission.module_name,
                'description': rp.permission.description,
            } for rp in assigned],
        })

    permission_names = request.data.get('permission_names')
    if not isinstance(permission_names, list):
        return Response(
            {'error': 'permission_names must be a list of permission name strings.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ok, err = validate_role_permission_update(role, permission_names)
    if not ok:
        return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)

    perm_objs = list(
        Permission.objects.filter(permission_name__in=permission_names)
    )
    found_names = {p.permission_name for p in perm_objs}
    unknown = set(permission_names) - found_names
    if unknown:
        return Response(
            {'error': f'Unknown permissions: {", ".join(sorted(unknown))}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    old_names = sorted(
        RolePermission.objects.filter(role=role)
        .values_list('permission__permission_name', flat=True)
    )

    with transaction.atomic():
        RolePermission.objects.filter(role=role).delete()
        for perm in perm_objs:
            RolePermission.objects.create(role=role, permission=perm)

    log_audit(
        request,
        'update_role_permissions',
        'role',
        role.role_id,
        old_value={'permissions': old_names},
        new_value={'permissions': sorted(permission_names)},
    )

    return Response({
        'message': f'Permissions updated for role {role.role_name}.',
        'role_id': role.role_id,
        'role_name': role.role_name,
        'permission_count': len(perm_objs),
    })
